"""Three sellable Islamic P2S products: Ramadan/Eid table sign, Eid cookie-cutter set + maʿmoul stamp, name plate.
Units mm. Parts are written in print orientation (Z up) + a manifest with a display transform (Y up)."""
import os, math, json, base64
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import distance_transform_edt as edt

src = open('/home/claude/print/gen.py').read()
exec(src[:src.index('# ---------------------------------------------------------------- parts')])
FONT = '/home/claude/signs/Cairo.woff2'
LATIN = '/mnt/skills/examples/canvas-design/canvas-fonts/InstrumentSans-Bold.ttf'
OUT = '/home/claude/products/stl'; os.makedirs(OUT, exist_ok=True)
GOLD, BLACK, CREAM, GREEN = '#d8b25a', '#262423', '#efe6d2', '#1f3a2e'

# ------------------------------------------------------------ raster canvas helpers
class Canvas:
    def __init__(s, x0, y0, x1, y1, px):
        s.x0, s.y0, s.px = x0, y0, px
        s.W, s.H = int(math.ceil((x1-x0)/px)), int(math.ceil((y1-y0)/px))
    def P(s, x, y): return ((x - s.x0)/s.px, (y - s.y0)/s.px)
    def img(s): return Image.new('L', (s.W, s.H), 0)
    def arr(s, im): return np.array(im) > 127                     # row index = y (bottom up)
    def poly(s, pts, im=None, fill=255):
        im = im or s.img(); ImageDraw.Draw(im).polygon([s.P(*p) for p in pts], fill=fill); return im
    def circle(s, cx, cy, r, im=None, fill=255):
        im = im or s.img(); a, b = s.P(cx-r, cy-r), s.P(cx+r, cy+r)
        ImageDraw.Draw(im).ellipse([a[0], a[1], b[0], b[1]], fill=fill); return im
    def place(s, small, cx, cy):
        full = np.zeros((s.H, s.W), bool)
        r0 = int(round((cy - s.y0)/s.px)) - small.shape[0]//2; c0 = int(round((cx - s.x0)/s.px)) - small.shape[1]//2
        full[r0:r0+small.shape[0], c0:c0+small.shape[1]] = small
        return full
    def boxes(s, m, z0, z1): return raster_boxes(m, s.px, s.x0, s.y0, z0, z1)[0]
    def din(s, m): return edt(m) * s.px                           # distance to outside (inside pixels)
    def dout(s, m): return edt(~m) * s.px

def latin_mask(text, max_w, cap_h, px, tracking=0.18):
    """uppercase Latin with letter-spacing (tracking = fraction of cap height); row 0 = bottom"""
    size = int(cap_h/0.72/px)
    while True:
        f = ImageFont.truetype(LATIN, size)
        gap = tracking*cap_h/px
        widths = [f.getlength(ch) for ch in text]
        tw = sum(widths) + gap*(len(text)-1)
        if tw*px <= max_w or size < 10: break
        size = int(size*0.95)
    asc = f.getbbox('H')
    W, H = int(tw)+4, int((asc[3]-asc[1]))+4
    im = Image.new('L', (W, H), 0); d = ImageDraw.Draw(im); x = 2
    for ch, w in zip(text, widths):
        d.text((x, 2-asc[1]), ch, font=f, fill=255); x += w + gap
    return np.flipud(np.array(im) > 127)

def star8_pts(cx, cy, R, r, rot=math.pi/2):
    return [(cx + math.cos(rot + k*math.pi/8)*(R if k % 2 == 0 else r), cy + math.sin(rot + k*math.pi/8)*(R if k % 2 == 0 else r)) for k in range(16)]

parts = []
def add(prod, name, tris, color, M, t, role=''):
    fn = f'{name}.stl'; write_stl(f'{OUT}/{fn}', tris)
    v = tris.reshape(-1, 3)
    parts.append(dict(product=prod, name=name, file=fn, color=color, M=np.asarray(M, float).tolist(), t=list(map(float, t)),
                      vol=volume(tris), area=surface(tris), size=np.round(np.ptp(v, 0), 1).tolist(), role=role, tris=len(tris)))
    print(f'{name:28s} {len(tris):7d} tris  {np.round(np.ptp(v,0),1)}  {volume(tris)/1000:.2f} cm3')

