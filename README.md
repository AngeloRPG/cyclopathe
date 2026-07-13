<div align="center" style="text-transform: uppercase;">

# Cyclopathe — configurateur vélo route & gravel

</div>

Configurateur qui référence des cadres route/gravel (≥ 2020) et des composants
compatibles (roues, transmission, cockpit, pneus, selle, pédales, porte-bidon),
puis calcule le **poids total** et le **prix** (MSRP) de la configuration.

URL de prod : https://cyclopathe.leignel.ddnsfree.com

## Stack
FastAPI + Jinja2 + HTMX, SQLAlchemy (SQLite en dev, PostgreSQL en prod).
Déployé via CI/CD Bitbucket → NAS ASUSTOR (Traefik, runner self-hosted).
Voir le README racine `nas-cicd/`.

## Architecture applicative
```
app/
├── main.py            # routes FastAPI + rendu HTMX
├── models.py          # frames, components (spec JSONB)
├── schemas.py         # validation Pydantic (ingestion)
├── compatibility.py   # MOTEUR DE COMPATIBILITÉ (règles techniques, centré cadre)
├── pricing.py         # calcul poids + prix
├── ingest/
│   ├── base.py        # interface SourceAdapter (port)
│   ├── curated.py     # adaptateur seed/fallback (ACTIF)
│   ├── ninetynine.py  # adaptateur 99spokes (à brancher quand licence obtenue)
│   └── run.py         # job fetch → valider → upsert Postgres
├── templates/         # base + index + partials HTMX
└── static/            # style.css + htmx.min.js (vendorisé)
seed/                  # jeu de données curé (frames.yaml, components.yaml)
```

## Modèle de compatibilité
Tout part du **cadre**. Chaque composant candidat est filtré par des règles
déclarées dans `compatibility.py` (faciles à corriger sans toucher au reste) :

| Composant | Règles |
|---|---|
| Roues | axe, freinage, diamètre == cadre ; freehub == transmission ; discipline (route vs gravel) |
| Transmission | freinage, boîtier, fixation dérailleur, électronique == cadre ; freehub == roues ; discipline (XPLR = gravel) |
| Pneus | diamètre == roues ; largeur ≤ clearance cadre |
| Cockpit | pivot == cadre ; discipline (Zipp = gravel) |
| Selle / Pédales | interfaces universelles (aucune règle) |
| Porte-bidon | cadre doit avoir ≥ 1 insert |

Quand un choix rend un composant déjà sélectionné incompatible, il est retiré
automatiquement (`_prune_incompatible`).

**Règles de discipline (route vs gravel):**
- Zipp XPLR (roues/cockpit) → gravel only
- Zipp non-XPLR (roues) → route only
- Fulcrum Rapid Red (roues) → gravel only
- DT Swiss ARC (roues) → route only
- Roval Alpinist (roues) → route only
- Roval Terra (roues) → gravel only
- SRAM *XPLR (transmissions) → gravel only

## Données : source active
- **`curated`** (par défaut) : lit `seed/*.yaml`, versionné dans le dépôt.
- **`ninetynine`** : 99spokes, **nécessite une licence** (pas d'API publique
  gratuite ; ne pas scraper — CGU). Basculer via `DATA_SOURCE=ninetynine` +
  `NINETYNINE_API_KEY` une fois l'accès obtenu, sans rien changer d'autre.

## Développement local

### Setup rapide (SQLite)
```sh
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
DATABASE_URL="sqlite:///./cyclopathe.db" python3 -m app.ingest.run --seed-if-empty
DATABASE_URL="sqlite:///./cyclopathe.db" uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
# http://localhost:8000
```

### Setup production-like (PostgreSQL)
Si tu veux tester avec PostgreSQL :
```sh
# Lancer Postgres en Docker
docker run -d --name cyclopathe-db \
  -e POSTGRES_USER=cyclopathe \
  -e POSTGRES_PASSWORD=cyclopathe \
  -e POSTGRES_DB=cyclopathe \
  -p 5432:5432 postgres:16

# Puis launcher l'app avec la config PostgreSQL
export DATABASE_URL="postgresql+psycopg://cyclopathe:cyclopathe@localhost:5432/cyclopathe"
python3 -m app.ingest.run --seed-if-empty
uvicorn app.main:app --host 0.0.0.0 --reload
```

