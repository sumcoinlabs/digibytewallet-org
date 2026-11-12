#!/usr/bin/env python3
"""Loopback-only DigiByte newsroom editor; requires SSH tunnel AND a password.

Private drafts and authentication never enter the public repository or webroot.
Python 3.8, Pillow 10.4 for image generation. Only invokes existing publisher.
"""
import base64
import datetime as dt
import getpass
import hashlib
import hmac
import html
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

try:
    from PIL import Image, ImageOps, UnidentifiedImageError
except ImportError:
    Image = ImageOps = None

HOME = Path('/root/.local/share/dgb-newsroom-editor')
ROOT = Path('/root/digibytewallet-org-github')
LIVE = Path('/var/www/digibytewallet-org')
PORT = 8769
AUTH = HOME / 'password.json'
DRAFTS = HOME / 'drafts'
IMAGES = HOME / 'images'
SESSION_FILE = HOME / 'sessions.sqlite3'
SLUG = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
S = {}
FAIL = []
LOCK = threading.RLock()
PUBLISH_LOCK = threading.Lock()
MAX_BODY = 12 * 1024 * 1024


def mkdir():
    for path in (HOME, DRAFTS, IMAGES):
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(str(path), 0o700)


def auth_revision():
    # A password change invalidates all surviving sessions, including saved ones.
    try:return hashlib.sha256(AUTH.read_bytes()).hexdigest()
    except OSError:return ''


def session_database():
    mkdir()
    with LOCK:
        with sqlite3.connect(str(SESSION_FILE),timeout=5) as conn:
            conn.execute('CREATE TABLE IF NOT EXISTS sessions (token_hash TEXT PRIMARY KEY,csrf TEXT NOT NULL,expires REAL NOT NULL,auth_revision TEXT NOT NULL)')
            conn.execute('DELETE FROM sessions WHERE expires < ?', (time.time(),))
            conn.commit()
    os.chmod(str(SESSION_FILE),0o600)


def remember_session(key,session):
    session_database()
    with sqlite3.connect(str(SESSION_FILE),timeout=5) as conn:
        conn.execute('INSERT OR REPLACE INTO sessions (token_hash,csrf,expires,auth_revision) VALUES (?,?,?,?)',
             (key,session['csrf'],session['expires'],session['auth_revision']))
        conn.commit()


def forget_session(key):
    with LOCK:S.pop(key,None)
    if SESSION_FILE.exists():
        with sqlite3.connect(str(SESSION_FILE),timeout=5) as conn:
            conn.execute('DELETE FROM sessions WHERE token_hash=?',(key,));conn.commit()


def stored_session(key):
    if not SESSION_FILE.exists():return None
    with sqlite3.connect(str(SESSION_FILE),timeout=5) as conn:
        row=conn.execute('SELECT csrf,expires,auth_revision FROM sessions WHERE token_hash=?',(key,)).fetchone()
    if not row:return None
    return {'csrf':row[0],'expires':row[1],'auth_revision':row[2]}


def safe_slug(s):
    return isinstance(s, str) and len(s) <= 85 and SLUG.fullmatch(s) is not None


def private_write(path, payload):
    import tempfile
    fd, name = tempfile.mkstemp(prefix='.draft-', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'wb') as f:
            os.fchmod(f.fileno(), 0o600)
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, str(path))
    finally:
        if os.path.exists(name):
            os.unlink(name)


def set_password():
    mkdir()
    print('Private DigiByte Newsroom editor password (not GitHub/SSH password).')
    while True:
        p = getpass.getpass('Choose password (at least 9 characters): ')
        if len(p) < 9:
            print('Please use at least 9 characters.'); continue
        confirm = getpass.getpass('Confirm password: ')
        if p != confirm:
            print('Passwords did not match.'); continue
        break
    salt = secrets.token_bytes(24)
    digest = hashlib.pbkdf2_hmac('sha256', p.encode(), salt, 600000)
    private_write(AUTH, json.dumps({'salt':salt.hex(), 'digest':digest.hex()}).encode())
    print('Password configured securely on server (PBKDF2-HMAC-SHA256, 600,000 rounds).')


def check_password(p):
    try:
        d = json.loads(AUTH.read_text())
        value = hashlib.pbkdf2_hmac('sha256', p.encode(), bytes.fromhex(d['salt']), 600000)
        return hmac.compare_digest(value, bytes.fromhex(d['digest']))
    except (ValueError, OSError, KeyError, TypeError):
        return False


def public_asset(path, data):
    """Atomic publication, never write user-provided paths."""
    import tempfile
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix='.dgb-image-', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'wb') as f:
            os.fchmod(f.fileno(), 0o644)
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        if path.exists():
            raise RuntimeError('Image filename already exists: ' + path.name)
        os.replace(temp, str(path))
    finally:
        if os.path.exists(temp): os.unlink(temp)


