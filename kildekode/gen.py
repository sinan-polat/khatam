"""Printable mini-model of the Islamic niche bookcase, for Bambu Lab P2S (256 mm cube).
All units mm. Every part is written in its print orientation (Z up, on the bed at Z=0),
plus a manifest with the transform that puts it into the assembled model (Y up, three.js).
"""
import json, math, os, struct
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUT = os.path.join(os.path.dirname(__file__), 'stl')
os.makedirs(OUT, exist_ok=True)
U = 70.0                       # mm per design unit  -> model ~19 x 24 x 7.4 cm
HS = 1.6 * U                   # springing height of the arch
IA, IR = 0.75 * U, 1.0 * U     # opening half width / rise
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'

# ---------------------------------------------------------------- mesh basics
def tri_arr(lst):
    return np.array(lst, dtype=np.float64).reshape(-1, 3, 3) if len(lst) else np.zeros((0, 3, 3))

def box(x0, y0, z0, x1, y1, z1):
    v = np.array([[x0,y0,z0],[x1,y0,z0],[x1,y1,z0],[x0,y1,z0],[x0,y0,z1],[x1,y0,z1],[x1,y1,z1],[x0,y1,z1]])
    f = [(0,2,1),(0,3,2),(4,5,6),(4,6,7),(0,1,5),(0,5,4),(2,3,7),(2,7,6),(1,2,6),(1,6,5),(3,0,4),(3,4,7)]
    return v[np.array(f)]

def area2(p):
    p = np.asarray(p); x, y = p[:,0], p[:,1]
    return float(np.sum(x*np.roll(y,-1) - np.roll(x,-1)*y))

def clean(poly, eps=1e-6):
    out = []
    for p in poly:
        if not out or (abs(p[0]-out[-1][0]) > eps or abs(p[1]-out[-1][1]) > eps):
            out.append((float(p[0]), float(p[1])))
    if len(out) > 1 and abs(out[0][0]-out[-1][0]) < eps and abs(out[0][1]-out[-1][1]) < eps:
        out.pop()
    # drop collinear points
    res = []
    n = len(out)
    for i in range(n):
        a, b, c = out[i-1], out[i], out[(i+1) % n]
        cr = (b[0]-a[0])*(c[1]-b[1]) - (b[1]-a[1])*(c[0]-b[0])
        if abs(cr) > 1e-9:
            res.append(b)
    return res

def earclip(poly):
    """poly: CCW simple polygon -> list of index triples"""
    n = len(poly); idx = list(range(n)); tris = []
    P = poly
    def cross(o, a, b): return (a[0]-o[0])*(b[1]-o[1]) - (a[1]-o[1])*(b[0]-o[0])
    def inside(p, a, b, c):
        return cross(a,b,p) >= -1e-12 and cross(b,c,p) >= -1e-12 and cross(c,a,p) >= -1e-12
    guard = 0
    while len(idx) > 3 and guard < 100000:
        guard += 1
        m = len(idx); cut = False
        for k in range(m):
            i0, i1, i2 = idx[k-1], idx[k], idx[(k+1) % m]
            a, b, c = P[i0], P[i1], P[i2]
            if cross(a, b, c) <= 1e-12: continue
            ok = True
            for j in idx:
                if j in (i0, i1, i2): continue
                q = P[j]
                if q == a or q == b or q == c: continue
                if inside(q, a, b, c): ok = False; break
            if ok:
                tris.append((i0, i1, i2)); idx.pop(k); cut = True; break
        if not cut:  # degenerate: force
            tris.append((idx[-1], idx[0], idx[1])); idx.pop(0)
    if len(idx) == 3: tris.append(tuple(idx))
    return tris

def loft(pb, pt, z0, z1):
    """prism between bottom polygon pb (z0) and top polygon pt (z1), same vertex count, CCW"""
    pb = list(pb); pt = list(pt)
    if area2(pb) < 0: pb = pb[::-1]; pt = pt[::-1]
    t = []
    for (i, j, k) in earclip(pb):
        t.append([(*pb[i], z0), (*pb[k], z0), (*pb[j], z0)])
    for (i, j, k) in earclip(pt):
        t.append([(*pt[i], z1), (*pt[j], z1), (*pt[k], z1)])
    n = len(pb)
    for i in range(n):
        a0 = (*pb[i], z0); b0 = (*pb[(i+1) % n], z0); a1 = (*pt[i], z1); b1 = (*pt[(i+1) % n], z1)
        t += [[a0, b0, b1], [a0, b1, a1]]
    return tri_arr(t)

