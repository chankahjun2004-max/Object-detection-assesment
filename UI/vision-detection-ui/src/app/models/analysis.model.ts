export type AnalysisStatus = 'queued' | 'processing' | 'complete' | 'failed';
export type ReviewStatus = 'unreviewed' | 'in-progress' | 'reviewed';
export type MatchReviewState = 'unreviewed' | 'confirmed' | 'rejected';

export interface Analysis {
  id: string;
  clipName: string;
  uploadDate: Date;
  status: AnalysisStatus;
  duration: string; // e.g. "2:34"
  matchCount: number;
  reviewStatus: ReviewStatus;
  framesAnalyzed: number;
  modelVersion: string;
}

export interface FrameMatch {
  id: string;
  analysisId: string;
  timestamp: number; // seconds
  frameNumber: number;
  trackId: string;
  confidence: number; // 0-1
  boundingBox: { x: number; y: number; width: number; height: number };
  reviewState: MatchReviewState;
  rejectionReason?: string;
  frameImageUrl?: string;
  tagCropUrl?: string;
}

