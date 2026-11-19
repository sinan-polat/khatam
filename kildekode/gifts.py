"""Four gift products (black / green / gold) for Bambu P2S. Units mm, parts in print orientation (Z up)."""
import os, math, json, base64
import numpy as np
src = open('/home/claude/products/products.py').read()
exec(src[:src.index('# ------------------------------------------------------------ A)')])   # Canvas, text, mesh helpers
OUT = '/home/claude/gifts/stl'; os.makedirs(OUT, exist_ok=True)
parts.clear()
GREEN, BLACK, GOLD = '#1f3a2e', '#262423', '#d8b25a'
REL = 0.6

def pointed(a, rise, n=60):
    c = (rise*rise - a*a)/(2*a); R = a + c; th1 = math.atan2(rise, -c); left = []
    for i in range(n+1):
        th = math.pi + (th1-math.pi)*i/n; left.append((c + R*math.cos(th), R*math.sin(th)))
    return left + [(-x, y) for x, y in reversed(left[:-1])]
def mihrab(W, rect_h, sh, rise):
    a = W/2 - sh; yb = rect_h + 1.5
    return clean([(-W/2, 0), (W/2, 0), (W/2, rect_h), (W/2-1.5, yb)] + [(x, y+yb) for x, y in reversed(pointed(a, rise))] + [(-W/2+1.5, yb), (-W/2, rect_h)])
def borders(cv, m, bands):
    d = cv.din(m); out = np.zeros_like(m)
    for a, b in bands: out |= m & (d >= a) & (d <= b)
    return out
def solid(cv, m, z0, z1, engrave=None, depth=0.6):
    """base from mask; optional engraving (recessed text) in the bottom `depth` mm (bed side)."""
    if engrave is None: return cv.boxes(m, z0, z1)
    return np.concatenate([cv.boxes(m & ~engrave, z0, z0+depth), cv.boxes(m, z0+depth, z1)])
def torus(cx, cy, cz, R, r, nu=40, nv=12):
    t = []
    P = lambda i, j: (cx + (R + r*math.cos(2*math.pi*j/nv))*math.cos(2*math.pi*i/nu), cy + (R + r*math.cos(2*math.pi*j/nv))*math.sin(2*math.pi*i/nu), cz + r*math.sin(2*math.pi*j/nv))
    for i in range(nu):
        for j in range(nv):
            a, b, c, d = P(i, j), P(i+1, j), P(i+1, j+1), P(i, j+1); t += [[a, b, c], [a, c, d]]
    return tri_arr(t)
def oct_pts(apo, rot=math.pi/8):
    R = apo/math.cos(math.pi/8); return [(R*math.cos(rot + k*math.pi/4), R*math.sin(rot + k*math.pi/4)) for k in range(8)]

# =========================================================== 1) BILOPHÆNG (car hanger)
HW, HRH, HSH, HRISE, HT_ = 48.0, 34.0, 7.0, 26.0, 3.0
SILH = mihrab(HW, HRH, HSH, HRISE); TOP = max(p[1] for p in SILH)
def hanger(name_ar, color, ox):
    cv = Canvas(-HW/2-1, -1, HW/2+1, TOP+10, 0.06)
    m = cv.arr(cv.poly(SILH)) | cv.arr(cv.circle(0, TOP+2.6, 5.0))
    hole = cv.arr(cv.circle(0, TOP+3.0, 2.0)); m &= ~hole
    sil = cv.arr(cv.poly(SILH))
    g = borders(cv, sil, [(1.3, 2.1), (2.9, 3.4)])
    cy = HRH + 1.5 + HRISE*0.40
    g |= cv.arr(cv.poly(star8_pts(0, cy, 3.8, 2.0))) & ~cv.arr(cv.circle(0, cy, 0.9))
    tm, _ = text_mask('بسم الله', HW-13, 13.0, cv.px, size_cap=13.0); g |= cv.place(tm, 0, 19.5)
    oy = 8.0
    g |= cv.arr(cv.poly([(-2.2, oy), (0, oy+1.6), (2.2, oy), (0, oy-1.6)]))
    for s in (-1, 1): g |= cv.arr(cv.poly([(s*3.2, oy-0.35), (s*11, oy-0.15), (s*11, oy+0.15), (s*3.2, oy+0.35)]))
    nm, _ = text_mask(name_ar, HW-16, 11.0, cv.px, size_cap=11.0)
    eng = cv.place(nm[:, ::-1], 0, 19.0) & sil                     # mirrored: reads correctly on the back
    base = solid(cv, m, 0, HT_, eng); gold = cv.boxes(g & sil, HT_, HT_+REL)
    key = 'groen' if color == GREEN else 'sort'
    add('bil', f'bil_{key}_plade', base, color, I3, (ox, 25, 0)); add('bil', f'bil_{key}_guld', gold, GOLD, I3, (ox, 25, 0))
