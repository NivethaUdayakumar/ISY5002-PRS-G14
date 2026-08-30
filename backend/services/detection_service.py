import csv
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

import cv2
from ultralytics import YOLO

BASE_DIR = Path(__file__).resolve().parent.parent.parent
AI_DIR = BASE_DIR / "ai-applications"
CONFIG_PATH = AI_DIR / "config.yaml"
BASE_WEIGHTS = AI_DIR / "yolov8n.pt"

sys.path.insert(0, str(AI_DIR / "pipeline"))
from two_stage_detector import TwoStageDetector  # noqa: E402

logger = logging.getLogger("detection_service")

DEFAULT_CONFIDENCE = 0.5
LOG_PATH = BASE_DIR / "data" / "logs" / "detections.csv"
BOX_COLOR = (30, 200, 90)  # BGR

_pipeline = None
_base_model = None
_model_lock = Lock()

_last_detections = {}
_last_detections_lock = Lock()


def _load_pipeline():
    """Loads the two-stage detector+classifier pipeline, or None if it isn't trained yet."""
    global _pipeline
    if _pipeline is None:
        with _model_lock:
            if _pipeline is None:
                candidate = TwoStageDetector(CONFIG_PATH)
                try:
                    candidate.load_models()
                except FileNotFoundError:
                    logger.warning(
                        "No trained pipeline models found under config.yaml's pipeline section; "
                        "falling back to the base COCO model until model_train_code/main.py has been run"
                    )
                    return None
                _pipeline = candidate
    return _pipeline


def _load_base_model():
    global _base_model
    if _base_model is None:
        with _model_lock:
            if _base_model is None:
                _base_model = YOLO(str(BASE_WEIGHTS))
    return _base_model


def _log_detections(camera_id, offset, detections):
    if not detections:
        return

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    is_new_file = not LOG_PATH.exists()

    with open(LOG_PATH, "a", newline="") as f:
        writer = csv.writer(f)
        if is_new_file:
            writer.writerow(
                ["timestamp", "camera_id", "offset_s", "species", "confidence", "x1", "y1", "x2", "y2"]
            )
        timestamp = datetime.now(timezone.utc).isoformat()
        for det in detections:
            writer.writerow(
                [timestamp, camera_id, offset, det["species"], f'{det["confidence"]:.4f}', *det["box"]]
            )


def _draw_detection(frame, species, confidence, box):
    x1, y1, x2, y2 = box
    label = f"{species} {confidence:.0%}"

    cv2.rectangle(frame, (x1, y1), (x2, y2), BOX_COLOR, 2)

    (text_w, text_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
    label_top = max(0, y1 - text_h - 8)
    cv2.rectangle(frame, (x1, label_top), (x1 + text_w + 6, y1), BOX_COLOR, -1)
    cv2.putText(
        frame,
        label,
        (x1 + 3, max(text_h + 2, y1 - 5)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (10, 10, 10),
        1,
        cv2.LINE_AA,
    )


def detect_and_annotate(frame, camera_id, offset, confidence=DEFAULT_CONFIDENCE):
    """Runs inference on `frame` using the trained two-stage detector+classifier
    pipeline (falling back to the base COCO model if it isn't trained yet), draws
    boxes/labels in place, logs detection events, and returns (annotated_frame, detections)."""
    pipeline = _load_pipeline()

    detections = []
    if pipeline is not None:
        for det in pipeline.predict(frame):
            if det["confidence"] < confidence:
                continue
            x1, y1, x2, y2 = (int(v) for v in det["box"])
            detections.append(
                {"species": det["species"], "confidence": round(det["confidence"], 4), "box": [x1, y1, x2, y2]}
            )
    else:
        model = _load_base_model()
        results = model.predict(frame, conf=confidence, verbose=False)[0]
        for box in results.boxes:
            cls_id = int(box.cls[0])
            det_confidence = float(box.conf[0])
            x1, y1, x2, y2 = (int(v) for v in box.xyxy[0])
            detections.append(
                {
                    "species": model.names.get(cls_id, str(cls_id)),
                    "confidence": round(det_confidence, 4),
                    "box": [x1, y1, x2, y2],
                }
            )

    for det in detections:
        _draw_detection(frame, det["species"], det["confidence"], tuple(det["box"]))

    with _last_detections_lock:
        _last_detections[camera_id] = detections

    _log_detections(camera_id, offset, detections)
    return frame, detections


def get_last_detections(camera_id):
    with _last_detections_lock:
        return list(_last_detections.get(camera_id, []))
