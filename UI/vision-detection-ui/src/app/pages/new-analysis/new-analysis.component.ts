import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { AnalysisService } from '../../services/analysis.service';

@Component({
  selector: 'app-new-analysis',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './new-analysis.component.html',
  styleUrl: './new-analysis.component.scss'
})
export class NewAnalysisComponent {
  private router = inject(Router);
  private analysisService = inject(AnalysisService);

  // Upload state
  isDragging = false;
  uploadedFile: File | null = null;
  uploadProgress = 0;
  isUploading = false;
  uploadError = '';

  // Target Reference
  targetImageUrl: string | null = null;
  targetFile: File | null = null;

  // Settings
  frameSampling = 5;
  detectionThreshold = 70;
  matchingThreshold = 60;
  enableTracking = true;
  showAdvanced = false;

  // Advanced settings
  minTagSize = 20;
  maxTagSize = 200;
  nmsThreshold = 0.5;

  // Submission
  isSubmitting = false;

  get canStart(): boolean {
    return this.uploadedFile !== null && !this.isUploading && !this.isSubmitting;
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging = true;
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging = false;
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging = false;

    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
      this.handleFile(files[0]);
    }
  }

  onFileSelect(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.handleFile(input.files[0]);
    }
  }

  handleFile(file: File): void {
    this.uploadError = '';

    if (!file.type.startsWith('video/')) {
      this.uploadError = 'Invalid file type. Please upload a video file (MP4).';
      return;
    }

    const maxSize = 500 * 1024 * 1024; // 500MB
    if (file.size > maxSize) {
      this.uploadError = `File too large (${this.formatFileSize(file.size)}). Maximum size is 500MB.`;
      return;
    }

    this.uploadedFile = file;
    this.simulateUpload();
  }

  simulateUpload(): void {
    this.isUploading = true;
    this.uploadProgress = 0;

    const interval = setInterval(() => {
      this.uploadProgress += Math.random() * 15 + 5;
      if (this.uploadProgress >= 100) {
        this.uploadProgress = 100;
        this.isUploading = false;
        clearInterval(interval);
      }
    }, 150);
  }

  formatFileSize(bytes: number): string {
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(1)} MB`;
  }

  formatDuration(seconds: number): string {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  }

  onTargetImageSelect(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      const file = input.files[0];
      this.targetFile = file;
      const reader = new FileReader();
      reader.onload = (e) => {
        this.targetImageUrl = e.target?.result as string;
      };
      reader.readAsDataURL(file);
    }
  }

  removeFile(): void {
    this.uploadedFile = null;
    this.uploadProgress = 0;
    this.isUploading = false;
    this.uploadError = '';
  }

  startAnalysis(): void {
    if (!this.canStart) return;

    this.isSubmitting = true;
    this.analysisService.createAnalysis(
      { clipName: this.uploadedFile!.name },
      this.uploadedFile!,
      this.targetFile || undefined,
      {
        frameSampling: this.frameSampling,
        detectionThreshold: this.detectionThreshold,
        matchingThreshold: this.matchingThreshold,
        enableTracking: this.enableTracking
      }
    ).subscribe(analysis => {
      this.isSubmitting = false;
      this.router.navigate(['/analyses']);
    });
  }

  goBack(): void {
    this.router.navigate(['/analyses']);
  }
}

