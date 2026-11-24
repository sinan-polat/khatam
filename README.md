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

## Nye funktioner (salg og synlighed)

- **Produktfotos:** Læg rigtige fotos i `img/foto/` som `<id>-1.webp` op til `-3.webp`. Se `img/foto/LAES_MIG.txt`.
- **Anmeldelser:** Tilføj rigtige anmeldelser i `const REVIEWS = []` øverst i `index.html`. Sektionen vises først, når der er mindst én.
- **Ramadan-frist:** Datoen står i `RAMADAN_DEADLINE`. Nedtællingen forsvinder selv efter fristen.
- **Statistik:** Opret en konto på plausible.io og skriv domænet i `ANALYTICS_DOMAIN`. Siden måler så "Læg i kurven", "Til kassen", "Ordre" og "Del design" uden cookies.
- **Google og deling:** `node tools/seo.mjs` laver rigtige sider, som Google kan finde: `p/<id>.html` (produkter), `c/<kategori>.html` (Til hjemmet, Ramadan & Eid, Til børnene) og `levering-og-faq.html`, plus `sitemap.xml` og `robots.txt`. Hver side er en kopi af butikken med egen titel, beskrivelse og strukturerede data. **Kør den efter hver ændring i `index.html`**, og når `SITE_URL` skifter til dit eget domæne.
- **Nyhedsbrev:** Opret en gratis Brevo-konto, lav en tilmeldingsformular og indsæt formularens adresse i `NEWSLETTER_URL`. Indtil da gemmes ingen e-mails, og formularen skriver ærligt, at tilmeldingen åbner snart.
- **Sociale medier og kontakt:** Skriv Instagram- og TikTok-adresser i `SOCIAL` (tomme ikoner skjules) og kontaktmailen i `CONTACT_EMAIL`.

## Produktsidens opbygning (opdateret november 2026)

Produktsiden er bygget op efter en klassisk Shopify-produktside: galleri med pile og prikker til venstre, købsboks til højre, sticky "Læg i kurven" når man scroller forbi knappen, og faste sektioner nedenunder.

Alt står i `index.html`:
- `POINTS` – tre korte salgspunkter med ikon pr. produkt. Vises som ikonrække under beskrivelsen.
- `FBT` – hvilke tre produkter der vises i "Passer godt sammen med". Produkter uden navn (fx Tabaq og Mubarak) kan lægges direkte i kurven derfra. Resten får knappen "Vælg navn".
- `REVIEWS` – når du tilføjer rigtige anmeldelser (gerne med `rating: 5`), vises stjerner under produktnavnet og en anmeldelses-karrusel på produktsiden. Uden anmeldelser vises ingen af delene.
- `RAMADAN_DEADLINE` – styrer nedtællingen i prisboksen og den øverste linje i topbjælken. Begge forsvinder selv efter fristen.
- `HERO_IMG` – stemningsfotoet øverst på forsiden og bag "Sådan bliver din gave til" på alle produktsider. Det er et gratis Unsplash-foto af Jasurbek Hasanov, som hentes direkte fra Unsplash. Vil du hoste det selv, så gem det som `img/hero.jpg` og skriv `'img/hero.jpg'` i `HERO_IMG`. Fotografen krediteres i footeren (`HERO_CREDIT`).
- Rigtige produktfotos: `img/foto/<id>-1.webp` til `-3.webp` dukker op i produktgalleriet.

## Mobil og stabilitet
- På telefoner og tablets vises den lette 2D-forhåndsvisning. 3D-modellen hentes først, når kunden trykker "Se i 3D", og den lukkes igen, når man forlader produktet. Tidligere brugte 3D-visningen 4K-teksturer, som fik Safari på iPhone til at løbe tør for hukommelse og genindlæse siden.
- Kan 3D ikke indlæses, eller mister telefonen grafikforbindelsen, skifter siden selv tilbage til 2D.
- Inputfelter er 16 px på mobil, så iPhone ikke zoomer ind, når man skriver.
