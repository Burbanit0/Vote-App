import axios from 'axios';
import { ScenarioDetail, ScenarioSummary } from '../types';

const API_BASE_URL = (process.env.VITE_API_URL) || 'http://localhost:4433';

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

export const listScenarios = async (): Promise<ScenarioSummary[]> => {
  const response = await axios.get<ScenarioSummary[]>(
    `${API_BASE_URL}/api/scenarios/`,
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
    `${API_BASE_URL}/api/scenarios/`,
    { name, config, results: results ?? null },
    { headers: getAuthHeader() }
  );
  return response.data;
};

export const getScenario = async (id: number): Promise<ScenarioDetail> => {
  const response = await axios.get<ScenarioDetail>(
    `${API_BASE_URL}/api/scenarios/${id}`,
    { headers: getAuthHeader() }
  );
  return response.data;
};

export const deleteScenario = async (id: number): Promise<void> => {
  await axios.delete(
    `${API_BASE_URL}/api/scenarios/${id}`,
    { headers: getAuthHeader() }
  );
};
