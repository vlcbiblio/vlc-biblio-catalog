"""Generate crawlable book pages and discovery files for GitHub Pages."""

from __future__ import annotations

import html
import json
import re
import argparse
from pathlib import Path
from urllib.parse import quote, urlparse

from book_categories import apply_categories, load_records, refresh_payload, static_categories_markup


SITE_URL = "https://vlcbiblio.github.io/vlc-biblio-catalog/"
BOOK_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
GENERATED_BOOK_PATTERN = re.compile(r"^b-[0-9a-f]{12}\.html$")

def compact(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def book_path(book):
    book_id = compact(book.get("id"))
    if not BOOK_ID_PATTERN.fullmatch(book_id):
        raise ValueError(f"Unsafe public book id: {book_id!r}")
    return f"books/{book_id}.html"


def book_url(book):
    return SITE_URL + book_path(book)


def absolute_asset_url(value):
    value = compact(value)
    if value.startswith("./"):
        return SITE_URL + value[2:]
    if value.startswith("/"):
        return "https://vlcbiblio.github.io" + value
    return value


def description_for(book):
    title = compact(book.get("title")) or "Книга"
    author = compact(book.get("author"))
    annotation = compact(book.get("annotation"))
    prefix = f"{title}{f' — {author}' if author else ''}. Книга в Валенсии (VLC Biblio)."
    if annotation:
        combined = f"{prefix} {annotation}"
        return combined[:157].rstrip(" ,.;:") + ("…" if len(combined) > 157 else "")
    return f"{title}{f' — {author}' if author else ''}. Книга на русском в Валенсии — взять почитать в каталоге VLC Biblio."


def direct_action(book):
    if compact(book.get("orderBot")):
        bot, start = compact(book.get("orderBot")), compact(book.get("orderStart"))
        if (book.get("availability") == "reserved" and book.get("section") == "exchange"
                and re.fullmatch(r"[A-Za-z0-9_]{5,32}", bot)
                and re.fullmatch(r"book_[0-9]+", start)):
            if bot == "toma_lib_valencia_bot":
                start = f"ext_{start}"
            return f"https://t.me/{bot}?start={start}"
        return ""
    request_id = compact(book.get("requestId"))
    if book.get("section") != "exchange" or not request_id.isdigit():
        return ""
    if book.get("availability") == "available":
        return f"https://t.me/VLS_Biblio_bot?start=book_{quote(request_id)}"
    if book.get("availability") == "reserved":
        return f"https://t.me/VLS_Biblio_bot?start=wait_{quote(request_id)}"
    return ""


def deposit_markup(book):
    if book.get("section") != "exchange":
        return ""
    deposit_eur = book.get("depositEur")
    if is_toma_source(book) or deposit_eur == 10:
        return '''<aside class="deposit-note" aria-label="Condiciones del depósito">
            <span class="deposit-note-icon" aria-hidden="true">↩</span>
            <span><strong>Возвратный депозит (залог) — 10 евро</strong><small>Библиотека работает по подписке:
1 книга на руках — 5 €/месяц, 3 книги — 10 €/месяц</small></span>
          </aside>'''
    if deposit_eur == 20:
        return '''<aside class="deposit-note" aria-label="Condiciones del depósito">
            <span class="deposit-note-icon" aria-hidden="true">↩</span>
            <span><strong>Depósito reembolsable: 20 euros</strong><small>por cada libro de esta biblioteca</small></span>
          </aside>'''
    return ""


def is_toma_source(book):
    source = urlparse(compact(book.get("sourceUrl")))
    return (book.get("section") == "exchange"
            and book.get("orderBot") == "toma_lib_valencia_bot"
            and source.scheme == "https" and source.netloc == "funny-cannon-067.notion.site"
            and re.fullmatch(r"/[0-9a-f]{32}", source.path) is not None)


def static_book_markup(book):
    esc = lambda value: html.escape(compact(value), quote=True)
    title = esc(book.get("title") or "Без названия")
    author = esc(book.get("author") or "Автор не указан")
    cover = compact(book.get("coverImage", {}).get("src") or book.get("cover"))
    cover_markup = (
        f'<img src="{esc(cover)}" alt="Обложка книги: {title}" fetchpriority="high" '
        'decoding="async" referrerpolicy="no-referrer" />'
        if cover else f'<div class="cover-placeholder">{title}</div>'
    )
    details = []
    for label, value in (
        ("ISBN", book.get("isbn")),
        ("Год выпуска", book.get("year")),
        ("Издательство", book.get("publisher")),
    ):
        if compact(value):
            details.append(f"<dt>{label}</dt><dd>{esc(value)}</dd>")
    private = book.get("section") == "exchange"
    status = "🏠 Частная библиотека в Валенсии" if private else "📚 Библиотека Pilar Faus (Валенсия)"
    note = (
        "Книга в частной коллекции в Валенсии. Вы можете запросить книгу на время через Telegram-бота VLC Biblio."
        if private else
        "Книга в фонде государственной библиотеки Валенсии Pilar Faus."
    )
    if is_toma_source(book):
        note = ('Книга в коллекции частной библиотеки '
                '<a href="https://www.instagram.com/toma_lib_valencia/" target="_blank" rel="noreferrer">ТОМА</a>. '
                'Выдача книг по подписке.')
    action = direct_action(book)
    action_markup = ""
    if action:
        label = "Встать в очередь через Telegram" if book.get("availability") == "reserved" else "Запросить книгу через Telegram"
        if book.get("orderBot"):
            label = "Consultar disponibilidad en el bot"
        action_markup = f'<a class="telegram-action" href="{esc(action)}" target="_blank" rel="noreferrer">{esc(label)}</a>'
    annotation = esc(book.get("annotation") or "Описание пока не добавлено.")
    deposit = deposit_markup(book)
    deposit_line = f"\n          {deposit}" if deposit else ""
    location_note = esc(book.get("locationNote") or ("Местоположение: Angel Guimera" if is_toma_source(book) else ""))
    location_markup = f'<strong class="location-note">{location_note}</strong>' if location_note else ""
    if is_toma_source(book):
        location_line = f"\n          {location_markup}" if location_markup else ""
        notes_block = f'\n          <div class="collection-note"><span>{note}</span></div>{deposit_line}{location_line}'
    else:
        notes_block = f'{deposit_line}\n          <div class="collection-note"><span>{note}</span>{location_markup}</div>'
    return f'''<section id="content">
      <article class="book">
        <div class="cover">{cover_markup}</div>
        <div class="body">
          <div class="badges"><span class="badge {'exchange' if private else 'library'}">{status}</span></div>
          <h1>{title}</h1>
          <p class="author">{author}</p>
          <p class="annotation">{annotation}</p>{notes_block}
          {static_categories_markup(book)}
          <dl class="details">{''.join(details)}</dl>
          <div class="actions">{action_markup}</div>
        </div>
      </article>
    </section>'''


def render_book_page(template, book, *, indexable=True, embedded_books=None):
    esc = lambda value: html.escape(compact(value), quote=True)
    title = compact(book.get("title")) or "Книга"
    author = compact(book.get("author"))
    page_title = f"{title}{f' — {author}' if author else ''} | Книги в Валенсии — VLC Biblio"
    canonical = book_url(book)
    description = description_for(book)
    image = absolute_asset_url(book.get("coverImage", {}).get("src") or book.get("cover"))
    structured = {
        "@context": "https://schema.org",
        "@type": "Book",
        "name": title,
        "url": canonical,
        "inLanguage": "ru",
        "isPartOf": {
            "@type": "WebSite",
            "name": "VLC Biblio — Книги на русском в Валенсии",
            "url": SITE_URL,
        },
    }
    if author:
        structured["author"] = {"@type": "Person", "name": author}
    if compact(book.get("isbn")):
        structured["isbn"] = compact(book.get("isbn"))
    if compact(book.get("publisher")):
        structured["publisher"] = {"@type": "Organization", "name": compact(book.get("publisher"))}
    if compact(book.get("year")):
        structured["datePublished"] = compact(book.get("year"))
    if image:
        structured["image"] = image
    if compact(book.get("annotation")):
        structured["description"] = compact(book.get("annotation"))
    breadcrumb = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": 1,
                "name": "Книги на русском в Валенсии — VLC Biblio",
                "item": SITE_URL,
            },
            {
                "@type": "ListItem",
                "position": 2,
                "name": title,
                "item": canonical,
            },
        ],
    }
    robots = "index,follow,max-image-preview:large" if indexable else "noindex,follow"
    metadata = f'''    <meta name="description" content="{esc(description)}" />
    <meta name="robots" content="{robots}" />
    <link rel="canonical" href="{esc(canonical)}" />
    <meta property="og:type" content="book" />
    <meta property="og:locale" content="ru_RU" />
    <meta property="og:site_name" content="VLC Biblio — Книги в Валенсии" />
    <meta property="og:title" content="{esc(page_title)}" />
    <meta property="og:description" content="{esc(description)}" />
    <meta property="og:url" content="{esc(canonical)}" />
    {f'<meta property="og:image" content="{esc(image)}" />' if image else ''}
    <meta name="twitter:card" content="{'summary_large_image' if image else 'summary'}" />
    <script type="application/ld+json">{json.dumps(structured, ensure_ascii=False).replace('</', '<\\/')}</script>
    <script type="application/ld+json">{json.dumps(breadcrumb, ensure_ascii=False).replace('</', '<\\/')}</script>'''
    metadata = re.sub(r"(?m)^ +$", "", metadata)
    rendered = template.replace(
        '    <meta name="viewport" content="width=device-width, initial-scale=1" />',
        '    <meta name="viewport" content="width=device-width, initial-scale=1" />\n    <base href="../" />\n' + metadata,
        1,
    )
    rendered = rendered.replace('    <meta name="robots" content="noindex,follow" />\n', "", 1)
    rendered = rendered.replace("<title>Книга | Книги в Валенсии — VLC Biblio</title>", f"<title>{esc(page_title)}</title>", 1)
    rendered = rendered.replace("<title>Libro | VLC Biblio</title>", f"<title>{esc(page_title)}</title>", 1)
    rendered = rendered.replace("  <body>", f'  <body data-book-id="{esc(book.get("id"))}">', 1)
    rendered = rendered.replace('      <section id="content"></section>', "      " + static_book_markup(book), 1)
    if embedded_books:
        payload = json.dumps(list(embedded_books), ensure_ascii=False).replace("</", "<\\/")
        rendered = re.sub(
            r'    <script src="\./data/books\.js[^>]*></script>',
            lambda match: match.group(0) + "\n" +
            f'    <script>window.BIBLIO_BOOKS = [...(Array.isArray(window.BIBLIO_BOOKS) ? window.BIBLIO_BOOKS : []), ...{payload}];</script>',
            rendered,
            count=1,
        )
    return rendered