## Tests & Design (Docker)

### 🎬 Tester avec Docker (tests visuels complets)

Lancer **serveur + tests design automatiques** :
```sh
docker-compose up
```

Cela va :
1. ✅ Builder l'image avec Playwright + Chromium
2. ✅ Lancer le serveur sur `http://localhost:8000`
3. ✅ Exécuter les tests visuels sur **mobile (375px)**, **tablet**, **desktop**
4. ✅ Générer des screenshots dans `tests/screenshots/`

**Résultats :** tests passent ou échouent, tu verras :
```
test_design.py::TestDesignMobile::test_homepage_loads PASSED
test_design.py::TestDesignMobile::test_discipline_tabs_visible PASSED
test_design.py::TestDesignMobile::test_frame_cards_pagination PASSED
test_design.py::TestDesignTablet::test_tablet_layout PASSED
test_design.py::TestScreenshots::test_screenshot_mobile PASSED
test_design.py::TestScreenshots::test_screenshot_desktop PASSED
```

### 📱 Tests couverts

**UX Mobile (375×812 — iPhone)**
- Homepage se charge correctement
- Tabs discipline visibles + interactifs
- Pagination des cadres (5-6 par page)
- Pas de scroll infini
- Layout empilé (1 colonne)
- Header compact

**UX Tablet (768×1024 — iPad)**
- Layout side-by-side fonctionnel

**UX Desktop (1920×1080)**
- Layout multi-colonnes complet

**Accessibilité**
- Navigation clavier
- Contrastes de texte

**Screenshots**
- Captures automatiques (mobile, tablet, desktop)
- Sauvegardées dans `tests/screenshots/`

### 🔧 Développement local (sans Docker)

Si tu veux juste la venv Python :
```sh
pip install -r requirements-dev.txt
playwright install chromium
pytest tests/test_design.py -v
```

### 📦 Images Docker disponibles

**Production (minimaliste)** :
```bash
docker build -t cyclopathe:prod .
docker run -p 8000:8000 cyclopathe:prod
```

**Tests (avec Playwright + Chromium)** :
```bash
docker build --target tests -t cyclopathe:test .
docker run cyclopathe:test pytest tests/ -v
```

## Déploiement
1. Sur le NAS : copie `nas/cyclopathe/` dans `/volume1/docker/cyclopathe/`,
   `cp .env.example .env` (+ secrets).
2. BDD : dans `nas/data/`, `cp .env.cyclopathe.example .env.cyclopathe`, puis
   `docker compose up -d postgres-cyclopathe`.
3. DNS : crée l'enregistrement **cyclopathe.leignel.ddnsfree.com** → ton IP.
4. Pousse ce dépôt sur `main` : le pipeline build+push l'image, le runner NAS
   `pull`+`up`, puis exécute l'ingestion `--seed-if-empty` au premier déploiement.

## Mise à jour périodique des données
Le pipeline lance `python -m app.ingest.run --seed-if-empty` (ne peuple que si
vide). Pour un rafraîchissement complet régulier, planifie via cron ADM :
```sh
docker compose -f /volume1/docker/cyclopathe/docker-compose.yml exec -T backend python -m app.ingest.run
```

## Ingestion depuis sources officielles — Web scraping + LLM (NEW)

### Architecture d'ingestion
L'appli supporte plusieurs sources (adaptateurs) :

| Adaptateur | Source | Statut | Config |
|---|---|---|---|
| **curated** | `seed/*.yaml` versionné | ✅ Actif par défaut | `DATA_SOURCE=curated` |
| **official_sites** | Sites constructeurs officiels + LLM | 🆕 Nouveau | `DATA_SOURCE=official_sites` + `ANTHROPIC_API_KEY` |
| **ninetynine** | API licenciée 99spokes | ⏳ Attente licence | `DATA_SOURCE=ninetynine` + `NINETYNINE_API_KEY` |

