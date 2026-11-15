"""Reviewed category overlay, independent of book ownership and ordering data."""
from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path
import re
from urllib.parse import urlparse

IDENTITY_FIELDS = ('title', 'author', 'isbn', 'annotation')
CATEGORY_FIELDS = ('reader_age_groups', 'reader_age_status', 'reader_age_basis', 'genres', 'genre_status', 'genre_basis', 'edition_age_ratings', 'edition_rating_status', 'edition_rating_sources', 'reader_age_sources', 'genre_sources', 'external_match', 'sources', 'research_sources', 'research_scope', 'editorial_note', 'classification_review_date')
LIST_FIELDS = {'reader_age_groups', 'reader_age_basis', 'genres', 'edition_age_ratings'}
SOURCE_FIELDS = {'edition_rating_sources', 'reader_age_sources', 'genre_sources', 'sources', 'research_sources'}


def clean(value):
    return re.sub(r'\s+', ' ', str(value or '')).strip()


def identity(book):
    return {key: clean(book.get(key)) for key in IDENTITY_FIELDS}


def safe_url(value):
    try:
        parsed = urlparse(str(value))
        return str(value) if parsed.scheme in ('http', 'https') and parsed.hostname and not parsed.username and not parsed.password else None
    except ValueError:
        return None


def category_fields(row):
    result = {}
    for key in CATEGORY_FIELDS:
        if key in LIST_FIELDS:
            result[key] = [str(v) for v in row.get(key, [])] if isinstance(row.get(key), list) else []
        elif key in SOURCE_FIELDS:
            result[key] = [url for v in row.get(key, []) if (url := safe_url(v))] if isinstance(row.get(key), list) else []
        else:
            result[key] = str(row.get(key) or '')
    return result


def pending(book, changed=False):
    return category_fields({
        'reader_age_groups': ['Возрастная рекомендация на проверке'], 'reader_age_status': 'pending_review',
        'genres': ['Категория на проверке'], 'genre_status': 'pending_review',
        'reader_age_basis': ['Библиографические сведения изменились; нужна повторная проверка.' if changed else 'Новая книга: возраст и жанр ещё не проверены.'],
        'edition_rating_status': 'unknown', 'external_match': 'unresolved',
    })


def load_records(root):
    path = Path(root) / 'data/book-categories.json'
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('version') != 1 or not isinstance(data.get('records'), dict):
        raise ValueError('Unsupported reviewed category overlay')
    for key, value in data['records'].items():
        if not isinstance(value, dict) or not isinstance(value.get('identity'), dict):
            raise ValueError(f'Invalid category record: {key}')
    return data['records']


def resolved(book, records):
    record = records.get(str(book.get('id')))
    if not record or record.get('identity') != identity(book):
        return pending(book, changed=bool(record))
    if not record.get('reader_age_groups') or not record.get('genres') or record.get('reader_age_status') not in ('external_catalog', 'editorial_recommendation', 'pending_review') or record.get('genre_status') not in ('external_catalog', 'editorial_review', 'pending_review'):
        return pending(book)
    return category_fields(record)


def apply_categories(books, records):
    return [{**book, **resolved(book, records)} for book in books]


def refresh_payload(root, books, records=None):
    root = Path(root)
    records = load_records(root) if records is None else records
    # Keep reviewed JSON untouched. Active JS includes explicit pending entries
    # for new/changed books, without overwriting previous reviewed decisions.
    active = {str(book.get('id')): {'identity': identity(book), **resolved(book, records)} for book in books}
    payload = json.dumps(active, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
    source = 'window.BIBLIO_CATEGORIES = ' + payload + ';\n'
    data = root / 'data'; data.mkdir(parents=True, exist_ok=True)
    (data / 'book-categories.js').write_text(source, encoding='utf-8')
    version = hashlib.sha256(source.encode('utf-8')).hexdigest()[:12]
    for name in ('index.html', 'book.html'):
        path = root / name
        if path.is_file():
            text = path.read_text(encoding='utf-8')
            updated = re.sub(r'(\./data/book-categories\.js)(?:\?v=[^"<>]*)?', lambda m: m[1] + '?v=' + version, text)
            if updated != text: path.write_text(updated, encoding='utf-8')
    return active


def import_reviewed(root, source):
    from generate_catalog_site import load_books_js
    root, source = Path(root), Path(source)
    raw = (root / 'data/books.js').read_bytes()
    reviewed = json.loads(source.read_text(encoding='utf-8'))
    if reviewed.get('source_sha256') != hashlib.sha256(raw).hexdigest():
        raise ValueError('Reviewed snapshot does not match the current public catalog')
    books = load_books_js(root / 'data/books.js')
    by_id = {str(book['id']): book for book in books}
    rows = reviewed.get('books', [])
    if len(by_id) != len(books) or len(rows) != len(books) or {str(row['id']) for row in rows} != set(by_id):
        raise ValueError('Reviewed and public IDs must match exactly without duplicates')
    records = {}
    for row in rows:
        if row.get('reader_age_status') not in ('external_catalog', 'editorial_recommendation') or row.get('genre_status') not in ('external_catalog', 'editorial_review') or not row.get('reader_age_groups') or not row.get('genres'):
            raise ValueError(f'Unfinished classification: {row.get("id")}')
        if any(clean(row.get(key)) != clean(by_id[str(row['id'])].get(key)) for key in ('title', 'author', 'isbn')):
            raise ValueError(f'Reviewed identity differs: {row["id"]}')
        records[str(row['id'])] = {'identity': identity(by_id[str(row['id'])]), **category_fields(row)}
    output = root / 'data/book-categories.json'
    output.write_text(json.dumps({'version': 1, 'review_date': reviewed.get('date', ''), 'records': records}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    refresh_payload(root, books, records)
    return len(records)


def static_categories_markup(book):
    if not book.get('reader_age_groups') and not book.get('genres'):
        return ''
    esc = lambda value: html.escape(str(value or ''), quote=True)
    statuses = {'external_catalog': 'Confirmado por una fuente externa', 'editorial_recommendation': 'Recomendación de la biblioteca', 'editorial_review': 'Categoría editorial', 'pending_review': 'Pendiente de revisión', 'unknown': 'Sin datos confirmados', 'conflict': 'Las fuentes discrepan'}
    def group(label, key, status_key):
        values = book.get(key) or ['Sin datos confirmados']
        return f'<div class="local-category-detail"><dt>{label}</dt><dd>{esc(" · ".join(values))}<small>{esc(statuses.get(book.get(status_key), "Pendiente de revisión"))}</small></dd></div>'
    basis = '; '.join(dict.fromkeys([*book.get('reader_age_basis', []), book.get('genre_basis', '')])).strip('; ')
    research = ' '.join(f'<a href="{esc(url)}" target="_blank" rel="noopener noreferrer">{esc(urlparse(url).hostname)}</a>' for value in book.get('research_sources', []) if (url := safe_url(value)))
    return '<div class="local-categories"><dl>' + group('Edad de lectura', 'reader_age_groups', 'reader_age_status') + group('Género y tema', 'genres', 'genre_status') + group('Clasificación de la edición', 'edition_age_ratings', 'edition_rating_status') + '</dl><details><summary>Base de la recomendación editorial</summary><p>La edad recomendada y la clasificación de una edición son datos distintos.</p>' + (f'<p>{esc(basis)}</p>' if basis else '') + (f'<p>Las referencias corresponden a la obra o serie y no confirman el ISBN de esta edición.</p><p>{research}</p>' if research else '') + '</details></div>'
