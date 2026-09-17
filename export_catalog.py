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
OWNER_LOCATION_NOTES = {
    "irishkakosh": (
        "Местоположение: Сагунто. Доступность метро на станциях Colón и Aragón "
        "в определённые дни и часы."
    ),
}

# These existing catalog entries were reviewed manually because their metadata
# does not contain a reliable age marker (or describes young-adult fiction).
ADULT_REQUEST_IDS = {
    "34", "40", "42", "45", "47", "48", "49", "70", "85", "106", "109",
    "118", "120", "138", "143", "148", "164", "165", "170", "194", "196",
    "198", "207", "209", "218", "227", "231", "232", "237",
}

CHILDREN_REQUEST_IDS = set("""
24 25 23 21 19 17 22 20 16 14 3 1 2 235 95 104 80 44 188 184 180 99 193 212
107 108 155 78 174 101 176 96 233 89 206 130 149 177 131 162 119 63 52 144
205 172 221 201 123 214 58 112 102 145 167 128 50 81 190 139 94 234 178 97 113
86 56 75 28 126 158 219 68 114 134 189 159 141 179 199 43 150 225 72 116 171
129 79 173 103 73 203 136 140 163 213 181 137 197 67 224 91 98 121 57 187 215
74 204 220 161 53 39 122 54 236 62 169 151 210 76 222 66 55 146 27 87 93 61 152
90 186 60 105 82 127 142 51 64 88 200 125 195 208 59 168 230 69 77 115 46 83 175
124 111 160 153 223 229 185 211 71 183 154 192 166 41 182 147 100 191 92 132 110 117
133 157 156 202 84 216 135 217 228 226 65 37 36 29 35 30 33 32 38 31 18 26 15 13
9 11 10 7 6 5 12 4 8
""".split())

CHILDREN_MARKERS = (
    "для детей", "детская", "детский", "детей", "ребёнок", "ребенка",
    "ребёнка", "малыш", "дошколь", "школьник", "школьная", "школьного",
    "подросток", "подростков", "юный читатель", "юных читателей",
    "внеклассное чтение", "среднего школьного возраста", "младшего школьного",
)


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
    destination = clean(row.get("destination")).lower()
    if any(marker in destination for marker in EXCHANGE_MARKERS):
        return "exchange"
    return "library"


def source_kind_for(row):
    destination = clean(row.get("destination")).lower()
    if any(marker in destination for marker in EXCHANGE_MARKERS):
        return "user"
    return "library"


def catalog_status_for(row, section):
    explicit = clean(row.get("catalog_status"))
    if section == "exchange":
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
        "unavailable": "unavailable",
        "given": "given",
        "archived": "archived",
        "planned": "planned",
        "transferred": "transferred",
        "accepted": "accepted",
        "доступна": "available",
        "зарезервирована": "reserved",
        "недоступна": "unavailable",
        "передана": "given",
        "архив": "archived",
        "запланирована": "planned",
        "передано": "transferred",
        "принято": "accepted",
    }
    if explicit in known:
        return known[explicit]
    return "available" if section == "exchange" else "transferred"


def audience_for(row):
    explicit = clean(
        row.get("audience")
        or row.get("literature_audience")
        or row.get("age_group")
    ).lower()
    if explicit in {"children", "child", "kids", "детская", "дети"}:
        return "children"
    if explicit in {"adult", "adults", "взрослая", "взрослые"}:
        return "adult"

    request_id = clean(row.get("book_number"))
    if request_id in ADULT_REQUEST_IDS:
        return "adult"
    if request_id in CHILDREN_REQUEST_IDS:
        return "children"

    searchable = " ".join(
        clean(row.get(field)).lower()
        for field in ("title", "author", "publisher", "annotation")
    ).replace("ё", "е")
    normalized_markers = tuple(marker.replace("ё", "е") for marker in CHILDREN_MARKERS)
    if any(marker in searchable for marker in normalized_markers):
        return "children"
    if re.search(r"(?:^|\D)(?:0|3|6|7|8|10|11|12|14)\s*\+", searchable):
        return "children"
    return "adult"


def library_key_for(row, section):
    source_kind = source_kind_for(row)
    if source_kind == "library":
        return "library:" + catalog_status_for(row, section).lower()

    owner_source = (
        clean(row.get("user_id"))
        or clean(row.get("chat_id"))
        or clean(row.get("username")).lower()
    )
    if not owner_source:
        return ""
    owner_hash = hashlib.sha1(owner_source.encode("utf-8")).hexdigest()[:12]
    return f"user:{owner_hash}"


def location_note_for(row, section):
    if section != "exchange":
        return ""
    username = clean(row.get("username")).lstrip("@").casefold()
    return OWNER_LOCATION_NOTES.get(username, "")


def has_public_book_data(row):
    if clean(row.get("status")) in BAD_STATUSES:
        return False
    if (clean(row.get("catalog_visibility")) != "public"
            and not clean(row.get("channel_published_at") or row.get("user_published_at"))):
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
        "sourceKind": source_kind_for(row),
        "availability": availability_for(row, section),
        "audience": audience_for(row),
        "cover": clean(row.get("preview_url")),
        "isbn": clean(row.get("isbn")),
        "year": clean(row.get("publication_year")),
        "publisher": clean(row.get("publisher")),
        "annotation": clean(row.get("annotation")),
        "locationNote": location_note_for(row, section),
        "sourceUrl": clean(row.get("metadata_source_url")),
        "livelibUrl": clean(row.get("livelib_url")),
        "wildberriesUrl": clean(row.get("wildberries_url")),
        "addedAt": parse_request_timestamp(request_file) or clean(row.get("catalog_added_at")),
        "updatedAt": clean(row.get("channel_published_at") or row.get("user_published_at")
                           or row.get("catalog_added_at")),
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
    root = output.resolve().parent.parent
    manifest_path = root / "assets/covers/manifest.json"
    covers = json.loads(manifest_path.read_text(encoding="utf-8")).get("covers", {}) if manifest_path.is_file() else {}
    public_books = []
    for book in books:
        public = {
            key: value
            for key, value in book.items()
            if key != "coverImage" and (key != "locationNote" or value)
        }
        # Match the exact source URL, so a corrected cover never uses an old image.
        variants = covers.get(book.get("cover"), {}).get("variants", [])
        if variants and all((root / image["src"]).is_file() for image in variants):
            largest = variants[-1]
            public["coverImage"] = {
                "src": largest["src"],
                "srcset": ", ".join(f'{image["src"]} {image["width"]}w' for image in variants),
                "width": largest["width"],
                "height": largest["height"],
            }
        public_books.append(public)
    payload = json.dumps(public_books, ensure_ascii=False, indent=2)
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