def publisher():
    p = ROOT / 'tools/news-publisher.py'
    spec = importlib.util.spec_from_file_location('dgb_publisher', str(p))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def markdown_source(d, images=None):
    fields = ['title','slug','summary','category','image_alt','tags']
    for key in fields:
        value = d.get(key, '')
        if not isinstance(value, str) or '\n' in value or '\r' in value or value.strip().startswith('---'):
            raise ValueError('Invalid value: ' + key)
    if not safe_slug(d.get('slug')): raise ValueError('Invalid article slug')
    img = images or {'image':'/news/assets/newsroom-social-v33.jpg'}
    data = {**{k:d.get(k,'').strip() for k in fields}, **img, 'published':'auto'}
    # No YAML parser: source publisher's line-based metadata; reject delimiters.
    if any(': ' in k or '\x00' in v for k,v in data.items()):
        raise ValueError('Invalid article metadata')
    body = d.get('body','')
    if not isinstance(body, str) or len(body) > 100000 or not body.strip():
        raise ValueError('Article body is required (max 100,000 characters)')
    return '---\n' + ''.join(f'{k}: {v}\n' for k,v in data.items()) + '---\n\n' + body.strip() + '\n'


def git(*args):
    proc = subprocess.run(['git','-C',str(ROOT),*args], text=True, capture_output=True)
    if proc.returncode: raise RuntimeError('Git operation failed: ' + ' '.join(args) + ': ' + proc.stderr[-600:])
    return proc.stdout.strip()


def create_images(d):
    if Image is None: raise RuntimeError('Image library missing; rerun installer')
    slug = d['slug']
    original = IMAGES / (slug + '.bin')
    if not original.is_file():
        raise ValueError('Upload a unique, relevant article image before publishing')
    raw = original.read_bytes()
    if len(raw) > 8 * 1024 * 1024:
        raise ValueError('Image is too large (8 MB limit)')
    Image.MAX_IMAGE_PIXELS = 24_000_000
    try:
        with Image.open(io.BytesIO(raw)) as test:
            if test.format not in ('JPEG','PNG','WEBP'): raise ValueError('Only JPEG, PNG or WebP accepted')
            test.verify()
        with Image.open(io.BytesIO(raw)) as src:
            src = ImageOps.exif_transpose(src).convert('RGB')
            if src.width < 1600 or src.height < 1200:
                raise ValueError('Featured image must be at least 1600 × 1200 pixels')
            center = (max(0,min(100,int(d.get('focus_x',50))))/100,
                      max(0,min(100,int(d.get('focus_y',50))))/100)
            variants = [('image',(1600,900),'16x9'),('image_4x3',(1200,900),'4x3'),('image_square',(1200,1200),'1x1')]
            produced = {}
            for key,size,suffix in variants:
                cropped = ImageOps.fit(src,size,method=Image.Resampling.LANCZOS,centering=center)
                output = io.BytesIO()
                cropped.save(output,format='JPEG',quality=86,optimize=True,progressive=True,subsampling=0)
                relative = 'news/assets/' + slug + '-' + suffix + '.jpg'
                produced[relative] = output.getvalue()
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError) as e:
        raise ValueError('Invalid or unsafe image: ' + e.__class__.__name__)
    return produced, {'image':'/news/assets/'+slug+'-16x9.jpg',
                      'image_4x3':'/news/assets/'+slug+'-4x3.jpg',
                      'image_square':'/news/assets/'+slug+'-1x1.jpg'}


def publish_slug(slug):
    if not PUBLISH_LOCK.acquire(blocking=False): raise RuntimeError('Another publication is running')
    try:
        if not safe_slug(slug): raise ValueError('Invalid slug')
        d = json.loads((DRAFTS/(slug+'.json')).read_text())
        if d.get('slug') != slug: raise ValueError('Draft mismatch')
        if 'EDITORIAL WORKING DRAFT' in d.get('body','') or 'VERIFY BEFORE PUBLISHING' in d.get('body',''):
            raise ValueError('Legacy working-draft warnings must be removed after factual review.')
        if d.get('review_required') is True and d.get('review_confirmed') is not True:
            raise ValueError('Verify the private source checklist and approve the AI draft before publishing.')
        mod = publisher()
        mod.verify_repo()
        # Prepare and validate content BEFORE writing a public image.
        images, paths = create_images(d)
        manuscript = markdown_source(d,paths)
        meta, body = mod.parse_manuscript(markdown_source(d))
        mod.markdown(body)
        # Variant paths are validated by the publisher after GitHub-first asset deployment.
        for rel in images:
            if (ROOT/rel).exists() or (LIVE/rel).exists():
                raise ValueError('Image asset already published: '+rel)
        if (ROOT/'news'/ (slug+'.html')).exists() or (LIVE/'news'/(slug+'.html')).exists():
            raise ValueError('Article URL already published')
        # GitHub first for image assets; then deploy only those assets. No secret files.
        for rel,buf in images.items(): public_asset(ROOT/rel,buf)
        git('add','--',*images)
        if sorted(git('diff','--cached','--name-only').splitlines()) != sorted(images):
            raise RuntimeError('Unexpected staged files, refusing to commit')
        git('diff','--cached','--check')
        git('commit','-m','Add article-specific image variants for '+slug)
        git('push','origin','main')
        for rel,buf in images.items(): public_asset(LIVE/rel,buf)
        # Publisher creates article + feeds + sitemaps, commits/pushes and deploys.
        mod.publish(manuscript)
        (DRAFTS/(slug+'.json')).unlink()
        original = IMAGES/(slug+'.bin')
        if original.exists(): original.unlink()
        return {'url':'https://www.digibytewallet.org/news/'+slug+'.html', 'images':list(images)}
    finally:
        PUBLISH_LOCK.release()





