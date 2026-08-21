"""Downloads wildlife images from iNaturalist and builds a YOLO dataset.

iNaturalist only gives whole-image species labels, no bounding boxes. This
script fakes them: it runs the existing yolov8n.pt on each image, keeps its
best box, and re-labels it with the *queried* species (weak supervision,
not real annotation — spot-check wildlife_dataset/raw_labels/ before
training). Falls back to a full-image box when the detector finds nothing.

Run with --help for options.
"""

import argparse
import logging
import random
import shutil
import sys
import time
from pathlib import Path

import requests
import yaml
from PIL import Image
from tqdm import tqdm

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"

logger = logging.getLogger("download_dataset")


def load_config(path):
    with open(path) as f:
        return yaml.safe_load(f)


def setup_logging(dataset_root):
    dataset_root.mkdir(parents=True, exist_ok=True)
    log_path = dataset_root / "download_dataset.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler(log_path), logging.StreamHandler(sys.stdout)],
    )


class RateLimiter:
    """Rate-limits the iNaturalist API only; S3 photo downloads aren't limited."""

    def __init__(self, requests_per_minute):
        self.min_interval = 60.0 / max(requests_per_minute, 1)
        self._last_call = 0.0

    def wait(self):
        elapsed = time.monotonic() - self._last_call
        remaining = self.min_interval - elapsed
        if remaining > 0:
            time.sleep(remaining)
        self._last_call = time.monotonic()


