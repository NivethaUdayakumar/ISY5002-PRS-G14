from fastapi import FastAPI, APIRouter, HTTPException, Query
from fastapi.responses import Response
from constants.file_paths import FilePaths, CameraFilePaths
from services.detection_service import DEFAULT_CONFIDENCE, detect_and_annotate, get_last_detections
import cv2


router = APIRouter(
    prefix="",
    tags=[""]
)

@router.get("/frame")
def get_frame(
    camera_id: str,
    offset: float = Query(..., ge=0),
    detect: bool = True,
    confidence: float = Query(DEFAULT_CONFIDENCE, ge=0.0, le=1.0),
):
    camera_file_path = CameraFilePaths.get(camera_id)

    if camera_file_path is None:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown camera_id '{camera_id}'"
        )

    cap = cv2.VideoCapture(camera_file_path)

    if not cap.isOpened():
        raise HTTPException(
            status_code=500,
            detail="Unable to open video"
        )

    try:
        # offset is in seconds
        cap.set(cv2.CAP_PROP_POS_MSEC, offset * 1000)

        success, frame = cap.read()

        if not success:
            raise HTTPException(
                status_code=404,
                detail="Frame not found"
            )

        if detect:
            frame, _ = detect_and_annotate(frame, camera_id, offset, confidence)

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

    finally:
        cap.release()


@router.get("/detections")
def get_detections(camera_id: str):
    """Returns the detections found in the most recently served /frame for
    this camera, without re-running inference."""
    return get_last_detections(camera_id)