I3 = np.eye(3)
RXM90 = [[1,0,0],[0,0,1],[0,-1,0]]
def rx(deg):
    a = math.radians(deg); return [[1,0,0],[0,math.cos(a),-math.sin(a)],[0,math.sin(a),math.cos(a)]]

# ------------------------------------------------------------ A) RAMADAN / EID TABLE SIGNS
SW, RH, SSH, RISE, ST, REL = 100.0, 44.0, 12.0, 40.0, 3.0, 0.6
TABW, TABH, TILT = 30.0, 7.0, 8.0
def pointed(a, rise, n=60):
    c = (rise*rise - a*a)/(2*a); R = a + c; th1 = math.atan2(rise, -c); left = []
    for i in range(n+1):
        th = math.pi + (th1-math.pi)*i/n; left.append((c + R*math.cos(th), R*math.sin(th)))
    return left + [(-x, y) for x, y in reversed(left[:-1])]
def mihrab(W, rect_h, sh, rise):
    a = W/2 - sh; yb = rect_h + 2.0
    pts = [(-W/2, 0), (W/2, 0), (W/2, rect_h), (W/2-2.0, yb)] + [(x, y+yb) for x, y in reversed(pointed(a, rise))] + [(-W/2+2.0, yb), (-W/2, rect_h)]
    return clean(pts)
SIL = mihrab(SW, RH, SSH, RISE)
HT = max(p[1] for p in SIL)

def table_sign(key, ar, lat):
    cv = Canvas(-SW/2-1, -1, SW/2+1, HT+1, 0.08)
    sil = cv.arr(cv.poly(SIL)); d = cv.din(sil)
    m = sil & (((d >= 1.6) & (d <= 2.7)) | ((d >= 3.7) & (d <= 4.4)))
    # crescent + star in the arch
    cy = RH + 2 + RISE*0.42
    cres = cv.arr(cv.circle(-1.0, cy, 7.5)) & ~cv.arr(cv.circle(2.4, cy+1.6, 6.4))
    star = cv.arr(cv.poly(star8_pts(3.6, cy+1.2, 2.9, 1.5)))
    m |= cres | star
    # Arabic greeting + letter-spaced Latin line
    tm, tsz = text_mask(ar, SW-18, 21.0, cv.px, size_cap=21.0)
    m |= cv.place(tm, 0, 27.5)
    lm = latin_mask(lat, SW-26, 3.6, cv.px, tracking=0.32)
    m |= cv.place(lm, 0, 10.5)
    # little diamonds either side of the Latin line
    lw = lm.shape[1]*cv.px/2 + 4.0
    for sx in (-1, 1):
        m |= cv.arr(cv.poly([(sx*lw-1.6, 10.5), (sx*lw, 12.1), (sx*lw+1.6, 10.5), (sx*lw, 8.9)]))
    plate = np.concatenate([extrude(SIL, 0, ST), box(-TABW/2, -TABH, 0, TABW/2, 0.01, ST)])
    gold = cv.boxes(m, ST, ST+REL)
    return plate, gold, tsz

def table_stand():
    def rect(w, d, oy=0): return [(-w/2, oy-d/2), (w/2, oy-d/2), (w/2, oy+d/2), (-w/2, oy+d/2)]
    p = [extrude(rect(112, 46, 4), 0, 2.0), loft(rect(112, 46, 4), rect(110.4, 44.4, 4), 2.0, 2.8),
         extrude(rect(96, 34, 4), 2.8, 4.0), loft(rect(96, 34, 4), rect(94.8, 32.8, 4), 4.0, 4.6)]
    zb, H = 4.6, 10.0; zt = zb + H
    SWD, SL, SD = ST + 0.35, TABW + 0.6, 8.2; zf = zt - SD
    sh = lambda z: math.tan(math.radians(TILT))*(z - zb)
    def blk(x0, x1, y0, y1, za, zc):
        return loft([(x0, y0+sh(za)), (x1, y0+sh(za)), (x1, y1+sh(za)), (x0, y1+sh(za))],
                    [(x0, y0+sh(zc)), (x1, y0+sh(zc)), (x1, y1+sh(zc)), (x0, y1+sh(zc))], za, zc)
    p += [blk(-21, 21, -7.5, 7.5, zb, zf), blk(-21, 21, -7.5, -SWD/2, zf, zt), blk(-21, 21, SWD/2, 7.5, zf, zt),
          blk(-21, -SL/2, -SWD/2, SWD/2, zf, zt), blk(SL/2, 21, -SWD/2, SWD/2, zf, zt)]
    return np.concatenate(p), zt, sh(zt)

