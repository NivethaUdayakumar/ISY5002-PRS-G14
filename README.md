# ISY5002 PRS G14 WildLens

Automated Wildlife Detection from Live camera-trap feeds.

**Team:** Nivetha Udayakumar (A0245895L), Lim Zheng Tao (A0339804X)

## Overview

Around one million species face extinction. Camera traps monitor wildlife without disturbing it, but they produce far more footage than biologists can review by hand, and endangered species appear in only a tiny fraction of it. Rare sightings and poaching need to reach rangers in time to act, which requires live detection.

WildLens is an automated pipeline that detects and classifies species from live camera feeds, flags endangered species with confidence scores, and stores every sighting for long-term study.

Field footage varies in pose, lighting, scale and occlusion, and a single model can carry architecture-specific bias. WildLens addresses this with two sources of diversity:

- **Data diversity:** Image augmentation during training (flip, rotation, mosaic, random erasing).
- **Model diversity:** Detectors with different architectures (YOLO11n, YOLO26l, RT-DETR-L, RF-DETR-M) whose predictions are fused with weighted boxes fusion, a species vote and a stacking layer. 206 ensemble configurations were compared against each detector alone.

The app runs an ensemble of three RF-DETR models (Weighted Boxes Fusion) on the live feeds.

## Features

- Live view of six cameras with detection boxes and a live count of sightings and species per camera.
- Every detected animal is saved as its own sighting: a crop of the animal, labelled `<camera_id>_<timestamp>`, filed under its species folder.
- Endangered species are also copied into `data/sightings/endangered/` and counted live on the Notifications button.
- Camera modal: live feed plus a scrolling list of that camera's sightings, with a record view to reclassify a sighting.
- Notifications modal: endangered sightings only.
- Collections page: browse sightings by species.

## Project structure

| Path | Contents |
| --- | --- |
| `backend/` | FastAPI service: frame reading, detection, sighting store |
| `frontend/` | React + Vite + Tailwind web app |
| `ai-applications/` | Training notebooks, scripts, results and trained models |
| `data/live-cam/` | Camera videos (not in git) |
| `data/sightings/` | Sightings written at runtime, plus `species.json` |

## Setup

Requirements: Python 3.10+, Node.js 18+. A CUDA GPU is optional but makes detection much faster.

### 1. Python environment

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r backend/requirements.txt
```

### 2. Ensemble models

Download the three checkpoints and put them in `ai-applications/trained_models/`, keeping these file names:

| File | Download |
| --- | --- |
| `rfdetr_dropout_10.pth` | [Google Drive](https://drive.google.com/file/d/1LXzarDc-gU15zmHVRScsmh7jhqANbA5H/view?usp=sharing) |
| `rfdetr_dropout_20.pth` | [Google Drive](https://drive.google.com/file/d/1EvNuyHMwc1lkjyxaCS8UH7XA3n5XL1RG/view?usp=sharing) |
| `rfdetr_erasing_10.pth` | [Google Drive](https://drive.google.com/file/d/173AS8hyFU9OLLLMZf11_NFojiaajssgb/view?usp=sharing) |

The ensemble settings (weights, fusion thresholds, class names) are in `ai-applications/trained_models/rfdetr_ensemble_wbf.json`. Model files are not tracked by git.

### 3. Camera videos

The six camera feeds are video files that are not in git. [Download them from Google Drive](https://drive.google.com/file/d/1CKFVP6j9nsGN-oa-KtbWa0CDdHvTqTd_/view) and place them at:

- `data/live-cam/location-a/camera_01.mp4`, `camera_02.mp4`, `camera_03.mp4`
- `data/live-cam/location-b/camera_04.mp4`, `camera_05.mp4`, `camera_06.mp4`

### 4. Frontend dependencies

```bash
cd frontend
npm install
```

## Running

From the repository root, `start.bat` opens the backend and the frontend in separate windows. Or run them yourself:

```bash
# Backend (http://127.0.0.1:8000)
cd backend
python -m uvicorn main:app --reload

# Frontend (http://localhost:5173)
cd frontend
npm run dev
```

Open http://localhost:5173. The first detection request loads all three models, so the cameras take a moment to start.

## Using the app

- **Cameras page:** click a camera to open its live view. The right-hand list shows that camera's sightings; click one to see its record and reclassify the species or endangered flag. "View collection" opens the Collections page.
- **Notifications:** the header button shows the live number of endangered sightings; click it to review them.
- **Collections:** browse sightings grouped by species.

Sightings exist only while the backend runs: they are cleared on every backend start. `data/sightings/species.json` (the species list and which are endangered) is kept.

## Dataset

The training dataset is hosted on Ultralytics Platform: [isy5002-g14-dataset](https://platform.ultralytics.com/nivetha-udayakumar/datasets/isy5002-g14-dataset).

Classes: buffalo, elephant, rhino, zebra, okapi, leopard, cheetah.

## Training and evaluation

Training notebooks (YOLO, RF-DETR variants and the WBF ensemble) are in `ai-applications/vs_notebooks/` and `ai-applications/colab_notebooks/`. Results are in `ai-applications/training_results/` and `ai-applications/ensemble_training_evaluation_results/`.
