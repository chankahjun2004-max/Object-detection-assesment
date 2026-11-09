import shutil
import uuid
import csv
import io
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, HTTPException, Response
from fastapi.responses import JSONResponse, StreamingResponse

from app.config import UPLOADS_DIR, REFERENCES_DIR, BASE_DIR
from app.models import Analysis, FrameMatch, MatchReviewUpdateRequest
from app.database import db
from app.pipeline import pipeline_service

router = APIRouter(prefix="/api", tags=["Analyses"])

@router.get("/analyses", response_model=List[Analysis])
def get_all_analyses():
    """Retrieve all video analysis jobs."""
    return db.get_all_analyses()

@router.get("/analyses/{analysis_id}", response_model=Analysis)
def get_analysis_by_id(analysis_id: str):
    """Retrieve status and metadata for a specific analysis job."""
    analysis = db.get_analysis(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis

@router.get("/analyses/{analysis_id}/matches", response_model=List[FrameMatch])
def get_analysis_matches(analysis_id: str):
    """Retrieve all frame matches for an analysis job."""
    return db.get_matches(analysis_id)

@router.patch("/matches/{match_id}", response_model=FrameMatch)
def update_match_review_state(match_id: str, request: MatchReviewUpdateRequest):
    """Update human verification decision (confirmed / rejected) for a candidate match."""
    updated = db.update_match_review(match_id, request.reviewState, request.rejectionReason)
    if not updated:
        raise HTTPException(status_code=404, detail="Match not found")
    return updated

@router.post("/analyses", response_model=Analysis)
async def create_analysis(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...),
    referenceTag: Optional[UploadFile] = File(None),
    frameSampling: int = Form(5),
    detectionThreshold: float = Form(0.70),
    matchingThreshold: float = Form(0.60),
    enableTracking: bool = Form(True),
    nmsThreshold: float = Form(0.50),
    minTagSize: int = Form(20),
    maxTagSize: int = Form(200)
):
    """
    Upload a video clip (MP4) and optional target tag reference image,
    creating a queued job and triggering background computer vision processing.
    """
    analysis_id = "a" + uuid.uuid4().hex[:6]
    
    # Save video file
    video_ext = Path(video.filename).suffix or ".mp4"
    saved_video_path = UPLOADS_DIR / f"{analysis_id}_{video.filename}"
    with open(saved_video_path, "wb") as buffer:
        shutil.copyfileobj(video.file, buffer)

    # Save target reference image if provided
    saved_ref_path = None
    ref_url = None
    if referenceTag and referenceTag.filename:
        ref_ext = Path(referenceTag.filename).suffix or ".png"
        saved_ref_path = REFERENCES_DIR / f"{analysis_id}_ref{ref_ext}"
        with open(saved_ref_path, "wb") as buffer:
            shutil.copyfileobj(referenceTag.file, buffer)
        ref_url = f"/static/references/{saved_ref_path.name}"

    # Threshold normalization if sent as percentages (e.g. 70 -> 0.70)
    det_thresh = detectionThreshold / 100.0 if detectionThreshold > 1.0 else detectionThreshold
    match_thresh = matchingThreshold / 100.0 if matchingThreshold > 1.0 else matchingThreshold

    # Create new analysis entry
    new_analysis = Analysis(
        id=analysis_id,
        clipName=video.filename or "uploaded_video.mp4",
        status="queued",
        duration="0:00",
        matchCount=0,
        reviewStatus="unreviewed",
        framesAnalyzed=0,
        modelVersion="v2.3.1",
        videoUrl=f"/static/uploads/{saved_video_path.name}",
        referenceImageUrl=ref_url
    )
    db.add_analysis(new_analysis)

    # Dispatch background worker
    background_tasks.add_task(
        pipeline_service.process_video_job,
        analysis_id=analysis_id,
        video_path=str(saved_video_path),
        reference_image_path=str(saved_ref_path) if saved_ref_path else None,
        frame_sampling=frameSampling,
        detection_threshold=det_thresh,
        matching_threshold=match_thresh,
        enable_tracking=enableTracking,
        nms_threshold=nmsThreshold,
        min_tag_size=minTagSize,
        max_tag_size=maxTagSize
    )

    return new_analysis

@router.post("/analyses/analyze-sample", response_model=Analysis)
async def analyze_sample_video(
    background_tasks: BackgroundTasks,
    frameSampling: int = 5,
    detectionThreshold: float = 0.50,
    matchingThreshold: float = 0.40,
    enableTracking: bool = True
):
    """
    Convenience endpoint to directly analyze the workspace sample.mp4 clip!
    """
    sample_file = BASE_DIR.parent / "sample.mp4"
    if not sample_file.exists():
        raise HTTPException(status_code=404, detail="sample.mp4 not found in workspace")

    analysis_id = "a" + uuid.uuid4().hex[:6]
    target_video_path = UPLOADS_DIR / f"{analysis_id}_sample.mp4"
    shutil.copyfile(sample_file, target_video_path)

    new_analysis = Analysis(
        id=analysis_id,
        clipName="sample.mp4",
        status="queued",
        duration="0:53",
        matchCount=0,
        reviewStatus="unreviewed",
        framesAnalyzed=0,
        modelVersion="v2.3.1",
        videoUrl=f"/static/uploads/{target_video_path.name}"
    )
    db.add_analysis(new_analysis)

    det_thresh = detectionThreshold / 100.0 if detectionThreshold > 1.0 else detectionThreshold
    match_thresh = matchingThreshold / 100.0 if matchingThreshold > 1.0 else matchingThreshold

    background_tasks.add_task(
        pipeline_service.process_video_job,
        analysis_id=analysis_id,
        video_path=str(target_video_path),
        reference_image_path=None,
        frame_sampling=frameSampling,
        detection_threshold=det_thresh,
        matching_threshold=match_thresh,
        enable_tracking=enableTracking
    )

    return new_analysis

@router.get("/analyses/{analysis_id}/export")
def export_analysis_results(analysis_id: str, format: str = "json"):
    """
    Export results in JSON or CSV format.
    """
    analysis = db.get_analysis(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    matches = db.get_matches(analysis_id)

    if format.lower() == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Match ID", "Timestamp (s)", "Frame Number", "Track ID", "Confidence", "Review State", "Rejection Reason", "BBox X", "BBox Y", "BBox Width", "BBox Height"])
        for m in matches:
            writer.writerow([
                m.id,
                m.timestamp,
                m.frameNumber,
                m.trackId,
                m.confidence,
                m.reviewState,
                m.rejectionReason or "",
                m.boundingBox.x,
                m.boundingBox.y,
                m.boundingBox.width,
                m.boundingBox.height
            ])
        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode("utf-8")),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=analysis_{analysis_id}.csv"}
        )

    # Default JSON
    result = {
        "analysis": analysis.model_dump(mode="json"),
        "matches": [m.model_dump(mode="json") for m in matches]
    }
    return JSONResponse(content=result)

