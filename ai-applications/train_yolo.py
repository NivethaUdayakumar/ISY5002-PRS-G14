"""Fine-tunes YOLOv8 on the wildlife dataset built by download_dataset.py.

Metrics (mAP, precision, recall, loss curves) are written automatically by
Ultralytics into ai-applications/runs/<run_name>/.

On success, the best checkpoint is copied to ai-applications/wildlife_yolov8.pt,
which backend/services/detection_service.py prefers over the stock yolov8n.pt
once it exists — so a successful run takes effect on the next live /frame
request with no other changes needed.

Run with --help for options.
"""

import argparse
import logging
import shutil
import sys
from pathlib import Path

import yaml
from ultralytics import YOLO

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"

logger = logging.getLogger("train_yolo")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def load_config(path):
    with open(path) as f:
        return yaml.safe_load(f)


def resolve_path(config_relative_path):
    return (REPO_ROOT / config_relative_path).resolve()


def find_resume_checkpoint(output_dir, run_name):
    checkpoint = output_dir / run_name / "weights" / "last.pt"
    return checkpoint if checkpoint.exists() else None


def parse_args():
    parser = argparse.ArgumentParser(description="Fine-tune YOLOv8 on the WildGuard wildlife dataset.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--dataset-yaml", type=Path, default=None, help="Override path to dataset.yaml")
    parser.add_argument("--model-variant", type=str, default=None, help="yolov8n | yolov8s | yolov8m")
    parser.add_argument("--epochs", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=None)
    parser.add_argument("--img-size", type=int, default=None)
    parser.add_argument("--device", type=str, default=None, help="'cpu' or a CUDA device index, e.g. '0'")
    parser.add_argument("--resume", action="store_true", help="Resume from this run's last checkpoint, if one exists")
    parser.add_argument("--run-name", type=str, default=None)
    return parser.parse_args()


def main():
    args = parse_args()
    config = load_config(args.config)
    train_cfg = config["training"]
    model_cfg = config["model"]

    run_name = args.run_name or train_cfg["run_name"]
    output_dir = resolve_path(train_cfg["output_dir"])
    dataset_yaml = args.dataset_yaml or (resolve_path(config["dataset"]["download_path"]) / "dataset.yaml")

    if not dataset_yaml.exists():
        logger.error("Dataset yaml not found at %s. Run download_dataset.py first.", dataset_yaml)
        sys.exit(1)

    model_variant = args.model_variant or train_cfg["model_variant"]
    epochs = args.epochs or train_cfg["epochs"]
    batch_size = args.batch_size or train_cfg["batch_size"]
    img_size = args.img_size or train_cfg["img_size"]
    device = args.device or train_cfg.get("device") or model_cfg.get("device", "cpu")

    resume_checkpoint = find_resume_checkpoint(output_dir, run_name) if args.resume else None

    if resume_checkpoint:
        logger.info("Resuming training from %s", resume_checkpoint)
        model = YOLO(str(resume_checkpoint))
        train_kwargs = {"resume": True}
    else:
        base_weights = f"{model_variant}.pt"
        logger.info("Starting fine-tune from pretrained %s on %s (%d epochs, batch %d, imgsz %d, device %s)",
                    base_weights, dataset_yaml, epochs, batch_size, img_size, device)
        model = YOLO(base_weights)
        train_kwargs = dict(
            data=str(dataset_yaml),
            epochs=epochs,
            batch=batch_size,
            imgsz=img_size,
            patience=train_cfg["patience"],
            device=device,
            project=str(output_dir),
            name=run_name,
            exist_ok=True,
        )

    results = model.train(**train_kwargs)

    run_dir = output_dir / run_name
    best_checkpoint = run_dir / "weights" / "best.pt"
    if best_checkpoint.exists():
        published_path = REPO_ROOT / "ai-applications" / model_cfg["finetuned_weights"]
        shutil.copy2(best_checkpoint, published_path)
        logger.info("Published best checkpoint to %s", published_path)
    else:
        logger.warning("No best.pt found in %s; live inference will keep using the base model.", run_dir)

    metrics = getattr(results, "results_dict", None)
    if metrics:
        logger.info("Final metrics: %s", metrics)
    logger.info("Training artifacts (loss curves, mAP/precision/recall, confusion matrix) are in %s", run_dir)


if __name__ == "__main__":
    main()