hanger('يوسف', BLACK, -32); hanger('عمر', GREEN, 32)

# =========================================================== 2) GLASBRIKKER + HOLDER
CR, CT = 47.5, 4.0
def coaster(color, idx, M, t):
    cv = Canvas(-CR-1, -CR-1, CR+1, CR+1, 0.1)
    m = cv.arr(cv.circle(0, 0, CR))
    g = borders(cv, m, [(1.6, 2.7), (3.7, 4.3)])
    sq = lambda r, rot: [(math.cos(rot + k*math.pi/2)*r, math.sin(rot + k*math.pi/2)*r) for k in range(4)]
    so = cv.arr(cv.poly(sq(26, math.pi/4))) | cv.arr(cv.poly(sq(26, 0)))
    si = cv.arr(cv.poly(sq(24.3, math.pi/4))) | cv.arr(cv.poly(sq(24.3, 0)))
    g |= so & ~si
    g |= cv.arr(cv.circle(0, 0, 10.5)) & ~cv.arr(cv.circle(0, 0, 9.3))
    g |= cv.arr(cv.poly(star8_pts(0, 0, 6.2, 3.4))) & ~cv.arr(cv.circle(0, 0, 1.3))
    for k in range(8):
        a = math.pi/8 + k*math.pi/4
        g |= cv.arr(cv.circle(math.cos(a)*33.5, math.sin(a)*33.5, 1.5))
    felt = np.zeros_like(m)                                       # 4 shallow pockets for felt pads underneath
    for k in range(4):
        a = math.pi/4 + k*math.pi/2; felt |= cv.arr(cv.circle(math.cos(a)*36, math.sin(a)*36, 5.2))
    base = solid(cv, m, 0, CT, felt); gold = cv.boxes(g, CT, CT+REL)
    key = f'{"groen" if color == GREEN else "sort"}{idx}'
    add('brikker', f'brik_{key}_plade', base, color, M, t); add('brikker', f'brik_{key}_guld', gold, GOLD, M, t)

def holder():
    cv = Canvas(-55, -55, 55, 55, 0.12)
    disc = cv.arr(cv.circle(0, 0, 52.5))
    yy, xx = np.mgrid[0:cv.H, 0:cv.W]; X = cv.x0 + xx*cv.px; Y = cv.y0 + yy*cv.px
    ang = np.degrees(np.arctan2(Y, X)) % 360; r = np.hypot(X, Y)
    wall = (r >= 49.4) & (r <= 52.5) & ~((ang > 228) & (ang < 312))   # opening at the front (-Y)
    return np.concatenate([cv.boxes(disc, 0, 3.0), cv.boxes(wall, 3.0, 24.0)])
hb = holder()
add('brikker', 'brik_holder', hb, BLACK, RXM90, (-60, 0, 0))
for i in range(2):                                              # two coasters stacked in the holder
    coaster(BLACK if i == 0 else GREEN, i+1, RXM90, (-60, 3.0 + i*(CT+REL), 0))
for i, col in enumerate([BLACK, GREEN]):                        # two lying next to it
    coaster(col, i+3, RXM90, (55 + i*0, 0, -50 + i*100))

# =========================================================== 3) EIDIYYA-ÆSKE (octagon box + lid)
APO, WALL, BH = 36.0, 2.0, 45.0
def eid_box():
    cv = Canvas(-40, -40, 40, 40, 0.1)
    o = lambda a: cv.arr(cv.poly(oct_pts(a)))
    floor = o(APO); wall = o(APO) & ~o(APO-WALL)
    p = [cv.boxes(floor, 0, 2.0), cv.boxes(wall, 2.0, BH)]
    for z0, z1, a_in in [(38, 40, APO-WALL-0.5), (40, 42, APO-WALL-1.0), (42, BH+3.0, APO-WALL-2.0)]:   # stepped inner lip
        p.append(cv.boxes(o(APO-WALL) & ~o(a_in), z0, z1))
    return np.concatenate(p)
def eid_lid(name_ar):
    cv = Canvas(-40, -40, 40, 40, 0.07)
    o = lambda a: cv.arr(cv.poly(oct_pts(a)))
    top = o(APO); groove = o(APO-WALL+0.4) & ~o(APO-WALL-2.0-0.4)
    base = np.concatenate([cv.boxes(top & ~groove, 0, 3.4), cv.boxes(top, 3.4, 7.0)])
    g = borders(cv, top, [(1.5, 2.6), (3.6, 4.2)])
    g |= cv.arr(cv.poly(star8_pts(0, 20.5, 4.4, 2.4))) & ~cv.arr(cv.circle(0, 20.5, 1.0))
    tm, _ = text_mask(name_ar, 46, 17.0, cv.px, size_cap=17.0); g |= cv.place(tm, 0, 3.0)
    em, _ = text_mask('عيد مبارك', 30, 7.0, cv.px, size_cap=7.0); g |= cv.place(em, 0, -15.5)
    for s in (-1, 1): g |= cv.arr(cv.poly([(s*19, -15.5-1.2), (s*20.4, -15.5), (s*19, -15.5+1.2), (s*17.6, -15.5)]))
    return base, cv.boxes(g & top, 7.0, 7.0+REL)
