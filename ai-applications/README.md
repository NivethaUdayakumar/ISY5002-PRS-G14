# WildLens AI Applications

Per-animal YOLO detectors, trained independently and combined into one ensemble.

## Layout

```
ai-applications/
├── config.yaml                  # dataset, yolo, training, ensemble, inference settings
├── download_dataset.py          # builds the shared pseudo-labeled dataset pool
├── wildlife_dataset/            # generated: raw_images/, raw_labels/, per_animal/<animal>/
├── model_train_code/
│   ├── data_preprocessing.py    # DatasetPreprocessor
│   ├── model_definition.py      # YOLOTrainer
│   ├── model_evaluation.py      # ModelEvaluator
│   └── main.py                  # run this: prep -> train -> save -> evaluate
├── trained_models/              # generated: <animal>_model.pt + <animal>_metrics.json
├── runs/                        # generated: raw Ultralytics training logs/plots per animal
├── ensemble/
│   ├── model_definition.py      # EnsembleModelLoader
│   ├── model_evaluation.py      # EnsembleEvaluator
│   ├── ensemble_inference.py    # run this: load -> predict -> merge -> visualize
│   └── predictions/             # generated: annotated ensemble outputs
├── requirements.txt
└── README.md
```

## Setup

```bash
pip install -r requirements.txt
```

## Dataset

```bash
python download_dataset.py --config config.yaml --species lion,bear,tiger
```

Pulls images from iNaturalist and pseudo-labels them with a base COCO
detector (weak supervision — spot-check `wildlife_dataset/raw_labels/`
before training). Writes `raw_images/<animal>/` and `raw_labels/<animal>/`.

No dataset generation script is required — `raw_images/<animal>/*.jpg` +
`raw_labels/<animal>/*.txt` (standard YOLO label format) is all
`model_train_code/main.py` needs, so a manually or externally labeled
dataset dropped into that layout works the same way.

## Train

```bash
python model_train_code/main.py --animal lion --config config.yaml
```

Carves that animal's images out of the pool, fine-tunes from
`yolo.pretrained_weights`, and evaluates on the test split. Flags:
`--config`, `--skip-eval`, `--epochs`, `--batch-size`.

Output: `trained_models/<animal>_model.pt` + `<animal>_metrics.json`. Every
run starts from the same pretrained checkpoint, never from another animal's
weights, so animals can be trained in any order on any machine.

## Ensemble

Register each trained model under `config.yaml`:

```yaml
ensemble:
  voting_strategy: "weighted_average"   # or "majority"
  confidence_threshold: 0.25
  iou_threshold: 0.45
  models:
    lion:
      path: "./ai-applications/trained_models/lion_model.pt"
      weight: 1.0
```

Then run:

```bash
python ensemble/ensemble_inference.py --image test.jpg --config config.yaml
```

Every registered model runs independently, then same-animal boxes that
overlap by `ensemble.iou_threshold` IoU are merged — averaged by weight
under `weighted_average`, or kept only if at least half the models agree
under `majority`. Missing model files are skipped with a warning, so this
works with a partial roster while other animals are still training. Result
saved to `ensemble/predictions/<image_stem>_ensemble.jpg`.

`backend/services/detection_service.py` uses the same ensemble for live
camera frames, falling back to the base COCO model until at least one
animal model is registered.
