from fastapi import FastAPI, APIRouter, HTTPException, Query
from fastapi.responses import Response
from constants.file_paths import FilePaths, CameraFilePaths
import cv2


router = APIRouter(
    prefix="",
    tags=[""]
)

@router.get("/frame")
def get_frame(camera_id: str, offset: float = Query(..., ge=0)):
    camera_file_path = CameraFilePaths.get(camera_id)
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