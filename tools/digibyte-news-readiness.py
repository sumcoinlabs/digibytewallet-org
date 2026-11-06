#!/usr/bin/env python3
# DGB_NEWS_MANAGER_V1 -- created for DigiByte Wallet; stdlib only.
"""Install and maintain a Google News sitemap without replacing existing content."""
import argparse
import datetime as dt
import html
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(os.environ.get('DGB_NEWS_ROOT', '/var/www/digibytewallet-org')).resolve()
NEWS = ROOT / 'news'
BASE = 'https://www.digibytewallet.org'
SITEMAP = ROOT / 'news-sitemap.xml'
ABOUT = NEWS / 'about.html'
INDEX = NEWS / 'index.html'
ROBOTS = ROOT / 'robots.txt'
CRON = Path(os.environ.get('DGB_NEWS_CRON', '/etc/cron.d/digibyte-news-sitemap'))
MANAGED = 'DGB_NEWS_MANAGER_V1'
SM_NS = 'http://www.sitemaps.org/schemas/sitemap/0.9'
NEWS_NS = 'http://www.google.com/schemas/sitemap-news/0.9'
ET.register_namespace('', SM_NS)
ET.register_namespace('news', NEWS_NS)


class Metadata(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.meta = {}
        self.canonical = ''
        self.alternates = []
        self.json_scripts = []
        self.script_parts = None
        self.h1_level = 0
        self.h1_text = []
        self.noindex = False
        self.lang = ''
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'html':
            self.lang = (a.get('lang') or '').lower()
        if tag == 'meta':
            k = (a.get('property') or a.get('name') or a.get('itemprop') or '').lower()
            v = a.get('content') or ''
            if k and v:
                self.meta[k] = v
            if k in ('robots', 'googlebot', 'googlebot-news') and re.search(r'\bnoindex\b', v, re.I):
                self.noindex = True
        if tag == 'link':
            rel = (a.get('rel') or '').lower().split()
            if 'canonical' in rel:
                self.canonical = a.get('href') or ''
            if 'alternate' in rel:
                self.alternates.append((a.get('type'), a.get('href')))
        if tag == 'time' and a.get('datetime'):
            self.meta.setdefault('time:datetime', a['datetime'])
        if tag == 'script' and (a.get('type') or '').lower() == 'application/ld+json':
            self.script_parts = []
        if tag == 'h1':
            self.h1_level += 1
        elif self.h1_level:
            self.h1_level += 1
    def handle_data(self, data):
        if self.script_parts is not None:
            self.script_parts.append(data)
        if self.h1_level:
            self.h1_text.append(data)
    def handle_endtag(self, tag):
        if tag == 'script' and self.script_parts is not None:
            self.json_scripts.append(''.join(self.script_parts))
            self.script_parts = None
        if self.h1_level:
            self.h1_level -= 1
    def article_json(self):
        def walk(o):
            if isinstance(o, list):
                for v in o:
                    yield from walk(v)
            elif isinstance(o, dict):
                typ = o.get('@type', [])
                types = [typ] if isinstance(typ, str) else typ if isinstance(typ, list) else []
                if any(t in ('NewsArticle', 'Article', 'BlogPosting') or
                       (isinstance(t, str) and t.endswith(('/NewsArticle', '/Article', '/BlogPosting')))
                       for t in types):
                    yield o
                for v in o.values():
                    if isinstance(v, (dict, list)):
                        yield from walk(v)
        for raw in self.json_scripts:
            try:
                yield from walk(json.loads(raw))
            except (ValueError, TypeError):
                continue


def read_metadata(path):
    parser = Metadata()
    parser.feed(path.read_text(encoding='utf-8'))
    return parser


def date_info(value):
    """Return (original W3C date, comparable UTC datetime); date-only UTC midnight is a conservative expiry boundary."""
    if not isinstance(value, str):
        return None
    s = value.strip()
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', s):
        try:
            day = dt.date.fromisoformat(s)
            return s, dt.datetime.combine(day, dt.time.min, dt.timezone.utc)
        except ValueError:
            return None
    try:
        parsed = dt.datetime.fromisoformat(s.replace('Z', '+00:00'))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            return None
        return s, parsed.astimezone(dt.timezone.utc)
    except ValueError:
        return None


def inspect_articles(now, verbose=True):
    candidates = sorted(NEWS.rglob('*.html'))
    records, problems, found = [], [], 0
    for path in candidates:
        if path.name in ('index.html', 'about.html'):
            continue
        if '/assets/' in str(path) or '/static/' in str(path):
            continue
        try:
            m = read_metadata(path)
        except Exception as e:
            problems.append(f'{path.relative_to(ROOT)}: cannot parse: {e}')
            continue
        article_data = list(m.article_json())
        published = None
        title = ' '.join(' '.join(m.h1_text).split())
        for obj in article_data:
            published = published or obj.get('datePublished')
            title = title or (obj.get('headline') if isinstance(obj.get('headline'), str) else '')
        published = published or m.meta.get('article:published_time') or m.meta.get('datepublished') or m.meta.get('time:datetime')
        if not published and not article_data:
            # Other HTML pages aren't articles.
            continue
        found += 1
        rel = path.relative_to(ROOT).as_posix()
        if not article_data:
            problems.append(f'{rel}: Article/NewsArticle JSON-LD not detected; review structured data')
        elif not any(obj.get('author') for obj in article_data) and not m.meta.get('author'):
            problems.append(f'{rel}: author missing from article JSON-LD/meta; consider an identifiable byline')
        expected = f'{BASE}/{rel}'
        canonical = urllib.parse.urljoin(BASE + '/', m.canonical) if m.canonical else ''
        if m.noindex:
            problems.append(f'{rel}: noindex detected; excluded')
            continue
        if not canonical or canonical != expected:
            problems.append(f'{rel}: canonical missing/mismatch ({m.canonical!r}); excluded')
            continue
        if not title or not published:
            problems.append(f'{rel}: missing headline or original publication date; excluded')
            continue
        date_record = date_info(published)
        if date_record is None:
            problems.append(f'{rel}: unsupported/no-timezone datePublished {published!r}; excluded')
            continue
        original, timestamp = date_record
        age = now - timestamp
        if age < dt.timedelta(minutes=-1):
            problems.append(f'{rel}: publication date in the future; excluded')
            continue
        if age > dt.timedelta(hours=48):
            continue
        if m.lang and not (m.lang == 'en' or m.lang.startswith('en-')):
            problems.append(f'{rel}: non-English page ({m.lang}); excluded')
            continue
        records.append((timestamp, expected, original, title))
    records.sort(reverse=True)
    if len(records) > 1000:
        raise RuntimeError('More than 1,000 qualifying articles; split news sitemaps before continuing.')
    if verbose:
        print(f'Inspected {len(candidates)} HTML files; {found} article candidates; {len(records)} eligible in last 48 hours')
        for _, url, pub, title in records:
            print(f'  INCLUDE {pub} {url} — {title}')
        for problem in problems:
            print('  NOTICE ' + problem)
    return records, problems, found


def sitemap_bytes(records):
    root = ET.Element(f'{{{SM_NS}}}urlset')
    for _, url, date, title in records:
        node = ET.SubElement(root, f'{{{SM_NS}}}url')
        ET.SubElement(node, f'{{{SM_NS}}}loc').text = url
        news = ET.SubElement(node, f'{{{NEWS_NS}}}news')
        publication = ET.SubElement(news, f'{{{NEWS_NS}}}publication')
        ET.SubElement(publication, f'{{{NEWS_NS}}}name').text = 'DigiByte Wallet'
        ET.SubElement(publication, f'{{{NEWS_NS}}}language').text = 'en'
        ET.SubElement(news, f'{{{NEWS_NS}}}publication_date').text = date
        ET.SubElement(news, f'{{{NEWS_NS}}}title').text = title
    payload = ET.tostring(root, encoding='utf-8', xml_declaration=True)
    return payload.replace(b'?>', b'?>\n<!-- DGB_NEWS_MANAGER_V1 -->', 1) + b'\n'


def atomic_write(path, data, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_bytes() if path.exists() else None
    if existing == data:
        return False
    fd, name = tempfile.mkstemp(prefix='.' + path.name + '.', suffix='.pending', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(name, mode)
        if path.exists():
            st = path.stat()
            os.chown(name, st.st_uid, st.st_gid)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)
    return True


def about_html():
    structured = json.dumps({
        '@context': 'https://schema.org', '@type': 'AboutPage',
        'name': 'About the DigiByte Wallet Newsroom',
        'url': BASE + '/news/about.html',
        'publisher': {'@type': 'Organization', 'name': 'DigiByte Wallet',
                      'url': BASE, 'legalName': 'Sigma Systems Inc.', 'email': 'digibytewalletorg@gmail.com'}
    }, ensure_ascii=False).replace('<', '\\u003c')
    return f'''<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>About the Newsroom &amp; Editorial Policy | DigiByte Wallet</title>
<meta name="description" content="Learn who publishes DigiByte Wallet news, how releases are verified, our editorial policy, corrections process, and how to contact the project.">
<link rel="canonical" href="{BASE}/news/about.html">
<link rel="alternate" type="application/rss+xml" title="DigiByte Wallet News RSS" href="{BASE}/news/feed.xml">
<meta name="robots" content="index,follow,max-image-preview:large"><meta property="og:type" content="website"><meta property="og:title" content="About the DigiByte Wallet Newsroom">
<meta property="og:url" content="{BASE}/news/about.html">
<meta property="og:description" content="Publisher details, editorial standards, disclosures and contact information for DigiByte Wallet News.">
<script type="application/ld+json">{structured}</script>
<style>
:root{{color-scheme:dark;--bg:#081429;--panel:#0e2340;--edge:#275477;--text:#edf5fd;--muted:#b4c9db;--accent:#48c9df}}
*{{box-sizing:border-box}}body{{margin:0;background:radial-gradient(ellipse at 90% 0%,#15436b 0%,var(--bg) 52%);color:var(--text);font:16px/1.7 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
a{{color:#8ce9f9}}a:hover{{color:#fff}}.wrap{{width:min(960px,calc(100% - 36px));margin:auto}}
header{{border-bottom:1px solid var(--edge);background:#07172ad9}}.nav{{min-height:74px;display:flex;align-items:center;justify-content:space-between;gap:20px;flex-wrap:wrap}}
.brand{{font-weight:760;letter-spacing:.01em;text-decoration:none;color:#fff;font-size:1.1rem}}nav{{display:flex;gap:22px;flex-wrap:wrap}}nav a{{color:var(--muted);text-decoration:none;font-weight:600}}
main{{padding:64px 0 80px}}.eyebrow{{color:var(--accent);font-size:.77rem;letter-spacing:.16em;text-transform:uppercase;font-weight:800}}
h1{{font-size:clamp(2.2rem,5vw,3.6rem);line-height:1.14;letter-spacing:-.04em;margin:12px 0 20px}}.lead{{font-size:1.15rem;color:#d1e4f2;max-width:760px}}
.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px;margin:38px 0 22px}}section{{margin:22px 0}}.panel{{border:1px solid var(--edge);border-radius:18px;background:var(--panel);padding:26px}}h2{{font-size:1.32rem;line-height:1.3;margin:0 0 12px}}p{{margin:0 0 14px}}p:last-child{{margin-bottom:0}}.muted{{color:var(--muted)}}
footer{{padding:28px 0;border-top:1px solid var(--edge);color:var(--muted)}}.footer{{display:flex;justify-content:space-between;flex-wrap:wrap;gap:16px}}
@media(max-width:680px){{.grid{{grid-template-columns:1fr}}main{{padding-top:44px}}.nav{{padding:16px 0}}}}
</style></head><body>
<header><div class="wrap nav"><a class="brand" href="/news/">DigiByte Wallet <span style="color:#7ceaf1">· Newsroom</span></a>
<nav aria-label="Site navigation"><a href="/">Home</a><a href="/news/">News</a><a href="/news/about.html" aria-current="page">About newsroom</a><a href="/#download">Get the wallet</a></nav></div></header>
<main class="wrap"><div class="eyebrow">Publisher information · Editorial transparency</div>
<h1>About the DigiByte Wallet Newsroom</h1>
<p class="lead">Official updates, original release reporting and practical explanations about DigiByte Wallet and its related open-source development.</p>
<div class="grid">
<section class="panel"><h2>Who publishes this newsroom</h2><p>DigiByte Wallet is the publisher of this newsroom. It is operated as a first-party publication for the DigiByte Wallet software project—not as an independent third-party news outlet or an official publication of the DigiByte blockchain network.</p><p>We cover wallet releases, development milestones, security-related maintenance and material changes affecting our software. The site's published privacy policy identifies Sigma Systems Inc. in its copyright notice.</p></section>
<section class="panel"><h2>Contact the publisher</h2><p>For questions, corrections, technical clarifications and press inquiries, contact <a href="mailto:digibytewalletorg@gmail.com">digibytewalletorg@gmail.com</a>.</p><p class="muted">Publication: DigiByte Wallet Newsroom<br>Website: <a href="{BASE}">digibytewallet.org</a><br>Language: English</p></section>
<section class="panel"><h2>Editorial standards</h2><p>We distinguish released software from previews or planned features, link to primary technical sources where available, and avoid treating automated testing as a third-party security audit. Release information is checked against published packages, source changes or official distribution listings before describing a feature as available.</p><p>Articles carry publication dates and identify the project or editorial author responsible for the information.</p></section>
<section class="panel"><h2>Corrections and updates</h2><p>We welcome factual corrections. Email the article URL and the issue to our contact address. Material corrections are made on the original page, with an update note when warranted. We do not silently republish old articles as new simply to change their date.</p></section>
<section class="panel"><h2>Editorial independence and advertising</h2><p>This newsroom publishes first-party project news and therefore has a direct interest in the software it covers. Our website or app may display advertising to support development. Advertising does not turn release previews into completed releases, and any paid or sponsored editorial content will be clearly labeled.</p></section>
<section class="panel"><h2>Sources and scope</h2><p>We prioritize publicly verifiable project resources such as the <a href="https://github.com/sumcoinlabs/digibyte_flutter">wallet's source code</a>, package registries, version histories and official app-store listings. DigiByte is a decentralized blockchain; publishing DigiByte Wallet news does not imply ownership or control of that network.</p></section>
</div><p class="muted">For the latest announcements, visit <a href="/news/">DigiByte Wallet News</a>. This page describes our editorial approach and does not provide personalized investment advice.</p></main>
<footer><div class="wrap footer"><span>© 2026 DigiByte Wallet · Newsroom</span><span><a href="/news/">News</a> · <a href="/privacy/">Privacy</a> · <a href="mailto:digibytewalletorg@gmail.com">Contact</a></span></div></footer>
<!-- {MANAGED} -->
</body></html>
'''.encode('utf-8')


def footer_with_about(old):
    if 'href="/news/about.html"' in old or "href='/news/about.html'" in old:
        return old
    start = old.lower().rfind('<footer')
    if start < 0:
        raise RuntimeError('Expected existing newsroom footer; refusing to modify unexpected HTML')
    nav_end = old.lower().rfind('</nav>', start)
    footer_end = old.lower().find('</footer>', start)
    if nav_end < 0 or footer_end < 0 or nav_end > footer_end:
        raise RuntimeError('Expected existing newsroom footer navigation; refusing unexpected layout')
    return old[:nav_end] + '<a href="/news/about.html">About &amp; editorial policy</a>' + old[nav_end:]


def feed_audit(m):
    refs = [(kind, url) for kind, url in m.alternates if url and kind]
    scanned = set()
    for kind, link in refs:
        url = urllib.parse.urlparse(urllib.parse.urljoin(BASE + '/news/', link))
        if url.hostname not in ('www.digibytewallet.org', 'digibytewallet.org'):
            continue
        path = ROOT / urllib.parse.unquote(url.path).lstrip('/')
        if path.is_file():
            scanned.add(path)
        else:
            print(f'  WARN linked feed missing from website directory: {link}')
    for folder in (NEWS, ROOT):
        for name in ('feed.xml', 'rss.xml', 'atom.xml', 'feed.json', 'news.json'):
            path = folder / name
            if path.is_file():
                scanned.add(path)
    if not scanned:
        print('  WARN no RSS/JSON feed files discovered by common filenames or newsroom alternate links')
    for path in sorted(scanned):
        try:
            if path.suffix == '.json':
                data = json.loads(path.read_text(encoding='utf-8'))
                count = len(data.get('items', [])) if isinstance(data, dict) else len(data) if isinstance(data, list) else 0
            else:
                node = ET.parse(path).getroot()
                count = sum(1 for x in node.iter() if x.tag.rsplit('}', 1)[-1] in ('item', 'entry'))
            print(f'  PASS feed: {path.relative_to(ROOT)} ({count} entries)')
        except Exception as e:
            print(f'  WARN feed invalid: {path.relative_to(ROOT)} ({e})')


def audit_regular_sitemap():
    path = ROOT / 'sitemap.xml'
    if not path.exists():
        print('  WARN /sitemap.xml is missing from the expected site root')
        return
    try:
        root = ET.parse(path).getroot()
        tag = root.tag.rsplit('}', 1)[-1]
        if tag not in ('urlset', 'sitemapindex'):
            print(f'  WARN sitemap.xml has unexpected root element {tag}')
        else:
            print(f'  PASS existing sitemap.xml is valid XML ({tag}); left unchanged')
    except Exception as e:
        print(f'  WARN existing sitemap.xml invalid XML ({e}); left unchanged')


def check_public():
    print('\nPUBLIC HTTP CHECKS (may be blocked by local egress or CDN cache):')
    for relative, expected in (('/news-sitemap.xml', 'xml'), ('/news/about.html', 'html'), ('/news/', 'html'), ('/robots.txt', 'robots'), ('/sitemap.xml', 'regular_xml')):
        url = BASE + relative
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'DigiByteWallet-Newsroom-Deployment-Check/1.0', 'Cache-Control': 'no-cache'})
            with urllib.request.urlopen(req, timeout=10) as r:
                b = r.read(20000)
                mime = r.headers.get('Content-Type', '')
                if expected == 'xml':
                    ET.fromstring(b if len(b) < 20000 else SITEMAP.read_bytes())
                    okay = b'<urlset' in b or b':urlset' in b
                elif expected == 'regular_xml':
                    okay = b'<urlset' in b or b'<sitemapindex' in b or b':urlset' in b or b':sitemapindex' in b
                elif expected == 'robots':
                    okay = b'Sitemap: https://www.digibytewallet.org/news-sitemap.xml' in b
                else:
                    okay = b'<html' in b.lower() and (relative != '/news/about.html' or b'Editorial' in b)
                if 'noindex' in (r.headers.get('X-Robots-Tag') or '').lower():
                    okay = False
                    print(f'  WARN X-Robots-Tag noindex returned for {url}')
                print(f'  {"PASS" if okay else "WARN"} HTTP {r.status} {url} [{mime}]')
                if not okay:
                    print('    Unexpected public response: verify Nginx static file routing and any CDN cache')
        except Exception as e:
            print(f'  WARN could not verify {url}: {e}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--install', action='store_true')
    ap.add_argument('--refresh', action='store_true')
    ap.add_argument('--audit', action='store_true')
    args = ap.parse_args()
    if not ROOT.is_dir() or not NEWS.is_dir() or not INDEX.is_file():
        raise RuntimeError(f'Expected existing site/newsroom not found at {ROOT}')
    now = dt.datetime.now(dt.timezone.utc)
    records, issues, article_count = inspect_articles(now, verbose=(not args.refresh))
    if not article_count:
        raise RuntimeError('No recognizable existing articles; inspect site implementation before changing anything')
    if args.install and not records and issues:
        raise RuntimeError('No eligible articles and metadata warnings are present; review article canonical/date fields before installation')
    if args.refresh:
        if SITEMAP.exists() and MANAGED.encode() not in SITEMAP.read_bytes():
            raise RuntimeError('Unexpected existing news-sitemap.xml, refusing to overwrite it')
        changed = atomic_write(SITEMAP, sitemap_bytes(records))
        if changed:
            print(f'News sitemap refreshed: {len(records)} URLs')
        return
    if not args.install:
        print('Dry inspection complete. Run with --install to deploy.')
        return
    print('\nPREFLIGHT: validating existing files (no website changes yet)')
    existing_about = ABOUT.read_text(encoding='utf-8') if ABOUT.exists() else ''
    if existing_about and MANAGED not in existing_about:
        raise RuntimeError(f'Existing {ABOUT} is not managed by this installer; refusing to overwrite')
    if SITEMAP.exists() and MANAGED.encode() not in SITEMAP.read_bytes():
        raise RuntimeError(f'Existing {SITEMAP} is not a Google News sitemap; refusing to overwrite')
    if CRON.exists() and MANAGED not in CRON.read_text(encoding='utf-8'):
        raise RuntimeError(f'Existing {CRON} is not managed by this installer; refusing to overwrite')
    old_index = INDEX.read_text(encoding='utf-8')
    new_index = footer_with_about(old_index)
    old_robots = ROBOTS.read_text(encoding='utf-8') if ROBOTS.exists() else ''
    if re.search(r'(?im)^\s*disallow\s*:\s*/news(?:\s|/|$)', old_robots):
        raise RuntimeError('robots.txt disallows /news; fix the intentional rule manually before deployment')
    sitemap_line = f'Sitemap: {BASE}/news-sitemap.xml'
    new_robots = old_robots
    if not re.search(r'(?im)^\s*sitemap:\s*https?://(?:www\.)?digibytewallet\.org/news-sitemap\.xml\s*$', old_robots):
        new_robots = (old_robots.rstrip() + '\n\n' if old_robots.strip() else '') + sitemap_line + '\n'
    if not old_robots.strip():
        regular = ROOT / 'sitemap.xml'
        if regular.exists():
            new_robots += f'Sitemap: {BASE}/sitemap.xml\n'
    # Preserve edits made to our previously installed About page on later reruns.
    new_about = existing_about.encode('utf-8') if existing_about else about_html()
    sitemap = sitemap_bytes(records)
    ET.fromstring(sitemap)
    cron = f'# {MANAGED} | Refresh Google News sitemap every 15 minutes\n*/15 * * * * root /usr/bin/python3 /usr/local/sbin/digibyte-news-readiness.py --refresh 2>&1 | /usr/bin/logger -t digibyte-news-sitemap\n'
    # Validate the generated page as HTML before any writes.
    if not (b'<html' in new_about and b'</html>' in new_about):
        raise RuntimeError('About page validation failed')
    print('PASS preflight. Applying small, atomic changes only:')
    for path, data, mode in (
        (ABOUT, new_about, 0o644),
        (SITEMAP, sitemap, 0o644),
        (INDEX, new_index.encode('utf-8'), 0o644),
        (ROBOTS, new_robots.encode('utf-8'), 0o644),
        (CRON, cron.encode('utf-8'), 0o644),
    ):
        updated = atomic_write(path, data, mode)
        print(f'  {"UPDATED" if updated else "UNCHANGED"} {path}')
    print('\nVALIDATION:')
    root = ET.parse(SITEMAP).getroot()
    ns = {'s': SM_NS, 'news': NEWS_NS}
    urls = root.findall('s:url', ns)
    for entry in urls:
        assert entry.findtext('s:loc', namespaces=ns)
        assert entry.findtext('news:news/news:publication/news:name', namespaces=ns) == 'DigiByte Wallet'
        assert entry.findtext('news:news/news:publication/news:language', namespaces=ns) == 'en'
        assert entry.findtext('news:news/news:publication_date', namespaces=ns)
        assert entry.findtext('news:news/news:title', namespaces=ns)
    assert len(urls) == len(records)
    assert 'href="/news/about.html"' in INDEX.read_text(encoding='utf-8')
    assert sitemap_line in ROBOTS.read_text(encoding='utf-8')
    assert MANAGED in CRON.read_text(encoding='utf-8')
    print(f'  PASS generated Google News XML ({len(urls)} eligible articles)')
    print('  PASS About page, newsroom link, robots.txt discovery, and 15-minute cron schedule')
    index_meta = read_metadata(INDEX)
    feed_audit(index_meta)
    audit_regular_sitemap()
    if os.environ.get('DGB_NEWS_NO_HTTP') != '1':
        check_public()
    print('\nGoogle Search Console → Sitemaps → submit: news-sitemap.xml')
    print(f'Canonical full URL: {BASE}/news-sitemap.xml')
    print('No Google News manual publisher application is required; placement is not guaranteed.')
    print('NOTE: Only original publication timestamps are used. Date-only values are interpreted at 00:00 UTC for the 48h filter.')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f'ERROR: {e}', file=sys.stderr)
        sys.exit(1)