def extrude(poly, z0, z1):
    poly = clean(poly)
    return loft(poly, poly, z0, z1)

def lathe(profile, segs=8, rot=math.pi/8):
    """profile: list of (r, z) bottom->top; first r>0 (capped), last may be r=0 (apex)"""
    t = []
    rings = []
    for r, z in profile:
        rings.append([(r*math.cos(rot+2*math.pi*s/segs), r*math.sin(rot+2*math.pi*s/segs), z) for s in range(segs)])
    # bottom cap
    c = (0, 0, profile[0][1])
    for s in range(segs):
        t.append([c, rings[0][(s+1) % segs], rings[0][s]])
    for k in range(len(rings)-1):
        A, B = rings[k], rings[k+1]
        for s in range(segs):
            a0, a1, b0, b1 = A[s], A[(s+1) % segs], B[s], B[(s+1) % segs]
            if profile[k+1][0] == 0:
                t.append([a0, a1, b0])
            else:
                t += [[a0, a1, b1], [a0, b1, b0]]
    if profile[-1][0] != 0:
        c = (0, 0, profile[-1][1])
        for s in range(segs):
            t.append([c, rings[-1][s], rings[-1][(s+1) % segs]])
    return tri_arr(t)

def uvsphere(cx, cy, cz, r, nu=16, nv=10):
    t = []
    def P(i, j):
        th = math.pi*i/nv; ph = 2*math.pi*j/nu
        return (cx + r*math.sin(th)*math.cos(ph), cy + r*math.sin(th)*math.sin(ph), cz - r*math.cos(th))
    for i in range(nv):
        for j in range(nu):
            a, b, c, d = P(i, j), P(i, j+1), P(i+1, j+1), P(i+1, j)
            if i == 0: t.append([a, c, d])
            elif i == nv-1: t.append([a, b, d])
            else: t += [[a, b, c], [a, c, d]]
    return tri_arr(t)

def raster_boxes(mask, px, x0, y0, z0, z1):
    """mask[row, col] with row 0 at y0 (y grows with row). Greedy merge of identical runs."""
    H, W = mask.shape
    rects = []; active = {}
    for r in range(H + 1):
        runs = set()
        if r < H:
            row = mask[r]
            if row.any():
                d = np.diff(np.concatenate([[0], row.astype(np.int8), [0]]))
                s = np.where(d == 1)[0]; e = np.where(d == -1)[0]
                runs = set(zip(s.tolist(), e.tolist()))
        for key in list(active):
            if key not in runs:
                rects.append((key[0], key[1], active.pop(key), r))
        for key in runs:
            if key not in active: active[key] = r
    out = [box(x0+s*px, y0+r0*px, z0, x0+e*px, y0+r1*px, z1) for s, e, r0, r1 in rects]
    return np.concatenate(out) if out else np.zeros((0, 3, 3)), len(rects)

def write_stl(path, tris):
    tris = np.asarray(tris, dtype=np.float32)
    n = np.cross(tris[:,1]-tris[:,0], tris[:,2]-tris[:,0])
    ln = np.linalg.norm(n, axis=1, keepdims=True); ln[ln == 0] = 1; n = (n/ln).astype(np.float32)
    rec = np.zeros(len(tris), dtype=[('n','<f4',3),('v','<f4',(3,3)),('a','<u2')])
    rec['n'] = n; rec['v'] = tris
    with open(path, 'wb') as f:
        f.write(b'Islamic niche mini model'.ljust(80, b' ')); f.write(struct.pack('<I', len(tris))); f.write(rec.tobytes())

def volume(tris):
    t = np.asarray(tris)
    return float(np.sum(np.einsum('ij,ij->i', t[:,0], np.cross(t[:,1], t[:,2]))) / 6.0)

