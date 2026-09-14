# VLC Biblio Catalog

Static catalog prototype for VLC Biblio.

## Basket and favorites

Both the catalog and book pages have persistent browser-local **Корзина** and
**Избранное** lists. Available private books can be added to the basket; any book
can be saved as a favorite. The same lists are available after page navigation,
reload, and reopening the site in this browser. Tabs on the same site share the
lists. Another browser, browser profile, or device has separate lists; clearing
site storage removes them. They are not linked to a Telegram account.

Favorite buttons use a heart on each cover: outline when unsaved, red and filled
when saved. Click again to remove the book. The heart in the top navigation opens
the favorites list. Buttons also work with a keyboard and have accessible labels.

Open the basket to review and remove books before using **Проверить в боте**.
Books are grouped by the existing public `libraryKey`; unknown owners are kept
separate. Each link opens the bot's existing draft and confirmation flow. Books
are not reserved by adding them to the basket or favorites. The bot checks
current availability, ownership, and duplicate requests before submission.

Orders respect the bot's limit of 30 books and Telegram's
[64-character `start` parameter limit](https://core.telegram.org/bots/features#deep-linking).
Larger groups get separate links labeled with the corresponding
book ranges. Unavailable or removed books stay visible in the basket, but are not
included in checkout. Reserved books retain their waitlist link. The basket stays
intact after opening Telegram because the static site cannot know whether the
reader confirmed the request; readers remove ordered books themselves.

`assets/shelf.js` and `assets/shelf.css` provide the shared behavior and UI.
Only public book IDs are saved in `localStorage`, under path-scoped
`vlc-biblio:shelf:v1:` keys. If storage is blocked, the current page remains usable
and displays a notice that the lists cannot be persisted.

Browser checks use synthetic books and block external requests:

```powershell
python -X utf8 -m unittest test_shelf test_catalog_navigation test_cover_loading -v
```

Publish both shared assets together with `index.html`, `book.html`, and
`privacy.html` to make these features available on GitHub Pages. No bot restart
is needed for this site change.

## GitHub Pages

1. Open repository settings.
2. Go to Pages.
3. Choose `Deploy from a branch`.
4. Select branch `main` and folder `/root`.
5. Save.

The public page will be available at:

```text
https://vlcbiblio.github.io/vlc-biblio-catalog/
```

## Data export

Generate the public catalog payload from the Telegram processing table:

```powershell
python export_catalog.py
```

Rows with book data are exported after Telegram delivery or with an explicit
`catalog_visibility=public` selection for a catalog batch. Private Telegram fields
such as `chat_id`, `user_id`, `username`, source photos,
OCR paths, and internal notes are not written to `data/books.js`.

## Publication state

Catalog-only batches use `catalog_batch_id` and `catalog_added_at` in the local
table. Their `telegram_delivery_mode=manual_batch` excludes them from automatic
admin handoff, user delivery and channel publication. Telegram receipt fields stay
empty. The private batch manifest records source reviews, backups and the verified
GitHub Pages deployment. Normal exports retain these explicitly selected books.

Readers can request these books through the bot. If the archive owner has no
linked Telegram ID, requests stay with the administrator until that account is
linked; the bot does not attempt to send to an unknown owner.

Catalog visibility and Telegram delivery are different facts. A book exported
because of `user_published_at` is not necessarily published to the channel. Do not
use the total catalog size as the channel's library count or as a delivery receipt.

The bot publishes one channel announcement per approved queue snapshot. For more
than 10 books it shows five books in comments and links to this catalog. That
shortened preview must wait until all batch books are verified on the public site,
with the expected identities, metadata and covers.

A generated `data/books.js`, a local Git commit, a successful push and a live
GitHub Pages update are separate steps. A push denied with HTTP 403 leaves local
commits unpublished; report the failure and resolve authorized access rather than
claiming that the public catalog was updated. Never force-push or switch accounts
as an automatic workaround.

Processing evidence, cover checks and duplicate decisions are documented in the
sibling Telegram repository: `../1.Telegram/_bot/PROCESSING_QUALITY.md` and
`../1.Telegram/_bot/REVIEW_WORKFLOW.md`. Keep runtime submissions and private review
reports out of this public catalog repository.

## Cover handling

The catalog uses local WebP copies of the existing public cover images, with variants
up to 360 and 720 pixels wide. The browser selects a size for the screen; the main
book cover loads with high priority, and related covers load near the viewport.
Content hashes in image filenames let browsers reuse unchanged covers between pages.

Prepare copies after adding or correcting public covers:

```powershell
python -m pip install Pillow
python optimize_covers.py
```

This processes only the existing `data/books.js`, preserving book data and original
cover URLs. It writes `assets/covers/optimized/`, `assets/covers/manifest.json` and
the responsive image references in `data/books.js`; publish these assets along with
the updated HTML/data files. `--refresh` downloads existing URLs again when their
image content has changed. Downloads have size/time limits, and failed downloads
retain the original source fallback. Originals are cached in the local temp directory.

Normal exports reuse the manifest without downloading images or requiring Pillow.
A corrected source URL cannot pick up a previously cached cover. New covers without
prepared variants use their original URL until the next optimization. Unavailable
images are replaced by a text placeholder instead of a broken image.

## Book pages

Each book opens as a standalone detail page with a shareable URL:

```text
https://vlcbiblio.github.io/vlc-biblio-catalog/book.html?id=7
```

Browser Back and Forward follow the visited book pages in order. The explicit
`← Назад к каталогу` link opens the catalog with the search, section and scroll
position last saved in that tab. History entries keep their own catalog state;
refreshing the catalog also restores its position. A visible book acts as a scroll
anchor if the layout or catalog contents change. A direct book link in a fresh tab
returns to the top of the unfiltered catalog.

Navigation checks use a local HTTP server and synthetic books:

```powershell
python -m pip install playwright
python -m playwright install chromium
python -X utf8 -m unittest test_catalog_navigation -v
```
