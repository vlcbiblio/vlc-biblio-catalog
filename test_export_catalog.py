import csv
import json
import tempfile
import unittest
from pathlib import Path

import export_catalog as export


class CatalogOnlyExportTests(unittest.TestCase):
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
            {"book_number": "1", "title": "Published", "user_published_at": "2026-09-12T12:00:00"},
            {"book_number": "2", "title": "Selected", "catalog_visibility": "public",
             "catalog_added_at": "2026-09-13T12:00:00", "telegram_delivery_mode": "manual_batch",
             "user_id": "42", "username": "private_owner"},
            {"book_number": "3", "title": "Unselected"},
            {"book_number": "4", "title": "Rejected", "catalog_visibility": "public", "status": "rejected"},
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


if __name__ == "__main__":
    unittest.main()
