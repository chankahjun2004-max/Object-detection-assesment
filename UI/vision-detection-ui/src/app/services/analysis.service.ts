import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of, catchError, map, tap } from 'rxjs';
import { Analysis, FrameMatch, MatchReviewState } from '../models/analysis.model';

@Injectable({
  providedIn: 'root'
})
export class AnalysisService {
  private http = inject(HttpClient);
  public apiUrl = 'http://localhost:8000/api';
  public baseUrl = 'http://localhost:8000';

  private fallbackAnalyses: Analysis[] = [
    {
      id: 'a001',
      clipName: 'warehouse_cam_01_2024-01-15.mp4',
      uploadDate: new Date('2024-01-15T09:23:00'),
      status: 'complete',
      duration: '4:32',
      matchCount: 7,
      reviewStatus: 'reviewed',
      framesAnalyzed: 8160,
      modelVersion: 'v2.3.1'
    },
    {
      id: 'a002',
      clipName: 'entrance_cam_feed_jan16.mp4',
      uploadDate: new Date('2024-01-16T14:05:00'),
      status: 'complete',
      duration: '2:15',
      matchCount: 3,
      reviewStatus: 'in-progress',
      framesAnalyzed: 4050,
      modelVersion: 'v2.3.1'
    },
    {
      id: 'a003',
      clipName: 'loading_dock_footage_0117.mp4',
      uploadDate: new Date('2024-01-17T08:45:00'),
      status: 'processing',
      duration: '6:10',
      matchCount: 0,
      reviewStatus: 'unreviewed',
      framesAnalyzed: 3200,
      modelVersion: 'v2.3.1'
    },
    {
      id: 'a004',
      clipName: 'perimeter_scan_night_0117.mp4',
      uploadDate: new Date('2024-01-17T22:00:00'),
      status: 'queued',
      duration: '10:00',
      matchCount: 0,
      reviewStatus: 'unreviewed',
      framesAnalyzed: 0,
      modelVersion: 'v2.3.1'
    },
    {
      id: 'a005',
      clipName: 'office_corridor_jan14.mp4',
      uploadDate: new Date('2024-01-14T11:30:00'),
      status: 'failed',
      duration: '1:48',
      matchCount: 0,
      reviewStatus: 'unreviewed',
      framesAnalyzed: 0,
      modelVersion: 'v2.3.0'
    },
    {
      id: 'a006',
      clipName: 'rooftop_cam_20240113.mp4',
      uploadDate: new Date('2024-01-13T16:00:00'),
      status: 'complete',
      duration: '3:55',
      matchCount: 5,
      reviewStatus: 'unreviewed',
      framesAnalyzed: 7050,
      modelVersion: 'v2.3.0'
    }
  ];

  private fallbackMatches: FrameMatch[] = [
    { id: 'm001', analysisId: 'a001', timestamp: 15.4, frameNumber: 462, trackId: 'TRK-001', confidence: 0.94, boundingBox: { x: 120, y: 85, width: 60, height: 90 }, reviewState: 'confirmed' },
    { id: 'm002', analysisId: 'a001', timestamp: 32.1, frameNumber: 963, trackId: 'TRK-001', confidence: 0.87, boundingBox: { x: 145, y: 90, width: 58, height: 88 }, reviewState: 'confirmed' },
    { id: 'm003', analysisId: 'a001', timestamp: 48.7, frameNumber: 1461, trackId: 'TRK-002', confidence: 0.78, boundingBox: { x: 200, y: 110, width: 65, height: 95 }, reviewState: 'rejected', rejectionReason: 'False positive - shadow' },
    { id: 'm004', analysisId: 'a001', timestamp: 72.3, frameNumber: 2169, trackId: 'TRK-001', confidence: 0.91, boundingBox: { x: 130, y: 80, width: 62, height: 92 }, reviewState: 'confirmed' },
    { id: 'm005', analysisId: 'a001', timestamp: 95.6, frameNumber: 2868, trackId: 'TRK-003', confidence: 0.65, boundingBox: { x: 300, y: 150, width: 55, height: 85 }, reviewState: 'unreviewed' },
    { id: 'm006', analysisId: 'a001', timestamp: 118.2, frameNumber: 3546, trackId: 'TRK-003', confidence: 0.72, boundingBox: { x: 310, y: 155, width: 57, height: 87 }, reviewState: 'unreviewed' },
    { id: 'm007', analysisId: 'a001', timestamp: 145.9, frameNumber: 4377, trackId: 'TRK-004', confidence: 0.88, boundingBox: { x: 180, y: 100, width: 60, height: 90 }, reviewState: 'unreviewed' }
  ];

