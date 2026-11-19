"""Tiny numpy software renderer for studio product shots from STL files (transparent PNG)."""
import struct, math, json
import numpy as np
from PIL import Image, ImageFilter

def load(fn):
    d = open(fn, 'rb').read(); n = struct.unpack('<I', d[80:84])[0]
    return np.frombuffer(d[84:], dtype=[('n', '<f4', 3), ('v', '<f4', (3, 3)), ('a', '<u2')], count=n)['v'].astype(np.float64)

def srgb2lin(h):
    c = np.array([int(h[i:i+2], 16)/255 for i in (1, 3, 5)]); return np.where(c <= 0.04045, c/12.92, ((c+0.055)/1.055)**2.4)
def lin2srgb(c):
    c = np.clip(c, 0, 1); return np.where(c <= 0.0031308, c*12.92, 1.055*c**(1/2.4)-0.055)

MAT = {  # hex -> (base override, spec, shininess, metallic)
    'gold':  dict(spec=1.0, shin=40, metal=True),
    'matte': dict(spec=0.10, shin=18, metal=False),
    'steel': dict(spec=0.9, shin=60, metal=True),
}
def material(hexcol):
    h = hexcol.lower()
    if h in ('#d8b25a', '#c8a04e'): return srgb2lin('#d9ad55'), MAT['gold']
    if h == '#b9b4ab': return srgb2lin('#c9c6c0'), MAT['steel']
    base = {'#262423': '#1d1c1a', '#1a1714': '#1d1c1a', '#1f3a2e': '#1e3a2f', '#173a2c': '#1e3a2f'}.get(h, h)
    return srgb2lin(base), MAT['matte']

def look_at(eye, target, up=(0, 1, 0)):
    f = np.array(target, float) - eye; f /= np.linalg.norm(f)
    r = np.cross(f, up); r /= np.linalg.norm(r); u = np.cross(r, f)
    return r, u, f

