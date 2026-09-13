import csv
import tempfile
import unittest
from pathlib import Path

import export_catalog as export


class CatalogOnlyExportTests(unittest.TestCase):
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