def static_latest_books_markup(books):
    esc = lambda value: html.escape(compact(value), quote=True)
    latest = sorted(
        books,
        key=lambda book: compact(book.get("addedAt") or book.get("updatedAt")),
        reverse=True,
    )[:6]
    cards = []
    for book in latest:
        title = esc(book.get("title") or "Без названия")
        author = esc(book.get("author") or "Автор не указан")
        cover = compact(book.get("coverImage", {}).get("src") or book.get("cover"))
        cover_html = (
            f'<img src="{esc(cover)}" alt="Обложка книги: {title}" loading="lazy" decoding="async" referrerpolicy="no-referrer" />'
            if cover else f'<div class="cover-placeholder">{title}</div>'
        )
        cards.append(
            f'<a class="latest-card" href="./{esc(book_path(book))}">'
            f'<div class="latest-cover">{cover_html}</div>'
            f'<h3>{title}</h3><p>{author}</p></a>'
        )
    return "".join(cards)


def update_homepage_snapshot(root: Path, books):
    index_path = root / "index.html"
    if not index_path.is_file():
        return
    source = index_path.read_text(encoding="utf-8")
    total_count = len(books)
    exchange_count = sum(1 for book in books if book.get("section") == "exchange")
    updated = re.sub(
        r'(<strong id="totalCount">)\d+(</strong>)',
        rf"\g<1>{total_count}\g<2>",
        source,
        count=1,
    )
    updated = re.sub(
        r'(<strong id="exchangeCount">)\d+(</strong>)',
        rf"\g<1>{exchange_count}\g<2>",
        updated,
        count=1,
    )
    updated = re.sub(
        r"<!-- LATEST_BOOKS_START -->.*?<!-- LATEST_BOOKS_END -->",
        lambda _match: f"<!-- LATEST_BOOKS_START -->{static_latest_books_markup(books)}<!-- LATEST_BOOKS_END -->",
        updated,
        count=1,
        flags=re.DOTALL,
    )
    if updated != source:
        index_path.write_text(updated, encoding="utf-8")


