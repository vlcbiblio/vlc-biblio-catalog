import json
import re
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree

import generate_catalog_site as generate


class StaticSiteGenerationTests(unittest.TestCase):
    def test_toma_note_is_limited_to_new_notion_source(self):
        source = {'section': 'exchange', 'orderBot': 'toma_lib_valencia_bot',
                  'sourceUrl': 'https://funny-cannon-067.notion.site/' + 'a' * 32}
        markup = generate.static_book_markup(source)
        self.assertIn('Книга в частной коллекции Библиотеки ', markup)
        self.assertIn('href="https://t.me/toma_lib_valencia"', markup)
        self.assertIn('>ТОМА</a>. Вы можете запросить книгу на время.', markup)
        for ordinary in ({'section': 'exchange'}, {'section': 'exchange', 'orderBot': source['orderBot']},
                         dict(source, sourceUrl='https://other.notion.site/' + 'a' * 32)):
            self.assertNotIn('>ТОМА</a>', generate.static_book_markup(ordinary))

    def test_reserved_external_source_link_is_visible_in_static_page(self):
        book = {'id': 'source', 'section': 'exchange', 'availability': 'reserved',
                'orderBot': 'toma_lib_valencia_bot', 'orderStart': 'book_166'}
        markup = generate.static_book_markup(book)
        self.assertIn('https://t.me/toma_lib_valencia_bot?start=book_166', markup)
        self.assertIn('Consultar disponibilidad', markup)
        self.assertNotIn('start=wait_', markup)

    def setUp(self):
        self.book = {
            "id": "b-0123456789ab",
            "requestId": "42",
            "title": "Книга & тест",
            "author": "Автор",
            "section": "exchange",
            "availability": "available",
            "isbn": "9780000000000",
            "annotation": "Описание книги",
            "cover": "https://example.org/cover.jpg",
            "updatedAt": "2026-10-18T12:00:00",
        }

    @staticmethod
    def static_content(page):
        return page.split('<section id="content">', 1)[1].split('</section>', 1)[0]

    def test_generated_page_has_static_content_and_unique_seo(self):
        root = Path(__file__).parent
        page = generate.render_book_page((root / "book.html").read_text(encoding="utf-8"), self.book)
        self.assertIn("<h1>Книга &amp; тест</h1>", page)
        self.assertIn('<body data-book-id="b-0123456789ab">', page)
        self.assertIn('<link rel="canonical" href="https://vlcbiblio.github.io/vlc-biblio-catalog/books/b-0123456789ab.html"', page)
        self.assertNotIn('content="noindex,follow"', page)
        self.assertIn('property="og:image" content="https://example.org/cover.jpg"', page)
        self.assertIn('type="application/ld+json"', page)
        self.assertIn('https://t.me/VLS_Biblio_bot?start=book_42', page)
        self.assertRegex(page, r'<script src="\./assets/i18n\.js\?v=[^"<>]+"></script>')
        self.assertNotIn("depósito", self.static_content(page))

    def test_deposit_notice_is_static_and_limited_to_configured_books(self):
        template = (Path(__file__).parent / "book.html").read_text(encoding="utf-8")
        configured = generate.render_book_page(template, {**self.book, "depositEur": 20})
        other_owner = generate.render_book_page(template, self.book)
        public_library = generate.render_book_page(template, {
            **self.book,
            "section": "library",
            "depositEur": 20,
        })

        configured_content = self.static_content(configured)
        self.assertIn('class="deposit-note" aria-label="Condiciones del depósito"', configured_content)
        self.assertIn("Depósito reembolsable: 20 euros", configured_content)
        self.assertLess(configured_content.index('class="annotation"'), configured_content.index('class="deposit-note"'))
        self.assertNotIn('class="deposit-note"', self.static_content(other_owner))
        self.assertNotIn('class="deposit-note"', self.static_content(public_library))

    def test_site_writes_one_canonical_url_per_book(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source_root = Path(__file__).parent
            (root / "book.html").write_text((source_root / "book.html").read_text(encoding="utf-8"), encoding="utf-8")
            generate.write_site(root, [self.book])
            self.assertTrue((root / "books" / "b-0123456789ab.html").is_file())
            sitemap = ElementTree.parse(root / "sitemap.xml")
            locations = [item.text for item in sitemap.findall("{*}url/{*}loc")]
            self.assertEqual(locations.count(generate.book_url(self.book)), 1)
            self.assertIn(generate.SITE_URL + "events.html", locations)
            self.assertIn(generate.SITE_URL + "events-archive.html", locations)
            self.assertIn(f"Sitemap: {generate.SITE_URL}sitemap.xml", (root / "robots.txt").read_text(encoding="utf-8"))

            self.assertFalse((root / "books" / "test-1.html").exists())
            self.assertFalse((root / "books" / "test-2.html").exists())

    def test_books_payload_parser_rejects_executable_javascript(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "books.js"
            path.write_text('alert(1); window.BIBLIO_BOOKS = [];', encoding="utf-8")
            with self.assertRaises(ValueError):
                generate.load_books_js(path)

    def test_checked_in_pages_match_the_current_public_payload(self):
        root = Path(__file__).parent
        books = generate.load_books_js(root / "data" / "books.js")
        pages = [page for page in (root / "books").glob("*.html") if generate.GENERATED_BOOK_PATTERN.fullmatch(page.name)]
        self.assertEqual(len(pages), len(books))
        canonicals = set()
        for page in pages:
            source = page.read_text(encoding="utf-8")
            canonical = re.search(r'<link rel="canonical" href="([^"]+)"', source)
            structured = re.search(r'<script type="application/ld\+json">(.*?)</script>', source, re.DOTALL)
            self.assertIsNotNone(canonical, page.name)
            self.assertIsNotNone(structured, page.name)
            self.assertNotIn('content="noindex,follow"', source)
            canonicals.add(canonical.group(1))
            self.assertEqual(json.loads(structured.group(1))["@type"], "Book")
        self.assertEqual(len(canonicals), len(books))
        sitemap = ElementTree.parse(root / "sitemap.xml")
        locations = {item.text for item in sitemap.findall("{*}url/{*}loc")}
        self.assertTrue(canonicals <= locations)
        self.assertEqual(len(locations), len(books) + 4)


if __name__ == "__main__":
    unittest.main()
