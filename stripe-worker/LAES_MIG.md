# Stripe-betaling via Cloudflare Workers

Siden ligger på GitHub Pages, og den kan ikke gemme hemmelige nøgler. Derfor laver denne lille worker betalingen:
kurven sendes hertil, workeren slår de rigtige priser op (den stoler aldrig på priser fra browseren), lægger fragt til og opretter en
Stripe Checkout-side. Kunden betaler hos Stripe og kommer tilbage til `qalam.dk/#/tak`, hvor betalingen bliver bekræftet.

## Opsætning (ca. 10 min)

1. **Opret Cloudflare-konto** på dash.cloudflare.com (gratis).
2. **Workers & Pages → Create → Create Worker.** Kald den `khatam-checkout` og tryk **Deploy**.
3. Tryk **Edit code**, slet alt i editoren, og indsæt hele indholdet af `worker.js`. Tryk **Deploy**.
4. **Stripe-nøglen:** I Stripe → Developers → API keys kopierer du **Secret key** (`sk_test_...` til test, `sk_live_...` når du går live).
   I Cloudflare: din worker → **Settings → Variables and Secrets → Add** → Type **Secret**, navn `STRIPE_SECRET_KEY`, indsæt nøglen → **Deploy**.
   Nøglen må aldrig stå i koden eller på GitHub.
5. Kopiér workerens adresse (fx `https://khatam-checkout.dit-navn.workers.dev`) og skriv den i `index.html`:
   `const CHECKOUT_API = 'https://khatam-checkout.dit-navn.workers.dev';`
   Kør derefter `node tools/seo.mjs`, commit og push.
6. **Betalingsmetoder:** I Stripe → Settings → Payment methods slår du MobilePay, kort, Apple Pay og Google Pay til.
   Workeren bruger automatisk dem, der er slået til.

## Test
Brug først `sk_test_`-nøglen. Betal med testkortet `4242 4242 4242 4242`, en dato i fremtiden og en vilkårlig CVC.
Ordren dukker op i Stripe under **Payments** (husk "Test mode"). Ordrenummer, navne, farver, adresse, telefon og besked står under **Metadata**.

## Når du ændrer priser eller produkter
Ret både `const P` i `index.html` **og** `PRODUCTS` øverst i `worker.js`, og deploy workeren igen. Det samme gælder fragtpriserne.
