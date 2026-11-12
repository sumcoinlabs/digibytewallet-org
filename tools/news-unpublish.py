#!/usr/bin/env python3
"""Password-protected editor helper to unpublish a live story from the DGB News site.

Removes an article from the index, JSON/RSS feeds and main/News sitemaps, deletes
its public page to return HTTP 404, and archives original bytes privately. Its
Git history and any external caches remain outside this tool's control.
"""
from __future__ import annotations
import argparse
import datetime as dt
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import sys
import xml.etree.ElementTree as ET

SLUG = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
BASE = 'https://www.digibytewallet.org/news/'
NS = 'http://www.sitemaps.org/schemas/sitemap/0.9'


def load_publisher():
    p = Path(__file__).resolve().parent / 'news-publisher.py'
    spec = importlib.util.spec_from_file_location('dgb_publication_base', str(p))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def prepare(slug, mod):
    if not isinstance(slug, str) or len(slug)>85 or not SLUG.fullmatch(slug):
        raise ValueError('Invalid article slug')
    mod.verify_repo()
    url = BASE + slug + '.html'
    page = 'news/' + slug + '.html'
    manuscript = 'news/content/' + slug + '.md'
    public = ['news/index.html','news/feed.json','news/feed.xml','sitemap.xml',page]
    for path in public:
        old=mod.git_old(path)
        dst=mod.live_destination(path)
        if old is None or not dst.is_file() or dst.read_bytes()!=old:
            raise RuntimeError('Production/source mismatch; refusing unpublish: '+path)
    if not (mod.ROOT / page).is_file():
        raise RuntimeError('Published article HTML does not exist')

    feeds = json.loads(mod.read('news/feed.json'))
    old_items=feeds.get('items')
    if not isinstance(old_items,list):raise RuntimeError('Unexpected JSON feed')
    found=[x for x in old_items if x.get('url')==url]
    if len(found)!=1:raise RuntimeError('Expected exactly one matching JSON feed item')
    feeds['items']=[x for x in old_items if x.get('url')!=url]

    xml=ET.fromstring(mod.read('news/feed.xml'))
    channel=xml.find('channel')
    if channel is None or xml.tag!='rss':raise RuntimeError('Unexpected RSS document')
    rss=[e for e in channel.findall('item') if e.findtext('link')==url]
    if len(rss)!=1:raise RuntimeError('Expected exactly one matching RSS item')
    channel.remove(rss[0])

    sitemap=ET.fromstring(mod.read('sitemap.xml'))
    sm=[e for e in sitemap.findall('{%s}url'%NS) if e.findtext('{%s}loc'%NS)==url]
    if len(sm)!=1:raise RuntimeError('Expected exactly one sitemap URL')
    sitemap.remove(sm[0])

    index=mod.read('news/index.html')
    cards=list(re.finditer(r'<article\b[^>]*class="[^"]*\bdw-card\b[^"]*"[^>]*>.*?</article>',index,re.S|re.I))
    target=[m for m in cards if ('href="/news/'+slug+'.html"') in m.group(0)]
    if len(target)!=1:raise RuntimeError('Expected exactly one article card')
    m=target[0]
    index=index[:m.start()]+index[m.end():]
    # Automatically published cards carry this optional marker. Older cards do not.
    index=index.replace('<!-- DGB_NEWS_PUBLISHER_V1 '+slug+' -->\n','')
    index=index.replace('<!-- DGB_NEWS_PUBLISHER_V1 '+slug+' -->','')

    ldpat=re.compile(r'(<script type="application/ld\+json">)(.*?)(</script>)',re.S)
    match=ldpat.search(index)
    if not match:raise RuntimeError('Newsroom JSON-LD missing')
    ld=json.loads(match.group(2))
    lists=[x for x in ld.get('@graph',[]) if x.get('@type')=='ItemList']
    if len(lists)!=1:raise RuntimeError('Newsroom list metadata missing')
    items=lists[0].get('itemListElement',[])
    if sum(x.get('url')==url for x in items)!=1:raise RuntimeError('Published card not in JSON-LD')
    lists[0]['itemListElement']=[dict(x,position=i+1) for i,x in enumerate(x for x in items if x.get('url')!=url)]
    index=index[:match.start(2)]+json.dumps(ld,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')+index[match.end(2):]
    # Avoid leaving the primary latest-story CTA pointed at a removed page.
    if ('href="/news/'+slug+'.html"') in index and feeds['items']:
        next_url=feeds['items'][0]['url']
        if not isinstance(next_url,str) or not next_url.startswith(BASE):raise RuntimeError('Invalid replacement target')
        index=re.sub(r'(<div class="dw-hero-links"><a class="dw-btn dw-btn-primary" href=")[^"]+("[^>]*>Read the latest news</a>)',
                     lambda m:m.group(1)+next_url[len('https://www.digibytewallet.org'):]+m.group(2),index,count=1)
    # A retired story may also have a secondary hero or related link. Remove
    # that stale navigation rather than leaving a visible link to a 404.
    stale_link=re.compile(r'<a\b[^>]*href="/news/'+re.escape(slug)+r'\.html"[^>]*>.*?</a>',re.S|re.I)
    index=stale_link.sub('',index)
    if 'href="/news/'+slug+'.html"' in index:
        raise RuntimeError('Old URL still appears on homepage; requires editorial review')

    new_files={
        'news/index.html':index,
        'news/feed.json':json.dumps(feeds,indent=2,ensure_ascii=False)+'\n',
        'news/feed.xml':ET.tostring(xml,encoding='unicode',xml_declaration=True)+'\n',
        'sitemap.xml':ET.tostring(sitemap,encoding='unicode',xml_declaration=True)+'\n'
    }
    return {'slug':slug,'url':url,'page':page,'manuscript':manuscript,'public':public,
            'files':new_files,'title':found[0].get('title','')}


def unpublish(slug):
    mod=load_publisher()
    plan=prepare(slug,mod)
    # Keep the original page and manuscript in a PRIVATE, non-served location.
    stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    private=Path('/root/.local/share/dgb-newsroom-editor/retracted')
    private.mkdir(parents=True,exist_ok=True,mode=0o700)
    os.chmod(str(private),0o700)
    folder=private/(stamp+'-'+slug)
    folder.mkdir(mode=0o700)
    for rel in (plan['page'],plan['manuscript']):
        src=mod.ROOT/rel
        if src.exists():
            dst=folder/src.name
            dst.write_bytes(src.read_bytes())
            os.chmod(str(dst),0o600)

    # No public edits until all constraints above pass.
    for rel,data in plan['files'].items():
        (mod.ROOT/rel).write_text(data,encoding='utf-8')
    (mod.ROOT/plan['page']).unlink()
    if (mod.ROOT/plan['manuscript']).exists():
        (mod.ROOT/plan['manuscript']).unlink()
    mod.generator_refresh(mod.ROOT)

    ET.parse(mod.ROOT/'news/feed.xml')
    ET.parse(mod.ROOT/'sitemap.xml')
    ET.parse(mod.ROOT/'news-sitemap.xml')
    json.loads((mod.ROOT/'news/feed.json').read_text())
    if plan['url'] in (mod.ROOT/'news/feed.xml').read_text() or plan['url'] in (mod.ROOT/'sitemap.xml').read_text():
        raise RuntimeError('Retracted URL still appears in metadata')
    tracked=[*plan['files'],plan['page'],'news-sitemap.xml']
    if (folder/(slug+'.md')).is_file():tracked.append(plan['manuscript'])
    mod.git('add','--',*tracked)
    staged=set(mod.git('diff','--cached','--name-only').splitlines())
    if not staged.issubset(set(tracked)) or not staged:
        raise RuntimeError('Unexpected staged files')
    mod.git('diff','--cached','--check')
    mod.git('commit','-m','Unpublish newsroom article: '+slug,capture=False)
    mod.git('push','origin','main',capture=False)
    revision=mod.git('rev-parse','--short','HEAD')
    for rel in plan['files']:
        mod.atomic_bytes(mod.live_destination(rel),(mod.ROOT/rel).read_bytes())
    # Once reference pages and discovery feeds are removed, the article goes 404.
    mod.live_destination(plan['page']).unlink()
    mod.generator_refresh(mod.LIVE,installed=True)
    log=private/'actions.jsonl'
    with log.open('a',encoding='utf-8') as out:
        out.write(json.dumps({'time':stamp,'slug':slug,'title':plan['title'],'action':'unpublish','commit':revision})+'\n')
    os.chmod(str(log),0o600)
    return {'ok':True,'slug':slug,'commit':revision,'archive':str(folder),
            'note':'Page removed (404), no longer in feeds/sitemaps; Git history and third-party caches are not erased.'}


def main():
    p=argparse.ArgumentParser(description='Retract a published DigiByte Wallet newsroom article')
    p.add_argument('--slug',required=True)
    p.add_argument('--check',action='store_true')
    args=p.parse_args()
    try:
        if args.check:
            x=prepare(args.slug,load_publisher())
            print(json.dumps({'ready':True,'title':x['title'],'url':x['url']}))
        else:print(json.dumps(unpublish(args.slug)))
    except Exception as exc:
        print('ERROR: '+str(exc)[:400],file=sys.stderr)
        return 1
    return 0

if __name__=='__main__':sys.exit(main())
