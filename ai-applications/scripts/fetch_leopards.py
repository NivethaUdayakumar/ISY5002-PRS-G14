"""
Download freely licensed leopard photos from Wikimedia Commons, skip any that
duplicate (or nearly duplicate) your existing images, and zip the results.

What it does:
  1. Searches Wikimedia Commons for photos of leopards (Panthera pardus).
  2. Downloads each one at 1024 px wide (like your existing images).
  3. Skips any photo already listed in your "attribution.csv" (matched by
     source URL, Commons page, or file name), plus exact duplicates and near-duplicates (resized / re-saved copies)
     of anything already in your "images" folder or already downloaded.
  4. Saves them to "new_leopards/" and writes "new_leopards/attribution.csv"
     with the author, license and source page for every photo.
  5. Zips everything into "new_leopards.zip".

Setup (once):
    pip install pillow imagehash

Usage:
    python fetch_leopards.py              # uses NUM_IMAGES (66)
    python fetch_leopards.py --count 100  # override for one run
"""

import argparse
import csv
import hashlib
import io
import json
import re
import shutil
import time
import urllib.parse
import urllib.request
from pathlib import Path

import imagehash
from PIL import Image

# ===== SETTINGS =====
NUM_IMAGES = 120   # how many new unique leopard images to download
# ====================

SCRIPT_DIR = Path(__file__).resolve().parent
EXISTING_DIR = SCRIPT_DIR / "images"
ATTRIBUTION_CSV = SCRIPT_DIR / "attribution.csv"  # images listed here are skipped
OUTPUT_DIR = SCRIPT_DIR / "images_2"
ZIP_PATH = SCRIPT_DIR / "new_leopards"  # .zip is added automatically

API = "https://commons.wikimedia.org/w/api.php"
# Wikimedia asks every script to identify itself; put your email here if you like.
USER_AGENT = "LeopardDatasetBuilder/1.0 (personal research project)"
SEARCH = '"Panthera pardus" filetype:bitmap'

# Titles containing these words are usually not photos of a live leopard.
SKIP_WORDS = [
    "wild leopard"
]
LICENSE_OK = ("cc0", "cc by", "cc-by", "public domain", "pd")
NEAR_DUP_DISTANCE = 8   # lower = stricter "near duplicate" test
MIN_WIDTH = 600          # skip small images


