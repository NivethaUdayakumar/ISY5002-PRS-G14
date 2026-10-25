from pathlib import Path
from threading import Lock

import cv2
import torch
from PIL import Image
from rfdetr import from_checkpoint

BASE_DIR = Path(__file__).resolve().parent.parent.parent
WEIGHTS_PATH = BASE_DIR / "ai-applications" / "trained_models" / "rfdetr_erasing_10_best.pth"
BOX_COLOR = (30, 200, 90)  # BGR

_model = None
_model_lock = Lock()


def _load_model():
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                model = from_checkpoint(str(WEIGHTS_PATH))
                # FP16 roughly halves GPU latency. compile=False keeps the model usable
                # with any batch size (a traced model is fixed to one batch size).
                if torch.cuda.is_available():
                    model.inference(compile=False, dtype=torch.float16)
                _model = model
    return _model


def _draw_detections(frame, detections, class_names):
    for (x1, y1, x2, y2), score, class_id in zip(
        detections.xyxy.astype(int), detections.confidence, detections.class_id
    ):
        label = f"{class_names[int(class_id)]} {score:.0%}"

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


def detect_and_annotate_batch(frames, confidence):
    """Runs the RF-DETR model on a list of BGR frames in a single batch, draws
    boxes/labels on each in place, and returns the annotated frames."""
    annotated, _ = detect_batch_with_metadata(frames, confidence)
    return annotated


def detect_batch_with_metadata(frames, confidence):
    """Return annotated frames and serializable detections for each frame."""
    if not frames:
        return [], []

    model = _load_model()
    images = [Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)) for frame in frames]
    results = model.predict(images, threshold=confidence, include_source_image=False)
    if not isinstance(results, list):
        results = [results]

    metadata = []
    for frame, detections in zip(frames, results):
        height, width = frame.shape[:2]
        frame_detections = []
        for box, score, class_id in zip(detections.xyxy, detections.confidence, detections.class_id):
            class_id = int(class_id)
            x1, y1, x2, y2 = (int(value) for value in box)
            # Copy the crop before boxes are drawn so it contains only the animal.
            crop = frame[max(0, y1):min(height, y2), max(0, x1):min(width, x2)].copy()
            frame_detections.append({
                "crop": crop,
                "species": model.class_names[class_id],
                "classId": class_id,
                "confidence": float(score),
                "bbox": [int(value) for value in box],
            })
        _draw_detections(frame, detections, model.class_names)
        metadata.append(frame_detections)

    return frames, metadata


def detect_and_annotate(frame, camera_id, confidence):
    """Runs the RF-DETR model on a single BGR `frame`, draws boxes/labels on it
    in place, and returns the annotated frame."""
    return detect_and_annotate_batch([frame], confidence)[0]
