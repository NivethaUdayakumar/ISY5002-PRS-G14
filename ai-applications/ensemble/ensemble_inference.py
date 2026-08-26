"""
Purpose: Run ensemble inference across every trained animal model and save an annotated result.
    Run this after all animal models are trained and registered under
    config.yaml's `ensemble.models` section.

Functions:
    draw_detections - draws ensemble detections onto a frame
    parse_args - parses CLI arguments (--image, --config, --output)
    main - loads models, runs the ensemble, visualizes, and saves the result

Usage:
    python ensemble/ensemble_inference.py --image test.jpg --config config.yaml
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent))

from model_definition import EnsembleModelLoader  # noqa: E402
from model_evaluation import EnsembleEvaluator  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = REPO_ROOT / "ai-applications" / "config.yaml"
DEFAULT_PREDICTIONS_DIR = REPO_ROOT / "ai-applications" / "ensemble" / "predictions"

BOX_COLOR = (30, 200, 90)  # BGR

logger = logging.getLogger("ensemble.ensemble_inference")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def draw_detections(frame, detections: list[dict]):
    """Draws ensemble detections (box + animal + confidence) onto `frame` in place."""
    for det in detections:
        x1, y1, x2, y2 = (int(v) for v in det["box"])
        label = f"{det['animal']} {det['confidence']:.0%}"

        cv2.rectangle(frame, (x1, y1), (x2, y2), BOX_COLOR, 2)
        (text_w, text_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        label_top = max(0, y1 - text_h - 8)
        cv2.rectangle(frame, (x1, label_top), (x1 + text_w + 6, y1), BOX_COLOR, -1)
        cv2.putText(
            frame, label, (x1 + 3, max(text_h + 2, y1 - 5)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (10, 10, 10), 1, cv2.LINE_AA,
        )
    return frame


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run ensemble inference across all trained animal models.")
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--output", type=Path, default=None, help="Where to save the annotated image")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.image.exists():
        logger.error("Image not found: %s", args.image)
        sys.exit(1)

    loader = EnsembleModelLoader(args.config)
    config = loader.load_config()
    loader.load_ensemble_models()
    logger.info("Loaded models for: %s", loader.list_models())

    ensemble_cfg = config.get("ensemble", {})
    model_weights = {animal: spec.get("weight", 1.0) for animal, spec in ensemble_cfg.get("models", {}).items()}

    evaluator = EnsembleEvaluator(
        models=loader.models,
        model_weights=model_weights,
        voting_strategy=ensemble_cfg.get("voting_strategy", "weighted_average"),
        confidence_threshold=ensemble_cfg.get("confidence_threshold", 0.25),
        iou_threshold=ensemble_cfg.get("iou_threshold", 0.45),
        device=config.get("inference", {}).get("device", "cpu"),
    )

    detections = evaluator.ensemble_predict(str(args.image))
    logger.info("Ensemble found %d detection(s): %s", len(detections), detections)

    frame = cv2.imread(str(args.image))
    if frame is None:
        logger.error("Could not read image with OpenCV: %s", args.image)
        sys.exit(1)
    annotated = draw_detections(frame, detections)

    output_path = args.output or (DEFAULT_PREDICTIONS_DIR / f"{args.image.stem}_ensemble.jpg")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), annotated)
    logger.info("Saved annotated result to %s", output_path)


if __name__ == "__main__":
    main()