  getAnalyses(): Observable<Analysis[]> {
    return this.http.get<Analysis[]>(`${this.apiUrl}/analyses`).pipe(
      map(list => list.map(a => ({ ...a, uploadDate: new Date(a.uploadDate) }))),
      catchError(() => of([...this.fallbackAnalyses]))
    );
  }

  getAnalysis(id: string): Observable<Analysis | undefined> {
    return this.http.get<Analysis>(`${this.apiUrl}/analyses/${id}`).pipe(
      map(a => ({ ...a, uploadDate: new Date(a.uploadDate) })),
      catchError(() => {
        const found = this.fallbackAnalyses.find(a => a.id === id);
        return of(found);
      })
    );
  }

  getMatches(analysisId: string): Observable<FrameMatch[]> {
    return this.http.get<FrameMatch[]>(`${this.apiUrl}/analyses/${analysisId}/matches`).pipe(
      map(matches => matches.map(m => ({
        ...m,
        frameImageUrl: m.frameImageUrl ? (m.frameImageUrl.startsWith('http') ? m.frameImageUrl : `${this.baseUrl}${m.frameImageUrl}`) : undefined,
        tagCropUrl: m.tagCropUrl ? (m.tagCropUrl.startsWith('http') ? m.tagCropUrl : `${this.baseUrl}${m.tagCropUrl}`) : undefined
      }))),
      catchError(() => of(this.fallbackMatches.filter(m => m.analysisId === analysisId)))
    );
  }

  updateMatchReview(matchId: string, state: MatchReviewState, reason?: string): Observable<FrameMatch | undefined> {
    return this.http.patch<FrameMatch>(`${this.apiUrl}/matches/${matchId}`, {
      reviewState: state,
      rejectionReason: reason
    }).pipe(
      catchError(() => {
        const match = this.fallbackMatches.find(m => m.id === matchId);
        if (match) {
          match.reviewState = state;
          if (reason) match.rejectionReason = reason;
          else if (state !== 'rejected') delete match.rejectionReason;
        }
        return of(match);
      })
    );
  }

  createAnalysis(
    data: Partial<Analysis>,
    videoFile?: File,
    referenceFile?: File,
    options?: any
  ): Observable<Analysis> {
    if (videoFile) {
      const formData = new FormData();
      formData.append('video', videoFile, videoFile.name);
      if (referenceFile) {
        formData.append('referenceTag', referenceFile, referenceFile.name);
      }
      if (options) {
        if (options.frameSampling) formData.append('frameSampling', options.frameSampling.toString());
        if (options.detectionThreshold) formData.append('detectionThreshold', options.detectionThreshold.toString());
        if (options.matchingThreshold) formData.append('matchingThreshold', options.matchingThreshold.toString());
        if (options.enableTracking !== undefined) formData.append('enableTracking', options.enableTracking.toString());
      }

      return this.http.post<Analysis>(`${this.apiUrl}/analyses`, formData).pipe(
        map(a => ({ ...a, uploadDate: new Date(a.uploadDate) })),
        catchError(() => {
          const fallback: Analysis = {
            id: 'a' + Math.floor(Math.random() * 1000).toString().padStart(3, '0'),
            clipName: videoFile.name,
            uploadDate: new Date(),
            status: 'queued',
            duration: '0:00',
            matchCount: 0,
            reviewStatus: 'unreviewed',
            framesAnalyzed: 0,
            modelVersion: 'v2.3.1'
          };
          this.fallbackAnalyses.unshift(fallback);
          return of(fallback);
        })
      );
    }

    const fallback: Analysis = {
      id: 'a' + Math.floor(Math.random() * 1000).toString().padStart(3, '0'),
      clipName: data.clipName || 'untitled.mp4',
      uploadDate: new Date(),
      status: 'queued',
      duration: '0:00',
      matchCount: 0,
      reviewStatus: 'unreviewed',
      framesAnalyzed: 0,
      modelVersion: 'v2.3.1'
    };
    this.fallbackAnalyses.unshift(fallback);
    return of(fallback);
  }
}
