"""Cache the current public covers as responsive WebP images on the static site."""

import argparse
import hashlib
import json
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path
from urllib.parse import unquote, urlsplit
from urllib.request import Request, urlopen

from PIL import Image, ImageOps

import export_catalog as export


WIDTHS = (360, 720)
MAX_DOWNLOAD_BYTES = 12 * 1024 * 1024
SITE_HOST = "vlcbiblio.github.io"
SITE_PATH = "/vlc-biblio-catalog/"


def read_public_books(path):
    text = path.read_text(encoding="utf-8")
    prefix = "window.BIBLIO_BOOKS = "
    if not text.startswith(prefix):
        raise ValueError("Expected the existing public catalog payload")
    return json.loads(text[len(prefix):].strip().removesuffix(";"))


def download_cover(source, root, cache_dir, refresh=False):
    url = urlsplit(source)
    if url.scheme not in {"http", "https"}:
        raise ValueError("Only public HTTP(S) cover URLs are supported")
    if url.netloc == SITE_HOST and url.path.startswith(SITE_PATH + "assets/covers/"):
        local = (root / unquote(url.path.removeprefix(SITE_PATH))).resolve()
        if local.is_relative_to((root / "assets/covers").resolve()) and local.is_file():
            return local.read_bytes()
    cache_file = cache_dir / (hashlib.sha256(source.encode()).hexdigest() + ".image")
    if cache_file.is_file() and not refresh:
        return cache_file.read_bytes()
    request = Request(source, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=20) as response:
        payload = response.read(MAX_DOWNLOAD_BYTES + 1)
    if len(payload) > MAX_DOWNLOAD_BYTES:
        raise ValueError("Cover exceeds the download limit")
    # Do not cache an HTML error response or a truncated image as a cover.
    with Image.open(BytesIO(payload)) as image:
        image.verify()
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file.write_bytes(payload)
    return payload


def create_variants(payload, root):
    output_dir = root / "assets/covers/optimized"
    output_dir.mkdir(parents=True, exist_ok=True)
    with Image.open(BytesIO(payload)) as original:
        oriented = ImageOps.exif_transpose(original)
        mode = "RGBA" if "A" in oriented.getbands() or "transparency" in oriented.info else "RGB"
        image = oriented.convert(mode)
        variants = []
        for width in sorted({min(width, image.width) for width in WIDTHS}):
            height = max(1, round(image.height * width / image.width))
            resized = image.resize((width, height), Image.Resampling.LANCZOS)
            buffer = BytesIO()
            resized.save(buffer, "WEBP", quality=82, method=6)
            encoded = buffer.getvalue()
            # Changed content gets a new URL; unchanged images stay browser-cacheable.
            digest = hashlib.sha256(encoded).hexdigest()[:20]
            relative = f"assets/covers/optimized/{digest}-{width}.webp"
            target = root / relative
            if not target.is_file():
                target.write_bytes(encoded)
            variants.append({"src": f"./{relative}", "width": width, "height": height, "bytes": len(encoded)})
    return {"sourceBytes": len(payload), "variants": variants}


def optimize_catalog(catalog, cache_dir, refresh=False):
    root = catalog.resolve().parent.parent
    original_catalog = catalog.read_bytes()
    books = read_public_books(catalog)
    manifest_path = root / "assets/covers/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {"version": 1, "covers": {}}
    sources = sorted({book["cover"] for book in books if book.get("cover")})
    results = {}

    def prepare(source):
        cached = manifest["covers"].get(source)
        if cached and not refresh and all((root / v["src"]).is_file() for v in cached["variants"]):
            return cached
        return create_variants(download_cover(source, root, cache_dir, refresh), root)

    with ThreadPoolExecutor(max_workers=6) as pool:
        pending = {pool.submit(prepare, source): source for source in sources}
        for future in as_completed(pending):
            source = pending[future]
            try:
                results[source] = future.result()
            except Exception as error:
                print(f"Could not optimize {source}: {error}", flush=True)
    # Do not overwrite a catalog that another publisher changed during downloads.
    if catalog.read_bytes() != original_catalog:
        raise RuntimeError("Catalog changed during optimization; rerun using the new public data")
    manifest["covers"].update(results)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    export.write_books(catalog, books)
    export.update_data_cache_buster(root / "index.html", root / "book.html")
    totals = {
        "optimized": len(results),
        "total": len(sources),
        "sourceBytes": sum(item["sourceBytes"] for item in results.values()),
        "thumbnailBytes": sum(item["variants"][0]["bytes"] for item in results.values()),
        "detailBytes": sum(item["variants"][-1]["bytes"] for item in results.values()),
    }
    print(json.dumps(totals, indent=2))
    return totals


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=export.DEFAULT_OUTPUT)
    parser.add_argument("--download-cache", type=Path, default=Path(tempfile.gettempdir()) / "vlc-biblio-cover-downloads")
    parser.add_argument("--refresh", action="store_true", help="Download and recompress existing source URLs again")
    args = parser.parse_args()
    optimize_catalog(args.catalog, args.download_cache, args.refresh)


if __name__ == "__main__":
    main()
