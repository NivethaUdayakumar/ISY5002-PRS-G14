#!/usr/bin/env python3
"""
WildLens ensemble pipeline: model diversity + test-time augmentation (TTA) + stacking layer.

Pipeline for every frame:
  1. TTA: view A = original frame, view B = horizontally flipped frame.
  2. Detection: YOLO11n (Y6), RT-DETR-L (R6) and RF-DETR-M each predict on both views
     at a low candidate threshold, so the later stages can still recover weak detections.
  3. Un-flip view B boxes:  x1' = W - x2,  x2' = W - x1.
  4. Per-model TTA merge: Weighted Boxes Fusion (WBF) of view A and view B.
     A box seen in only one view keeps half its confidence.
  5. Cross-model fusion: boxes from the three models are grouped class-agnostically
     (IoU >= CLUSTER_IOU). Each group becomes one box (confidence-weighted average),
     its species is a confidence-weighted vote, and a stacking layer (logistic regression
     trained on the validation set) turns the group's features into P(correct detection).
  6. Output: boxes whose stacking probability >= the threshold chosen on validation.

Commands:
  fit       Run the three models on the validation split, train the stacking layer,
            choose the final threshold, save stacker.joblib.
  evaluate  Compare each single model and the ensemble on a split (default: test).
  video     Extract frames from a video file, webcam index or RTSP/HTTP stream
            (one frame every --every seconds) and log ensemble detections to CSV.

Requirements: pip install ultralytics rfdetr supervision ensemble-boxes scikit-learn joblib opencv-python pyyaml

Examples:
  python ensemble_pipeline.py fit
  python ensemble_pipeline.py evaluate --split test
  python ensemble_pipeline.py video --source ../../data/datasets/location-a/camera_01.mp4 --camera-id camera_01
  python ensemble_pipeline.py video --source rtsp://user:pass@host/stream --camera-id gate --every 1
"""

import argparse
import csv
import time
from datetime import datetime, timezone
from pathlib import Path

import cv2
import joblib
import numpy as np
import yaml
from ensemble_boxes import weighted_boxes_fusion
from PIL import Image
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[2]  # repo root (ai-applications/scripts -> repo)
DATASET_DIR = ROOT / "data" / "wildlife_dataset"
DATA_YAML = DATASET_DIR / "wildlife_dataset.yaml"
MODEL_DIR = ROOT / "ai-applications" / "trained_models"
STACKER_PATH = MODEL_DIR / "ensemble_stacker.joblib"

MODELS = {  # name -> (weights file, framework, final single-model confidence)
    "YOLO11n": (MODEL_DIR / "y6_best.pt", "yolo", 0.50),
    "RT-DETR-L": (MODEL_DIR / "r6_best.pt", "rtdetr", 0.70),
    "RF-DETR-M": (MODEL_DIR / "rfdetr_erasing_10_best.pth", "rfdetr", 0.50),
}
BASE_MODEL = "RF-DETR-M"  # tie-break for the species vote (highest single-model mAP50-95)

CANDIDATE_CONF = 0.05  # low threshold for ensemble inputs: keeps weak boxes for the stacker
TTA_IOU = 0.55  # WBF IoU for merging the original and flipped view of one model
CLUSTER_IOU = 0.55  # IoU for grouping boxes from different models into one object
MATCH_IOU = 0.50  # IoU for counting a detection as correct during evaluation


# ----------------------------------------------------------------------------------------
# Models
# ----------------------------------------------------------------------------------------
class Detector:
    """Uniform wrapper: predict(bgr) -> (xyxy [N,4] pixels, scores [N], classes [N])."""

    def __init__(self, name, weights, kind):
        self.name, self.kind = name, kind
        if kind == "yolo":
            from ultralytics import YOLO
            self.model = YOLO(str(weights))
        elif kind == "rtdetr":
            from ultralytics import RTDETR
            self.model = RTDETR(str(weights))
        elif kind == "rfdetr":
            from rfdetr import from_checkpoint
            self.model = from_checkpoint(str(weights))
        else:
            raise ValueError(kind)

    def predict(self, bgr, conf):
        if self.kind in ("yolo", "rtdetr"):
            r = self.model.predict(bgr, conf=conf, verbose=False)[0].boxes
            return r.xyxy.cpu().numpy(), r.conf.cpu().numpy(), r.cls.cpu().numpy().astype(int)
        det = self.model.predict(Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)), threshold=conf)
        return det.xyxy.astype(float), det.confidence.astype(float), det.class_id.astype(int)


