import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createHash } from 'node:crypto';
import { createRequire } from 'node:module';
import { createBrowser } from './dom-harness.mjs';
const require = createRequire(import.meta.url);
const logic = require('../assets/category-logic.js');
const overlay = require('../assets/category-overlay.js');
const read = name => fs.readFileSync(new URL('../' + name, import.meta.url), 'utf8');
const original = { id: 'b-test', requestId: '42', title: 'Ёжик', author: 'Маршак', isbn: '978-5-1234', annotation: 'Описание', publisher: 'Издатель', section: 'exchange', availability: 'available', orderBot: 'real_bot', orderStart: 'book_42', audience: 'adult', cover: '' };
const record = { identity: Object.fromEntries(['title', 'author', 'isbn', 'annotation'].map(key => [key, original[key]])), reader_age_groups: ['12–14 лет'], reader_age_status: 'editorial_recommendation', genres: ['Фэнтези'], genre_status: 'editorial_review', reader_age_basis: ['Основание'], edition_age_ratings: ['12+'], edition_rating_status: 'external_catalog' };
const state = { search: '', section: '', age: '', genre: '' };

test('category overlay retains all original ordering fields and rejects field overrides', () => {
  const merged = overlay.apply([original], { [original.id]: { ...record, orderStart: 'bad', requestId: 'bad', availability: 'bad' } })[0];
  for (const [key, value] of Object.entries(original)) assert.deepEqual(merged[key], value);
  assert.equal(merged.reader_age_status, 'editorial_recommendation');
});
test('new, changed or incomplete records are explicitly pending, independent of legacy audience', () => {
  for (const records of [{}, { [original.id]: { ...record, identity: { ...record.identity, isbn: 'different' } } }, { [original.id]: { ...record, genres: [] } }]) {
    const merged = overlay.apply([original], records)[0]; assert.equal(merged.reader_age_status, 'pending_review'); assert.equal(merged.genre_status, 'pending_review'); assert.ok(!merged.reader_age_groups.includes('Взрослые'));
  }
});
test('broad reader ranges overlap precise recommendations without mixing adults or rating 0+', () => {
  const book = overlay.apply([original], { [original.id]: record })[0];
  assert.ok(logic.matches(book, { ...state, age: '11–14 лет', genre: 'Фэнтези', section: 'exchange', search: 'ежик' }));
  assert.ok(!logic.matches(book, { ...state, age: 'Взрослые' }));
  assert.ok(logic.ageMatches({ reader_age_groups: ['16–17 лет'] }, '15–17 лет'));
  assert.ok(!logic.ageMatches({ reader_age_groups: ['4–6 лет'] }, '0–3 года'));
  assert.ok(!logic.ageMatches({ reader_age_groups: ['Возрастная рекомендация на проверке'], edition_age_ratings: ['0+'] }, '0–3 года'));
  assert.ok(logic.matches(book, { ...state, search: '97851234' }));
});
test('inline catalog handlers combine pending input with category filters and reset/Back', () => {
  const books = overlay.apply([original], { [original.id]: record }); const browser = createBrowser(books);
  browser.run(read('assets/category-logic.js')); browser.run(read('assets/local-categories.js'));
  const inline = [...read('index.html').matchAll(/<script>\s*([\s\S]*?)<\/script>/g)].at(-1)[1];
  browser.run(inline + '\nglobalThis.stateSnapshot = () => JSON.stringify(state);');
  browser.input('Маршак'); browser.filter('ageFilter', '11–14 лет'); browser.flush();
  assert.deepEqual(browser.renderedIds(), ['b-test']); assert.equal(browser.element('search').value, 'Маршак');
  browser.filter('genreFilter', 'Фэнтези'); assert.equal(new URLSearchParams(browser.location.search).get('genre'), 'Фэнтези');
  browser.input('не подходит'); browser.history.back(); browser.flush(); assert.equal(browser.element('search').value, 'Маршак');
  browser.input('new'); browser.element('resetCategories').dispatch('click'); browser.flush(); assert.equal(browser.element('search').value, '');
});
test('detail distinguishes editorial sources from edition marking and escapes source content', () => {
  const browser = createBrowser([]); browser.run(read('assets/category-logic.js')); browser.run(read('assets/local-categories.js'));
  const markup = browser.window.BiblioCategories.detailMarkup({ ...record, research_sources: ['https://example.org/series', 'javascript:bad'], genre_basis: '<img onerror=bad>' });
  assert.match(markup, /Рекомендация библиотеки/); assert.match(markup, /Редакционная категория/); assert.match(markup, /Маркировка издания/); assert.match(markup, /12\+/); assert.match(markup, /не подтверждают ISBN/); assert.doesNotMatch(markup, /<img|javascript:/);
});
test('live payload and overlay preserve every source book and have reviewed current IDs', () => {
  const browser = createBrowser([]); browser.run(read('data/books.js')); const base = browser.window.BIBLIO_BOOKS; browser.run(read('data/book-categories.js')); browser.run(read('assets/category-overlay.js'));
  const merged = browser.window.BIBLIO_BOOKS; assert.equal(merged.length, base.length); assert.equal(new Set(merged.map(b => b.id)).size, base.length);
  for (let i = 0; i < base.length; i++) { for (const [key, value] of Object.entries(base[i])) assert.equal(JSON.stringify(merged[i][key]), JSON.stringify(value), `${base[i].id}:${key}`); assert.notEqual(merged[i].reader_age_status, 'pending_review'); assert.notEqual(merged[i].genre_status, 'pending_review'); }
  assert.equal(merged.filter(book => logic.matches(book, { ...state, search: 'Вебб', age: '7–10 лет', genre: 'Детектив' })).length, 5);
});
test('original Telegram assets are byte-identical and remain connected in both page templates', () => {
  const expected = { 'assets/shelf.js': 'e8a3e3d75e9ce9841cb6ac257fbaeea5ce0cd7b55326f291e6e99cf586d54a5d', 'assets/telegram-links.js': '080d8af6b95d814e590b83848f6a1f0c3513bd1bd08276846aa895198094d472' };
  for (const [name, hash] of Object.entries(expected)) assert.equal(createHash('sha256').update(read(name)).digest('hex'), hash, name);
  for (const name of ['index.html', 'book.html']) { const html = read(name); assert.match(html, /telegram\.org\/js\/telegram-web-app\.js/); assert.match(html, /assets\/telegram-links\.js/); assert.match(html, /assets\/shelf\.js/); assert.doesNotMatch(html, /local-preview-note|data-local-action|Solicitudes desactivadas/); }
  assert.doesNotMatch(read('assets/categories.css'), /checkout|disabled|local-preview-note/);
});