stand, s_top, s_shift = table_stand()
for i, (key, ar, lat) in enumerate([('ramadan', 'رمضان مبارك', 'RAMADAN MUBARAK'), ('eid', 'عيد مبارك', 'EID MUBARAK')]):
    plate, gold, tsz = table_sign(key, ar, lat)
    print(key, 'text', np.round(tsz, 1))
    ox = -65 if i == 0 else 65
    # display: stand Z-up -> Y-up; plate standing, tilted back TILT, bottom edge on holder top
    Mp = rx(-TILT)
    th = math.radians(TILT)
    tp = (ox, s_top - (ST/2)*math.sin(th), 4 - s_shift - (ST/2)*math.cos(th))
    add('skilte', f'A_{key}_plade', plate, BLACK, Mp, tp, 'plade')
    add('skilte', f'A_{key}_guld', gold, GOLD, Mp, tp, 'guld')
    add('skilte', f'A_{key}_fod', stand, BLACK, RXM90, (ox, 0, 4), 'fod')

# ------------------------------------------------------------ B) EID COOKIE CUTTERS + MAʿMOUL STAMP
def cutter(mask, cv):
    din, dout = cv.din(mask), cv.dout(mask)
    flange = (~mask & (dout <= 4.0)) | (mask & (din <= 0.5))
    wall = (~mask & (dout <= 0.5)) | (mask & (din <= 0.5))
    edge = (~mask & (dout <= 0.32)) | (mask & (din <= 0.32))
    return np.concatenate([cv.boxes(flange, 0, 1.8), cv.boxes(wall, 1.8, 11.5), cv.boxes(edge, 11.5, 14.0)])

shapes = {}
cv = Canvas(-42, -42, 42, 42, 0.15)
shapes['maane'] = cv.arr(cv.circle(0, 0, 30)) & ~cv.arr(cv.circle(12, 5, 24.5))
sq = lambda r, rot: [(math.cos(rot + k*math.pi/2)*r, math.sin(rot + k*math.pi/2)*r) for k in range(4)]
shapes['stjerne'] = cv.arr(cv.poly(sq(30, math.pi/4))) | cv.arr(cv.poly(sq(30, 0)))
half = [(9, -34), (15, -27), (19, -3), (13, 17), (17, 21), (8, 29), (3, 34)]
lan = cv.arr(cv.poly(half + [(0, 35)] + [(-x, y) for x, y in reversed(half)]))
lan |= cv.arr(cv.circle(0, 37.5, 3.6))
shapes['lanterne'] = lan
mos = cv.arr(cv.poly([(-31, -26), (31, -26), (31, -4), (-31, -4)]))
mos |= cv.arr(cv.circle(0, -4, 19)) & cv.arr(cv.poly([(-40, -4), (40, -4), (40, 40), (-40, 40)]))
mos |= cv.arr(cv.poly([(-8, 12), (8, 12), (0, 24)]))
for sx in (-1, 1):
    mos |= cv.arr(cv.poly([(sx*30, -26), (sx*38, -26), (sx*38, 18), (sx*34, 29), (sx*30, 18)]))
