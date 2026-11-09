import json
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
from app.models import Analysis, FrameMatch, MatchReviewState
from app.config import BASE_DIR

DATA_FILE = BASE_DIR / "analyses_store.json"

class Database:
    def __init__(self):
        self.analyses: Dict[str, Analysis] = {}
        self.matches: Dict[str, List[FrameMatch]] = {}
        self._load_seed_data()

    def _load_seed_data(self):
        if DATA_FILE.exists():
            try:
                with open(DATA_FILE, "r") as f:
                    data = json.load(f)
                    for a_dict in data.get("analyses", []):
                        a_dict["uploadDate"] = datetime.fromisoformat(a_dict["uploadDate"])
                        analysis = Analysis(**a_dict)
                        self.analyses[analysis.id] = analysis
                    for m_dict in data.get("matches", []):
                        match = FrameMatch(**m_dict)
                        if match.analysisId not in self.matches:
                            self.matches[match.analysisId] = []
                        self.matches[match.analysisId].append(match)
                return
            except Exception as e:
                print(f"Error loading stored data: {e}")

        # Seed initial analyses matching the Angular UI mock data
        initial_analyses = [
            Analysis(
                id="a001",
                clipName="warehouse_cam_01_2024-01-15.mp4",
                uploadDate=datetime.fromisoformat("2024-01-15T09:23:00"),
                status="complete",
                duration="4:32",
                matchCount=7,
                reviewStatus="reviewed",
                framesAnalyzed=8160,
                modelVersion="v2.3.1"
            ),
            Analysis(
                id="a002",
                clipName="entrance_cam_feed_jan16.mp4",
                uploadDate=datetime.fromisoformat("2024-01-16T14:05:00"),
                status="complete",
                duration="2:15",
                matchCount=3,
                reviewStatus="in-progress",
                framesAnalyzed=4050,
                modelVersion="v2.3.1"
            ),
            Analysis(
                id="a003",
                clipName="loading_dock_footage_0117.mp4",
                uploadDate=datetime.fromisoformat("2024-01-17T08:45:00"),
                status="processing",
                duration="6:10",
                matchCount=0,
                reviewStatus="unreviewed",
                framesAnalyzed=3200,
                modelVersion="v2.3.1"
            ),
            Analysis(
                id="a004",
                clipName="perimeter_scan_night_0117.mp4",
                uploadDate=datetime.fromisoformat("2024-01-17T22:00:00"),
                status="queued",
                duration="10:00",
                matchCount=0,
                reviewStatus="unreviewed",
                framesAnalyzed=0,
                modelVersion="v2.3.1"
            ),
            Analysis(
                id="a005",
                clipName="office_corridor_jan14.mp4",
                uploadDate=datetime.fromisoformat("2024-01-14T11:30:00"),
                status="failed",
                duration="1:48",
                matchCount=0,
                reviewStatus="unreviewed",
                framesAnalyzed=0,
                modelVersion="v2.3.0"
            ),
            Analysis(
                id="a006",
                clipName="rooftop_cam_20240113.mp4",
                uploadDate=datetime.fromisoformat("2024-01-13T16:00:00"),
                status="complete",
                duration="3:55",
                matchCount=5,
                reviewStatus="unreviewed",
                framesAnalyzed=7050,
                modelVersion="v2.3.0"
            )
        ]

        for a in initial_analyses:
            self.analyses[a.id] = a

        # Initial seed matches
        initial_matches = [
            FrameMatch(id="m001", analysisId="a001", timestamp=15.4, frameNumber=462, trackId="TRK-001", confidence=0.94, boundingBox={"x": 120, "y": 85, "width": 60, "height": 90}, reviewState="confirmed"),
            FrameMatch(id="m002", analysisId="a001", timestamp=32.1, frameNumber=963, trackId="TRK-001", confidence=0.87, boundingBox={"x": 145, "y": 90, "width": 58, "height": 88}, reviewState="confirmed"),
            FrameMatch(id="m003", analysisId="a001", timestamp=48.7, frameNumber=1461, trackId="TRK-002", confidence=0.78, boundingBox={"x": 200, "y": 110, "width": 65, "height": 95}, reviewState="rejected", rejectionReason="False positive - shadow"),
            FrameMatch(id="m004", analysisId="a001", timestamp=72.3, frameNumber=2169, trackId="TRK-001", confidence=0.91, boundingBox={"x": 130, "y": 80, "width": 62, "height": 92}, reviewState="confirmed"),
            FrameMatch(id="m005", analysisId="a001", timestamp=95.6, frameNumber=2868, trackId="TRK-003", confidence=0.65, boundingBox={"x": 300, "y": 150, "width": 55, "height": 85}, reviewState="unreviewed"),
            FrameMatch(id="m006", analysisId="a001", timestamp=118.2, frameNumber=3546, trackId="TRK-003", confidence=0.72, boundingBox={"x": 310, "y": 155, "width": 57, "height": 87}, reviewState="unreviewed"),
            FrameMatch(id="m007", analysisId="a001", timestamp=145.9, frameNumber=4377, trackId="TRK-004", confidence=0.88, boundingBox={"x": 180, "y": 100, "width": 60, "height": 90}, reviewState="unreviewed"),
            FrameMatch(id="m013", analysisId="a002", timestamp=20.0, frameNumber=600, trackId="TRK-020", confidence=0.85, boundingBox={"x": 140, "y": 90, "width": 60, "height": 90}, reviewState="confirmed"),
            FrameMatch(id="m014", analysisId="a002", timestamp=55.5, frameNumber=1665, trackId="TRK-021", confidence=0.69, boundingBox={"x": 260, "y": 130, "width": 56, "height": 86}, reviewState="unreviewed"),
            FrameMatch(id="m015", analysisId="a002", timestamp=90.1, frameNumber=2703, trackId="TRK-020", confidence=0.90, boundingBox={"x": 148, "y": 88, "width": 61, "height": 91}, reviewState="unreviewed")
        ]

        for m in initial_matches:
            if m.analysisId not in self.matches:
                self.matches[m.analysisId] = []
            self.matches[m.analysisId].append(m)

        self.save()

    def save(self):
        try:
            data = {
                "analyses": [a.model_dump(mode="json") for a in self.analyses.values()],
                "matches": [m.model_dump(mode="json") for sublist in self.matches.values() for m in sublist]
            }
            with open(DATA_FILE, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            print(f"Error persisting data: {e}")

    def get_all_analyses(self) -> List[Analysis]:
        return list(self.analyses.values())

    def get_analysis(self, analysis_id: str) -> Optional[Analysis]:
        return self.analyses.get(analysis_id)

    def add_analysis(self, analysis: Analysis):
        self.analyses[analysis.id] = analysis
        self.save()

    def update_analysis(self, analysis: Analysis):
        self.analyses[analysis.id] = analysis
        self.save()

    def get_matches(self, analysis_id: str) -> List[FrameMatch]:
        return self.matches.get(analysis_id, [])

    def add_match(self, match: FrameMatch):
        if match.analysisId not in self.matches:
            self.matches[match.analysisId] = []
        self.matches[match.analysisId].append(match)
        # Update matchCount in analysis
        if match.analysisId in self.analyses:
            self.analyses[match.analysisId].matchCount = len(self.matches[match.analysisId])
        self.save()

    def update_match_review(self, match_id: str, state: MatchReviewState, reason: Optional[str] = None) -> Optional[FrameMatch]:
        for aid, match_list in self.matches.items():
            for m in match_list:
                if m.id == match_id:
                    m.reviewState = state
                    if reason:
                        m.rejectionReason = reason
                    elif state != "rejected":
                        m.rejectionReason = None
                    
                    # Update analysis reviewStatus
                    unreviewed = sum(1 for match in match_list if match.reviewState == "unreviewed")
                    confirmed = sum(1 for match in match_list if match.reviewState == "confirmed")
                    rejected = sum(1 for match in match_list if match.reviewState == "rejected")
                    
                    if unreviewed == 0:
                        self.analyses[aid].reviewStatus = "reviewed"
                    elif confirmed > 0 or rejected > 0:
                        self.analyses[aid].reviewStatus = "in-progress"
                    else:
                        self.analyses[aid].reviewStatus = "unreviewed"

                    self.save()
                    return m
        return None

db = Database()

