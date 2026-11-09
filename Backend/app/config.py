import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

STATIC_DIR = BASE_DIR / "static"
UPLOADS_DIR = STATIC_DIR / "uploads"
EVIDENCE_DIR = STATIC_DIR / "evidence"
REFERENCES_DIR = STATIC_DIR / "references"

for d in [UPLOADS_DIR, EVIDENCE_DIR, REFERENCES_DIR]:
    d.mkdir(parents=True, exist_ok=True)

YOLO_MODEL_PATH = str(BASE_DIR / "yolov8m.pt" if (BASE_DIR / "yolov8m.pt").exists() else BASE_DIR / "yolov8n.pt")
MODEL_VERSION = "YOLOv8-ByteTrack-v2.3.1"

# CORS settings for Angular Frontend
CORS_ORIGINS = [
    "http://localhost:4200",
    "http://127.0.0.1:4200",
    "http://localhost:3000",
    "*"
]

HOST = "0.0.0.0"
PORT = 8000