def surface(tris):
    t = np.asarray(tris)
    return float(np.sum(np.linalg.norm(np.cross(t[:,1]-t[:,0], t[:,2]-t[:,0]), axis=1)) / 2.0)

# ---------------------------------------------------------------- 2D shapes
def arch_pts(a, rise, n=72, scallop=0.0, bumps=7):
    c = (rise*rise - a*a) / (2*a); R = a + c; th1 = math.atan2(rise, -c); left = []
    for i in range(n+1):
        th = math.pi + (th1 - math.pi)*i/n
        x = c + R*math.cos(th); y = R*math.sin(th)
        if scallop:
            k = abs(math.sin(i/n*math.pi*bumps))**0.7
            x += math.cos(th)*scallop*k; y += math.sin(th)*scallop*k
        left.append((x, y))
    return left + [(-x, y) for x, y in reversed(left[:-1])]

def arch_poly(a, rise, bottom, scallop=0.0, bumps=7):
    pts = [(-a, bottom)] + [(x, y+HS) for x, y in arch_pts(a, rise, scallop=scallop, bumps=bumps)] + [(a, bottom)]
    return clean(pts)

def u_poly(oa, orise, ia, irise, bottom, scallop=0.0, bumps=7, ibottom=None):
    ib = bottom if ibottom is None else ibottom
    outer = [(-oa, bottom)] + [(x, y+HS) for x, y in arch_pts(oa, orise, scallop=scallop, bumps=bumps)] + [(oa, bottom)]
    inner = [(ia, ib)] + [(x, y+HS) for x, y in reversed(arch_pts(ia, irise))] + [(-ia, ib)]
    return clean(outer + inner)

def to_px(poly, px, x0, y0):
    return [((x-x0)/px, (y-y0)/px) for x, y in poly]

def star_lines(draw, x0, y0, w, h, cell, px, ox, oy, width, octagon=False):
    """draw khatam tiling into a PIL image whose pixel (0,0) is world (ox, oy); y up = row up."""
    def P(x, y): return ((x-ox)/px, (y-oy)/px)
    nx = int(w/cell)+2; ny = int(h/cell)+2
    for i in range(-1, nx):
        for j in range(-1, ny):
            cx = x0 + (i+.5)*cell; cy = y0 + (j+.5)*cell
            R = cell*0.36; r = R*0.62
            pts = [P(cx+math.cos(k*math.pi/8)*(R if k % 2 == 0 else r), cy+math.sin(k*math.pi/8)*(R if k % 2 == 0 else r)) for k in range(16)]
            draw.line(pts + [pts[0]], fill=255, width=width, joint='curve')
            if octagon:
                o = [P(cx+math.cos(k*math.pi/4+math.pi/8)*r*.72, cy+math.sin(k*math.pi/4+math.pi/8)*r*.72) for k in range(8)]
                draw.line(o + [o[0]], fill=255, width=width, joint='curve')
            for k in range(8):
                a = k*math.pi/4; reach = cell/2 if k % 2 == 0 else cell/2*math.sqrt(2)
                draw.line([P(cx+math.cos(a)*R, cy+math.sin(a)*R), P(cx+math.cos(a)*reach, cy+math.sin(a)*reach)], fill=255, width=width)

def text_mask(text, max_w, max_h, px, size_cap=None):
    """returns bool mask (row 0 = bottom) of Arabic text fitted into max_w x max_h mm"""
    size_mm = max_h if size_cap is None else min(max_h, size_cap)
    while True:
        fpx = max(8, int(size_mm/px))
        font = ImageFont.truetype(FONT, fpx, layout_engine=ImageFont.Layout.RAQM)
        bb = font.getbbox(text, direction='rtl', language='ar')
        tw, th = (bb[2]-bb[0])*px, (bb[3]-bb[1])*px
        if (tw <= max_w and th <= max_h) or size_mm < 1.5: break
        size_mm *= 0.94
    W = int(math.ceil(max_w/px)); H = int(math.ceil(max_h/px))
    img = Image.new('L', (W, H), 0); d = ImageDraw.Draw(img)
    d.text((W/2 - (bb[0]+bb[2])/2, H/2 - (bb[1]+bb[3])/2), text, font=font, fill=255, direction='rtl', language='ar')
    return np.flipud(np.array(img) > 127), (tw, th)

