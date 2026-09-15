"""Browser regression checks: python -X utf8 -m unittest test_catalog_navigation -v.

Requires Playwright and its Chromium browser. The local HTTP server substitutes
synthetic books, so these checks never modify catalog data or contact Telegram.
"""

import json
import threading
import unittest
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

try:
    from playwright.sync_api import expect, sync_playwright
except ImportError:
    sync_playwright = None


BOOKS = [
    {
        "id": f"test-{number}",
        "title": f"Shelf volume {number:03}",
        "author": f"Author {number % 3}",
        "section": "library" if number < 24 else "exchange",
        "libraryKey": "test-library",
        "availability": "available",
        "requestId": str(number + 1),
    }
    for number in range(96)
]


class CatalogHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if urlsplit(self.path).path == "/data/books.js":
            payload = f"window.BIBLIO_BOOKS = {json.dumps(BOOKS)};".encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        super().do_GET()

    def log_message(self, *_args):
        pass


@unittest.skipUnless(sync_playwright, "Install Playwright to run browser checks")
class CatalogNavigationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        handler = partial(CatalogHandler, directory=str(Path(__file__).parent))
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}/"
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.server.shutdown()
        cls.server.server_close()
        cls.server_thread.join()

    def setUp(self):
        self.context = self.browser.new_context(viewport={"width": 1280, "height": 900})
        self.context.route("https://telegram.org/js/telegram-web-app.js*", lambda route: route.fulfill(
            content_type="application/javascript", body=""))
        self.page = self.context.new_page()
        self.errors = []
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))

    def tearDown(self):
        self.context.close()
        self.assertEqual(self.errors, [])

    def open_catalog(self, section="exchange", scroll=2200):
        self.page.goto(self.base_url)
        self.page.locator("#search").fill("Shelf")
        self.page.locator("#sectionFilter").select_option(section)
        self.page.evaluate("top => window.scrollTo(0, top)", scroll)

    def open_visible_book(self):
        # Click a cover already on screen, so the test does not scroll for us.
        target = self.page.evaluate("""() => {
            const top = Math.max(0, document.querySelector('.controls').getBoundingClientRect().bottom);
            const card = [...document.querySelectorAll('#grid .book')].find(card => {
                const rect = card.getBoundingClientRect();
                return rect.top > top && rect.top + 40 < innerHeight;
            });
            const rect = card.getBoundingClientRect();
            return {id: card.dataset.bookId, x: rect.left + 20, y: rect.top + 30, scroll: scrollY};
        }""")
        self.page.mouse.click(target["x"], target["y"])
        expect(self.page).to_have_url(f"{self.base_url}book.html?id={target['id']}")
        expect(self.page.locator("#content h1")).to_be_visible()
        return target

    def assert_scroll(self, expected):
        self.page.wait_for_function("top => Math.abs(scrollY - top) <= 2", arg=expected)

    def assert_catalog(self, scroll, section="exchange", search="Shelf"):
        expect(self.page).to_have_url(self.base_url)
        expect(self.page.locator("#search")).to_have_value(search)
        expect(self.page.locator("#sectionFilter")).to_have_value(section)
        self.assert_scroll(scroll)

    def test_back_forward_and_catalog_link_on_desktop_and_mobile(self):
        for width, height in [(1280, 900), (390, 844)]:
            with self.subTest(width=width):
                self.page.set_viewport_size({"width": width, "height": height})
                self.open_catalog()
                first = self.open_visible_book()
                first_url = self.page.url
                link = self.page.locator(".related-card-link").first
                link.scroll_into_view_if_needed()
                book_scroll = self.page.evaluate("scrollY")
                second_url = self.base_url + link.get_attribute("href").removeprefix("./")
                link.click()
                expect(self.page).to_have_url(second_url)
                self.assert_scroll(0)

                self.page.go_back()
                expect(self.page).to_have_url(first_url)
                self.assert_scroll(book_scroll)
                self.page.go_back()
                self.assert_catalog(first["scroll"])
                self.page.go_forward()
                expect(self.page).to_have_url(first_url)
                self.page.go_forward()
                expect(self.page).to_have_url(second_url)
                self.page.locator("a.back").click()
                self.assert_catalog(first["scroll"])

    def test_older_catalog_history_entry_keeps_its_own_filters_and_position(self):
        self.open_catalog()
        first = self.open_visible_book()
        first_url = self.page.url
        self.page.locator("a.back").click()
        self.assert_catalog(first["scroll"])
        self.page.locator("#sectionFilter").select_option("library")
        self.page.evaluate("window.scrollTo(0, 700)")
        second = self.open_visible_book()
        self.page.go_back()
        self.assert_catalog(second["scroll"], section="library")
        self.page.go_back()
        expect(self.page).to_have_url(first_url)
        self.page.go_back()
        self.assert_catalog(first["scroll"])

    def test_catalog_reload_restores_filters_and_scroll(self):
        self.open_catalog()
        previous_scroll = self.page.evaluate("scrollY")
        self.page.reload()
        self.assert_catalog(previous_scroll)

    def test_catalog_keeps_visible_book_when_viewport_changes(self):
        self.open_catalog()
        self.open_visible_book()
        snapshot = self.page.evaluate("JSON.parse(Object.values(sessionStorage)[0])")
        self.page.set_viewport_size({"width": 390, "height": 844})
        self.page.locator("a.back").click()
        expect(self.page.locator("#sectionFilter")).to_have_value("exchange")
        self.page.wait_for_function("""saved => {
            const card = [...document.querySelectorAll('#grid .book')].find(c => c.dataset.bookId === saved.anchorId);
            return card && Math.abs(card.getBoundingClientRect().top - saved.anchorOffset) <= 2;
        }""", arg=snapshot)

    def test_direct_book_link_returns_to_catalog_top_in_a_fresh_tab(self):
        self.page.goto(f"{self.base_url}book.html?id=test-24")
        self.page.locator(".related-card-link").first.click()
        self.page.go_back()
        expect(self.page).to_have_url(f"{self.base_url}book.html?id=test-24")
        self.page.locator("a.back").click()
        self.assert_catalog(0, section="", search="")

    def test_legacy_book_link_preserves_saved_catalog(self):
        self.open_catalog()
        previous_scroll = self.page.evaluate("scrollY")
        self.page.goto(f"{self.base_url}?book=test-24")
        expect(self.page).to_have_url(f"{self.base_url}book.html?id=test-24")
        self.page.locator("a.back").click()
        self.assert_catalog(previous_scroll)

    def test_browser_back_works_without_session_storage(self):
        self.context.add_init_script("""Object.defineProperty(window, 'sessionStorage', {
            get() { throw new DOMException('Storage disabled', 'SecurityError'); }
        });""")
        self.open_catalog()
        first = self.open_visible_book()
        self.page.go_back()
        self.assert_catalog(first["scroll"])


if __name__ == "__main__":
    unittest.main()
