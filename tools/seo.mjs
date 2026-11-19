// Builds one static page per product (p/<id>.html) plus sitemap.xml and robots.txt.
// Each page carries its own title, description, share image and Product data for Google,
// then forwards the visitor to the live product page in index.html.
// Run after changing products or the domain:   node tools/seo.mjs
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const html = readFileSync(join(root, 'index.html'), 'utf8');
const SITE = html.match(/const SITE_URL = '([^']+)'/)[1].replace(/\/?$/, '/');
const block = html.slice(html.indexOf('const P = ['), html.indexOf('const byId'));
const P = new Function(block + '; return P;')();

const esc = s => String(s).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');
const nice = n => n.charAt(0) + n.slice(1).toLowerCase();
mkdirSync(join(root, 'p'), { recursive: true });

for (const p of P) {
  const url = `${SITE}p/${p.id}.html`, img = `${SITE}img/${p.imgs[0]}.webp`;
  const title = `${nice(p.name)} – ${p.type} | KHATAM`, desc = p.desc.replace(/<[^>]+>/g, '');
  const ld = { '@context': 'https://schema.org', '@type': 'Product', name: `${nice(p.name)} ${p.ar}`, description: desc, image: img,
    brand: { '@type': 'Brand', name: 'KHATAM' }, sku: p.id,
    offers: { '@type': 'Offer', price: String(p.price), priceCurrency: 'DKK', availability: 'https://schema.org/InStock', url } };
  writeFileSync(join(root, 'p', `${p.id}.html`), `<!doctype html>
<html lang="da"><head><meta charset="utf-8">
<title>${esc(title)}</title>
<meta name="description" content="${esc(desc)}">
<link rel="canonical" href="${url}">
<meta property="og:type" content="product"><meta property="og:title" content="${esc(title)}">
<meta property="og:description" content="${esc(desc)}"><meta property="og:image" content="${img}"><meta property="og:url" content="${url}">
<meta property="product:price:amount" content="${p.price}"><meta property="product:price:currency" content="DKK">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">${JSON.stringify(ld)}</script>
<meta http-equiv="refresh" content="0; url=../index.html#/p/${p.id}">
<script>location.replace('../index.html#/p/${p.id}' + (location.search ? '?' + location.search.slice(1) : ''));</script>
</head><body><a href="../index.html#/p/${p.id}">${esc(nice(p.name))}: ${esc(desc)}</a></body></html>
`);
}
writeFileSync(join(root, 'sitemap.xml'), `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>${SITE}</loc></url>
${P.map(p => `  <url><loc>${SITE}p/${p.id}.html</loc></url>`).join('\n')}
</urlset>
`);
writeFileSync(join(root, 'robots.txt'), `User-agent: *\nAllow: /\nSitemap: ${SITE}sitemap.xml\n`);
console.log(`${P.length} produktsider, sitemap.xml og robots.txt skrevet for ${SITE}`);
