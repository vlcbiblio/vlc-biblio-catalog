import json
import re
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree

import generate_catalog_site as generate


class StaticSiteGenerationTests(unittest.TestCase):
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
        self.assertNotIn("depósito", page)

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
            self.assertIn(f"Sitemap: {generate.SITE_URL}sitemap.xml", (root / "robots.txt").read_text(encoding="utf-8"))

    def test_books_payload_parser_rejects_executable_javascript(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "books.js"
            path.write_text('alert(1); window.BIBLIO_BOOKS = [];', encoding="utf-8")
            with self.assertRaises(ValueError):
                generate.load_books_js(path)

    def test_checked_in_pages_match_the_current_public_payload(self):
        root = Path(__file__).parent
        books = generate.load_books_js(root / "data" / "books.js")
        pages = list((root / "books").glob("*.html"))
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
        self.assertEqual(len(locations), len(books) + 2)


if __name__ == "__main__":
    unittest.main()
