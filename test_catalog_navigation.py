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
        "audience": "children" if number % 2 == 0 else "adult",
        "requestId": str(number + 1),
    }
    for number in range(96)
]
BOOKS[24]["locationNote"] = (
    "Местоположение: Сагунто. Доступность метро на станциях Colón и Aragón "
    "в определённые дни и часы."
)
BOOKS[24]["depositEur"] = 20
BOOKS[0]["annotation"] = "Новогодняя ёлка"
BOOKS[1]["annotation"] = "Новогодняя елка"
BOOKS[2]["searchAliases"] = "Кейт Дикамило; Дикамило"
BOOKS[0].update({"author": "Сьюзен Коллинз", "authorKey": "suzanne-collins"})
BOOKS[1].update({"author": "Коллинз Сьюзен", "authorKey": "suzanne-collins"})
BOOKS[2].update({"author": "Suzanne Collins", "authorKey": "suzanne-collins"})


class CatalogHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        request_path = urlsplit(self.path).path
        if request_path == "/data/books.js":
            payload = f"window.BIBLIO_BOOKS = {json.dumps(BOOKS)};".encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        if request_path.startswith("/books/test-") and request_path.endswith(".html"):
            book_id = Path(request_path).stem
            page = (Path(__file__).parent / "book.html").read_text(encoding="utf-8")
            page = page.replace(
                '<meta name="viewport" content="width=device-width, initial-scale=1" />',
                '<meta name="viewport" content="width=device-width, initial-scale=1" />\n    <base href="../" />',
                1,
            ).replace("<body>", f'<body data-book-id="{book_id}">', 1)
            payload = page.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
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

    def open_catalog(self, section="exchange", scroll=None):
        self.page.goto(self.base_url)
        self.page.locator("#search").fill("Shelf")
        self.page.locator("#sectionFilter").select_option(section)
        if scroll is None:
            scroll = self.page.evaluate("document.querySelector('#grid').offsetTop + 300")
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
        expect(self.page).to_have_url(f"{self.base_url}books/{target['id']}.html")
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
        self.page.evaluate("window.scrollTo(0, document.querySelector('#grid').offsetTop + 700)")
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

    def test_loaded_catalog_batches_survive_book_navigation(self):
        self.open_catalog()
        self.page.locator("#loadMore").click()
        expect(self.page.locator("#grid .book")).to_have_count(72)

        card = self.page.locator("[data-book-id='test-90']")
        card.scroll_into_view_if_needed()
        previous_scroll = self.page.evaluate("scrollY")
        card.click(position={"x": 20, "y": 30})
        expect(self.page).to_have_url(f"{self.base_url}books/test-90.html")

        self.page.go_back()
        expect(self.page.locator("#grid .book")).to_have_count(72)
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

    def test_owner_location_note_follows_private_collection_note(self):
        self.page.goto(f"{self.base_url}book.html?id=test-24")
        self.assertEqual(
            self.page.locator(".body > .collection-note").first.inner_text(),
            "Книга в частной коллекции. Вы можете запросить книгу на время.\n"
            "Местоположение: Сагунто. Доступность метро на станциях Colón и Aragón "
            "в определённые дни и часы.",
        )

    def test_deposit_notice_is_visible_only_for_configured_book_on_desktop_and_mobile(self):
        for width, height in [(1280, 900), (390, 844)]:
            with self.subTest(width=width):
                self.page.set_viewport_size({"width": width, "height": height})
                self.page.goto(f"{self.base_url}book.html?id=test-24")
                notice = self.page.locator(".body > .deposit-note")
                expect(notice).to_be_visible()
                expect(notice).to_have_attribute("aria-label", "Условия залога")
                expect(notice).to_contain_text("Возвратный залог — 20 евро")
                self.assertLess(
                    self.page.locator(".annotation").bounding_box()["y"],
                    notice.bounding_box()["y"],
                )

                self.page.goto(f"{self.base_url}book.html?id=test-25")
                expect(self.page.locator(".body > .deposit-note")).to_have_count(0)

                self.page.goto(f"{self.base_url}book.html?id=test-0")
                expect(self.page.locator(".body > .deposit-note")).to_have_count(0)

    def test_legacy_book_link_preserves_saved_catalog(self):
        self.open_catalog()
        previous_scroll = self.page.evaluate("scrollY")
        self.page.goto(f"{self.base_url}?book=test-24")
        expect(self.page).to_have_url(f"{self.base_url}books/test-24.html")
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

    def test_audience_classification_is_hidden_and_public_sections_are_available(self):
        self.page.goto(self.base_url)
        expect(self.page.locator("[data-open-external-browser]")).to_be_hidden()
        expect(self.page.locator("#how-it-works")).to_be_visible()
        expect(self.page.locator(".event-preview")).to_be_visible()
        expect(self.page.locator(".topbar > .event-preview")).to_have_count(1)
        expect(self.page.locator(".events-teaser")).to_have_count(0)
        expect(self.page.locator("#business")).to_be_visible()
        expect(self.page.locator("#faq")).to_be_visible()
        expect(self.page.locator("#latestGrid .latest-card")).to_have_count(6)

        self.assertEqual(self.page.locator("#totalCount").inner_text(), "96")
        self.assertEqual(self.page.locator("#libraryCount").inner_text(), "24")
        self.assertEqual(self.page.locator("#exchangeCount").inner_text(), "72")

        expect(self.page.locator("#audienceFilter")).to_have_count(0)
        expect(self.page.locator("#grid .book")).to_have_count(48)
        expect(self.page.locator("#catalogProgress")).to_have_text("Показано 48 из 96")
        self.page.locator("#loadMore").click()
        expect(self.page.locator("#grid .book")).to_have_count(96)
        expect(self.page.locator("#catalogMore")).to_be_hidden()
        expect(self.page.get_by_text("Детская литература", exact=True)).to_have_count(0)
        expect(self.page.get_by_text("Взрослая литература", exact=True)).to_have_count(0)
        self.assertEqual(
            self.page.locator("#grid .book .badge.exchange").first.inner_text(),
            "🏠 Частная библиотека",
        )

        response = self.page.request.get(f"{self.base_url}privacy.html")
        self.assertEqual(response.status, 200)

        events_link = self.page.locator(".event-preview")
        self.assertEqual(events_link.get_attribute("href"), "./events.html")

        events_response = self.page.request.get(f"{self.base_url}events.html")
        self.assertEqual(events_response.status, 200)

    def test_search_treats_yo_and_e_as_the_same_letter(self):
        self.page.goto(self.base_url)

        self.page.locator("#search").fill("елка")
        expect(self.page.locator("#grid .book")).to_have_count(2)

        self.page.locator("#search").fill("ёлка")
        expect(self.page.locator("#grid .book")).to_have_count(2)

    def test_search_uses_hidden_aliases(self):
        self.page.goto(self.base_url)
        self.page.locator("#search").fill("Дикамило")

        expect(self.page.locator("#grid .book")).to_have_count(1)
        expect(self.page.locator("#grid .book")).to_contain_text("Shelf volume 002")

    def test_related_books_use_author_key_across_name_variants(self):
        self.page.goto(f"{self.base_url}book.html?id=test-0")

        related = self.page.locator(".related-results")
        expect(related).to_contain_text("Shelf volume 001")
        expect(related).to_contain_text("Shelf volume 002")

    def test_partner_link_opens_the_bot_team_message_scenario(self):
        self.page.goto(self.base_url)
        partner_link = self.page.get_by_role("link", name="Стать партнёром")
        self.assertEqual(
            partner_link.get_attribute("href"),
            "https://t.me/VLS_Biblio_bot?start=partner",
        )

    def test_header_links_to_instagram_below_telegram_links(self):
        self.page.goto(self.base_url)
        instagram = self.page.get_by_role("link", name="Instagram VLC Biblio")

        expect(instagram).to_be_visible()
        self.assertEqual(instagram.get_attribute("href"), "https://www.instagram.com/vlc.biblio")
        self.assertEqual(instagram.locator("svg.instagram-icon").count(), 1)

    def test_events_page_lists_only_the_confirmed_event_in_both_languages(self):
        self.page.goto(f"{self.base_url}events.html")

        expect(self.page.locator("h1")).to_have_text("Встречи")
        expect(self.page.locator(".event-card")).to_have_count(1)
        poster = self.page.locator(".event-poster img")
        expect(poster).to_be_visible()
        expect(poster).to_have_attribute("src", "./assets/events/children-book-club-2026-10-28.webp")
        expect(poster).to_have_attribute("alt", "Афиша книжного и творческого клуба для детей")
        expect(self.page.locator(".event-card h3")).to_have_text(
            "Книжный и творческий клуб для детей 5–8 лет"
        )
        expect(self.page.locator(".event-program li")).to_have_count(3)
        expect(self.page.locator(".event-contacts")).to_contain_text("@odnazhdy_vlc")
        expect(self.page.locator(".event-contacts a")).to_have_count(1)
        expect(self.page.locator(".event-contacts a")).to_have_attribute("href", "https://t.me/odnazhdy_vlc")
        expect(self.page.locator(".event-support")).to_contain_text("@VLS_Biblio_bot")
        registration = self.page.locator(".event-card .primary-link")
        self.assertEqual(registration.get_attribute("href"), "https://clck.ru/3VtMAP")

        self.page.locator("[data-language-toggle]").click()
        expect(self.page.locator("h1")).to_have_text("Encuentros")
        expect(poster).to_have_attribute("alt", "Cartel del club de lectura y creatividad para niños")
        expect(self.page.locator(".event-card h3")).to_have_text(
            "Club de lectura y creatividad para niños de 5 a 8 años"
        )

    def test_language_toggle_switches_ui_and_preserves_book_data(self):
        self.page.goto(self.base_url)
        first_title = self.page.locator("#grid .book .title").first.inner_text()

        expect(self.page.locator("#how-title")).to_have_text("Как это работает")
        expect(self.page.locator(".event-preview-kicker")).to_have_text("Ближайшая встреча")
        expect(self.page.locator(".event-preview-meta")).to_contain_text("28 октября")
        expect(self.page.locator("#loadMore")).to_have_text("Показать ещё")
        expect(self.page.locator("[data-shelf-open='cart']")).to_contain_text("Корзина")
        expect(self.page.locator("#grid .badge.exchange").first).to_have_text("🏠 Частная библиотека")
        expect(self.page.locator("#grid .shelf-favorite").first).to_have_attribute("title", "Добавить в избранное")
        expect(self.page.locator("[data-language-toggle]")).to_have_text("ES")
        self.assertEqual(self.page.locator("html").get_attribute("lang"), "ru")
        self.assertEqual(self.page.locator("#grid .book .title").first.inner_text(), first_title)

        self.page.reload()
        expect(self.page.locator("#how-title")).to_have_text("Как это работает")

        self.page.locator("[data-language-toggle]").click()
        expect(self.page.locator("#how-title")).to_have_text("Cómo funciona")
        expect(self.page.locator(".event-preview-kicker")).to_have_text("Próximo encuentro")
        expect(self.page.locator(".event-preview-meta")).to_contain_text("28 de octubre")
        expect(self.page.locator("#loadMore")).to_have_text("Mostrar más")
        self.assertEqual(self.page.locator("html").get_attribute("lang"), "es")
        self.page.goto(f"{self.base_url}privacy.html")
        expect(self.page.locator("h1")).to_have_text("Privacidad")

        self.page.goto(self.base_url)
        self.page.locator("[data-language-toggle]").click()
        expect(self.page.locator("#how-title")).to_have_text("Как это работает")
        self.assertEqual(self.page.locator("html").get_attribute("lang"), "ru")
        self.page.goto(f"{self.base_url}privacy.html")
        expect(self.page.locator("h1")).to_have_text("Конфиденциальность")

    def test_telegram_catalog_can_open_a_clean_url_in_external_browser(self):
        self.page.set_viewport_size({"width": 390, "height": 844})
        self.context.add_init_script("""
            window.Telegram = {WebApp: {
                platform: "android",
                ready() {},
                isVersionAtLeast(version) { return version === "6.1"; },
                openLink(url) { window.openedExternalCatalogUrl = url; },
            }};
        """)
        self.page.goto(f"{self.base_url}?audience=all#tgWebAppData=private-data")

        button = self.page.locator("[data-open-external-browser]")
        expect(button).to_be_visible()
        bounds = button.bounding_box()
        self.assertGreaterEqual(bounds["x"], 0)
        self.assertLessEqual(bounds["x"] + bounds["width"], 390)
        button.click()

        self.assertEqual(
            self.page.evaluate("window.openedExternalCatalogUrl"),
            f"{self.base_url}?audience=all",
        )


if __name__ == "__main__":
    unittest.main()
