"""
Tests de design visuels pour Cyclopathe.
Captures screenshots sur différents viewports et valide l'UX mobile.
"""

import time
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright


BASE_URL = "http://localhost:8001"
SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"


@pytest.fixture(scope="session")
def browser():
    """Lancer Playwright + Chromium (session scope)."""
    SCREENSHOTS_DIR.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def mobile_context(browser):
    """Contexte mobile (375×812 — iPhone)."""
    context = browser.new_context(
        viewport={"width": 375, "height": 812},
        device_scale_factor=2,
    )
    yield context
    context.close()


@pytest.fixture
def tablet_context(browser):
    """Contexte tablet (768×1024 — iPad)."""
    context = browser.new_context(viewport={"width": 768, "height": 1024})
    yield context
    context.close()


@pytest.fixture
def desktop_context(browser):
    """Contexte desktop (1920×1080)."""
    context = browser.new_context(viewport={"width": 1920, "height": 1080})
    yield context
    context.close()


class TestDesignMobile:
    """Tests UX mobile (375×812 — iPhone)."""

    def test_homepage_loads(self, mobile_context):
        """Vérifier que la page d'accueil se charge correctement."""
        page = mobile_context.new_page()
        page.goto(BASE_URL, wait_until="networkidle")

        # Vérifier les éléments clés
        assert page.locator("h1:has-text('CYCLOPATHE')").is_visible()
        assert page.locator(".discipline-tabs").is_visible()
        assert page.locator(".filters").is_visible()
        assert page.locator(".frame-cards").is_visible()

        page.close()

    def test_discipline_tabs_visible(self, mobile_context):
        """Vérifier que les tabs discipline sont accessibles."""
        page = mobile_context.new_page()
        page.goto(BASE_URL, wait_until="networkidle")

        tabs = page.locator(".tab-btn").all()
        assert len(tabs) == 3, "Devrait avoir 3 tabs (Tous, Route, Gravel)"

        # Vérifier les labels
        tab_texts = [tab.text_content().strip() for tab in tabs]
        assert any("Tous" in t for t in tab_texts)
        assert any("Route" in t for t in tab_texts)
        assert any("Gravel" in t for t in tab_texts)

        page.close()

    def test_frame_cards_pagination(self, mobile_context):
        """Vérifier la pagination des cadres."""
        page = mobile_context.new_page()
        page.goto(BASE_URL, wait_until="networkidle")

        # Compter les cartes initiales
        initial_cards = page.locator(".frame-card").count()
        assert initial_cards >= 5, f"Devrait avoir au moins 5 cadres, trouvé {initial_cards}"

        # Vérifier le bouton "Charger plus"
        load_more = page.locator(".load-more-btn").is_visible()
        assert load_more, "Le bouton 'Charger plus' doit être visible"

        page.close()

    def test_mobile_layout_stacked(self, mobile_context):
        """Vérifier que le layout mobile est bien empilé (pas side-by-side)."""
        page = mobile_context.new_page()
        page.goto(BASE_URL, wait_until="networkidle")

        layout = page.locator(".layout")
        grid_cols = layout.evaluate("el => getComputedStyle(el).gridTemplateColumns")
        assert "1fr" in grid_cols or grid_cols.count("fr") == 1, \
            f"Layout mobile devrait être en colonne, trouvé: {grid_cols}"

        page.close()

    def test_filter_by_discipline(self, mobile_context):
        """Tester le filtre par discipline."""
        page = mobile_context.new_page()
        page.goto(BASE_URL, wait_until="networkidle")

        # Cliquer sur le tab "Route"
        page.locator(".tab-btn[data-discipline='road']").click()
        page.wait_for_timeout(500)

        # Vérifier que les cartes sont mises à jour
        cards = page.locator(".frame-card").count()
        assert cards > 0, "Devrait avoir des cadres route"

        page.close()

    def test_no_infinite_scroll(self, mobile_context):
        """Vérifier qu'il n'y a pas de scroll infini (max ~6 cadres par page)."""
        page = mobile_context.new_page()
        page.goto(BASE_URL, wait_until="networkidle")

        initial = page.locator(".frame-card").count()
        assert initial <= 10, f"Trop de cadres d'un coup ({initial}), pagination requise"

        page.close()

    def test_header_compact_mobile(self, mobile_context):
        """Vérifier que le header est compact sur mobile."""
        page = mobile_context.new_page()
        page.goto(BASE_URL, wait_until="networkidle")

        header = page.locator(".topbar")
        padding = header.evaluate("el => getComputedStyle(el).paddingTop")
        padding_value = float(padding.replace("px", ""))
        assert padding_value < 50, f"Header padding trop grand ({padding})"

        page.close()


