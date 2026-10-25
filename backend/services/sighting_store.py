import json
import math
import re
import struct
from datetime import datetime, timezone
from io import BytesIO
from threading import RLock

import cv2
from PIL import Image

from constants.file_paths import BASE_DIR

SIGHTINGS_DIR = BASE_DIR / "data" / "sightings"
LEGACY_SIGHTINGS_FILE = SIGHTINGS_DIR / "sightings.json"
SPECIES_FILE = SIGHTINGS_DIR / "species.json"
ENDANGERED_DIR = SIGHTINGS_DIR / "endangered"
DEDUPLICATION_SECONDS = 15
MATCH_MIN_OVERLAP = 0.25  # box IoU above which two detections are the same animal
MATCH_MAX_CENTRE_DISTANCE = 0.5  # ...or centres closer than this fraction of the box size
EXIF_IMAGE_DESCRIPTION = 0x010E
EXIF_DATETIME = 0x0132
EXIF_IFD = 0x8769
EXIF_DATETIME_ORIGINAL = 0x9003
EXIF_DATETIME_FORMAT = "%Y:%m:%d %H:%M:%S"
APP1_MARKER = bytes([0xFF, 0xE1])
EXIF_HEADER = b"Exif" + bytes(2)
_lock = RLock()
_index = {}  # sighting id -> record, mirrors the EXIF of the images on disk
_paths = {}  # sighting id -> path of its image inside its species folder
_copies = {}  # sighting id -> path of its copy in the endangered folder
_index_loaded = False

# Model labels that are not part of the dataset; detections of these are not recorded.
IGNORED_SPECIES = {"donkey"}

# Species the dataset contains, seeded into species.json: name -> (class, endangered / protected).
SEED_SPECIES = {
    "Rhino": ("Mammals", True),
    "Zebra": ("Mammals", False),
    "Elephant": ("Mammals", False),
    "Okapi": ("Mammals", True),
    "Buffalo": ("Mammals", False),
    "Leopard": ("Mammals", True),
    "Cheetah": ("Mammals", True),
}

# Layout under SIGHTINGS_DIR:
#   <species>/<camera_id>_<timestamp>.jpg            one folder per species
#   endangered/<species>_<camera_id>_<timestamp>.jpg  copy of every endangered sighting (for notifications)
# A sighting is one JPEG. Its metadata (camera, species, confidence,
# first/last seen, ...) lives in the image's EXIF, so the images are the source of truth.


def _build_exif(record):
    exif = Image.Exif()
    exif[EXIF_IMAGE_DESCRIPTION] = json.dumps(record)
    last_seen = datetime.fromisoformat(record["lastSeen"]).astimezone().strftime(EXIF_DATETIME_FORMAT)
    exif[EXIF_DATETIME] = last_seen
    exif.get_ifd(EXIF_IFD)[EXIF_DATETIME_ORIGINAL] = datetime.fromisoformat(record["firstSeen"]).astimezone().strftime(EXIF_DATETIME_FORMAT)
    return exif.tobytes()


def _with_exif(jpeg_bytes, record):
    """Returns the JPEG bytes with their EXIF segment replaced, without re-encoding the image."""
    payload = _build_exif(record)
    segment = APP1_MARKER + struct.pack(">H", len(payload) + 2) + payload
    out = [jpeg_bytes[:2]]
    pos = 2
    while pos + 4 <= len(jpeg_bytes) and jpeg_bytes[pos] == 0xFF and jpeg_bytes[pos + 1] != 0xDA:
        length = struct.unpack(">H", jpeg_bytes[pos + 2:pos + 4])[0]
        body = jpeg_bytes[pos:pos + 2 + length]
        if not (jpeg_bytes[pos + 1] == 0xE1 and body[4:10] == EXIF_HEADER):
            out.append(body)
        pos += 2 + length
    out.append(segment)
    out.append(jpeg_bytes[pos:])
    return b"".join(out)


def _slug(name):
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "unknown"


def _species_dir(species):
    return SIGHTINGS_DIR / _slug(species)


def _image_path(record):
    return _species_dir(record["species"]) / f"{record['id']}.jpg"


def _endangered_path(record):
    return ENDANGERED_DIR / f"{_slug(record['species'])}_{record['id']}.jpg"


def _ensure_folders(species_names):
    ENDANGERED_DIR.mkdir(parents=True, exist_ok=True)
    for name in species_names:
        _species_dir(name).mkdir(parents=True, exist_ok=True)


