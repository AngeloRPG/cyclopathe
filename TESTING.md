# 🧪 Guide des tests de design — Cyclopathe

Infrastructure de test complète pour valider l'UX sur tous les appareils (mobile, tablet, desktop).

## 📦 Fichiers ajoutés

```
repo-cyclopathe/
├── Dockerfile                    # Multi-stage : prod + tests
├── docker-compose.yml            # Orchestration serveur + tests
├── requirements-dev.txt          # Playwright + pytest
├── run_design_tests.sh           # Script helper (local)
├── TESTING.md                    # Ce fichier
└── tests/
    ├── __init__.py
    ├── .gitignore                # Ignorer screenshots/
    ├── test_design.py            # Suite complète de tests
    └── screenshots/              # Généré après tests
```

## 🚀 Démarrer les tests

### Option 1 : Docker (recommandé - complet)

```bash
docker-compose up
```

Cela :
1. Build l'image avec Playwright + Chromium
2. Lance le serveur (http://localhost:8000)
3. Exécute les tests visuels automatiquement
4. Génère des screenshots dans `tests/screenshots/`

**Output exemple :**
```
test_design.py::TestDesignMobile::test_homepage_loads PASSED
test_design.py::TestDesignMobile::test_discipline_tabs_visible PASSED
test_design.py::TestDesignMobile::test_frame_cards_pagination PASSED
test_design.py::TestScreenshots::test_screenshot_mobile PASSED
...
======================== 12 passed in 8.43s ========================
```

### Option 2 : Local (sans Docker)

```bash
# 1. Installer dépendances
pip install -r requirements-dev.txt

# 2. Installer navigateur Chromium
playwright install chromium

# 3. Lancer serveur
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 4. En parallèle : lancer les tests
chmod +x run_design_tests.sh
./run_design_tests.sh all          # Tous les tests
./run_design_tests.sh mobile       # Juste mobile
./run_design_tests.sh tablet       # Juste tablet
./run_design_tests.sh desktop      # Juste desktop
```

### Option 3 : Docker (image test seule)

```bash
# Build image tests
docker build -t cyclopathe:test --target tests .

# Lancer les tests
docker run cyclopathe:test
```

## 📋 Tests couverts

### 🎬 Visuels (Playwright)

| Test | Viewport | Description |
|---|---|---|
| **Mobile** | 375×812 (iPhone) | Layout empilé, tabs, pagination |
| **Tablet** | 768×1024 (iPad) | Layout side-by-side |
| **Desktop** | 1920×1080 | Full layout multi-colonnes |

### ✅ Validations

**UX Mobile**
- ✓ Homepage se charge sans erreur
- ✓ Tabs discipline visibles (Tous/Route/Gravel)
- ✓ Compteurs affichés (11 route, 12 gravel)
- ✓ Cadres paginés (5-6 par page, pas infini)
- ✓ Bouton "Charger plus" fonctionnel
- ✓ Layout en colonne unique (responsive)
- ✓ Header compact (<50px padding)

**UX Tablet**
- ✓ Layout side-by-side activé (2+ colonnes)

**UX Desktop**
- ✓ Layout full (colonnes variables)

**Accessibilité**
- ✓ Navigation clavier (Tab)
- ✓ Contrastes texte (pas invisible)

**Screenshots** (automatiques)
- ✓ `mobile_homepage.png` — vue mobile accueil
- ✓ `mobile_route_tab.png` — après clic tab Route
- ✓ `desktop_homepage.png` — vue desktop

## 🎨 Tester manuellement

```bash
# Serveur tournant, ouvre dans le navigateur :
open http://localhost:8000

# Teste :
1. Tab "Route" → doit filtrer cadres
2. Filtre "Marque" → change la liste
3. "Charger plus" → ajoute à la fin (sans reload)
4. Sur mobile : verify layout empilé
```

## 📸 Résultats des screenshots

Après les tests, consulte :
```bash
ls tests/screenshots/
# mobile_homepage.png
# mobile_route_tab.png
# desktop_homepage.png
```

Partage sur Slack ou fais un diff visuel contre la branche précédente.

## 🔧 Débogage

### Test échoue : "Serveur non joignable"
```bash
# Vérifier que le serveur tourne
curl http://localhost:8000/health
# Sinon : uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Screenshot vide
```bash
# Vérifier que Playwright est installé
python -m playwright install chromium
```

### Docker : permission denied
```bash
# Utilisateur du groupe docker
sudo usermod -aG docker $USER
newgrp docker
```

## 🔄 Réutilisable pour d'autres projets

Le `Dockerfile` multi-stage est générique :
- Adapte `requirements.txt` → `requirements-dev.txt`
- Modifie `test_design.py` → tes propres tests
- Laisse le reste identique

Parfait pour tous les projets FastAPI/NAS! 🎯

## 📚 Ressources

- [Playwright Python](https://playwright.dev/python/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Docker multi-stage builds](https://docs.docker.com/build/building/multi-stage/)

## ✨ Prochaines étapes

- [ ] Ajouter tests de performance (Lighthouse, Web Vitals)
- [ ] E2E tests : sélectionner un cadre + composants + checkout
- [ ] Visual regression testing (Percy, Chromatic)
- [ ] CI/CD : exécuter tests dans Bitbucket Pipelines
