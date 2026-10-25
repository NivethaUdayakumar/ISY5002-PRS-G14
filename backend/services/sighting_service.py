import json
import shutil
import uuid
from datetime import datetime

import cv2
from PIL import Image

from constants.endanagered_species import ENDANGERED_SPECIES
from constants.file_paths import BASE_DIR, SIGHTINGS_DIR

# EXIF ImageDescription tag; holds the sighting metadata as JSON.
EXIF_IMAGE_DESCRIPTION = 0x010E


def clear_sightings():
    """Removes all saved sighting images and label folders."""
    shutil.rmtree(SIGHTINGS_DIR, ignore_errors=True)
    SIGHTINGS_DIR.mkdir(parents=True, exist_ok=True)


def save_sightings(frame, camera_id, labels):
    """Writes the BGR `frame` to data/sightings/<label>/<camera_id>_<datetime>.jpg for every
    detected label, creating the label folder if needed. Endangered species go
    under data/sightings/endangered/<label>/ instead. Each image's EXIF
    metadata stores its id, camera_id, species and image_path.

    Returns the metadata of the saved images."""
    image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    sightings = []

    for label in labels:
        label_dir = SIGHTINGS_DIR / label
        if label.lower() in ENDANGERED_SPECIES:
            label_dir = SIGHTINGS_DIR / "endangered" / label
        label_dir.mkdir(parents=True, exist_ok=True)

        sighting_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        image_path = label_dir / f"{camera_id}_{timestamp}.jpg"
        metadata = {
            "id": sighting_id,
            "camera_id": camera_id,
            "species": label,
            "image_path": image_path.relative_to(BASE_DIR).as_posix(),
        }

        exif = Image.Exif()
        exif[EXIF_IMAGE_DESCRIPTION] = json.dumps(metadata)
        image.save(image_path, "JPEG", exif=exif)
        sightings.append(metadata)

    return sightings
