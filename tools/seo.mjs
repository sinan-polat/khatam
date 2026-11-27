// Builds real, crawlable pages from index.html so Google can index each product, category and the FAQ:
//   p/<id>.html                 one page per product
//   c/<kategori>.html           Til hjemmet, Ramadan & Eid, Til børnene
//   levering-og-faq.html        delivery and FAQ
// Each page is a full copy of the shop that opens directly on its own view (window.KHATAM_BOOT), with its own
// title, description, canonical address, share image and structured data. Plus sitemap.xml and robots.txt.
//
// Run after every change to index.html (products, texts, design) or when SITE_URL changes:   node tools/seo.mjs
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const html = readFileSync(join(root, 'index.html'), 'utf8');
const SITE = html.match(/const SITE_URL = '([^']+)'/)[1].replace(/\/?$/, '/');
const block = html.slice(html.indexOf('const P = ['), html.indexOf('const byId'));
const P = new Function(block + '; return P;')();
const FREE = +html.match(/const FREE = (\d+)/)[1];
const CATS = new Function(html.match(/const CATS = (\{[^}]+\});/)[0] + '; return CATS;')();
if (!html.includes('<!--seo-->') || !html.includes('<!--/seo-->')) throw new Error('index.html mangler <!--seo--> ... <!--/seo-->');

const esc = s => String(s).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');
const nice = n => n.charAt(0) + n.slice(1).toLowerCase();
const plain = s => String(s).replace(/<[^>]+>/g, '');

// The site's own home page keeps its WebSite/Organization data; sub-pages point back to it.
function page({ file, boot, title, desc, img, ld, depth, alt }) {
  const url = SITE + file;
  const head = `<!--seo-->
${depth ? '<base href="../">\n' : ''}<script>window.KHATAM_BOOT = ${JSON.stringify(boot)};</script>
<title>${esc(title)}</title>
<meta name="description" content="${esc(desc)}">
<link rel="canonical" href="${url}">
<meta property="og:site_name" content="QALAM">
<meta property="og:locale" content="da_DK">
<meta property="og:type" content="${ld && ld['@type'] === 'Product' ? 'product' : 'website'}">
<meta property="og:url" content="${url}">
<meta property="og:title" content="${esc(title)}">
<meta property="og:description" content="${esc(desc)}">
<meta property="og:image" content="${img}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="${esc(alt || title)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="${esc(title)}">
<meta name="twitter:description" content="${esc(desc)}">
<meta name="twitter:image" content="${img}">
${ld ? `<script type="application/ld+json">${JSON.stringify(ld)}</script>\n` : ''}<!--/seo-->`;
  const out = html.replace(/<!--seo-->[\s\S]*?<!--\/seo-->/, head);
  mkdirSync(dirname(join(root, file)), { recursive: true });
  writeFileSync(join(root, file), out);
  return url;
}
const crumbs = items => ({ '@type': 'BreadcrumbList', itemListElement: items.map(([name, item], i) => ({ '@type': 'ListItem', position: i + 1, name, item })) });

const urls = [SITE];
const og = key => existsSync(join(root, `img/og/${key}.jpg`)) ? `${SITE}img/og/${key}.jpg` : `${SITE}img/og/forside.jpg`;
const photos = id => [1, 2, 3].map(n => `img/foto/${id}-${n}.webp`).filter(f => existsSync(join(root, f))).map(f => SITE + f);
const RETURNABLE = p => p.personal === 'none' || p.personal === 'greeting';
const ORG = { '@type': 'Organization', name: 'QALAM', url: SITE };
const SHIPPING = { '@type': 'OfferShippingDetails',
  shippingRate: { '@type': 'MonetaryAmount', value: '45', currency: 'DKK' },
  shippingDestination: { '@type': 'DefinedRegion', addressCountry: 'DK' },
  deliveryTime: { '@type': 'ShippingDeliveryTime',
    handlingTime: { '@type': 'QuantitativeValue', minValue: 4, maxValue: 6, unitCode: 'DAY' },
    transitTime: { '@type': 'QuantitativeValue', minValue: 1, maxValue: 3, unitCode: 'DAY' } } };
const returns = p => RETURNABLE(p)
  ? { '@type': 'MerchantReturnPolicy', applicableCountry: 'DK', returnPolicyCategory: 'https://schema.org/MerchantReturnFiniteReturnWindow', merchantReturnDays: 14,
      returnMethod: 'https://schema.org/ReturnByMail', returnFees: 'https://schema.org/ReturnShippingFees', merchantReturnLink: SITE + 'levering-og-faq.html' }
  : { '@type': 'MerchantReturnPolicy', applicableCountry: 'DK', returnPolicyCategory: 'https://schema.org/MerchantReturnNotPermitted', merchantReturnLink: SITE + 'levering-og-faq.html' };
