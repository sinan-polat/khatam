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

// ---- keep in step with index.html (const P, SUBJECTS and FREE / SHIP_*) ----
const PRODUCTS = {
  hyldeskilt: { name: 'Hyldeskilt', type: 'Ét skilt til bogreolen', price: 69, pick: 1 },
  maktaba:    { name: 'Maktaba',    type: 'Sæt med 4 hyldeskilte',  price: 249, pick: 4 },
  lanterne:   { name: 'Lanterne',   type: 'Lanterne med LED-lys',
                sizes: { lille: ['Lille', 99], mellem: ['Mellem', 149], stor: ['Stor', 199], saet: ['Sæt med alle 3', 275] } },
};
const FREE = 349, SHIP_PS = 45, SHIP_HOME = 59, HOME_UPGRADE = 15;
const SUBJECTS = { quran: 'Quran', tafsir: 'Tafsir', hadith: 'Hadith', aqidah: 'Aqidah', fiqh: 'Fiqh', seerah: 'Seerah', tazkiyah: 'Tazkiyah', adab: 'Adab', tarikh: 'Tarikh' };
const ALLOWED_ORIGINS = ['https://qalam.dk', 'https://www.qalam.dk', 'https://sinan-polat.github.io', 'http://localhost:8765', 'http://127.0.0.1:8765'];

const clean = (s, n = 40) => String(s ?? '').replace(/[<>\u0000-\u001f]/g, '').trim().slice(0, n);
const price = it => { const p = PRODUCTS[it.id]; return p.sizes ? p.sizes[it.size][1] : p.price; };
const title = it => { const p = PRODUCTS[it.id]; return p.sizes ? `${p.name} – ${p.sizes[it.size][0].toLowerCase()}` : `${p.name} – ${p.type}`; };
function describe(it) {
  if (it.subjects) return 'Emner: ' + it.subjects.map(k => SUBJECTS[k]).join(', ');
  return it.size === 'saet' ? 'Lille, mellem og stor · 3 LED-lys med batteri' : 'Inkl. LED-lys med batteri';
}

function readItems(raw) {
  if (!Array.isArray(raw) || !raw.length || raw.length > 30) throw new Error('Kurven er tom eller ugyldig.');
  return raw.map(r => {
    const p = PRODUCTS[r.id]; if (!p) throw new Error('Varen findes ikke længere. Tøm kurven og prøv igen.');
    const it = { id: r.id, qty: Math.max(1, Math.min(20, parseInt(r.qty, 10) || 1)) };
    if (p.sizes) { if (!p.sizes[r.size]) throw new Error('Vælg en størrelse.'); it.size = r.size; }
    if (p.pick) {
      const s = Array.isArray(r.subjects) ? r.subjects.filter(k => SUBJECTS[k]) : [];
      if (s.length !== p.pick) throw new Error(p.pick === 1 ? 'Vælg et emne.' : 'Vælg 4 emner.');
      it.subjects = s;
    }
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
  const goods = items.reduce((a, it) => a + price(it) * it.qty, 0);
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
    price_data: { currency: 'dkk', unit_amount: price(it) * 100,
      product_data: { name: title(it), description: describe(it).slice(0, 480) } },
  }));
  if (ship) line_items.push({ quantity: 1, price_data: { currency: 'dkk', unit_amount: ship * 100,
    product_data: { name: home ? 'Levering til døren (PostNord)' : 'Levering til PostNord pakkeshop' } } });

  const metadata = { ordre: order, levering: home ? 'Til døren' : 'Pakkeshop', telefon: phone, besked: clean(c.note, 480) };
  items.forEach((it, i) => { metadata[`vare_${i + 1}`] = `${it.qty} × ${title(it)}: ${describe(it)}`.slice(0, 480); });

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
