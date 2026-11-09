"""
Dataset Preparation & Auto-Labeling Utility for Overhead FootfallCam Sensor Footage.
Extracts person detections, crops upper-body regions, generates pseudo-annotations,
and formats data for YOLO object detection and Siamese/Triplet metric learning.
"""

import os
import cv2
import json
import random
import argparse
from pathlib import Path
from ultralytics import YOLO

def create_yolo_yaml(dataset_dir: Path):
    yaml_content = f"""path: {dataset_dir.as_posix()}
train: images/train
val: images/val

names:
  0: staff_tag
"""
    with open(dataset_dir / "data.yaml", "w") as f:
        f.write(yaml_content)
    print(f"Created data.yaml at {dataset_dir / 'data.yaml'}")

def prepare_dataset_from_video(
    video_path: str,
    output_dir: str,
    sample_interval: int = 5,
    val_ratio: float = 0.20
):
    dataset_dir = Path(output_dir)
    img_train = dataset_dir / "images" / "train"
    img_val = dataset_dir / "images" / "val"
    lbl_train = dataset_dir / "labels" / "train"
    lbl_val = dataset_dir / "labels" / "val"
    triplets_dir = dataset_dir / "triplet_crops"

    for d in [img_train, img_val, lbl_train, lbl_val, triplets_dir / "positive", triplets_dir / "negative"]:
        d.mkdir(parents=True, exist_ok=True)

    create_yolo_yaml(dataset_dir)

    print(f"Loading YOLO person detector...")
    model = YOLO("yolov8m.pt" if Path("yolov8m.pt").exists() else "yolov8n.pt")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Could not open video {video_path}")
        return

    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"Processing {video_path} ({frame_count} frames, interval={sample_interval})...")

    frame_idx = 0
    saved_samples = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % sample_interval == 0:
            h, w = frame.shape[:2]
            results = model(frame, classes=[0], verbose=False)
            boxes = results[0].boxes

            if boxes is not None and len(boxes) > 0:
                is_val = (random.random() < val_ratio)
                dest_img_dir = img_val if is_val else img_train
                dest_lbl_dir = lbl_val if is_val else lbl_train

                frame_name = f"frame_{frame_idx:05d}"
                img_out_path = dest_img_dir / f"{frame_name}.jpg"
                cv2.imwrite(str(img_out_path), frame)

                label_lines = []
                for box_i, b in enumerate(boxes):
                    x1, y1, x2, y2 = b.xyxy[0].cpu().numpy().tolist()
                    bw = x2 - x1
                    bh = y2 - y1

                    if bw < 20 or bh < 30:
                        continue

                    # Pseudo-labeling staff tag location: Upper 35% of detected torso
                    # Centered horizontally on chest
                    tag_w = bw * 0.35
                    tag_h = bh * 0.20
                    tag_xc = x1 + (bw / 2.0)
                    tag_yc = y1 + (bh * 0.25)

                    # Normalize to [0, 1] for YOLO format
                    norm_xc = tag_xc / w
                    norm_yc = tag_yc / h
                    norm_w = tag_w / w
                    norm_h = tag_h / h

                    label_lines.append(f"0 {norm_xc:.6f} {norm_yc:.6f} {norm_w:.6f} {norm_h:.6f}")

                    # Also save cropped badge for Siamese/Triplet dataset
                    tx1 = max(0, int(tag_xc - tag_w / 2.0))
                    ty1 = max(0, int(tag_yc - tag_h / 2.0))
                    tx2 = min(w, int(tag_xc + tag_w / 2.0))
                    ty2 = min(h, int(tag_yc + tag_h / 2.0))
                    tag_crop = frame[ty1:ty2, tx1:tx2]

                    if tag_crop.size > 0:
                        # Extract positive tag crop
                        cv2.imwrite(str(triplets_dir / "positive" / f"{frame_name}_p{box_i}.jpg"), tag_crop)
                        # Extract negative distractor (lower torso / background)
                        neg_crop = frame[min(h-10, int(y1 + bh*0.6)):min(h, int(y2)), tx1:tx2]
                        if neg_crop.size > 0:
                            cv2.imwrite(str(triplets_dir / "negative" / f"{frame_name}_n{box_i}.jpg"), neg_crop)

                with open(dest_lbl_dir / f"{frame_name}.txt", "w") as f:
                    f.write("\n".join(label_lines))

                saved_samples += 1

        frame_idx += 1

    cap.release()
    print(f"Dataset preparation complete! Saved {saved_samples} labeled frames to {output_dir}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract and prepare training dataset from video")
    parser.add_argument("--video", type=str, default="../../sample.mp4", help="Path to video file")
    parser.add_argument("--output", type=str, default="./dataset", help="Output directory")
    parser.add_argument("--interval", type=int, default=5, help="Frame sampling interval")
    parser.add_argument("--val-ratio", type=float, default=0.20, help="Validation set ratio")
    args = parser.parse_args()

    prepare_dataset_from_video(args.video, args.output, args.interval, args.val_ratio)