const feed = [];
for (const p of P) {
  const file = `p/${p.id}.html`, render = existsSync(join(root, `img/${p.id}.webp`)) ? `${SITE}img/${p.id}.webp` : `${SITE}img/${p.imgs[0]}.webp`, images = [...photos(p.id), render];
  const cat = p.cats.find(c => CATS[c]) || 'hjem';
  const name = `${nice(p.name)} – ${p.type}`;
  urls.push(page({
    file, depth: 1, boot: `/p/${p.id}`, img: og(p.id), alt: name,
    title: `${name} | QALAM`, desc: plain(p.desc),
    ld: { '@context': 'https://schema.org', '@type': 'Product', name: `${nice(p.name)} ${p.ar}`, description: plain(p.desc), image: images,
      brand: { '@type': 'Brand', name: 'QALAM' }, sku: p.id, category: CATS[cat],
      offers: { '@type': 'Offer', price: String(p.price), priceCurrency: 'DKK', availability: 'https://schema.org/InStock', itemCondition: 'https://schema.org/NewCondition',
        url: SITE + file, seller: ORG, shippingDetails: { ...SHIPPING, shippingRate: { '@type': 'MonetaryAmount', value: p.price >= FREE ? '0' : '45', currency: 'DKK' } }, hasMerchantReturnPolicy: returns(p) } },
  }));
  feed.push({ p, name, link: SITE + file, images, cat });
}
const CAT_TXT = {
  hjem: ['Til hjemmet – personlige islamiske gaver | QALAM', 'Hyldeskilte, dørskilte og nøglebakke med arabisk kalligrafi i guld. Designet og lavet i Danmark.', 'maktaba'],
  ramadan: ['Ramadan & Eid – gaver og pynt | QALAM', 'Bordskilte med Ramadan Mubarak og Eid Mubarak, Eidiyya-æsker med barnets navn og gaveæsker. Bestil senest 25. januar.', 'mubarak'],
  born: ['Til børnene – Eid-gaver med navn | QALAM', 'Eidiyya-æsker og gaver med barnets navn i guld på arabisk og latin. Designet og lavet i Danmark.', 'eidiyya'],
};
for (const [k, [title, desc, im]] of Object.entries(CAT_TXT)) {
  if (!CATS[k]) continue;
  urls.push(page({ file: `c/${k}.html`, depth: 1, boot: `/?c=${k}`, title, desc, img: og(k), alt: title,
    ld: { '@context': 'https://schema.org', '@type': 'CollectionPage', name: CATS[k], url: `${SITE}c/${k}.html`, breadcrumb: crumbs([['QALAM', SITE], [CATS[k], `${SITE}c/${k}.html`]]) } }));
}
urls.push(page({ file: 'levering-og-faq.html', depth: 0, boot: '/info', img: og('forside'),
  title: 'Levering, retur og spørgsmål | QALAM', desc: 'Fragt, leveringstid, Ramadan-frist, returret for personlige varer og svar på de mest stillede spørgsmål.', ld: null }));

const today = new Date().toISOString().slice(0, 10);
writeFileSync(join(root, 'sitemap.xml'), `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls.map(u => `  <url><loc>${u}</loc><lastmod>${today}</lastmod></url>`).join('\n')}
</urlset>
`);
// Google Merchant Center product feed (free listings and Shopping ads): add https://qalam.dk/products.xml as a scheduled feed
const x = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
writeFileSync(join(root, 'products.xml'), `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:g="http://base.google.com/ns/1.0">
<channel>
<title>QALAM</title>
<link>${SITE}</link>
<description>Arabisk kalligrafi og islamiske gaver til hjemmet</description>
${feed.map(({ p, name, link, images, cat }) => `<item>
  <g:id>${p.id}</g:id>
  <g:title>${x(name)}</g:title>
  <g:description>${x(plain(p.desc) + (p.details ? ' ' + plain(p.details) : ''))}</g:description>
  <g:link>${link}</g:link>
  <g:image_link>${images[0]}</g:image_link>
${images.slice(1, 10).map(i => `  <g:additional_image_link>${i}</g:additional_image_link>`).join('\n')}
  <g:availability>in_stock</g:availability>
  <g:price>${p.price.toFixed(2)} DKK</g:price>
  <g:condition>new</g:condition>
  <g:brand>QALAM</g:brand>
  <g:identifier_exists>no</g:identifier_exists>
  <g:google_product_category>696</g:google_product_category>
  <g:product_type>${x(CATS[cat])}</g:product_type>
  <g:is_bundle>${p.id === 'gaveaeske' || p.id === 'maktaba' ? 'yes' : 'no'}</g:is_bundle>
  <g:shipping><g:country>DK</g:country><g:service>PostNord pakkeshop</g:service><g:price>${p.price >= FREE ? '0.00' : '45.00'} DKK</g:price></g:shipping>
</item>`).join('\n')}
</channel>
</rss>
`);
writeFileSync(join(root, 'robots.txt'), `User-agent: *\nAllow: /\nSitemap: ${SITE}sitemap.xml\n`);
console.log(`${urls.length - 1} sider, sitemap.xml, products.xml og robots.txt skrevet for ${SITE}`);
