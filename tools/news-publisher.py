#!/usr/bin/env python3
"""DigiByte Wallet: publish a Markdown newsroom article through GitHub, then deploy only public outputs.

Safeguards: source-tree clean check, allowlisted paths, live baseline comparison,
no modifying existing article URLs, no interaction with faucet or unreviewed apps.
"""
from __future__ import annotations

import argparse
import datetime as dt
import email.utils
import html
import json
import mimetypes
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from urllib.parse import quote

ROOT = Path(os.environ.get('DGB_NEWS_REPO', '/root/digibytewallet-org-github')).resolve()
LIVE = Path(os.environ.get('DGB_NEWS_LIVE', '/var/www/digibytewallet-org')).resolve()
BASE = 'https://www.digibytewallet.org'
SITEMAP_NS = 'http://www.sitemaps.org/schemas/sitemap/0.9'
ET.register_namespace('', SITEMAP_NS)
MARKER = 'DGB_NEWS_PUBLISHER_V1'
DEFAULT_IMAGE = '/news/assets/newsroom-social-v33.jpg'
ALLOWED_FIELDS = {'title','slug','summary','category','image','image_square','image_4x3','image_alt','tags','published'}


def fail(message):
    raise RuntimeError(message)


def git(*args, capture=True):
    r = subprocess.run(['git', '-C', str(ROOT), *args], text=True,
                       stdout=subprocess.PIPE if capture else None,
                       stderr=subprocess.PIPE if capture else None)
    if r.returncode != 0:
        fail('git ' + ' '.join(args) + ' failed: ' + (r.stderr or '').strip())
    return (r.stdout or '').strip()


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


def verify_repo():
    if not (ROOT / '.git').exists():
        fail(f'Git source clone not found: {ROOT}')
    remote = git('remote', 'get-url', 'origin')
    if not re.search(r'(?:github\.com[:/])sumcoinlabs/digibytewallet-org(?:\.git)?$', remote):
        fail(f'Unexpected GitHub origin: {remote}')
    if git('branch', '--show-current') != 'main':
        fail('Source clone must be on branch main')
    if git('status', '--porcelain', '--untracked-files=all'):
        fail('Git source clone has changes. Review git status before publishing.')
    git('fetch', '--quiet', 'origin', 'main')
    if git('rev-parse', 'HEAD') != git('rev-parse', 'origin/main'):
        fail('Local source is not aligned with origin/main. Review and update it first.')
    for p in ('news/index.html', 'news/feed.xml', 'news/feed.json', 'sitemap.xml',
              'news/digicoinlib-0-0-3-release.html', 'tools/digibyte-news-readiness.py'):
        if not (ROOT / p).is_file():
            fail(f'Expected existing source missing: {p}')
    if not LIVE.is_dir():
        fail('Live website directory missing')