def fetch_observations(session, rate_limiter, api_base_url, species_query, quality_grade, per_page, page):
    rate_limiter.wait()
    resp = session.get(
        f"{api_base_url}/observations",
        params={
            "taxon_name": species_query,
            "quality_grade": quality_grade,
            "photos": "true",
            "per_page": per_page,
            "page": page,
            "order_by": "created_at",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def iter_species_photos(session, rate_limiter, api_base_url, species, filters, max_images):
    seen_photo_ids = set()
    per_page = 200
    # iNaturalist caps pagination at 10,000 results.
    max_page = 10_000 // per_page
    allowed_licenses = {code.lower() for code in filters["license"]}

    for query_name in species["common_names"]:
        page = 1
        while len(seen_photo_ids) < max_images and page <= max_page:
            try:
                data = fetch_observations(
                    session, rate_limiter, api_base_url, query_name,
                    filters["quality_grade"], per_page, page,
                )
            except requests.RequestException as exc:
                logger.warning("iNaturalist request failed for '%s' page %d: %s", query_name, page, exc)
                break

            results = data.get("results", [])
            if not results:
                break

            for obs in results:
                for photo in obs.get("photos", []):
                    if photo["id"] in seen_photo_ids:
                        continue
                    license_code = (photo.get("license_code") or "").lower()
                    if license_code not in allowed_licenses:
                        continue
                    dims = photo.get("original_dimensions") or {}
                    if min(dims.get("width", 0), dims.get("height", 0)) < filters["min_resolution"]:
                        continue
                    seen_photo_ids.add(photo["id"])
                    yield obs["id"], photo
                    if len(seen_photo_ids) >= max_images:
                        break
                if len(seen_photo_ids) >= max_images:
                    break

            if len(results) < per_page:
                break
            page += 1

        if len(seen_photo_ids) >= max_images:
            break


def original_photo_url(thumbnail_url):
    return thumbnail_url.replace("square.jpg", "original.jpg").replace("square.jpeg", "original.jpeg")


def download_image(session, url, dest_path, retries=3):
    for attempt in range(1, retries + 1):
        try:
            resp = session.get(url, timeout=30)
            resp.raise_for_status()
            dest_path.write_bytes(resp.content)
            return True
        except requests.RequestException as exc:
            logger.warning("Download failed (attempt %d/%d) %s: %s", attempt, retries, url, exc)
            time.sleep(1.5 * attempt)
    return False


def validate_image(path, min_resolution):
    try:
        with Image.open(path) as img:
            img.verify()
        with Image.open(path) as img:  # verify() closes the handle; reopen for size
            width, height = img.size
        return min(width, height) >= min_resolution
    except Exception:
        return False


def download_species(session, rate_limiter, config, species, images_root):
    filters = config["dataset"]["filters"]
    max_images = config["dataset"]["images_per_species_max"]
    min_images = config["dataset"]["images_per_species_min"]

    species_dir = images_root / species["name"]
    species_dir.mkdir(parents=True, exist_ok=True)

    existing = {p.stem for p in species_dir.glob("*.jpg")}
    downloaded = len(existing)
    if downloaded >= min_images:
        logger.info("%s: already have %d images, skipping download", species["name"], downloaded)
        return downloaded

    photo_iter = iter_species_photos(
        session, rate_limiter, config["dataset"]["api_base_url"], species, filters, max_images
    )

    pbar = tqdm(total=max_images, initial=downloaded, desc=species["name"])
    for _obs_id, photo in photo_iter:
        filename = f"{species['name']}_{photo['id']}"
        if filename in existing:
            continue

        dest = species_dir / f"{filename}.jpg"
        if download_image(session, original_photo_url(photo["url"]), dest):
            if validate_image(dest, filters["min_resolution"]):
                existing.add(filename)
                downloaded += 1
                pbar.update(1)
            else:
                dest.unlink(missing_ok=True)
                logger.warning("Rejected corrupt/low-res image: %s", photo["url"])

        if downloaded >= max_images:
            break
    pbar.close()

    if downloaded < min_images:
        logger.warning(
            "%s: only found %d/%d minimum images from iNaturalist", species["name"], downloaded, min_images
        )
    return downloaded


def build_pseudo_labels(images_root, labels_root, class_names, fallback_full_image):
    from ultralytics import YOLO  # heavy import, not needed for --dry-run

    detector = YOLO(str(REPO_ROOT / "ai-applications" / "yolov8n.pt"))
    class_index = {name: i for i, name in enumerate(class_names)}

    for species_dir in sorted(p for p in images_root.iterdir() if p.is_dir()):
        species = species_dir.name
        if species not in class_index:
            continue

        label_dir = labels_root / species
        label_dir.mkdir(parents=True, exist_ok=True)
        class_id = class_index[species]

        image_paths = sorted(species_dir.glob("*.jpg"))
        for image_path in tqdm(image_paths, desc=f"labeling {species}"):
            label_path = label_dir / f"{image_path.stem}.txt"
            if label_path.exists():
                continue

            with Image.open(image_path) as img:
                width, height = img.size

            result = detector.predict(str(image_path), verbose=False)[0]
            box = None
            if len(result.boxes):
                best = max(result.boxes, key=lambda b: float(b.conf[0]))
                box = tuple(float(v) for v in best.xyxy[0])
            elif fallback_full_image:
                margin_x, margin_y = width * 0.05, height * 0.05
                box = (margin_x, margin_y, width - margin_x, height - margin_y)

            if box is None:
                continue

            x1, y1, x2, y2 = box
            x_center = ((x1 + x2) / 2) / width
            y_center = ((y1 + y2) / 2) / height
            box_w = (x2 - x1) / width
            box_h = (y2 - y1) / height
            label_path.write_text(f"{class_id} {x_center:.6f} {y_center:.6f} {box_w:.6f} {box_h:.6f}\n")


def split_dataset(images_root, labels_root, dataset_root, class_names, split_ratios, seed=42):
    random.seed(seed)
    train_ratio, val_ratio, _test_ratio = split_ratios

    for split in ("train", "val", "test"):
        (dataset_root / "images" / split).mkdir(parents=True, exist_ok=True)
        (dataset_root / "labels" / split).mkdir(parents=True, exist_ok=True)

    for species in class_names:
        label_dir = labels_root / species
        if not label_dir.exists():
            continue

        stems = sorted(p.stem for p in label_dir.glob("*.txt"))
        random.shuffle(stems)

        n = len(stems)
        n_train = int(n * train_ratio)
        n_val = int(n * val_ratio)
        splits = {
            "train": stems[:n_train],
            "val": stems[n_train:n_train + n_val],
            "test": stems[n_train + n_val:],
        }

        for split, split_stems in splits.items():
            for stem in split_stems:
                src_image = images_root / species / f"{stem}.jpg"
                src_label = label_dir / f"{stem}.txt"
                if not src_image.exists():
                    continue
                shutil.copy2(src_image, dataset_root / "images" / split / f"{stem}.jpg")
                shutil.copy2(src_label, dataset_root / "labels" / split / f"{stem}.txt")

        logger.info(
            "%s: train=%d val=%d test=%d", species, len(splits["train"]), len(splits["val"]), len(splits["test"])
        )


def write_dataset_yaml(dataset_root, class_names):
    dataset_yaml = {
        "path": str(dataset_root.resolve()),
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "nc": len(class_names),
        "names": class_names,
    }
    out_path = dataset_root / "dataset.yaml"
    with open(out_path, "w") as f:
        yaml.safe_dump(dataset_yaml, f, sort_keys=False)
    logger.info("Wrote %s", out_path)
    return out_path


def parse_args():
    parser = argparse.ArgumentParser(description="Download a wildlife dataset from iNaturalist and build YOLO labels.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--species", type=str, default=None, help="Comma-separated species names to limit the run to, e.g. 'lion,zebra'")
    parser.add_argument("--min-images", type=int, default=None, help="Override dataset.images_per_species_min")
    parser.add_argument("--max-images", type=int, default=None, help="Override dataset.images_per_species_max")
    parser.add_argument("--skip-download", action="store_true", help="Only (re)generate pseudo-labels and the split for already-downloaded images")
    parser.add_argument("--skip-labels", action="store_true", help="Only download images; skip pseudo-labeling and splitting")
    parser.add_argument("--dry-run", action="store_true", help="Print the planned species/queries without making network requests")
    return parser.parse_args()


def main():
    args = parse_args()
    config = load_config(args.config)

    dataset_root = (REPO_ROOT / config["dataset"]["download_path"]).resolve()

    if args.min_images:
        config["dataset"]["images_per_species_min"] = args.min_images
    if args.max_images:
        config["dataset"]["images_per_species_max"] = args.max_images

    species_list = config["dataset"]["species"]
    if args.species:
        wanted = {s.strip() for s in args.species.split(",")}
        species_list = [s for s in species_list if s["name"] in wanted]
        if not species_list:
            print(f"No species in config matched --species {args.species}", file=sys.stderr)
            sys.exit(1)

    if args.dry_run:
        for s in species_list:
            print(f"{s['name']}: {s['common_names']}")
        return

    setup_logging(dataset_root)
    class_names = [s["name"] for s in species_list]
    images_root = dataset_root / "raw_images"
    labels_root = dataset_root / "raw_labels"

    if not args.skip_download:
        session = requests.Session()
        session.headers.update({"User-Agent": "WildGuard-DatasetDownloader/1.0"})
        rate_limiter = RateLimiter(config["dataset"]["requests_per_minute"])

        for species in species_list:
            try:
                download_species(session, rate_limiter, config, species, images_root)
            except Exception:
                logger.exception("Failed downloading %s, continuing with next species", species["name"])

    if not args.skip_labels:
        build_pseudo_labels(images_root, labels_root, class_names, config["dataset"]["pseudo_label_fallback_full_image"])
        split_dataset(images_root, labels_root, dataset_root, class_names, config["dataset"]["train_val_test_split"])
        write_dataset_yaml(dataset_root, class_names)

    logger.info("Done.")


if __name__ == "__main__":
    main()