def unpublish_slug(slug):
    if not safe_slug(slug):raise ValueError('Invalid published article slug')
    if not PUBLISH_LOCK.acquire(blocking=False):raise RuntimeError('Another publication or withdrawal is in progress')
    try:
        tool=ROOT/'tools/news-unpublish.py'
        if not tool.is_file():raise RuntimeError('Unpublish helper not installed')
        run=subprocess.run([sys.executable,str(tool),'--slug',slug],
                 text=True,capture_output=True,timeout=120)
        if run.returncode:
            raise RuntimeError('Withdrawal refused: '+(run.stderr or run.stdout)[-400:])
        try:return json.loads(run.stdout.splitlines()[-1])
        except (ValueError,IndexError):raise RuntimeError('Withdrawal tool returned invalid response')
    finally:
        PUBLISH_LOCK.release()

def publication_control_v06():
    """Published story inventory, including protected withdrawal controls."""
    items=json.loads((ROOT/'news/feed.json').read_text(encoding='utf-8')).get('items',[])
    output=[]
    for x in items[:80]:
        url=x.get('url','')
        prefix='https://www.digibytewallet.org/news/'
        if not isinstance(url,str) or not url.startswith(prefix) or not url.endswith('.html'):continue
        slug=url[len(prefix):-5]
        if not safe_slug(slug):continue
        rel='news/'+slug+'.html'
        source=ROOT/rel;live=LIVE/rel
        aligned=source.is_file() and live.is_file() and source.read_bytes()==live.read_bytes()
        output.append({'title':str(x.get('title',''))[:155],'slug':slug,'url':url,
                       'published':str(x.get('date_published',''))[:45],
                       'source_present':(ROOT/'news/content'/(slug+'.md')).is_file(),
                       'deployment_aligned':bool(aligned),
                       'source_url':'https://github.com/sumcoinlabs/digibytewallet-org/blob/main/news/content/'+slug+'.md'})
    return {'articles':output,'mode':'admin-withdrawals','auto_publish':False,
            'correction_enabled':False,'retraction_enabled':True}

