// Builds real, crawlable pages from index.html so Google can index each product, category and the FAQ:
//   p/<id>.html                 one page per product
//   c/<kategori>.html           Til hjemmet, Ramadan & Eid, Til børnene
//   levering-og-faq.html        delivery and FAQ
// Each page is a full copy of the shop that opens directly on its own view (window.KHATAM_BOOT), with its own
// title, description, canonical address, share image and structured data. Plus sitemap.xml and robots.txt.
//
// Run after every change to index.html (products, texts, design) or when SITE_URL changes:   node tools/seo.mjs
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const html = readFileSync(join(root, 'index.html'), 'utf8');
const SITE = html.match(/const SITE_URL = '([^']+)'/)[1].replace(/\/?$/, '/');
const block = html.slice(html.indexOf('const P = ['), html.indexOf('const byId'));
const P = new Function(block + '; return P;')();
const CATS = new Function(html.match(/const CATS = (\{[^}]+\});/)[0] + '; return CATS;')();
if (!html.includes('<!--seo-->') || !html.includes('<!--/seo-->')) throw new Error('index.html mangler <!--seo--> ... <!--/seo-->');

const esc = s => String(s).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');
const nice = n => n.charAt(0) + n.slice(1).toLowerCase();
const plain = s => String(s).replace(/<[^>]+>/g, '');

// The site's own home page keeps its WebSite/Organization data; sub-pages point back to it.
function page({ file, boot, title, desc, img, ld, depth }) {
  const url = SITE + file;
  const head = `<!--seo-->
${depth ? '<base href="../">\n' : ''}<script>window.KHATAM_BOOT = ${JSON.stringify(boot)};</script>
<title>${esc(title)}</title>
<meta name="description" content="${esc(desc)}">
<link rel="canonical" href="${url}">
<meta property="og:site_name" content="KHATAM">
<meta property="og:type" content="${ld && ld['@type'] === 'Product' ? 'product' : 'website'}">
<meta property="og:url" content="${url}">
<meta property="og:title" content="${esc(title)}">
<meta property="og:description" content="${esc(desc)}">
<meta property="og:image" content="${img}">
<meta name="twitter:card" content="summary_large_image">
${ld ? `<script type="application/ld+json">${JSON.stringify(ld)}</script>\n` : ''}<!--/seo-->`;
  const out = html.replace(/<!--seo-->[\s\S]*?<!--\/seo-->/, head);
  mkdirSync(dirname(join(root, file)), { recursive: true });
  writeFileSync(join(root, file), out);
  return url;
}
const crumbs = items => ({ '@type': 'BreadcrumbList', itemListElement: items.map(([name, item], i) => ({ '@type': 'ListItem', position: i + 1, name, item })) });

const urls = [SITE];
for (const p of P) {
  const file = `p/${p.id}.html`, img = `${SITE}img/${p.imgs[0]}.webp`;
  const cat = p.cats.find(c => CATS[c]) || 'hjem';
  urls.push(page({
    file, depth: 1, boot: `/p/${p.id}`, img,
    title: `${nice(p.name)} – ${p.type} | KHATAM`, desc: plain(p.desc),
    ld: { '@context': 'https://schema.org', '@type': 'Product', name: `${nice(p.name)} ${p.ar}`, description: plain(p.desc), image: img,
      brand: { '@type': 'Brand', name: 'KHATAM' }, sku: p.id, category: CATS[cat],
      offers: { '@type': 'Offer', price: String(p.price), priceCurrency: 'DKK', availability: 'https://schema.org/InStock', url: SITE + file,
        shippingDetails: { '@type': 'OfferShippingDetails', shippingDestination: { '@type': 'DefinedRegion', addressCountry: 'DK' } } } },
  }));
}
const CAT_TXT = {
  hjem: ['Til hjemmet – personlige islamiske gaver | KHATAM', 'Hyldeskilte, dørskilte og nøglebakke med arabisk kalligrafi i guld. Designet og lavet i Danmark.', 'maktaba'],
  ramadan: ['Ramadan & Eid – gaver og pynt | KHATAM', 'Bordskilte med Ramadan Mubarak og Eid Mubarak, Eidiyya-æsker med barnets navn og gaveæsker. Bestil senest 25. januar.', 'mubarak'],
  born: ['Til børnene – Eid-gaver med navn | KHATAM', 'Eidiyya-æsker og gaver med barnets navn i guld på arabisk og latin. Designet og lavet i Danmark.', 'eidiyya'],
};
for (const [k, [title, desc, im]] of Object.entries(CAT_TXT)) {
  if (!CATS[k]) continue;
  urls.push(page({ file: `c/${k}.html`, depth: 1, boot: `/?c=${k}`, title, desc, img: `${SITE}img/${im}.webp`,
    ld: { '@context': 'https://schema.org', '@type': 'CollectionPage', name: CATS[k], url: `${SITE}c/${k}.html`, breadcrumb: crumbs([['KHATAM', SITE], [CATS[k], `${SITE}c/${k}.html`]]) } }));
}
urls.push(page({ file: 'levering-og-faq.html', depth: 0, boot: '/info', img: `${SITE}img/maktaba.webp`,
  title: 'Levering, retur og spørgsmål | KHATAM', desc: 'Fragt, leveringstid, Ramadan-frist, returret for personlige varer og svar på de mest stillede spørgsmål.', ld: null }));

writeFileSync(join(root, 'sitemap.xml'), `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls.map(u => `  <url><loc>${u}</loc></url>`).join('\n')}
</urlset>
`);
writeFileSync(join(root, 'robots.txt'), `User-agent: *\nAllow: /\nSitemap: ${SITE}sitemap.xml\n`);
console.log(`${urls.length - 1} sider, sitemap.xml og robots.txt skrevet for ${SITE}`);
