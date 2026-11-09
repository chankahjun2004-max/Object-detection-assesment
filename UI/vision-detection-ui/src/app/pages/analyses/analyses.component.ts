import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { AnalysisService } from '../../services/analysis.service';
import { Analysis, AnalysisStatus, ReviewStatus } from '../../models/analysis.model';

@Component({
  selector: 'app-analyses',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule],
  templateUrl: './analyses.component.html',
  styleUrl: './analyses.component.scss'
})
export class AnalysesComponent implements OnInit {
  private analysisService = inject(AnalysisService);

  analyses: Analysis[] = [];
  filteredAnalyses: Analysis[] = [];
  loading = true;

  // Filters
  statusFilter: string = 'all';
  dateFrom: string = '';
  dateTo: string = '';
  reviewFilter: string = 'all';

  // Pagination
  currentPage = 1;
  itemsPerPage = 5;
  totalPages = 1;
  paginatedAnalyses: Analysis[] = [];

  ngOnInit(): void {
    this.loadAnalyses();
  }

  loadAnalyses(): void {
    this.loading = true;
    this.analysisService.getAnalyses().subscribe(data => {
      this.analyses = data;
      this.applyFilters();
      this.loading = false;
    });
  }

  applyFilters(): void {
    let result = [...this.analyses];

    if (this.statusFilter !== 'all') {
      result = result.filter(a => a.status === this.statusFilter);
    }

    if (this.reviewFilter !== 'all') {
      if (this.reviewFilter === 'unreviewed') {
        result = result.filter(a => a.reviewStatus === 'unreviewed');
      } else if (this.reviewFilter === 'reviewed') {
        result = result.filter(a => a.reviewStatus === 'reviewed' || a.reviewStatus === 'in-progress');
      }
    }

    if (this.dateFrom) {
      const from = new Date(this.dateFrom);
      result = result.filter(a => a.uploadDate >= from);
    }

    if (this.dateTo) {
      const to = new Date(this.dateTo);
      to.setHours(23, 59, 59, 999);
      result = result.filter(a => a.uploadDate <= to);
    }

    this.filteredAnalyses = result;
    this.totalPages = Math.ceil(result.length / this.itemsPerPage);
    this.currentPage = 1;
    this.updatePage();
  }

  updatePage(): void {
    const start = (this.currentPage - 1) * this.itemsPerPage;
    this.paginatedAnalyses = this.filteredAnalyses.slice(start, start + this.itemsPerPage);
  }

  goToPage(page: number): void {
    if (page < 1 || page > this.totalPages) return;
    this.currentPage = page;
    this.updatePage();
  }

  get pageNumbers(): number[] {
    return Array.from({ length: this.totalPages }, (_, i) => i + 1);
  }

  getStatusClass(status: AnalysisStatus): string {
    return `badge badge-${status}`;
  }

  getReviewClass(reviewStatus: ReviewStatus): string {
    const cls = reviewStatus === 'in-progress' ? 'in-progress' : reviewStatus;
    return `badge badge-${cls}`;
  }

  getStatusLabel(status: AnalysisStatus): string {
    const labels: Record<AnalysisStatus, string> = {
      queued: 'Queued',
      processing: 'Processing',
      complete: 'Complete',
      failed: 'Failed'
    };
    return labels[status];
  }

  getReviewLabel(status: ReviewStatus): string {
    const labels: Record<ReviewStatus, string> = {
      unreviewed: 'Unreviewed',
      'in-progress': 'In Progress',
      reviewed: 'Reviewed'
    };
    return labels[status];
  }

  get startItem(): number {
    return this.filteredAnalyses.length === 0 ? 0 : (this.currentPage - 1) * this.itemsPerPage + 1;
  }

  get endItem(): number {
    return Math.min(this.currentPage * this.itemsPerPage, this.filteredAnalyses.length);
  }
}
