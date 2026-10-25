
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SIGHTINGS_DIR = BASE_DIR / "data" / "sightings"

class FilePaths:
    CAMERA_1 = str(BASE_DIR / "data" / "live-cam" / "location-a" / "camera_01.mp4")
    CAMERA_2 = str(BASE_DIR / "data" / "live-cam" / "location-a" / "camera_02.mp4")
    CAMERA_3 = str(BASE_DIR / "data" / "live-cam" / "location-a" / "camera_03.mp4")
    CAMERA_4 = str(BASE_DIR / "data" / "live-cam" / "location-b" / "camera_04.mp4")
    CAMERA_5 = str(BASE_DIR / "data" / "live-cam" / "location-b" / "camera_05.mp4")
    CAMERA_6 = str(BASE_DIR / "data" / "live-cam" / "location-b" / "camera_06.mp4")


CameraFilePaths = {
    "camera_01": FilePaths.CAMERA_1,
    "camera_02": FilePaths.CAMERA_2,
    "camera_03": FilePaths.CAMERA_3,
    "camera_04": FilePaths.CAMERA_4,
    "camera_05": FilePaths.CAMERA_5,
    "camera_06": FilePaths.CAMERA_6,
}
    
   