
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class FilePaths:
    CAMERA_1 = str(BASE_DIR / "data" / "datasets" / "location-a" / "camera_01.mp4")
    CAMERA_2 = str(BASE_DIR / "data" / "datasets" / "location-a" / "camera_02.mp4")
    CAMERA_3 = str(BASE_DIR / "data" / "datasets" / "location-a" / "camera_03.mp4")
    CAMERA_4 = str(BASE_DIR / "data" / "datasets" / "location-b" / "camera_04.mp4")
    UPLOAD_FOLDER = "backend/uploads"


CameraFilePaths = {
    "camera_01": FilePaths.CAMERA_1,
    "camera_02": FilePaths.CAMERA_2,
    "camera_03": FilePaths.CAMERA_3,
    "camera_04": FilePaths.CAMERA_4,
}
    
   