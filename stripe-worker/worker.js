// QALAM – Stripe Checkout via Cloudflare Workers
//
// The shop on GitHub Pages sends the cart here. This worker looks up the real prices (never trusts prices
// from the browser), adds shipping, and creates a Stripe Checkout Session. The customer is then sent to
// Stripe's own payment page (MobilePay, card, Apple Pay, Google Pay – whatever is enabled in the Stripe dashboard).
//
// Secret: STRIPE_SECRET_KEY (set it in the Cloudflare dashboard: Worker → Settings → Variables and Secrets → Add → type "Secret").
// Optional variable: SITE_URL (default https://qalam.dk).
//
// Endpoints
//   POST /checkout          body: { items:[...], checkout:{...} }   → { url }
//   GET  /session?id=cs_... → { paid, order, email, total }

// ---- keep in step with index.html (const P and const FREE / SHIP_*) ----
const PRODUCTS = {
  gaveaeske: { name: 'Gaveæsken', type: 'Gaveæske til hjemmet med 3 dele', price: 499 },
  eidiyya:   { name: 'Eidiyya',   type: 'Æske med navn',                   price: 129 },
  mubarak:   { name: 'Mubarak',   type: 'Bordskilt',                       price: 129 },
  bayt:      { name: 'Bayt',      type: 'Navneskilt til døren',            price: 179 },
  usra:      { name: 'Usra',      type: 'Tandbørsteholder til familien',   price: 249 },
  tabaq:     { name: 'Tabaq',     type: 'Nøglebakke',                      price: 179 },
  maktaba:   { name: 'Maktaba',   type: 'Sæt med 4 hyldeskilte',           price: 249 },
};
const FREE = 349, SHIP_PS = 45, SHIP_HOME = 59, HOME_UPGRADE = 15;
const COLORS = { sort: 'Sort & guld', smaragd: 'Smaragd & guld' };
const SHELF = { quran: 'Quran', tafsir: 'Tafsir', hadith: 'Hadith', aqidah: 'Aqidah', fiqh: 'Fiqh', seerah: 'Seerah', tazkiyah: 'Tazkiyah', historie: 'Historie' };
const ALLOWED_ORIGINS = ['https://qalam.dk', 'https://www.qalam.dk', 'https://sinan-polat.github.io', 'http://localhost:8765', 'http://127.0.0.1:8765'];

const clean = (s, n = 40) => String(s ?? '').replace(/[<>\u0000-\u001f]/g, '').trim().slice(0, n);

function describe(it) {
  const parts = [COLORS[it.color] || COLORS.sort];
  if (it.name) parts.push((it.id === 'bayt' || it.id === 'gaveaeske' ? 'Familien ' : '') + it.name + (it.ar ? ` (${it.ar})` : ''));
  if (it.greeting) parts.push(it.greeting === 'eid' ? 'Eid Mubarak' : 'Ramadan Mubarak');
  if (it.names?.length) parts.push('Navne: ' + it.names.map((n, k) => n + (it.ars?.[k] ? ` (${it.ars[k]})` : '')).join(', '));
  if (it.shelf?.length) parts.push('Skilte: ' + it.shelf.map(k => SHELF[k] || k).join(', '));
  return parts.join(' · ');
}

function readItems(raw) {
  if (!Array.isArray(raw) || !raw.length || raw.length > 30) throw new Error('Kurven er tom eller ugyldig.');
  return raw.map(r => {
    const p = PRODUCTS[r.id]; if (!p) throw new Error('Ukendt vare: ' + clean(r.id, 20));
    const qty = Math.max(1, Math.min(20, parseInt(r.qty, 10) || 1));
    const it = { id: r.id, qty, color: COLORS[r.color] ? r.color : 'sort', name: clean(r.name, 20), ar: clean(r.ar, 30) };
    if (r.greeting) it.greeting = r.greeting === 'eid' ? 'eid' : 'ramadan';
    if (Array.isArray(r.names)) { it.names = r.names.slice(0, 4).map(n => clean(n, 16)).filter(Boolean); it.ars = (r.ars || []).slice(0, 4).map(a => clean(a, 24)); }
    if (Array.isArray(r.shelf)) it.shelf = r.shelf.slice(0, 4).map(k => clean(k, 12)).filter(k => SHELF[k]);
    return it;
  });
}

