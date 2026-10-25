from fastapi import FastAPI, APIRouter, HTTPException, Query
from fastapi.responses import Response
from constants.file_paths import FilePaths, CameraFilePaths
from services.detection_service_2 import detect_and_annotate, detect_and_annotate_batch
from services.video_service import read_frame
from concurrent.futures import ThreadPoolExecutor
import base64
import cv2


router = APIRouter(
    prefix="",
    tags=[""]
)

CONFIDENCE = 0.45


@router.get("/frame")
def get_frame(
    camera_id: str,
    offset: float = Query(..., ge=0),
    detect: bool = True
):
    if camera_id not in CameraFilePaths:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown camera_id '{camera_id}'"
        )

    frame = read_frame(camera_id, offset)

    if frame is None:
        raise HTTPException(
            status_code=404,
            detail="Frame not found"
        )

    if detect:
        frame = detect_and_annotate(frame, camera_id, CONFIDENCE)

    success, buffer = cv2.imencode(".jpg", frame)

    if not success:
        raise HTTPException(
            status_code=500,
            detail="Unable to encode frame"
        )

    return Response(
        content=buffer.tobytes(),
        media_type="image/jpeg"
    )


@router.get("/frames")
def get_frames(
    camera_ids: str,
    offset: float = Query(..., ge=0),
    detect: bool = True
):
    """Returns annotated frames for several cameras in one call, running
    detection on all of them as a single batch.

    `camera_ids` is comma-separated, e.g. "camera_01,camera_02". The response maps
    each camera_id to a base64 JPEG data URL, or null if its frame couldn't be read."""
    camera_ids = [camera_id.strip() for camera_id in camera_ids.split(",") if camera_id.strip()]

    unknown = [camera_id for camera_id in camera_ids if camera_id not in CameraFilePaths]
    if unknown:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown camera_id(s) {unknown}"
        )

    # Each camera has its own video reader, so read them in parallel.
    with ThreadPoolExecutor(max_workers=max(1, len(camera_ids))) as executor:
        frames = dict(zip(
            camera_ids,
            executor.map(lambda camera_id: read_frame(camera_id, offset), camera_ids)
        ))
    readable_ids = [camera_id for camera_id, frame in frames.items() if frame is not None]

    if detect:
        annotated = detect_and_annotate_batch([frames[camera_id] for camera_id in readable_ids], CONFIDENCE)
        frames.update(zip(readable_ids, annotated))

    result = {}
    for camera_id, frame in frames.items():
        result[camera_id] = None
        if frame is None:
            continue

        success, buffer = cv2.imencode(".jpg", frame)
        if success:
            result[camera_id] = "data:image/jpeg;base64," + base64.b64encode(buffer.tobytes()).decode("ascii")

    return result
