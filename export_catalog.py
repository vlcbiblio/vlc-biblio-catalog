import argparse
import csv
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_SOURCE = ROOT.parent / "1.Telegram" / "_obrabotka" / "books.csv"
DEFAULT_OUTPUT = ROOT / "data" / "books.js"
DEFAULT_INDEX = ROOT / "index.html"
DEFAULT_BOOK_PAGE = ROOT / "book.html"

BAD_STATUSES = {"bad_photo", "rejected"}
EXCHANGE_MARKERS = ("книгообмен", "каталог")
INTERNAL_CATALOG_STATUSES = {"На согласовании"}
PUBLIC_LIBRARY_STATUSES = {"pilar faus"}


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


def public_id_for(row):
    stable_source = clean(row.get("request_file")) or clean(row.get("isbn"))
    if stable_source:
        return "b-" + hashlib.sha1(stable_source.encode("utf-8")).hexdigest()[:12]
    fallback = "|".join(
        clean(row.get(field)) for field in ("title", "author", "publication_year")
    )
    return "b-" + hashlib.sha1(fallback.encode("utf-8")).hexdigest()[:12]


def section_for(row):
    explicit = clean(row.get("catalog_status")).lower()
    if explicit in PUBLIC_LIBRARY_STATUSES:
        return "library"
    destination = clean(row.get("destination")).lower()
    return "exchange" if any(marker in destination for marker in EXCHANGE_MARKERS) else "library"


def catalog_status_for(row, section):
    explicit = clean(row.get("catalog_status"))
    if section == "exchange" and explicit.lower() in EXCHANGE_MARKERS:
        return "Частная библиотека"
    if explicit and explicit not in INTERNAL_CATALOG_STATUSES:
        return explicit
    return "Частная библиотека" if section == "exchange" else "Pilar Faus"


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


def library_key_for(row, section):
    status = clean(row.get("catalog_status"))
    if section == "library":
        return "library:" + (status or "Pilar Faus").lower()

    owner_source = (
        clean(row.get("user_id"))
        or clean(row.get("chat_id"))
        or clean(row.get("username")).lower()
    )
    if not owner_source:
        return ""
    owner_hash = hashlib.sha1(owner_source.encode("utf-8")).hexdigest()[:12]
    return f"user:{owner_hash}"


def has_public_book_data(row):
    if clean(row.get("status")) in BAD_STATUSES:
        return False
    if not clean(row.get("channel_published_at") or row.get("user_published_at")):
        return False
    return any(clean(row.get(field)) for field in ("isbn", "title", "author"))


def public_book(row):
    section = section_for(row)
    book_number = clean(row.get("book_number"))
    request_file = clean(row.get("request_file"))
    return {
        "id": public_id_for(row),
        "requestId": book_number or re.sub(r"\W+", "-", request_file).strip("-"),
        "title": clean(row.get("title")),
        "author": clean(row.get("author")),
        "section": section,
        "catalogStatus": catalog_status_for(row, section),
        "libraryKey": library_key_for(row, section),
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


def section_priority(book):
    return 0 if book.get("section") == "library" else 1


def book_timestamp(book):
    value = book.get("updatedAt") or book.get("addedAt") or ""
    if not value:
        return 0
    try:
        return datetime.fromisoformat(value).timestamp()
    except ValueError:
        return 0


def load_books(source):
    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    books = [public_book(row) for row in rows if has_public_book_data(row)]
    return sorted(
        books,
        key=lambda book: (
            section_priority(book),
            -book_timestamp(book),
            book.get("id") or "",
        ),
    )


def write_books(output, books):
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(books, ensure_ascii=False, indent=2)
    output.write_text(f"window.BIBLIO_BOOKS = {payload};\n", encoding="utf-8")


def update_data_cache_buster(*html_paths):
    version = datetime.now().strftime("%Y%m%d%H%M%S")
    for html_path in html_paths:
        if not html_path.is_file():
            continue
        html = html_path.read_text(encoding="utf-8")
        updated = re.sub(
            r'(\./data/books\.js)(?:\?v=[^"]*)?',
            rf"\1?v={version}",
            html,
            count=1,
        )
        if updated != html:
            html_path.write_text(updated, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export public VLC Biblio catalog data.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--book-page", type=Path, default=DEFAULT_BOOK_PAGE)
    args = parser.parse_args()

    books = load_books(args.source)
    write_books(args.output, books)
    update_data_cache_buster(args.index, args.book_page)
    print(f"Exported {len(books)} books to {args.output}")


if __name__ == "__main__":
    main()
