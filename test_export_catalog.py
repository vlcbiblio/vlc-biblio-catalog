import csv
import json
import tempfile
import unittest
from pathlib import Path

import export_catalog as export


class CatalogOnlyExportTests(unittest.TestCase):
    def test_same_site_original_cover_works_without_optimized_manifest(self):
        from PIL import Image
        from generate_catalog_site import static_book_markup
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            covers = root / 'assets/covers'
            covers.mkdir(parents=True)
            Image.new('RGB', (20, 30), 'red').save(covers / 'notion-test.png')
            url = 'https://vlcbiblio.github.io/vlc-biblio-catalog/assets/covers/notion-test.png'
            rows = [{'id': 'source', 'cover': url}]
            result = export.write_books(root / 'data/books.js', rows)
            self.assertEqual(result[0]['cover'], url)
            self.assertEqual(result[0]['coverImage']['src'], './assets/covers/notion-test.png')
            self.assertEqual(result[0]['coverImage']['width'], 20)
            self.assertIn('src="./assets/covers/notion-test.png"', static_book_markup(result[0]))
            self.assertEqual(rows, [{'id': 'source', 'cover': url}])
            # An encoded traversal must never attach an asset outside covers.
            Image.new('RGB', (20, 30)).save(root / 'outside.png')
            result = export.write_books(root / 'data/books.js', [{'cover': url.replace('notion-test.png', '%2e%2e/%2e%2e/outside.png')}])
            self.assertNotIn('coverImage', result[0])

    def test_external_order_routes_are_per_record(self):
        source = {'username': 'ekailnina', 'destination': 'книгообмен',
                  'order_bot': 'toma_lib_valencia_bot', 'order_start': 'book_220'}
        imported = export.public_book(source)
        self.assertEqual(imported['orderStart'], 'book_220')
        self.assertEqual(imported['orderBot'], 'toma_lib_valencia_bot')
        ordinary = export.public_book({'username': 'ekailnina', 'book_number': '13'})
        self.assertNotIn('orderBot', ordinary)
        with self.assertRaises(ValueError):
            export.public_book(dict(source, order_start='https://example.com'))

    def test_explicit_missing_notion_cover_does_not_weaken_other_checks(self):
        row = {'request_file': 'notion:3f94f95a-2ae4-815a-9b18-fe742d0f74d4',
               'source_cover_status': 'missing', 'order_bot': 'toma_lib_valencia_bot',
               'order_start': 'book_220'}
        export.require_publishable_covers([export.public_book(row)])
        with self.assertRaises(ValueError):
            export.require_publishable_covers([export.public_book(dict(row, request_file='ordinary'))])

    def test_author_key_groups_collins_name_variants(self):
        variants = ("Сьюзен Коллинз", "Коллинз Сьюзен", "Suzanne Collins")
        self.assertEqual(
            {export.author_key_for(author) for author in variants},
            {"suzanne-collins"},
        )

        book = export.public_book({"title": "Роман", "author": "Коллинз Сьюзен"})
        self.assertEqual(book["authorKey"], "suzanne-collins")

    def test_search_aliases_are_exported_separately_from_visible_metadata(self):
        book = export.public_book({
            "title": "Спасибо Уинн-Дикси",
            "author": "Кейт Дикамилло",
            "search_aliases": "Кейт Дикамило; Дикамило",
        })

        self.assertEqual(book["author"], "Кейт Дикамилло")
        self.assertEqual(book["searchAliases"], "Кейт Дикамило; Дикамило")
        self.assertEqual(book["annotation"], "")

    def test_reviewed_author_overrides_correct_kotofeyevka_books(self):
        for request_id in ("88", "132", "154"):
            book = export.public_book({
                "book_number": request_id,
                "title": "Книга из серии «У нас в Котофеевке»",
                "author": "Ошибочный автор",
            })
            self.assertEqual(book["author"], "Рина Зенюк")

        untouched = export.public_book({"book_number": "1", "author": "Другой автор"})
        self.assertEqual(untouched["author"], "Другой автор")

    def test_unavailable_book_keeps_explicit_catalog_state(self):
        self.assertEqual(export.availability_for({"availability_status": "unavailable"}, "exchange"),
                         "unavailable")
        self.assertEqual(export.availability_for({"availability_status": "недоступна"}, "exchange"),
                         "unavailable")

    def test_irishkakosh_private_books_get_location_note(self):
        expected = (
            "Местоположение: Сагунто. Доступность метро на станциях Colón и Aragón "
            "в определённые дни и часы."
        )
        self.assertEqual(export.location_note_for({"username": "@IrishkaKosh"}, "exchange"), expected)
        self.assertEqual(export.location_note_for({"username": "irishkakosh"}, "exchange"), expected)
        self.assertEqual(export.location_note_for({"username": "IrishkaKosh"}, "library"), "")
        self.assertEqual(export.location_note_for({"username": "another_user"}, "exchange"), "")

    def test_deposit_is_exported_only_for_the_configured_private_library(self):
        configured = export.public_book({
            "username": "@IrishkaKosh",
            "destination": "книгообмен",
            "title": "Книга",
        })
        other_owner = export.public_book({
            "username": "another_user",
            "destination": "книгообмен",
            "title": "Другая книга",
        })
        public_library = export.public_book({
            "username": "@IrishkaKosh",
            "destination": "Pilar Faus",
            "title": "Библиотечная книга",
        })

        self.assertEqual(configured["depositEur"], 20)
        self.assertNotIn("depositEur", other_owner)
        self.assertNotIn("depositEur", public_library)
        self.assertNotIn("username", configured)

    def test_oyellowsparrow_private_books_get_campanar_location_note(self):
        expected = "Местоположение: метро Campanar"
        self.assertEqual(export.location_note_for({"username": "@oYellowSparrow"}, "exchange"), expected)
        self.assertEqual(export.location_note_for({"username": "oyellowsparrow"}, "exchange"), expected)
        self.assertEqual(export.location_note_for({"username": "oYellowSparrow"}, "library"), "")

    def test_audience_uses_metadata_and_reviewed_overrides(self):
        self.assertTrue(export.ADULT_REQUEST_IDS.isdisjoint(export.CHILDREN_REQUEST_IDS))
        self.assertEqual(export.audience_for({
            "title": "Приключения котёнка",
            "annotation": "Для младшего школьного возраста.",
        }), "children")
        self.assertEqual(export.audience_for({
            "title": "Тихий роман",
            "annotation": "История для взрослого читателя.",
        }), "adult")
        self.assertEqual(export.audience_for({
            "book_number": "42",
            "title": "Пищеблок",
            "annotation": "Роман о школьном лагере.",
        }), "adult")
        self.assertEqual(export.audience_for({
            "audience": "детская",
            "book_number": "42",
        }), "children")

    def test_duplicate_requests_are_merged_into_retained_cards(self):
        rows = [
            {"book_number": "206", "title": "Старый дубль", "isbn": "9785389121713",
             "annotation": "Полная аннотация", "catalog_visibility": "public"},
            {"book_number": "798", "title": "Фамильяры. Книга 2",
             "catalog_visibility": "public", "preview_url": "https://example.org/familiars.jpg"},
        ]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "books.csv"
            fields = sorted({key for row in rows for key in row})
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
            books = export.load_books(path)

        self.assertEqual([book["requestId"] for book in books], ["798"])
        self.assertEqual(books[0]["isbn"], "9785389121713")
        self.assertEqual(books[0]["annotation"], "Полная аннотация")

    def test_russian_metadata_override_matches_the_spanish_source_book(self):
        book = export.public_book({
            "book_number": "199",
            "request_file": "chat_export_20260911_group_0772",
            "title": "Wrong title",
            "author": "Wrong author",
        })

        self.assertEqual(book["id"], "b-59e5a3f12b7c")
        self.assertEqual(book["title"], "Голодные игры. Рассвет жатвы (на испанском языке)")
        self.assertEqual(book["author"], "Сьюзен Коллинз")
        self.assertEqual(book["isbn"], "9788427248427")
        self.assertEqual(book["publisher"], "Molino")
        self.assertEqual(book["audience"], "adult")
        self.assertIn("Amanecer en la cosecha", book["searchAliases"])

    def test_existing_russian_sunrise_card_is_completed(self):
        book = export.public_book({
            "book_number": "580",
            "title": "Рассвет жатвы",
            "author": "Сьюзен Коллинз",
            "isbn": "978-5-17-170878-8",
        })

        self.assertEqual(book["title"], "Рассвет Жатвы")
        self.assertEqual(book["year"], "2025")
        self.assertEqual(book["publisher"], "АСТ, Neoclassic")
        self.assertIn("Хеймитч Эбернети", book["annotation"])

    def test_retained_familiars_cards_stay_in_the_children_catalog(self):
        for request_id in ("797", "798", "799", "800"):
            self.assertEqual(export.audience_for({"book_number": request_id}), "children")

    def test_export_reuses_optimized_images_only_for_the_matching_source(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            cover = root / "assets/covers/optimized/cover.webp"
            cover.parent.mkdir(parents=True)
            cover.write_bytes(b"existing optimized image")
            manifest = root / "assets/covers/manifest.json"
            manifest.write_text(json.dumps({"covers": {"https://example.org/original.jpg": {
                "variants": [{"src": "./assets/covers/optimized/cover.webp", "width": 360, "height": 540}]
            }}}), encoding="utf-8")
            output = root / "data/books.js"
            books = [
                {"id": "cached", "cover": "https://example.org/original.jpg"},
                {"id": "corrected", "cover": "https://example.org/corrected.jpg", "coverImage": {"src": "stale.webp"}},
            ]
            export.write_books(output, books)
            result = json.loads(output.read_text(encoding="utf-8").split("=", 1)[1].strip().rstrip(";"))
            self.assertEqual(result[0]["coverImage"]["src"], "./assets/covers/optimized/cover.webp")
            self.assertEqual(result[0]["cover"], books[0]["cover"])
            self.assertNotIn("coverImage", result[1])
            self.assertNotIn("coverImage", books[0])

            cover.unlink()
            export.write_books(output, books)
            result = json.loads(output.read_text(encoding="utf-8").split("=", 1)[1].strip().rstrip(";"))
            self.assertNotIn("coverImage", result[0])

    def test_explicit_catalog_selection_survives_export_without_telegram_receipts(self):
        rows = [
            {"book_number": "1", "title": "Published", "user_published_at": "2026-09-12T12:00:00",
             "preview_url": "https://example.org/published.jpg"},
            {"book_number": "2", "title": "Selected", "catalog_visibility": "public",
             "catalog_added_at": "2026-09-13T12:00:00", "telegram_delivery_mode": "manual_batch",
             "user_id": "42", "username": "private_owner",
             "preview_url": "https://example.org/selected.jpg"},
            {"book_number": "3", "title": "Unselected"},
            {"book_number": "4", "title": "Rejected", "catalog_visibility": "public", "status": "rejected",
             "preview_url": "https://example.org/rejected.jpg"},
        ]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "books.csv"
            fields = sorted({key for row in rows for key in row})
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
            books = export.load_books(path)
        self.assertEqual({b["requestId"] for b in books}, {"1", "2"})
        selected = next(b for b in books if b["requestId"] == "2")
        self.assertEqual(selected["updatedAt"], rows[1]["catalog_added_at"])
        self.assertNotIn("username", selected)
        self.assertNotIn("user_id", selected)
        self.assertNotIn("telegram_delivery_mode", selected)
        self.assertNotIn("user_published_at", rows[1])
        self.assertNotIn("channel_published_at", rows[1])

    def test_export_is_blocked_when_a_public_book_has_no_cover(self):
        rows = [
            {"book_number": "1", "title": "Ready", "catalog_visibility": "public",
             "preview_url": "https://example.org/ready.jpg"},
            {"book_number": "2", "title": "Missing cover", "catalog_visibility": "public",
             "preview_url": ""},
        ]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "books.csv"
            fields = sorted({key for row in rows for key in row})
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)

            with self.assertRaisesRegex(ValueError, r"2: Missing cover"):
                export.load_books(path)

    def test_export_is_blocked_for_a_local_cover_path(self):
        rows = [
            {"book_number": "3", "title": "Local cover", "catalog_visibility": "public",
             "preview_url": r"C:\\covers\\book.jpg"},
        ]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "books.csv"
            fields = sorted({key for row in rows for key in row})
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)

            with self.assertRaisesRegex(ValueError, r"3: Local cover"):
                export.load_books(path)


if __name__ == "__main__":
    unittest.main()
