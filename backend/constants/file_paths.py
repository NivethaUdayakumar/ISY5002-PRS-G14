
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class FilePaths:
    CAMERA_1 = str(BASE_DIR / "data" / "datasets" / "location-a" / "camera-01.mp4")
    UPLOAD_FOLDER = "backend/uploads"