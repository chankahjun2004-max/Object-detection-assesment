from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field

AnalysisStatus = Literal['queued', 'processing', 'complete', 'failed']
ReviewStatus = Literal['unreviewed', 'in-progress', 'reviewed']
MatchReviewState = Literal['unreviewed', 'confirmed', 'rejected']

class BoundingBox(BaseModel):
    x: float
    y: float
    width: float
    height: float

class FrameMatch(BaseModel):
    id: str
    analysisId: str
    timestamp: float
    frameNumber: int
    trackId: str
    confidence: float
    boundingBox: BoundingBox
    reviewState: MatchReviewState = "unreviewed"
    rejectionReason: Optional[str] = None
    frameImageUrl: Optional[str] = None
    tagCropUrl: Optional[str] = None

class Analysis(BaseModel):
    id: str
    clipName: str
    uploadDate: datetime = Field(default_factory=datetime.now)
    status: AnalysisStatus = "queued"
    duration: str = "0:00"
    matchCount: int = 0
    reviewStatus: ReviewStatus = "unreviewed"
    framesAnalyzed: int = 0
    modelVersion: str = "v2.3.1"
    videoUrl: Optional[str] = None
    referenceImageUrl: Optional[str] = None

class MatchReviewUpdateRequest(BaseModel):
    reviewState: MatchReviewState
    rejectionReason: Optional[str] = None

class AnalysisSettings(BaseModel):
    frameSampling: int = 5
    detectionThreshold: float = 0.70
    matchingThreshold: float = 0.60
    enableTracking: bool = True
    nmsThreshold: float = 0.50
    minTagSize: int = 20
    maxTagSize: int = 200