def render(parts, out, W=1600, H=1600, eye_dir=(0.55, 0.42, 1.0), fov=22, fill=0.78, ss=2, shadow=True):
    """parts: list of (stl_path, hexcolor, M 3x3, t 3)"""
    tris, cols = [], []
    for fn, col, M, t in parts:
        v = load(fn) @ np.asarray(M).T + np.asarray(t)
        tris.append(v); cols += [col]*len(v)
    T = np.concatenate(tris); cols = np.array(cols)
    pts = T.reshape(-1, 3); lo, hi = pts.min(0), pts.max(0); ctr = (lo+hi)/2; rad = np.linalg.norm(hi-lo)/2
    ed = np.array(eye_dir, float); ed /= np.linalg.norm(ed)
    dist = rad/math.tan(math.radians(fov/2))/fill
    eye = ctr + ed*dist
    r, u, f = look_at(eye, ctr)
    w, h = W*ss, H*ss; foc = (h/2)/math.tan(math.radians(fov/2))
    def proj(P):
        d = P - eye; x, y, z = d @ r, d @ u, d @ f
        return np.stack([w/2 + foc*x/z, h/2 - foc*y/z, z], -1)
    S = proj(T)
    N = np.cross(T[:, 1]-T[:, 0], T[:, 2]-T[:, 0]); nl = np.linalg.norm(N, axis=1, keepdims=True); nl[nl == 0] = 1; N /= nl
    # lighting
    lights = [(np.array([-0.45, 0.85, 0.55]), 1.25), (np.array([0.7, 0.35, 0.45]), 0.45), (np.array([0.0, 0.5, -1.0]), 0.55)]
    lights = [(l/np.linalg.norm(l), k) for l, k in lights]
    V = eye - T.mean(1); V /= np.linalg.norm(V, axis=1, keepdims=True)
    color = np.zeros((len(T), 3))
    groups = {}
    for i, c in enumerate(cols): groups.setdefault(c, []).append(i)
    for c, idx in groups.items():
        idx = np.array(idx); base, m = material(c); n = N[idx]; v = V[idx]
        amb = 0.16 + 0.10*np.clip(n[:, 1], 0, 1)
        col = np.zeros((len(idx), 3))
        if m['metal']:
            refl = 2*np.sum(n*v, 1, keepdims=True)*n - v
            env = 0.25 + 0.75*np.clip(refl[:, 1:2]*0.8 + 0.35, 0, 1)**1.5        # sky-ish gradient
            col += base*env*0.85
        else:
            col += base*amb[:, None]
        for L, k in lights:
            diff = np.clip(n @ L, 0, 1)[:, None]
            hv = L + v; hv /= np.linalg.norm(hv, axis=1, keepdims=True)
            spec = np.clip(np.sum(n*hv, 1), 0, 1)**m['shin']
            if m['metal']:
                col += base*diff*0.55*k + base*spec[:, None]*m['spec']*k*1.6
            else:
                col += base*diff*k*0.95 + spec[:, None]*m['spec']*k
        color[idx] = col
    # rasterize
    zb = np.full((h, w), np.inf); img = np.zeros((h, w, 3)); a = np.zeros((h, w))
    facing = np.sum(N*(T.mean(1)-eye), 1) < 0
    order = np.where(facing)[0]
    for i in order:
        p = S[i]; xs, ys = p[:, 0], p[:, 1]
        x0, x1 = max(int(xs.min()), 0), min(int(xs.max())+1, w-1); y0, y1 = max(int(ys.min()), 0), min(int(ys.max())+1, h-1)
        if x0 > x1 or y0 > y1: continue
        X, Y = np.meshgrid(np.arange(x0, x1+1)+0.5, np.arange(y0, y1+1)+0.5)
        (ax, ay), (bx, by), (cx, cy) = p[0, :2], p[1, :2], p[2, :2]
        den = (by-cy)*(ax-cx) + (cx-bx)*(ay-cy)
        if abs(den) < 1e-12: continue
        l1 = ((by-cy)*(X-cx) + (cx-bx)*(Y-cy))/den; l2 = ((cy-ay)*(X-cx) + (ax-cx)*(Y-cy))/den; l3 = 1-l1-l2
        msk = (l1 >= -1e-6) & (l2 >= -1e-6) & (l3 >= -1e-6)
        if not msk.any(): continue
        z = l1*p[0, 2] + l2*p[1, 2] + l3*p[2, 2]
        sub = zb[y0:y1+1, x0:x1+1]; upd = msk & (z < sub)
        sub[upd] = z[upd]; img[y0:y1+1, x0:x1+1][upd] = color[i]; a[y0:y1+1, x0:x1+1][upd] = 1
    rgb = (lin2srgb(img)*255).astype(np.uint8)
    obj = Image.fromarray(np.dstack([rgb, (a*255).astype(np.uint8)]), 'RGBA')
    final = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    if shadow:
        # soft shadow: project geometry to ground (y = lo[1]) along the key light, plus a tight contact shadow
        sh = np.zeros((h, w), np.uint8); shi = Image.fromarray(sh); from PIL import ImageDraw
        L = lights[0][0]; gy = lo[1]
        for spread, blur, alpha in ((1.0, 28, 0.32), (0.0, 10, 0.38)):
            m_img = Image.new('L', (w, h), 0); dr = ImageDraw.Draw(m_img)
            P = T.reshape(-1, 3).copy()
            tt = (P[:, 1]-gy); P[:, 0] -= L[0]/L[1]*tt*spread; P[:, 2] -= L[2]/L[1]*tt*spread; P[:, 1] = gy
            if spread == 0:  # contact: only geometry close to the ground
                keep = (T.reshape(-1, 3)[:, 1]-gy) < rad*0.08
            Q = proj(P).reshape(-1, 3, 3)
            sel = range(0, len(Q))
            for j in sel:
                if spread == 0 and not keep[j*3:(j+1)*3].any(): continue
                dr.polygon([tuple(q[:2]) for q in Q[j]], fill=255)
            m_img = m_img.filter(ImageFilter.GaussianBlur(blur*ss))
            layer = Image.new('RGBA', (w, h), (20, 14, 8, 0)); layer.putalpha(m_img.point(lambda v: int(v*alpha)))
            final = Image.alpha_composite(final, layer)
    final = Image.alpha_composite(final, obj)
    final = final.resize((W, H), Image.LANCZOS)
    bb = final.getbbox(); final = final.crop(bb)
    final.save(out); return final.size
