"""
Purpose: Combine predictions from multiple single-animal YOLO models into one ensemble result.

Functions:
    compute_iou - computes intersection-over-union between two boxes
    ensemble_predict - runs every loaded model on an image and returns merged detections
    _weighted_average_voting - merges overlapping same-animal boxes via weighted-confidence averaging
    _majority_voting - keeps merged boxes that at least half the loaded models agree on
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Optional

from ultralytics import YOLO

logger = logging.getLogger(__name__)


class EnsembleEvaluator:
    """Runs every loaded animal model on an image and merges their detections via voting."""

    def __init__(
        self,
        models: dict[str, YOLO],
        model_weights: Optional[dict[str, float]] = None,
        voting_strategy: str = "weighted_average",
        confidence_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        device: str = "cpu",
    ) -> None:
        self.models = models
        self.model_weights = model_weights or {}
        self.voting_strategy = voting_strategy
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.device = device

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

    def _collect_raw_detections(self, image) -> list[dict]:
        """Runs every animal-specific model on `image` (a file path or an in-memory frame),
        tagging each box with its source animal."""
        raw = []
        for animal, model in self.models.items():
            result = model.predict(image, conf=self.confidence_threshold, device=self.device, verbose=False)[0]
            for box in result.boxes:
                raw.append(
                    {
                        "animal": animal,
                        "confidence": float(box.conf[0]),
                        "box": [float(v) for v in box.xyxy[0]],
                        "weight": self.model_weights.get(animal, 1.0),
                    }
                )
        return raw

    def _weighted_average_voting(self, raw_detections: list[dict]) -> list[dict]:
        """Clusters overlapping same-animal boxes (by IoU) and merges each cluster via a weighted average."""
        by_animal: dict[str, list[dict]] = defaultdict(list)
        for det in raw_detections:
            by_animal[det["animal"]].append(det)

        merged = []
        for animal, dets in by_animal.items():
            dets = sorted(dets, key=lambda d: d["confidence"] * d["weight"], reverse=True)
            used = [False] * len(dets)

            for i, det in enumerate(dets):
                if used[i]:
                    continue
                cluster = [det]
                used[i] = True
                for j in range(i + 1, len(dets)):
                    if not used[j] and self.compute_iou(det["box"], dets[j]["box"]) >= self.iou_threshold:
                        cluster.append(dets[j])
                        used[j] = True

                total_weight = sum(c["weight"] for c in cluster)
                avg_box = [sum(c["box"][k] * c["weight"] for c in cluster) / total_weight for k in range(4)]
                avg_conf = sum(c["confidence"] * c["weight"] for c in cluster) / total_weight
                merged.append(
                    {
                        "animal": animal,
                        "confidence": avg_conf,
                        "box": avg_box,
                        "num_models_agreeing": len(cluster),
                    }
                )
        return merged

    def _majority_voting(self, raw_detections: list[dict]) -> list[dict]:
        """Keeps only merged boxes that at least half of the loaded models agree on."""
        merged = self._weighted_average_voting(raw_detections)
        quorum = max(1, -(-len(self.models) // 2))  # ceil(n / 2)
        return [m for m in merged if m["num_models_agreeing"] >= quorum]

    def ensemble_predict(self, image) -> list[dict]:
        """Runs all loaded models on `image` (a file path or an in-memory frame)
        and returns merged detections per the configured voting strategy."""
        raw_detections = self._collect_raw_detections(image)
        if self.voting_strategy == "majority":
            return self._majority_voting(raw_detections)
        return self._weighted_average_voting(raw_detections)
