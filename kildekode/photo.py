"""Small deferred 'photographic' renderer: perspective-correct raster G-buffer, soft shadow map,
SSAO, procedural textures, spine texture images, filmic tone map, DOF, vignette and grain."""
import math, struct
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

def load_stl(fn):
    d = open(fn, 'rb').read(); n = struct.unpack('<I', d[80:84])[0]
    return np.frombuffer(d[84:], dtype=[('n', '<f4', 3), ('v', '<f4', (3, 3)), ('a', '<u2')], count=n)['v'].astype(np.float64)

def srgb(h):
    c = np.array([int(h[i:i+2], 16)/255 for i in (1, 3, 5)]); return np.where(c <= 0.04045, c/12.92, ((c+0.055)/1.055)**2.4)

# ---------------------------------------------------------------- noise
_rng = np.random.default_rng(7)
_G = [_rng.random((256, 256)) for _ in range(6)]
def noise(u, v, seed=0, oct=4):
    out = np.zeros_like(u); amp = 1; tot = 0; f = 1
    for o in range(oct):
        g = _G[(seed+o) % 6]
        out += amp*ndimage.map_coordinates(g, [ (v*f) % 256, (u*f) % 256 ], order=1, mode='wrap')
        tot += amp; amp *= 0.5; f *= 2.03
    return out/tot

# ---------------------------------------------------------------- scene
class Scene:
    def __init__(s):
        s.T = []; s.NV = []; s.obj = []; s.objs = []
    def add(s, tris, mat, vnormals=None, **info):
        tris = np.asarray(tris, float)
        oid = len(s.objs); s.objs.append(dict(mat=mat, **info))
        if vnormals is None:
            n = np.cross(tris[:, 1]-tris[:, 0], tris[:, 2]-tris[:, 0]); l = np.linalg.norm(n, axis=1, keepdims=True); l[l == 0] = 1
            n = n/l; vnormals = np.repeat(n[:, None, :], 3, 1)
        s.T.append(tris); s.NV.append(vnormals); s.obj.append(np.full(len(tris), oid))
        return oid
    def box(s, x0, x1, y0, y1, z0, z1, mat, **info):
        c = np.array([[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0], [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]])
        F = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (3, 7, 6, 2), (0, 4, 7, 3), (1, 2, 6, 5)]
        tris = []
        for a, b, cc, d in F: tris += [[c[a], c[b], c[cc]], [c[a], c[cc], c[d]]]
        tris = np.array(tris, float)
        ctr = np.array([(x0+x1)/2, (y0+y1)/2, (z0+z1)/2])
        n = np.cross(tris[:, 1]-tris[:, 0], tris[:, 2]-tris[:, 0]); out = np.sum(n*(tris.mean(1)-ctr), 1) < 0
        tris[out] = tris[out][:, [0, 2, 1]]
        return s.add(tris, mat, bounds=(x0, x1, y0, y1, z0, z1), **info)
    def cylinder(s, cx, cz, y0, y1, r, mat, seg=72, cap=True, r_top=None, **info):
        rt = r if r_top is None else r_top
        a = np.linspace(0, 2*math.pi, seg+1)
        tris, nv = [], []
        for i in range(seg):
            a0, a1 = a[i], a[i+1]
            p = lambda ang, y, rr: [cx+math.cos(ang)*rr, y, cz+math.sin(ang)*rr]
            n0 = [math.cos(a0), (r-rt)/(y1-y0), math.sin(a0)]; n1 = [math.cos(a1), (r-rt)/(y1-y0), math.sin(a1)]
            tris += [[p(a0, y0, r), p(a1, y1, rt), p(a1, y0, r)], [p(a0, y0, r), p(a0, y1, rt), p(a1, y1, rt)]]
            nv += [[n0, n1, n1], [n0, n0, n1]]
            if cap:
                tris += [[[cx, y1, cz], p(a1, y1, rt), p(a0, y1, rt)]]; nv += [[[0, 1, 0]]*3]
        nv = np.array(nv, float); nv /= np.linalg.norm(nv, axis=2, keepdims=True)
        return s.add(np.array(tris), mat, vnormals=nv, **info)
    def mesh(s, fn, mat, M=np.eye(3), t=(0, 0, 0), **info):
        v = load_stl(fn) @ np.asarray(M, float).T + np.asarray(t, float)
        return s.add(v, mat, **info)
    def build(s):
        s.Ta = np.concatenate(s.T); s.Na = np.concatenate(s.NV); s.Oa = np.concatenate(s.obj)

