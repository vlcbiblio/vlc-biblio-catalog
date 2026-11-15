/* Compact category additions. The existing Telegram and shelf services are unchanged. */
(() => {
  'use strict';
  const logic = window.BiblioCategoryLogic;
  const language = () => window.BiblioI18n?.locale || 'ru';
  const text = (ru, es) => language() === 'es' ? es : ru;
  const escape = value => String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);
  const genresEs = {
    'Сказки и фольклор': 'Cuentos y folclore', 'Фэнтези': 'Fantasía', 'Научная фантастика': 'Ciencia ficción',
    'Детектив': 'Novela policíaca', 'Триллер': 'Thriller', 'Ужасы и мистика': 'Terror y misterio', 'Приключения': 'Aventuras',
    'Любовная проза': 'Narrativa romántica', 'Историческая проза': 'Narrativa histórica',
    'Социальная и психологическая проза': 'Narrativa social y psicológica', 'Юмор и сатира': 'Humor y sátira',
    'Рассказы и повести': 'Relatos y novelas cortas', 'Художественная проза': 'Narrativa', 'Фантастика': 'Ficción especulativa',
    'Поэзия': 'Poesía', 'Драматургия': 'Teatro', 'Комиксы и манга': 'Cómics y manga', 'Биографии и мемуары': 'Biografías y memorias',
    'Научно-популярная литература': 'Divulgación científica', 'История и общество': 'Historia y sociedad',
    'Искусство и культура': 'Arte y cultura', 'Психология': 'Psicología', 'Воспитание и родительство': 'Crianza',
    'Здоровье и медицина': 'Salud y medicina', 'Саморазвитие': 'Desarrollo personal', 'Бизнес и финансы': 'Negocios y finanzas',
    'Религия и мифология': 'Religión y mitología', 'Путешествия и краеведение': 'Viajes e historia local',
    'Языки и учебные пособия': 'Idiomas y manuales', 'Познавательная литература для детей': 'Divulgación infantil',
    'Кулинария': 'Cocina', 'Творчество и хобби': 'Creatividad y aficiones', 'Музыка': 'Música', 'Здоровье и тело': 'Salud y cuerpo',
    'Фантастика и фэнтези — общая рубрика': 'Ficción y fantasía — categoría general', 'Жанр не определён': 'Género sin determinar', 'Категория на проверке': 'Categoría pendiente de revisión',
    'Детская проза': 'Narrativa infantil', 'Истории о животных': 'Relatos de animales', 'Сказки': 'Cuentos',
    'Природа и животные': 'Naturaleza y animales', 'Эмоции и общение': 'Emociones y comunicación',
    'Книги-картинки': 'Álbumes ilustrados', 'Антиутопия': 'Distopía', 'Комиксы': 'Cómics',
    'Подростковая проза': 'Narrativa juvenil', 'Психологическая проза': 'Narrativa psicológica',
    'Животные и природа': 'Animales y naturaleza', 'История искусства': 'Historia del arte',
    'Изучение английского языка': 'Aprendizaje del inglés', 'Тёмное фэнтези': 'Fantasía oscura',
    'Личная безопасность': 'Seguridad personal', 'Философская проза': 'Narrativa filosófica',
    'Семейная проза': 'Narrativa familiar', 'Социальная проза': 'Narrativa social', 'Ужасы': 'Terror',
    'Мистика': 'Misterio sobrenatural', 'Адаптированное чтение': 'Lecturas adaptadas', 'Тело человека': 'El cuerpo humano',
    'Тело и взросление': 'Cuerpo y crecimiento', 'Семейная сага': 'Saga familiar', 'Готическая проза': 'Narrativa gótica',
    'Сатира': 'Sátira', 'Программирование': 'Programación', 'Хрестоматии': 'Antologías didácticas',
    'Школьное чтение': 'Lecturas escolares', 'Головоломки и игры': 'Acertijos y juegos',
    'Магический реализм': 'Realismo mágico', 'Литературный нонсенс': 'Nonsense literario',
    'Иллюстрация': 'Ilustración', 'Техника и изобретения': 'Tecnología e inventos',
    'Изучение испанского языка': 'Aprendizaje del español', 'Энциклопедии': 'Enciclopedias',
    'Биология': 'Biología', 'Учебная литература': 'Material didáctico', 'Биографическая проза': 'Narrativa biográfica',
    'Развивающие занятия': 'Actividades de desarrollo', 'История науки': 'Historia de la ciencia',
    'Литература о книгах': 'Libros sobre libros', 'Интерактивная книга': 'Libro interactivo',
    'Древнерусская литература': 'Literatura rusa antigua', 'Философия': 'Filosofía', 'Путешествия': 'Viajes',
    'Искусство в художественной литературе': 'Arte en la literatura', 'Городское фэнтези': 'Fantasía urbana',
    'Спорт и активный отдых': 'Deporte y ocio activo', 'Керамика': 'Cerámica', 'Практические навыки': 'Habilidades prácticas',
    'Рукоделие': 'Manualidades', 'Шитьё': 'Costura', 'Физика': 'Física', 'Химия': 'Química', 'Краеведение': 'Historia local',
    'Лирическая проза': 'Prosa lírica', 'Фотография': 'Fotografía', 'Словари': 'Diccionarios', 'Русский язык': 'Lengua rusa',
    'Уход за животными': 'Cuidado de animales', 'Дрессировка собак': 'Adiestramiento canino',
    'Мифы и легенды': 'Mitos y leyendas', 'Техника и технологии': 'Técnica y tecnología',
  };
  function categoryLabel(value, age = false) {
    if (language() !== 'es') return value;
    if (!age) return genresEs[value] || value;
    const ages = { 'Взрослые': 'Personas adultas', 'Возраст не определён': 'Edad sin determinar', 'Возрастная рекомендация на проверке': 'Edad recomendada pendiente de revisión', 'Дети — возраст уточняется': 'Infantil — edad sin determinar', 'Подростки — возраст уточняется': 'Juvenil — edad sin determinar' };
    return ages[value] || value.replace(/лет|года|год/g, 'años');
  }
  function statusLabel(status) {
    const labels = {
      external_catalog: text('Подтверждено внешним источником', 'Confirmado por una fuente externa'),
      editorial_recommendation: text('Рекомендация библиотеки', 'Recomendación de la biblioteca'),
      editorial_review: text('Редакционная категория', 'Categoría editorial'),
      editorial_proposal: text('Предварительная редакционная рекомендация', 'Propuesta editorial provisional'),
      legacy_unverified: text('Прежняя метка, без подтверждения', 'Etiqueta anterior sin confirmar'),
      unknown: text('Нет подтверждённых данных', 'Sin datos confirmados'),
      conflict: text('Источники расходятся', 'Las fuentes discrepan'),
      pending_review: text('На проверке', 'Pendiente de revisión'),
    };
    return labels[status] || text('Редакционная рекомендация', 'Recomendación editorial');
  }
  function cardMarkup(book) {
    const age = logic.list(book, 'reader_age_groups').map(value => categoryLabel(value, true));
    const genres = logic.list(book, 'genres').map(value => categoryLabel(value));
    const ageText = age.length ? age.join(' · ') : text('Возраст: нет данных', 'Edad: sin datos');
    const genreText = genres.length ? genres.slice(0, 2).join(' · ') : text('Жанр: нет данных', 'Género: sin datos');
    return `<div class="local-category-tags"><span class="local-age" title="${escape(text('Возраст читателя', 'Edad de lectura'))}">${escape(ageText)}</span><span class="local-genre" title="${escape(genres.join(' · '))}">${escape(genreText)}</span></div>`;
  }
  function sourceMarkup(values) {
    return [...new Set(values || [])].map(raw => {
      const url = logic.safeUrl(raw);
      return url ? `<a href="${escape(url)}" target="_blank" rel="noopener noreferrer">${escape(new URL(url).hostname.replace(/^www\./, ''))} ↗</a>` : '';
    }).join(' ');
  }
  function detailMarkup(book) {
    const group = (title, values, status, sources, age = false) => `<div class="local-category-detail"><dt>${escape(title)}</dt><dd>${escape(values.length ? values.map(value => categoryLabel(value, age)).join(' · ') : text('Нет данных', 'Sin datos'))}<small>${escape(statusLabel(status))}</small>${sourceMarkup(sources)}</dd></div>`;
    const genreBasis = /\.py|RULES|classification\.json/.test(book.genre_basis || '') ? '' : book.genre_basis;
    const basis = [...new Set([...logic.list(book, 'reader_age_basis'), ...(genreBasis ? [genreBasis] : [])].map(value => String(value).trim()).filter(Boolean))];
    const research = sourceMarkup(book.research_sources);
    return `<section class="local-categories" aria-label="${escape(text('Возраст и жанр', 'Edad y género'))}"><dl>
      ${group(text('Возраст читателя', 'Edad de lectura'), logic.list(book, 'reader_age_groups'), book.reader_age_status, book.reader_age_sources, true)}
      ${group(text('Жанр и тема', 'Género y tema'), logic.list(book, 'genres'), book.genre_status, book.genre_sources)}
      ${group(text('Маркировка издания', 'Clasificación de la edición'), logic.list(book, 'edition_age_ratings'), book.edition_rating_status, book.edition_rating_sources)}
    </dl><details><summary>${escape(text('Основание редакционной рекомендации', 'Base de la recomendación editorial'))}</summary><p>${escape(text('Возраст читателя — рекомендация для выбора книги. Маркировка относится к конкретному изданию; 0+ не означает рекомендацию для младенцев. Редакционные рекомендации библиотеки не являются возрастной маркировкой издателя.', 'La edad de lectura es una orientación para elegir. La clasificación corresponde a una edición concreta; 0+ no significa que se recomiende a bebés. Las recomendaciones editoriales de la biblioteca no son la clasificación de la editorial.'))}</p>${basis.length ? `<p>${escape(basis.join('; '))}</p>` : ''}${research ? `<p>${escape(text('Ссылки ниже относятся к произведению или серии и не подтверждают ISBN конкретного издания.', 'Las siguientes referencias corresponden a la obra o la serie y no confirman el ISBN de esta edición.'))}</p><p class="local-research-sources">${research}</p>` : ''}</details>${book.editorial_note ? `<p class="local-editorial-note">${escape(book.editorial_note)}</p>` : ''}</section>`;
  }
  function fillFilters(books, state) {
    const labels = { age: text('Возраст читателя', 'Edad de lectura'), genre: text('Жанр и тема', 'Género y tema'), reset: text('Сбросить', 'Restablecer') };
    document.querySelectorAll('[data-category-label]').forEach(element => { element.textContent = labels[element.dataset.categoryLabel] || ''; });
    for (const [id, key, initial, age] of [['ageFilter', 'reader_age_groups', text('Любой возраст', 'Cualquier edad'), true], ['genreFilter', 'genres', text('Все жанры и темы', 'Todos los géneros y temas'), false]]) {
      const select = document.getElementById(id);
      select.replaceChildren();
      const values = age ? logic.ageOptions(books) : logic.options(books, key);
      for (const [value, label] of [['', initial], ...values.map(value => [value, categoryLabel(value, age)])]) {
        const option = document.createElement('option'); option.value = value; option.textContent = label; select.append(option);
      }
    }
    syncControls(state);
  }
  function syncControls(state) {
    for (const [id, key] of [['search', 'search'], ['sectionFilter', 'section'], ['ageFilter', 'age'], ['genreFilter', 'genre']]) {
      const control = document.getElementById(id); if (control) control.value = state[key] || '';
      // Keep an existing precise-age deep link visible while the main menu uses
      // six broad groups. Detail labels themselves are never rounded or changed.
      if (control && key === 'age' && state.age && !Array.from(control.options || control.children).some(option => option.value === state.age)) {
        const option = document.createElement('option'); option.value = state.age; option.textContent = categoryLabel(state.age, true); control.append(option); control.value = state.age;
      }
    }
  }
  window.BiblioCategories = Object.freeze({ cardMarkup, detailMarkup, fillFilters, syncControls, categoryLabel, statusLabel });
})();
