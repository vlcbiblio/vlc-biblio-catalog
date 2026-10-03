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
  const t = (key, fallback) => window.BiblioI18n?.t(`shelf.${key}`, fallback) ?? fallback;
  const bookText = (key, fallback) => window.BiblioI18n?.t(`book.${key}`, fallback) ?? fallback;

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
    return list === "cart" ? (selected ? t("inCart", "En la cesta ✓") : t("addCart", "Añadir a la cesta"))
      : (selected ? t("removeFavorite", "Quitar de favoritos") : t("addFavorite", "Añadir a favoritos"));
  }

  function buttonMarkup(list, book) {
    const id = String(book.id);
    const selected = has(list, id);
    const label = buttonLabel(list, selected);
    const favorite = list === "favorites";
    return `<button class="shelf-button${favorite ? " shelf-favorite" : ""}" type="button" data-shelf-toggle="${list}" data-shelf-id="${escape(id)}" aria-pressed="${selected}" aria-label="${escape(label + ': ' + (book.title || bookText('untitled', 'Sin título')))}" title="${escape(label)}">${favorite ? heartMarkup() : label}</button>`;
  }

  function favoriteMarkup(book) {
    return buttonMarkup("favorites", book);
  }

  function controlsMarkup(book, includeFavorite = true) {
    return `<div class="shelf-controls">${canAdd(book) || has("cart", book.id) ? buttonMarkup("cart", book) : ""}${includeFavorite ? favoriteMarkup(book) : ""}</div>`;
  }

  const toolbar = document.querySelector("[data-shelf-toolbar]");
  let floatingCart;
  let toolbarCartVisible = true;
  if (toolbar) {
    toolbar.innerHTML = `<nav class="shelf-nav" aria-label="${escape(t("lists", "Mis listas"))}">
      <button class="shelf-button" type="button" data-shelf-open="cart">${escape(t("cart", "Cesta"))} <span data-shelf-count="cart">0</span></button>
      <button class="shelf-button shelf-favorites-nav" type="button" data-shelf-open="favorites" title="${escape(t("favorites", "Favoritos"))}">${heartMarkup()} ${escape(t("favorites", "Favoritos"))} <span data-shelf-count="favorites">0</span></button>
    </nav>`;
    floatingCart = document.createElement("button");
    floatingCart.className = "shelf-floating-cart";
    floatingCart.type = "button";
    floatingCart.dataset.shelfFloatingOpen = "cart";
    floatingCart.setAttribute("aria-label", t("openCart", "Abrir la cesta"));
    floatingCart.setAttribute("aria-hidden", "true");
    floatingCart.tabIndex = -1;
    floatingCart.innerHTML = `<svg class="shelf-floating-cart-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><circle cx="9" cy="20" r="1"></circle><circle cx="19" cy="20" r="1"></circle><path d="M3 4h2l2.4 10.4a2 2 0 0 0 2 1.6h7.7a2 2 0 0 0 2-1.6L21 7H6"></path></svg><span>${escape(t("cart", "Cesta"))}</span><span data-shelf-floating-count>0</span>`;
    document.body.append(floatingCart);
  }
  const dialog = document.createElement("dialog");
  dialog.className = "shelf-dialog";
  dialog.setAttribute("aria-labelledby", "shelf-title");
  dialog.innerHTML = `<div class="shelf-dialog-header"><h2 id="shelf-title"></h2>
    <button class="shelf-button" type="button" data-shelf-close autofocus>${escape(t("close", "Cerrar"))}</button></div>
    <div class="shelf-content"></div><p class="shelf-feedback" role="status"></p><p class="shelf-storage-note"></p>`;
  document.body.append(dialog);
  const status = document.createElement("p");
  status.className = "shelf-status";
  status.setAttribute("role", "status");
  document.body.append(status);
  let statusTimer;

  function syncFloatingCart() {
    if (!floatingCart) return;
    const visible = lists.cart.length > 0 && !toolbarCartVisible && !dialog.open;
    floatingCart.querySelector("[data-shelf-floating-count]").textContent = lists.cart.length;
    floatingCart.classList.toggle("is-visible", visible);
    floatingCart.setAttribute("aria-hidden", String(!visible));
    floatingCart.tabIndex = visible ? 0 : -1;
    document.documentElement.classList.toggle("has-floating-cart", visible);
  }

  if (floatingCart) {
    const toolbarCart = toolbar.querySelector('[data-shelf-open="cart"]');
    if ("IntersectionObserver" in window) {
      new IntersectionObserver(([entry]) => {
        toolbarCartVisible = entry.isIntersecting;
        syncFloatingCart();
      }).observe(toolbarCart);
    } else {
      const checkToolbarCart = () => {
        const rect = toolbarCart.getBoundingClientRect();
        toolbarCartVisible = rect.bottom > 0 && rect.top < window.innerHeight;
        syncFloatingCart();
      };
      window.addEventListener("scroll", checkToolbarCart, { passive: true });
      window.addEventListener("resize", checkToolbarCart);
      checkToolbarCart();
    }
  }

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
      announce(t("full", "La lista está llena. Elimina los libros que no necesites."));
      return;
    }
    lists[list] = selected ? lists[list].filter((savedId) => savedId !== id) : [...lists[list], id];
    try {
      localStorage.setItem(prefix + list, JSON.stringify(lists[list]));
    } catch {
      storageAvailable = false;
    }
    sync();
    const message = list === "cart" ? (selected ? t("removedCart", "Libro eliminado de la cesta") : t("addedCart", "Libro añadido a la cesta"))
      : (selected ? t("removedFavorite", "Libro eliminado de favoritos") : t("addedFavorite", "Libro añadido a favoritos"));
    announce(storageAvailable ? message : message + t("storageBlockedSuffix", ". El navegador no permite guardar datos: la lista solo está disponible en esta página."));
  }

  function availabilityLabel(book) {
    if (!book) return t("unpublished", "El libro ya no está publicado en el catálogo");
    if (canAdd(book)) return t("available", "Disponible para solicitar");
    if (book.section === "library") return bookText("library", "Biblioteca Pilar Faus");
    if (book.availability === "reserved") return t("reserved", "Reservado: puedes apuntarte a la lista de espera");
    return t("unavailable", "No disponible para solicitar por el momento");
  }

  function rowMarkup(id, number) {
    const book = byId.get(id);
    const title = book?.title || `${bookText("fallback", "Libro")} ${id}`;
    const cover = book?.coverImage?.src || book?.cover;
    const waitlist = book?.section === "exchange" && book.availability === "reserved" && requestId(book);
    return `<li class="shelf-row" data-shelf-row="${escape(id)}">
      <div class="shelf-cover">${cover ? `<img src="${escape(cover)}" alt="" loading="lazy" referrerpolicy="no-referrer" />` : `<span aria-hidden="true">${escape(bookText("fallback", "Libro"))}</span>`}</div>
      <div class="shelf-row-body">
        ${book ? `<a class="shelf-book-title" href="./book.html?id=${encodeURIComponent(id)}">${number ? `${number}. ` : ""}${escape(title)}</a>` : `<span class="shelf-book-title">${escape(title)}</span>`}
        <p class="shelf-author">${escape(book?.author)}</p>
        <p class="shelf-availability">${availabilityLabel(book)}</p>
        ${waitlist ? `<a class="shelf-waitlist" href="https://t.me/VLS_Biblio_bot?start=wait_${requestId(book)}" target="_blank" rel="noreferrer">${escape(t("waitlistBot", "Apuntarme a la lista de espera en el bot"))}</a>` : ""}
        ${activeList === "favorites" && book ? controlsMarkup(book) : `<div class="shelf-controls"><button class="shelf-button" type="button" data-shelf-toggle="${activeList}" data-shelf-id="${escape(id)}">${escape(t("remove", "Eliminar"))}</button>${book ? buttonMarkup("favorites", book) : ""}</div>`}
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
      if (payload.length > limits.startLength) return `<p class="shelf-note">${escape(t("linkError", "No se ha podido preparar el enlace para este libro."))}</p>`;
      return `<div class="shelf-checkout">${batches.length > 1 ? `<p class="shelf-note">${escape(t("order", "Pedido"))} ${index + 1}: ${escape(t("booksRange", "libros"))} ${range}</p>` : ""}
        <a class="shelf-button shelf-primary" data-shelf-checkout href="https://t.me/VLS_Biblio_bot?start=${payload}" target="_blank" rel="noreferrer"><span>${items.length === 1 ? escape(bookText("request", "Solicitar el libro")) : `${escape(t("requestSelected", "Solicitar los seleccionados"))}: ${items.length}`}</span><span>${escape(bookText("telegram", "por Telegram"))}</span></a></div>`;
    }).join("");
  }

  function locationMarkup(ids) {
    const notes = [...new Set(ids.map((id) => byId.get(id)?.locationNote).filter(Boolean))];
    if (!notes.length) return "";
    return `<aside class="shelf-location" aria-label="${escape(t("location", "Lugar de entrega de los libros"))}">
      ${notes.map((note) => `<p>${escape(note)}</p>`).join("")}
    </aside>`;
  }

  function renderList() {
    dialog.querySelector("#shelf-title").textContent = `${activeList === "cart" ? t("cart", "Cesta") : t("favorites", "Favoritos")} · ${lists[activeList].length}`;
    let markup;
    if (!lists[activeList].length) {
      markup = `<p class="shelf-empty">${escape(activeList === "cart" ? t("cartEmpty", "La cesta está vacía. Añade libros del catálogo y revisa la lista antes de enviarla al bot.") : t("favoritesEmpty", "Aquí aparecerán los libros que quieras guardar para más adelante. Pulsa el corazón de la ficha del libro."))}</p>`;
    } else if (activeList === "favorites") {
      markup = `<p class="shelf-note">${escape(t("favoritesNote", "Libros guardados para más adelante. Puedes añadir los que estén disponibles a la cesta."))}</p><ul class="shelf-list">${lists.favorites.map((id) => rowMarkup(id)).join("")}</ul>`;
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
      markup = `<p class="shelf-note">${escape(t("cartNote", "Revisa la lista y elimina lo que no necesites. Los libros de distintas personas propietarias se tramitan por separado. Añadir un libro a la cesta no lo reserva; el bot comprobará su disponibilidad y te pedirá que confirmes el envío."))}</p>`;
      markup += Array.from(groups.values()).map((ids, index) => `<section class="shelf-group" aria-label="${escape(t("library", "Biblioteca"))} ${index + 1}"><h3>${escape(t("library", "Biblioteca"))} ${index + 1} · ${ids.length}</h3>
        <ul class="shelf-list">${ids.map((id, number) => rowMarkup(id, number + 1)).join("")}</ul>${locationMarkup(ids)}${checkoutMarkup(ids)}</section>`).join("");
      if (unavailable.length) markup += `<section class="shelf-group"><h3>${escape(t("unavailableHeading", "No disponibles por el momento"))} · ${unavailable.length}</h3><p class="shelf-note">${escape(t("unavailableNote", "Estos libros no se incluyen en la solicitud. Puedes guardarlos en favoritos o eliminarlos de la cesta."))}</p><ul class="shelf-list">${unavailable.map((id) => rowMarkup(id)).join("")}</ul></section>`;
      if (groups.size) markup += `<p class="shelf-note">${escape(t("afterBot", "La cesta se conserva después de abrir el bot. Elimina los libros cuando hayas confirmado el pedido."))}</p>`;
    }
    const focused = document.activeElement;
    const focusId = focused?.dataset.shelfId;
    const focusList = focused?.dataset.shelfToggle;
    const scrollTop = dialog.scrollTop;
    dialog.querySelector(".shelf-content").innerHTML = markup;
    dialog.querySelector(".shelf-storage-note").textContent = storageAvailable
      ? t("storageOk", "Las listas se guardan en este navegador. Serán distintas en otro dispositivo o navegador.")
      : t("storageBlocked", "El navegador no permite guardar datos. Las listas solo están disponibles en esta página.");
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
      button.setAttribute("aria-label", label + ": " + (book.title || bookText("untitled", "Sin título")));
      button.setAttribute("title", label);
    });
    syncFloatingCart();
    if (dialog.open) renderList();
  }

  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-shelf-toggle], [data-shelf-open], [data-shelf-floating-open], [data-shelf-close]");
    if (!button) return;
    if (button.hasAttribute("data-shelf-close")) dialog.close();
    else if (button.dataset.shelfOpen || button.dataset.shelfFloatingOpen) {
      if (storageAvailable) readLists();
      activeList = button.dataset.shelfOpen || button.dataset.shelfFloatingOpen;
      dialog.querySelector(".shelf-feedback").textContent = "";
      renderList();
      dialog.showModal();
      dialog.scrollTop = 0;
      syncFloatingCart();
    } else toggle(button.dataset.shelfToggle, button.dataset.shelfId);
  });
  dialog.addEventListener("close", syncFloatingCart);
  dialog.addEventListener("error", (event) => {
    if (event.target.tagName === "IMG") event.target.replaceWith(document.createTextNode(bookText("fallback", "Libro")));
  }, true);
  window.addEventListener("storage", (event) => {
    if (event.key === null || event.key?.startsWith(prefix)) { readLists(); sync(); }
  });
  window.addEventListener("pageshow", () => { if (storageAvailable) readLists(); sync(); });
  window.BiblioShelf = Object.freeze({ controlsMarkup, favoriteMarkup });
  sync();
})();
