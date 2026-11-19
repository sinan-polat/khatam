"""Entré-sæt: ZAWJ (زوج) parnøgleringe der stablet danner khatam-stjernen, BAB (باب) nøgleholder, TABAQ (طبق) nøglebakke.
Units mm, print orientation Z up."""
import os, math, json, struct
import numpy as np
src = open('/home/claude/products/products.py').read()
exec(src[:src.index('parts = []')])
OUT = '/home/claude/entre/stl'; os.makedirs(OUT, exist_ok=True)
def rot(pts, a): return [(x*math.cos(a)-y*math.sin(a), x*math.sin(a)+y*math.cos(a)) for x, y in pts]
def rsq(s, r, n=8):   # rounded square, centred
    pts = []
    for cx, cy, a0 in [(s/2-r, s/2-r, 0), (-s/2+r, s/2-r, 90), (-s/2+r, -s/2+r, 180), (s/2-r, -s/2+r, 270)]:
        for k in range(n+1):
            a = math.radians(a0 + 90*k/n); pts.append((cx + r*math.cos(a), cy + r*math.sin(a)))
    return pts
def save(name, tris): write_stl(f'{OUT}/{name}.stl', tris); return name

# ================= ZAWJ: two squares (40 mm) – together, rotated 45°, they form the 8-point khatam star
S, ZT, INL = 40.0, 4.0, 0.4
MAG_D, MAG_H = 10.2, 2.1            # pocket for a 10 x 2 mm neodymium magnet, inserted at a print pause
def zawj(name_ar, name_lat, tag):
    px = 0.04; cv = Canvas(-S, -S, S, S, px)
    sq = cv.arr(cv.poly(rsq(S, 2.5)))
    # key hole at one corner (pointing down-right when worn)
    hx, hy = S/2-5.2, -(S/2-5.2)
    body = sq & ~cv.arr(cv.circle(hx, hy, 2.3))
    d = cv.din(sq)
    front = sq & (d >= 1.6) & (d <= 2.2)                                  # inner gold square line
    front |= cv.arr(cv.poly(star8_pts(0, 10.5, 1.8, 0.9)))
    front &= ~cv.arr(cv.circle(hx, hy, 4.2))
    tm, _ = text_mask(name_ar, S*0.42, S*0.2, px); front |= cv.place(tm, 0, 0.6)
    lm = latin_mask(name_lat, S*0.42, 2.2, px, tracking=0.3); front |= cv.place(lm, 0, -6.4)
    front &= body
    back = np.zeros_like(sq)
    km = latin_mask('KHATAM', S*0.4, 2.0, px, tracking=0.5); back |= cv.place(km, 0, -12)[:, ::-1] & body
    mag = cv.arr(cv.circle(0, 0, MAG_D/2))
    z0m = (ZT-MAG_H)/2; z1m = z0m+MAG_H
    plate = np.concatenate([cv.boxes(body & ~back, 0, INL), cv.boxes(body, INL, z0m), cv.boxes(body & ~mag, z0m, z1m),
                            cv.boxes(body, z1m, ZT-INL), cv.boxes(body & ~front, ZT-INL, ZT)])
    save(f'zawj_{tag}_plade', plate); save(f'zawj_{tag}_guld_forside', cv.boxes(front, ZT-INL, ZT)); save(f'zawj_{tag}_guld_bagside', cv.boxes(back, 0, INL))
zawj('يوسف', 'YUSUF', 'ham'); zawj('مريم', 'MARYAM', 'hende')

# ================= BAB: wall key holder (mihrab plaque) with star dock for ZAWJ + 4 hook holes
BW, RECT, BT = 160.0, 140.0, 7.0
def pointed(a, rise, n=60):
    c = (rise*rise - a*a)/(2*a); R = a + c; th1 = math.atan2(rise, -c); left = []
    for i in range(n+1):
        th = math.pi + (th1-math.pi)*i/n; left.append((c + R*math.cos(th), R*math.sin(th)))
    return left + [(-x, y) for x, y in reversed(left[:-1])]