def parse_manuscript(raw):
    raw = raw.replace('\r\n', '\n').lstrip('\ufeff')
    if not raw.startswith('---\n') or '\n---\n' not in raw[4:]:
        fail('Markdown must start with --- metadata --- followed by the article body')
    front, body = raw[4:].split('\n---\n', 1)
    meta = {}
    for line in front.splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        if ':' not in line:
            fail(f'Invalid metadata line: {line[:70]!r}')
        k, v = line.split(':', 1)
        k = k.strip().lower()
        if k in meta or k not in ALLOWED_FIELDS:
            fail(f'Duplicate/unknown metadata field: {k}')
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in ('"', "'"):
            v = v[1:-1]
        meta[k] = v
    for required in ('title','summary','slug'):
        if not meta.get(required):
            fail(f'Missing metadata: {required}')
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', meta['slug']) or len(meta['slug']) > 85:
        fail('Slug must use lowercase letters, numbers and hyphens (max 85 chars)')
    if len(meta['title']) < 10 or len(meta['title']) > 155:
        fail('Title should be 10-155 characters')
    if meta['title'].upper().startswith('REPLACE ') or meta['slug'].startswith('replace-') or meta['summary'].lower().startswith('replace this'):
        fail('This still appears to be the blank article template; refusing to publish')
    if len(meta['summary']) < 45 or len(meta['summary']) > 360:
        fail('Summary should be 45-360 characters')
    if not body.strip() or len(re.findall(r'\w+', body)) < 60:
        fail('Article body should contain at least 60 words')
    if re.search(r'-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----|AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9_]{25,}|\b(?:api[_-]?key|secret[_-]?key|access[_-]?token)\s*[:=]\s*[\x22\x27]?[A-Za-z0-9/+=_-]{18,}', raw, re.I):
        fail('Possible private key or token in article manuscript; refusing to publish')
    image = meta.get('image', DEFAULT_IMAGE)
    if not re.fullmatch(r'/news/assets/[A-Za-z0-9][A-Za-z0-9._-]*\.(?:jpg|jpeg|png|webp)', image):
        fail('Image must be an existing JPG, PNG or WebP under /news/assets/')
    image_repo = ROOT / image.lstrip('/')
    image_live = LIVE / image.lstrip('/')
    if not image_repo.is_file() or not image_live.is_file():
        fail(f'Image must already exist both in GitHub source and on the live website: {image}')
    if image_repo.read_bytes() != image_live.read_bytes():
        fail('Image differs between source and production; review before publishing')
    meta['image'] = image
    for variant in ('image_square', 'image_4x3'):
        if variant not in meta:
            continue
        value = meta[variant]
        if not re.fullmatch(r'/news/assets/[A-Za-z0-9][A-Za-z0-9._-]*\.(?:jpg|jpeg|png|webp)', value):
            fail('Invalid alternate image path: ' + variant)
        source = ROOT / value.lstrip('/')
        public = LIVE / value.lstrip('/')
        if not source.is_file() or not public.is_file() or source.read_bytes() != public.read_bytes():
            fail('Alternate image must exist and match on GitHub source and live site: ' + variant)
    meta['image_alt'] = meta.get('image_alt') or meta['title']
    meta['category'] = meta.get('category') or 'Development update'
    if any(len(str(meta[k])) > 180 for k in ('image_alt','category')):
        fail('Image alt text or category too long')
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    original_date = meta.get('published', 'auto')
    if original_date == 'auto':
        date = now
    else:
        try:
            date = dt.datetime.fromisoformat(original_date.replace('Z','+00:00'))
        except ValueError:
            fail('published must be auto or timezone-aware ISO 8601 date-time')
        if not date.tzinfo or date.utcoffset() is None:
            fail('published must include a time zone, e.g. 2026-11-05T18:00:00Z')
        date = date.astimezone(dt.timezone.utc).replace(microsecond=0)
        if date > now + dt.timedelta(minutes=1):
            fail('Publication date cannot be in the future')
    meta['published'] = date.isoformat(timespec='seconds').replace('+00:00', 'Z')
    meta['published_date'] = date.strftime('%Y-%m-%d')
    meta['published_human'] = f'{date.strftime("%B")} {date.day}, {date.year}'
    meta['tags_list'] = [x.strip() for x in meta.get('tags', 'DigiByte, DigiByte Wallet').split(',') if x.strip()][:8]
    return meta, body.strip()


INLINE_RE = re.compile(r'\[([^\]]+)\]\(([^\s)]+)\)|\*\*([^*\n]+)\*\*|`([^`\n]+)`')


def inline(text):
    out, pos = [], 0
    for match in INLINE_RE.finditer(text):
        out.append(html.escape(text[pos:match.start()], quote=True))
        if match.group(1) is not None:
            label, url = match.group(1), match.group(2)
            if not (url.startswith('https://') or url.startswith('http://') or (url.startswith('/') and not url.startswith('//'))):
                fail(f'Unsupported link URL: {url[:100]}')
            out.append(f'<a href="{html.escape(url, quote=True)}">{html.escape(label)}</a>')
        elif match.group(3) is not None:
            out.append('<strong>' + html.escape(match.group(3)) + '</strong>')
        else:
            out.append('<code>' + html.escape(match.group(4)) + '</code>')
        pos = match.end()
    out.append(html.escape(text[pos:], quote=True))
    return ''.join(out)


