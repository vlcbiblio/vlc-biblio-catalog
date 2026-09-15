import json
import threading
import unittest
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from test_catalog_navigation import BOOKS, CatalogHandler, sync_playwright


class CoverHandler(CatalogHandler):
    def handle(self):
        try:
            super().handle()
        except ConnectionError:
            # Closing a test page cancels neighboring lazy image requests.
            pass

    def do_GET(self):
        if urlsplit(self.path).path != "/data/books.js":
            super().do_GET()
            return
        books = []
        for book in BOOKS:
            src = f'./assets/covers/b-2a3b6987dd2d.webp?test={book["id"]}'
            books.append({
                **book,
                "annotation": "A long book description. " * (1400 if book["id"] == "test-24" else 1),
                "cover": f'https://covers.invalid/{book["id"]}.jpg',
                "coverImage": {"src": src, "srcset": f"{src} 484w", "width": 484, "height": 756},
            })
        payload = f"window.BIBLIO_BOOKS = {json.dumps(books)};".encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/javascript")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


@unittest.skipUnless(sync_playwright, "Install Playwright to run browser checks")
class CoverLoadingTests(unittest.TestCase):
    def test_detail_loads_local_main_cover_before_offscreen_related_images(self):
        handler = partial(CoverHandler, directory=str(Path(__file__).parent))
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                try:
                    for width in (1280, 390):
                        with self.subTest(width=width):
                            page = browser.new_page(viewport={"width": width, "height": 844})
                            page.route("https://telegram.org/js/telegram-web-app.js*", lambda route: route.fulfill(
                                content_type="application/javascript", body=""))
                            requests = []
                            errors = []
                            page.on("request", lambda request: requests.append(request.url) if request.resource_type == "image" else None)
                            page.on("pageerror", lambda error: errors.append(str(error)))
                            page.goto(f"http://127.0.0.1:{server.server_port}/book.html?id=test-24")
                            main = page.locator(".book > .cover img")
                            self.assertTrue(main.evaluate("img => img.complete && img.naturalWidth > 0"))
                            self.assertEqual(main.get_attribute("fetchpriority"), "high")
                            self.assertEqual(len([url for url in requests if "?test=" in url]), 1)
                            related = page.locator(".related-card-link img").first
                            related.scroll_into_view_if_needed()
                            page.wait_for_function("""() => {
                                const img = document.querySelector('.related-card-link img');
                                return img.complete && img.naturalWidth > 0;
                            }""")
                            self.assertGreater(len([url for url in requests if "?test=" in url]), 1)
                            self.assertLess(len([url for url in requests if "?test=" in url]), len(BOOKS))
                            self.assertFalse(any("covers.invalid" in url for url in requests))
                            self.assertEqual(errors, [])
                            page.close()
                finally:
                    browser.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == "__main__":
    unittest.main()
