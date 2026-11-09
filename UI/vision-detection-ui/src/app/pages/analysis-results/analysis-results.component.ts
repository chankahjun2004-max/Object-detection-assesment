import { Component, OnInit, inject, ElementRef, ViewChild, AfterViewInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { AnalysisService } from '../../services/analysis.service';
import { Analysis, FrameMatch, MatchReviewState } from '../../models/analysis.model';

@Component({
  selector: 'app-analysis-results',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './analysis-results.component.html',
  styleUrl: './analysis-results.component.scss'
})
export class AnalysisResultsComponent implements OnInit, AfterViewInit {
  @ViewChild('frameCanvas') frameCanvas!: ElementRef<HTMLCanvasElement>;

  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private analysisService = inject(AnalysisService);

  analysis: Analysis | null = null;
  matches: FrameMatch[] = [];
  selectedMatch: FrameMatch | null = null;
  currentFrameIndex = 0;
  loading = true;
  rejectionReason = '';
  showRejectionInput = false;

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id') ?? '';
    this.analysisService.getAnalysis(id).subscribe(analysis => {
      this.analysis = analysis ?? null;
    });
    this.analysisService.getMatches(id).subscribe(matches => {
      this.matches = matches;
      if (matches.length > 0) {
        this.selectMatch(matches[0]);
      }
      this.loading = false;
    });
  }

  ngAfterViewInit(): void {
    // Draw initial frame after view initializes
    if (this.selectedMatch) {
      setTimeout(() => this.drawFrame(), 100);
    }
  }

  selectMatch(match: FrameMatch): void {
    this.selectedMatch = match;
    this.currentFrameIndex = this.matches.indexOf(match);
    this.showRejectionInput = false;
    this.rejectionReason = '';
    setTimeout(() => this.drawFrame(), 50);
  }

  prevFrame(): void {
    if (this.currentFrameIndex > 0) {
      this.selectMatch(this.matches[this.currentFrameIndex - 1]);
    }
  }

  nextFrame(): void {
    if (this.currentFrameIndex < this.matches.length - 1) {
      this.selectMatch(this.matches[this.currentFrameIndex + 1]);
    }
  }

  drawFrame(): void {
    if (!this.frameCanvas || !this.selectedMatch) return;
    const canvas = this.frameCanvas.nativeElement;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const W = canvas.width;
    const H = canvas.height;

    if (this.selectedMatch.frameImageUrl) {
      const img = new Image();
      img.crossOrigin = 'anonymous';
      img.onload = () => {
        ctx.drawImage(img, 0, 0, W, H);
        this.renderOverlay(ctx, W, H, img.naturalWidth, img.naturalHeight);
      };
      img.src = this.selectedMatch.frameImageUrl;
    } else {
      this.renderFallbackScene(ctx, W, H);
      this.renderOverlay(ctx, W, H, 960, 720);
    }
  }

  private renderFallbackScene(ctx: CanvasRenderingContext2D, W: number, H: number): void {
    ctx.fillStyle = '#0a0f1e';
    ctx.fillRect(0, 0, W, H);

    ctx.strokeStyle = 'rgba(30, 77, 140, 0.15)';
    ctx.lineWidth = 1;
    for (let x = 0; x < W; x += 40) {
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke();
    }
    for (let y = 0; y < H; y += 40) {
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke();
    }

    ctx.fillStyle = 'rgba(13, 27, 42, 0.8)';
    ctx.fillRect(0, H * 0.6, W, H * 0.4);

    ctx.fillStyle = 'rgba(37, 99, 235, 0.08)';
    ctx.fillRect(80, 100, 120, 200);
    ctx.fillRect(400, 80, 100, 220);
  }

  private renderOverlay(ctx: CanvasRenderingContext2D, W: number, H: number, sourceW: number = 960, sourceH: number = 720): void {
    if (!this.selectedMatch) return;

    // Frame label
    ctx.fillStyle = 'rgba(255,255,255,0.85)';
    ctx.font = '12px monospace';
    ctx.fillText(`Frame #${this.selectedMatch.frameNumber}`, 12, 20);
    ctx.fillText(`t = ${this.selectedMatch.timestamp.toFixed(1)}s`, 12, 36);

    // Coordinate scaling
    const bb = this.selectedMatch.boundingBox;
    const scaleX = (sourceW > 0 && bb.x + bb.width > W) ? (W / sourceW) : 1.0;
    const scaleY = (sourceH > 0 && bb.y + bb.height > H) ? (H / sourceH) : 1.0;

    const bx = bb.x * scaleX;
    const by = bb.y * scaleY;
    const bw = bb.width * scaleX;
    const bh = bb.height * scaleY;

    const color = this.getBoxColor(this.selectedMatch);

    // Shadow glow
    ctx.shadowColor = color;
    ctx.shadowBlur = 12;

    ctx.strokeStyle = color;
    ctx.lineWidth = 2.5;
    ctx.setLineDash([]);
    ctx.strokeRect(bx, by, bw, bh);

    ctx.shadowBlur = 0;

    // Corner decorations
    const cs = 10;
    ctx.lineWidth = 3;
    [[bx, by], [bx + bw - cs, by], [bx, by + bh - cs], [bx + bw - cs, by + bh - cs]].forEach(([cx, cy]) => {
      ctx.strokeRect(cx, cy, cs, cs);
    });

    // Label background
    const labelText = `${this.selectedMatch.trackId} · ${(this.selectedMatch.confidence * 100).toFixed(0)}%`;
    ctx.font = 'bold 11px monospace';
    const lw = ctx.measureText(labelText).width;
    ctx.fillStyle = color;
    ctx.fillRect(bx, Math.max(0, by - 20), lw + 12, 20);
    ctx.fillStyle = '#fff';
    ctx.fillText(labelText, bx + 6, Math.max(14, by - 6));

    // Confidence indicator bar at bottom
    ctx.fillStyle = 'rgba(0,0,0,0.6)';
    ctx.fillRect(0, H - 24, W, 24);
    ctx.fillStyle = color;
    ctx.fillRect(0, H - 24, W * this.selectedMatch.confidence, 24);
    ctx.fillStyle = 'rgba(255,255,255,0.9)';
    ctx.font = '10px monospace';
    ctx.fillText(`Confidence: ${(this.selectedMatch.confidence * 100).toFixed(1)}%`, 8, H - 8);
  }

  getBoxColor(match: FrameMatch): string {
    switch (match.reviewState) {
      case 'confirmed': return '#10b981';
      case 'rejected': return '#ef4444';
      default: return '#2563eb';
    }
  }

  confirmMatch(match: FrameMatch): void {
    this.analysisService.updateMatchReview(match.id, 'confirmed').subscribe(updated => {
      if (updated) {
        match.reviewState = 'confirmed';
        delete match.rejectionReason;
        this.drawFrame();
      }
    });
  }

  startRejectMatch(match: FrameMatch): void {
    if (this.selectedMatch?.id !== match.id) {
      this.selectMatch(match);
    }
    this.showRejectionInput = true;
    this.rejectionReason = match.rejectionReason ?? '';
  }

  submitRejection(match: FrameMatch): void {
    this.analysisService.updateMatchReview(match.id, 'rejected', this.rejectionReason || undefined).subscribe(updated => {
      if (updated) {
        match.reviewState = 'rejected';
        match.rejectionReason = this.rejectionReason || undefined;
        this.showRejectionInput = false;
        this.rejectionReason = '';
        this.drawFrame();
      }
    });
  }

  cancelRejection(): void {
    this.showRejectionInput = false;
    this.rejectionReason = '';
  }

  formatTimestamp(seconds: number): string {
    const m = Math.floor(seconds / 60);
    const s = (seconds % 60).toFixed(1);
    return `${m}:${Number(s) < 10 ? '0' : ''}${s}`;
  }

  get confirmedCount(): number {
    return this.matches.filter(m => m.reviewState === 'confirmed').length;
  }

  get rejectedCount(): number {
    return this.matches.filter(m => m.reviewState === 'rejected').length;
  }

  get unreviewedCount(): number {
    return this.matches.filter(m => m.reviewState === 'unreviewed').length;
  }

  downloadJSON(): void {
    const data = JSON.stringify({ analysis: this.analysis, matches: this.matches }, null, 2);
    this.downloadFile(data, 'analysis-results.json', 'application/json');
  }

  downloadCSV(): void {
    const header = 'Match ID,Timestamp,Frame,Track ID,Confidence,Review State,Rejection Reason\n';
    const rows = this.matches.map(m =>
      `${m.id},${m.timestamp},${m.frameNumber},${m.trackId},${m.confidence},${m.reviewState},${m.rejectionReason ?? ''}`
    ).join('\n');
    this.downloadFile(header + rows, 'analysis-results.csv', 'text/csv');
  }

  downloadReviewSummary(): void {
    const summary = `Review Summary
==============
Analysis: ${this.analysis?.clipName}
Total Matches: ${this.matches.length}
Confirmed: ${this.confirmedCount}
Rejected: ${this.rejectedCount}
Unreviewed: ${this.unreviewedCount}

Confirmed Matches:
${this.matches.filter(m => m.reviewState === 'confirmed').map(m => `  - ${m.trackId} at ${this.formatTimestamp(m.timestamp)} (${(m.confidence * 100).toFixed(0)}% confidence)`).join('\n')}

Rejected Matches:
${this.matches.filter(m => m.reviewState === 'rejected').map(m => `  - ${m.trackId} at ${this.formatTimestamp(m.timestamp)} | Reason: ${m.rejectionReason ?? 'Not specified'}`).join('\n')}
`;
    this.downloadFile(summary, 'review-summary.txt', 'text/plain');
  }

  private downloadFile(content: string, filename: string, type: string): void {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  goBack(): void {
    this.router.navigate(['/analyses']);
  }
}

