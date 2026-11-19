# Kildekode til KHATAM-produkterne

Python-scripts, der genererer printfilerne (STL) og produktbillederne. Kræver Python 3 med numpy, scipy og Pillow.

| Fil | Laver |
|---|---|
| gen.py | Fælles mesh-funktioner (bokse, ekstrudering, STL-skrivning) |
| products.py | Bordskilt, navneskilt, hjælpefunktioner til tekst og former |
| signs.py | Hyldeskiltene (MAKTABA) |
| gifts.py | Bilophæng, glasbrikker, Eidiyya-æske, nøglering (gammel version) |
| ism_token.py | ISM som nøglering og indkøbsvognsmønt |
| usra.py | USRA tandbørsteholder |
| entre.py | Entré-sættet: ZAWJ, BAB og TABAQ |
| render3d.py, photo.py | Produktbilleder (render) |
| logos.py | Logo-SVG'er |

Navne ændres i bunden af hver fil (fx `NAMES` i usra.py eller `zawj(...)` i entre.py).
Selve webshoppen ligger i `../khatam-site/` (åbn `index.html`).
