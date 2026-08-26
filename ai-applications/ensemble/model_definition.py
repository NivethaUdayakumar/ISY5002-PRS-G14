"""
Purpose: Load every trained single-animal YOLO model for ensemble inference.

Functions:
    load_config - loads and parses config.yaml
    load_ensemble_models - loads every model listed under ensemble.models from trained_models/
    get_model - returns the loaded model for one animal
    list_models - returns the animal names currently loaded
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import yaml
from ultralytics import YOLO

logger = logging.getLogger(__name__)


class EnsembleModelLoader:
    """Loads all trained models listed under config.yaml's `ensemble.models` section."""

    def __init__(self, config_path: Path, repo_root: Optional[Path] = None) -> None:
        self.config_path = Path(config_path)
        # config.yaml lives at <repo_root>/ai-applications/config.yaml
        self.repo_root = Path(repo_root) if repo_root else self.config_path.resolve().parents[1]
        self.config: dict = {}
        self.models: dict[str, YOLO] = {}

    def load_config(self) -> dict:
        """Loads and parses config.yaml."""
        with open(self.config_path) as f:
            self.config = yaml.safe_load(f)
        return self.config

    def load_ensemble_models(self) -> dict[str, YOLO]:
        """Loads every model referenced under config['ensemble']['models'] from trained_models/."""
        if not self.config:
            self.load_config()

        model_specs = self.config.get("ensemble", {}).get("models", {}) or {}
        for animal, spec in model_specs.items():
            raw_path = Path(spec["path"])
            model_path = raw_path if raw_path.is_absolute() else (self.repo_root / raw_path).resolve()
            if not model_path.exists():
                logger.warning("Skipping '%s': model not found at %s (not trained yet?)", animal, model_path)
                continue
            self.models[animal] = YOLO(str(model_path))
            logger.info("Loaded model for '%s' from %s", animal, model_path)

        if not self.models:
            raise FileNotFoundError(
                "No trained models found. Train at least one animal model with "
                "model_train_code/main.py before running the ensemble."
            )
        return self.models

    def get_model(self, animal: str) -> YOLO:
        """Returns the loaded model for a specific animal."""
        if animal not in self.models:
            raise KeyError(f"No loaded model for '{animal}'. Available: {self.list_models()}")
        return self.models[animal]

    def list_models(self) -> list[str]:
        """Returns the animal names for which a model is currently loaded."""
        return sorted(self.models.keys())
