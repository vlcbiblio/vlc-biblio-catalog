/* Shared local category rules. The existing catalog's sections remain intact. */
((root) => {
  'use strict';
  const normalize = value => String(value ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('ru').replaceAll('ё', 'е').replace(/\s+/g, ' ').trim();
  const list = (book, key) => Array.isArray(book[key]) ? book[key] : [];
  const options = (books, key) => [...new Set(books.flatMap(book => list(book, key)))].sort((a, b) => a.localeCompare(b, 'ru', { numeric: true }));
  const AGE_GROUPS = ['0–3 года', '4–6 лет', '7–10 лет', '11–14 лет', '15–17 лет', 'Взрослые'];
  function readerAgeRange(value) {
    // These are reader recommendations, never the separate edition-rating field.
    const match = /^(\d{1,2})(?:\s*[–—-]\s*(\d{1,2}))?\s*(?:лет|года|год)$/.exec(normalize(value));
    if (!match) return null;
    const low = Number(match[1]); const high = Number(match[2] || match[1]);
    return low <= high && high <= 17 ? [low, high] : null;
  }
  function ageMatches(book, selected) {
    if (!selected) return true;
    const groups = list(book, 'reader_age_groups');
    if (normalize(selected) === 'взрослые') return groups.some(value => normalize(value) === 'взрослые');
    const wanted = readerAgeRange(selected);
    if (!wanted) return groups.includes(selected);
    return groups.some(value => {
      const actual = readerAgeRange(value);
      return actual && wanted[0] <= actual[1] && actual[0] <= wanted[1];
    });
  }
  function ageOptions(books) {
    const known = AGE_GROUPS.filter(group => books.some(book => ageMatches(book, group)));
    const unspecified = options(books, 'reader_age_groups').filter(group => !readerAgeRange(group) && normalize(group) !== 'взрослые');
    return [...known, ...unspecified];
  }
  function matches(book, state) {
    const query = normalize(state.search);
    const text = normalize([book.title, book.author, book.isbn, book.publisher, book.annotation, book.searchAliases].join(' '));
    const isbn = normalize(book.isbn).replace(/[\s-]/g, '');
    const compactQuery = query.replace(/[\s-]/g, '');
    return (!query || text.includes(query) || (compactQuery.length >= 4 && isbn.includes(compactQuery)))
      && (!state.section || book.section === state.section)
      && ageMatches(book, state.age)
      && (!state.genre || list(book, 'genres').includes(state.genre));
  }
  function readCatalogState(search, saved, books) {
    const params = new URLSearchParams(search);
    const explicit = ['q', 'section', 'age', 'genre'].some(key => params.has(key));
    const value = key => explicit ? (params.get(key === 'search' ? 'q' : key) || '') : (saved?.[key] || '');
    const state = { search: String(value('search')).slice(0, 200), section: '', age: '', genre: '' };
    if (['library', 'exchange'].includes(value('section'))) state.section = value('section');
    if ([...ageOptions(books), ...options(books, 'reader_age_groups')].includes(value('age'))) state.age = value('age');
    if (options(books, 'genres').includes(value('genre'))) state.genre = value('genre');
    return state;
  }
  function catalogUrl(state, current = root.location?.href || 'http://localhost/') {
    const url = new URL(current);
    for (const key of ['q', 'section', 'age', 'genre', 'book']) url.searchParams.delete(key);
    for (const [key, value] of [['q', state.search], ['section', state.section], ['age', state.age], ['genre', state.genre]]) if (value) url.searchParams.set(key, value);
    return url.pathname + url.search + url.hash;
  }
  function safeUrl(value) {
    try {
      const url = new URL(value);
      if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || ['t.me', 'telegram.me', 'telegram.org'].includes(url.hostname)) return null;
      return url.href;
    } catch { return null; }
  }
  const api = Object.freeze({ normalize, list, options, readerAgeRange, ageMatches, ageOptions, matches, readCatalogState, catalogUrl, safeUrl });
  root.BiblioCategoryLogic = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window === 'undefined' ? globalThis : window);