# ---------------------------------------------------------------- raster
def raster(xy, w, W, H):
    """xy: (N,3,2) pixel coords, w: (N,3) 1/depth (bigger=closer). returns wbuf, tri, l1, l2 (perspective-correct)"""
    wb = np.zeros((H, W)); tri = np.full((H, W), -1, np.int64); L1 = np.zeros((H, W)); L2 = np.zeros((H, W))
    mn = xy.min(1); mx = xy.max(1)
    vis = (mx[:, 0] >= 0) & (mn[:, 0] < W) & (mx[:, 1] >= 0) & (mn[:, 1] < H) & (w.min(1) > 0)
    for i in np.where(vis)[0]:
        p = xy[i]
        x0, x1 = max(int(mn[i, 0]), 0), min(int(mx[i, 0])+1, W-1); y0, y1 = max(int(mn[i, 1]), 0), min(int(mx[i, 1])+1, H-1)
        if x0 > x1 or y0 > y1: continue
        X = np.arange(x0, x1+1)+0.5; Y = (np.arange(y0, y1+1)+0.5)[:, None]
        (ax, ay), (bx, by), (cx, cy) = p
        den = (by-cy)*(ax-cx) + (cx-bx)*(ay-cy)
        if abs(den) < 1e-9: continue
        l1 = ((by-cy)*(X-cx) + (cx-bx)*(Y-cy))/den; l2 = ((cy-ay)*(X-cx) + (ax-cx)*(Y-cy))/den; l3 = 1-l1-l2
        m = (l1 >= -1e-7) & (l2 >= -1e-7) & (l3 >= -1e-7)
        if not m.any(): continue
        ww = l1*w[i, 0] + l2*w[i, 1] + l3*w[i, 2]
        sub = wb[y0:y1+1, x0:x1+1]; up = m & (ww > sub)
        if not up.any(): continue
        sub[up] = ww[up]; tri[y0:y1+1, x0:x1+1][up] = i
        L1[y0:y1+1, x0:x1+1][up] = (l1*w[i, 0]/ww)[up]; L2[y0:y1+1, x0:x1+1][up] = (l2*w[i, 1]/ww)[up]
    return wb, tri, L1, L2

def basis(f, up=(0, 1, 0)):
    f = np.asarray(f, float); f /= np.linalg.norm(f); r = np.cross(f, up); r /= np.linalg.norm(r); u = np.cross(r, f); return r, u, f

