"""
Staff Tag Detection Model Fine-Tuning Script using Ultralytics YOLO.
Trains a specialized detector on staff badges/lanyards with top-down fisheye camera augmentations.
"""

import os
import argparse
from pathlib import Path
from ultralytics import YOLO

def train_detector(
    data_yaml: str,
    base_model: str = "yolov8n.pt",
    epochs: int = 50,
    batch_size: int = 16,
    imgsz: int = 640,
    device: str = "0",
    export_onnx: bool = True
):
    print(f"--- Starting Staff Tag Detector Training ---")
    print(f"Base model: {base_model}")
    print(f"Dataset config: {data_yaml}")
    print(f"Epochs: {epochs}, Batch size: {batch_size}, Image size: {imgsz}")

    # Initialize YOLO model
    model = YOLO(base_model)

    # Train with specific augmentations tailored for overhead ceiling sensors:
    # - Rotation: 0-180 deg (people walk in all directions relative to ceiling sensor)
    # - Perspective: Simulates lens distortion towards edges of wide-angle camera
    # - Scale jitter: Captures variation between tall/short staff
    # - Color / HSV jitter: Resilient against overhead fluorescent flicker & glare
    results = model.train(
        data=data_yaml,
        epochs=epochs,
        batch=batch_size,
        imgsz=imgsz,
        device=device,
        degrees=45.0,          # Rotation augmentation
        translate=0.10,        # Spatial translation
        scale=0.30,            # Scale jitter
        fliplr=0.5,            # Horizontal flip
        flipud=0.5,            # Vertical flip (valid for top-down ceiling sensors)
        perspective=0.0005,    # Lens distortion simulation
        hsv_h=0.015,           # Hue variation
        hsv_s=0.7,             # Saturation variation
        hsv_v=0.4,             # Brightness variation
        save=True,
        save_period=10,
        project="runs/tag_detector",
        name="overhead_staff_tag",
        exist_ok=True,
        pretrained=True
    )

    print("--- Training Completed! ---")
    best_weights = Path(model.trainer.best)
    print(f"Best model weights saved at: {best_weights}")

    # Validate model
    print("Running validation...")
    val_results = model.val()
    print(f"Validation mAP50: {val_results.box.map50:.4f}")
    print(f"Validation mAP50-95: {val_results.box.map:.4f}")

    # Copy best weights to models directory
    dest_dir = Path("../models")
    dest_dir.mkdir(parents=True, exist_ok=True)
    best_dest = dest_dir / "tag_detector_best.pt"
    if best_weights.exists():
        import shutil
        shutil.copyfile(best_weights, best_dest)
        print(f"Copied best model to: {best_dest}")

    # Export to ONNX if requested
    if export_onnx:
        print("Exporting model to ONNX format...")
        onnx_path = model.export(format="onnx", dynamic=True)
        print(f"ONNX model exported to: {onnx_path}")

    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train YOLO Staff Tag Detector")
    parser.add_argument("--data", type=str, default="./dataset/data.yaml", help="Path to data.yaml")
    parser.add_argument("--model", type=str, default="yolov8n.pt", help="Base model weights")
    parser.add_argument("--epochs", type=int, default=30, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=16, help="Batch size")
    parser.add_argument("--imgsz", type=int, default=640, help="Image resolution")
    parser.add_argument("--device", type=str, default="", help="Device: '0', 'cpu', etc.")
    parser.add_argument("--onnx", action="store_true", help="Export to ONNX after training")
    args = parser.parse_args()

    train_detector(
        data_yaml=args.data,
        base_model=args.model,
        epochs=args.epochs,
        batch_size=args.batch_size,
        imgsz=args.imgsz,
        device=args.device,
        export_onnx=args.onnx
    )