# ---------------------------------------------------------------- parts
parts = []   # dicts: name, file, tris, color, material, group, M (3x3), t (3), explode
def add(name, tris, color, material, plate, M, t, explode, note=''):
    tris = np.concatenate(tris) if isinstance(tris, list) else tris
    fn = name + '.stl'
    write_stl(os.path.join(OUT, fn), tris)
    mn, mx = tris.reshape(-1, 3).min(0), tris.reshape(-1, 3).max(0)
    parts.append(dict(name=name, file=fn, color=color, material=material, plate=plate, M=np.asarray(M, float).tolist(),
                      t=list(map(float, t)), explode=list(map(float, explode)), tris=len(tris),
                      vol=volume(tris), area=surface(tris), size=(mx-mn).round(1).tolist(), note=note))
    print(f'{name:22s} {len(tris):7d} tris  size {np.round(mx-mn,1)}  vol {volume(tris)/1000:.1f} cm3')

I3 = np.eye(3)
RX_M90 = [[1,0,0],[0,0,1],[0,-1,0]]     # print Z-up -> assembly Y-up  (x, z, -y)
RX_180 = [[1,0,0],[0,-1,0],[0,0,-1]]
BACK_Z = -0.4*U                          # assembly z of the korpus back

# 1) KORPUS + RAMME  (printed lying on its back, front relief up)
DEPTH = 0.65*U; FT = 0.06*U; FLOOR = 0.06*U
korpus = [
    extrude(u_poly(1.0*U, 1.3*U, IA, IR, FLOOR), 0, DEPTH),
    box(-1.0*U, 0, 0, 1.0*U, FLOOR, DEPTH),
    extrude(u_poly(1.06*U, 1.36*U, IA, IR, 0, scallop=0.045*U, bumps=9), DEPTH, DEPTH+FT),
    extrude(u_poly(IA+0.07*U, IR+0.075*U, IA, IR, FLOOR), DEPTH+FT, DEPTH+FT+2.2),
]
ZF = DEPTH + FT            # front face of carved frame
PX = 0.93*U; PW = 14.0
for sx in (-1, 1):
    cx = sx*PX
    korpus.append(box(cx-PW/2-0.5, 0, ZF, cx+PW/2+0.5, 6.0, ZF+3.2))           # base
    korpus.append(box(cx-PW/2+0.8, 6.0, ZF, cx+PW/2-0.8, 8.0, ZF+2.4))           # base fillet
    for k in range(4):                                                             # 4 flutes (cluster column)
        fx = cx + (k-1.5)*3.3
        korpus.append(box(fx-1.1, 8.0, ZF, fx+1.1, HS-6.5, ZF+2.0))
    korpus.append(box(cx-PW/2, HS-6.5, ZF, cx+PW/2, HS-2.0, ZF+2.6))              # capital
    korpus.append(box(cx-PW/2-1.0, HS-2.0, ZF, cx+PW/2+1.0, HS+0.5, ZF+3.2))     # abacus
add('01_korpus_ramme', korpus, '#c9a679', 'PLA Wood / PLA Basic (træfarve)', 'A', I3, (0, 0, BACK_Z), (0, 0, 0))

# 1b) star relief on the frame (separate part -> same filament or gold)
px = 0.2
fx0, fy0 = -1.12*U, 0.0
fw, fh = 2.24*U, HS + 1.42*U
Wp, Hp = int(fw/px), int(fh/px)
m_frame = Image.new('L', (Wp, Hp), 0); d = ImageDraw.Draw(m_frame)
d.polygon(to_px(u_poly(1.06*U, 1.36*U, IA, IR, 0, scallop=0.045*U, bumps=9), px, fx0, fy0), fill=255)
m_frame = m_frame.filter(ImageFilter.MinFilter(13))            # 1.2 mm margin from all edges
d = ImageDraw.Draw(m_frame)
d.polygon(to_px(arch_poly(IA+0.07*U+1.5, IR+0.075*U+1.5, -5), px, fx0, fy0), fill=0)   # keep clear of moulding
for sx in (-1, 1):
    cx = sx*PX
    d.rectangle([((cx-PW/2-2)-fx0)/px, 0, ((cx+PW/2+2)-fx0)/px, (HS+2-fy0)/px], fill=0)
