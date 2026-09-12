# VLC Biblio Catalog

Static catalog prototype for VLC Biblio.

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

Only rows with book data and either `channel_published_at` or `user_published_at` are
exported. Private Telegram fields such as `chat_id`, `user_id`, `username`, source photos,
OCR paths, and internal notes are not written to `data/books.js`.

## Publication state

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

Book covers are loaded from public source URLs. If an external image is unavailable,
the catalog replaces it with a local text placeholder instead of leaving a broken image.

## Book pages

Each book opens as a standalone detail page with a shareable URL:

```text
https://vlcbiblio.github.io/vlc-biblio-catalog/book.html?id=7
```