def _save(record, jpeg_bytes):
    """Writes the sighting image with its EXIF into its species folder (moving it if the
    species changed) and keeps its copy in the endangered folder in step."""
    sighting_id = record["id"]
    path = _image_path(record)
    record["file"] = path.relative_to(SIGHTINGS_DIR).as_posix()
    data = _with_exif(jpeg_bytes, record)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    previous = _paths.get(sighting_id)
    if previous and previous != path:
        previous.unlink(missing_ok=True)
    _paths[sighting_id] = path

    copy = _copies.get(sighting_id)
    if record.get("endangered"):
        target = _endangered_path(record)
        ENDANGERED_DIR.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        if copy and copy != target:
            copy.unlink(missing_ok=True)
        _copies[sighting_id] = target
    elif copy:
        copy.unlink(missing_ok=True)
        del _copies[sighting_id]

    _index[sighting_id] = record


def _read_record(path):
    try:
        with Image.open(path) as image:
            return json.loads(image.getexif()[EXIF_IMAGE_DESCRIPTION])
    except (OSError, KeyError, ValueError):
        return None


def _load_index():
    """Reads the EXIF of every image once; afterwards the index is kept in step with the writes."""
    global _index_loaded
    if _index_loaded:
        return
    for path in SIGHTINGS_DIR.glob("*/*.jpg") if SIGHTINGS_DIR.exists() else []:
        record = _read_record(path)
        if not record:
            continue
        if path.parent == ENDANGERED_DIR:
            _copies[record["id"]] = path
        else:
            _index[record["id"]] = record
            _paths[record["id"]] = path
    _index_loaded = True


def reset_runtime_sightings():
    """Deletes every sighting image (species folders and the endangered folder); the folders stay."""
    global _index_loaded
    SIGHTINGS_DIR.mkdir(parents=True, exist_ok=True)
    _index.clear()
    _paths.clear()
    _copies.clear()
    _index_loaded = True
    LEGACY_SIGHTINGS_FILE.unlink(missing_ok=True)
    for path in [*SIGHTINGS_DIR.glob("*.jpg"), *SIGHTINGS_DIR.glob("*/*.jpg")]:
        path.unlink()
    _ensure_folders(item["name"] for item in _read_species())


def _box_overlap(a, b):
    """Intersection over union of two [x1, y1, x2, y2] boxes."""
    width = min(a[2], b[2]) - max(a[0], b[0])
    height = min(a[3], b[3]) - max(a[1], b[1])
    if width <= 0 or height <= 0:
        return 0.0
    intersection = width * height
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - intersection
    return intersection / union if union else 0.0


def _same_animal(old_box, new_box):
    """The same animal moves a little between frames; a different animal sits elsewhere."""
    if _box_overlap(old_box, new_box) >= MATCH_MIN_OVERLAP:
        return True
    centre_distance = math.hypot(
        (old_box[0] + old_box[2]) / 2 - (new_box[0] + new_box[2]) / 2,
        (old_box[1] + old_box[3]) / 2 - (new_box[1] + new_box[3]) / 2,
    )
    size = max(old_box[2] - old_box[0], old_box[3] - old_box[1], new_box[2] - new_box[0], new_box[3] - new_box[1])
    return centre_distance < MATCH_MAX_CENTRE_DISTANCE * size


def _match_sighting(candidates, claimed, detection):
    """Finds the recent sighting of the same species that this detection continues, if any."""
    best, best_overlap = None, -1.0
    for item in candidates:
        if item["id"] in claimed or item["species"].lower() != detection["species"].lower():
            continue
        if not _same_animal(item["bbox"], detection["bbox"]):
            continue
        overlap = _box_overlap(item["bbox"], detection["bbox"])
        if overlap > best_overlap:
            best, best_overlap = item, overlap
    return best


def _new_sighting_id(camera_id, moment):
    """Sightings are labelled <camera_id>_<timestamp>, e.g. camera_01_20261025T150102123456Z."""
    base = f"{camera_id}_{moment.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}"
    sighting_id, suffix = base, 1
    while sighting_id in _index:
        suffix += 1
        sighting_id = f"{base}_{suffix}"
    return sighting_id


def record_detections(camera_id, detections, frame, offset):
    detections = [item for item in detections if item["species"].lower() not in IGNORED_SPECIES]
    if not detections:
        return

    SIGHTINGS_DIR.mkdir(parents=True, exist_ok=True)
    with _lock:
        _load_index()
        now = datetime.now(timezone.utc)
        recent_sightings = [
            item for item in _index.values()
            if item["cameraId"] == camera_id
            and (now - datetime.fromisoformat(item["lastSeen"])).total_seconds() < DEDUPLICATION_SECONDS
        ]
        claimed = set()  # a sighting can be matched by at most one detection per frame
        for detection in detections:
            recent = _match_sighting(recent_sightings, claimed, detection)
            if recent:
                claimed.add(recent["id"])
                recent.update({
                    "lastSeen": now.isoformat(),
                    "confidence": detection["confidence"],
                    "bbox": detection["bbox"],
                    "offset": offset,
                })
                _save(recent, _paths[recent["id"]].read_bytes())
                continue

            success, buffer = cv2.imencode(".jpg", detection["crop"])
            if not success:
                continue
            entry = add_species(detection["species"])
            sighting_id = _new_sighting_id(camera_id, now)
            record = {
                "id": sighting_id,
                "cameraId": camera_id,
                "species": entry["name"],
                "class": entry["class"],
                "confidence": detection["confidence"],
                "bbox": detection["bbox"],
                "offset": offset,
                "firstSeen": now.isoformat(),
                "lastSeen": now.isoformat(),
                "imageUrl": f"/sightings/{sighting_id}/image",
                "endangered": entry["endangered"],
            }
            _save(record, buffer.tobytes())
            claimed.add(sighting_id)
            recent_sightings.append(record)