m_star = Image.new('L', (Wp, Hp), 0)
star_lines(ImageDraw.Draw(m_star), fx0, fy0, fw, fh, 13.0, px, fx0, fy0, width=int(0.9/px))
mask = (np.array(m_frame) > 127) & (np.array(m_star) > 127)
rel, nrect = raster_boxes(mask, px, fx0, fy0, ZF, ZF+0.8)
add('01b_ramme_stjernerelief', rel, '#d8b25a', 'PLA Silk+ Guld (eller samme træfarve)', 'A', I3, (0, 0, BACK_Z), (0, 0, 0),
    note='Indlæs sammen med 01 som ét objekt med to dele')

# 2) MASHRABIYA back panel (flat, thin translucent base + lattice)
pa, pr = IA + 4.0, IR + 4.0
outline = arch_poly(pa, pr, 0)
mash = [extrude(outline, 0, 0.6)]
px = 0.2
mx0, my0 = -pa-1, -1
mw, mh = 2*pa+2, HS+pr+2
Wp, Hp = int(mw/px), int(mh/px)
m_in = Image.new('L', (Wp, Hp), 0); d = ImageDraw.Draw(m_in); d.polygon(to_px(outline, px, mx0, my0), fill=255)
m_rim = m_in.filter(ImageFilter.MinFilter(int(3.0/px)*2+1))
lat = Image.new('L', (Wp, Hp), 0)
star_lines(ImageDraw.Draw(lat), -pa, 0, 2*pa, HS+pr, 17.0, px, mx0, my0, width=int(1.8/px), octagon=True)
a_in, a_rim, a_lat = np.array(m_in) > 127, np.array(m_rim) > 127, np.array(lat) > 127
mask = a_in & (~a_rim | a_lat)
rib, _ = raster_boxes(mask, px, mx0, my0, 0.6, 2.4)
mash.append(rib)
add('02_mashrabiya_bagplade', mash, '#f2eadb', 'PLA Basic Hvid (lyser igennem)', 'B', I3, (0, 0, BACK_Z-2.4), (0, 0, -70))

# 3) SOKKEL (upright) + top/foot lips with 45° chamfer
PLW, PLD, PLH = 2.62*U, 1.0*U, 0.25*U
def rect(w, d): return [(-w/2, -d/2), (w/2, -d/2), (w/2, d/2), (-w/2, d/2)]
sok = [
    loft(rect(PLW+5, PLD+5), rect(PLW, PLD), 0, 2.5),          # foot chamfer
    extrude(rect(PLW, PLD), 2.5, PLH-2.5),
    loft(rect(PLW, PLD), rect(PLW+5, PLD+5), PLH-2.5, PLH),     # top chamfer (45°, no support)
]
add('03_sokkel', sok, '#b98e5c', 'PLA Wood / PLA Basic (træfarve)', 'C', RX_M90, (0, -PLH, -0.05*U), (0, -45, 0))

# 3b) Bismillah plaque (green base + gold text/rim) – printed flat
PQW, PQH = 128.0, 11.0
px = 0.1
plaque_base = extrude(rect(PQW, PQH), 0, 1.2)
Wp, Hp = int(PQW/px), int(PQH/px)
rim = np.zeros((Hp, Wp), bool); b = int(0.7/px)
rim[:b, :] = rim[-b:, :] = True; rim[:, :b] = rim[:, -b:] = True
tm, tsz = text_mask('بسم الله الرحمن الرحيم', PQW-14, PQH-3.2, px)
tmask = np.zeros((Hp, Wp), bool)
oy, ox = (Hp - tm.shape[0])//2, (Wp - tm.shape[1])//2
tmask[oy:oy+tm.shape[0], ox:ox+tm.shape[1]] = tm
for cx in (-PQW/2+4.2, PQW/2-4.2):                                   # small diamonds
    for r in range(Hp):
        for c in range(int((cx-2.4+PQW/2)/px), int((cx+2.4+PQW/2)/px)):
            xm = c*px - PQW/2 - cx; ym = r*px - PQH/2
            if abs(xm) + abs(ym) < 2.2: tmask[r, c] = True