PAGE = r'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex,nofollow"><title>DigiByte Newsroom · Private Editor</title>
<style>
:root{color-scheme:dark;--bg:#081629;--panel:#102440;--line:#284968;--fg:#edf6ff;--muted:#a8bfd4;--a:#5ddce8}
*{box-sizing:border-box}body{background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,sans-serif;margin:0}button,input,textarea,select{font:inherit}button{cursor:pointer;background:#206083;color:white;border:1px solid #397e9d;border-radius:9px;padding:9px 14px}button:hover{background:#2b7797}button:disabled{opacity:.5;cursor:wait}
header{background:#0a1c32;border-bottom:1px solid var(--line);padding:16px max(24px,calc((100vw - 1300px)/2))}header strong{font-size:20px}.top{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap}header small{color:var(--muted)}main{max-width:1340px;margin:24px auto;padding:0 20px;display:grid;grid-template-columns:220px minmax(0,1fr) 280px;gap:22px}.panel{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px}h2{margin:0 0 18px;font-size:19px}label{display:block;color:#d6e6f3;font-weight:650;margin:12px 0 5px;font-size:13px}input,textarea,select{width:100%;background:#091a30;border:1px solid #365777;border-radius:9px;color:var(--fg);padding:10px}input:focus,textarea:focus{outline:2px solid var(--a)}textarea{min-height:350px;resize:vertical;font-family:ui-monospace,monospace;font-size:14px;line-height:1.7}#title{font-size:22px;font-weight:700}#summary{min-height:85px}.muted,small{color:var(--muted)}.toolbar{display:flex;gap:5px;flex-wrap:wrap;margin:10px 0}.toolbar button{padding:5px 10px}.buttons{display:flex;gap:10px;flex-wrap:wrap;margin-top:17px}.publish{background:#197354;border-color:#2f9e77}.draft{padding:10px;margin:8px 0;border-radius:8px;border:1px solid var(--line);cursor:pointer;overflow-wrap:anywhere}.draft:hover{border-color:var(--a)}#preview{background:#f9fbfe;color:#1b2c3d;min-height:350px;padding:25px;border-radius:9px;overflow:auto;display:none}#preview a{color:#17658f}#preview img{max-width:100%}.notice{color:#e8dba6;font-size:13px}.ok{color:#7cddb7}.err{color:#ffadb1}#imgpreview{width:100%;aspect-ratio:16/9;object-fit:cover;border-radius:8px;display:none}.stack{display:flex;flex-direction:column;gap:8px}.count{font-size:12px;color:var(--muted);text-align:right}a{color:#70e4ef}@media(max-width:1050px){main{grid-template-columns:1fr}.side{order:3}}@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important}}
</style></head><body><header><div class="top"><div><strong>DigiByte Wallet · Private Newsroom</strong><br><small>SSH tunnel + password · drafts stay on server · GitHub-first publishing</small></div><a href="http://127.0.0.1:8878/" target="_blank" rel="noopener noreferrer" style="margin-right:16px">Story Radar ↗</a><button id="logout">Sign out</button></div></header><main>
<aside class="panel side"><h2>Private drafts</h2><button id="new">+ New article</button><div id="drafts"></div><p class="notice">Unpublished drafts and original images never enter the public repository.</p><h2 style="margin-top:22px">Published control</h2><p class="muted" style="font-size:12px">Published stories can be withdrawn after confirmation. Original Git history remains available.</p><button id="refreshPublishedV06" type="button">Refresh published</button><div id="publishedV06" class="stack" style="margin-top:10px"></div></aside>
<section class="panel"><label>Headline</label><input id="title" maxlength="155" placeholder="A clear, factual headline"><label>Article address (slug)</label><input id="slug" maxlength="85" placeholder="a-descriptive-article-title"><label>SEO summary</label><textarea id="summary" maxlength="360" style="min-height:85px" placeholder="A concise, factual description (45–360 characters)"></textarea><div class="count" id="summarycount"></div><label>Article text</label><div class="toolbar"><button data-md="bold" type="button">Bold</button><button data-md="h2" type="button">Heading</button><button data-md="h3" type="button">Subheading</button><button data-md="list" type="button">List</button><button data-md="link" type="button">Link</button><button id="togglepreview" type="button">Preview</button></div><textarea id="body" placeholder="Write your story here. You can use the toolbar for headings, emphasis, links, and lists."></textarea><div id="preview"></div><div id="reviewpanel" class="panel" style="display:none;margin-top:14px;background:#112b3e"><strong>Private source verification</strong><p class="notice">These notes are private and are never added to the published article.</p><ul id="reviewnotes" style="font-size:13px;padding-left:20px"></ul><label style="display:flex;gap:10px;align-items:center"><input id="reviewchecked" type="checkbox" style="width:auto">I have checked the claims, links, release status and artwork.</label></div><div class="buttons"><button id="save">Save draft</button><button class="publish" id="publish">Publish to website</button></div><p id="status" role="status" aria-live="polite"></p></section>
<aside class="panel side"><h2>Search presentation</h2><p class="muted">Each article receives NewsArticle + breadcrumb data, canonical URL, accurate first-published timestamp, social metadata and sitemap entries.</p><label>Category</label><select id="category"><option>Development update</option><option>Security</option><option>Release</option><option>Education</option><option>Project news</option></select><label>Tags (comma separated)</label><input id="tags" value="DigiByte, DGB, DigiByte Wallet"><label>Featured image · JPEG, PNG, WebP</label><input id="image" type="file" accept="image/jpeg,image/png,image/webp"><img id="imgpreview" alt="Featured image crop preview"><p class="notice">Upload an original, relevant image at least 1600 × 1200px (max 8 MB). We generate 16:9, 4:3 and square crops for Google. Generic logos/text-heavy images are discouraged.</p><label>Horizontal focal point</label><input id="focus_x" type="range" min="0" max="100" value="50"><label>Vertical focal point</label><input id="focus_y" type="range" min="0" max="100" value="50"><label>Image alternative text</label><input id="image_alt" maxlength="180" placeholder="Describe what is visible in the picture"><div class="buttons"><button id="check">Check article</button></div><p class="notice">Release status must be verified. Publishing cannot guarantee search rankings, rich results, Google News or Discover placement.</p></aside>
</main><script>
const $=id=>document.getElementById(id), fields=['title','slug','summary','category','tags','body','image_alt','focus_x','focus_y'];let slugLocked=false;let preview=false;let csrf='';let imageData=null;let hasServerImage=false;let reviewRequired=false;let reviewVerification=[];
async function api(path,body){let r=await fetch(path,{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json','X-CSRF-Token':csrf}:{},body:body?JSON.stringify(body):undefined,credentials:'same-origin'});let x=await r.json();if(r.status===401){location.href='/login';throw Error('Session expired')}if(!r.ok)throw Error(x.error||'Request failed');return x}
function announce(s,err=false){$('status').textContent=s;$('status').className=err?'err':'ok'}
function data(){let o={};for(let key of fields)o[key]=$(key).value.trim();o.review_required=reviewRequired;o.review_confirmed=reviewRequired?$('reviewchecked').checked:false;o.verification=reviewVerification;return o}
function apply(d){for(let key of fields)$(key).value=d[key]||((key==='focus_x'||key==='focus_y')?'50':'');$('slug').dataset.original=d.slug||'';slugLocked=!!d.slug;hasServerImage=!!d.has_image;imageData=null;$('image').value='';$('imgpreview').style.display='none';preview=false;$('preview').style.display='none';$('body').style.display='block';$('togglepreview').textContent='Preview';reviewRequired=d.review_required===true;reviewVerification=Array.isArray(d.verification)?d.verification:[];$('reviewpanel').style.display=reviewRequired?'block':'none';$('reviewchecked').checked=reviewRequired&&d.review_confirmed===true;const details=$('reviewnotes');details.replaceChildren();reviewVerification.forEach(v=>{const li=document.createElement('li');li.textContent=v;details.append(li)});announce('Draft loaded')}
async function publishedControlV06(){
 const out=$('publishedV06');out.replaceChildren();
 try{let x=await api('/api/published-control-v06');
 for(const p of x.articles){let card=document.createElement('div');card.className='draft';
   let title=document.createElement('strong');title.textContent=p.title;card.append(title);
   let status=document.createElement('small');status.style.display='block';
   status.textContent=p.deployment_aligned?'Production matches GitHub checkout':'Warning: production/source mismatch';card.append(status);
   let link=document.createElement('a');link.textContent='Open article';link.href=p.url;link.target='_blank';link.rel='noopener noreferrer';card.append(link);
    if(p.deployment_aligned){
      let b=document.createElement('button');b.textContent='Unpublish';b.type='button';
      b.style.marginLeft='8px';b.style.background='#7e3142';
      b.onclick=async()=>{
        let typed=prompt('To unpublish this story from the site and feeds, type its exact slug: '+p.slug);
        if(typed!==p.slug){announce('Unpublish cancelled: slug did not match',true);return}
        if(!confirm('Remove this article from the website, feeds and sitemaps? Git history and outside caches will remain.'))return;
        b.disabled=true;
        try{let result=await api('/api/unpublish',{slug:p.slug});announce('Unpublished: '+result.slug+' (GitHub '+result.commit+')');await publishedControlV06()}
        catch(e){announce('Unpublish failed: '+e.message,true);b.disabled=false}
      };card.append(b);
    }
   if(p.source_present){let src=document.createElement('a');src.textContent=' · Manuscript';src.href=p.source_url;src.target='_blank';src.rel='noopener noreferrer';card.append(src)}
   out.append(card);
 }
 if(!x.articles.length){out.textContent='No published stories in feed.'}
 }catch(err){out.textContent='Published inventory unavailable: '+err.message}
}
$('refreshPublishedV06').onclick=publishedControlV06;
async function list(){let x=await api('/api/drafts');$('drafts').replaceChildren();for(let d of x.drafts){let b=document.createElement('div');b.className='draft';b.textContent=d.title||d.slug;b.onclick=async()=>{try{let v=await api('/api/draft/'+encodeURIComponent(d.slug));apply(v.draft)}catch(e){announce(e.message,true)}};$('drafts').append(b)}}
function slugify(s){return s.toLowerCase().normalize('NFKD').replace(/[^a-z0-9 ]/g,'').trim().replace(/\s+/g,'-').slice(0,85).replace(/-+$/,'')}
$('title').oninput=()=>{if(!slugLocked)$('slug').value=slugify($('title').value)};$('slug').oninput=()=>{slugLocked=true};$('summary').oninput=()=>$('summarycount').textContent=$('summary').value.length+'/360';
for(let b of document.querySelectorAll('[data-md]'))b.onclick=()=>{let t=$('body'),a=t.selectionStart,z=t.selectionEnd,s=t.value.slice(a,z)||'text';let k=b.dataset.md;let v=k==='bold'?'**'+s+'**':k==='h2'?'## '+s:k==='h3'?'### '+s:k==='list'?'- '+s:'['+s+'](https://example.com)';t.setRangeText(v,a,z,'select');t.focus()};
$('image').onchange=async()=>{let f=$('image').files[0];if(!f)return;if(f.size>8*1024*1024){announce('Image must be 8 MB or less',true);return}if(!['image/jpeg','image/png','image/webp'].includes(f.type)){announce('JPEG, PNG or WebP only',true);return}imageData=await new Promise((resolve,reject)=>{let rd=new FileReader();rd.onload=()=>resolve(rd.result);rd.onerror=reject;rd.readAsDataURL(f)});hasServerImage=true;$('imgpreview').src=imageData;$('imgpreview').style.display='block';announce('Image loaded; save draft to store it privately')};
function focusPreview(){$('imgpreview').style.objectPosition=$('focus_x').value+'% '+$('focus_y').value+'%'};$('focus_x').oninput=focusPreview;$('focus_y').oninput=focusPreview;
$('new').onclick=()=>{apply({category:'Development update',tags:'DigiByte, DGB, DigiByte Wallet'});slugLocked=false};
$('togglepreview').onclick=async()=>{try{if(!preview){let x=await api('/api/preview',{body:$('body').value});$('preview').innerHTML=x.html;$('preview').style.display='block';$('body').style.display='none';$('togglepreview').textContent='Edit article';preview=true}else{$('preview').style.display='none';$('body').style.display='block';$('togglepreview').textContent='Preview';preview=false}}catch(e){announce(e.message,true)}};
$('save').onclick=async()=>{try{let d=data();if(imageData)d.image_data=imageData;let x=await api('/api/save',d);imageData=null;hasServerImage=x.has_image;announce('Draft saved privately');await list()}catch(e){announce(e.message,true)}};
$('check').onclick=async()=>{try{let x=await api('/api/check',data());announce(x.message)}catch(e){announce(e.message,true)}};
$('publish').onclick=async()=>{if(!confirm('Publish this article publicly on digibytewallet.org and commit to GitHub?'))return;let b=$('publish');b.disabled=true;try{let d=data();if(imageData){d.image_data=imageData;await api('/api/save',d);imageData=null;}else await api('/api/save',d);let x=await api('/api/publish',{slug:d.slug});announce('Published: '+x.url);await list()}catch(e){announce(e.message,true)}finally{b.disabled=false}};
$('logout').onclick=async()=>{await api('/api/logout',{});location.href='/login'};
// Accept only explicitly confirmed working drafts from the private SSH-tunneled Story Radar.
const dgbImportedTickets=new Map();
window.addEventListener('message',event=>{
  if(event.origin!=='http://127.0.0.1:8878'||!csrf)return;
  const msg=event.data;
  if(!msg||msg.type!=='dgb_engine_import'||msg.version!==1||typeof msg.ticket!=='string'||!/^dgb-[a-f0-9]{24}$/.test(msg.ticket))return;
  const d=msg.draft;
  if(!d||typeof d!=='object'||typeof d.title!=='string'||d.title.length>155||typeof d.slug!=='string'||!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(d.slug)||d.slug.length>85||typeof d.summary!=='string'||d.summary.length>360||typeof d.body!=='string'||d.body.length>100000)return;
  if(dgbImportedTickets.has(msg.ticket)){if(event.source)event.source.postMessage({type:'dgb_editor_imported',ticket:msg.ticket,accepted:dgbImportedTickets.get(msg.ticket)},event.origin);return;}
  // Automatically import into a blank editor without interrupting the user.
  // Never silently overwrite an existing article, image, or unsaved work.
  const existingWork=Boolean(
    ['title','slug','summary','body','image_alt'].some(id=>$(id).value.trim()) ||
    imageData || hasServerImage
  );
  let accepted=!existingWork;
  if(existingWork){
    announce('Import skipped to protect your existing work. Open a fresh Article Editor tab from Story Radar and resend.',true);
  }
  if(accepted){
    apply({title:d.title,slug:d.slug,summary:d.summary,body:d.body,category:d.category||'Development update',tags:d.tags||'DigiByte, DGB, DigiByte Wallet',image_alt:d.image_alt||'',focus_x:'50',focus_y:'50',review_required:d.review_required===true||d.ai_generated===true,review_confirmed:false,verification:d.verification||[]});
    // Import only private, editor-validated, original PNG artwork from Story Radar.
    // The normal Save route revalidates actual bytes, dimensions and metadata.
    if(typeof d.image_data==='string' &&
       d.image_data.startsWith('data:image/png;base64,') &&
       d.image_data.length<=4*1024*1024){
      imageData=d.image_data;
      hasServerImage=true;
      $('imgpreview').src=imageData;
      $('imgpreview').style.display='block';
      focusPreview();
    }
    announce('Working draft and original artwork imported. Verify claims and image, then Save draft.');
  }
  dgbImportedTickets.set(msg.ticket,accepted);
  if(event.source)event.source.postMessage({type:'dgb_editor_imported',ticket:msg.ticket,accepted:accepted},event.origin);
});
(async()=>{try{$('new').click();let x=await api('/api/session');csrf=x.csrf;await list();await publishedControlV06()}catch(e){announce(e.message,true)}})();
</script></body></html>'''

LOGIN = '''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>Private DigiByte Newsroom</title><style>body{background:#081629;color:#eff7ff;font:16px system-ui;min-height:90vh;display:grid;place-items:center}main{width:min(420px,90vw);background:#102440;border:1px solid #34506d;border-radius:20px;padding:30px}input,button{width:100%;box-sizing:border-box;padding:13px;font:inherit;border-radius:8px;margin-top:14px}button{background:#186181;color:white;border:0;cursor:pointer}input{background:#081629;color:white;border:1px solid #567895}small{color:#b3c6db}</style></head><body><main><h1>DigiByte Newsroom</h1><p>Private publishing dashboard</p><form method="POST" action="/login"><label>Password<input name="password" type="password" autocomplete="current-password" required autofocus></label><button>Sign in</button></form><p><small>Only available through your SSH tunnel. Authentication is required in addition to SSH access.</small></p></main></body></html>'''


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    def log_message(self,fmt,*args):
        # Never log untrusted request lines or submitted credentials.
        return
    def headers_secure(self,typ='application/json; charset=utf-8'):
        self.send_header('Content-Type',typ)
        self.send_header('Cache-Control','no-store, max-age=0')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('X-Frame-Options','DENY')
        self.send_header('Referrer-Policy','same-origin')
        self.send_header('Cross-Origin-Resource-Policy','same-origin')
        self.send_header('Content-Security-Policy',"default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'")
    def send(self,status,obj,typ='application/json; charset=utf-8',cookie=None):
        b=(obj.encode() if isinstance(obj,str) else bytes(obj) if isinstance(obj,(bytes,bytearray)) else json.dumps(obj,ensure_ascii=False).encode())
        self.send_response(status)
        self.headers_secure(typ)
        if status >= 400 and self.command == 'POST':
            self.close_connection = True
            self.send_header('Connection','close')
        if cookie is not None:self.send_header('Set-Cookie',cookie)
        self.send_header('Content-Length',str(len(b)))
        self.end_headers()
        self.wfile.write(b)
    def guard(self):
        host=self.headers.get('Host','')
        if not re.fullmatch(r'(?:127\.0\.0\.1|localhost):\d{1,5}',host):
            self.send(403,{'error':'Local access only'});return False
        if self.client_address[0] not in ('127.0.0.1','::1'):
            self.send(403,{'error':'Loopback only'});return False
        if self.command=='POST':
            origin=self.headers.get('Origin','')
            if origin!='http://'+host:
                self.send(403,{'error':'Invalid origin'});return False
        return True
    def current_session(self):
        m=re.search(r'(?:^|;\s*)dgb_session=([0-9a-f]{64})(?:;|$)',self.headers.get('Cookie',''))
        if not m:return None
        h=hashlib.sha256(m.group(1).encode()).hexdigest()
        with LOCK:
            session=S.get(h) or stored_session(h)
            if not session:return None
            if session['expires']<time.time() or session.get('auth_revision') != auth_revision():
                forget_session(h)
                return None
            S[h]=session
            return session
    def auth(self,mutate=False):
        ses=self.current_session()
        if not ses:
            self.send(401,{'error':'Sign in required'});return None
        if mutate and not hmac.compare_digest(self.headers.get('X-CSRF-Token',''),ses['csrf']):
            self.send(403,{'error':'Invalid CSRF token'});return None
        return ses
    def data(self):
        size=int(self.headers.get('Content-Length','-1'))
        if size<0 or size>MAX_BODY:raise ValueError('Request too large')
        raw=self.rfile.read(size)
        val=json.loads(raw)
        if not isinstance(val,dict):raise ValueError('Expected JSON object')
        return val
    def do_GET(self):
        if not self.guard():return
        path=urlparse(self.path).path
        if path in ('/login', '/'):
            session = self.current_session()
            if (path == '/login' and session) or (path == '/' and not session):
                self.send_response(303)
                self.headers_secure('text/plain')
                self.send_header('Location', '/' if session else '/login')
                self.send_header('Content-Length', '0')
                self.end_headers()
                return
            if path == '/login':
                return self.send(200, LOGIN, 'text/html; charset=utf-8')
        if not self.auth():return
        if path=='/':return self.send(200,PAGE,'text/html; charset=utf-8')
        if path=='/api/session':return self.send(200,{'csrf':self.current_session()['csrf']})
        if path.startswith('/api/image/'):
            slug=path[len('/api/image/'):]
            if not safe_slug(slug):return self.send(400,{'error':'Invalid slug'})
            try:
                raw=(IMAGES/(slug+'.bin')).read_bytes()
                d=json.loads((DRAFTS/(slug+'.json')).read_text())
                x=max(0,min(100,int(d.get('focus_x',50))))/100
                y=max(0,min(100,int(d.get('focus_y',50))))/100
                with Image.open(io.BytesIO(raw)) as pic:
                    pic=ImageOps.exif_transpose(pic).convert('RGB')
                    small=ImageOps.fit(pic,(640,360),method=Image.Resampling.LANCZOS,centering=(x,y))
                    out=io.BytesIO();small.save(out,format='JPEG',quality=75)
                return self.send(200,out.getvalue(),'image/jpeg')
            except (OSError,ValueError,TypeError):return self.send(404,{'error':'Draft image not found'})
        if path=='/api/published-control-v06':return self.send(200,publication_control_v06())
        if path=='/api/drafts':
            items=[]
            for p in DRAFTS.glob('*.json'):
                try:
                    d=json.loads(p.read_text());items.append({'slug':d['slug'],'title':d['title']})
                except (OSError,ValueError,KeyError):pass
            return self.send(200,{'drafts':sorted(items,key=lambda x:x['slug'])})
        if path.startswith('/api/draft/'):
            slug=path[len('/api/draft/'):]
            if not safe_slug(slug):return self.send(400,{'error':'Invalid slug'})
            try:
                d=json.loads((DRAFTS/(slug+'.json')).read_text())
                d['has_image']=(IMAGES/(slug+'.bin')).is_file()
                return self.send(200,{'draft':d})
            except OSError:return self.send(404,{'error':'Draft not found'})
        return self.send(404,{'error':'Not found'})
    def do_POST(self):
        if not self.guard():return
        path=urlparse(self.path).path
        try:
            if path=='/login':
                size=int(self.headers.get('Content-Length','0'))
                if size<0 or size>2048:return self.send(400,{'error':'Invalid login'})
                from urllib.parse import parse_qs
                pw=parse_qs(self.rfile.read(size).decode()).get('password',[''])[0]
                with LOCK:
                    FAIL[:]=[t for t in FAIL if time.time()-t<600]
                    if len(FAIL)>=8:return self.send(429,'Too many attempts. Retry later.','text/plain')
                    if not check_password(pw):
                        FAIL.append(time.time())
                        return self.send(401,'Invalid password','text/plain')
                    FAIL.clear()
                    token=secrets.token_hex(32)
                    session={'csrf':secrets.token_hex(24),'expires':time.time()+8*3600,'auth_revision':auth_revision()}
                    token_hash=hashlib.sha256(token.encode()).hexdigest()
                    S[token_hash]=session
                    remember_session(token_hash,session)
                self.send_response(303)
                self.headers_secure('text/plain')
                self.send_header('Location','/')
                self.send_header('Set-Cookie','dgb_session='+token+'; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800')
                self.send_header('Content-Length','0')
                return self.end_headers()
            ses=self.auth(mutate=True)
            if not ses:return
            v=self.data()
            if path=='/api/logout':
                m=re.search(r'dgb_session=([0-9a-f]{64})',self.headers.get('Cookie',''))
                if m:
                    forget_session(hashlib.sha256(m.group(1).encode()).hexdigest())
                return self.send(200,{'ok':True},cookie='dgb_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0')
            if path=='/api/preview':
                body=v.get('body','')
                if not isinstance(body,str) or len(body)>100000:raise ValueError('Article too long')
                return self.send(200,{'html':publisher().markdown(body)})
            if path=='/api/check':
                source=markdown_source(v)
                mod=publisher()
                # Preview does not require an uploaded image yet.
                mod.markdown(v['body'])
                if len(re.findall(r'\w+',v['body']))<60:raise ValueError('Write at least 60 words')
                if len(v['title'])<10 or len(v['summary'])<45:raise ValueError('Headline or summary too short')
                return self.send(200,{'message':'Article fields and Markdown look ready. Upload a featured image and save draft before publishing.'})
            if path=='/api/save':
                slug=v.get('slug','')
                if not safe_slug(slug):raise ValueError('Invalid slug')
                if (LIVE/'news'/(slug+'.html')).exists():raise ValueError('This article URL is already published')
                if len(json.dumps(v))>MAX_BODY:raise ValueError('Draft too large')
                original_image=v.pop('image_data',None)
                # Validate all textual fields and private editorial metadata before saving.
                for flag in ('review_required','review_confirmed'):
                    if flag in v and type(v[flag]) is not bool:
                        raise ValueError('Invalid private review status')
                checks=v.get('verification',[])
                if not isinstance(checks,list) or len(checks)>12 or not all(isinstance(item,str) and len(item)<300 for item in checks):
                    raise ValueError('Invalid private verification checklist')
                markdown_source(v)
                if original_image is not None:
                    if not isinstance(original_image,str) or not re.match(r'^data:image/(jpeg|png|webp);base64,',original_image):raise ValueError('Invalid image data')
                    binary=base64.b64decode(original_image.split(',',1)[1],validate=True)
                    if len(binary)>8*1024*1024:raise ValueError('Image too large')
                    if Image is None:raise RuntimeError('Image library missing')
                    with Image.open(io.BytesIO(binary)) as im:
                        if im.format not in ('JPEG','PNG','WEBP') or im.width<1600 or im.height<1200 or im.width*im.height>24_000_000:
                            raise ValueError('Image must be JPEG/PNG/WebP, at least 1600 × 1200, max 24 megapixels')
                    private_write(IMAGES/(slug+'.bin'),binary)
                private_write(DRAFTS/(slug+'.json'),json.dumps(v,ensure_ascii=False).encode())
                return self.send(200,{'ok':True,'has_image':(IMAGES/(slug+'.bin')).exists()})
            if path=='/api/unpublish':
                return self.send(200,unpublish_slug(v.get('slug','')))
            if path=='/api/publish':
                result=publish_slug(v.get('slug',''))
                return self.send(200,result)
            return self.send(404,{'error':'Not found'})
        except (ValueError, RuntimeError, OSError, KeyError, TypeError) as e:
            # Error is shown to authenticated editor only; never print tokens.
            return self.send(400,{'error':str(e)[:500]})


def main():
    if len(sys.argv)==2 and sys.argv[1]=='--set-password':
        set_password();return
    if len(sys.argv)!=2 or sys.argv[1]!='--serve':
        print('Use --set-password or --serve');sys.exit(2)
    if not AUTH.is_file():
        raise SystemExit('Password not initialized. Run --set-password first.')
    if Image is None:
        raise SystemExit('Pillow is missing; install the pinned package before starting.')
    mkdir()
    print('Private editor: listening on 127.0.0.1:%d only' % PORT,flush=True)
    server=ThreadingHTTPServer(('127.0.0.1',PORT),Handler)
    server.daemon_threads=True
    server.serve_forever()


if __name__=='__main__':main()
