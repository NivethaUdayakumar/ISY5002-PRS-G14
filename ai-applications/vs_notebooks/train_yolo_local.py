"""Script version of vs_notebooks/YOLO_Training_v2.ipynb for running training outside Jupyter.

Usage:
    python train_yolo_local.py                # full training (100 epochs, imgsz 640)
    python train_yolo_local.py --smoke-test   # quick pipeline check (1 epoch, small subset)
"""
import argparse
import shutil
from pathlib import Path

import torch
import yaml
from ultralytics import YOLO

PROJECT_ROOT = Path(r'C:\Users\nivet\ISY5002-PRS-G14')
DATASET_DIR = PROJECT_ROOT / 'data' / 'wildlife_dataset'
MODEL_CFG = PROJECT_ROOT / 'ai-applications' / 'model_configurations' / 'yolo_nivetha_v1.yaml'
TRAINED_MODEL_DIR = PROJECT_ROOT / 'ai-applications' / 'trained_model'
RUNS_DIR = PROJECT_ROOT / 'ai-applications' / 'yolo_runs'


def write_dataset_yaml() -> Path:
    data_yaml = DATASET_DIR / 'wildlife_dataset.yaml'
    dataset_config = {
        'path': str(DATASET_DIR),
        'train': 'images/train',
        'val': 'images/val',
        'test': 'images/test',
        'names': {0: 'buffalo', 1: 'elephant', 2: 'lion', 3: 'zebra'},
    }
    with open(data_yaml, 'w') as f:
        yaml.safe_dump(dataset_config, f, sort_keys=False)
    return data_yaml


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--smoke-test', action='store_true', help='1 epoch on a small subset to verify the pipeline')
    parser.add_argument('--epochs', type=int, default=100)
    parser.add_argument('--imgsz', type=int, default=640)
    parser.add_argument('--batch', type=int, default=16)
    args = parser.parse_args()

    assert DATASET_DIR.exists(), f'Dataset not found: {DATASET_DIR}'
    assert MODEL_CFG.exists(), f'Model config not found: {MODEL_CFG}'
    TRAINED_MODEL_DIR.mkdir(parents=True, exist_ok=True)

    data_yaml = write_dataset_yaml()
    device = 0 if torch.cuda.is_available() else 'cpu'
    run_name = 'wildlife_smoke_test' if args.smoke_test else 'wildlife_from_scratch'

    print('Device:', device)
    print('Dataset YAML:', data_yaml)

    model = YOLO(str(MODEL_CFG))
    model.train(
        data=str(data_yaml),
        epochs=1 if args.smoke_test else args.epochs,
        imgsz=320 if args.smoke_test else args.imgsz,
        batch=8 if args.smoke_test else args.batch,
        fraction=0.05 if args.smoke_test else 1.0,
        device=device,
        workers=2,
        pretrained=False,
        patience=25,
        project=str(RUNS_DIR),
        name=run_name,
        plots=True,
        save=True,
        exist_ok=True,
    )

    weights_dir = RUNS_DIR / run_name / 'weights'
    if not args.smoke_test:
        shutil.copy2(weights_dir / 'best.pt', TRAINED_MODEL_DIR / 'yolo_nivetha_v1_best.pt')
        if (weights_dir / 'last.pt').exists():
            shutil.copy2(weights_dir / 'last.pt', TRAINED_MODEL_DIR / 'yolo_nivetha_v1_last.pt')
        print('Final trained model saved to:', TRAINED_MODEL_DIR / 'yolo_nivetha_v1_best.pt')
    else:
        print('Smoke test complete. Weights at:', weights_dir)


if __name__ == '__main__':
    main()
