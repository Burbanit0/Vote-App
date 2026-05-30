import axios from 'axios';
import { ScenarioDetail, ScenarioSummary } from '../types';
import { apiPath } from '../api/apiVersion';

const API_BASE_URL = (process.env.VITE_API_URL) || 'http://localhost:4434';

function getAuthHeader(): Record<string, string> {
  const userString = localStorage.getItem('user');
  if (!userString) return {};
  try {
    const token = JSON.parse(userString).access_token;
    return token ? { Authorization: `Bearer ${token}` } : {};
  } catch {
    return {};
  }
}

// `scenarios` is migrated to FastAPI; `scenarios/${id}` resolves the same way
// via the prefix match in apiPath().
const scenariosRoot = () => `${API_BASE_URL}${apiPath('scenarios')}`;

export const listScenarios = async (): Promise<ScenarioSummary[]> => {
  const response = await axios.get<ScenarioSummary[]>(
    scenariosRoot(),
    { headers: getAuthHeader() }
  );
  return response.data;
};

export const saveScenario = async (
  name: string,
  config: Record<string, any>,
  results?: Record<string, any> | null
): Promise<ScenarioDetail> => {
  const response = await axios.post<ScenarioDetail>(
    scenariosRoot(),
    { name, config, results: results ?? null },
    { headers: getAuthHeader() }
  );
  return response.data;
};

export const getScenario = async (id: number): Promise<ScenarioDetail> => {
  const response = await axios.get<ScenarioDetail>(
    `${scenariosRoot()}/${id}`,
    { headers: getAuthHeader() }
  );
  return response.data;
};

export const deleteScenario = async (id: number): Promise<void> => {
  await axios.delete(
    `${scenariosRoot()}/${id}`,
    { headers: getAuthHeader() }
  );
};
