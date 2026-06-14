import { apiGet, apiPost } from '../api/client';
import type { ScenarioResultsSummary } from '../types';

export interface GalleryScenario {
  id: number;
  title: string;
  description: string;
  tags: string[];
  views: number;
  is_featured: boolean;
  created_at: string;
  results_summary: ScenarioResultsSummary;
  params?: Record<string, unknown>;
}

export interface GalleryPage {
  items: GalleryScenario[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface CreateGalleryPayload {
  title: string;
  description: string;
  params?: Record<string, unknown>;
  results_summary?: Record<string, unknown>;
  tags?: string[];
}

// Phase 4.5.a.1: gallery lives on /api/v2/scenarios/gallery (FastAPI).
// Routes are exact-match — no trailing slashes — and Pydantic enforces
// per_page ≤ 50 and limit ≤ 20 server-side.
const ROOT = '/api/v2/scenarios/gallery';

export const galleryApi = {
  list: (params: { page?: number; per_page?: number; sort?: string; tag?: string } = {}) =>
    apiGet<GalleryPage>(ROOT, params),

  featured: () => apiGet<GalleryScenario[]>(`${ROOT}/featured`),

  get: (id: number) => apiGet<GalleryScenario>(`${ROOT}/${id}`),

  create: (payload: CreateGalleryPayload) => apiPost<GalleryScenario>(ROOT, payload),
};
