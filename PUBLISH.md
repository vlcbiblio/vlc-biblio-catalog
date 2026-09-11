# Как опубликовать изменения сайта

## Главное правило для агента

Не рапортовать пользователю, что публичный сайт изменился, сразу после локальной
правки файла.

Сайт считается изменённым только после всей цепочки:

```text
локальная правка -> git diff -> git add -> git commit -> git push origin main -> проверка GitHub Pages
```

Если сделана только локальная правка, писать нужно так:

```text
Файл изменён локально, но публичный сайт ещё не обновлён.
```

Если `git push` ещё не выполнен или не прошёл, нельзя писать:

```text
Сайт обновлён.
```

Если `git push` прошёл, но GitHub Pages ещё отдаёт старую версию, писать нужно так:

```text
Изменения уже на GitHub, но GitHub Pages пока отдаёт старую версию. Нужно подождать и проверить снова.
```

Финальный отчёт “сайт обновлён” допустим только когда публичный URL с cache-buster
уже содержит проверяемый новый текст или HTML.

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