def load_detectors():
    dets = {}
    for name, (weights, kind, _) in MODELS.items():
        assert Path(weights).exists(), f"Missing weights for {name}: {weights}"
        dets[name] = Detector(name, weights, kind)
    return dets


# ----------------------------------------------------------------------------------------
# Stages 1-4: TTA and per-model merge
# ----------------------------------------------------------------------------------------
def unflip(xyxy, width):
    out = xyxy.copy()
    out[:, 0], out[:, 2] = width - xyxy[:, 2], width - xyxy[:, 0]
    return out


def predict_tta(detector, bgr, conf=CANDIDATE_CONF):
    """Original + horizontal flip, merged with WBF. Returns xyxy (pixels), scores, classes."""
    h, w = bgr.shape[:2]
    a = detector.predict(bgr, conf)
    b = detector.predict(cv2.flip(bgr, 1), conf)
    b = (unflip(b[0], w), b[1], b[2])
    scale = np.array([w, h, w, h], dtype=float)
    boxes, scores, labels = [], [], []
    for xyxy, s, c in (a, b):
        boxes.append(np.clip(xyxy / scale, 0, 1).tolist())
        scores.append(s.tolist())
        labels.append(c.tolist())
    if sum(len(s) for s in scores) == 0:
        return np.zeros((0, 4)), np.zeros(0), np.zeros(0, int)
    fb, fs, fl = weighted_boxes_fusion(boxes, scores, labels, iou_thr=TTA_IOU, skip_box_thr=conf, conf_type="avg")
    return np.asarray(fb) * scale, np.asarray(fs), np.asarray(fl).astype(int)


