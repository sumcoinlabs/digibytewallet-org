"""Original abstract crypto editorial imagery, without headline text or copied assets.

Locally generated with Pillow; safe on the private newsroom editor's Python 3.8 venv.
"""
import hashlib
import io
import math
import random
import re
from PIL import Image, ImageDraw, ImageFilter

W, H = 1600, 1200
THEMES = {
    'digibyte': ((6, 25, 55), (35, 137, 224), (105, 220, 239)),
    'bitcoin': ((37, 23, 27), (235, 150, 50), (255, 214, 126)),
    'ethereum': ((29, 27, 68), (137, 121, 225), (151, 213, 241)),
    'sumcoin': ((5, 39, 42), (51, 179, 162), (190, 224, 173)),
    'crypto': ((10, 33, 58), (54, 137, 196), (155, 207, 224)),
}

def topic_for(text):
    t = str(text).lower()
    for k in ('digibyte', 'bitcoin', 'ethereum', 'sumcoin'):
        if k in t or (k == 'digibyte' and re.search(r'\bdgb\b', t)):
            return k
    return 'crypto'

def motif_for(text):
    t = str(text).lower()
    if re.search(r'\bcore\b|\bnode\b|network|protocol|consensus|\bblock\b|chain', t): return 'network'
    if re.search(r'wallet|address|payment|transaction|send|receive', t): return 'wallet'
    if re.search(r'secur|breach|patch|attack|vulnerab|encrypt|audit', t): return 'security'
    if re.search(r'price|market|rate|volume', t): return 'market'
    return 'release'

def blend(x, y, p): return tuple(round(x[i]*(1-p)+y[i]*p) for i in range(3))

def render(article):
    title = str(article.get('title') or '')
    content = title+' '+str(article.get('category') or '')+' '+str(article.get('body') or '')[:100]
    topic = topic_for(content)
    motif = motif_for(content)
    bg, accent, ice = THEMES[topic]
    seed = hashlib.sha256((title+'|'+str(article.get('artwork_variant',''))).encode()).digest()
    rng = random.Random(int.from_bytes(seed[:8], 'big'))
    im = Image.new('RGB', (W,H), bg)
    dr = ImageDraw.Draw(im)
    # Smooth cinematic background with no per-pixel Python loops.
    for y in range(0,H,4):
        p = .07+.16*(y/H)
        dr.rectangle((0,y,W,y+4),fill=blend(bg, accent,p))
    # Two slanted architectural planes provide depth, but no arbitrary grid text.
    dr.polygon([(0,0),(540,0),(180,1200),(0,1200)],fill=blend(bg,accent,.10))
    dr.polygon([(1070,0),(1600,0),(1600,1200),(570,1200)],fill=blend(bg,ice,.07))
    layer = Image.new('RGBA',(W,H),(0,0,0,0)); glow=ImageDraw.Draw(layer,'RGBA')
    glow.ellipse((410,40,1460,1150),fill=(*accent,105))
    glow.ellipse((570,185,1290,990),fill=(*ice,45))
    im=Image.alpha_composite(im.convert('RGBA'),layer.filter(ImageFilter.GaussianBlur(155)))
    d=ImageDraw.Draw(im,'RGBA')
    # A restrained network of quiet particles surrounds the primary editorial motif.
    cx, cy=840+rng.randint(-40,40), 605+rng.randint(-30,30)
    for radius in (230,315,405):
        d.ellipse((cx-radius,cy-radius,cx+radius,cy+radius),outline=(*ice,30),width=2)
    for _ in range(56):
        t=rng.uniform(0,2*math.pi); r=rng.uniform(315,640)
        x=round(cx+r*math.cos(t)); y=round(cy+r*math.sin(t))
        if 28<x<W-28 and 28<y<H-28:
            size=rng.randint(2,5)
            d.ellipse((x-size,y-size,x+size,y+size),fill=(*ice,rng.randint(45,150)))
    core=Image.new('RGBA',(W,H),(0,0,0,0)); c=ImageDraw.Draw(core,'RGBA')
    c.ellipse((cx-270,cy-270,cx+270,cy+270),fill=(*bg,203),outline=(*ice,145),width=4)
    c.ellipse((cx-238,cy-238,cx+238,cy+238),outline=(*accent,125),width=16)
    if motif=='network':
        nodes=[(cx-155,cy-105),(cx+136,cy-135),(cx-135,cy+150),(cx+156,cy+125),(cx,cy)]
        for a,b in [(0,1),(0,2),(0,4),(1,3),(1,4),(2,3),(2,4),(3,4)]:
            c.line((nodes[a],nodes[b]),fill=(*ice,133),width=12)
        for i,(x,y) in enumerate(nodes):
            rad=39 if i==4 else 23
            c.ellipse((x-rad,y-rad,x+rad,y+rad),fill=(*accent,240),outline=(243,252,255,250),width=5)
    elif motif=='wallet':
        c.rounded_rectangle((cx-175,cy-125,cx+160,cy+125),radius=32,fill=(*accent,85),outline=(*ice,242),width=14)
        c.rounded_rectangle((cx+20,cy-53,cx+192,cy+70),radius=26,fill=(*bg,250),outline=(*ice,245),width=9)
        c.ellipse((cx+94,cy-9,cx+124,cy+21),fill=(*accent,250))
    elif motif=='security':
        polygon=[(cx,cy-190),(cx+170,cy-120),(cx+145,cy+89),(cx,cy+185),(cx-145,cy+89),(cx-170,cy-120)]
        c.polygon(polygon,fill=(*accent,108));c.line(polygon+[polygon[0]],fill=(*ice,247),width=14,joint='curve')
        c.line([(cx-75,cy+5),(cx-14,cy+68),(cx+100,cy-62)],fill=(246,255,255,250),width=19,joint='curve')
    elif motif=='market':
        pts=[(cx-174,cy+145),(cx-95,cy+72),(cx-20,cy+98),(cx+65,cy-20),(cx+166,cy-148)]
        c.line(pts,fill=(*ice,234),width=18,joint='curve')
        for x,y in pts:c.ellipse((x-14,y-14,x+14,y+14),fill=(*accent,245),outline=(245,255,255,245),width=3)
    else:
        for i in range(4):
            y=cy-141+i*85
            c.rounded_rectangle((cx-152,y,cx+152,y+55),radius=14,fill=(*accent,55+i*24),outline=(*ice,194),width=4)
            c.ellipse((cx-125,y+21,cx-111,y+35),fill=(*ice,250))
            c.line((cx-70,y+27,cx+116,y+27),fill=(241,251,255,205),width=6)
    # Fine gold/blue accents introduce material depth, rather than copied logos or headlines.
    im=Image.alpha_composite(im,core.filter(ImageFilter.GaussianBlur(1.2)))
    d=ImageDraw.Draw(im,'RGBA')
    for i in range(3):
        d.arc((cx-470+i*22,cy-470+i*22,cx+470-i*22,cy+470-i*22),
              210+i*19,302+i*19,fill=(*ice,75),width=4)
    output=io.BytesIO()
    im.convert('RGB').save(output,format='PNG',optimize=True)
    return output.getvalue()