def write_site(root: Path, books):
    root = Path(root)
    records = load_records(root)
    refresh_payload(root, books, records)
    books = apply_categories(books, records)
    template = (root / "book.html").read_text(encoding="utf-8")
    output_dir = root / "books"
    output_dir.mkdir(parents=True, exist_ok=True)
    expected = set()
    for book in books:
        filename = Path(book_path(book)).name
        expected.add(filename)
        (output_dir / filename).write_text(render_book_page(template, book), encoding="utf-8")
    for existing in output_dir.glob("*.html"):
        if GENERATED_BOOK_PATTERN.fullmatch(existing.name) and existing.name not in expected:
            existing.unlink()

    update_homepage_snapshot(root, books)

    latest_dates = [
        compact(book.get("updatedAt") or book.get("addedAt"))[:10]
        for book in books
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", compact(book.get("updatedAt") or book.get("addedAt"))[:10])
    ]
    home_lastmod = max(latest_dates) if latest_dates else ""
    urls = [(SITE_URL, home_lastmod), (SITE_URL + "new-year.html", home_lastmod), (SITE_URL + "events.html", ""), (SITE_URL + "events-archive.html", ""), (SITE_URL + "privacy.html", ""), (SITE_URL + "legal.html", "")]
    urls.extend((book_url(book), compact(book.get("updatedAt") or book.get("addedAt"))[:10]) for book in books)
    sitemap_items = []
    for url, lastmod in urls:
        lastmod_markup = f"<lastmod>{html.escape(lastmod)}</lastmod>" if re.fullmatch(r"\d{4}-\d{2}-\d{2}", lastmod) else ""
        sitemap_items.append(f"  <url><loc>{html.escape(url)}</loc>{lastmod_markup}</url>")
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(sitemap_items) + "\n</urlset>\n"
    (root / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    (root / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}sitemap.xml\n", encoding="utf-8")


def load_books_js(path: Path):
    source = Path(path).read_text(encoding="utf-8")
    match = re.fullmatch(r"\s*window\.BIBLIO_BOOKS\s*=\s*(\[.*\])\s*;\s*", source, re.DOTALL)
    if not match:
        raise ValueError(f"Unsupported catalog payload: {path}")
    books = json.loads(match.group(1))
    if not isinstance(books, list):
        raise ValueError("Catalog payload must be a list")
    return books


def main():
    parser = argparse.ArgumentParser(description="Generate crawlable VLC Biblio pages.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--data", type=Path)
    args = parser.parse_args()
    data = args.data or args.root / "data" / "books.js"
    books = load_books_js(data)
    write_site(args.root, books)
    print(f"Generated {len(books)} book pages, sitemap.xml and robots.txt")


if __name__ == "__main__":
    main()

