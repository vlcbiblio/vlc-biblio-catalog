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
     "libraryKey": "owner-a" if number <= 36 else "owner-b",
     "locationNote": ("Местоположение: Сагунто. Доступность метро на станциях Colón и Aragón "
                      "в определённые дни и часы.") if number <= 36 else ""}
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
        if route.request.url.startswith("https://telegram.org/js/telegram-web-app.js?"):
            route.fulfill(content_type="application/javascript", body="")
        elif not route.request.url.startswith(self.url):
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

    def mock_telegram(self, platform="android"):
        self.context.add_init_script("""
            window.telegramEvents = [];
            window.Telegram = { WebApp: {
                platform: PLATFORM, initData: '', version: '8.0',
                isVersionAtLeast: () => true,
                ready: () => window.telegramEvents.push(['ready']),
                openTelegramLink: url => window.telegramEvents.push(['open', url]),
                close: () => window.telegramEvents.push(['close']),
            }};
        """.replace("PLATFORM", json.dumps(platform)))
        self.page.reload()

    def assert_telegram_handoff(self, expected_url):
        self.assertEqual(self.page.evaluate("window.telegramEvents"), [
            ["ready"], ["open", expected_url], ["close"],
        ])
        self.assertEqual(len(self.context.pages), 1)

    def test_telegram_checkout_from_catalog_and_book_keeps_full_basket(self):
        self.mock_telegram()
        self.button(1).click()
        self.button(2).click()
        for path, width in [("", 1280), ("book.html?id=1", 390)]:
            with self.subTest(path=path, width=width):
                self.page.set_viewport_size({"width": width, "height": 844})
                self.page.goto(self.url + path)
                self.assertEqual(self.page.evaluate("window.telegramEvents"), [["ready"]])
                self.open_list()
                link = self.page.locator("[data-shelf-checkout]")
                self.assertTrue(link.is_visible())
                self.assertTrue(self.page.locator(".shelf-dialog").evaluate(
                    "node => node.scrollWidth <= node.clientWidth"))
                # Exercise both nested-span clicks and keyboard activation.
                if path:
                    link.focus()
                    self.page.keyboard.press("Enter")
                else:
                    link.locator("span").first.click()
                self.assert_telegram_handoff("https://t.me/VLS_Biblio_bot?start=books_1_2")
                self.assertEqual(self.page.url, self.url + path)
                self.page.reload()
                self.assertEqual(self.page.locator('[data-shelf-count="cart"]').inner_text(), "2")

    def test_telegram_waitlist_from_cart_and_book_opens_the_bot(self):
        self.mock_telegram()
        self.button(1).click()
        self.replace_books([
            {**book, "availability": "reserved"} if book["id"] == "1" else book
            for book in BOOKS
        ])
        self.page.reload()
        self.open_list()
        self.page.locator(".shelf-waitlist").click()
        self.assert_telegram_handoff("https://t.me/VLS_Biblio_bot?start=wait_1")
        self.page.goto(self.url + "book.html?id=41")
        self.page.locator('.book a[href$="start=wait_41"]').click()
        self.assert_telegram_handoff("https://t.me/VLS_Biblio_bot?start=wait_41")

    def assert_browser_checkout(self):
        # Fulfill the popup locally; never contact Telegram from a test.
        self.context.route("https://t.me/**", lambda route: route.fulfill(
            content_type="text/html", body="<title>Telegram link test</title>"))
        self.button(1).click()
        self.open_list()
        with self.page.expect_popup() as opened:
            self.page.locator("[data-shelf-checkout]").click()
        popup = opened.value
        popup.wait_for_load_state()
        self.assertEqual(popup.url, "https://t.me/VLS_Biblio_bot?start=books_1")
        popup.close()
        self.assertEqual(self.page.locator('[data-shelf-count="cart"]').inner_text(), "1")

    def test_checkout_without_telegram_sdk_uses_regular_browser_link(self):
        self.assert_browser_checkout()

    def test_checkout_with_sdk_in_regular_browser_uses_regular_link(self):
        self.mock_telegram(platform="unknown")
        self.assert_browser_checkout()
        self.assertEqual(self.page.evaluate("window.telegramEvents"), [])

    def test_checkout_with_failed_telegram_bridge_falls_back_to_regular_link(self):
        self.mock_telegram()
        self.page.evaluate("""() => {
            window.Telegram.WebApp.openTelegramLink = () => { throw new Error('bridge unavailable'); };
        }""")
        self.assert_browser_checkout()
        self.assertEqual(self.page.evaluate("window.telegramEvents"), [["ready"]])

    def test_old_telegram_client_uses_regular_link(self):
        self.mock_telegram()
        self.page.evaluate("window.Telegram.WebApp.isVersionAtLeast = () => false")
        self.assert_browser_checkout()
        self.assertEqual(self.page.evaluate("window.telegramEvents"), [["ready"]])

    def test_failed_close_does_not_open_a_duplicate_checkout(self):
        self.mock_telegram()
        self.page.evaluate("""() => {
            window.Telegram.WebApp.close = () => { throw new Error('close unavailable'); };
        }""")
        self.button(1).click()
        self.open_list()
        self.page.locator("[data-shelf-checkout]").click()
        self.assertEqual(self.page.evaluate("window.telegramEvents"), [
            ["ready"], ["open", "https://t.me/VLS_Biblio_bot?start=books_1"],
        ])
        self.assertEqual(len(self.context.pages), 1)

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

    def test_cart_shows_transfer_location_before_telegram_checkout(self):
        self.button(1).click()
        self.button(2).click()
        self.open_list()
        location = self.page.locator(".shelf-location")
        self.assertEqual(location.count(), 1)
        self.assertEqual(
            location.inner_text(),
            "Местоположение: Сагунто. Доступность метро на станциях Colón и Aragón "
            "в определённые дни и часы.",
        )
        self.assertTrue(location.locator("xpath=following-sibling::div//a[@data-shelf-checkout]").is_visible())

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
            fresh.route("**/*", self.route)
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

    def test_floating_cart_appears_after_toolbar_leaves_view_and_opens_cart(self):
        floating = self.page.locator("[data-shelf-floating-open]")
        self.button(1).click()
        self.assertEqual(floating.get_attribute("aria-hidden"), "true")

        self.page.evaluate("scrollTo(0, document.body.scrollHeight)")
        self.page.wait_for_function(
            "document.querySelector('[data-shelf-floating-open]').classList.contains('is-visible')"
        )
        self.assertEqual(floating.locator("[data-shelf-floating-count]").inner_text(), "1")
        floating.click()
        self.assertTrue(self.page.locator(".shelf-dialog").is_visible())
        self.assertEqual(floating.get_attribute("aria-hidden"), "true")

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