def api_get(params):
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def download(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def strip_html(text):
    return re.sub(r"<[^>]+>", "", text or "").strip()


def search_candidates():
    """Yield image info dicts from Commons search results, page by page."""
    params = {
        "action": "query", "format": "json",
        "generator": "search", "gsrsearch": SEARCH,
        "gsrnamespace": 6, "gsrlimit": 50,
        "prop": "imageinfo", "iiprop": "url|mime|size|extmetadata",
        "iiurlwidth": 1024,
    }
    while True:
        data = api_get(params)
        for page in data.get("query", {}).get("pages", {}).values():
            info = (page.get("imageinfo") or [None])[0]
            if info:
                info["title"] = page["title"]
                yield info
        if "continue" not in data:
            return
        params.update(data["continue"])
        time.sleep(1)


def is_usable(info):
    title = info["title"].lower()
    if any(w in title for w in SKIP_WORDS):
        return False
    if info.get("mime") != "image/jpeg" or info.get("width", 0) < MIN_WIDTH:
        return False
    lic = info.get("extmetadata", {}).get("LicenseShortName", {}).get("value", "")
    return lic.lower().startswith(LICENSE_OK)


def normalize(value):
    """Turn a URL, 'File:Name.jpg' title or filename into a comparable key."""
    value = urllib.parse.unquote(str(value or "")).strip()
    value = value.split("?")[0].rstrip("/").rsplit("/", 1)[-1]  # last URL part
    value = re.sub(r"^(file|image):", "", value, flags=re.IGNORECASE)
    value = re.sub(r"^\d+px-", "", value)                       # thumbnail prefix
    return value.replace("_", " ").strip().lower()


def load_attribution_keys():
    """Collect every source URL, title or filename mentioned in attribution.csv,
    whatever its column names are."""
    keys = set()
    if not ATTRIBUTION_CSV.is_file():
        print("No attribution.csv found; nothing extra to skip.")
        return keys
    with open(ATTRIBUTION_CSV, newline="", encoding="utf-8-sig") as fh:
        for row in csv.reader(fh):
            for cell in row:
                for part in re.split(r"\s+", cell.strip()):
                    if "/" in part or re.search(r"\.(jpe?g|png|gif|webp|tiff?)$", part, re.I):
                        key = normalize(part)
                        if key:
                            keys.add(key)
                if re.match(r"^(file|image):", cell.strip(), re.I):
                    keys.add(normalize(cell))
    print(f"Loaded {len(keys)} entries from attribution.csv to skip.")
    return keys


def candidate_keys(info):
    return {normalize(info["title"]), normalize(info.get("url")),
            normalize(info.get("descriptionurl"))} - {""}


def fingerprint(img):
    return imagehash.phash(img.convert("RGB"))


def load_existing():
    md5s, hashes = set(), []
    if EXISTING_DIR.is_dir():
        for f in EXISTING_DIR.iterdir():
            if f.suffix.lower() in {".jpg", ".jpeg", ".png"}:
                data = f.read_bytes()
                md5s.add(hashlib.md5(data).hexdigest())
                try:
                    hashes.append(fingerprint(Image.open(io.BytesIO(data))))
                except Exception:
                    pass
    print(f"Loaded {len(hashes)} existing images for duplicate checking.")
    return md5s, hashes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=NUM_IMAGES,
                        help=f"Number of images to fetch (default: {NUM_IMAGES})")
    args = parser.parse_args()

    md5s, hashes = load_existing()
    listed = load_attribution_keys()
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir()

    rows, saved = [], 0
    for info in search_candidates():
        if saved >= args.count:
            break
        if not is_usable(info):
            continue
        if candidate_keys(info) & listed:
            print(f"  skip (in attribution.csv): {info['title']}")
            continue
        url = info.get("thumburl") or info["url"]
        try:
            data = download(url)
            img = Image.open(io.BytesIO(data))
            img.load()
        except Exception as e:
            print(f"  skip (download failed): {info['title']} - {e}")
            continue

        md5 = hashlib.md5(data).hexdigest()
        fp = fingerprint(img)
        if md5 in md5s or any(fp - h <= NEAR_DUP_DISTANCE for h in hashes):
            print(f"  skip (duplicate): {info['title']}")
            continue
        md5s.add(md5)
        hashes.append(fp)

        saved += 1
        name = f"web_{saved:04d}_leopard.jpg"
        (OUTPUT_DIR / name).write_bytes(data)

        meta = info.get("extmetadata", {})
        rows.append({
            "file": name,
            "title": info["title"],
            "author": strip_html(meta.get("Artist", {}).get("value")),
            "license": meta.get("LicenseShortName", {}).get("value", ""),
            "license_url": meta.get("LicenseUrl", {}).get("value", ""),
            "source": info.get("descriptionurl", ""),
        })
        print(f"[{saved}/{args.count}] {name}  <-  {info['title']}")
        time.sleep(1)  # be polite to Wikimedia's servers

    with open(OUTPUT_DIR / "attribution.csv", "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]) if rows else ["file"])
        writer.writeheader()
        writer.writerows(rows)

    shutil.make_archive(str(ZIP_PATH), "zip", SCRIPT_DIR, OUTPUT_DIR.name)
    print(f"\nSaved {saved} new image(s) to {OUTPUT_DIR.name}/ and {ZIP_PATH.name}.zip")
    if saved < args.count:
        print("Fewer than requested; try loosening SKIP_WORDS or NEAR_DUP_DISTANCE.")


if __name__ == "__main__":
    main()