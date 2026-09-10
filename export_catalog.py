import argparse
import csv
import json
import re
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_SOURCE = ROOT.parent / "1.Telegram" / "_obrabotka" / "books.csv"
DEFAULT_OUTPUT = ROOT / "data" / "books.js"

BAD_STATUSES = {"bad_photo", "rejected"}
EXCHANGE_MARKER = "книгообмен"


def clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def parse_request_timestamp(request_file):
    match = re.match(r"(\d{8})_(\d{6})_", request_file or "")
    if not match:
        return ""
    stamp = "".join(match.groups())
    try:
        return datetime.strptime(stamp, "%Y%m%d%H%M%S").isoformat(timespec="seconds")
    except ValueError:
        return ""


def section_for(row):
    destination = clean(row.get("destination")).lower()
    return "exchange" if EXCHANGE_MARKER in destination else "library"


def catalog_status_for(row, section):
    explicit = clean(row.get("catalog_status"))
    if explicit:
        return explicit
    return "Книгообмен" if section == "exchange" else "Pilar Faus"


def availability_for(row, section):
    explicit = clean(
        row.get("availability_status")
        or row.get("public_status")
        or row.get("catalog_availability")
    ).lower()
    known = {
        "available": "available",
        "reserved": "reserved",
        "given": "given",
        "archived": "archived",
        "planned": "planned",
        "transferred": "transferred",
        "accepted": "accepted",
        "доступна": "available",
        "зарезервирована": "reserved",
        "передана": "given",
        "архив": "archived",
        "запланирована": "planned",
        "передано": "transferred",
        "принято": "accepted",
    }
    if explicit in known:
        return known[explicit]
    return "available" if section == "exchange" else "transferred"


def has_public_book_data(row):
    if clean(row.get("status")) in BAD_STATUSES:
        return False
    if not clean(row.get("channel_published_at")):
        return False
    return any(clean(row.get(field)) for field in ("isbn", "title", "author"))


def public_book(row):
    section = section_for(row)
    book_number = clean(row.get("book_number"))
    request_file = clean(row.get("request_file"))
    return {
        "id": book_number or re.sub(r"\W+", "-", request_file).strip("-"),
        "title": clean(row.get("title")),
        "author": clean(row.get("author")),
        "section": section,
        "catalogStatus": catalog_status_for(row, section),
        "availability": availability_for(row, section),
        "cover": clean(row.get("preview_url")),
        "isbn": clean(row.get("isbn")),
        "year": clean(row.get("publication_year")),
        "publisher": clean(row.get("publisher")),
        "annotation": clean(row.get("annotation")),
        "sourceUrl": clean(row.get("metadata_source_url")),
        "livelibUrl": clean(row.get("livelib_url")),
        "wildberriesUrl": clean(row.get("wildberries_url")),
        "addedAt": parse_request_timestamp(request_file),
        "updatedAt": clean(row.get("channel_published_at") or row.get("user_published_at")),
    }


def load_books(source):
    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    books = [public_book(row) for row in rows if has_public_book_data(row)]
    return sorted(
        books,
        key=lambda book: (book.get("updatedAt") or book.get("addedAt") or "", book.get("id") or ""),
        reverse=True,
    )


def write_books(output, books):
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(books, ensure_ascii=False, indent=2)
    output.write_text(f"window.BIBLIO_BOOKS = {payload};\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export public VLC Biblio catalog data.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    books = load_books(args.source)
    write_books(args.output, books)
    print(f"Exported {len(books)} books to {args.output}")


if __name__ == "__main__":
    main()
