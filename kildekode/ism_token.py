"""ISM 2-i-1: nøglering + indkøbsvognsmønt (20 kr: Ø27.0 x 2.35 mm / 10 kr: Ø23.35 mm).
Flush gold inlay (top + bottom 0.4 mm) so thickness stays coin-like. Print orientation Z up; back side = bed."""
import os, math, json, sys
import numpy as np
src = open('/home/claude/products/products.py').read()
exec(src[:src.index('parts = []')])
OUT = '/home/claude/token/stl'; os.makedirs(OUT, exist_ok=True)
T, INL = 2.3, 0.4                       # total thickness, inlay depth per side

def token(D, name_ar, name_lat, tag):
    R = D/2; px = 0.03
    cv = Canvas(-R-1, -R-1, R+1, R+12, px)
    coin = cv.arr(cv.circle(0, 0, R))
    ty = R + 4.6
    tab = cv.arr(cv.poly([(-5.2, R-4), (5.2, R-4), (5.2, ty), (-5.2, ty)])) | cv.arr(cv.circle(0, ty, 5.2))
    hole = cv.arr(cv.circle(0, ty+0.4, 2.3))
    body = (coin | tab) & ~hole
    # front (top) gold: border ring + name + small star on tab
    d = cv.din(coin)
    front = coin & (d >= 0.9) & (d <= 1.45)
    tm, _ = text_mask(name_ar, D*0.66, D*0.36, px); front |= cv.place(tm, 0, -0.6) & coin
    front |= cv.arr(cv.poly(star8_pts(0, R-2.9, 1.25, 0.62))) & coin
    # back (bed) gold: ring + latin name + KHATAM, mirrored so it reads correctly from behind
    back = coin & (d >= 0.9) & (d <= 1.45)
    lm = latin_mask(name_lat, D*0.62, D*0.13, px, tracking=0.22)
    km = latin_mask('KHATAM', D*0.34, D*0.055, px, tracking=0.5)
    b2 = cv.place(lm, 0, 0.8) | cv.place(km, 0, -D*0.22)
    back |= b2[:, ::-1] & coin
    plate = np.concatenate([cv.boxes(body & ~back, 0, INL), cv.boxes(body, INL, T-INL), cv.boxes(body & ~front, T-INL, T)])
    gf = cv.boxes(front, T-INL, T); gb = cv.boxes(back, 0, INL)
    files = {}
    for k, tr in [('plade', plate), ('guld_forside', gf), ('guld_bagside', gb)]:
        fn = f'{OUT}/ism_{tag}_{k}.stl'; write_stl(fn, tr); files[k] = fn
    return files, ty

def torus(cx, cy, cz, R, r, nu=40, nv=12):
    t = []
    P = lambda i, j: (cx + (R + r*math.cos(2*math.pi*j/nv))*math.cos(2*math.pi*i/nu), cy + (R + r*math.cos(2*math.pi*j/nv))*math.sin(2*math.pi*i/nu), cz + r*math.sin(2*math.pi*j/nv))
    for i in range(nu):
        for j in range(nv):
            a, b, c, d = P(i, j), P(i+1, j), P(i+1, j+1), P(i, j+1); t += [[a, b, c], [a, c, d]]
    return tri_arr(t)

def ring_mesh(cy, R=8.0, r=0.75):
    return torus(0, cy, T/2, R, r)

if __name__ == '__main__':
    out = {}
    out['20kr_yusuf'] = token(26.9, 'يوسف', 'YUSUF', '20kr_yusuf')[0]
    out['20kr_omar'] = token(26.9, 'عمر', 'OMAR', '20kr_omar')[0]
    out['10kr_yusuf'] = token(23.3, 'يوسف', 'YUSUF', '10kr_yusuf')[0]
    # calibration discs (no tab text), diameters to test in the shop
    for D in (26.7, 26.8, 26.9, 27.0, 23.2, 23.3):
        R = D/2; cv = Canvas(-R-1, -R-1, R+1, R+12, 0.03)
        coin = cv.arr(cv.circle(0, 0, R)); ty = R+4.6
        body = (coin | cv.arr(cv.poly([(-5.2, R-4), (5.2, R-4), (5.2, ty), (-5.2, ty)])) | cv.arr(cv.circle(0, ty, 5.2))) & ~cv.arr(cv.circle(0, ty+0.4, 2.3))
        lab = latin_mask(f'{D:.1f}'.replace('.', ','), D*0.5, D*0.16, 0.03, tracking=0.1)
        eng = cv.place(lab, 0, 0) & coin
        write_stl(f'{OUT}/kalibrering_{str(D).replace(".", "_")}.stl', np.concatenate([cv.boxes(body, 0, T-0.6), cv.boxes(body & ~eng, T-0.6, T)]))
    json.dump(out, open(f'{OUT}/files.json', 'w'), indent=1)
    import struct
    for f in sorted(os.listdir(OUT)):
        if f.endswith('.stl'):
            d = open(f'{OUT}/{f}', 'rb').read(84); print(f, struct.unpack('<I', d[80:84])[0])
