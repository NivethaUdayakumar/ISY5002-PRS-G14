"""
Purpose: Carve a single-animal YOLO dataset out of the shared pseudo-labeled image pool
    produced by download_dataset.py, remapping that animal's class id to 0.

Functions:
    create_yolo_dataset_structure - creates the images/labels train-val-test folder layout
    split_dataset - splits one animal's raw images/labels into train/val/test
    create_dataset_yaml - writes a single-class dataset.yaml for this animal
    validate_dataset - checks image/label pairing and readable images across all splits
    get_dataset_stats - returns image counts per split
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Sequence

import yaml
from PIL import Image
from sklearn.model_selection import train_test_split

logger = logging.getLogger(__name__)


class DatasetPreprocessor:
    """Prepares a per-animal YOLO detection dataset for a single team member."""

    def __init__(
        self,
        animal: str,
        raw_images_root: Path,
        raw_labels_root: Path,
        output_root: Path,
        split_ratios: Sequence[float] = (0.8, 0.1, 0.1),
        seed: int = 42,
    ) -> None:
        self.animal = animal
        self.raw_images_root = Path(raw_images_root)
        self.raw_labels_root = Path(raw_labels_root)
        self.output_root = Path(output_root)
        self.split_ratios = tuple(split_ratios)
        self.seed = seed

    def create_yolo_dataset_structure(self) -> dict[str, Path]:
        """Creates images/{train,val,test} and labels/{train,val,test} under output_root."""
        paths = {}
        for kind in ("images", "labels"):
            for split in ("train", "val", "test"):
                split_dir = self.output_root / kind / split
                split_dir.mkdir(parents=True, exist_ok=True)
                paths[f"{kind}_{split}"] = split_dir
        return paths

    @staticmethod
    def _remap_label_to_class_zero(src_label_path: Path, dest_label_path: Path) -> None:
        """Copies a YOLO label file, rewriting every box's class id to 0."""
        lines_out = []
        for line in src_label_path.read_text().splitlines():
            parts = line.split()
            if not parts:
                continue
            parts[0] = "0"
            lines_out.append(" ".join(parts))
        dest_label_path.write_text("\n".join(lines_out) + ("\n" if lines_out else ""))

    def split_dataset(self) -> dict[str, int]:
        """Splits this animal's raw images/labels into train/val/test and copies
        them into the YOLO structure, remapping the class id to 0 as it goes."""
        self.create_yolo_dataset_structure()

        species_image_dir = self.raw_images_root / self.animal
        species_label_dir = self.raw_labels_root / self.animal
        if not species_label_dir.exists():
            raise FileNotFoundError(
                f"No pseudo-labels found for '{self.animal}' at {species_label_dir}. "
                f"Run download_dataset.py --species {self.animal} first."
            )

        stems = sorted(p.stem for p in species_label_dir.glob("*.txt"))
        if not stems:
            raise ValueError(f"No labeled images found for '{self.animal}' in {species_label_dir}")

        train_ratio, val_ratio, test_ratio = self.split_ratios
        if len(stems) < 3:
            splits = {"train": stems, "val": [], "test": []}
        else:
            train_stems, rest_stems = train_test_split(
                stems, train_size=train_ratio, random_state=self.seed
            )
            remaining = val_ratio + test_ratio
            val_share = val_ratio / remaining if remaining > 0 else 0.5
            if len(rest_stems) >= 2:
                val_stems, test_stems = train_test_split(
                    rest_stems, train_size=val_share, random_state=self.seed
                )
            else:
                val_stems, test_stems = rest_stems, []
            splits = {"train": train_stems, "val": val_stems, "test": test_stems}

        counts = {}
        for split, split_stems in splits.items():
            for stem in split_stems:
                src_image = species_image_dir / f"{stem}.jpg"
                src_label = species_label_dir / f"{stem}.txt"
                if not src_image.exists():
                    continue
                shutil.copy2(src_image, self.output_root / "images" / split / f"{stem}.jpg")
                self._remap_label_to_class_zero(src_label, self.output_root / "labels" / split / f"{stem}.txt")
            counts[split] = len(split_stems)

        logger.info(
            "%s: train=%d val=%d test=%d", self.animal, counts["train"], counts["val"], counts["test"]
        )
        return counts

    def create_dataset_yaml(self) -> Path:
        """Writes a single-class dataset.yaml describing this animal's split."""
        dataset_yaml = {
            "path": str(self.output_root.resolve()),
            "train": "images/train",
            "val": "images/val",
            "test": "images/test",
            "nc": 1,
            "names": [self.animal],
        }
        out_path = self.output_root / "dataset.yaml"
        with open(out_path, "w") as f:
            yaml.safe_dump(dataset_yaml, f, sort_keys=False)
        logger.info("Wrote %s", out_path)
        return out_path

    def validate_dataset(self) -> tuple[bool, list[str]]:
        """Checks every split for image/label pairing and readable images.

        Returns (is_valid, issues) where issues is a human-readable list of
        problems found (empty when is_valid is True).
        """
        issues: list[str] = []
        for split in ("train", "val", "test"):
            image_dir = self.output_root / "images" / split
            label_dir = self.output_root / "labels" / split
            image_stems = {p.stem for p in image_dir.glob("*.jpg")}
            label_stems = {p.stem for p in label_dir.glob("*.txt")}

            missing_labels = image_stems - label_stems
            missing_images = label_stems - image_stems
            if missing_labels:
                issues.append(f"{split}: {len(missing_labels)} image(s) missing a label file")
            if missing_images:
                issues.append(f"{split}: {len(missing_images)} label(s) missing an image file")

            for stem in image_stems:
                try:
                    with Image.open(image_dir / f"{stem}.jpg") as img:
                        img.verify()
                except Exception as exc:
                    issues.append(f"{split}/{stem}.jpg: unreadable ({exc})")

        train_count = len(list((self.output_root / "images" / "train").glob("*.jpg")))
        if train_count == 0:
            issues.append("train split is empty")

        return (len(issues) == 0, issues)

    def get_dataset_stats(self) -> dict:
        """Returns image counts per split plus the class name for this dataset."""
        stats: dict = {"animal": self.animal}
        for split in ("train", "val", "test"):
            stats[split] = len(list((self.output_root / "images" / split).glob("*.jpg")))
        stats["total"] = stats["train"] + stats["val"] + stats["test"]
        return stats
