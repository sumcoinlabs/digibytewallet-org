"""Original topic-aware editorial art for DigiByte Wallet Newsroom Studio.

All artwork is generated locally with Pillow. No remote images, fonts, or APIs.
Python 3.8+; used on the authenticated loopback editor only.
"""
import hashlib
import io
import math
import re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1600, 1200
THEMES = {
    'digibyte': ('#081e42', '#2b94ee', '#61dae9'),
    'bitcoin': ('#21192a', '#f1a43a', '#f9d98e'),
    'ethereum': ('#211a40', '#9f90e7', '#9ddce9'),
    'sumcoin': ('#0a2829', '#3ccbb8', '#d6c184'),
    'crypto': ('#10253c', '#4ba3dc', '#84c9ce'),
}
FONTS = [
    '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    '/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
]

def font(size, bold=True):
    files = FONTS if bold else FONTS[::-1]
    for name in files:
        if Path(name).is_file():
            try:
                return ImageFont.truetype(name, size)
            except OSError:
                pass
    return ImageFont.load_default()

def topic_for(text):
    text = text.lower()
    for key in ('digibyte', 'bitcoin', 'ethereum', 'sumcoin'):
        if key in text or (key == 'digibyte' and re.search(r'\bdgb\b', text)):
            return key
    return 'crypto'

def motif_for(text):
    text = text.lower()
    if re.search(r'\bcore\b|\bnode\b|\bnetwork\b|\bconsensus\b|\bblock\b', text):
        return 'network'
    if re.search(r'wallet|payment|transaction|address|send|receive', text):
        return 'wallet'
    if re.search(r'vulnerab|attack|breach|security|exploit|patch|audit', text):
        return 'security'
    if re.search(r'chain|protocol', text):
        return 'network'
    if re.search(r'price|market|rate|volume', text):
        return 'markets'
    return 'release'

def fit_headline(draw, title):
    title = ' '.join(re.sub(r'[^\w\s.\-:+,/#()]', ' ', title).split())[:150]
    if not title:
        title = 'Crypto technology update'
    for size in (70, 64, 58, 52, 46):
        ff = font(size)
        lines, current = [], ''
        for word in title.split():
            candidate = (current + ' ' + word).strip()
            if current and draw.textbbox((0,0), candidate, font=ff)[2] > 720:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
        if len(lines) <= 5:
            return lines, ff, size
    return lines[:5], ff, size