def markdown(body):
    pieces, para, list_items, list_type = [], [], [], ''
    def flush_para():
        if para:
            pieces.append('<p>' + inline(' '.join(para)) + '</p>')
            para.clear()
    def flush_list():
        nonlocal list_type
        if list_items:
            pieces.append(f'<{list_type}>' + ''.join(f'<li>{inline(v)}</li>' for v in list_items) + f'</{list_type}>')
            list_items.clear()
            list_type = ''
    for raw in body.splitlines():
        line = raw.strip()
        if not line:
            flush_para(); flush_list(); continue
        m = re.match(r'^(#{2,3})\s+(.+)$', line)
        if m:
            flush_para(); flush_list()
            h = len(m.group(1))
            pieces.append(f'<h{h}>{inline(m.group(2))}</h{h}>')
            continue
        m = re.match(r'^(?:[-*]\s+|\d+\.\s+)(.+)$', line)
        if m:
            flush_para()
            typ = 'ul' if re.match(r'^[-*]\s+', line) else 'ol'
            if list_type and list_type != typ:
                flush_list()
            list_type = typ
            list_items.append(m.group(1))
            continue
        flush_list()
        if line.startswith('# ') or line.startswith('```') or line.startswith('<script'):
            fail('Unsupported Markdown construct. Use ##/### headings and plain Markdown only.')
        para.append(line)
    flush_para(); flush_list()
    return '\n'.join(pieces)