gold, _ = raster_boxes(rim | tmask, px, -PQW/2, -PQH/2, 1.2, 1.8)
add('03b_plakette_base', plaque_base, '#1f3a2e', 'PLA Basic Mørkegrøn', 'E', I3, (0, -PLH/2, -0.05*U + PLD/2), (0, -45, 40))
add('03c_plakette_guldtekst', gold, '#d8b25a', 'PLA Silk+ Guld', 'E', I3, (0, -PLH/2, -0.05*U + PLD/2), (0, -45, 40),
    note=f'Tekst ca. {tsz[0]:.0f} x {tsz[1]:.1f} mm')

# 4) HYLDER + sidepaneler (flat boards)
SH1, SH2, SH3 = 0.48*U, 0.90*U, 1.32*U
ST, SD = 2.1, 35.0
ZC = -0.14*U
shelf_w_full = 2*IA - 0.6
side_x_in = 0.31*U + 0.875 + 0.2
side_w = IA - side_x_in - 0.3
for name, w, x, y in [('04a_hylde_top', shelf_w_full, 0, SH3), ('04b_hylde_midt', shelf_w_full, 0, SH2),
                      ('04c_hylde_venstre', side_w, -(side_x_in + side_w/2), SH1), ('04d_hylde_hoejre', side_w, side_x_in + side_w/2, SH1)]:
    tr = [box(-w/2, -SD/2, 0, w/2, SD/2, ST), box(-w/2, -SD/2-1.2, 0, w/2, -SD/2, ST+0.6)]   # board + front lip (lip at -Y -> front)
    add(name, tr, '#c9a679', 'PLA Wood / PLA Basic (træfarve)', 'C', RX_M90, (x, y - ST, ZC), (0, 0, 60 + 15*(y/U)))
PH = SH2 - ST - FLOOR
for sx, nm in ((-1, '04e_sidepanel_venstre'), (1, '04f_sidepanel_hoejre')):
    tr = box(0, -SD/2, 0, PH, SD/2, 1.75)
    M = [[0,0,1],[1,0,0],[0,1,0]]
    add(nm, tr, '#c9a679', 'PLA Wood / PLA Basic (træfarve)', 'C', M, (sx*0.31*U - 0.875, FLOOR, ZC), (sx*20, 0, 55))

# 5) BOGBLOKKE – each set one block, printed spine-up; gold relief as separate part
SETS = [  # key, title, n, spine mm, colour, row, side
    ('tabari', 'تفسير الطبري', 20, 2.6, '#1a1714', 3),
    ('fath', 'فتح الباري', 15, 3.1, '#173a2c', 3),
    ('fatawa', 'مجموع الفتاوى', 20, 2.4, '#4a1418', 2),
    ('kathir', 'تفسير ابن كثير', 8, 3.2, '#1a1714', 2),
    ('masir', 'زاد المسير', 4, 3.5, '#4a1418', 2),
    ('muwatta', 'الموطأ', 2, 3.5, '#4a1418', 2),
    ('sitta', 'الكتب الستة', 6, 3.6, '#1a1714', 1),
    ('riyad', 'رياض الصالحين', 1, 4.2, '#173a2c', 1),
    ('badai', 'بدائع التفسير', 3, 3.5, '#4a1418', 1),
    ('zadmaad', 'زاد المعاد', 5, 3.2, '#173a2c', 1),
]
BH, BD = 0.28*U, 0.2*U          # book height 19.6, depth 14
GROOVE, GDEP, RELIEF = 0.45, 0.8, 0.5
rows = {3: (['tabari', 'fath'], SH3, -IA+0.6, IA-0.6), 2: (['fatawa', 'kathir', 'masir', 'muwatta'], SH2, -IA+0.6, IA-0.6),
        '1L': (['sitta', 'riyad'], SH1, -IA+0.5, -side_x_in-0.3), '1R': (['badai', 'zadmaad'], SH1, side_x_in+0.3, IA-0.5)}
