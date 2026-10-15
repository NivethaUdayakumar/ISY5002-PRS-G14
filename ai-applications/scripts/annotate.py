"""
Train YOLO11 on your labeled images, then use it to annotate ONLY the images
that don't have bounding boxes yet (label file missing or empty).

New label files are written to "new_annotate/" and the matching images are
copied to "new_images/". The original "images/" and "annotated/" folders are
never modified. Hand-made labels are used
for training and to measure how accurate the model is.

A label file is only written when the model predicts class 5 with
confidence >= CONF_THRESHOLD. Images with no confident prediction are listed
in needs_review.txt instead.

Folder layout expected (run this script from the folder containing both):
    images/         5 (1).jpg, 5 (2).jpg, ...
    annotated/      5 (1).txt, 5 (2).txt, ..., classes.txt
Created by this script:
    new_annotate/   label files for previously unlabeled images (+ classes.txt)
    new_images/     copies of the images that got a new label file

Install first:  python -m pip install ultralytics
"""

import random
import shutil
from pathlib import Path

from ultralytics import YOLO

# ---------------- settings ----------------
IMAGES_DIR = Path("images")
LABELS_DIR = Path("annotated")      # existing hand-made labels (read only)
OUTPUT_DIR = Path("new_annotate")   # new label files go here
NEW_IMAGES_DIR = Path("new_images") # matching images are copied here
WORK_DIR = Path("yolo_dataset")     # temporary training copy (rebuilt each run)
CLASS_ID = 5
CONF_THRESHOLD = 0.5                # minimum confidence to accept a prediction
IOU_MATCH = 0.5                     # overlap needed to count a box as correct
VAL_FRACTION = 0.2                  # share of labeled images held out for checking
EPOCHS = 200
PATIENCE = 10                       # early stopping: stop if no improvement for this many epochs
IMGSZ = 640
MODEL = "yolo11n.pt"                # yolo11s.pt / yolo11m.pt are more accurate but slower
SEED = 42
IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
# ------------------------------------------


def read_labels(path):
    """Return a list of (cls, xc, yc, w, h) from a YOLO .txt file."""
    boxes = []
    if path.exists():
        for line in path.read_text().splitlines():
            parts = line.split()
            if len(parts) == 5:
                boxes.append((int(parts[0]), *map(float, parts[1:])))
    return boxes


def iou(a, b):
    """IoU of two boxes given as normalized (xc, yc, w, h)."""
    ax1, ay1, ax2, ay2 = a[0] - a[2] / 2, a[1] - a[3] / 2, a[0] + a[2] / 2, a[1] + a[3] / 2
    bx1, by1, bx2, by2 = b[0] - b[2] / 2, b[1] - b[3] / 2, b[0] + b[2] / 2, b[1] + b[3] / 2
    iw = max(0.0, min(ax2, bx2) - max(ax1, bx1))
    ih = max(0.0, min(ay2, by2) - max(ay1, by1))
    inter = iw * ih
    union = a[2] * a[3] + b[2] * b[3] - inter
    return inter / union if union > 0 else 0.0


def load_class_names():
    classes_file = LABELS_DIR / "classes.txt"
    if classes_file.exists():
        names = [n.strip() for n in classes_file.read_text().splitlines() if n.strip()]
    else:
        names = []
    while len(names) <= CLASS_ID:          # make sure class 5 exists in the list
        names.append(f"class_{len(names)}")
    return names


def build_dataset(train_imgs, val_imgs, names):
    if WORK_DIR.exists():
        shutil.rmtree(WORK_DIR)
    for split, imgs in (("train", train_imgs), ("val", val_imgs)):
        img_out = WORK_DIR / "images" / split
        lbl_out = WORK_DIR / "labels" / split
        img_out.mkdir(parents=True)
        lbl_out.mkdir(parents=True)
        for img in imgs:
            shutil.copy2(img, img_out / img.name)
            shutil.copy2(LABELS_DIR / f"{img.stem}.txt", lbl_out / f"{img.stem}.txt")

    yaml_path = WORK_DIR / "data.yaml"
    lines = [f"path: {WORK_DIR.resolve().as_posix()}", "train: images/train", "val: images/val", "names:"]
    lines += [f"  {i}: {n}" for i, n in enumerate(names)]
    yaml_path.write_text("\n".join(lines) + "\n")
    return yaml_path