### Adaptateur official_sites : Web Scraping HTML + Claude LLM

**Stratégie (pas d'API requise) :**
1. **Scrape pages HTML** des constructeurs officiels (Canyon, Specialized, etc.)
   - Extrait les listes de produits (pages `/road-bikes/`, `/gravel-bikes/`)
   - Scrape chaque page produit pour collecter contenu texte

2. **Extraction intelligente de contenu HTML**
   - Cherche sections clés : titre, prix, specs, poids
   - Filtre le bruit (publicités, commentaires)
   - Extrait uniquement le texte pertinent (weight, price, brake, axle, bb, steerer, tire, etc.)

3. **Normalisation via Claude (LLM)**
   - Envoie le texte extrait à Claude API
   - Claude parse et structure : poids, prix EUR, normes techniques (BB, axles, steerer, discipline, etc.)
   - Gère formats variables, unités, abréviations
   - Retourne JSON structuré validé (Pydantic)

4. **Fallback curatés** (si scrape/parse échoue)
   - Retombe sur `seed/*.yaml` pour garantir un minimum de données

**Setup :**
```bash
# 1. Obtiens une clé API Anthropic (gratuite pour usage personnel)
# https://console.anthropic.com/

# 2. Configure le .env
cat > .env << 'EOF'
DATABASE_URL=sqlite:///./cyclopathe.db
DATA_SOURCE=official_sites
ANTHROPIC_API_KEY=sk-...
EOF

# 3. Ingère
python3 -m app.ingest.run
```

**Architecture :**
```
OfficialSitesAdapter
├─ Pour chaque marque (Canyon, Specialized, Cervélo, Trek, Giant)
│  ├─ Scrape liste produits (road-bikes/, gravel-bikes/)
│  ├─ Extrait URLs produits (parsing HTML avec BeautifulSoup)
│  └─ Pour chaque produit :
│     ├─ Scrape page HTML
│     ├─ Extrait contenu pertinent (titre, prix, specs, poids)
│     └─ Normalise via Claude → FrameIn structuré
└─ Si peu de résultats → Fallback CuratedAdapter
```

**Exemple : de HTML → JSON structuré :**
```
HTML PAGE (Canyon.com) :
<h1>Canyon Ultimate CF SLX</h1>
<div class="specs">
  Weight: 780g | Brake: Disc | Axle: 12x100/12x142
  BB: BB86 | Steerer: Tapered 1-1/8
</div>
<div class="price">€2,499</div>

↓ Claude LLM parse ↓

JSON (prêt pour FrameIn):
{
  "brand": "Canyon",
  "model": "Ultimate CF SLX",
  "weight_g": 780,
  "price": 2499.00,
  "brake_type": "disc",
  "axle_front": "12x100",
  "axle_rear": "12x142",
  "bb_standard": "BB86",
  "steerer": "tapered",
  ...
}
```

**Avantages :**
- ✅ **Pas d'API requise** — fonctionne avec n'importe quel site public
- ✅ **Flexible** — gère layouts HTML différents (BeautifulSoup + LLM)
- ✅ **Intelligent** — Claude comprend le contexte, les abréviations, les unités
- ✅ **Robuste** — fallback curatés si extraction échoue

**Limitations actuelles :**
- URLs de scrape à adapter pour chaque marque (patterns HTML différents)
- Limite : 10 produits/catégorie pour éviter overload. À augmenter après test.
- Composants (wheels, drivetrain, etc.) pas encore implémentés (utilisent fallback curatés)

**À adapter pour chaque marque :**
- Chaque site a un layout HTML différent
- Les selectors CSS pour extraire titre, prix, specs varient
- Certains sites ont du JavaScript rendering (peut nécessiter Selenium)

**Prochaines étapes :**
1. Adapter `product_list_urls` pour chaque marque (trouver les bonnes catégories)
2. Tester scrape → vérifier extraction contenu
3. Augmenter limite produits (de 10 à X)
4. Ajouter marques composants
5. Si site nécessite JavaScript : utiliser Selenium/Playwright
