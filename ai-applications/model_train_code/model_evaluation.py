"""
Purpose: Evaluate a trained single-animal YOLO model.

Functions:
    evaluate_on_dataset - runs YOLO validation and returns precision/recall/mAP metrics
    predict_on_image - runs inference on a single image and returns detections
    compute_iou - computes intersection-over-union between two boxes
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Union

from ultralytics import YOLO

logger = logging.getLogger(__name__)


class ModelEvaluator:
    """Evaluates a trained YOLO model on a held-out dataset or single images."""

    def __init__(
        self,
        model: Union[str, Path, YOLO],
        confidence_threshold: float = 0.5,
        device: str = "cpu",
    ) -> None:
        self.model = model if isinstance(model, YOLO) else YOLO(str(model))
        self.confidence_threshold = confidence_threshold
        self.device = device

    def evaluate_on_dataset(self, data_yaml: Path, split: str = "test") -> dict:
        """Runs YOLO validation on `data_yaml` and returns precision/recall/mAP metrics.

        mAP is computed by sweeping the precision-recall curve across all
        confidence levels, so this deliberately does not filter by
        `self.confidence_threshold` (that threshold is for deployment-time
        inference in predict_on_image, not for measuring the model itself -
        passing it here would silently drop low-confidence-but-correct
        detections and report a misleadingly low score).
        """
        metrics = self.model.val(data=str(data_yaml), split=split, device=self.device)
        results_dict = getattr(metrics, "results_dict", {}) or {}
        summary = {
            "precision": results_dict.get("metrics/precision(B)"),
            "recall": results_dict.get("metrics/recall(B)"),
            "mAP50": results_dict.get("metrics/mAP50(B)"),
            "mAP50-95": results_dict.get("metrics/mAP50-95(B)"),
        }
        logger.info("Evaluation on '%s' split: %s", split, summary)
        return summary

    def predict_on_image(
        self, image_path: Union[str, Path], confidence_threshold: Optional[float] = None
    ) -> list[dict]:
        """Runs inference on a single image and returns a list of detections."""
        conf = confidence_threshold if confidence_threshold is not None else self.confidence_threshold
        result = self.model.predict(str(image_path), conf=conf, device=self.device, verbose=False)[0]

        detections = []
        for box in result.boxes:
            class_id = int(box.cls[0])
            x1, y1, x2, y2 = (float(v) for v in box.xyxy[0])
            detections.append(
                {
                    "class_id": class_id,
                    "class_name": result.names.get(class_id, str(class_id)),
                    "confidence": float(box.conf[0]),
                    "box": [x1, y1, x2, y2],
                }
            )
        return detections

    @staticmethod
    def compute_iou(box1: list[float], box2: list[float]) -> float:
        """Computes intersection-over-union between two [x1, y1, x2, y2] boxes."""
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])

        intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
        area1 = max(0.0, box1[2] - box1[0]) * max(0.0, box1[3] - box1[1])
        area2 = max(0.0, box2[2] - box2[0]) * max(0.0, box2[3] - box2[1])
        union = area1 + area2 - intersection

        return intersection / union if union > 0 else 0.0