def predict_boxes(model, images):
    """Yield (image_path, [(conf, xc, yc, w, h), ...]) keeping only class CLASS_ID."""
    for r in model.predict(source=[str(p) for p in images], conf=CONF_THRESHOLD,
                           imgsz=IMGSZ, stream=True, verbose=False):
        boxes = []
        for cls, conf, xywh in zip(r.boxes.cls.tolist(), r.boxes.conf.tolist(), r.boxes.xywhn.tolist()):
            if int(cls) == CLASS_ID and conf >= CONF_THRESHOLD:
                boxes.append((conf, *xywh))
        yield Path(r.path), boxes


def main():
    random.seed(SEED)

    # 1. Sort images into labeled (has boxes) / unlabeled (no file or empty file)
    images = sorted(p for p in IMAGES_DIR.iterdir() if p.suffix.lower() in IMG_EXTS)
    labeled, unlabeled = [], []
    for img in images:
        (labeled if read_labels(LABELS_DIR / f"{img.stem}.txt") else unlabeled).append(img)
    print(f"Images: {len(images)} | labeled: {len(labeled)} | unlabeled: {len(unlabeled)}")
    if len(labeled) < 10:
        raise SystemExit("Need at least ~10 labeled images to train.")
    if not unlabeled:
        raise SystemExit("Every image already has bounding boxes - nothing to annotate.")

    # 2. Prepare the output folders (images/ and annotated/ are never written to)
    OUTPUT_DIR.mkdir(exist_ok=True)
    NEW_IMAGES_DIR.mkdir(exist_ok=True)
    classes_file = LABELS_DIR / "classes.txt"
    if classes_file.exists():
        shutil.copy2(classes_file, OUTPUT_DIR / "classes.txt")   # so LabelImg etc. can open it

    # 3. Train on labeled images only (empty files would teach the model "no leopard here")
    random.shuffle(labeled)
    n_val = max(1, int(len(labeled) * VAL_FRACTION))
    val_imgs, train_imgs = labeled[:n_val], labeled[n_val:]
    data_yaml = build_dataset(train_imgs, val_imgs, load_class_names())

    model = YOLO(MODEL)
    model.train(data=str(data_yaml), epochs=EPOCHS, patience=PATIENCE, imgsz=IMGSZ, seed=SEED,
                project="runs", name="leopard", exist_ok=True)
    best = Path(model.trainer.best)
    print(f"Best weights: {best}")
    model = YOLO(best)

    # 4. Check accuracy on held-out labeled images (these files are NOT modified)
    correct = 0
    for img, preds in predict_boxes(model, val_imgs):
        truth = [b[1:] for b in read_labels(LABELS_DIR / f"{img.stem}.txt") if b[0] == CLASS_ID]
        if truth and all(any(iou(t, p[1:]) >= IOU_MATCH for p in preds) for t in truth):
            correct += 1
    print(f"Validation: {correct}/{len(val_imgs)} images fully correct "
          f"({100 * correct / len(val_imgs):.1f}%)")

    # 5. Annotate ONLY the unlabeled images; write labels to new_annotate/
    #    and copy the matching image to new_images/
    written, skipped = 0, []
    for img, preds in predict_boxes(model, unlabeled):
        if not preds:
            skipped.append(img.name)
            continue
        lines = [f"{CLASS_ID} {xc:.6f} {yc:.6f} {w:.6f} {h:.6f}" for _, xc, yc, w, h in preds]
        (OUTPUT_DIR / f"{img.stem}.txt").write_text("\n".join(lines) + "\n")
        shutil.copy2(img, NEW_IMAGES_DIR / img.name)
        written += 1

    review_file = Path("needs_review.txt")
    review_file.write_text("\n".join(skipped) + ("\n" if skipped else ""))
    print(f"New label files written to {OUTPUT_DIR}/ (images copied to {NEW_IMAGES_DIR}/): {written}")
    print(f"No confident prediction (no file written): {len(skipped)} -> listed in {review_file}")


if __name__ == "__main__":   # required on Windows for training dataloaders
    main()