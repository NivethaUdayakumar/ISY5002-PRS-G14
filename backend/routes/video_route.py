from fastapi import FastAPI, APIRouter, Body, HTTPException, Query
from fastapi.responses import FileResponse, Response
from constants.file_paths import FilePaths, CameraFilePaths
from services.detection_service_2 import detect_and_annotate, detect_batch_with_metadata
from services.sighting_store import add_species, delete_sighting, get_collection_image, get_collections, get_species, get_sighting_image, get_sightings, record_detections, update_sighting
from services.video_service import read_frame
from concurrent.futures import ThreadPoolExecutor
import base64
import cv2


router = APIRouter(
    prefix="",
    tags=[""]
)

CONFIDENCE = 0.45
PREVIEW_MAX_WIDTH = 854
PREVIEW_JPEG_QUALITY = 75


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
        input_frames = [frames[camera_id] for camera_id in readable_ids]
        annotated, detections = detect_batch_with_metadata(input_frames, CONFIDENCE)
        frames.update(zip(readable_ids, annotated))
        for camera_id, frame_detections in zip(readable_ids, detections):
            record_detections(camera_id, frame_detections, frames[camera_id], offset)

    result = {}
    for camera_id, frame in frames.items():
        result[camera_id] = None
        if frame is None:
            continue

        # Detection and sighting crops use the full-resolution frame; the live preview is downscaled.
        height, width = frame.shape[:2]
        if width > PREVIEW_MAX_WIDTH:
            frame = cv2.resize(frame, (PREVIEW_MAX_WIDTH, round(height * PREVIEW_MAX_WIDTH / width)), interpolation=cv2.INTER_AREA)
        success, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, PREVIEW_JPEG_QUALITY])
        if success:
            result[camera_id] = "data:image/jpeg;base64," + base64.b64encode(buffer.tobytes()).decode("ascii")

    return result


@router.get("/sightings")
def list_sightings():
    return get_sightings()


@router.get("/sightings/{sighting_id}/image")
def sighting_image(sighting_id: str):
    image_path = get_sighting_image(sighting_id)
    if image_path is None:
        raise HTTPException(status_code=404, detail="Sighting image not found")
    return FileResponse(image_path, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=5"})


@router.patch("/sightings/{sighting_id}")
def patch_sighting(sighting_id: str, changes: dict = Body(...)):
    record = update_sighting(sighting_id, changes)
    if record is None:
        raise HTTPException(status_code=404, detail="Sighting not found")
    return record


@router.delete("/sightings/{sighting_id}")
def remove_sighting(sighting_id: str):
    if not delete_sighting(sighting_id):
        raise HTTPException(status_code=404, detail="Sighting not found")
    return {"deleted": sighting_id}


@router.get("/species")
def list_species():
    return get_species()


@router.post("/species")
def create_species(entry: dict = Body(...)):
    name = str(entry.get("name", "")).strip()
    if not name:
        raise HTTPException(status_code=422, detail="Species name is required")
    return add_species(name, entry.get("class", "Unknown"), entry.get("endangered", False))


@router.get("/collections")
def list_collections():
    return get_collections()


@router.get("/collections/{folder_name}/{file_name}")
def collection_image(folder_name: str, file_name: str):
    image_path = get_collection_image(folder_name, file_name)
    if image_path is None:
        raise HTTPException(status_code=404, detail="Collection image not found")
    return FileResponse(image_path)
