"""KHATAM brand – logo SVGs (text embedded via @font-face so they render anywhere a browser renders SVG)."""
import base64, math, os
B = '/home/claude/brand'
OUT = f'{B}/out/01_Logo'
C = dict(onyx='#161513', emerald='#1E3A2F', gold='#C8A04E', sand='#EAE0CE', ivory='#F8F4EC')
def font_b64(f): return base64.b64encode(open(f'{B}/fonts/{f}', 'rb').read()).decode()
FONTS = f"""<style>
@font-face{{font-family:'Italiana';src:url(data:font/ttf;base64,{font_b64('Italiana-Regular.ttf')}) format('truetype');}}
@font-face{{font-family:'InstrumentSans';font-weight:600;src:url(data:font/ttf;base64,{font_b64('InstrumentSans-Bold.ttf')}) format('truetype');}}
@font-face{{font-family:'Cairo';font-weight:800;src:url(data:font/woff2;base64,{font_b64('Cairo.woff2')}) format('woff2');}}
</style>"""

def seal(cx, cy, s, col, sw=1.0):
    """khatam seal: interlaced 8-point star (two squares), inner octagon, centre star. s = outer radius."""
    sq = lambda r, rot: ' '.join(f'{cx+math.cos(rot+k*math.pi/2)*r:.2f},{cy+math.sin(rot+k*math.pi/2)*r:.2f}' for k in range(4))
    oc = ' '.join(f'{cx+math.cos(math.pi/8+k*math.pi/4)*s*0.47:.2f},{cy+math.sin(math.pi/8+k*math.pi/4)*s*0.47:.2f}' for k in range(8))
    st = ' '.join(f'{cx+math.cos(-math.pi/2+k*math.pi/8)*(s*0.17 if k%2==0 else s*0.085):.2f},{cy+math.sin(-math.pi/2+k*math.pi/8)*(s*0.17 if k%2==0 else s*0.085):.2f}' for k in range(16))
    w = s*0.055*sw
    return (f'<g fill="none" stroke="{col}" stroke-linejoin="miter" stroke-width="{w:.2f}">'
            f'<polygon points="{sq(s, math.pi/4)}"/><polygon points="{sq(s, 0)}"/>'
            f'<polygon points="{sq(s*0.86, math.pi/4)}" stroke-width="{w*0.45:.2f}"/><polygon points="{sq(s*0.86, 0)}" stroke-width="{w*0.45:.2f}"/>'
            f'<polygon points="{oc}" stroke-width="{w*0.6:.2f}"/></g>'
            f'<polygon points="{st}" fill="{col}"/>')

def svg(w, h, body, bg=None):
    r = f'<rect width="{w}" height="{h}" fill="{bg}"/>' if bg else ''
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">{FONTS}{r}{body}</svg>'

def primary(fg, accent, bg=None):
    W, H = 900, 240
    body = seal(120, 120, 92, accent)
    body += f'<text x="262" y="138" font-family="Italiana" font-size="118" letter-spacing="30" fill="{fg}">KHATAM</text>'
    body += f'<line x1="268" y1="168" x2="874" y2="168" stroke="{accent}" stroke-width="1.6"/>'
    body += f'<text x="268" y="206" font-family="InstrumentSans" font-weight="600" font-size="22" letter-spacing="9.5" fill="{accent}">ISLAMISK DESIGN · DANMARK</text>'
    return svg(W, H, body, bg)

def stacked(fg, accent, bg=None):
    W, H = 620, 640
    body = seal(310, 170, 130, accent)
    body += f'<text x="310" y="430" font-family="Italiana" font-size="112" letter-spacing="26" fill="{fg}" text-anchor="middle">KHATAM</text>'
    body += f'<text x="310" y="506" font-family="Cairo" font-weight="800" font-size="40" fill="{accent}" text-anchor="middle" direction="rtl">خاتم</text>'
    body += f'<line x1="150" y1="540" x2="470" y2="540" stroke="{accent}" stroke-width="1.5"/>'
    body += f'<text x="310" y="584" font-family="InstrumentSans" font-weight="600" font-size="20" letter-spacing="8" fill="{fg}" text-anchor="middle">ISLAMISK DESIGN · DANMARK</text>'
    return svg(W, H, body, bg)

def seal_only(col, bg=None, size=600):
    return svg(size, size, seal(size/2, size/2, size*0.42, col), bg)

def arabic(fg, accent, bg=None):
    W, H = 600, 300
    body = seal(300, 70, 48, accent, 1.2)
    body += f'<text x="300" y="232" font-family="Cairo" font-weight="800" font-size="110" fill="{fg}" text-anchor="middle" direction="rtl">خاتم</text>'
    return svg(W, H, body, bg)

def profile(bg, col):
    S = 1080
    ring = f'<circle cx="540" cy="540" r="470" fill="none" stroke="{col}" stroke-width="3"/><circle cx="540" cy="540" r="452" fill="none" stroke="{col}" stroke-width="1.2"/>'
    return svg(S, S, ring + seal(540, 540, 330, col), bg)

FILES = {
    'khatam_logo_primaer_moerk': primary(C['onyx'], C['gold']),
    'khatam_logo_primaer_lys': primary(C['ivory'], C['gold']),
    'khatam_logo_primaer_paa_onyx': primary(C['ivory'], C['gold'], C['onyx']),
    'khatam_logo_primaer_paa_smaragd': primary(C['ivory'], C['gold'], C['emerald']),
    'khatam_logo_stablet_moerk': stacked(C['onyx'], C['gold']),
    'khatam_logo_stablet_lys': stacked(C['ivory'], C['gold']),
    'khatam_logo_stablet_paa_onyx': stacked(C['ivory'], C['gold'], C['onyx']),
    'khatam_logo_stablet_paa_sand': stacked(C['onyx'], C['gold'], C['sand']),
    'khatam_segl_guld': seal_only(C['gold']),
    'khatam_segl_onyx': seal_only(C['onyx']),
    'khatam_segl_hvid': seal_only(C['ivory']),
    'khatam_arabisk_moerk': arabic(C['onyx'], C['gold']),
    'khatam_arabisk_lys': arabic(C['ivory'], C['gold']),
    'khatam_profilbillede_instagram': profile(C['onyx'], C['gold']),
}
if __name__ == '__main__':
    os.makedirs(f'{OUT}/svg', exist_ok=True)
    for k, v in FILES.items():
        open(f'{OUT}/svg/{k}.svg', 'w').write(v)
    print(len(FILES), 'svg')
