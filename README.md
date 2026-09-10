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

Only rows with book data and `channel_published_at` are exported. Private Telegram fields
such as `chat_id`, `user_id`, `username`, source photos, OCR paths, and internal notes are
not written to `data/books.js`.

## Cover handling

Book covers are loaded from public source URLs. If an external image is unavailable,
the catalog replaces it with a local text placeholder instead of leaving a broken image.