byk = {s[0]: s for s in SETS}
book_info = []
for rk, (keys, y, xa, xb) in rows.items():
    total = sum(byk[k][2]*byk[k][3] for k in keys) + 1.5*(len(keys)-1)
    x = xa + max(0, (xb - xa - total)/2)
    for k in keys:
        _, title, n, sw, col, _ = byk[k]
        W = n*sw
        base = [box(0, 0, 0, W, BH, BD - GDEP)]
        for i in range(n):
            base.append(box(i*sw + GROOVE/2, 0, BD-GDEP, (i+1)*sw - GROOVE/2, BH, BD))
        # gold relief mask on the spine face (X = width, Y = book height)
        px = 0.1
        Wp, Hp = int(round(W/px)), int(round(BH/px))
        gm = np.zeros((Hp, Wp), bool)
        def band(y0, y1): gm[int(y0/px):int(y1/px), :] = True
        band(1.2, 1.9); band(2.5, 2.9); band(BH-1.9, BH-1.2); band(BH-2.9, BH-2.5)     # head & tail bands
        if n >= 3:
            band(5.0, 5.4); band(14.4, 14.8)                                               # cartouche lines
            tm, _ = text_mask(title, W - 2.0, 8.0, px)
            oy = int((9.9)/px) - tm.shape[0]//2; ox = (Wp - tm.shape[1])//2
            gm[oy:oy+tm.shape[0], ox:ox+tm.shape[1]] |= tm
        else:
            for i in range(n):                                                              # diamond per spine
                cx, cy = (i+.5)*sw, BH*0.62
                for r in range(int((cy-1.6)/px), int((cy+1.6)/px)):
                    for c in range(int((cx-1.6)/px), int((cx+1.6)/px)):
                        if abs(c*px-cx) + abs(r*px-cy) < 1.3 and abs(c*px-cx) + abs(r*px-cy) > 0.55: gm[r, c] = True
        # cut relief at grooves so each volume keeps its own slice
        for i in range(n+1):
            c0 = int((i*sw - GROOVE/2)/px); c1 = int((i*sw + GROOVE/2)/px) + 1
            gm[:, max(0, c0):max(0, min(Wp, c1))] = False
        gold, _ = raster_boxes(gm, px, 0, 0, BD, BD + RELIEF)
        t = (x, y, 0.112*U - 1.5 - BD)
        pl = {'#1a1714': 'D1', '#173a2c': 'D2', '#4a1418': 'D3'}[col]
        cname = {'D1': 'Sort', 'D2': 'Mørkegrøn', 'D3': 'Bordeaux'}[pl]
        add(f'05_bog_{k}_base', base, col, f'PLA Basic {cname}', pl, I3, t, (0, 0, 95))
        add(f'05_bog_{k}_guld', gold, '#d8b25a', 'PLA Silk+ Guld', pl, I3, t, (0, 0, 95))
        book_info.append(dict(key=k, title=title, n=n, width=round(W, 1)))
        x += W + 1.5

# 6) BÆNK (printed upside down), REHAL + KORAN (printed lying on the side)
bench = [box(-17.5, -11.9, 0, 17.5, 11.9, 2.45), box(-16.1, -10.5, 2.45, 16.1, 10.5, 5.25)]
for sx in (-1, 1):
    for sz in (-1, 1):
        bench.append(box(sx*14.7-1.4, sz*9.1-1.4, 2.45, sx*14.7+1.4, sz*9.1+1.4, 2.45+10.5))
BENCH_H = 2.45 + 10.5
add('06_baenk', bench, '#b98e5c', 'PLA Wood / PLA Basic (træfarve)', 'C', RX_180, (0, FLOOR + BENCH_H, -0.04*U), (0, 0, 70))

