import axios from 'axios';

const API = process.env.VITE_API_URL || 'http://localhost:4433';

export interface GalleryScenario {
  id: number;
  title: string;
  description: string;
  tags: string[];
  views: number;
  is_featured: boolean;
  created_at: string;
  results_summary: Record<string, unknown>;
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

// Phase 4.5.a.1: gallery now lives on /api/v2/scenarios/gallery (FastAPI).
// Routes are exact-match — no trailing slashes — and Pydantic enforces
// per_page ≤ 50 and limit ≤ 20 server-side.
const ROOT = `${API}/api/v2/scenarios/gallery`;

export const galleryApi = {
  list: (params: { page?: number; per_page?: number; sort?: string; tag?: string } = {}) =>
    axios.get<GalleryPage>(ROOT, { params })
      .then((r) => r.data),

  featured: () =>
    axios.get<GalleryScenario[]>(`${ROOT}/featured`)
      .then((r) => r.data),

  get: (id: number) =>
    axios.get<GalleryScenario>(`${ROOT}/${id}`)
      .then((r) => r.data),

  create: (payload: CreateGalleryPayload) =>
    axios.post<GalleryScenario>(ROOT, payload)
      .then((r) => r.data),
};
