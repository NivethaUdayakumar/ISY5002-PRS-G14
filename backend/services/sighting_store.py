import json
import struct
from datetime import datetime, timezone
from io import BytesIO
from threading import RLock
from uuid import uuid4

import cv2
from PIL import Image

from constants.file_paths import BASE_DIR

SIGHTINGS_DIR = BASE_DIR / "data" / "sightings"
LEGACY_SIGHTINGS_FILE = SIGHTINGS_DIR / "sightings.json"
SPECIES_FILE = SIGHTINGS_DIR / "species.json"
DEDUPLICATION_SECONDS = 15
EXIF_IMAGE_DESCRIPTION = 0x010E
EXIF_DATETIME = 0x0132
EXIF_IFD = 0x8769
EXIF_DATETIME_ORIGINAL = 0x9003
EXIF_DATETIME_FORMAT = "%Y:%m:%d %H:%M:%S"
APP1_MARKER = bytes([0xFF, 0xE1])
EXIF_HEADER = b"Exif" + bytes(2)
_lock = RLock()
_index = {}  # sighting id -> record, mirrors the EXIF of the images on disk
_index_loaded = False

# Species the dataset contains, seeded into species.json: name -> (class, endangered / protected).
SEED_SPECIES = {
    "Rhino": ("Mammals", True),
    "Zebra": ("Mammals", False),
    "Elephant": ("Mammals", True),
    "Okapi": ("Mammals", True),
    "Buffalo": ("Mammals", False),
    "Leopard": ("Mammals", True),
    "Cheetah": ("Mammals", True),
}

# A sighting is one JPEG in SIGHTINGS_DIR. Its metadata (camera, species, confidence,
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


def _image_path(sighting_id):
    return SIGHTINGS_DIR / f"{sighting_id}.jpg"


def _write_record(record):
    path = _image_path(record["id"])
    path.write_bytes(_with_exif(path.read_bytes(), record))
    _index[record["id"]] = record


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
    for path in SIGHTINGS_DIR.glob("*.jpg") if SIGHTINGS_DIR.exists() else []:
        record = _read_record(path)
        if record:
            _index[record["id"]] = record
    _index_loaded = True


def reset_runtime_sightings():
    SIGHTINGS_DIR.mkdir(parents=True, exist_ok=True)
    global _index_loaded
    _index.clear()
    _index_loaded = True
    for path in SIGHTINGS_DIR.iterdir():
        if path.is_file() and (path == LEGACY_SIGHTINGS_FILE or path.suffix.lower() in {".jpg", ".jpeg"}):
            path.unlink()


def record_detections(camera_id, detections, frame, offset):
    if not detections:
        return

    SIGHTINGS_DIR.mkdir(parents=True, exist_ok=True)
    with _lock:
        _load_index()
        records = list(_index.values())
        now = datetime.now(timezone.utc)
        for detection in detections:
            recent = next(
                (
                    item for item in reversed(records)
                    if item["cameraId"] == camera_id
                    and item["species"].lower() == detection["species"].lower()
                    and (now - datetime.fromisoformat(item["lastSeen"])).total_seconds() < DEDUPLICATION_SECONDS
                ),
                None,
            )
            if recent:
                recent.update({
                    "lastSeen": now.isoformat(),
                    "confidence": detection["confidence"],
                    "bbox": detection["bbox"],
                    "offset": offset,
                })
                _write_record(recent)
                continue

            success, buffer = cv2.imencode(".jpg", detection["crop"])
            if not success:
                continue
            sighting_id = uuid4().hex
            entry = add_species(detection["species"])
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
            _image_path(sighting_id).write_bytes(_with_exif(buffer.tobytes(), record))
            _index[sighting_id] = record
            records.append(record)


def get_sightings():
    """Reads every sighting from its image's EXIF metadata, oldest first."""
    with _lock:
        _load_index()
        return sorted(_index.values(), key=lambda item: item["firstSeen"])


def get_sighting_image(sighting_id):
    path = _image_path(sighting_id)
    return path if path.is_file() and path.parent == SIGHTINGS_DIR else None


def update_sighting(sighting_id, changes):
    allowed = {"species", "class", "endangered"}
    with _lock:
        _load_index()
        record = _index.get(sighting_id)
        if record is None:
            return None
        record = {**record, **{key: value for key, value in changes.items() if key in allowed}}
        _write_record(record)
        add_species(record["species"], record.get("class", "Unknown"), record.get("endangered", False))
        return record


def delete_sighting(sighting_id):
    with _lock:
        image = get_sighting_image(sighting_id)
        if image is None:
            return False
        image.unlink()
        _index.pop(sighting_id, None)
        return True


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
