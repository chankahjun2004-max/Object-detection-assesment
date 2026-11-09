import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', redirectTo: 'analyses', pathMatch: 'full' },
  { path: 'analyses', loadComponent: () => import('./pages/analyses/analyses.component').then(m => m.AnalysesComponent) },
  { path: 'analyses/new', loadComponent: () => import('./pages/new-analysis/new-analysis.component').then(m => m.NewAnalysisComponent) },
  { path: 'analyses/:id', loadComponent: () => import('./pages/analysis-results/analysis-results.component').then(m => m.AnalysisResultsComponent) },
];
