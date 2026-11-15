/* Category-only overlay. Ownership, availability and Telegram routes are retained. */
((root) => {
  'use strict';
  const fields = ['reader_age_groups', 'reader_age_status', 'reader_age_basis', 'genres', 'genre_status', 'genre_basis', 'edition_age_ratings', 'edition_rating_status', 'edition_rating_sources', 'reader_age_sources', 'genre_sources', 'external_match', 'sources', 'research_sources', 'research_scope', 'editorial_note', 'classification_review_date'];
  const clean = value => String(value ?? '').replace(/\s+/g, ' ').trim();
  const identity = book => Object.fromEntries(['title', 'author', 'isbn', 'annotation'].map(key => [key, clean(book[key])]));
  function apply(books, records) {
    return books.map(book => {
      const record = records[String(book.id)];
      const current = identity(book);
      const matched = record?.identity && Object.keys(current).every(key => record.identity[key] === current[key])
        && Array.isArray(record.reader_age_groups) && record.reader_age_groups.length
        && Array.isArray(record.genres) && record.genres.length
        && ['external_catalog', 'editorial_recommendation', 'pending_review'].includes(record.reader_age_status)
        && ['external_catalog', 'editorial_review', 'pending_review'].includes(record.genre_status);
      const category = matched ? record : {
        reader_age_groups: ['Возрастная рекомендация на проверке'], reader_age_status: 'pending_review',
        genres: ['Категория на проверке'], genre_status: 'pending_review', edition_age_ratings: [], edition_rating_status: 'unknown',
        reader_age_basis: [record ? 'Библиографические сведения изменились; нужна повторная проверка.' : 'Новая книга: возраст и жанр ещё не проверены.'],
      };
      const output = { ...book };
      for (const key of fields) {
        if (Object.hasOwn(category, key)) output[key] = category[key];
        else delete output[key];
      }
      return output;
    });
  }
  root.BiblioCategoryOverlay = Object.freeze({ apply });
  if (Array.isArray(root.BIBLIO_BOOKS)) root.BIBLIO_BOOKS = apply(root.BIBLIO_BOOKS, root.BIBLIO_CATEGORIES || {});
  if (typeof module !== 'undefined' && module.exports) module.exports = { apply };
})(typeof window === 'undefined' ? globalThis : window);