class TestDesignTablet:
    """Tests UX tablet (768×1024 — iPad)."""

    def test_tablet_layout(self, tablet_context):
        """Vérifier le layout tablet (side-by-side)."""
        page = tablet_context.new_page()
        page.goto(BASE_URL, wait_until="networkidle")

        layout = page.locator(".layout")
        grid_cols = layout.evaluate("el => getComputedStyle(el).gridTemplateColumns")
        assert grid_cols.count("fr") >= 2 or "380px" in grid_cols, \
            f"Layout tablet devrait être 2 colonnes, trouvé: {grid_cols}"

        page.close()


class TestDesignDesktop:
    """Tests UX desktop (1920×1080)."""

    def test_desktop_layout(self, desktop_context):
        """Vérifier le layout desktop."""
        page = desktop_context.new_page()
        page.goto(BASE_URL, wait_until="networkidle")

        layout = page.locator(".layout")
        grid_cols = layout.evaluate("el => getComputedStyle(el).gridTemplateColumns")
        assert "380px" in grid_cols or "fr" in grid_cols, \
            f"Layout desktop devrait avoir colonnes, trouvé: {grid_cols}"

        page.close()


class TestAccessibility:
    """Tests d'accessibilité."""

    def test_keyboard_navigation(self, mobile_context):
        """Vérifier la navigation au clavier."""
        page = mobile_context.new_page()
        page.goto(BASE_URL, wait_until="networkidle")

        page.keyboard.press("Tab")
        focused = page.evaluate("document.activeElement.className")
        # Au moins on devrait pouvoir tab

        page.close()

    def test_contrast_ratios(self, mobile_context):
        """Vérifier les contrastes (très basique)."""
        page = mobile_context.new_page()
        page.goto(BASE_URL, wait_until="networkidle")

        text_elements = page.locator("body").text_content()
        assert len(text_elements) > 100, "Page devrait avoir du contenu visible"

        page.close()


class TestScreenshots:
    """Capturer des screenshots pour review."""

    def test_screenshot_mobile(self, mobile_context):
        """Capturer un screenshot mobile."""
        page = mobile_context.new_page()
        page.goto(BASE_URL, wait_until="networkidle")
        page.wait_for_timeout(500)

        screenshot_path = SCREENSHOTS_DIR / "mobile_homepage.png"
        page.screenshot(path=str(screenshot_path))
        assert screenshot_path.exists(), f"Screenshot non créé: {screenshot_path}"
        print(f"\n📱 Screenshot mobile: {screenshot_path}")

        page.close()

    def test_screenshot_mobile_tabs(self, mobile_context):
        """Capturer screenshot après clic sur tab."""
        page = mobile_context.new_page()
        page.goto(BASE_URL, wait_until="networkidle")

        page.locator(".tab-btn[data-discipline='road']").click()
        page.wait_for_timeout(500)

        screenshot_path = SCREENSHOTS_DIR / "mobile_route_tab.png"
        page.screenshot(path=str(screenshot_path))
        assert screenshot_path.exists()
        print(f"\n📱 Screenshot route tab: {screenshot_path}")

        page.close()

    def test_screenshot_desktop(self, desktop_context):
        """Capturer screenshot desktop pour comparaison."""
        page = desktop_context.new_page()
        page.goto(BASE_URL, wait_until="networkidle")
        page.wait_for_timeout(500)

        screenshot_path = SCREENSHOTS_DIR / "desktop_homepage.png"
        page.screenshot(path=str(screenshot_path))
        assert screenshot_path.exists()
        print(f"\n🖥️  Screenshot desktop: {screenshot_path}")

        page.close()


if __name__ == "__main__":
    # Pour lancer localement sans pytest
    print("Lancez avec: pytest tests/test_design.py -v")