# ---------------------------------------------------------------- materials
def shade_albedo(sc, oid, P, N, mats):
    """returns albedo (n,3), spec (n), shin (n), metal (n bool)"""
    n = len(P); alb = np.zeros((n, 3)); spec = np.full(n, 0.04); shin = np.full(n, 20.0); metal = np.zeros(n, bool)
    for o in np.unique(oid):
        sel = oid == o; ob = sc.objs[o]; m = ob['mat']; p = P[sel]; nn = N[sel]
        if m == 'wood':
            base = ob.get('tone', 1.0)
            g = p[:, 1]*0.9 + p[:, 2]*0.35 + 26*noise(p[:, 0]*0.006, p[:, 1]*0.05+p[:, 2]*0.05, 1, 3)
            bands = 0.5+0.5*np.sin(g*0.55)
            fib = noise(p[:, 0]*0.02, (p[:, 1]+p[:, 2])*1.4, 2, 3)
            t = np.clip(0.55*bands**3 + 0.45*fib, 0, 1)
            light, dark = srgb('#b8875a'), srgb('#7a5233')
            a = light*(1-t[:, None]*0.55) + dark*(t[:, None]*0.55)
            alb[sel] = a*base; spec[sel] = 0.06; shin[sel] = 30
        elif m == 'plaster':
            nz = noise(p[:, 0]*0.03, p[:, 1]*0.03, 3, 4)
            alb[sel] = srgb(ob.get('col', '#ece4d6'))*(0.94+0.1*nz[:, None]); spec[sel] = 0.01
        elif m == 'leather':
            c = srgb(ob['col']); nz = noise(p[:, 0]*0.6, p[:, 1]*0.6, 4, 2); nz2 = noise(p[:, 0]*0.04, p[:, 1]*0.04, 5, 3)
            a = c*(0.88+0.16*nz[:, None])*(0.85+0.3*nz2[:, None])*ob.get('var', 1.0)
            sp = np.full(len(p), 0.10); sh = np.full(len(p), 26.0); mt = np.zeros(len(p), bool)
            tex = ob.get('tex'); x0, x1, y0, y1, z0, z1 = ob['bounds']
            front = nn[:, 2] > 0.7
            if tex is not None and front.any():
                u = (p[front, 0]-x0)/(x1-x0); v = (y1-p[front, 1])/(y1-y0)
                th, tw = tex.shape[:2]
                tx = np.clip((u*tw).astype(int), 0, tw-1); ty = np.clip((v*th).astype(int), 0, th-1)
                tv = tex[ty, tx]
                gold = tv[:, 0] > 0.5; panel = tv[:, 1]
                af = a[front]; af *= (1-0.45*panel[:, None]);
                af[gold] = srgb('#d6aa52'); a[front] = af
                spf = sp[front]; spf[gold] = 1.0; sp[front] = spf
                shf = sh[front]; shf[gold] = 70; sh[front] = shf
                mtf = mt[front]; mtf[gold] = True; mt[front] = mtf
            top = nn[:, 1] > 0.7
            if top.any():
                # page block, with thin board edge
                ed = np.minimum.reduce([p[top, 0]-x0, x1-p[top, 0], p[top, 2]-z0, z1-p[top, 2]])
                pg = srgb('#e9dcc0')*(0.9+0.1*np.sin(p[top, 0]*9)[:, None]*0.5+0.05)
                at = a[top]; inner = ed > 2.2; at[inner] = pg[inner]; a[top] = at
            alb[sel] = a; spec[sel] = sp; shin[sel] = sh; metal[sel] = mt
        elif m == 'gold':
            alb[sel] = srgb('#d9ad55'); spec[sel] = 1.0; shin[sel] = 60; metal[sel] = True
        elif m == 'steel':
            alb[sel] = srgb('#c9c6c0'); spec[sel] = 0.9; shin[sel] = 80; metal[sel] = True
        elif m == 'pla':
            c = srgb(ob.get('col', '#1d1c1a'))
            ll = 0.97+0.03*np.sin(p[:, 1]*2*math.pi/0.12*0.25)  # faint layer lines
            alb[sel] = c[None]*ll[:, None]; spec[sel] = 0.06; shin[sel] = 14
        elif m == 'ceramic':
            alb[sel] = srgb(ob.get('col', '#efe9de')); spec[sel] = 0.5; shin[sel] = 120
        elif m == 'flat':
            alb[sel] = srgb(ob['col']); spec[sel] = ob.get('spec', 0.05); shin[sel] = ob.get('shin', 20)
        else:
            alb[sel] = 0.5
    return alb, spec, shin, metal

