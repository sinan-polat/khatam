"""Shelf category signs (mihrab-arch plate + stepped stand) for Bambu Lab P2S. Units mm.
Plate is printed flat, face up: black base + 0.6 mm gold relief on top (one filament change).
Stand is printed upright, slot open on top.
"""
import os, math, json
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

src = open('/home/claude/print/gen.py').read()
exec(src[:src.index('# ---------------------------------------------------------------- parts')])  # mesh helpers

OUT = '/home/claude/signs/stl'; os.makedirs(OUT, exist_ok=True)
FONT = '/home/claude/signs/Cairo.woff2'   # Cairo ExtraBold (Google Fonts, OFL)

W, RECT_H, RISE = 72.0, 34.0, 31.0      # plate width, straight part, arch rise  -> 67 mm tall
T, REL = 3.0, 0.6                        # plate thickness, gold relief height
TAB_W, TAB_H = 26.0, 7.0
CATS = [
    ('quran', 'القرآن', 'Koranen'), ('tafsir', 'التفسير', 'Tafsir'), ('hadith', 'الحديث', 'Hadith'),
    ('aqidah', 'العقيدة', 'ʿAqida'), ('fiqh', 'الفقه', 'Fiqh'), ('sirah', 'السيرة', 'Sira'),
    ('tazkiyah', 'التزكية', 'Tazkiya'), ('tarikh', 'التاريخ', 'Historie'),
]

def pointed(a, rise, n=60):
    c = (rise*rise - a*a)/(2*a); R = a + c; th1 = math.atan2(rise, -c); left = []
    for i in range(n+1):
        th = math.pi + (th1-math.pi)*i/n; left.append((c + R*math.cos(th), R*math.sin(th)))
    return left + [(-x, y) for x, y in reversed(left[:-1])]

# Silhouette: straight sides, small shoulder step, then pointed arch.  y=0 is the bottom edge.
SH = 10.0   # shoulder inset
def silhouette():
    a = W/2 - SH; yb = RECT_H + 2.0
    pts = [(-W/2, 0), (W/2, 0), (W/2, RECT_H), (W/2 - 2.0, yb)]
    pts += [(x, y + yb) for x, y in reversed(pointed(a, RISE))]
    pts += [(-W/2 + 2.0, yb), (-W/2, RECT_H)]
    return clean(pts)
SIL = silhouette()
HTOT = max(p[1] for p in SIL)

def plate_mesh():
    body = extrude(SIL, 0, T)
    tab = box(-TAB_W/2, -TAB_H, 0, TAB_W/2, 0.01, T)
    return np.concatenate([body, tab])

PX = 0.08
X0, Y0 = -W/2 - 1, -1
GW, GH = int((W + 2)/PX), int((HTOT + 2)/PX)
def P(x, y): return ((x - X0)/PX, (y - Y0)/PX)

def erode(img, mm):
    k = int(round(mm/PX))*2 + 1
    return img.filter(ImageFilter.MinFilter(k)) if k > 1 else img

def star8(cx, cy, R, r):
    return [P(cx + math.cos(k*math.pi/8 + math.pi/2)*(R if k % 2 == 0 else r), cy + math.sin(k*math.pi/8 + math.pi/2)*(R if k % 2 == 0 else r)) for k in range(16)]

def gold_mask(text):
    sil = Image.new('L', (GW, GH), 0); ImageDraw.Draw(sil).polygon([P(*p) for p in SIL], fill=255)
    e1, e2, e3, e4 = erode(sil, 1.6), erode(sil, 2.6), erode(sil, 3.6), erode(sil, 4.3)
    a = lambda im: np.array(im) > 127
    m = (a(e1) & ~a(e2)) | (a(e3) & ~a(e4))                 # double border: 1.0 mm + 0.7 mm
    deco = Image.new('L', (GW, GH), 0); d = ImageDraw.Draw(deco)
    # 8-point star in the arch, with a hollow centre
    sy = RECT_H + 2.0 + RISE*0.42
    d.polygon(star8(0, sy, 4.6, 2.6), fill=255)
    d.ellipse([P(-1.3, sy-1.3), P(1.3, sy+1.3)], fill=0)
    m |= np.array(deco) > 127
    # text (row 0 = bottom in our convention)
    maxw = W - 15
    tm, tsz = text_mask(text, maxw, 22.0, PX, size_cap=22.0)
    tm = np.flipud(tm)                                        # back to image rows (top = 0)
    cy = 18.6                                                 # text centred in the lower panel
    r0 = int((cy - Y0)/PX) - tm.shape[0]//2; c0 = int((0 - X0)/PX) - tm.shape[1]//2
    full = np.zeros((GH, GW), bool); full[r0:r0+tm.shape[0], c0:c0+tm.shape[1]] = tm[::-1]
    m |= full
    return m, tsz