add('aeske', 'aeske_boks', eid_box(), GREEN, RXM90, (-45, 0, 0))
lb, lg = eid_lid('سارة')
add('aeske', 'aeske_laag_plade', lb, BLACK, RXM90, (-45, BH, 0)); add('aeske', 'aeske_laag_guld', lg, GOLD, RXM90, (-45, BH, 0))
lb2, lg2 = eid_lid('آدم')
add('aeske', 'aeske_laag2_plade', lb2, BLACK, RXM90, (50, 0, 10)); add('aeske', 'aeske_laag2_guld', lg2, GOLD, RXM90, (50, 0, 10))

# =========================================================== 4) NØGLERING
KW, KH, KT = 54.0, 22.0, 3.2
def keyring(name_ar, name_lat, color, t):
    cv = Canvas(-KW/2-10, -KH/2-1, KW/2+1, KH/2+1, 0.05)
    rr = 4.0
    body = cv.arr(cv.poly([(-KW/2+rr, -KH/2), (KW/2-rr, -KH/2), (KW/2, -KH/2+rr), (KW/2, KH/2-rr), (KW/2-rr, KH/2), (-KW/2+rr, KH/2), (-KW/2, KH/2-rr), (-KW/2, -KH/2+rr)]))
    for sx in (-1, 1):
        for sy in (-1, 1): body |= cv.arr(cv.circle(sx*(KW/2-rr), sy*(KH/2-rr), rr))
    m = body | cv.arr(cv.circle(-KW/2-2.5, 0, 6.0)) | cv.arr(cv.poly([(-KW/2-2.5, -6), (-KW/2+2, -6), (-KW/2+2, 6), (-KW/2-2.5, 6)]))
    m &= ~cv.arr(cv.circle(-KW/2-3.0, 0, 2.6))
    g = borders(cv, body, [(1.2, 1.9), (2.6, 3.0)])
    g &= ~cv.arr(cv.circle(-KW/2-2.5, 0, 7.5))
    g |= cv.arr(cv.poly(star8_pts(-KW/2+8.5, 0, 3.0, 1.6))) & ~cv.arr(cv.circle(-KW/2+8.5, 0, 0.7))
    tm, _ = text_mask(name_ar, 33, 13.0, cv.px, size_cap=13.0); g |= cv.place(tm, 5.0, 0.4)
    lm = latin_mask(name_lat, 34, 4.2, cv.px, tracking=0.3)
    eng = cv.place(lm[:, ::-1], 2.0, 0) & body                          # Latin name engraved on the back
    base = solid(cv, m, 0, KT, eng); gold = cv.boxes(g & body, KT, KT+REL)
    key = 'groen' if color == GREEN else 'sort'
    add('noegle', f'noegle_{key}_plade', base, color, RXM90, t); add('noegle', f'noegle_{key}_guld', gold, GOLD, RXM90, t)
    ring = torus(-KW/2-3.0-9.0, KT/2, 0, 9.0, 0.9)[:, :, [0, 2, 1]][:, ::-1, :]   # vertical ring through the hole
    add('noegle', f'noegle_{key}_ring_visning', ring, '#b9b4ab', RXM90, t, role='kun visning')
keyring('يوسف', 'YUSUF', BLACK, (0, 0, -22)); keyring('عمر', 'OMAR', GREEN, (0, 0, 22))

# =========================================================== estimates + export
RHO = 1.24
def grams(p):
    V = p['vol']/1000; A = p['area']/100; sh = min(V, A*0.1); return RHO*(sh + max(0, V-sh)*0.15)
for p in parts: p['g'] = round(grams(p), 2)
import hashlib
geo_by_prod = {}; seen = {}
for p in parts:
    raw = open(f"{OUT}/{p['file']}", 'rb').read(); h = hashlib.sha1(raw).hexdigest()
    if h not in seen:
        seen[h] = p['name']; geo_by_prod.setdefault(p['product'], {})[p['name']] = base64.b64encode(raw).decode()
    p['geo'] = seen[h]; p['geofile'] = [k for k, v in geo_by_prod.items() if seen[h] in v][0]
json.dump(dict(parts=parts), open(f'{OUT}/manifest.json', 'w'), ensure_ascii=False, indent=1)
for k, v in geo_by_prod.items():
    json.dump(v, open(f'{OUT}/geo_{k}.json', 'w')); print(k, round(os.path.getsize(f'{OUT}/geo_{k}.json')/1e6, 1), 'MB')
