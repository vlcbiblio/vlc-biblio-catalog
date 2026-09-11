# Как опубликовать изменения сайта

Публичный сайт находится здесь:

```text
https://vlcbiblio.github.io/vlc-biblio-catalog/
```

Локальные файлы лежат здесь:

```text
C:\29.Biblio\3.GitHub catalog
```

GitHub Pages публикует сайт из репозитория:

```text
https://github.com/vlcbiblio/vlc-biblio-catalog.git
```

## Почему сайт не меняется сразу

Если поменять `index.html` на компьютере, публичный сайт не обновится сам. Нужно отправить изменения в GitHub:

```powershell
cd "C:\29.Biblio\3.GitHub catalog"
git status
git add index.html data/books.js book.html privacy.html
git commit -m "Update site"
git push origin main
```

Если менялся только один файл, можно добавить только его:

```powershell
git add index.html
git commit -m "Update homepage links"
git push origin main
```

## Как проверить публикацию

После `git push` GitHub Pages обычно обновляется не мгновенно. Подождите 1-3 минуты и откройте сайт с принудительным обновлением:

```text
https://vlcbiblio.github.io/vlc-biblio-catalog/?v=1
```

Если браузер всё ещё показывает старую версию:

- нажмите `Ctrl + F5`;
- откройте сайт в режиме инкогнито;
- добавьте к адресу новый параметр, например `?v=2`.

## Быстрая проверка перед публикацией

```powershell
cd "C:\29.Biblio\3.GitHub catalog"
git diff -- index.html
git status
```

В `git diff` должны быть видны нужные изменения. В `git status` изменённые файлы должны исчезнуть после успешного коммита и `git push`.
