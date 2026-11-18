import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent


class AnalyticsIntegrationTests(unittest.TestCase):
    def test_all_public_html_pages_load_analytics_after_i18n(self):
        pages = [
            "index.html",
            "book.html",
            "events.html",
            "events-archive.html",
            "privacy.html",
            "legal.html",
        ]
        for name in pages:
            content = (ROOT / name).read_text(encoding="utf-8")
            self.assertIn("./assets/analytics.js", content, f"{name} should include analytics.js")
            i18n_pos = content.find("./assets/i18n.js")
            analytics_pos = content.find("./assets/analytics.js")
            self.assertGreater(analytics_pos, i18n_pos, f"{name} should load analytics.js after i18n.js")

    def test_analytics_js_contains_consent_mode_v2_and_api(self):
        js = (ROOT / "assets" / "analytics.js").read_text(encoding="utf-8")
        self.assertIn('gtag("consent", "default"', js)
        self.assertIn('analytics_storage: "denied"', js)
        self.assertIn("window.BiblioAnalytics = Object.freeze", js)
        self.assertIn("openConsent", js)

    def test_shelf_js_tracks_order_funnel_events(self):
        js = (ROOT / "assets" / "shelf.js").read_text(encoding="utf-8")
        for event_name in ("add_to_cart", "remove_from_cart", "add_to_wishlist", "view_cart", "begin_checkout"):
            self.assertIn(event_name, js, f"shelf.js should track {event_name}")

    def test_book_html_tracks_view_item_and_begin_checkout(self):
        html = (ROOT / "book.html").read_text(encoding="utf-8")
        self.assertIn('track("view_item"', html)
        self.assertIn('track("begin_checkout"', html)

    def test_privacy_and_i18n_cover_analytics_consent(self):
        privacy = (ROOT / "privacy.html").read_text(encoding="utf-8")
        i18n = (ROOT / "assets" / "i18n.js").read_text(encoding="utf-8")
        self.assertIn("privacy.analytics.title", privacy)
        self.assertIn("BiblioAnalytics.openConsent()", privacy)
        for key in (
            "privacy.analytics.title",
            "privacy.analytics.manage",
            "analytics.banner.text",
            "analytics.banner.accept",
            "analytics.banner.reject",
        ):
            self.assertIn(f'"{key}"', i18n, f"i18n.js should translate {key}")


if __name__ == "__main__":
    unittest.main()
