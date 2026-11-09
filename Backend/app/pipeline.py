import cv2
import os
import uuid
import numpy as np
from pathlib import Path
from typing import Optional
from ultralytics import YOLO

from app.config import YOLO_MODEL_PATH, EVIDENCE_DIR, MODEL_VERSION
from app.models import Analysis, FrameMatch, BoundingBox
from app.matcher import VisualTagMatcher
from app.database import db

def format_duration(seconds: float) -> str:
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m}:{s:02d}"

class VideoAnalysisPipeline:
    def __init__(self):
        self.matcher = VisualTagMatcher()
        print(f"Loading YOLO model from: {YOLO_MODEL_PATH}")
        self.detector = YOLO(YOLO_MODEL_PATH)

    def process_video_job(
        self,
        analysis_id: str,
        video_path: str,
        reference_image_path: Optional[str] = None,
        frame_sampling: int = 5,
        detection_threshold: float = 0.70,
        matching_threshold: float = 0.60,
        enable_tracking: bool = True,
        nms_threshold: float = 0.50,
        min_tag_size: int = 20,
        max_tag_size: int = 200
    ):
        """
        Background task to process a video clip frame by frame,
        performing person detection, ByteTrack tracking, tag matching, and evidence saving.
        """
        analysis = db.get_analysis(analysis_id)
        if not analysis:
            print(f"Analysis {analysis_id} not found.")
            return

        analysis.status = "processing"
        db.update_analysis(analysis)

        # Create evidence folder for this analysis
        evidence_folder = EVIDENCE_DIR / analysis_id
        evidence_folder.mkdir(parents=True, exist_ok=True)

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"Failed to open video: {video_path}")
            analysis.status = "failed"
            db.update_analysis(analysis)
            return

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_sec = total_frames / fps if fps > 0 else 0
        analysis.duration = format_duration(duration_sec)
        analysis.modelVersion = MODEL_VERSION

        # Load reference tag image if available
        reference_bgr = None
        if reference_image_path and os.path.exists(reference_image_path):
            reference_bgr = cv2.imread(reference_image_path)
            print(f"Loaded reference tag image: {reference_image_path}")

        match_count = 0
        frame_idx = 0
        frames_analyzed = 0

        # Reset ByteTrack memory for this new video
        tracker_type = "bytetrack.yaml" if enable_tracking else None

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                # Process every Nth frame according to frame_sampling
                if frame_idx % frame_sampling == 0:
                    frames_analyzed += 1
                    timestamp = round(frame_idx / fps, 2)
                    frame_h, frame_w = frame.shape[:2]

                    # Run YOLO person detector / tracker
                    if enable_tracking:
                        results = self.detector.track(
                            frame,
                            persist=True,
                            classes=[0], # person class only
                            tracker=tracker_type,
                            conf=detection_threshold,
                            iou=nms_threshold,
                            verbose=False
                        )
                    else:
                        results = self.detector(
                            frame,
                            classes=[0],
                            conf=detection_threshold,
                            iou=nms_threshold,
                            verbose=False
                        )

                    boxes = results[0].boxes
                    if boxes is not None and len(boxes) > 0:
                        for b in boxes:
                            # Person bounding box [x1, y1, x2, y2]
                            x1, y1, x2, y2 = b.xyxy[0].cpu().numpy().tolist()
                            conf_det = float(b.conf[0])
                            
                            # Track ID
                            if b.id is not None:
                                trk_num = int(b.id[0])
                                track_id = f"TRK-{trk_num:03d}"
                            else:
                                track_id = "TRK-001"

                            # Clamp coordinates within frame boundaries
                            x1 = max(0, min(frame_w - 1, int(x1)))
                            y1 = max(0, min(frame_h - 1, int(y1)))
                            x2 = max(0, min(frame_w, int(x2)))
                            y2 = max(0, min(frame_h, int(y2)))
                            w = x2 - x1
                            h = y2 - y1

                            if w <= 10 or h <= 10:
                                continue

                            # Crop person
                            person_crop = frame[y1:y2, x1:x2]
                            
                            # Upper-body crop (top 40% where tag / lanyard sits)
                            upper_h = max(10, int(h * 0.40))
                            upper_body_crop = person_crop[0:upper_h, :]

                            # Compute matching score against reference tag
                            if reference_bgr is not None:
                                match_score = self.matcher.compute_similarity(upper_body_crop, reference_bgr)
                            else:
                                # Heuristic badge presence score
                                match_score, _ = self.matcher.detect_tag_presence_heuristic(upper_body_crop)

                            # Check against matching threshold (normalized 0.0 - 1.0)
                            if match_score >= matching_threshold:
                                match_count += 1
                                match_id = f"m_{analysis_id}_{match_count:03d}"

                                # Save full frame thumbnail with bounding box overlay
                                annot_frame = frame.copy()
                                cv2.rectangle(annot_frame, (x1, y1), (x2, y2), (235, 99, 37), 2)
                                label = f"{track_id} {int(match_score*100)}%"
                                cv2.putText(annot_frame, label, (x1, max(20, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (235, 99, 37), 2)

                                frame_img_name = f"frame_{frame_idx}_{track_id}.jpg"
                                frame_img_path = evidence_folder / frame_img_name
                                cv2.imwrite(str(frame_img_path), annot_frame)

                                # Save tag crop thumbnail
                                tag_crop_name = f"tag_{frame_idx}_{track_id}.jpg"
                                tag_crop_path = evidence_folder / tag_crop_name
                                cv2.imwrite(str(tag_crop_path), upper_body_crop)

                                match_record = FrameMatch(
                                    id=match_id,
                                    analysisId=analysis_id,
                                    timestamp=timestamp,
                                    frameNumber=frame_idx,
                                    trackId=track_id,
                                    confidence=round(match_score, 2),
                                    boundingBox=BoundingBox(
                                        x=round(float(x1), 1),
                                        y=round(float(y1), 1),
                                        width=round(float(w), 1),
                                        height=round(float(h), 1)
                                    ),
                                    reviewState="unreviewed",
                                    frameImageUrl=f"/static/evidence/{analysis_id}/{frame_img_name}",
                                    tagCropUrl=f"/static/evidence/{analysis_id}/{tag_crop_name}"
                                )
                                db.add_match(match_record)

                    # Update progressive status periodically
                    if frames_analyzed % 20 == 0:
                        analysis.framesAnalyzed = frames_analyzed
                        db.update_analysis(analysis)

                frame_idx += 1

            cap.release()
            analysis.framesAnalyzed = frames_analyzed
            analysis.matchCount = match_count
            analysis.status = "complete"
            analysis.reviewStatus = "unreviewed" if match_count > 0 else "reviewed"
            db.update_analysis(analysis)
            print(f"Job {analysis_id} complete! Analyzed {frames_analyzed} frames, found {match_count} matches.")

        except Exception as e:
            print(f"Error processing video job {analysis_id}: {e}")
            analysis.status = "failed"
            db.update_analysis(analysis)
            if cap.isOpened():
                cap.release()

pipeline_service = VideoAnalysisPipeline()