def html_tags(meta, markup):
    title = meta['title']
    canonical = f'{BASE}/news/{meta["slug"]}.html'
    full_image = BASE + meta['image']
    graph = {
        '@context': 'https://schema.org',
        '@graph': [
            {'@type': 'Organization', '@id': BASE + '/#organization',
             'name': 'DigiByte Wallet', 'url': BASE + '/',
             'logo': {'@type': 'ImageObject', 'url': BASE + '/images/digibyte-dgb-logo.png'}},
            {'@type': 'WebSite', '@id': BASE + '/#website', 'url': BASE + '/',
             'name': 'DigiByte Wallet', 'publisher': {'@id': BASE + '/#organization'}},
            {'@type': 'BreadcrumbList', 'itemListElement': [
                {'@type': 'ListItem', 'position': 1, 'name': 'Home', 'item': BASE + '/'},
                {'@type': 'ListItem', 'position': 2, 'name': 'News', 'item': BASE + '/news/'},
                {'@type': 'ListItem', 'position': 3, 'name': title, 'item': canonical}]},
            {'@type': 'NewsArticle', '@id': canonical + '#article',
             'mainEntityOfPage': {'@type': 'WebPage', '@id': canonical},
             'headline': title, 'description': meta['summary'],
             'datePublished': meta['published'], 'dateModified': meta['published'],
             'image': [BASE + meta[k] for k in ('image_square', 'image_4x3', 'image') if meta.get(k)], 'inLanguage': 'en',
             'author': {'@type': 'Organization', 'name': 'DigiByte Wallet',
                        'url': BASE + '/news/about.html'},
             'publisher': {'@id': BASE + '/#organization'}}]
    }
    def E(x): return html.escape(x, quote=True)
    template = read('news/digicoinlib-0-0-3-release.html')
    if not ('<body class="dw-news">' in template and '<main id="main">' in template and '</main>' in template):
        fail('Article layout template no longer matches expected site')
    old_head = template.split('<body class="dw-news">', 1)[0]
    account_m = re.search(r'ca-pub-\d{10,}', old_head)
    if not account_m:
        fail('Existing Google AdSense identity could not be verified')
    account = account_m.group(0)
    ads_m = re.search(r'<script\b[^>]*src="https://pagead2\.googlesyndication\.com/pagead/js/adsbygoogle\.js\?client=ca-pub-\d+"[^>]*></script>', old_head)
    if not ads_m or account not in ads_m.group(0):
        fail('Existing AdSense loading script could not be verified')
    body_before_main = template.split('<body class="dw-news">', 1)[1].split('<main id="main">', 1)[0]
    after_main = template.split('</main>', 1)[1]
    side_m = re.search(r'<aside aria-label="Related information" class="dw-sidebar">(.*?)</aside>', template, re.S)
    if not side_m:
        fail('Existing related-information sidebar could not be reused')
    sidebar = '<aside aria-label="Related information" class="dw-sidebar">' + side_m.group(1) + '</aside>'
    news_path = f'/news/{meta["slug"]}.html'
    heading = E(title)
    category = E(meta['category'])
    summary = E(meta['summary'])
    image_url = E(meta['image'])
    image_alt = E(meta['image_alt'])
    share_url = E('https://twitter.com/intent/tweet?text=' + quote(title) + '&url=' + quote(canonical))
    graph_json = json.dumps(graph, ensure_ascii=False, separators=(',', ':'))
    graph_json = graph_json.replace('</', '<' + chr(92) + '/')
    header = f'''<!doctype html>\n<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{heading} | DigiByte Wallet News</title>
<meta name="description" content="{summary}"><meta name="author" content="DigiByte Wallet">
<meta name="robots" content="index,follow,max-image-preview:large"><meta name="google-adsense-account" content="{account}">
<link rel="canonical" href="{E(canonical)}"><link rel="icon" type="image/x-icon" href="/favicon.ico">
<link rel="alternate" type="application/rss+xml" title="DigiByte Wallet News RSS" href="{BASE}/news/feed.xml">
<link rel="alternate" type="application/feed+json" title="DigiByte Wallet News JSON Feed" href="{BASE}/news/feed.json">
<meta property="og:type" content="article"><meta property="og:site_name" content="DigiByte Wallet">
<meta property="og:url" content="{E(canonical)}"><meta property="og:title" content="{heading}"><meta property="og:description" content="{summary}">
<meta property="og:image" content="{E(full_image)}"><meta property="og:image:alt" content="{image_alt}">
<meta property="article:published_time" content="{meta['published']}"><meta property="article:modified_time" content="{meta['published']}">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{heading}">
<meta name="twitter:description" content="{summary}"><meta name="twitter:image" content="{E(full_image)}">
<link rel="stylesheet" href="/css/base.css"><link rel="stylesheet" href="/css/main.css"><link rel="stylesheet" href="/news/assets/news.css">
<script type="application/ld+json">{graph_json}</script>
<script defer src="/news/assets/news.js"></script>
{ads_m.group(0)}
</head>\n<body class="dw-news">{body_before_main}'''
    feature = f'''<figure class="dw-feature-figure"><img src="{image_url}" alt="{image_alt}" width="1200" height="630" loading="eager" decoding="async"><figcaption>{heading}</figcaption></figure>'''
    body_section = f'''<main id="main"><section class="dw-article-wrap"><div class="dw-shell dw-article-grid"><article class="dw-story">
<nav aria-label="Breadcrumb" class="dw-breadcrumb"><a href="/">Home</a> / <a href="/news/">News</a> / {heading}</nav>
<div class="dw-section-label">Published · {category}</div><h1>{heading}</h1>
<p class="dw-story-meta"><time datetime="{meta['published']}">{meta['published_human']}</time> · DigiByte Wallet newsroom</p>
<p class="dw-dek">{summary}</p><div class="dw-ad-target" data-ad-zone="inArticle"></div>
{feature}\n{markup}\n<p class="dw-end"><strong>About DigiByte Wallet.</strong> For official updates, visit the <a href="/news/">DigiByte Wallet newsroom</a>. Send questions or corrections to <a href="/news/about.html">our editorial contact page</a>.</p>
<div class="dw-share"><a href="{share_url}" rel="noopener noreferrer" target="_blank">Share on X</a><button data-copy-link="" type="button">Copy link</button></div></article>{sidebar}</div></section></main>'''
    result = header + body_section + after_main
    if not result.endswith('</html>') or result.count('<main id="main">') != 1:
        fail('Generated article HTML did not pass basic layout validation')
    return result + '\n'


def card(meta):
    def E(x): return html.escape(x, quote=True)
    title, url = E(meta['title']), f'/news/{meta["slug"]}.html'
    category = E(meta['category'])
    preview_class = ' dw-pill-soon' if 'preview' in meta['category'].lower() or 'coming' in meta['category'].lower() else ''
    return f'''<!-- {MARKER} {meta['slug']} -->
<article class="dw-card"><div class="dw-card-visual has-preview"><img alt="{E(meta['image_alt'])}" class="dw-card-preview" decoding="async" height="630" loading="lazy" src="{E(meta['image'])}" width="1200"></div>
<div class="dw-card-body"><div><time class="dw-card-date" datetime="{meta['published']}">{meta['published_human']}</time> · <span class="dw-pill{preview_class}">{category}</span></div>
<h3><a href="{url}">{title}</a></h3><p>{E(meta['summary'])}</p>
<div class="dw-card-bottom"><a href="{url}">Read the story →</a></div></div></article>'''