// Stripe's API takes form-encoded nested keys: line_items[0][price_data][currency]=dkk
function form(obj, prefix = '', out = new URLSearchParams()) {
  for (const [k, v] of Object.entries(obj)) {
    if (v === undefined || v === null || v === '') continue;
    const key = prefix ? `${prefix}[${k}]` : k;
    if (typeof v === 'object') form(v, key, out); else out.append(key, String(v));
  }
  return out;
}
async function stripe(env, method, path, body) {
  const res = await fetch('https://api.stripe.com/v1/' + path, {
    method, body: body ? form(body) : undefined,
    headers: { Authorization: 'Bearer ' + env.STRIPE_SECRET_KEY, 'Content-Type': 'application/x-www-form-urlencoded' },
  });
  const data = await res.json();
  if (!res.ok) { console.log('Stripe error', JSON.stringify(data.error || data)); throw new Error('Betalingen kunne ikke startes. Prøv igen om lidt.'); }
  return data;
}

async function createCheckout(req, env) {
  const { items: raw, checkout: c = {} } = await req.json();
  const items = readItems(raw);
  const goods = items.reduce((a, it) => a + PRODUCTS[it.id].price * it.qty, 0);
  const free = goods >= FREE, home = c.ship === 'home';
  const ship = home ? (free ? HOME_UPGRADE : SHIP_HOME) : (free ? 0 : SHIP_PS);
  const site = (env.SITE_URL || 'https://qalam.dk').replace(/\/$/, '');
  // short, readable order number: day + month + 3 digits, e.g. 2711-482
  const dm = new Intl.DateTimeFormat('da-DK', { timeZone: 'Europe/Copenhagen', day: '2-digit', month: '2-digit' }).formatToParts(new Date());
  const order = dm.find(p => p.type === 'day').value + dm.find(p => p.type === 'month').value + '-' + (100 + Math.floor(Math.random() * 900));
  const email = clean(c.email, 120), phone = clean(c.phone, 20);
  const name = clean(`${c.fname || ''} ${c.lname || ''}`, 80);

  const line_items = items.map(it => ({
    quantity: it.qty,
    price_data: { currency: 'dkk', unit_amount: PRODUCTS[it.id].price * 100,
      product_data: { name: `${PRODUCTS[it.id].name} – ${PRODUCTS[it.id].type}`, description: describe(it).slice(0, 480) } },
  }));
  if (ship) line_items.push({ quantity: 1, price_data: { currency: 'dkk', unit_amount: ship * 100,
    product_data: { name: home ? 'Levering til døren (PostNord)' : 'Levering til PostNord pakkeshop' } } });

  const metadata = { ordre: order, levering: home ? 'Til døren' : 'Pakkeshop', telefon: phone, besked: clean(c.note, 480) };
  items.forEach((it, i) => { metadata[`vare_${i + 1}`] = `${it.qty} × ${PRODUCTS[it.id].name}: ${describe(it)}`.slice(0, 480); });

  const session = await stripe(env, 'POST', 'checkout/sessions', {
    mode: 'payment', locale: 'da', client_reference_id: order,
    customer_email: /^\S+@\S+\.\S+$/.test(email) ? email : undefined,
    line_items, metadata,
    payment_intent_data: { description: `QALAM ordre ${order}`, metadata,
      shipping: c.addr ? { name: name || 'Kunde', phone, address: { line1: clean(c.addr, 120), postal_code: clean(c.zip, 4), city: clean(c.city, 60), country: 'DK' } } : undefined },
    success_url: `${site}/#/tak?session_id={CHECKOUT_SESSION_ID}`,
    cancel_url: `${site}/#/kasse`,
  });
  return { url: session.url };
}

async function sessionStatus(url, env) {
  const id = url.searchParams.get('id') || '';
  if (!/^cs_[A-Za-z0-9_]+$/.test(id)) throw new Error('Ugyldigt id.');
  const s = await stripe(env, 'GET', 'checkout/sessions/' + id);
  return { paid: s.payment_status === 'paid', order: s.client_reference_id, email: s.customer_details?.email || s.customer_email, total: (s.amount_total || 0) / 100 };
}

export default {
  async fetch(req, env) {
    const url = new URL(req.url), origin = req.headers.get('Origin') || '';
    const cors = { 'Access-Control-Allow-Origin': ALLOWED_ORIGINS.includes(origin) ? origin : ALLOWED_ORIGINS[0],
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS', 'Access-Control-Allow-Headers': 'Content-Type', Vary: 'Origin' };
    if (req.method === 'OPTIONS') return new Response(null, { headers: cors });
    const json = (data, status = 200) => new Response(JSON.stringify(data), { status, headers: { ...cors, 'Content-Type': 'application/json' } });
    try {
      if (!env.STRIPE_SECRET_KEY) return json({ error: 'Stripe-nøglen mangler på serveren.' }, 500);
      if (req.method === 'POST' && url.pathname === '/checkout') return json(await createCheckout(req, env));
      if (req.method === 'GET' && url.pathname === '/session') return json(await sessionStatus(url, env));
      return json({ ok: true, service: 'QALAM checkout' });
    } catch (e) { return json({ error: e.message || 'Der skete en fejl.' }, 400); }
  },
};
