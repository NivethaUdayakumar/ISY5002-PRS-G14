"""
Sync the team dataset from Ultralytics Platform into "data/wildlife_dataset"
(images/, labels/ and wildlife_dataset.yaml).

What it does:
  1. Reads the dataset's NDJSON manifest (every image, its split and its YOLO
     labels). By default it uses "isy5002-g14-dataset.ndjson" next to this
     script (exported from the Platform dataset page); if that file is missing
     it asks Ultralytics Platform for a fresh export (needs an API key).
  2. Downloads any image that is new or has changed size into images/<split>/,
     keeping the original file names.
  3. Rewrites labels/<split>/<name>.txt for every image from the Platform labels.
  4. Deletes local images/labels that are no longer on the Platform (or that
     moved to another split), and removes stale labels/*.cache files.
  5. Updates the class names in wildlife_dataset.yaml.

Setup (once):
    pip install ultralytics pillow
    Only needed without a local .ndjson file: get an API key at
    https://platform.ultralytics.com/settings, then either
      $env:ULTRALYTICS_API_KEY="<key>"     (PowerShell)
      yolo settings api_key=<key>          (saved permanently)
    or pass --api-key <key>.

Note: the image links inside an exported .ndjson are signed and expire after
about a week. If downloads start failing, export a fresh .ndjson.

Usage:
    python pull_platform_dataset.py --dry-run   # show what would change
    python pull_platform_dataset.py             # apply the changes
    python pull_platform_dataset.py --ndjson path/to/export.ndjson
    python pull_platform_dataset.py --online    # ignore the local file, export from Platform
    python pull_platform_dataset.py --no-prune  # add/update only, never delete
"""

import argparse
import json
import os
import shutil
import tempfile
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse

import yaml
from PIL import Image

# ===== SETTINGS =====
DATASET_URL = "https://platform.ultralytics.com/nivetha-udayakumar/datasets/isy5002-g14-dataset"
WORKERS = 16  # parallel image downloads
# ====================

SCRIPT_DIR = Path(__file__).resolve().parent
NDJSON_PATH = SCRIPT_DIR / "isy5002-g14-dataset.ndjson"
DATASET_DIR = SCRIPT_DIR.parents[1] / "data" / "wildlife_dataset"
YAML_PATH = DATASET_DIR / "wildlife_dataset.yaml"
SPLITS = ("train", "val", "test")
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}
KEY_HELP = (
    "Put an exported .ndjson next to this script (or pass --ndjson), or set your API key with one of:\n"
    '  $env:ULTRALYTICS_API_KEY="<key>"      (PowerShell, this window only)\n'
    "  yolo settings api_key=<key>            (saved permanently)\n"
    "  python pull_platform_dataset.py --api-key <key>"
)


def to_platform_uri(url):
    """https://platform.ultralytics.com/user/datasets/slug -> ul://user/datasets/slug"""
    if url.startswith("ul://"):
        return url
    parts = [p for p in urlparse(url).path.split("/") if p]
    if len(parts) != 3 or parts[1] != "datasets":
        raise ValueError(f"Not a Platform dataset URL: {url}")
    return "ul://" + "/".join(parts)


def read_manifest(path):
    with Path(path).open(encoding="utf-8") as f:
        lines = [json.loads(line) for line in f if line.strip()]
    return lines[0], lines[1:]


def fetch_manifest(dataset_url):
    """Export the dataset on Platform and download its NDJSON manifest."""
    from ultralytics.utils.checks import resolve_platform_uri

    uri = to_platform_uri(dataset_url)
    print(f"Requesting export of {uri} (this can take a while for large datasets)...")
    try:
        signed_url = resolve_platform_uri(uri)
    except (ValueError, PermissionError, FileNotFoundError, ConnectionError) as e:
        raise SystemExit(f"Could not fetch the dataset: {e}\n{KEY_HELP}")
    with tempfile.TemporaryDirectory() as workdir:
        path = Path(workdir) / "dataset.ndjson"
        download(signed_url, path)
        return read_manifest(path)