A = 0.72; L = 0.36*U; BT = 2.0; DEP = 14.0
def board_poly(sgn, length, thick, off_along=0.0, off_norm=0.0):
    d = (-sgn*math.sin(A), math.cos(A)); nrm = (sgn*math.cos(A), math.sin(A))
    c = (d[0]*off_along + nrm[0]*off_norm, d[1]*off_along + nrm[1]*off_norm)
    p = []
    for a, b in ((-length/2, -thick/2), (length/2, -thick/2), (length/2, thick/2), (-length/2, thick/2)):
        # local: along d by a, along perpendicular (cos, sin rotated) by b
        px_ = c[0] + d[0]*a + d[1]*b; py_ = c[1] + d[1]*a - d[0]*b
        p.append((px_, py_))
    if area2(p) < 0: p = p[::-1]
    return p
rehal = [extrude(board_poly(s, L, BT), 0, DEP) for s in (-1, 1)]
pages = []
for s in (-1, 1):
    rehal.append(extrude(board_poly(s, 0.165*U, 1.0, 0.095*U, BT/2 + 0.5), 0, DEP))               # cover
    pages.append(extrude(board_poly(s, 0.155*U, 1.4, 0.093*U, BT/2 + 1.0 + 0.7), 0.5, DEP-0.5))  # page block
REHAL_Y = FLOOR + BENCH_H + math.cos(A)*L/2
add('07_rehal', rehal, '#d8b25a', 'PLA Silk+ Guld (eller træfarve)', 'F', I3, (0, REHAL_Y, -0.04*U - DEP/2), (0, 25, 85))
add('07b_koran_sider', pages, '#efe3c8', 'PLA Basic Hvid', 'B', I3, (0, REHAL_Y, -0.04*U - DEP/2), (0, 25, 85))

# 7) LANTERNE (upright) with hanging rod
prof = [(0.03,0),(0.05,0.025),(0.068,0.07),(0.074,0.11),(0.062,0.155),(0.04,0.19),(0.022,0.22),(0.012,0.25),(0.0,0.27)]
lan = [lathe([(r*U, z*U) for r, z in prof], 8)]
LTOP = 0.27*U
lan.append(lathe([(1.1, LTOP-3), (1.1, LTOP+14.5), (0.0, LTOP+15.0)], 8))
lan.append(uvsphere(0, 0, LTOP-0.6, 1.6))
LAN_Y = HS + IR - 0.48*U
add('08_lanterne', lan, '#d8b25a', 'PLA Silk+ Guld', 'F', RX_M90, (0, LAN_Y, -0.05*U), (0, 35, 40))

# 8) FINIAL (upright): base, sphere, rod, crescent
fin = [lathe([(4.9, 0), (3.6, 2.8), (2.2, 3.4)], 16)]
fin.append(uvsphere(0, 0, 3.4 + 3.6, 3.85))
fin.append(lathe([(1.0, 9.8), (1.0, 16.0), (0.0, 16.4)], 8))
outer = [(4.0*math.cos(math.radians(a)), 4.0*math.sin(math.radians(a))) for a in np.linspace(50, 310, 40)]
P = outer[0]; cxm = 1.5; rin = math.hypot(P[0]-cxm, P[1]); a0 = math.degrees(math.atan2(P[1], P[0]-cxm))
inner = [(cxm + rin*math.cos(math.radians(a)), rin*math.sin(math.radians(a))) for a in np.linspace(360-a0, a0, 40)][1:-1]
cres = clean(outer + inner)
cr = extrude(cres, -0.9, 0.9)                         # in XY, thickness along Z
cr = cr[:, :, [0, 2, 1]]                              # rotate into XZ plane (stand upright)
cr = cr[:, :, :] ; cr[:, :, 2] += 16.0 + 3.2          # lift onto rod
cr = cr[:, :, :]
# swapping y/z mirrors the mesh -> fix winding
cr = cr[:, ::-1, :]
fin.append(cr)
add('09_finial_halvmaane', fin, '#d8b25a', 'PLA Silk+ Guld', 'F', RX_M90, (0, HS + 1.3*U - 1.0, -0.08*U), (0, 45, 0))

json.dump(dict(unit_mm=U, parts=parts, books=book_info), open(os.path.join(OUT, 'manifest.json'), 'w'), indent=1, ensure_ascii=False)
print('total tris', sum(p['tris'] for p in parts))
