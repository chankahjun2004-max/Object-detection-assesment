# Model Training Guide: Staff Tag Detection & Metric Learning

This folder contains the complete training code for fine-tuning vision models tailored to FootfallCam 3D overhead ceiling sensors.

---

## 1. Architecture Overview

Because sensor cameras are ceiling-mounted and subject tags/badges are small, the pipeline uses a two-stage approach:
1. **Object Detection (`train_tag_detector.py`)**: Direct localization of staff badges/lanyards on the torso using fine-tuned **Ultralytics YOLOv8/YOLO11**.
2. **Deep Metric Learning (`train_metric_embedder.py`)**: A Triplet-Loss embedding network that projects upper-body visual crops into a compact 128-dimensional metric space where the cosine similarity between matching tags is maximized while background distractors are suppressed.

---

## 2. Step 1: Extract and Prepare Dataset

Run `prepare_dataset.py` to extract frames from `sample.mp4`, run person detection, crop upper-body regions, and auto-generate labels in both YOLO and Triplet formats:

```bash
cd Backend/training
python prepare_dataset.py --video ../../sample.mp4 --output ./dataset --interval 5 --val-ratio 0.20
```

This creates:
- `dataset/data.yaml`: YOLO configuration.
- `dataset/images/train`, `dataset/images/val`: Extracted video frames.
- `dataset/labels/train`, `dataset/labels/val`: Torso/tag bounding box annotations.
- `dataset/triplet_crops/positive`: Cropped staff tags/badges.
- `dataset/triplet_crops/negative`: Distractor crops (desks, shirts, shadows).

---

## 3. Step 2: Train Tag Detector (YOLO Fine-Tuning)

Fine-tune the YOLO detector with spatial augmentations designed specifically for top-down ceiling perspectives (360° rotation, perspective warp, lighting shifts):

```bash
python train_tag_detector.py --data ./dataset/data.yaml --model yolov8n.pt --epochs 30 --batch-size 16 --onnx
```

* **Output Weights:** `Backend/models/tag_detector_best.pt`
* **Exported ONNX:** `runs/tag_detector/overhead_staff_tag/weights/best.onnx`

---

## 4. Step 3: Train Metric Embedder (Triplet Loss)

Train the deep embedding network for zero-shot tag comparison:

```bash
python train_metric_embedder.py --data ./dataset --epochs 15 --batch-size 32 --margin 0.3 --lr 0.0001
```

* **Output Weights:** `Backend/models/tag_embedder_best.pth`

---

## 5. Deployment into the Live Backend

The trained weights in `Backend/models/` are automatically picked up by the FastAPI inference service (`Backend/app/pipeline.py`), improving detection accuracy and reducing false positives during live video evaluation.