def download(url, path, attempts=3):
    """Download url to path atomically, retrying transient failures."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.part")
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(url, timeout=60) as r, tmp.open("wb") as f:
                shutil.copyfileobj(r, f)
            os.replace(tmp, path)
            return
        except Exception:
            tmp.unlink(missing_ok=True)
            if attempt == attempts:
                raise


def needs_download(path, record):
    """Download if missing, unreadable, or a different size than on Platform.

    (Platform re-encodes uploads, so its content hashes never match local files.)
    """
    if not path.exists():
        return True
    if not record.get("width") or not record.get("height"):
        return False
    try:
        with Image.open(path) as im:
            return im.size != (record["width"], record["height"])
    except Exception:
        return True


def label_text(record):
    annotations = record.get("annotations") or {}
    rows = next(iter(annotations.values()), []) if annotations else []
    return "".join(" ".join(map(str, row)) + "\n" for row in rows if row)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ndjson", type=Path, default=NDJSON_PATH, help="local NDJSON export to use")
    ap.add_argument("--online", action="store_true", help="export from Platform even if the local .ndjson exists")
    ap.add_argument("--url", default=DATASET_URL, help="Platform dataset URL or ul:// URI (with --online)")
    ap.add_argument("--dest", type=Path, default=DATASET_DIR, help="local dataset folder")
    ap.add_argument("--api-key", help="Ultralytics API key (else ULTRALYTICS_API_KEY / yolo settings)")
    ap.add_argument("--dry-run", action="store_true", help="only report what would change")
    ap.add_argument("--no-prune", action="store_true", help="keep local files that are not on Platform")
    args = ap.parse_args()

    if args.api_key:
        os.environ["ULTRALYTICS_API_KEY"] = args.api_key
    dest = args.dest.resolve()
    yaml_path = dest / YAML_PATH.name

    if not args.online and args.ndjson.is_file():
        print(f"Using local manifest {args.ndjson}")
        meta, records = read_manifest(args.ndjson)
    else:
        meta, records = fetch_manifest(args.url)

    if meta.get("task", "detect") != "detect":
        raise SystemExit(f"Expected a detection dataset, got task={meta.get('task')!r}")

    # ---- work out the plan -------------------------------------------------
    wanted_images, wanted_labels = set(), {}
    to_download, to_move = [], []
    for r in records:
        split, name = r.get("split"), r.get("file")
        if split not in SPLITS or not name or Path(name).name != name:
            print(f"  skipping malformed record: split={split!r} file={name!r}")
            continue
        img = dest / "images" / split / name
        lbl = dest / "labels" / split / f"{Path(name).stem}.txt"
        wanted_images.add(img)
        wanted_labels[lbl] = label_text(r)
        if needs_download(img, r):
            # Image moved to another split on Platform: move the local copy instead of re-downloading it
            src = next((p for s in SPLITS if (p := dest / "images" / s / name) != img and not needs_download(p, r)), None)
            if src and not img.exists():
                to_move.append((src, img))
            else:
                to_download.append((img, r.get("url")))
    moved_from = {src for src, _ in to_move}

    changed_labels = [p for p, t in wanted_labels.items() if not p.exists() or p.read_text() != t]

    stale = []
    if not args.no_prune:
        for split in SPLITS:
            for p in (dest / "images" / split).glob("*"):
                if p.is_file() and p.suffix.lower() in IMAGE_EXTS and p not in wanted_images and p not in moved_from:
                    stale.append(p)
            for p in (dest / "labels" / split).glob("*.txt"):
                if p not in wanted_labels:
                    stale.append(p)

    counts = {s: sum(r.get("split") == s for r in records) for s in SPLITS}
    names = {int(k): v for k, v in (meta.get("class_names") or {}).items()}
    print(f"Platform: {len(records)} images ({counts['train']} train, {counts['val']} val, {counts['test']} test)")
    print(f"Classes:  {names}")
    stale_images = [p for p in stale if p.suffix.lower() in IMAGE_EXTS]
    print(
        f"To download: {len(to_download)} | to move between splits: {len(to_move)} | "
        f"labels to write: {len(changed_labels)} | images to delete: {len(stale_images)} "
        f"(+{len(stale) - len(stale_images)} labels)"
    )

    if args.dry_run:
        for p, _ in to_download[:10]:
            print(f"  + {p.relative_to(dest)}")
        for src, dst in to_move[:10]:
            print(f"  > {src.relative_to(dest)} -> {dst.parent.name}/")
        for p in stale_images:
            print(f"  - {p.relative_to(dest)}")
        print("Dry run: nothing changed.")
        return

    # ---- apply -------------------------------------------------------------
    for src, dst in to_move:
        dst.parent.mkdir(parents=True, exist_ok=True)
        os.replace(src, dst)

    failed = [img for img, url in to_download if not url]
    jobs = [(img, url) for img, url in to_download if url]
    if jobs:
        with ThreadPoolExecutor(WORKERS) as pool:
            futures = {pool.submit(download, url, img): img for img, url in jobs}
            for i, fut in enumerate(as_completed(futures), 1):
                if fut.exception():
                    failed.append(futures[fut])
                if i % 50 == 0 or i == len(futures):
                    print(f"  downloaded {i}/{len(futures)}")

    for p in changed_labels:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(wanted_labels[p])

    for p in stale:
        p.unlink()
    for cache in (dest / "labels").glob("*.cache"):
        cache.unlink()  # YOLO rebuilds these on the next training run

    cfg = yaml.safe_load(yaml_path.read_text()) if yaml_path.exists() else {}
    cfg.update({"path": str(dest), **{s: f"images/{s}" for s in SPLITS if counts[s]}})
    if names:
        cfg["names"] = names
    yaml_path.write_text(yaml.safe_dump(cfg, sort_keys=False))

    print(f"Done. Updated {dest}")
    if failed:
        print(
            f"WARNING: {len(failed)} images failed to download, e.g. {failed[0].relative_to(dest)}. Re-run to retry; "
            "if it keeps failing, the .ndjson links have probably expired, so export a fresh one from Platform."
        )


if __name__ == "__main__":
    main()