# ---------------------------------------------------------------- render
DEBUG=False
def render(sc, out, W, H, eye, target, fov=30, ss=2, light_dir=(-0.55, 0.62, 0.55), focus=None, fstop=1.0,
           key=3.1, amb=0.75, exposure=1.0, sm_res=3072, shadow_soft=3.0, ao_radius=28, grade='warm', win_falloff=None, sat=0.78):
    sc.build(); T = sc.Ta; NV = sc.Na; O = sc.Oa
    w, h = W*ss, H*ss; eye = np.asarray(eye, float)
    r, u, f = basis(np.asarray(target, float)-eye)
    foc = (h/2)/math.tan(math.radians(fov/2))
    D = T-eye; x = D@r; y = D@u; z = D@f
    z = np.maximum(z, 1e-3)
    xy = np.stack([w/2+foc*x/z, h/2-foc*y/z], -1)
    wb, tri, L1, L2 = raster(xy, 1/z, w, h)
    hit = tri >= 0
    ti = tri[hit]; l1 = L1[hit]; l2 = L2[hit]; l3 = 1-l1-l2
    P = T[ti, 0]*l1[:, None]+T[ti, 1]*l2[:, None]+T[ti, 2]*l3[:, None]
    N = NV[ti, 0]*l1[:, None]+NV[ti, 1]*l2[:, None]+NV[ti, 2]*l3[:, None]; N /= np.linalg.norm(N, axis=1, keepdims=True)+1e-9
    V = eye-P; dist = np.linalg.norm(V, axis=1); V /= dist[:, None]
    flip = np.sum(N*V, 1) < 0; N[flip] *= -1
    oid = O[ti]
    # rounded book spines: bend normals across the spine width
    for o in np.unique(oid):
        ob = sc.objs[o]
        if ob['mat'] != 'leather': continue
        sel = (oid == o) & (N[:, 2] > 0.7)
        if not sel.any(): continue
        x0, x1 = ob['bounds'][0], ob['bounds'][1]; uu = (P[sel, 0]-x0)/(x1-x0)*2-1
        N[sel, 0] += np.sign(uu)*np.abs(uu)**1.6*0.9
        N[sel] /= np.linalg.norm(N[sel], axis=1, keepdims=True)
    # ---- shadow map (orthographic along light)
    Ld = np.asarray(light_dir, float); Ld /= np.linalg.norm(Ld)
    lr, lu, lf = basis(-Ld, up=(0, 0, 1) if abs(Ld[1]) > 0.99 else (0, 1, 0))
    pts = T.reshape(-1, 3); lx = pts@lr; ly = pts@lu
    # restrict shadow map to the camera-visible region (plus margin)
    vx = P@lr; vy = P@lu; pad = 120
    bx0, bx1, by0, by1 = vx.min()-pad, vx.max()+pad, vy.min()-pad, vy.max()+pad
    sres = sm_res; scl = sres/max(bx1-bx0, by1-by0)
    lxy = np.stack([(T@lr-bx0)*scl, (by1-T@lu)*scl], -1)
    ld = T@lf; LC = ld.max()+10
    swb, _, _, _ = raster(lxy, LC-ld, sres, sres)
    sdepth = np.where(swb > 0, LC-swb, np.inf)
    px = (P@lr-bx0)*scl; py = (by1-P@lu)*scl; pd = (P@lf)
    bias = 0.6 + 1.2*(1-np.clip(np.sum(N*Ld, 1), 0, 1))
    rng = np.random.default_rng(3); vis = np.zeros(len(P)); K = 24
    for k in range(K):
        a = rng.random()*2*math.pi; rr = math.sqrt((k+0.5)/K)*shadow_soft*scl*1.0
        sx = np.clip((px+math.cos(a)*rr).astype(int), 0, sres-1); sy = np.clip((py+math.sin(a)*rr).astype(int), 0, sres-1)
        vis += (pd <= sdepth[sy, sx]+bias)
    vis /= K
    # ---- SSAO (view-space depth)
    zbuf = np.where(hit, 1/np.maximum(wb, 1e-12), np.inf)
    hy, hx = np.where(hit); zc = zbuf[hy, hx]
    occ = np.zeros(len(P)); S = 16; jit = np.random.default_rng(5).random(len(P))
    for k in range(S):
        a = (k/S + jit)*2*math.pi; rad_px = ao_radius*foc/zc*(0.15+0.85*((k*0.618+jit) % 1))
        sx = np.clip((hx+np.cos(a)*rad_px).astype(int), 0, w-1); sy = np.clip((hy+np.sin(a)*rad_px).astype(int), 0, h-1)
        dz = zc-zbuf[sy, sx]
        occ += np.clip(dz/ (ao_radius*0.6), 0, 1)*(dz < ao_radius*2.5)
    ao = 1-np.clip(occ/S*1.6, 0, 0.85)
    aoimg = np.ones((h, w)); aoimg[hit] = ao; aoimg = ndimage.gaussian_filter(aoimg, 3*ss); ao = aoimg[hit]
    if DEBUG:
        dv=np.zeros((h,w)); dv[hit]=vis; Image.fromarray((dv*255).astype(np.uint8)).resize((w//ss,h//ss)).save('/tmp/dbg_vis.png')
        da=np.zeros((h,w)); da[hit]=ao; Image.fromarray((da*255).astype(np.uint8)).resize((w//ss,h//ss)).save('/tmp/dbg_ao.png')
        do=np.zeros((h,w)); do[hit]=(oid*37%255); Image.fromarray(do.astype(np.uint8)).resize((w//ss,h//ss)).save('/tmp/dbg_oid.png')
    # ---- shading
    alb, spec, shin, metal = shade_albedo(sc, oid, P, N, None)
    keyc = np.array([1.0, 0.9, 0.76])*key
    sky = np.array([0.62, 0.66, 0.74]); gnd = np.array([0.42, 0.34, 0.27])
    hemi = (sky*(0.5+0.5*N[:, 1:2]) + gnd*(0.5-0.5*N[:, 1:2]))*amb
    ndl = np.clip(np.sum(N*Ld, 1), 0, 1)
    H_ = Ld+V; H_ /= np.linalg.norm(H_, axis=1, keepdims=True)
    ndh = np.clip(np.sum(N*H_, 1), 0, 1)
    fres = 0.04+0.96*(1-np.clip(np.sum(N*V, 1), 0, 1))**5
    if win_falloff:
        g = np.clip(1.15-(P[:, 0]-win_falloff[0])/win_falloff[1], 0.35, 1.15)
        vis = vis*g
    col = alb*(hemi*ao[:, None] + keyc*(ndl*vis)[:, None])
    sp = (spec*(ndh**shin)*(shin+8)/40*ndl*vis)[:, None]*keyc
    col += sp*np.where(metal[:, None], alb*1.2, 1.0) + (fres*spec*0.25*ao)[:, None]*sky*np.where(metal[:, None], 0, 1)
    if metal.any():
        R = 2*np.sum(N*V, 1, keepdims=True)*N-V
        win = np.exp(-(1-np.clip(R@Ld, -1, 1))*5)*3.2
        env = 0.12+0.55*np.clip(R[:, 1]*0.6+0.4, 0, 1)**1.6 + win
        env = env*ao*(0.45+0.55*vis)
        mcol = alb*env[:, None]*0.9 + alb*keyc*(ndl*vis)[:, None]*0.25
        col[metal] = mcol[metal] + sp[metal]*alb[metal]*1.4
    img = np.zeros((h, w, 3), np.float32); img[hit] = col
    bg = np.array(srgb('#efe7da'))*0.6; img[~hit] = bg
    del P, N, V, col, alb, hemi, sp
    # downsample to output resolution before post
    img = img.reshape(H, ss, W, ss, 3).mean((1, 3))
    zb2 = np.where(hit, zbuf, 1e9).reshape(H, ss, W, ss).min((1, 3)); hit = zb2 < 1e9; zbuf = zb2
    h, w, ss = H, W, 1
    # ---- DOF
    if focus is not None:
        coc = np.abs(1/np.maximum(zbuf, 1)-1/focus)*focus*fstop*ss*6.0  # pixels
        coc[~hit] = coc[hit].max() if hit.any() else 0
        levels = [0, 1.5, 3, 6, 10, 16, 24]
        stack = [img] + [ndimage.gaussian_filter(img, (s/2, s/2, 0)).astype(np.float32) for s in levels[1:]]
        cc = np.clip(coc/ss, 0, levels[-1]); dof = np.zeros_like(img)
        idx = np.searchsorted(levels, cc, side='right')-1; idx = np.clip(idx, 0, len(levels)-2)
        lo = np.array(levels)[idx]; hi_ = np.array(levels)[idx+1]; t = (cc-lo)/(hi_-lo)
        for i in range(len(levels)-1):
            m = idx == i
            if m.any(): dof[m] = stack[i][m]*(1-t[m, None]) + stack[i+1][m]*t[m, None]
        img = dof
    # ---- bloom
    br = np.clip(img-1.0, 0, None)
    img += ndimage.gaussian_filter(br, (6, 6, 0))*0.5
    # ---- tone map (ACES approx) + grade
    img = img*exposure
    a, b, c, d, e = 2.51, 0.03, 2.43, 0.59, 0.14
    img = np.clip((img*(a*img+b))/(img*(c*img+d)+e), 0, 1)
    lum = (img*np.array([0.2126, 0.7152, 0.0722])).sum(-1, keepdims=True); img = lum+(img-lum)*sat
    if grade == 'warm':
        img = img**np.array([0.97, 1.0, 1.05])
    yy, xx = np.mgrid[0:h, 0:w]; rr = np.sqrt(((xx-w/2)/(w/2))**2+((yy-h/2)/(h/2))**2)
    img *= (1-0.22*np.clip(rr-0.55, 0, 1)**1.5)[..., None]
    img = np.where(img <= 0.0031308, img*12.92, 1.055*img**(1/2.4)-0.055)
    im = Image.fromarray((np.clip(img, 0, 1)*255).astype(np.uint8))
    g = np.random.default_rng(1).normal(0, 2.2, (H, W, 1))
    arr = np.clip(np.asarray(im).astype(float)+g, 0, 255).astype(np.uint8)
    Image.fromarray(arr).save(out, quality=92)
    return out

def _sphere(s, c, r, mat, seg=28, **info):
    cx, cy, cz = c; rx_, ry_, rz_ = r
    th = np.linspace(0, math.pi, seg//2+1); ph = np.linspace(0, 2*math.pi, seg+1)
    P = lambda t, p: np.array([cx+rx_*math.sin(t)*math.cos(p), cy+ry_*math.cos(t), cz+rz_*math.sin(t)*math.sin(p)])
    Nn = lambda t, p: (lambda v: v/np.linalg.norm(v))(np.array([math.sin(t)*math.cos(p)/rx_, math.cos(t)/ry_, math.sin(t)*math.sin(p)/rz_]))
    tris, nv = [], []
    for i in range(len(th)-1):
        for j in range(len(ph)-1):
            a, b, c2, d = (th[i], ph[j]), (th[i+1], ph[j]), (th[i+1], ph[j+1]), (th[i], ph[j+1])
            tris += [[P(*a), P(*b), P(*c2)], [P(*a), P(*c2), P(*d)]]; nv += [[Nn(*a), Nn(*b), Nn(*c2)], [Nn(*a), Nn(*c2), Nn(*d)]]
    return s.add(np.array(tris), mat, vnormals=np.array(nv), **info)
Scene.sphere = _sphere
