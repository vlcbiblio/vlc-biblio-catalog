import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import book_categories as categories
import export_catalog as export
import generate_catalog_site as generate


class BookCategoryTests(unittest.TestCase):
    def setUp(self):
        self.book = {'id': 'b-0123456789ab', 'title': 'Книга', 'author': 'Автор', 'isbn': '123', 'annotation': 'Описание', 'requestId': '42', 'section': 'exchange', 'availability': 'reserved', 'orderBot': 'toma_lib_valencia_bot', 'orderStart': 'book_42', 'audience': 'adult'}
        self.record = {'identity': categories.identity(self.book), 'reader_age_groups': ['12–14 лет'], 'reader_age_status': 'editorial_recommendation', 'reader_age_basis': ['Адресация произведения'], 'genres': ['Фэнтези'], 'genre_status': 'editorial_review', 'genre_basis': 'Сюжет произведения', 'edition_age_ratings': ['12+'], 'edition_rating_status': 'external_catalog', 'research_sources': ['https://example.org/series'], 'research_scope': 'work_or_series_reference', 'classification_review_date': '2026-11-15'}

    def fixture(self, root):
        (root / 'data').mkdir()
        reviewed = {'version': 1, 'review_date': '2026-11-15', 'records': {self.book['id']: self.record}}
        path = root / 'data/book-categories.json'
        path.write_text(json.dumps(reviewed, ensure_ascii=False), encoding='utf-8')
        return path

    def test_categories_cannot_change_book_order_routes(self):
        bad_record = {**self.record, 'requestId': '999', 'orderBot': 'bad_bot', 'orderStart': 'bad', 'availability': 'available'}
        result = categories.apply_categories([self.book], {self.book['id']: bad_record})[0]
        for key, value in self.book.items(): self.assertEqual(result[key], value)
        self.assertEqual(result['genres'], ['Фэнтези'])
        self.assertEqual(generate.direct_action(result), generate.direct_action(self.book))

    def test_new_changed_or_incomplete_books_stay_pending_not_adult(self):
        for book, record in [({**self.book, 'id': 'new'}, self.record), ({**self.book, 'annotation': 'Changed'}, self.record), (self.book, {**self.record, 'genres': []})]:
            result = categories.apply_categories([book], {self.book['id']: record})[0]
            self.assertEqual(result['reader_age_status'], 'pending_review')
            self.assertNotIn('Взрослые', result['reader_age_groups'])
            self.assertEqual(result['genre_status'], 'pending_review')
        for key in ('cover', 'availability', 'libraryKey'):
            result = categories.apply_categories([{**self.book, key: 'changed'}], {self.book['id']: self.record})[0]
            self.assertEqual(result['reader_age_status'], 'editorial_recommendation')

    def test_export_refreshes_active_overlay_without_erasing_reviewed_json(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); path = self.fixture(root); original = path.read_bytes()
            export.write_books(root / 'data/books.js', [self.book, {**self.book, 'id': 'b-111111111111', 'title': 'New'}])
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(generate.load_books_js(root / 'data/books.js')[0], self.book)
            active = (root / 'data/book-categories.js').read_text(encoding='utf-8')
            self.assertIn('editorial_recommendation', active); self.assertIn('pending_review', active)
            self.assertNotIn('"orderStart"', active)

    def test_generator_has_static_categories_and_retains_sdk_checkout_routes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.fixture(root)
            template = (Path(__file__).parent / 'book.html').read_text(encoding='utf-8')
            (root / 'book.html').write_text(template, encoding='utf-8')
            generate.write_site(root, [self.book])
            page = (root / 'books' / (self.book['id'] + '.html')).read_text(encoding='utf-8')
            static = page.split('<section id="content">', 1)[1].split('</section>', 1)[0]
            self.assertIn('12–14 лет', static); self.assertIn('Фэнтези', static)
            self.assertNotIn('12+', static)
            self.assertNotIn('Recomendación de la biblioteca', static)
            self.assertIn('telegram.org/js/telegram-web-app.js', page)
            self.assertIn('assets/telegram-links.js', page)
            self.assertIn('https://t.me/toma_lib_valencia_bot?start=ext_book_42', page)
            self.assertIn('data/book-categories.js?v=', page)
            self.assertIn('work_or_series_reference', (root / 'data/book-categories.js').read_text(encoding='utf-8'))

    def test_import_requires_exact_public_snapshot_and_ids_and_whitelists_fields(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / 'data').mkdir()
            raw = 'window.BIBLIO_BOOKS = ' + json.dumps([self.book], ensure_ascii=False) + ';\n'
            (root / 'data/books.js').write_text(raw, encoding='utf-8')
            row = {**self.book, **self.record, 'user_id': 'private fixture only'}
            source = root / 'reviewed.json'
            reviewed = {'source_sha256': hashlib.sha256((root / 'data/books.js').read_bytes()).hexdigest(), 'date': '2026-11-15', 'books': [row]}
            source.write_text(json.dumps(reviewed), encoding='utf-8')
            self.assertEqual(categories.import_reviewed(root, source), 1)
            overlay = (root / 'data/book-categories.json').read_text(encoding='utf-8')
            self.assertNotIn('user_id', overlay); self.assertNotIn('orderStart', overlay)
            reviewed['source_sha256'] = 'wrong'; source.write_text(json.dumps(reviewed), encoding='utf-8')
            with self.assertRaises(ValueError): categories.import_reviewed(root, source)


if __name__ == '__main__': unittest.main()