# ----------------------------------------------------------------------------------------
# Stage 5: cross-model grouping, species vote and stacking features
# ----------------------------------------------------------------------------------------
def iou_matrix(a, b):
    if len(a) == 0 or len(b) == 0:
        return np.zeros((len(a), len(b)))
    x1 = np.maximum(a[:, None, 0], b[None, :, 0]); y1 = np.maximum(a[:, None, 1], b[None, :, 1])
    x2 = np.minimum(a[:, None, 2], b[None, :, 2]); y2 = np.minimum(a[:, None, 3], b[None, :, 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    area_a = (a[:, 2] - a[:, 0]) * (a[:, 3] - a[:, 1]); area_b = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
    return inter / (area_a[:, None] + area_b[None, :] - inter + 1e-9)


def fuse_models(per_model, n_classes):
    """per_model: {name: (xyxy, scores, classes)} -> list of fused objects with features.

    Boxes from all models are sorted by confidence. Each box joins the first group whose
    fused box it overlaps with IoU >= CLUSTER_IOU and that has no box from the same model yet;
    otherwise it starts a new group (class-agnostic, so species disagreement stays in one group).
    """
    names = list(MODELS)
    items = [(s, n, xyxy, c) for n in names for xyxy, s, c in zip(*per_model[n])]
    items.sort(key=lambda t: -t[0])
    groups = []
    for s, n, xyxy, c in items:
        best, best_iou = None, CLUSTER_IOU
        for g in groups:
            if n in g["members"]:
                continue
            iou = iou_matrix(xyxy[None], g["box"][None])[0, 0]
            if iou >= best_iou:
                best, best_iou = g, iou
        if best is None:
            groups.append({"members": {n: (s, xyxy, c)}, "box": xyxy.copy()})
        else:
            best["members"][n] = (s, xyxy, c)
            w = np.array([m[0] for m in best["members"].values()])
            bx = np.array([m[1] for m in best["members"].values()])
            best["box"] = (w[:, None] * bx).sum(0) / w.sum()

    fused = []
    for g in groups:
        votes = np.zeros(n_classes)
        for s, _, c in g["members"].values():
            votes[c] += s
        top = np.flatnonzero(votes == votes.max())
        if len(top) > 1 and BASE_MODEL in g["members"] and g["members"][BASE_MODEL][2] in top:
            cls = g["members"][BASE_MODEL][2]
        else:
            cls = int(top[0])
        member_boxes = np.array([m[1] for m in g["members"].values()])
        feats = [g["members"].get(n, (0.0,))[0] for n in names]  # each model's confidence (0 = not detected)
        feats += [
            len(g["members"]) / len(names),  # share of models that detected the object
            np.mean([m[2] == cls for m in g["members"].values()]),  # species agreement
            iou_matrix(member_boxes, g["box"][None]).mean(),  # box agreement
            votes[cls] / max(votes.sum(), 1e-9),  # vote share of the winning species
        ]
        feats += list(np.eye(n_classes)[cls])  # species one-hot
        fused.append({"box": g["box"], "cls": cls, "feats": np.array(feats, float),
                      "mean_conf": float(sum(m[0] for m in g["members"].values()) / len(names))})
    return fused


class Ensemble:
    def __init__(self, detectors, n_classes, stacker=None):
        self.detectors, self.n_classes = detectors, n_classes
        self.stacker = stacker["model"] if stacker else None
        self.threshold = stacker["threshold"] if stacker else 0.5

    def candidates(self, bgr):
        per_model = {n: predict_tta(d, bgr) for n, d in self.detectors.items()}
        return fuse_models(per_model, self.n_classes), per_model

    def score(self, fused):
        if not fused:
            return np.zeros(0)
        if self.stacker is None:  # fallback: WBF-style mean confidence over the three models
            return np.array([f["mean_conf"] for f in fused])
        return self.stacker.predict_proba(np.stack([f["feats"] for f in fused]))[:, 1]

    def predict(self, bgr):
        fused, _ = self.candidates(bgr)
        p = self.score(fused)
        keep = p >= self.threshold
        boxes = np.array([f["box"] for f in fused]).reshape(-1, 4)[keep]
        classes = np.array([f["cls"] for f in fused], int)[keep]
        return boxes, p[keep], classes


# ----------------------------------------------------------------------------------------
# Data and evaluation
# ----------------------------------------------------------------------------------------
def class_names():
    names = yaml.safe_load(open(DATA_YAML))["names"]
    return [names[i] for i in sorted(names)] if isinstance(names, dict) else list(names)


def load_split(split):
    img_dir = DATASET_DIR / "images" / split
    for img_path in sorted(p for p in img_dir.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"}):
        bgr = cv2.imread(str(img_path))
        h, w = bgr.shape[:2]
        lbl = DATASET_DIR / "labels" / split / (img_path.stem + ".txt")
        rows = np.loadtxt(lbl, ndmin=2) if lbl.exists() and lbl.stat().st_size else np.zeros((0, 5))
        cls = rows[:, 0].astype(int)
        cx, cy, bw, bh = rows[:, 1] * w, rows[:, 2] * h, rows[:, 3] * w, rows[:, 4] * h
        gt = np.stack([cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2], 1) if len(rows) else np.zeros((0, 4))
        yield img_path, bgr, gt, cls


def match(pred_boxes, pred_scores, pred_cls, gt_boxes, gt_cls, iou_thr=MATCH_IOU):
    """Class-agnostic greedy matching (highest confidence first).
    Returns per-prediction outcome ('correct' / 'wrong' / 'fp') and the number of missed animals."""
    order = np.argsort(-pred_scores)
    iou = iou_matrix(pred_boxes, gt_boxes)
    used = np.zeros(len(gt_boxes), bool)
    outcome = np.empty(len(pred_boxes), object)
    for i in order:
        cand = np.where(~used)[0]
        if len(cand) and iou[i, cand].max() >= iou_thr:
            j = cand[iou[i, cand].argmax()]
            used[j] = True
            outcome[i] = "correct" if pred_cls[i] == gt_cls[j] else "wrong"
        else:
            outcome[i] = "fp"
    return outcome, int((~used).sum())


def summarise(counts, n_gt, ap):
    c, w, f, m = counts["correct"], counts["wrong"], counts["fp"], counts["missed"]
    return {"mAP50": ap[0], "mAP50-95": ap[1], "Recall": c / max(n_gt, 1),
            "Precision": c / max(c + w + f, 1), "Correct": c, "Wrong": w, "FP": f, "Missed": m}


def map_metrics(preds, targets):
    import supervision as sv
    from supervision.metrics import MeanAveragePrecision
    P = [sv.Detections(xyxy=b.reshape(-1, 4), confidence=s, class_id=c) for b, s, c in preds]
    T = [sv.Detections(xyxy=b.reshape(-1, 4), class_id=c) for b, c in targets]
    r = MeanAveragePrecision().update(P, T).compute()
    return float(r.map50), float(r.map50_95)


# ----------------------------------------------------------------------------------------
# Commands
# ----------------------------------------------------------------------------------------
def cmd_fit(args):
    names = class_names()
    ens = Ensemble(load_detectors(), len(names))
    X, y = [], []
    for k, (path, bgr, gt, gcls) in enumerate(load_split(args.split), 1):
        fused, _ = ens.candidates(bgr)
        if fused:
            boxes = np.array([f["box"] for f in fused]); cls = np.array([f["cls"] for f in fused])
            conf = np.array([f["mean_conf"] for f in fused])
            outcome, _ = match(boxes, conf, cls, gt, gcls)
            X += [f["feats"] for f in fused]; y += [o == "correct" for o in outcome]
        if k % 50 == 0:
            print(f"{args.split}: {k} images")
    X, y = np.array(X), np.array(y, int)
    stacker = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, C=1.0))
    # Out-of-fold probabilities, so the threshold is not chosen on the stacker's own training fit
    p = cross_val_predict(stacker, X, y, cv=5, method="predict_proba")[:, 1]
    n_gt_found = y.sum()  # correct candidates = the most animals the ensemble can find
    best = (0, 0.5)
    for t in np.arange(0.05, 0.96, 0.01):
        tp, kept = (y[p >= t]).sum(), (p >= t).sum()
        prec, rec = tp / max(kept, 1), tp / max(n_gt_found, 1)
        f1 = 2 * prec * rec / max(prec + rec, 1e-9)
        if f1 > best[0]:
            best = (f1, round(float(t), 2))
    stacker.fit(X, y)
    joblib.dump({"model": stacker, "threshold": best[1], "features": X.shape[1]}, STACKER_PATH)
    print(f"Stacker trained on {len(y)} candidate boxes ({y.mean():.1%} correct). "
          f"Threshold {best[1]} (out-of-fold F1 {best[0]:.3f}). Saved to {STACKER_PATH}")


def cmd_evaluate(args):
    names = class_names()
    detectors = load_detectors()
    stacker = joblib.load(STACKER_PATH) if STACKER_PATH.exists() else None
    ens = Ensemble(detectors, len(names), stacker)
    systems = list(MODELS) + ["Ensemble (TTA + stacking)"]
    counts = {s: {"correct": 0, "wrong": 0, "fp": 0, "missed": 0} for s in systems}
    preds = {s: [] for s in systems}
    targets, n_gt, t0 = [], 0, {s: 0.0 for s in systems}
    for k, (path, bgr, gt, gcls) in enumerate(load_split(args.split), 1):
        targets.append((gt, gcls)); n_gt += len(gt)
        for n, d in detectors.items():  # single models: original view, final threshold
            s0 = time.perf_counter()
            b, s, c = d.predict(bgr, 0.001)  # low threshold for mAP
            t0[n] += time.perf_counter() - s0
            preds[n].append((b, s, c))
            keep = s >= MODELS[n][2]
            out, missed = match(b[keep], s[keep], c[keep], gt, gcls)
            for o in out: counts[n][o] += 1
            counts[n]["missed"] += missed
        s0 = time.perf_counter()
        fused, _ = ens.candidates(bgr)
        p = ens.score(fused)
        t0[systems[-1]] += time.perf_counter() - s0
        b = np.array([f["box"] for f in fused]).reshape(-1, 4); c = np.array([f["cls"] for f in fused], int)
        preds[systems[-1]].append((b, p, c))
        keep = p >= ens.threshold
        out, missed = match(b[keep], p[keep], c[keep], gt, gcls)
        for o in out: counts[systems[-1]][o] += 1
        counts[systems[-1]]["missed"] += missed
        if k % 50 == 0:
            print(f"{args.split}: {k} images")
    n_img = len(targets)
    rows = []
    for s in systems:
        r = summarise(counts[s], n_gt, map_metrics(preds[s], targets))
        r["ms/image"] = 1000 * t0[s] / n_img
        rows.append((s, r))
    keys = ["mAP50", "mAP50-95", "Recall", "Precision", "Correct", "Wrong", "FP", "Missed", "ms/image"]
    print(f"\n[{args.split}] {n_img} images, {n_gt} animals")
    print(f"{'System':28s}" + "".join(f"{k:>10s}" for k in keys))
    for s, r in rows:
        print(f"{s:28s}" + "".join(f"{r[k]:>10.4f}" if isinstance(r[k], float) else f"{r[k]:>10d}" for k in keys))
    best = max(rows[:-1], key=lambda t: t[1]["mAP50-95"])
    ensr = rows[-1][1]
    print(f"\nGain over best single model ({best[0]}): "
          f"mAP50-95 {ensr['mAP50-95'] - best[1]['mAP50-95']:+.4f}, "
          f"Recall {ensr['Recall'] - best[1]['Recall']:+.4f}, Precision {ensr['Precision'] - best[1]['Precision']:+.4f}")
    with open(Path(args.out), "w", newline="") as f:
        wr = csv.writer(f); wr.writerow(["System"] + keys)
        for s, r in rows: wr.writerow([s] + [r[k] for k in keys])
    print("Saved", args.out)


def frames(source, every_s):
    """Yield (offset_seconds, frame) every `every_s` seconds from a file, webcam index or stream."""
    cap = cv2.VideoCapture(int(source) if str(source).isdigit() else source)
    assert cap.isOpened(), f"Cannot open {source}"
    fps = cap.get(cv2.CAP_PROP_FPS) or 0
    is_file = cap.get(cv2.CAP_PROP_FRAME_COUNT) > 0 and fps > 0
    if is_file:  # recorded video: step through frame indices
        step, idx = max(int(round(fps * every_s)), 1), 0
        while True:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ok, frame = cap.read()
            if not ok:
                break
            yield idx / fps, frame
            idx += step
    else:  # live stream: keep grabbing so the buffer stays current, decode one frame per interval
        start, last = time.time(), -every_s
        while True:
            if not cap.grab():
                break
            now = time.time() - start
            if now - last >= every_s:
                ok, frame = cap.retrieve()
                if ok:
                    last = now
                    yield now, frame
    cap.release()


def cmd_video(args):
    names = class_names()
    ens = Ensemble(load_detectors(), len(names), joblib.load(STACKER_PATH) if STACKER_PATH.exists() else None)
    out = Path(args.out); new = not out.exists()
    with open(out, "a", newline="") as f:
        wr = csv.writer(f)
        if new:
            wr.writerow(["timestamp", "camera_id", "offset_s", "species", "confidence", "x1", "y1", "x2", "y2"])
        for offset, frame in frames(args.source, args.every):
            boxes, scores, classes = ens.predict(frame)
            ts = datetime.now(timezone.utc).isoformat()
            for (x1, y1, x2, y2), s, c in zip(boxes, scores, classes):
                wr.writerow([ts, args.camera_id, round(offset, 1), names[c], round(float(s), 4),
                             int(x1), int(y1), int(x2), int(y2)])
            f.flush()
            print(f"{args.camera_id} t={offset:7.1f}s  {len(boxes)} animals  "
                  + ", ".join(f"{names[c]} {s:.2f}" for s, c in zip(scores, classes)))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("fit"); p.add_argument("--split", default="val")
    p = sub.add_parser("evaluate"); p.add_argument("--split", default="test"); p.add_argument("--out", default="ensemble_evaluation.csv")
    p = sub.add_parser("video"); p.add_argument("--source", required=True); p.add_argument("--camera-id", default="camera_01")
    p.add_argument("--every", type=float, default=1.0, help="seconds between extracted frames")
    p.add_argument("--out", default=str(ROOT / "data" / "logs" / "detections.csv"))
    args = ap.parse_args()
    {"fit": cmd_fit, "evaluate": cmd_evaluate, "video": cmd_video}[args.cmd](args)


if __name__ == "__main__":
    main()
