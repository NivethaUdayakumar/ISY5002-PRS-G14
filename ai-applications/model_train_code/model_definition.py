"""
Purpose: Fine-tune a single-animal YOLO detector, always starting from pretrained weights.

Functions:
    load_model - loads the pretrained YOLO checkpoint as the training starting point
    train - runs YOLO fine-tuning on the animal's single-class dataset
    save_model - copies the run's best checkpoint to trained_models/<animal>_model.pt
    get_training_metrics - returns the final-epoch metrics from the last training run
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Optional

from ultralytics import YOLO

logger = logging.getLogger(__name__)


class YOLOTrainer:
    """Fine-tunes one animal's YOLO detector.

    Always loads its starting weights from the shared pretrained checkpoint
    declared in config.yaml (`yolo.pretrained_weights`), never from a
    previously fine-tuned animal model, so each animal's detector is trained
    independently and combined later by the ensemble.
    """

    def __init__(self, animal: str, config: dict, output_dir: Path) -> None:
        self.animal = animal
        self.config = config
        self.output_dir = Path(output_dir)
        self.model: Optional[YOLO] = None
        self.results = None

    def load_model(self, pretrained_weights: Optional[str] = None) -> YOLO:
        """Loads the shared pretrained YOLO checkpoint as the training starting point."""
        yolo_cfg = self.config["yolo"]
        weights = pretrained_weights or yolo_cfg.get("pretrained_weights") or f"{yolo_cfg['model_variant']}.pt"
        logger.info("Loading pretrained weights for '%s': %s", self.animal, weights)
        self.model = YOLO(weights)
        return self.model

    def train(
        self,
        data_yaml: Path,
        epochs: Optional[int] = None,
        batch_size: Optional[int] = None,
        img_size: Optional[int] = None,
        device: Optional[str] = None,
        patience: Optional[int] = None,
    ):
        """Runs YOLO fine-tuning on this animal's single-class dataset."""
        if self.model is None:
            self.load_model()

        train_cfg = self.config["training"]
        yolo_cfg = self.config["yolo"]
        run_name = f"{self.animal}_train"

        self.results = self.model.train(
            data=str(data_yaml),
            epochs=epochs or train_cfg["epochs"],
            batch=batch_size or train_cfg["batch_size"],
            imgsz=img_size or yolo_cfg["img_size"],
            device=device or yolo_cfg.get("device", "cpu"),
            patience=patience or train_cfg["patience"],
            project=str(self.output_dir),
            name=run_name,
            exist_ok=True,
        )
        return self.results

    def save_model(self, dest_dir: Path) -> Path:
        """Copies this run's best checkpoint to trained_models/<animal>_model.pt."""
        dest_dir = Path(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)
        run_name = f"{self.animal}_train"
        best_checkpoint = self.output_dir / run_name / "weights" / "best.pt"
        if not best_checkpoint.exists():
            raise FileNotFoundError(f"No best.pt found at {best_checkpoint}; did training complete?")

        dest_path = dest_dir / f"{self.animal}_model.pt"
        shutil.copy2(best_checkpoint, dest_path)
        logger.info("Saved trained model to %s", dest_path)
        return dest_path

    def get_training_metrics(self) -> dict:
        """Returns the final-epoch metrics dict from the most recent train() call."""
        if self.results is None:
            raise RuntimeError("No training results available; call train() first.")
        metrics = getattr(self.results, "results_dict", None)
        return dict(metrics) if metrics else {}
