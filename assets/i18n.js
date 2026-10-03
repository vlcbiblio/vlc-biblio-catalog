/* Lightweight UI localization. Book data is intentionally left untouched. */
(() => {
  "use strict";

  const storageKey = "vlc-biblio:language";
  const supported = new Set(["es", "ru"]);
  let locale = "ru";
  try {
    const saved = localStorage.getItem(storageKey);
    if (supported.has(saved)) locale = saved;
  } catch {
    // Russian remains the default when browser storage is unavailable.
  }

  const ru = {
    "language.switch": "Переключить язык на испанский",
    "catalog.subtitle": "Пополняемый каталог книг для фонда библиотеки Pilar Faus и частных библиотек участников.",
    "catalog.menu.open": "Открыть меню",
    "catalog.nav.main": "Основная навигация",
    "catalog.nav.catalog": "Каталог",
    "catalog.nav.donate": "Подарить книгу",
    "catalog.nav.how": "Как это работает",
    "catalog.nav.business": "Для бизнеса",
    "catalog.nav.privacy": "Конфиденциальность",
    "catalog.nav.about": "О проекте",
    "catalog.telegram.add": "Добавить свою книгу",
    "catalog.telegram.news": "Новости проекта",
    "catalog.telegram.chat": "Обсуждения",
    "catalog.external": "Открыть во внешнем браузере",
    "catalog.stats.label": "Статистика каталога",
    "catalog.stats.total": "всего",
    "catalog.stats.library": "в библиотеке Pilar Faus",
    "catalog.stats.private": "частные",
    "catalog.how.title": "Как это работает",
    "catalog.how.1": "Посмотрите, какие книги уже есть в каталоге",
    "catalog.how.2": "Подарите книгу библиотеке Pilar Faus",
    "catalog.how.3": "Добавьте свою книгу и давайте её читать другим",
    "catalog.how.4": "Всё управление книгами происходит через Telegram-бота",
    "catalog.add.label": "Добавить книгу",
    "catalog.donate.title": "Подарить книгу библиотеке",
    "catalog.donate.text": "Книга будет передана в государственную библиотеку Pilar Faus и станет доступна читателям.",
    "catalog.donate.link": "Подарить книгу →",
    "catalog.private.title": "Добавить в частную библиотеку",
    "catalog.private.text": "Книга остаётся у вас, но другие участники смогут найти её в каталоге и попросить почитать.",
    "catalog.private.link": "Добавить свою книгу →",
    "catalog.latest": "Последние добавленные книги",
    "catalog.title": "Каталог",
    "catalog.filters": "Фильтры",
    "catalog.search": "Поиск по названию, автору, ISBN или издательству",
    "catalog.sections.all": "Все разделы",
    "catalog.sections.library": "Библиотека Pilar Faus",
    "catalog.sections.private": "Частная библиотека",
    "catalog.books": "Книги",
    "catalog.empty": "Ничего не найдено. Попробуйте убрать часть фильтров.",
    "catalog.about.title": "Зачем мы это делаем?",
    "catalog.about.text": "Читать — важно. Мы хотим сделать книги доступнее для жителей Валенсии: пополняем фонд государственной библиотеки Pilar Faus и одновременно создаём сеть небольших частных библиотек.",
    "catalog.business.title": "Для бизнеса",
    "catalog.business.heading": "Станьте точкой передачи книг",
    "catalog.business.lead": "Кафе, магазин, студия или другое пространство может помочь проекту, став удобной точкой передачи книг. Достаточно выделить небольшое место — полку, ящик или часть стеллажа, — где участники смогут оставлять и забирать подготовленные пачки книг в часы работы.",
    "catalog.business.text": "Каждая пачка будет подписана номером заказа: сотрудникам не нужно вести учёт книг или организовывать их передачу.",
    "catalog.business.needs": "Что потребуется от партнёра:",
    "catalog.business.1": "небольшое место для нескольких пачек книг;",
    "catalog.business.2": "возможность зайти и оставить или забрать книги в часы работы;",
    "catalog.business.3": "никаких дополнительных процессов для сотрудников.",
    "catalog.business.link": "Стать партнёром →",
    "catalog.faq.q1": "Какие книги можно передавать?",
    "catalog.faq.a1": "Предлагайте книги в хорошем состоянии. Отправьте информацию или фотографии книги через Telegram-бота — команда проверит заявку и подскажет дальнейшие шаги.",
    "catalog.faq.q2": "Куда приносить книги?",
    "catalog.faq.a2": "После согласования бот сообщит актуальный способ и точку передачи. Не приносите книгу в Pilar Faus без подтверждения проекта.",
    "catalog.faq.q3": "Как взять книгу у частного владельца?",
    "catalog.faq.a3": "Откройте карточку доступной книги, добавьте её в корзину и отправьте запрос через Telegram. Бот поможет согласовать передачу с владельцем.",
    "catalog.faq.q4": "Нужно ли отдавать свою книгу навсегда?",
    "catalog.faq.a4": "Нет. При добавлении выберите частную библиотеку: книга останется у вас, а участники смогут просить её на время.",
    "catalog.faq.q5": "На каких языках книги?",
    "catalog.faq.a5": "В каталоге могут быть книги на разных языках. Найдите нужный язык по названию, автору или описанию через строку поиска.",
    "catalog.faq.q6": "Как книга попадёт в Pilar Faus?",
    "catalog.faq.a6": "Вы отправляете заявку через бота, команда проверяет книгу и организует передачу. Статус в каталоге покажет, на каком этапе она находится.",
    "catalog.back": "← Назад к каталогу",
    "book.year": "Год выпуска",
    "book.publisher": "Издательство",
    "book.updated": "Обновлено",
    "book.fallback": "Книга",
    "book.cover": "Обложка",
    "book.waitlist": "Встать в очередь",
    "book.request": "Запросить книгу",
    "book.telegram": "через Телеграм",
    "book.library": "Библиотека Pilar Faus",
    "book.private": "Частная библиотека",
    "book.note.reserved": "Книга зарезервирована. Встаньте в очередь, чтобы получить уведомление, когда подойдёт ваша очередь.",
    "book.note.unavailable": "Книга пока недоступна для запроса.",
    "book.note.private": "Книга в частной коллекции. Вы можете запросить книгу на время.",
    "book.note.planned": "Книга собирается для передачи в библиотеку Pilar Faus.",
    "book.note.transferred": "Книга передана в библиотеку Pilar Faus.",
    "book.note.accepted": "Книга принята в фонд библиотеки Pilar Faus.",
    "book.note.library": "Книга относится к библиотеке Pilar Faus.",
    "book.status.private": "🏠 Частная библиотека",
    "book.status.planned": "🎁 Собирается для Pilar Faus",
    "book.status.transferred": "📦 Передана в Pilar Faus",
    "book.status.accepted": "📚 В фонде Pilar Faus",
    "book.status.unavailable": "⏸ Пока недоступна",
    "book.open": "Открыть карточку",
    "book.untitled": "Без названия",
    "book.noAuthor": "Автор не указан",
    "book.related": "Похожие книги",
    "book.relatedFilter": "Фильтр похожих книг",
    "book.sameAuthor": "Того же автора",
    "book.sameLibrary": "В этой же библиотеке",
    "book.noDescription": "Описание пока не добавлено.",
    "book.reportError": "Хочу сообщить об ошибке",
    "book.notFoundTitle": "Книга не найдена",
    "book.notFound": "Книга не найдена. Вернитесь в каталог и выберите другую карточку.",
    "privacy.title": "Конфиденциальность",
    "privacy.pageTitle": "Конфиденциальность | VLC Biblio",
    "privacy.updated": "Последнее обновление: 2 октября 2026",
    "privacy.intro": "VLC Biblio ведёт публичный каталог книг и Telegram-бота для передачи книг в библиотеку Pilar Faus и временного обмена книгами между участниками.",
    "privacy.public.title": "Публичный сайт",
    "privacy.public.p1": "Этот сайт является статическим каталогом. Он не использует аналитику, рекламные пиксели, формы регистрации или собственные cookies.",
    "privacy.public.p2": "В каталоге публикуются сведения о книгах: название, автор, ISBN, издательство, год, описание, статус, дата обновления и ссылка для запроса книги через Telegram. Имена, Telegram ID, chat ID, исходные фотографии пользователей и внутренние заметки в публичный каталог не выгружаются.",
    "privacy.lists.title": "Корзина и избранное",
    "privacy.lists.p1": "Корзина и избранное сохраняются в локальном хранилище вашего браузера (localStorage). Сохраняются только идентификаторы выбранных книг. Списки доступны после закрытия и повторного открытия сайта в этом браузере; на другом устройстве или в другом браузере они будут отдельными. Списки не привязаны к Telegram-аккаунту и не отправляются команде проекта. Удалить книгу можно в соответствующем списке, а удалить все сохранённые списки — очистив данные сайта в настройках браузера.",
    "privacy.lists.p2": "Добавление книги в корзину или избранное не создаёт заявку и не резервирует книгу. При нажатии кнопки запроса книг через Telegram номера книг выбранного заказа передаются Telegram-боту через ссылку. Бот проверяет доступность и предлагает подтвердить отправку. Корзина после перехода в бот не очищается автоматически.",
    "privacy.external.title": "Внешние сервисы",
    "privacy.external.p1": "Обложки книг могут загружаться с публичных сайтов издателей, магазинов или книжных каталогов. При загрузке такой обложки браузер обращается к внешнему сайту напрямую. Ссылки на Telegram и Google Maps открываются только после нажатия пользователем.",
    "privacy.external.p2": "Страницы каталога и книг загружают официальный скрипт Telegram с telegram.org, чтобы кнопки перехода в бот работали внутри приложения Telegram. Корзина передаётся боту только после нажатия кнопки запроса книг.",
    "privacy.bot.title": "Telegram-бот",
    "privacy.bot.intro": "Если вы используете Telegram-бота, он может получать и хранить данные, необходимые для обработки заявки:",
    "privacy.bot.li1": "Telegram user ID, chat ID, username и отображаемое имя;",
    "privacy.bot.li2": "фотографии книг, текстовые сообщения и результаты OCR;",
    "privacy.bot.li3": "данные о книге, статус обработки, запросы на временную передачу и возврат книги.",
    "privacy.bot.p": "Эти данные нужны, чтобы обработать фотографии, подготовить карточку книги, отправить результат пользователю, передать заявку администраторам и, при необходимости, связать владельца книги с человеком, который запросил книгу.",
    "privacy.sharing.title": "Публикация и передача данных",
    "privacy.sharing.p": "Книга появляется в публичном каталоге только после проверки. Для частных книг публичная карточка не показывает владельца. Telegram username владельца передаётся запросившему пользователю только после согласия владельца на передачу книги.",
    "privacy.retention.title": "Сроки хранения",
    "privacy.retention.p": "Исходные фотографии, входные JSON-заявки, сообщения и OCR-тексты удаляются из рабочего архива через 90 дней после обработки. Заявки на обмен книгами хранятся до завершения: после возврата книги, отказа администратора или отказа владельца они удаляются через 90 дней. Chat ID администраторов хранятся только пока администратор находится в разрешённом списке.",
    "privacy.rights.title": "Ваши права",
    "privacy.rights.p": "Вы можете попросить удалить или исправить связанные с вами данные, а также уточнить, какие данные были сохранены. Для этого напишите в Telegram-бот <a href=\"https://t.me/VLS_Biblio_bot\" target=\"_blank\" rel=\"noreferrer\">@VLS_Biblio_bot</a> или в чат проекта <a href=\"https://t.me/bibliotecavlc\" target=\"_blank\" rel=\"noreferrer\">@bibliotecavlc</a>.",
    "privacy.contact.title": "Контакт",
    "privacy.contact.p": "По вопросам конфиденциальности напишите команде VLC Biblio через Telegram: <a href=\"https://t.me/bibliotecavlc\" target=\"_blank\" rel=\"noreferrer\">@bibliotecavlc</a>.",
    "shelf.inCart": "В корзине ✓",
    "shelf.addCart": "В корзину",
    "shelf.removeFavorite": "Убрать из избранного",
    "shelf.addFavorite": "Добавить в избранное",
    "shelf.lists": "Мои списки",
    "shelf.cart": "Корзина",
    "shelf.favorites": "Избранное",
    "shelf.openCart": "Открыть корзину",
    "shelf.close": "Закрыть",
    "shelf.full": "Список заполнен. Удалите ненужные книги.",
    "shelf.removedCart": "Книга удалена из корзины",
    "shelf.addedCart": "Книга добавлена в корзину",
    "shelf.removedFavorite": "Книга удалена из избранного",
    "shelf.addedFavorite": "Книга добавлена в избранное",
    "shelf.storageBlockedSuffix": ". Браузер не разрешает сохранение: список доступен только на этой странице.",
    "shelf.unpublished": "Книга больше не опубликована в каталоге",
    "shelf.available": "Доступна для запроса",
    "shelf.reserved": "Зарезервирована — можно встать в очередь",
    "shelf.unavailable": "Сейчас недоступна для запроса",
    "shelf.waitlistBot": "Встать в очередь в боте",
    "shelf.remove": "Удалить",
    "shelf.linkError": "Не удалось подготовить ссылку для этой книги.",
    "shelf.order": "Заказ",
    "shelf.booksRange": "книги",
    "shelf.requestSelected": "Запросить выбранные",
    "shelf.location": "Место передачи книг",
    "shelf.cartEmpty": "Корзина пока пуста. Добавляйте книги из каталога, а затем проверьте список перед отправкой в бот.",
    "shelf.favoritesEmpty": "Здесь будут книги, которые вы хотите сохранить на потом. Нажмите на сердечко на карточке книги.",
    "shelf.favoritesNote": "Сохранённые книги на потом. Доступные книги можно добавить в корзину.",
    "shelf.cartNote": "Проверьте список и удалите лишнее. Книги разных владельцев оформляются отдельно. Добавление в корзину не резервирует книгу; бот проверит доступность и попросит подтвердить отправку.",
    "shelf.library": "Библиотека",
    "shelf.unavailableHeading": "Сейчас недоступны",
    "shelf.unavailableNote": "Эти книги не включены в запрос. Можно оставить их в избранном или удалить из корзины.",
    "shelf.afterBot": "После перехода в бот корзина сохраняется. Удалите книги из неё, когда подтвердите заказ.",
    "shelf.storageOk": "Списки хранятся в этом браузере. На другом устройстве или в другом браузере они будут отдельными.",
    "shelf.storageBlocked": "Браузер не разрешает сохранение. Списки доступны только на этой странице.",
  };

  function t(key, fallback) {
    return locale === "ru" && Object.hasOwn(ru, key) ? ru[key] : fallback;
  }

  function translateDocument() {
    document.documentElement.lang = locale;
    document.querySelectorAll("[data-i18n]").forEach((element) => {
      const translated = t(element.dataset.i18n, element.textContent.trim());
      element.textContent = translated;
    });
    document.querySelectorAll("[data-i18n-html]").forEach((element) => {
      element.innerHTML = t(element.dataset.i18nHtml, element.innerHTML);
    });
    document.querySelectorAll("[data-i18n-placeholder]").forEach((element) => {
      element.placeholder = t(element.dataset.i18nPlaceholder, element.placeholder);
    });
    document.querySelectorAll("[data-i18n-aria-label]").forEach((element) => {
      element.setAttribute("aria-label", t(element.dataset.i18nAriaLabel, element.getAttribute("aria-label") || ""));
    });
    const toggle = document.querySelector("[data-language-toggle]");
    if (toggle) {
      toggle.textContent = locale === "es" ? "RU" : "ES";
      toggle.setAttribute("aria-label", t("language.switch", "Cambiar el idioma a ruso"));
      toggle.setAttribute("title", toggle.getAttribute("aria-label"));
      toggle.addEventListener("click", () => {
        const next = locale === "es" ? "ru" : "es";
        try { localStorage.setItem(storageKey, next); } catch { /* Reload still uses Russian. */ }
        location.reload();
      });
    }
  }

  window.BiblioI18n = Object.freeze({ locale, t, translateDocument });
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", translateDocument, { once: true });
  } else {
    translateDocument();
  }
})();