arch = [(x, RECT+y) for x, y in pointed(BW/2, BW/2*1.25)]
SIL = [(-BW/2, 0), (BW/2, 0)] + arch[::-1][:0] + list(reversed([(x, y) for x, y in arch]))
SIL = [(-BW/2, 0), (BW/2, 0)] + [(x, y) for x, y in reversed(arch)]
TOPY = max(p[1] for p in SIL)
px = 0.1; cv = Canvas(-BW/2-1, -1, BW/2+1, TOPY+1, px)
sil = cv.arr(cv.poly(SIL))
d = cv.din(sil)
gold = sil & (((d >= 4) & (d <= 5.2)) | ((d >= 7) & (d <= 7.6)))
dua, _ = text_mask('بسم الله توكلت على الله', BW*0.62, 16, px); gold |= cv.place(dua, 0, RECT+8) & sil
# star dock: outline of the 8-point star (two 40 mm squares) + magnet under centre
SC = (0, 92.0)
sqA = cv.arr(cv.poly([(x+SC[0], y+SC[1]) for x, y in rsq(S+1.2, 3.0)]))
sqB = cv.arr(cv.poly([(x+SC[0], y+SC[1]) for x, y in rot(rsq(S+1.2, 3.0), math.pi/4)]))
star = sqA | sqB
ds = cv.dout(star)
gold |= (ds >= 2.5) & (ds <= 3.3) & sil
# 4 hook pilot holes + names
hooks = [(-BW/2 + BW*(i+0.5)/4, 22.0) for i in range(4)]
holes = np.zeros_like(sil)
for i, (hx, hy) in enumerate(hooks):
    holes |= cv.arr(cv.circle(hx, hy, 1.4))
    gold |= cv.arr(cv.circle(hx, hy, 5.2)) & ~cv.arr(cv.circle(hx, hy, 4.4))
for i, nm in enumerate(['يوسف', 'مريم', 'آدم', 'سارة']):
    tm, _ = text_mask(nm, BW/4-10, 8, px); gold |= cv.place(tm, hooks[i][0], 38) & sil
# keyhole slots on the back for wall screws
kh = np.zeros_like(sil)
for x in (-45, 45):
    kh |= cv.arr(cv.circle(x, 128, 4.6)) | cv.arr(cv.poly([(x-2.3, 128), (x+2.3, 128), (x+2.3, 140), (x-2.3, 140)])) | cv.arr(cv.circle(x, 140, 2.3))
khead = np.zeros_like(sil)
for x in (-45, 45): khead |= cv.arr(cv.poly([(x-4.6, 128), (x+4.6, 128), (x+4.6, 140), (x-4.6, 140)])) | cv.arr(cv.circle(x, 140, 4.6)) | cv.arr(cv.circle(x, 128, 4.6))
mag = cv.arr(cv.circle(SC[0], SC[1], 7.7))          # 15 x 3 mm magnet (or two 10x2) under 1 mm skin
gold &= ~holes
plate = np.concatenate([
    cv.boxes(sil & ~holes & ~khead, 0, 2.5),            # back: key-hole head cavity 2.5 mm deep
    cv.boxes(sil & ~holes & ~kh, 2.5, 4.0),             # slot neck layer
    cv.boxes(sil & ~holes & ~mag, 4.0, BT-1.0),
    cv.boxes(sil & ~holes, BT-1.0, BT)])
save('bab_plade', plate); save('bab_guld', cv.boxes(gold, BT, BT+0.6))

# ================= TABAQ: octagonal key tray with star floor
AP, TH, WT, FT = 68.0, 20.0, 2.6, 3.0
def octo(apo, rot0=math.pi/8):
    R = apo/math.cos(math.pi/8); return [(R*math.cos(rot0+k*math.pi/4), R*math.sin(rot0+k*math.pi/4)) for k in range(8)]
px = 0.1; cv = Canvas(-AP-2, -AP-2, AP+2, AP+2, px)
outer = cv.arr(cv.poly(octo(AP))); inner = cv.arr(cv.poly(octo(AP-WT)))
starm = cv.arr(cv.poly(rsq(46, 2))) | cv.arr(cv.poly(rot(rsq(46, 2), math.pi/4)))
din = cv.din(starm)
sg = starm & (din <= 1.6)                                             # star outline
sg |= cv.arr(cv.poly(rot(rsq(14, 1), math.pi/4))) | cv.arr(cv.poly(rsq(14, 1)))
di = cv.din(inner); sg |= inner & (di >= 5) & (di <= 5.8)            # floor ring
rim = outer & ~inner
tray = np.concatenate([cv.boxes(outer, 0, FT), cv.boxes(rim, FT, TH-0.6), cv.boxes(rim & False, 0, 0)])
save('tabaq_bakke', tray); save('tabaq_guld', np.concatenate([cv.boxes(sg & inner, FT, FT+0.6), cv.boxes(rim, TH-0.6, TH)]))

for f in sorted(os.listdir(OUT)):
    if f.endswith('.stl'):
        t = np.fromfile(f'{OUT}/{f}', dtype=np.uint8)[84:].view(np.dtype([('n','<f4',3),('v','<f4',(3,3)),('a','<u2')]))['v'].astype(float)
        v = t.reshape(-1, 3); print(f, len(t), v.min(0).round(1), v.max(0).round(1))
