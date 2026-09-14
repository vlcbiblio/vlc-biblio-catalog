"""Browser-local basket/favorites checks, with synthetic books and no Telegram calls."""

import json
import threading
import unittest
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from test_catalog_navigation import sync_playwright


BOOKS = [
    {"id": str(number), "requestId": str(number), "title": f"Книга {number}",
     "author": "Автор", "section": "exchange", "availability": "available",
     "libraryKey": "owner-a" if number <= 36 else "owner-b"}
    for number in range(1, 40)
] + [
    {"id": "40", "requestId": "40", "title": "В библиотеке", "section": "library"},
    {"id": "41", "requestId": "41", "title": "Занята", "section": "exchange", "availability": "reserved"},
    {"id": "42", "requestId": "bad-42", "title": "Без номера", "section": "exchange", "availability": "available"},
]


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if urlsplit(self.path).path.endswith("/data/books.js"):
            payload = f"window.BIBLIO_BOOKS = {json.dumps(BOOKS)};".encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        else:
            super().do_GET()

    def log_message(self, *_args):
        pass


@unittest.skipUnless(sync_playwright, "Install Playwright to run browser checks")
class ShelfTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(Path(__file__).parent)))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}/"
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        self.context = self.browser.new_context(viewport={"width": 1280, "height": 900})
        self.errors = []
        self.external = []
        self.context.on("page", lambda page: page.on("pageerror", lambda error: self.errors.append(str(error))))
        self.context.route("**/*", self.route)
        self.page = self.context.new_page()
        self.page.goto(self.url)

    def route(self, route):
        if not route.request.url.startswith(self.url):
            self.external.append(route.request.url)
            route.abort()
        else:
            route.continue_()

    def tearDown(self):
        self.context.close()
        self.assertEqual(self.errors, [])
        self.assertEqual(self.external, [])

    def button(self, number, list_name="cart", page=None):
        return (page or self.page).locator(f'.grid [data-shelf-id="{number}"][data-shelf-toggle="{list_name}"]')

    def open_list(self, name="cart"):
        self.page.locator(f'[data-shelf-open="{name}"]').click()
        self.assertTrue(self.page.locator(".shelf-dialog").is_visible())

    def test_collect_across_pages_reload_and_reopen_without_submitting(self):
        self.button(1).click()
        self.button(2).click()
        self.button(40, "favorites").click()
        self.page.goto(self.url + "book.html?id=3")
        self.page.locator('.book [data-shelf-toggle="cart"]').click()
        self.page.reload()
        self.assertEqual(self.page.locator('[data-shelf-count="cart"]').inner_text(), "3")
        self.open_list()
        self.assertEqual(self.page.locator(".shelf-row").count(), 3)
        link = self.page.locator("[data-shelf-checkout]")
        self.assertEqual(parse_qs(urlsplit(link.get_attribute("href")).query)["start"], ["books_1_2_3"])
        self.page.locator('[data-shelf-row="2"] [data-shelf-toggle="cart"]').click()
        self.assertEqual(self.page.locator(".shelf-row").count(), 2)
        self.page.keyboard.press("Escape")
        self.assertFalse(self.page.locator(".shelf-dialog").is_visible())
        self.page.close()
        self.page = self.context.new_page()
        self.page.goto(self.url)
        self.assertEqual(self.page.locator('[data-shelf-count="cart"]').inner_text(), "2")
        self.assertEqual(self.button(1).get_attribute("aria-pressed"), "true")
        self.open_list("favorites")
        self.assertEqual(self.page.locator(".shelf-row").count(), 1)
        self.assertIn("В библиотеке", self.page.locator(".shelf-row").inner_text())
        self.assertEqual(self.page.locator("[data-shelf-checkout]").count(), 0)

    def test_favorites_remain_when_added_to_cart_and_are_removable(self):
        self.button(1, "favorites").click()
        self.open_list("favorites")
        row = self.page.locator('[data-shelf-row="1"]')
        row.locator('[data-shelf-toggle="cart"]').click()
        self.assertEqual(self.page.locator('[data-shelf-count="favorites"]').inner_text(), "1")
        self.assertEqual(self.page.locator('[data-shelf-count="cart"]').inner_text(), "1")
        row.locator('[data-shelf-toggle="favorites"]').click()
        self.assertEqual(self.page.locator(".shelf-row").count(), 0)
        self.assertTrue(self.page.locator(".shelf-empty").is_visible())

    def test_independent_owners_and_unknown_libraries_never_share_checkout(self):
        self.button(1).click()
        self.button(2).click()
        self.button(37).click()
        self.open_list()
        links = self.page.locator("[data-shelf-checkout]").evaluate_all("nodes => nodes.map(node => node.href)")
        self.assertEqual([parse_qs(urlsplit(link).query)["start"][0] for link in links], ["books_1_2", "books_37"])
        self.page.keyboard.press("Escape")
        changed = [{**book, "libraryKey": ""} for book in BOOKS]
        self.replace_books(changed)
        self.page.reload()
        self.open_list()
        self.assertEqual(self.page.locator("[data-shelf-checkout]").count(), 3)

    def replace_books(self, books):
        self.page.route("**/data/books.js?*", lambda route: route.fulfill(
            content_type="application/javascript", body=f"window.BIBLIO_BOOKS = {json.dumps(books)};"))

    def test_stale_unavailable_and_missing_books_stay_visible_but_are_not_requested(self):
        for number in (1, 2, 3):
            self.button(number).click()
        self.replace_books([
            {**book, "availability": "reserved"} if book["id"] == "2" else book
            for book in BOOKS if book["id"] != "3"
        ])
        self.page.reload()
        self.open_list()
        self.assertEqual(self.page.locator(".shelf-row").count(), 3)
        self.assertTrue(self.page.locator('[data-shelf-row="3"]').is_visible())
        self.assertIn("books_1", self.page.locator("[data-shelf-checkout]").get_attribute("href"))
        self.assertIn("wait_2", self.page.locator(".shelf-waitlist").get_attribute("href"))
        self.assertEqual(self.page.locator('[data-shelf-row="3"] [data-shelf-toggle]').count(), 1)

    def test_large_basket_is_split_into_valid_complete_nonoverlapping_orders(self):
        for number in range(1, 37):
            self.button(number).click()
        self.open_list()
        links = self.page.locator("[data-shelf-checkout]").evaluate_all("nodes => nodes.map(node => node.href)")
        self.assertGreater(len(links), 1)
        result = []
        for link in links:
            payload = parse_qs(urlsplit(link).query)["start"][0]
            ids = payload.removeprefix("books_").split("_")
            self.assertLessEqual(len(payload), 64)
            self.assertLessEqual(len(ids), 30)
            result.extend(ids)
        self.assertEqual(result, [str(number) for number in range(1, 37)])

    def test_tabs_share_lists_while_fresh_browser_has_its_own_lists(self):
        other = self.context.new_page()
        other.goto(self.url)
        self.button(1).click()
        other.wait_for_function('document.querySelector(\'[data-shelf-count="cart"]\').textContent === "1"')
        self.button(2, page=other).click()
        self.page.wait_for_function('document.querySelector(\'[data-shelf-count="cart"]\').textContent === "2"')
        self.button(1).click()
        other.wait_for_function('document.querySelector(\'[data-shelf-count="cart"]\').textContent === "1"')
        with self.browser.new_context() as fresh:
            page = fresh.new_page()
            page.goto(self.url)
            self.assertEqual(page.locator('[data-shelf-count="cart"]').inner_text(), "0")

    def test_mobile_keyboard_empty_states_and_ineligible_books(self):
        self.page.set_viewport_size({"width": 390, "height": 844})
        self.open_list()
        self.assertTrue(self.page.locator(".shelf-empty").is_visible())
        self.page.keyboard.press("Escape")
        self.button(1).focus()
        self.page.keyboard.press("Enter")
        self.assertEqual(self.page.url, self.url)
        self.assertEqual(self.page.locator('[data-shelf-count="cart"]').inner_text(), "1")
        for number in (40, 41, 42):
            self.assertEqual(self.button(number).count(), 0)
            self.assertTrue(self.button(number, "favorites").count())
        self.open_list()
        self.assertTrue(self.page.locator("[data-shelf-checkout]").is_visible())
        self.assertTrue(self.page.evaluate("document.documentElement.scrollWidth <= innerWidth"))
        self.assertTrue(self.page.locator(".shelf-dialog").evaluate("node => node.scrollWidth <= node.clientWidth"))

    def test_corrupt_or_blocked_storage_does_not_break_catalog(self):
        self.page.evaluate("localStorage.setItem('vlc-biblio:shelf:v1:/:cart', '{broken')")
        self.page.reload()
        self.button(1).click()
        self.open_list()
        self.assertEqual(self.page.locator(".shelf-row").count(), 1)
        self.page.keyboard.press("Escape")
        self.page.add_init_script("Object.defineProperty(window, 'localStorage', { get() { throw new Error('blocked'); } });")
        self.page.reload()
        self.button(2).click()
        self.open_list()
        self.assertIn("только на этой странице", self.page.locator(".shelf-storage-note").inner_text())
        self.assertEqual(self.page.locator(".shelf-row").count(), 1)


if __name__ == "__main__":
    unittest.main()
