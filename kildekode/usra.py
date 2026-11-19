"""USRA (أسرة) – islamisk tandbørsteholder til familien. Arkade med 4 spidsbuer, 4 rum, navne i guld på toppen,
separat drypbakke. Units mm, print orientation Z up."""
import os, math, json, struct
import numpy as np
src = open('/home/claude/products/products.py').read()
exec(src[:src.index('parts = []')])
OUT = '/home/claude/usra/stl'; os.makedirs(OUT, exist_ok=True)
L, Dp, H, WT = 150.0, 58.0, 100.0, 3.0     # length (x), depth (y), height (z), wall
TOP = 6.0; N = 4; CW = L/N
NAMES = [('يوسف','YUSUF'),('مريم','MARYAM'),('آدم','ADAM'),('سارة','SARA')]

def pointed(a, rise, n=50):
    c = (rise*rise - a*a)/(2*a); R = a + c; th1 = math.atan2(rise, -c); left = []
    for i in range(n+1):
        th = math.pi + (th1-math.pi)*i/n; left.append((c + R*math.cos(th), R*math.sin(th)))
    return left + [(-x, y) for x, y in reversed(left[:-1])]

def wall_mask(arches=True, side=False):
    w = Dp if side else L
    cv = Canvas(-w/2, 0, w/2, H-TOP, 0.1)
    m = np.ones((cv.H, cv.W), bool)
    if arches:
        centers = [0.0] if side else [(-L/2 + CW*(i+0.5)) for i in range(N)]
        aw = 22.0 if side else CW-10.0; spring = 60.0 if side else 62.0
        for cx in centers:
            pts = [(cx-aw/2, 12)] + [(cx+x, spring+y) for x, y in pointed(aw/2, aw/2*1.55)] + [(cx+aw/2, 12)]
            # pointed() runs left->right over the top; build closed polygon: bottom-left, up, arch, down, bottom-right
            poly = [(cx-aw/2, 12), (cx-aw/2, spring)] + [(cx+x, spring+y) for x, y in pointed(aw/2, aw/2*1.55)][1:-1] + [(cx+aw/2, spring), (cx+aw/2, 12)]
            m &= ~cv.arr(cv.poly(poly))
    return cv, m

def wall_tris(cv, m, axis_y0, axis_y1, along='x'):
    b = cv.boxes(m, axis_y0, axis_y1)     # boxes in (u, v=z, w=thickness)
    v = b.reshape(-1, 3)
    if along == 'x': out = np.stack([v[:, 0], v[:, 2], v[:, 1]], 1)       # u->x, thickness->y, v->z
    else: out = np.stack([v[:, 2], v[:, 0], v[:, 1]], 1)                  # thickness->x, u->y, v->z
    t = out.reshape(-1, 3, 3)
    return t[:, ::-1, :] if along == 'x' else t

parts_out = {}
# ---- body
cvF, mF = wall_mask(True); cvS, mS = wall_mask(True, side=True)
body = [wall_tris(cvF, mF, -Dp/2, -Dp/2+WT, 'x'), wall_tris(cvF, mF, Dp/2-WT, Dp/2, 'x'),
        wall_tris(cvS, mS, -L/2, -L/2+WT, 'y'), wall_tris(cvS, mS, L/2-WT, L/2, 'y')]
for i in range(1, N):     # dividers (ribs) keep brushes apart and carry the top
    x = -L/2 + CW*i; body.append(box(x-1.2, -Dp/2+WT, 0, x+1.2, Dp/2-WT, H-TOP))
# top plate with brush holes, names raised in gold
OV = 2.0
cv = Canvas(-L/2-OV-1, -Dp/2-OV-1, L/2+OV+1, Dp/2+OV+1, 0.05)
plate = cv.arr(cv.poly([(-L/2-OV, -Dp/2-OV), (L/2+OV, -Dp/2-OV), (L/2+OV, Dp/2+OV), (-L/2-OV, Dp/2+OV)]))
hy = 6.0
for i in range(N):
    cx = -L/2 + CW*(i+0.5); plate &= ~cv.arr(cv.circle(cx, hy, 8.2))
gold = np.zeros_like(plate)
d = cv.din(plate)
for i, (ar, lat) in enumerate(NAMES):
    cx = -L/2 + CW*(i+0.5)
    tm, _ = text_mask(ar, CW-9, 9.5, cv.px, size_cap=9.5); gold |= cv.place(tm, cx, -13.0) & plate
    gold |= cv.arr(cv.circle(cx, hy, 10.4)) & ~cv.arr(cv.circle(cx, hy, 9.6))   # gold ring around hole
star_m = np.zeros_like(plate)
dd = cv.din(plate | cv.arr(cv.circle(0,0,0.01)))
edge = cv.din(cv.arr(cv.poly([(-L/2-OV, -Dp/2-OV), (L/2+OV, -Dp/2-OV), (L/2+OV, Dp/2+OV), (-L/2-OV, Dp/2+OV)])))
gold |= (edge >= 2.0) & (edge <= 2.7)
body.append(cv.boxes(plate, H-TOP, H))
body = np.concatenate(body)
write_stl(f'{OUT}/usra_holder.stl', body)
write_stl(f'{OUT}/usra_guld.stl', cv.boxes(gold, H, H+0.6))
# ---- drip tray
TW, TD, TH, TT = L+8, Dp+8, 9.0, 1.8
tray = [box(-TW/2, -TD/2, 0, TW/2, TD/2, TT),
        box(-TW/2, -TD/2, TT, TW/2, -TD/2+TT, TH), box(-TW/2, TD/2-TT, TT, TW/2, TD/2, TH),
        box(-TW/2, -TD/2+TT, TT, -TW/2+TT, TD/2-TT, TH), box(TW/2-TT, -TD/2+TT, TT, TW/2, TD/2-TT, TH)]
# small feet ribs inside tray so the holder stands above water
for x in np.linspace(-L/2+10, L/2-10, 6): tray.append(box(x-1, -Dp/2+6, TT, x+1, Dp/2-6, TT+2.0))
write_stl(f'{OUT}/usra_bakke.stl', np.concatenate(tray))
def vol(t): v=t.reshape(-1,3,3); return abs(np.einsum('ij,ij->i', v[:,0], np.cross(v[:,1], v[:,2])).sum()/6)
for f in sorted(os.listdir(OUT)):
    t = np.fromfile(f'{OUT}/{f}', dtype=np.uint8)[84:].view(np.dtype([('n','<f4',3),('v','<f4',(3,3)),('a','<u2')]))['v'].astype(float)
    print(f, len(t), 'tris', round(vol(t)/1000,1), 'cm3', t.reshape(-1,3).min(0).round(1), t.reshape(-1,3).max(0).round(1))