def update_index(meta):
    src = read('news/index.html')
    marker = '<div class="dw-cards">'
    if src.count(marker) != 1 or f'{MARKER} {meta["slug"]}' in src:
        fail('News index marker missing/duplicated; not overwriting layout')
    src = src.replace(marker, marker + card(meta), 1)
    # Keep the established design, but make its landing-page copy evergreen.
    src = src.replace('Two important updates, with a clear distinction between the developer library that has shipped and the wallet app version being prepared.',
                      'Official wallet announcements, developer releases and project updates, with release status clearly identified.')
    src = re.sub(r'(<div class="dw-hero-links"><a class="dw-btn dw-btn-primary" href=")[^"]+("[^>]*>)[^<]+(</a>)',
                 lambda m: m.group(1) + f'/news/{meta["slug"]}.html' + m.group(2) + 'Read the latest news' + m.group(3), src, count=1)
    pattern = re.compile(r'(<script type="application/ld\+json">)(.*?)(</script>)', re.S)
    match = pattern.search(src)
    if not match:
        fail('Newsroom structured data not found')
    data = json.loads(match.group(2))
    lists = [x for x in data.get('@graph', []) if x.get('@type') == 'ItemList']
    if len(lists) != 1:
        fail('Expected single newsroom ItemList structured data')
    items = lists[0].get('itemListElement', [])
    url = BASE + '/news/' + meta['slug'] + '.html'
    if any(i.get('url') == url for i in items):
        fail('New URL already present in newsroom structured data')
    lists[0]['itemListElement'] = [
        {'@type':'ListItem','position':1,'name':meta['title'],'url':url},
        *[dict(i, position=j+2) for j,i in enumerate(items)]
    ]
    src = src[:match.start(2)] + json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + src[match.end(2):]
    return src


def update_feed_json(meta):
    obj = json.loads(read('news/feed.json'))
    items = obj.get('items')
    if not isinstance(items, list):
        fail('JSON feed items missing')
    url = BASE + '/news/' + meta['slug'] + '.html'
    if any(v.get('id') == url or v.get('url') == url for v in items):
        fail('Article already in JSON feed')
    obj['items'] = [{
        'id':url,'url':url,'title':meta['title'],'summary':meta['summary'],
        'date_published':meta['published'],'tags':meta['tags_list'],
        'image':BASE + meta['image']
    }, *items]
    return json.dumps(obj, indent=2, ensure_ascii=False) + '\n'


def update_feed_xml(meta):
    root = ET.fromstring(read('news/feed.xml'))
    channel = root.find('channel')
    if root.tag != 'rss' or channel is None:
        fail('Unexpected existing RSS feed format')
    url = BASE + '/news/' + meta['slug'] + '.html'
    if any(v.findtext('link') == url for v in channel.findall('item')):
        fail('Article already in RSS feed')
    item = ET.Element('item')
    for key,val in (('title',meta['title']),('link',url),('guid',url),
                    ('description',meta['summary'])):
        ET.SubElement(item,key).text = val
    item.find('guid').set('isPermaLink', 'true')
    published = dt.datetime.fromisoformat(meta['published'].replace('Z','+00:00'))
    ET.SubElement(item,'pubDate').text = email.utils.format_datetime(published, usegmt=True)
    img = ROOT / meta['image'].lstrip('/')
    ET.SubElement(item,'enclosure',{'url':BASE + meta['image'],
             'length':str(img.stat().st_size),
             'type':mimetypes.guess_type(str(img))[0] or 'image/jpeg'})
    first_item = next((i for i,e in enumerate(channel) if e.tag == 'item'), len(channel))
    channel.insert(first_item, item)
    return ET.tostring(root, encoding='unicode', xml_declaration=True) + '\n'