def get_sightings():
    """Reads every sighting from its image's EXIF metadata, oldest first."""
    with _lock:
        _load_index()
        return sorted(_index.values(), key=lambda item: item["firstSeen"])


def get_sighting_image(sighting_id):
    with _lock:
        _load_index()
        path = _paths.get(sighting_id)
    return path if path and path.is_file() else None


def update_sighting(sighting_id, changes):
    allowed = {"species", "class", "endangered"}
    with _lock:
        _load_index()
        record = _index.get(sighting_id)
        if record is None:
            return None
        record = {**record, **{key: value for key, value in changes.items() if key in allowed}}
        entry = add_species(record["species"], record.get("class", "Unknown"), record.get("endangered", False))
        record["species"] = entry["name"]
        _save(record, _paths[sighting_id].read_bytes())
        return record


def delete_sighting(sighting_id):
    with _lock:
        _load_index()
        path = _paths.pop(sighting_id, None)
        if path is None:
            return False
        path.unlink(missing_ok=True)
        copy = _copies.pop(sighting_id, None)
        if copy:
            copy.unlink(missing_ok=True)
        _index.pop(sighting_id, None)
        return True


def get_collections():
    """Lists each folder under SIGHTINGS_DIR with the number of files it holds and its most
    recently modified image, largest first. imageUrl is None for folders with no images."""
    if not SIGHTINGS_DIR.exists():
        return []
    collections = []
    for folder in SIGHTINGS_DIR.iterdir():
        if not folder.is_dir():
            continue
        files = [path for path in folder.iterdir() if path.is_file()]
        images = [path for path in files if path.suffix.lower() in (".jpg", ".jpeg", ".png")]
        latest = max(images, key=lambda path: path.stat().st_mtime, default=None)
        collections.append({
            "name": folder.name,
            "count": len(files),
            "imageUrl": f"/collections/{folder.name}/{latest.name}" if latest else None,
        })
    return sorted(collections, key=lambda item: (-item["count"], item["name"]))


def get_collection_image(folder_name, file_name):
    """Resolves an image inside a collection folder, refusing paths that escape SIGHTINGS_DIR."""
    path = (SIGHTINGS_DIR / folder_name / file_name).resolve()
    if path.parent.parent != SIGHTINGS_DIR.resolve() or not path.is_file():
        return None
    return path


def get_species():
    with _lock:
        return _read_species()


def _read_species():
    return json.loads(SPECIES_FILE.read_text(encoding="utf-8")) if SPECIES_FILE.exists() else []


def add_species(name, species_class="Unknown", endangered=False):
    """Adds a species to the catalog in species.json unless it already exists."""
    name = name.strip()
    if not name:
        return None
    with _lock:
        return _add_species_locked(name, species_class, endangered)


def _add_species_locked(name, species_class, endangered):
    SIGHTINGS_DIR.mkdir(parents=True, exist_ok=True)
    catalog = _read_species()
    existing = next((item for item in catalog if item["name"].lower() == name.lower()), None)
    if existing:
        return existing
    entry = {"name": name, "class": species_class, "endangered": bool(endangered)}
    catalog.append(entry)
    catalog.sort(key=lambda item: item["name"].lower())
    SPECIES_FILE.write_text(json.dumps(catalog, indent=2), encoding="utf-8")
    _ensure_folders([name])
    return entry


def seed_species():
    """Makes sure the dataset's species are in species.json with their class."""
    with _lock:
        SIGHTINGS_DIR.mkdir(parents=True, exist_ok=True)
        catalog = _read_species()
        by_name = {item["name"].lower(): item for item in catalog}
        for name, (species_class, endangered) in SEED_SPECIES.items():
            entry = by_name.get(name.lower())
            if entry is None:
                catalog.append({"name": name, "class": species_class, "endangered": endangered})
            else:
                entry.update({"name": name, "class": species_class, "endangered": endangered})
        catalog.sort(key=lambda item: item["name"].lower())
        SPECIES_FILE.write_text(json.dumps(catalog, indent=2), encoding="utf-8")
        _ensure_folders(item["name"] for item in catalog)
