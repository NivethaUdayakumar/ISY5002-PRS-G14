"""Weighted Boxes Fusion ensemble of RF-DETR models, as built and evaluated in
ai-applications/vs_notebooks/RFDETR_ensemble_wbf.ipynb.

The ensemble is described by trained_models/rfdetr_ensemble_wbf.json: the models' checkpoint paths (relative
to the repo root) and weights, the WBF settings and the confidence threshold picked on the val split."""
import json
from pathlib import Path
from threading import Lock

import numpy as np
import supervision as sv
import torch
from rfdetr import from_checkpoint

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENSEMBLE_PATH = BASE_DIR / "ai-applications" / "trained_models" / "rfdetr_ensemble_wbf.json"

_ensemble = None
_ensemble_lock = Lock()


class Ensemble:
    def __init__(self, config, models):
        self.config = config
        self.models = models
        self.weights = np.array([entry["weight"] for entry in config["models"]], dtype=float)
        self.class_names = config["class_names"]
        self.confidence_threshold = config["confidence_threshold"]

    def predict_batch(self, images, confidence=None):
        """Runs every model on the batch of PIL images and fuses their boxes image by image.
        Returns one sv.Detections per image, keeping the boxes at or above `confidence`
        (the ensemble's own threshold when None)."""
        threshold = self.confidence_threshold if confidence is None else confidence
        per_model = []
        for model in self.models:
            results = model.predict(images, threshold=self.config["predict_threshold"], include_source_image=False)
            per_model.append(results if isinstance(results, list) else [results])

        fused_per_image = []
        for per_image in zip(*per_model):
            fused = fuse(per_image, self.weights, self.config["wbf_iou"], self.config["skip_box_thr"])
            fused_per_image.append(fused[fused.confidence >= threshold])
        return fused_per_image


def load_ensemble():
    global _ensemble
    if _ensemble is None:
        with _ensemble_lock:
            if _ensemble is None:
                with open(ENSEMBLE_PATH) as f:
                    config = json.load(f)
                models = []
                for entry in config["models"]:
                    model = from_checkpoint(str(BASE_DIR / entry["path"]))
                    # FP16 roughly halves GPU latency. compile=False keeps the model usable
                    # with any batch size (a traced model is fixed to one batch size).
                    if torch.cuda.is_available():
                        model.inference(compile=False, dtype=torch.float16)
                    models.append(model)
                _ensemble = Ensemble(config, models)
    return _ensemble


def fuse(detections_per_model, weights, wbf_iou, skip_box_thr):
    """Weighted Boxes Fusion of one image's detections from every model.

    Per class, boxes are taken from highest to lowest confidence; a box joins the cluster whose fused box it
    overlaps with IoU > `wbf_iou`, otherwise it starts a new cluster. A cluster's box is the confidence-weighted
    average of its boxes, and its confidence the weighted average over all models of each model's best
    confidence in the cluster (0 for a model without a box there)."""
    xyxy, conf, class_id, model_idx = [], [], [], []
    for m, detections in enumerate(detections_per_model):
        keep = detections.confidence >= skip_box_thr
        xyxy.append(detections.xyxy[keep])
        conf.append(detections.confidence[keep])
        class_id.append(detections.class_id[keep])
        model_idx.append(np.full(keep.sum(), m))
    xyxy, conf, class_id, model_idx = map(np.concatenate, (xyxy, conf, class_id, model_idx))
    weights = np.asarray(weights, dtype=float)
    box_weight = conf * weights[model_idx]

    fused_xyxy, fused_conf, fused_class = [], [], []
    for cls in np.unique(class_id):
        order = np.flatnonzero(class_id == cls)
        order = order[np.argsort(-conf[order], kind="stable")]
        clusters, boxes = [], np.empty((0, 4))
        for i in order:
            if len(boxes):
                iou = sv.box_iou_batch(xyxy[i][None], boxes)[0]
                j = iou.argmax()
                if iou[j] > wbf_iou:
                    clusters[j].append(i)
                    members = clusters[j]
                    boxes[j] = (box_weight[members, None] * xyxy[members]).sum(axis=0) / box_weight[members].sum()
                    continue
            clusters.append([i])
            boxes = np.vstack([boxes, xyxy[i]])

        for members, box in zip(clusters, boxes):
            best = np.zeros(len(weights))
            np.maximum.at(best, model_idx[members], conf[members])
            fused_xyxy.append(box)
            fused_conf.append((weights * best).sum() / weights.sum())
            fused_class.append(cls)

    if not fused_xyxy:
        return sv.Detections.empty()
    return sv.Detections(
        xyxy=np.array(fused_xyxy),
        class_id=np.array(fused_class, dtype=int),
        confidence=np.array(fused_conf),
    )