def update_sitemap(meta):
    root = ET.fromstring(read('sitemap.xml'))
    tagurl = f'{{{SITEMAP_NS}}}url'
    loc = f'{{{SITEMAP_NS}}}loc'
    last = f'{{{SITEMAP_NS}}}lastmod'
    if root.tag != f'{{{SITEMAP_NS}}}urlset':
        fail('Unexpected main sitemap root')
    url = BASE + '/news/' + meta['slug'] + '.html'
    found_home = False
    for node in root.findall(tagurl):
        val = node.findtext(loc)
        if val == url:
            fail('New URL already exists in main sitemap')
        if val == BASE + '/news/':
            found_home = True
            ele = node.find(last)
            if ele is None:
                ele = ET.SubElement(node, last)
            ele.text = meta['published_date']
    if not found_home:
        fail('Newsroom URL missing from existing main sitemap')
    e = ET.SubElement(root, tagurl)
    ET.SubElement(e, loc).text = url
    ET.SubElement(e, last).text = meta['published_date']
    return ET.tostring(root, encoding='unicode', xml_declaration=True) + '\n'


def atomic_bytes(dest, data):
    dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.is_symlink():
        fail(f'Refusing symlink as deployment destination: {dest}')
    fd, tmp = tempfile.mkstemp(prefix='.'+dest.name+'.', suffix='.pending', dir=dest.parent)
    try:
        with os.fdopen(fd,'wb') as f:
            f.write(data)
            f.flush(); os.fsync(f.fileno())
        os.chmod(tmp, 0o644)
        if dest.exists():
            st = dest.stat()
            os.chown(tmp, st.st_uid, st.st_gid)
        os.replace(tmp, dest)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def git_old(path, rev='HEAD'):
    r = subprocess.run(['git','-C',str(ROOT),'show',f'{rev}:{path}'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    return r.stdout if r.returncode == 0 else None


def live_destination(relative):
    dst = LIVE / relative
    if dst.is_symlink() or not str(dst.resolve()).startswith(str(LIVE) + '/'):
        fail(f'Deployment destination unsafe: {dst}')
    return dst


def deployment_preflight(paths, old_revision='HEAD'):
    for p in paths:
        src = ROOT / p
        dst = live_destination(p)
        old = git_old(p, old_revision)
        if old is None:
            if dst.exists():
                fail(f'New published URL already exists on production: {p}')
        elif not dst.is_file() or dst.read_bytes() not in (old, src.read_bytes()):
            fail(f'Production differs from Git baseline: {p}; stopping before publish')


def generator_refresh(source_root, installed=False):
    script = (Path('/usr/local/sbin/digibyte-news-readiness.py') if installed
              else ROOT / 'tools/digibyte-news-readiness.py')
    environment = os.environ.copy()
    environment['DGB_NEWS_ROOT'] = str(source_root)
    r = subprocess.run(['python3',str(script),'--refresh'],capture_output=True,text=True,env=environment)
    if r.returncode:
        fail('Google News sitemap generator failed: '+(r.stdout+'\n'+r.stderr)[-2000:])


def publish(raw):
    verify_repo()
    meta, body = parse_manuscript(raw)
    for image_key in ('image', 'image_square', 'image_4x3'):
        if meta.get(image_key):
            git('ls-files', '--error-unmatch', '--', meta[image_key].lstrip('/'))
    slug = meta['slug']
    page_path = f'news/{slug}.html'
    source_path = f'news/content/{slug}.md'
    if (ROOT/page_path).exists() or (ROOT/source_path).exists() or (LIVE/page_path).exists():
        fail('An article already uses that slug. Existing published URLs will never be overwritten.')
    markup = markdown(body)
    page = html_tags(meta, markup)
    changes = {
        page_path:page,
        source_path: raw.rstrip() + '\n',
        'news/index.html':update_index(meta),
        'news/feed.xml':update_feed_xml(meta),
        'news/feed.json':update_feed_json(meta),
        'sitemap.xml':update_sitemap(meta)
    }
    # Store the exact first-publication time in the source manuscript, even when input said 'auto'.
    if re.search(r'^published\s*:', changes[source_path], re.M):
        changes[source_path] = re.sub(r'^published\s*:.*$',f'published: {meta["published"]}', changes[source_path], count=1,flags=re.M)
    else:
        changes[source_path] = changes[source_path].replace('---\n', f'---\npublished: {meta["published"]}\n',1)
    # Preflight existing public files before touching the source clone or GitHub.
    public_files = ['news/index.html','news/feed.xml','news/feed.json','sitemap.xml',page_path]
    for p in public_files:
        old = git_old(p)
        dst = live_destination(p)
        if old is None:
            if dst.exists(): fail(f'Already exists on production: {p}')
        elif not dst.is_file() or dst.read_bytes() != old:
            fail(f'Unexpected production edit since GitHub baseline: {p}')
    for p, content in changes.items():
        dest = ROOT / p
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text(content,encoding='utf-8')
    generator_refresh(ROOT)
    changed_paths = [*changes, 'news-sitemap.xml']
    # Check regenerated artifacts before any push/deploy.
    ET.parse(ROOT/'news/feed.xml')
    ET.parse(ROOT/'sitemap.xml')
    news_xml = ET.parse(ROOT/'news-sitemap.xml')
    published_at = dt.datetime.fromisoformat(meta['published'].replace('Z', '+00:00'))
    if dt.datetime.now(dt.timezone.utc) - published_at <= dt.timedelta(hours=48):
        urls = {e.text for e in news_xml.findall(f'.//{{{SITEMAP_NS}}}loc')}
        if BASE + '/' + page_path not in urls:
            fail('New article missing from generated Google News sitemap; stopping before push')
    if len(json.loads(read('news/feed.json'))['items']) < 1:
        fail('Generated JSON feed has no entries')
    if not (ROOT/page_path).is_file() or f'/{page_path}' not in read('news/index.html'):
        fail('News homepage/article validation failed')
    # Explicit staging. No recursive website add; never anything from faucet/.
    git('add','--',*changed_paths)
    staged = git('diff','--cached','--name-only').splitlines()
    if sorted(staged) != sorted(changed_paths):
        fail('Unexpected staged files; stopping before commit: ' + repr(staged))
    git('diff','--cached','--check')
    print(f'Prepared: {meta["title"]}')
    print(f'Published: {meta["published"]} | Canonical: {BASE}/{page_path}')
    print('Files: ' + ', '.join(changed_paths))
    # One commit, then push, then only public output files are deployed.
    git('commit','-m','Publish news: '+meta['title'][:75],capture=False)
    commit = git('rev-parse','--short','HEAD')
    git('push','origin','main',capture=False)
    print('GitHub commit pushed: ' + commit)
    deployment_preflight(public_files, old_revision='HEAD^')
    for p in (page_path,'news/feed.xml','news/feed.json','news/index.html','sitemap.xml'):
        atomic_bytes(live_destination(p),(ROOT/p).read_bytes())
    generator_refresh(LIVE, installed=True)
    print('Production updated; sitemap refresh successful.')
    print('Article: ' + BASE + '/' + page_path)
    print('RSS: ' + BASE + '/news/feed.xml')
    print('News sitemap: ' + BASE + '/news-sitemap.xml')
    print('Main sitemap: ' + BASE + '/sitemap.xml')
    print('Excluded directories, especially faucet/, were not read or changed.')


def check():
    verify_repo()
    for p in ('news/index.html','news/feed.xml','news/feed.json','sitemap.xml'):
        old = git_old(p)
        if not old or not (LIVE/p).is_file():
            fail('Missing existing production or source: '+p)
        if old != (LIVE/p).read_bytes():
            fail('Production/source mismatch in '+p)
    ET.parse(ROOT/'news/feed.xml')
    ET.parse(ROOT/'sitemap.xml')
    json.loads(read('news/feed.json'))
    print('PASS: GitHub aligned, feeds and main sitemap parse, production files match.')
    print('Ready for a Markdown article on stdin: --publish-stdin')


def main():
    ap=argparse.ArgumentParser(description='Publish DigiByte Wallet news from Markdown; no web-facing admin panel')
    group=ap.add_mutually_exclusive_group(required=True)
    group.add_argument('--check',action='store_true')
    group.add_argument('--publish-stdin',action='store_true')
    args=ap.parse_args()
    try:
        if args.check:
            check()
        else:
            if sys.stdin.isatty():
                fail('Pipe a Markdown article into stdin; no interactive editor is started')
            publish(sys.stdin.read())
    except Exception as exc:
        print('ERROR: '+str(exc),file=sys.stderr)
        return 1
    return 0

if __name__=='__main__':
    sys.exit(main())
