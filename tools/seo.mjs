// Builds real, crawlable pages from index.html so Google can index each product and the FAQ:
//   p/<id>.html                 one page per product (hyldeskilt, maktaba, lanterne)
//   levering-og-faq.html        delivery, returns and FAQ
// Each page is a full copy of the shop that opens directly on its own view (window.KHATAM_BOOT), with its own
// title, description, canonical address, share image and structured data.
// Old product and category addresses become small redirect pages, so old links and Google results still work.
// Also writes sitemap.xml, robots.txt and products.xml (Google Merchant Center feed).
//
// Run after every change to index.html:   node tools/seo.mjs
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const html = readFileSync(join(root, 'index.html'), 'utf8');
const SITE = html.match(/const SITE_URL = '([^']+)'/)[1].replace(/\/?$/, '/');
const block = html.slice(html.indexOf('const P = ['), html.indexOf('const byId'));
const P = new Function(block + '; return P;')();
const FREE = +html.match(/const FREE = (\d+)/)[1];
const SHIP = +html.match(/SHIP_PS = (\d+)/)[1];
if (!html.includes('<!--seo-->') || !html.includes('<!--/seo-->')) throw new Error('index.html mangler <!--seo--> ... <!--/seo-->');

const esc = s => String(s).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');
const x = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

