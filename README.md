# KHATAM – webshop

Statisk webshop (HTML, CSS og JavaScript i én fil) til personlige islamiske gaver.
Ingen build-trin: siden kører direkte fra mappen.

## Indhold
```
index.html      hele siden (forside, produkter, kurv, kasse, levering/FAQ)
img/            produkt- og stemningsbilleder (.webp)
fonts/          Poppins, Italiana (logo) og Cairo (arabisk)
favicon.svg     ikon
404.html        sender ukendte adresser tilbage til forsiden
.nojekyll       får GitHub Pages til at vise filerne som de er
```

## Læg den på GitHub Pages
1. Opret et nyt repository på github.com, fx `khatam-site` (Public).
2. Upload alt indholdet af denne mappe (ikke selve zip-filen) med **Add file → Upload files**, eller:
   ```
   git init
   git add .
   git commit -m "KHATAM webshop"
   git branch -M main
   git remote add origin https://github.com/<dit-brugernavn>/khatam-site.git
   git push -u origin main
   ```
3. Gå til **Settings → Pages**. Vælg **Deploy from a branch**, branch `main`, mappe `/ (root)`, og gem.
4. Efter et minut ligger siden på `https://<dit-brugernavn>.github.io/khatam-site/`.

### Eget domæne (fx khatam.dk)
- I **Settings → Pages → Custom domain** skriver du `khatam.dk`. GitHub laver en `CNAME`-fil.
- Hos din domæneudbyder sættes DNS: fire A-records for `@` til GitHub Pages' IP-adresser
  (se GitHub-dokumentationen "Managing a custom domain") og en CNAME for `www` til `<dit-brugernavn>.github.io`.
- Slå **Enforce HTTPS** til, når certifikatet er klar.

## Før siden går live
- **Betaling:** Kassen er en prototype. GitHub Pages kan ikke køre server-kode, så Stripe skal kobles på enten
  med **Stripe Payment Links** (én pr. produkt) eller med en lille serverfunktion (fx Netlify/Vercel/Cloudflare)
  der opretter en Stripe Checkout-session ud fra kurven. Hemmelige Stripe-nøgler må aldrig ligge i dette repository.
- **Nyhedsbrev:** formularen viser kun en tak. Kobl den til fx Mailchimp eller Brevo.
- **Tekster:** udfyld `[UDFYLD]` (CVR og handelsbetingelser) i `index.html`.
- **Billeder:** stemningsbillederne er visualiseringer. Udskift dem med rigtige fotos med samme filnavn.

## Redigering
Produkter, priser og tekster står i `index.html` i listen `const P = [...]`.
Fragtgrænse og fragtpriser: `const FREE = 349, SHIP_PS = 45, SHIP_HOME = 59, HOME_UPGRADE = 15`.
