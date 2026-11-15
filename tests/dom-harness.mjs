import vm from 'node:vm';

export function createBrowser(books, locale = 'ru') {
  const elements = new Map(); const timers = new Map(); const events = new Map();
  const local = new Map(); const session = new Map(); let timerId = 0; let document;
  const camel = value => value.replace(/-([a-z])/g, (_, c) => c.toUpperCase());
  function match(el, selector) {
    if (selector.startsWith('#')) return el.id === selector.slice(1);
    if (selector.startsWith('.')) return (el.className || '').split(/\s+/).includes(selector.slice(1));
    const attr = /^\[([^=\]]+)(?:="([^\"]*)")?\]$/.exec(selector);
    if (attr) return el.hasAttribute(attr[1]) && (attr[2] === undefined || el.getAttribute(attr[1]) === attr[2]);
    return el.tagName.toLowerCase() === selector.toLowerCase();
  }
  class Element {
    constructor(tag = 'div') {
      this.tagName = tag.toUpperCase(); this.children = []; this.dataset = {}; this.attributes = {}; this.listeners = new Map(); this.style = {};
      this.value = ''; this.open = false; this.hidden = false; this.scrollTop = 0; this._html = ''; this._text = '';
      this.classList = { contains: name => (this.className || '').split(/\s+/).includes(name),
        toggle: (name, force) => { const set = new Set((this.className || '').split(/\s+/).filter(Boolean)); if (force ?? !set.has(name)) set.add(name); else set.delete(name); this.className = [...set].join(' '); },
        add: name => this.classList.toggle(name, true), remove: name => this.classList.toggle(name, false) };
    }
    set innerHTML(value) {
      this._html = value; this.children = [];
      for (const [, tag, raw] of String(value).matchAll(/<([a-z][a-z0-9-]*)\b([^>]*)>/gi)) {
        const child = new Element(tag);
        for (const [, key, val] of raw.matchAll(/([\w-]+)(?:="([^\"]*)")?/g)) child.setAttribute(key, val ?? '');
        child.parentElement = this; this.children.push(child);
      }
    }
    get innerHTML() { return this._html; }
    set textContent(value) { this._text = String(value); this.children = []; }
    get textContent() { return this._text; }
    setAttribute(key, value) { this.attributes[key] = String(value); if (key === 'id') this.id = value; if (key === 'class') this.className = value; if (key.startsWith('data-')) this.dataset[camel(key.slice(5))] = String(value); }
    getAttribute(key) { return this.attributes[key] ?? null; }
    hasAttribute(key) { return Object.hasOwn(this.attributes, key); }
    append(...children) { for (const child of children) { child.parentElement = this; this.children.push(child); } }
    replaceChildren(...children) { this.children = []; this.append(...children); }
    addEventListener(type, callback) { if (!this.listeners.has(type)) this.listeners.set(type, []); this.listeners.get(type).push(callback); }
    dispatch(type, extra = {}) { for (const callback of this.listeners.get(type) || []) callback({ target: this, preventDefault() {}, ...extra }); }
    querySelectorAll(selector) { const choices = selector.split(',').map(x => x.trim()); return this.children.flatMap(child => [...(choices.some(s => match(child, s)) ? [child] : []), ...child.querySelectorAll(selector)]); }
    querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
    closest(selector) { if (selector.split(',').some(s => match(this, s.trim()))) return this; return this.parentElement?.closest(selector) || null; }
    contains(el) { return el === this || this.children.some(child => child.contains(el)); }
    focus() { document.activeElement = this; }
    getBoundingClientRect() { return { top: 100, bottom: this.id === 'controls' ? 120 : 300, left: 0, right: 400 }; }
    showModal() { this.open = true; }
    close() { this.open = false; this.dispatch('close'); }
    scrollIntoView() {}
  }
  const element = id => { if (!elements.has(id)) { const el = new Element(id === 'grid' ? 'section' : 'div'); el.id = id; elements.set(id, el); } return elements.get(id); };
  element('controls').className = 'controls'; element('toolbar').setAttribute('data-shelf-toolbar', '');
  const body = new Element('body'); const documentEvents = new Element();
  document = { baseURI: 'http://127.0.0.1:8766/', body, head: new Element('head'), documentElement: new Element('html'), activeElement: null, visibilityState: 'visible', getElementById: element,
    querySelector(selector) { if (selector.startsWith('#')) return element(selector.slice(1)); if (selector === '.controls') return element('controls'); if (selector === '[data-shelf-toolbar]') return element('toolbar'); return body.querySelector(selector); },
    querySelectorAll(selector) { return [...new Set([...elements.values(), body].flatMap(el => [...(selector.split(',').some(s => match(el, s.trim())) ? [el] : []), ...el.querySelectorAll(selector)]))]; },
    createElement: tag => new Element(tag), createTextNode(text) { const el = new Element('span'); el.textContent = text; return el; }, addEventListener: (...args) => documentEvents.addEventListener(...args) };
  const location = { href: 'http://127.0.0.1:8766/', pathname: '/', search: '', hash: '', replace(url) { this.href = url; } };
  const entries = [{ url: '/', state: null }]; let index = 0;
  function assign(url) { const u = new URL(url, 'http://127.0.0.1:8766'); Object.assign(location, { href: u.href, pathname: u.pathname, search: u.search, hash: u.hash }); }
  const history = { state: null,
    pushState(state, _, url) { entries.splice(index + 1); entries.push({ state, url: url || location.href }); index++; this.state = state; if (url) assign(url); },
    replaceState(state, _, url) { entries[index] = { state, url: url || location.href }; this.state = state; if (url) assign(url); },
    back() { if (!index) return; index--; this.state = entries[index].state; assign(entries[index].url); for (const callback of events.get('popstate') || []) callback(); } };
  const storage = store => ({ getItem: key => store.get(key) || null, setItem: (key, value) => store.set(key, value) });
  const window = { BIBLIO_BOOKS: books, location, history, innerHeight: 900, scrollY: 0, BiblioI18n: { locale, t: (_, fallback) => fallback }, BiblioShelf: { favoriteMarkup: () => '', controlsMarkup: () => '' },
    addEventListener(type, callback) { if (!events.has(type)) events.set(type, []); events.get(type).push(callback); }, scrollTo() {} };
  const context = vm.createContext({ window, document, location, history, URL, URLSearchParams, console, performance: { getEntriesByType: () => [] }, localStorage: storage(local), sessionStorage: storage(session),
    setTimeout(callback) { const id = ++timerId; timers.set(id, callback); return id; }, clearTimeout(id) { timers.delete(id); } });
  return { context, window, element, document, location, history, session, local, run(code) { return vm.runInContext(code, context); },
    input(value) { element('search').value = value; element('search').dispatch('input'); }, filter(id, value) { element(id).value = value; element(id).dispatch('change'); },
    clickDocument(target) { documentEvents.dispatch('click', { target }); }, flush() { for (const [id, callback] of [...timers]) if (timers.delete(id)) callback(); },
    renderedIds: () => element('grid').children.filter(x => x.dataset.bookId).map(x => x.dataset.bookId) };
}