def render(data):
    title = str(data.get('title') or '')
    body = str(data.get('body') or '')[:500]
    category = str(data.get('category') or 'Technology update')[:40]
    topic = topic_for(title + ' ' + category + ' ' + body[:160])
    motif = motif_for(title + ' ' + body[:120])
    dark, accent, soft = THEMES[topic]
    seed = hashlib.sha256((title + '|' + category + '|' + str(data.get('artwork_variant',''))).encode()).digest()

    # A simple, quick local composition: no remote resources or slow pixel loops.
    im = Image.new('RGB', (W, H), dark)
    d = ImageDraw.Draw(im)
    for i in range(25):
        x = 790 + i * 40
        d.polygon([(x, 0), (x+410, 0), (x-140, H), (x-550, H)],
                  fill=(18+i//4, 44+i//2, 83+i//3))
    glow = Image.new('RGBA', (W, H), (0,0,0,0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((850, 190, 1560, 970), fill=tuple(bytes.fromhex(accent[1:])) + (92,))
    glow = glow.filter(ImageFilter.GaussianBlur(115))
    im = Image.alpha_composite(im.convert('RGBA'), glow)
    d = ImageDraw.Draw(im, 'RGBA')
    a = tuple(bytes.fromhex(accent[1:]))
    s = tuple(bytes.fromhex(soft[1:]))
    for x in range(130, W, 92):
        d.line((x, 0, x, H), fill=(*s, 6), width=1)
    for y in range(80, H, 92):
        d.line((0, y, W, y), fill=(*s, 6), width=1)
    d.rounded_rectangle((104, 124, 1496, 1070), radius=40,
                        outline=(*s, 90), width=3)
    d.rounded_rectangle((211, 218, 644, 274), radius=17,
                        fill=(*a, 57), outline=(*a, 160), width=2)
    d.text((232, 228), 'DIGIBYTE WALLET  /  NEWSROOM', font=font(19), fill=(238,249,255,250))
    d.text((211, 323), category.upper(), font=font(29), fill=(*s, 245))
    d.line((211, 377, 1000, 377), fill=(*a, 204), width=4)

    headline, f, size = fit_headline(d, title)
    y = 442
    for line in headline:
        d.text((208, y), line, font=f, fill=(244,250,254,255))
        y += size + 27
    d.text((211, 955), 'SOURCE-BASED REPORT   •   ORIGINAL EDITORIAL ARTWORK',
           font=font(19,False), fill=(199,220,238,225))

    # The subject motif changes with the article, while a uniform visual
    # language keeps the newsroom brand recognizable.
    cx, cy = 1231, 650
    for rad in (294, 237, 176):
        d.ellipse((cx-rad, cy-rad, cx+rad, cy+rad), outline=(*s, 91), width=3)
    for k in range(18):
        theta = 2*math.pi*k/18 + (seed[k%32]/255)
        radius = 256 + seed[k%32]%60
        x = int(cx + radius*math.cos(theta))
        y = int(cy + radius*math.sin(theta))
        d.ellipse((x-6,y-6,x+6,y+6),fill=(*a,242))
    d.rounded_rectangle((1080, 507, 1385, 812), radius=56,
                        fill=(9, 29, 54, 245), outline=(*a, 230), width=7)
    if motif == 'network':
        nodes = [(1147,600), (1320,588), (1230,662), (1154,742), (1320,742)]
        for x,y in [(0,2),(1,2),(2,3),(2,4),(0,1),(3,4)]:
            d.line(nodes[x]+nodes[y], fill=(*s,230), width=8)
        for x,y in nodes:
            d.ellipse((x-18,y-18,x+18,y+18),fill=(*a,245),outline=(255,255,255,240),width=4)
    elif motif == 'wallet':
        d.rounded_rectangle((1131,590,1335,743),radius=22,fill=(*a,120),outline=(*s,250),width=8)
        d.rounded_rectangle((1226,639,1360,699),radius=18,fill=(9,29,54,255),outline=(*s,250),width=6)
        d.ellipse((1250,657,1276,683),fill=(*a,250))
    elif motif == 'security':
        pts = [(1232,555),(1337,594),(1328,705),(1232,774),(1136,705),(1127,594)]
        d.polygon(pts,fill=(*a,95))
        d.line(pts+[pts[0]],fill=(*s,242),width=10,joint='curve')
        d.line([(1186,667),(1218,699),(1284,622)],fill=(246,255,255,250),width=15,joint='curve')
    elif motif == 'markets':
        points=[(1131,746),(1194,686),(1249,714),(1300,615),(1356,566)]
        d.line(points, fill=(*s,240), width=10, joint='curve')
        for x,y in points:
            d.ellipse((x-11,y-11,x+11,y+11),fill=(*a,255))
    else:
        for k in range(4):
            y=554+54*k
            d.rounded_rectangle((1133,y,1338,y+42),radius=8,
                                fill=(*a,35+k*17),outline=(*s,170),width=3)
            d.ellipse((1151,y+13,1167,y+29),fill=(*a,250))
            d.line((1190,y+21,1300,y+21),fill=(244,250,255,222),width=5)
    d.rounded_rectangle((1114,849,1353,910),radius=18,
                        fill=(*a,48),outline=(*s,130),width=2)
    d.text((1136,862),motif.upper(),font=font(24),fill=(244,252,255,248))
    out = io.BytesIO()
    im.convert('RGB').save(out, format='PNG', optimize=True)
    return out.getvalue()
