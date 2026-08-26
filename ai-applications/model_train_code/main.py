"""
Purpose: Run the full per-animal training pipeline: prepare dataset, train, save, evaluate.
    Every run starts from the shared pretrained checkpoint in config.yaml
    (`yolo.pretrained_weights`), never from a previously fine-tuned model.

Functions:
    load_config - loads config.yaml
    resolve - resolves a config-relative path against the repo root
    parse_args - parses CLI arguments (--animal, --config, --skip-eval, --epochs, --batch-size)
    main - runs the pipeline end to end

Usage:
    python model_train_code/main.py --animal lion --config config.yaml
    python model_train_code/main.py --animal lion --skip-eval
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from data_preprocessing import DatasetPreprocessor  # noqa: E402
from model_definition import YOLOTrainer  # noqa: E402
from model_evaluation import ModelEvaluator  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
AI_DIR = REPO_ROOT / "ai-applications"
DEFAULT_CONFIG_PATH = AI_DIR / "config.yaml"

logger = logging.getLogger("model_train_code.main")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def load_config(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def resolve(path_str: str) -> Path:
    return (REPO_ROOT / path_str).resolve()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a single-animal YOLO detector.")
    parser.add_argument("--animal", required=True, help="Animal/class name, e.g. 'lion' (should match config.yaml dataset.species)")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--skip-eval", action="store_true", help="Skip the post-training evaluation step")
    parser.add_argument("--epochs", type=int, default=None, help="Override training.epochs")
    parser.add_argument("--batch-size", type=int, default=None, help="Override training.batch_size")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)

    animal = args.animal
    known_species = {s["name"] for s in config["dataset"]["species"]}
    if animal not in known_species:
        logger.warning("'%s' is not in config.yaml dataset.species; proceeding anyway", animal)

    dataset_root = resolve(config["dataset"]["download_path"])
    raw_images_root = dataset_root / "raw_images"
    raw_labels_root = dataset_root / "raw_labels"
    animal_dataset_root = dataset_root / "per_animal" / animal

    logger.info("=== Step 1/4: preparing dataset for '%s' ===", animal)
    preprocessor = DatasetPreprocessor(
        animal=animal,
        raw_images_root=raw_images_root,
        raw_labels_root=raw_labels_root,
        output_root=animal_dataset_root,
        split_ratios=tuple(config["dataset"]["train_val_test_split"]),
    )
    preprocessor.split_dataset()
    data_yaml = preprocessor.create_dataset_yaml()

    is_valid, issues = preprocessor.validate_dataset()
    if not is_valid:
        for issue in issues:
            logger.warning("Dataset issue: %s", issue)
    logger.info("Dataset stats: %s", preprocessor.get_dataset_stats())

    logger.info("=== Step 2/4: training '%s' from pretrained YOLO weights ===", animal)
    output_dir = resolve(config["training"]["output_dir"])
    trainer = YOLOTrainer(animal=animal, config=config, output_dir=output_dir)
    trainer.load_model()
    trainer.train(data_yaml=data_yaml, epochs=args.epochs, batch_size=args.batch_size)

    logger.info("=== Step 3/4: saving trained model ===")
    trained_models_dir = resolve(config["training"]["trained_models_dir"])
    model_path = trainer.save_model(trained_models_dir)
    training_metrics = trainer.get_training_metrics()

    eval_metrics: dict = {}
    if args.skip_eval:
        logger.info("Skipping evaluation (--skip-eval)")
    else:
        logger.info("=== Step 4/4: evaluating '%s' on the held-out test split ===", animal)
        evaluator = ModelEvaluator(
            model=model_path,
            confidence_threshold=config["yolo"].get("confidence_threshold", 0.5),
            device=config["yolo"].get("device", "cpu"),
        )
        eval_metrics = evaluator.evaluate_on_dataset(data_yaml, split="test")

    metrics_path = trained_models_dir / f"{animal}_metrics.json"
    metrics_path.write_text(
        json.dumps(
            {
                "training": training_metrics,
                "test_evaluation": eval_metrics,
                "dataset_stats": preprocessor.get_dataset_stats(),
            },
            indent=2,
        )
    )
    logger.info("Wrote metrics to %s", metrics_path)
    logger.info("Done. Model saved at %s", model_path)


if __name__ == "__main__":
    main()
