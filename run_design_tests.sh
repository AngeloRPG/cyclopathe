#!/bin/bash
# Script de test de design pour Cyclopathe
# Utilisation: ./run_design_tests.sh [mobile|tablet|desktop|all]

set -e

MODE=${1:-all}
SCREENSHOTS_DIR="tests/screenshots"

echo "🚀 Tests de design Cyclopathe"
echo "Mode: $MODE"
echo ""

# Vérifier que le serveur tourne
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "⚠️  Serveur non détecté sur localhost:8000"
    echo "Démarrage automatique du serveur..."
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
    SERVER_PID=$!
    sleep 4
    trap "kill $SERVER_PID 2>/dev/null || true" EXIT
fi

# Créer dossier screenshots
mkdir -p "$SCREENSHOTS_DIR"

# Lancer pytest avec le mode approprié
case $MODE in
    mobile)
        echo "📱 Tests mobile (375×812)..."
        pytest tests/test_design.py::TestDesignMobile -v --tb=short
        ;;
    tablet)
        echo "📱 Tests tablet (768×1024)..."
        pytest tests/test_design.py::TestDesignTablet -v --tb=short
        ;;
    desktop)
        echo "🖥️  Tests desktop (1920×1080)..."
        pytest tests/test_design.py::TestDesignDesktop -v --tb=short
        ;;
    all|*)
        echo "🎯 Tous les tests (mobile + tablet + desktop + a11y)..."
        pytest tests/test_design.py -v --tb=short
        ;;
esac

echo ""
echo "✅ Tests complétés!"
echo "📸 Screenshots: $SCREENSHOTS_DIR/"
ls -lah "$SCREENSHOTS_DIR"/ 2>/dev/null || echo "Pas de screenshots générés"
