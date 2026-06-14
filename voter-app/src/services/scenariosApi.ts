import { ScenarioDetail, ScenarioSummary } from '../types';
import { apiDelete, apiGet, apiPost } from '../api/client';

// scenarios live on /api/v2/scenarios (FastAPI). The apiClient auth middleware
// attaches the Bearer token, so no per-call getAuthHeader() is needed.
const ROOT = '/api/v2/scenarios';

export const listScenarios = async (): Promise<ScenarioSummary[]> => {
  return apiGet<ScenarioSummary[]>(ROOT);
};

export const saveScenario = async (
  name: string,
  config: Record<string, unknown>,
  results?: Record<string, unknown> | null
): Promise<ScenarioDetail> => {
  return apiPost<ScenarioDetail>(ROOT, { name, config, results: results ?? null });
};

export const getScenario = async (id: number): Promise<ScenarioDetail> => {
  return apiGet<ScenarioDetail>(`${ROOT}/${id}`);
};

export const deleteScenario = async (id: number): Promise<void> => {
  await apiDelete(`${ROOT}/${id}`);
};
