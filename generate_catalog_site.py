"""Generate crawlable book pages and discovery files for GitHub Pages."""

from __future__ import annotations

import html
import json
import re
import argparse
from pathlib import Path
from urllib.parse import quote, urlparse


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
    annotation = compact(book.get("annotation"))
    if annotation:
        return annotation[:157].rstrip(" ,.;:") + ("…" if len(annotation) > 157 else "")
    title = compact(book.get("title")) or "Libro"
    author = compact(book.get("author"))
    return f"{title}{f' — {author}' if author else ''}. Ficha en el catálogo VLC Biblio."


def direct_action(book):
    if compact(book.get("orderBot")):
        bot, start = compact(book.get("orderBot")), compact(book.get("orderStart"))
        if (book.get("availability") == "reserved" and book.get("section") == "exchange"
                and re.fullmatch(r"[A-Za-z0-9_]{5,32}", bot)
                and re.fullmatch(r"book_[0-9]+", start)):
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
    if book.get("section") != "exchange" or book.get("depositEur") != 20:
        return ""
    return '''<aside class="deposit-note" aria-label="Condiciones del depósito">
            <span class="deposit-note-icon" aria-hidden="true">↩</span>
            <span><strong>Depósito reembolsable: 20 euros</strong><small>por cada libro de esta biblioteca</small></span>
          </aside>'''


def is_toma_source(book):
    source = urlparse(compact(book.get("sourceUrl")))
    return (book.get("section") == "exchange"
            and book.get("orderBot") == "toma_lib_valencia_bot"
            and source.scheme == "https" and source.netloc == "funny-cannon-067.notion.site"
            and re.fullmatch(r"/[0-9a-f]{32}", source.path) is not None)


def static_book_markup(book):
    esc = lambda value: html.escape(compact(value), quote=True)
    title = esc(book.get("title") or "Sin título")
    author = esc(book.get("author") or "Autor no indicado")
    cover = compact(book.get("coverImage", {}).get("src") or book.get("cover"))
    cover_markup = (
        f'<img src="{esc(cover)}" alt="Portada: {title}" fetchpriority="high" '
        'decoding="async" referrerpolicy="no-referrer" />'
        if cover else f'<div class="cover-placeholder">{title}</div>'
    )
    details = []
    for label, value in (
        ("ISBN", book.get("isbn")),
        ("Año de publicación", book.get("year")),
        ("Editorial", book.get("publisher")),
    ):
        if compact(value):
            details.append(f"<dt>{label}</dt><dd>{esc(value)}</dd>")
    private = book.get("section") == "exchange"
    status = "🏠 Biblioteca particular" if private else "📚 Biblioteca Pilar Faus"
    note = (
        "Este libro pertenece a una biblioteca particular. Puedes solicitarlo en préstamo."
        if private else
        "Este libro forma parte del catálogo de la biblioteca pública Pilar Faus. Consulta allí su disponibilidad."
    )
    if is_toma_source(book):
        note = ('Книга в частной коллекции Библиотеки '
                '<a href="https://t.me/toma_lib_valencia" target="_blank" rel="noreferrer">ТОМА</a>. '
                'Вы можете запросить книгу на время.')
    action = direct_action(book)
    action_markup = ""
    if action:
        label = "Apuntarme a la lista de espera" if book.get("availability") == "reserved" else "Solicitar el libro por Telegram"
        if book.get("orderBot"):
            label = "Consultar disponibilidad en el bot"
        action_markup = f'<a class="telegram-action" href="{esc(action)}" target="_blank" rel="noreferrer">{esc(label)}</a>'
    annotation = esc(book.get("annotation") or "Todavía no se ha añadido una descripción.")
    deposit = deposit_markup(book)
    deposit_line = f"\n          {deposit}" if deposit else ""
    return f'''<section id="content">
      <article class="book">
        <div class="cover">{cover_markup}</div>
        <div class="body">
          <div class="badges"><span class="badge {'exchange' if private else 'library'}">{status}</span></div>
          <h1>{title}</h1>
          <p class="author">{author}</p>
          <dl class="details">{''.join(details)}</dl>
          <p class="annotation">{annotation}</p>{deposit_line}
          <div class="collection-note">{note}</div>
          <div class="actions">{action_markup}</div>
        </div>
      </article>
    </section>'''


def render_book_page(template, book, *, indexable=True, embedded_books=None):
    esc = lambda value: html.escape(compact(value), quote=True)
    title = compact(book.get("title")) or "Libro"
    author = compact(book.get("author"))
    page_title = f"{title}{f' — {author}' if author else ''} | VLC Biblio"
    canonical = book_url(book)
    description = description_for(book)
    image = absolute_asset_url(book.get("coverImage", {}).get("src") or book.get("cover"))
    structured = {
        "@context": "https://schema.org",
        "@type": "Book",
        "name": title,
        "url": canonical,
    }
    if author:
        structured["author"] = {"@type": "Person", "name": author}
    if compact(book.get("isbn")):
        structured["isbn"] = compact(book.get("isbn"))
    if image:
        structured["image"] = image
    if compact(book.get("annotation")):
        structured["description"] = compact(book.get("annotation"))
    robots = "index,follow" if indexable else "noindex,follow"
    metadata = f'''    <meta name="description" content="{esc(description)}" />
    <meta name="robots" content="{robots}" />
    <link rel="canonical" href="{esc(canonical)}" />
    <meta property="og:type" content="book" />
    <meta property="og:site_name" content="VLC Biblio" />
    <meta property="og:title" content="{esc(page_title)}" />
    <meta property="og:description" content="{esc(description)}" />
    <meta property="og:url" content="{esc(canonical)}" />
    {f'<meta property="og:image" content="{esc(image)}" />' if image else ''}
    <meta name="twitter:card" content="{'summary_large_image' if image else 'summary'}" />
    <script type="application/ld+json">{json.dumps(structured, ensure_ascii=False).replace('</', '<\\/')}</script>'''
    metadata = re.sub(r"(?m)^ +$", "", metadata)
    rendered = template.replace(
        '    <meta name="viewport" content="width=device-width, initial-scale=1" />',
        '    <meta name="viewport" content="width=device-width, initial-scale=1" />\n    <base href="../" />\n' + metadata,
        1,
    )
    rendered = rendered.replace('    <meta name="robots" content="noindex,follow" />\n', "", 1)
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


def write_site(root: Path, books):
    root = Path(root)
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

    urls = [(SITE_URL, ""), (SITE_URL + "events.html", ""), (SITE_URL + "privacy.html", "")]
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