TILT = math.radians(5)          # sign leans back 5°
def extrude_yz(poly, x0, x1):
    """polygon in (y,z), extruded along x"""
    t = extrude(poly, x0, x1)
    return t[:, :, [2, 0, 1]]     # (u,v,w) -> (x=w, y=u, z=v), cyclic = keeps winding

def stand_mesh():
    """Bookshelf foot: stepped front + long thin tongue that slides under the books (books hold it down)."""
    def rect(w, d, oy=0): return [(-w/2, oy-d/2), (w/2, oy-d/2), (w/2, oy+d/2), (-w/2, oy+d/2)]
    parts = []
    # tier 1 (front block)  y: -22 .. +12
    parts.append(extrude(rect(84, 34, -5), 0, 1.8))
    parts.append(loft(rect(84, 34, -5), rect(82.4, 32.4, -5), 1.8, 2.6))
    # tongue under the books: 60 mm wide, 2 mm thick, ramp at the back so books slide on
    parts.append(extrude_yz([(11.0, 0), (82.0, 0), (82.0, 0.6), (70.0, 2.0), (11.0, 2.0)], -30, 30))
    # tier 2
    parts.append(extrude(rect(70, 24, -3), 2.6, 3.8))
    parts.append(loft(rect(70, 24, -3), rect(68.8, 22.8, -3), 3.8, 4.4))
    # holder with slot tilted back by TILT (sheared walls)
    zb, H = 4.4, 9.0
    zt = zb + H
    SLOT_W, SLOT_L, SLOT_D = T + 0.35, TAB_W + 0.6, 7.6
    zf = zt - SLOT_D
    sh = lambda z: math.tan(TILT) * (z - zb)                  # +y = backwards
    def blk(x0, x1, y0, y1, za, zc):
        pb = [(x0, y0+sh(za)), (x1, y0+sh(za)), (x1, y1+sh(za)), (x0, y1+sh(za))]
        pt = [(x0, y0+sh(zc)), (x1, y0+sh(zc)), (x1, y1+sh(zc)), (x0, y1+sh(zc))]
        return loft(pb, pt, za, zc)
    parts.append(blk(-18, 18, -7, 7, zb, zf))                       # floor
    parts.append(blk(-18, 18, -7, -SLOT_W/2, zf, zt))               # front wall
    parts.append(blk(-18, 18, SLOT_W/2, 7, zf, zt))                 # back wall
    parts.append(blk(-18, -SLOT_L/2, -SLOT_W/2, SLOT_W/2, zf, zt))  # side walls
    parts.append(blk(SLOT_L/2, 18, -SLOT_W/2, SLOT_W/2, zf, zt))
    return np.concatenate(parts), zt

if __name__ == '__main__':
    info = []
    plate = plate_mesh()
    stand, stand_top = stand_mesh()
    write_stl(f'{OUT}/fod.stl', stand)
    masks = {}
    for key, ar, da in CATS:
        m, tsz = gold_mask(ar)
        masks[key] = m
        gold, nrect = raster_boxes(m[::-1] if False else m, PX, X0, Y0, T, T + REL)
        write_stl(f'{OUT}/skilt_{key}_plade.stl', plate)
        write_stl(f'{OUT}/skilt_{key}_guld.stl', gold)
        info.append(dict(key=key, ar=ar, da=da, text_mm=[round(tsz[0], 1), round(tsz[1], 1)], gold_tris=len(gold),
                         plate_vol=volume(plate), gold_vol=volume(gold), plate_area=surface(plate)))
        print(key, ar, 'text', [round(v, 1) for v in tsz], 'rects', nrect)
    json.dump(dict(info=info, stand_vol=volume(stand), stand_area=surface(stand), stand_top=stand_top,
                   plate_size=[W, HTOT + TAB_H, T + REL]), open(f'{OUT}/info.json', 'w'), ensure_ascii=False, indent=1)
    np.savez_compressed('/home/claude/signs/masks.npz', **masks)
    print('plate', np.round(np.ptp(plate.reshape(-1,3),0),1), 'vol', volume(plate)/1000, 'stand', np.round(np.ptp(stand.reshape(-1,3),0),1), volume(stand)/1000)
