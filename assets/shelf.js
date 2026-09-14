/* Browser-local lists. Only an explicit checkout link opens the Telegram bot. */
(() => {
  "use strict";

  const books = Array.isArray(window.BIBLIO_BOOKS) ? window.BIBLIO_BOOKS : [];
  const byId = new Map(books.map((book) => [String(book.id), book]));
  const prefix = `vlc-biblio:shelf:v1:${new URL("./", location.href).pathname}:`;
  const limits = { orderBooks: 30, startLength: 64, savedBooks: 2000 };
  const lists = { cart: [], favorites: [] };
  let storageAvailable = true;
  let activeList = "cart";

  const escape = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[char]);
  const requestId = (book) => /^\d+$/.test(String(book?.requestId ?? "")) ? String(book.requestId) : "";
  const canAdd = (book) => book?.section === "exchange" && book.availability === "available" && !!requestId(book);
  const has = (list, id) => lists[list].includes(String(id));

  function readLists() {
    for (const list of Object.keys(lists)) {
      try {
        const saved = JSON.parse(localStorage.getItem(prefix + list) || "[]");
        lists[list] = Array.isArray(saved)
          ? [...new Set(saved.filter((id) => typeof id === "string" && id.length > 0 && id.length <= 128))].slice(0, limits.savedBooks)
          : [];
      } catch {
        // Keep the current session usable if browser storage is unavailable.
        storageAvailable = false;
      }
    }
  }
  readLists();

  function heartMarkup() {
    return '<svg class="shelf-heart" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"></path></svg>';
  }

  function buttonLabel(list, selected) {
    return list === "cart" ? (selected ? "В корзине ✓" : "В корзину")
      : (selected ? "Убрать из избранного" : "Добавить в избранное");
  }

  function buttonMarkup(list, book) {
    const id = String(book.id);
    const selected = has(list, id);
    const label = buttonLabel(list, selected);
    const favorite = list === "favorites";
    return `<button class="shelf-button${favorite ? " shelf-favorite" : ""}" type="button" data-shelf-toggle="${list}" data-shelf-id="${escape(id)}" aria-pressed="${selected}" aria-label="${escape(label + ': ' + (book.title || 'Без названия'))}" title="${escape(label)}">${favorite ? heartMarkup() : label}</button>`;
  }

  function favoriteMarkup(book) {
    return buttonMarkup("favorites", book);
  }

  function controlsMarkup(book, includeFavorite = true) {
    return `<div class="shelf-controls">${canAdd(book) || has("cart", book.id) ? buttonMarkup("cart", book) : ""}${includeFavorite ? favoriteMarkup(book) : ""}</div>`;
  }

  const toolbar = document.querySelector("[data-shelf-toolbar]");
  if (toolbar) {
    toolbar.innerHTML = `<nav class="shelf-nav" aria-label="Мои списки">
      <button class="shelf-button" type="button" data-shelf-open="cart">Корзина <span data-shelf-count="cart">0</span></button>
      <button class="shelf-button shelf-favorites-nav" type="button" data-shelf-open="favorites" title="Избранное">${heartMarkup()} Избранное <span data-shelf-count="favorites">0</span></button>
    </nav>`;
  }
  const dialog = document.createElement("dialog");
  dialog.className = "shelf-dialog";
  dialog.setAttribute("aria-labelledby", "shelf-title");
  dialog.innerHTML = `<div class="shelf-dialog-header"><h2 id="shelf-title"></h2>
    <button class="shelf-button" type="button" data-shelf-close autofocus>Закрыть</button></div>
    <div class="shelf-content"></div><p class="shelf-feedback" role="status"></p><p class="shelf-storage-note"></p>`;
  document.body.append(dialog);
  const status = document.createElement("p");
  status.className = "shelf-status";
  status.setAttribute("role", "status");
  document.body.append(status);
  let statusTimer;

  function announce(message) {
    if (dialog.open) dialog.querySelector(".shelf-feedback").textContent = message;
    status.textContent = message;
    status.classList.add("is-visible");
    clearTimeout(statusTimer);
    statusTimer = setTimeout(() => status.classList.remove("is-visible"), 4000);
  }

  function toggle(list, id) {
    if (!Object.hasOwn(lists, list)) return;
    if (storageAvailable) readLists();
    const selected = has(list, id);
    const book = byId.get(id);
    if (!selected && (!book || (list === "cart" && !canAdd(book)))) return;
    if (!selected && lists[list].length >= limits.savedBooks) {
      announce("Список заполнен. Удалите ненужные книги.");
      return;
    }
    lists[list] = selected ? lists[list].filter((savedId) => savedId !== id) : [...lists[list], id];
    try {
      localStorage.setItem(prefix + list, JSON.stringify(lists[list]));
    } catch {
      storageAvailable = false;
    }
    sync();
    const message = list === "cart" ? (selected ? "Книга удалена из корзины" : "Книга добавлена в корзину")
      : (selected ? "Книга удалена из избранного" : "Книга добавлена в избранное");
    announce(storageAvailable ? message : message + ". Браузер не разрешает сохранение: список доступен только на этой странице.");
  }

  function availabilityLabel(book) {
    if (!book) return "Книга больше не опубликована в каталоге";
    if (canAdd(book)) return "Доступна для запроса";
    if (book.section === "library") return "Библиотека Pilar Faus";
    if (book.availability === "reserved") return "Зарезервирована — можно встать в очередь";
    return "Сейчас недоступна для запроса";
  }

  function rowMarkup(id, number) {
    const book = byId.get(id);
    const title = book?.title || `Книга ${id}`;
    const cover = book?.coverImage?.src || book?.cover;
    const waitlist = book?.section === "exchange" && book.availability === "reserved" && requestId(book);
    return `<li class="shelf-row" data-shelf-row="${escape(id)}">
      <div class="shelf-cover">${cover ? `<img src="${escape(cover)}" alt="" loading="lazy" referrerpolicy="no-referrer" />` : "<span aria-hidden=\"true\">Книга</span>"}</div>
      <div class="shelf-row-body">
        ${book ? `<a class="shelf-book-title" href="./book.html?id=${encodeURIComponent(id)}">${number ? `${number}. ` : ""}${escape(title)}</a>` : `<span class="shelf-book-title">${escape(title)}</span>`}
        <p class="shelf-author">${escape(book?.author)}</p>
        <p class="shelf-availability">${availabilityLabel(book)}</p>
        ${waitlist ? `<a class="shelf-waitlist" href="https://t.me/VLS_Biblio_bot?start=wait_${requestId(book)}" target="_blank" rel="noreferrer">Встать в очередь в боте</a>` : ""}
        ${activeList === "favorites" && book ? controlsMarkup(book) : `<div class="shelf-controls"><button class="shelf-button" type="button" data-shelf-toggle="${activeList}" data-shelf-id="${escape(id)}">Удалить</button>${book ? buttonMarkup("favorites", book) : ""}</div>`}
      </div>
    </li>`;
  }

  function checkoutMarkup(ids) {
    // Both the existing bot's order limit and Telegram's start limit apply.
    const batches = [];
    let batch = [];
    for (const id of ids) {
      const candidate = [...batch, id];
      const payload = `books_${candidate.map((value) => requestId(byId.get(value))).join("_")}`;
      if (batch.length && (candidate.length > limits.orderBooks || payload.length > limits.startLength)) {
        batches.push(batch);
        batch = [];
      }
      batch.push(id);
    }
    if (batch.length) batches.push(batch);
    let offset = 0;
    return batches.map((items, index) => {
      const payload = `books_${items.map((id) => requestId(byId.get(id))).join("_")}`;
      const range = `${offset + 1}–${offset + items.length}`;
      offset += items.length;
      if (payload.length > limits.startLength) return '<p class="shelf-note">Не удалось подготовить ссылку для этой книги.</p>';
      return `<div class="shelf-checkout">${batches.length > 1 ? `<p class="shelf-note">Заказ ${index + 1}: книги ${range}</p>` : ""}
        <a class="shelf-button shelf-primary" data-shelf-checkout href="https://t.me/VLS_Biblio_bot?start=${payload}" target="_blank" rel="noreferrer">Проверить в боте (${items.length}) →</a></div>`;
    }).join("");
  }

  function renderList() {
    dialog.querySelector("#shelf-title").textContent = `${activeList === "cart" ? "Корзина" : "Избранное"} · ${lists[activeList].length}`;
    let markup;
    if (!lists[activeList].length) {
      markup = `<p class="shelf-empty">${activeList === "cart" ? "Корзина пока пуста. Добавляйте книги из каталога, а затем проверьте список перед отправкой в бот." : "Здесь будут книги, которые вы хотите сохранить на потом. Нажмите на сердечко на карточке книги."}</p>`;
    } else if (activeList === "favorites") {
      markup = `<p class="shelf-note">Сохранённые книги на потом. Доступные книги можно добавить в корзину.</p><ul class="shelf-list">${lists.favorites.map((id) => rowMarkup(id)).join("")}</ul>`;
    } else {
      const groups = new Map();
      const unavailable = [];
      for (const id of lists.cart) {
        const book = byId.get(id);
        if (!canAdd(book)) { unavailable.push(id); continue; }
        // Unknown owners must never be combined based on a shared empty key.
        const key = book.libraryKey || `book:${id}`;
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key).push(id);
      }
      markup = '<p class="shelf-note">Проверьте список и удалите лишнее. Книги разных владельцев оформляются отдельно. Добавление в корзину не резервирует книгу; бот проверит доступность и попросит подтвердить отправку.</p>';
      markup += Array.from(groups.values()).map((ids, index) => `<section class="shelf-group" aria-label="Библиотека ${index + 1}"><h3>Библиотека ${index + 1} · ${ids.length}</h3>
        <ul class="shelf-list">${ids.map((id, number) => rowMarkup(id, number + 1)).join("")}</ul>${checkoutMarkup(ids)}</section>`).join("");
      if (unavailable.length) markup += `<section class="shelf-group"><h3>Сейчас недоступны · ${unavailable.length}</h3><p class="shelf-note">Эти книги не включены в запрос. Можно оставить их в избранном или удалить из корзины.</p><ul class="shelf-list">${unavailable.map((id) => rowMarkup(id)).join("")}</ul></section>`;
      if (groups.size) markup += '<p class="shelf-note">После перехода в бот корзина сохраняется. Удалите книги из неё, когда подтвердите заказ.</p>';
    }
    const focused = document.activeElement;
    const focusId = focused?.dataset.shelfId;
    const focusList = focused?.dataset.shelfToggle;
    const scrollTop = dialog.scrollTop;
    dialog.querySelector(".shelf-content").innerHTML = markup;
    dialog.querySelector(".shelf-storage-note").textContent = storageAvailable
      ? "Списки хранятся в этом браузере. На другом устройстве или в другом браузере они будут отдельными."
      : "Браузер не разрешает сохранение. Списки доступны только на этой странице.";
    if (focusId) {
      const replacement = Array.from(dialog.querySelectorAll("[data-shelf-toggle]")).find((button) => button.dataset.shelfId === focusId && button.dataset.shelfToggle === focusList);
      (replacement || dialog.querySelector("[data-shelf-close]")).focus({ preventScroll: true });
    }
    dialog.scrollTop = scrollTop;
  }

  function sync() {
    document.querySelectorAll("[data-shelf-count]").forEach((counter) => {
      counter.textContent = lists[counter.dataset.shelfCount].length;
    });
    document.querySelectorAll("[data-shelf-toggle]").forEach((button) => {
      if (dialog.contains(button)) return;
      const book = byId.get(button.dataset.shelfId);
      if (!book) return;
      const list = button.dataset.shelfToggle;
      const selected = has(list, book.id);
      const label = buttonLabel(list, selected);
      if (list === "cart") button.textContent = label;
      button.setAttribute("aria-pressed", String(selected));
      button.setAttribute("aria-label", label + ": " + (book.title || "Без названия"));
      button.setAttribute("title", label);
    });
    if (dialog.open) renderList();
  }

  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-shelf-toggle], [data-shelf-open], [data-shelf-close]");
    if (!button) return;
    if (button.hasAttribute("data-shelf-close")) dialog.close();
    else if (button.dataset.shelfOpen) {
      if (storageAvailable) readLists();
      activeList = button.dataset.shelfOpen;
      dialog.querySelector(".shelf-feedback").textContent = "";
      renderList();
      dialog.showModal();
      dialog.scrollTop = 0;
    } else toggle(button.dataset.shelfToggle, button.dataset.shelfId);
  });
  dialog.addEventListener("error", (event) => {
    if (event.target.tagName === "IMG") event.target.replaceWith(document.createTextNode("Книга"));
  }, true);
  window.addEventListener("storage", (event) => {
    if (event.key === null || event.key?.startsWith(prefix)) { readLists(); sync(); }
  });
  window.addEventListener("pageshow", () => { if (storageAvailable) readLists(); sync(); });
  window.BiblioShelf = Object.freeze({ controlsMarkup, favoriteMarkup });
  sync();
})();