shapes['moske'] = mos
names = {'maane': 'Halvmåne', 'stjerne': 'Rub el-Hizb-stjerne', 'lanterne': 'Fanous-lanterne', 'moske': 'Moské'}
for i, (k, msk) in enumerate(shapes.items()):
    tr = cutter(msk, cv)
    gx, gz = (i % 2)*95 - 47.5, (i // 2)*95 - 47.5
    add('udstikkere', f'B_udstikker_{k}', tr, '#c9a679', RXM90, (gx - 60, 0, gz), names[k])

# stamp (face up) + knob
cs = Canvas(-27, -27, 27, 27, 0.08)
disc = cs.arr(cs.circle(0, 0, 26))
d = cs.din(disc)
relief = disc & (d >= 1.0) & (d <= 2.3)
for k in range(24):
    a = 2*math.pi*k/24
    relief |= cs.arr(cs.circle(math.cos(a)*21.0, math.sin(a)*21.0, 0.95))
st_out = cs.arr(cs.poly(star8_pts(0, 0, 16.5, 12.0, rot=0))); st_in = cs.arr(cs.poly(star8_pts(0, 0, 14.9, 10.6, rot=0)))
relief |= st_out & ~st_in
tm, _ = text_mask('عيد', 16, 10, cs.px, size_cap=10)
relief |= cs.place(tm[:, ::-1], 0, 0.6)                    # mirrored, so the cookie reads correctly
stamp = np.concatenate([lathe([(26, 0), (26, 2.4), (25.4, 3.0)], 64), cs.boxes(relief, 2.99, 4.4)])
knob = lathe([(8, 0), (8, 1.2), (5.5, 2.5), (5, 13), (6.5, 16), (8.5, 18.5), (8.5, 20), (6, 22), (0, 22.5)], 32)
add('udstikkere', 'B_maamoul_stempel', stamp, '#c9a679', RXM90, (70, 0, -30), 'Maʿmoul-stempel')
add('udstikkere', 'B_stempel_haandtag', knob, '#c9a679', RXM90, (70, 0, 35), 'Håndtag (limes på bagsiden)')

# ------------------------------------------------------------ C) NAME PLATES
NW, NH, NT = 150.0, 58.0, 3.5
def nameplate(ar, lat):
    cv = Canvas(-NW/2-1, -NH/2-1, NW/2+1, NH/2+1, 0.08)
    base = cv.arr(cv.poly([(-NW/2, -NH/2), (NW/2, -NH/2), (NW/2, NH/2), (-NW/2, NH/2)]))
    for sx in (-1, 1):
        for sy in (-1, 1):
            base &= ~cv.arr(cv.circle(sx*NW/2, sy*NH/2, 7.5))       # Islamic inverted corners
    d = cv.din(base)
    m = base & (((d >= 1.6) & (d <= 2.7)) | ((d >= 3.7) & (d <= 4.4)))
    for sx in (-1, 1):                                            # 8-point stars at the ends
        m |= cv.arr(cv.poly(star8_pts(sx*(NW/2-15), 0, 5.2, 2.9)))
        m &= ~cv.arr(cv.circle(sx*(NW/2-15), 0, 1.4))
    tm, tsz = text_mask(ar, NW-56, 26.0, cv.px, size_cap=26.0)
    m |= cv.place(tm, 0, 6.5)
    lm = latin_mask(lat, NW-60, 5.2, cv.px, tracking=0.35)
    m |= cv.place(lm, 0, -16.5)
    return cv.boxes(base, 0, NT), cv.boxes(m, NT, NT+REL), tsz
for i, (k, ar, lat, col) in enumerate([('maryam', 'مريم', 'MARYAM', GREEN), ('yusuf', 'يوسف', 'YUSUF', BLACK)]):
    b, g, tsz = nameplate(ar, lat); print(k, 'text', np.round(tsz, 1))
    t = (0, 40 + i*70, 0)
    add('navneskilt', f'C_navn_{k}_plade', b, col, I3, t, 'plade')
    add('navneskilt', f'C_navn_{k}_guld', g, GOLD, I3, t, 'guld')

# ------------------------------------------------------------ estimates
RHO = 1.24
def grams(p, infill=0.15):
    V = p['vol']/1000; A = p['area']/100; sh = min(V, A*0.1); return RHO*(sh + max(0, V-sh)*infill)
for p in parts:
    p['g'] = round(grams(p, 1.0 if p['product'] == 'udstikkere' else 0.15), 2)   # cutters are all walls
json.dump(dict(parts=parts), open(f'{OUT}/manifest.json', 'w'), ensure_ascii=False, indent=1)
geo = {p['name']: base64.b64encode(open(f"{OUT}/{p['file']}", 'rb').read()).decode() for p in parts}
json.dump(geo, open(f'{OUT}/geometry.json', 'w'))
print('geometry.json MB', os.path.getsize(f'{OUT}/geometry.json')/1e6)
for prod in ('skilte', 'udstikkere', 'navneskilt'):
    print(prod, round(sum(p['g'] for p in parts if p['product'] == prod), 1), 'g')