function page({ file, boot, title, desc, img, ld, depth, alt, type }) {
  const url = SITE + file;
  const head = `<!--seo-->
${depth ? '<base href="../">\n' : ''}<script>window.KHATAM_BOOT = ${JSON.stringify(boot)};</script>
<title>${esc(title)}</title>
<meta name="description" content="${esc(desc)}">
<link rel="canonical" href="${url}">
<meta property="og:site_name" content="QALAM">
<meta property="og:locale" content="da_DK">
<meta property="og:type" content="${type || 'website'}">
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
function redirect(file, to) {
  mkdirSync(dirname(join(root, file)), { recursive: true });
  writeFileSync(join(root, file), `<!DOCTYPE html><html lang="da"><head><meta charset="utf-8"><title>QALAM</title><meta name="robots" content="noindex"><link rel="canonical" href="${to}"><meta http-equiv="refresh" content="0; url=${to}"><script>location.replace(${JSON.stringify(to)})</script></head><body><a href="${to}">Gå til QALAM</a></body></html>\n`);
}

const og = key => existsSync(join(root, `img/og/${key}.jpg`)) ? `${SITE}img/og/${key}.jpg` : `${SITE}img/og/forside.jpg`;
const pics = p => p.imgs.map(k => `${SITE}img/p/${k}.webp`);
const ORG = { '@type': 'Organization', name: 'QALAM', url: SITE };
const shipping = price => ({ '@type': 'OfferShippingDetails',
  shippingRate: { '@type': 'MonetaryAmount', value: String(price >= FREE ? 0 : SHIP), currency: 'DKK' },
  shippingDestination: { '@type': 'DefinedRegion', addressCountry: 'DK' },
  deliveryTime: { '@type': 'ShippingDeliveryTime',
    handlingTime: { '@type': 'QuantitativeValue', minValue: 3, maxValue: 5, unitCode: 'DAY' },
    transitTime: { '@type': 'QuantitativeValue', minValue: 1, maxValue: 3, unitCode: 'DAY' } } });
const RETURNS = { '@type': 'MerchantReturnPolicy', applicableCountry: 'DK', returnPolicyCategory: 'https://schema.org/MerchantReturnFiniteReturnWindow', merchantReturnDays: 14,
  returnMethod: 'https://schema.org/ReturnByMail', returnFees: 'https://schema.org/ReturnShippingFees', merchantReturnLink: SITE + 'levering-og-faq.html' };
const offer = (price, url, extra = {}) => ({ '@type': 'Offer', price: String(price), priceCurrency: 'DKK', availability: 'https://schema.org/InStock',
  itemCondition: 'https://schema.org/NewCondition', url, seller: ORG, shippingDetails: shipping(price), hasMerchantReturnPolicy: RETURNS, ...extra });

const urls = [SITE], feed = [];
for (const p of P) {
  const file = `p/${p.id}.html`, url = SITE + file, name = `${p.name} – ${p.type}`, images = pics(p);
  const desc = `${p.lead} ${p.sizes ? 'Fra ' + Math.min(...p.sizes.map(s => s.price)) : p.price} kr. Gratis fragt over ${FREE} kr.`;
  let ld;
  if (p.sizes) {
    ld = { '@context': 'https://schema.org', '@type': 'ProductGroup', name: `${p.name} ${p.ar}`.trim(), description: p.lead + ' ' + p.details, image: images,
      brand: { '@type': 'Brand', name: 'QALAM' }, productGroupID: p.id, variesBy: ['https://schema.org/size'], url,
      hasVariant: p.sizes.map(s => ({ '@type': 'Product', name: `${p.name} – ${s.label.toLowerCase()}`, sku: `${p.id}-${s.id}`, size: s.label, image: images[0],
        offers: offer(s.price, url) })) };
  } else {
    ld = { '@context': 'https://schema.org', '@type': 'Product', name: `${p.name} ${p.ar}`.trim(), description: p.lead + ' ' + p.details, image: images,
      brand: { '@type': 'Brand', name: 'QALAM' }, sku: p.id, offers: offer(p.price, url) };
  }
  urls.push(page({ file, depth: 1, boot: `/p/${p.id}`, img: og(p.id), alt: name, type: 'product', title: `${name} | QALAM`, desc, ld }));
  const variants = p.sizes ? p.sizes.map(s => ({ id: `${p.id}-${s.id}`, title: `${p.name} – ${s.label.toLowerCase()}`, price: s.price, size: s.label, group: p.id }))
    : [{ id: p.id, title: name, price: p.price }];
  for (const v of variants) feed.push({ ...v, desc: p.lead + ' ' + p.details, link: url, images });
}
urls.push(page({ file: 'levering-og-faq.html', depth: 0, boot: '/info', img: og('forside'),
  title: 'Levering, retur og spørgsmål | QALAM', desc: `Fragt, leveringstid, Ramadan-frist, 14 dages returret og svar på de mest stillede spørgsmål. Gratis fragt over ${FREE} kr.`, ld: null }));

// old addresses → new
const OLD = { bayt: 'p/hyldeskilt.html', mubarak: 'p/lanterne.html', tabaq: '', eidiyya: '', gaveaeske: '', usra: '' };
for (const [id, to] of Object.entries(OLD)) redirect(`p/${id}.html`, SITE + to);
for (const c of ['hjem', 'ramadan', 'born']) redirect(`c/${c}.html`, c === 'ramadan' ? SITE + 'p/lanterne.html' : SITE);

const today = new Date().toISOString().slice(0, 10);
writeFileSync(join(root, 'sitemap.xml'), `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls.map(u => `  <url><loc>${u}</loc><lastmod>${today}</lastmod></url>`).join('\n')}
</urlset>
`);
writeFileSync(join(root, 'robots.txt'), `User-agent: *\nAllow: /\n\nSitemap: ${SITE}sitemap.xml\n`);
// Google Merchant Center: add https://qalam.dk/products.xml as a scheduled feed
writeFileSync(join(root, 'products.xml'), `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:g="http://base.google.com/ns/1.0">
<channel>
<title>QALAM</title>
<link>${SITE}</link>
<description>Hyldeskilte og lanterner med arabisk kalligrafi</description>
${feed.map(f => `<item>
  <g:id>${f.id}</g:id>
  <g:title>${x(f.title)}</g:title>
  <g:description>${x(f.desc)}</g:description>
  <g:link>${f.link}</g:link>
  <g:image_link>${f.images[0]}</g:image_link>
${f.images.slice(1, 10).map(i => `  <g:additional_image_link>${i}</g:additional_image_link>`).join('\n')}
  <g:availability>in_stock</g:availability>
  <g:condition>new</g:condition>
  <g:price>${f.price}.00 DKK</g:price>
  <g:brand>QALAM</g:brand>
  <g:identifier_exists>no</g:identifier_exists>
  <g:google_product_category>Home &amp; Garden &gt; Decor</g:google_product_category>
${f.group ? `  <g:item_group_id>${f.group}</g:item_group_id>\n  <g:size>${x(f.size)}</g:size>\n` : ''}  <g:shipping><g:country>DK</g:country><g:service>PostNord pakkeshop</g:service><g:price>${f.price >= FREE ? 0 : SHIP}.00 DKK</g:price></g:shipping>
</item>`).join('\n')}
</channel>
</rss>
`);
console.log(`OK: ${urls.length} sider, ${feed.length} varer i feed`);
