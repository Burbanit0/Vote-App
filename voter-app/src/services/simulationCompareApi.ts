import axios from 'axios';
import {
  SimulationCompareResult,
  StrategicImpactPoint,
  CondorcetMatrixResult,
  SensitivityResult,
} from '../types';

const API_BASE_URL = 'http://localhost:4433';

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

export interface CompareParams {
  num_voters?: number;
  candidates?: string[];
  ideology_distribution?: string;
}

export interface StrategicImpactParams extends CompareParams {
  strategic_percentages?: number[];
}

export interface CondorcetMatrixParams extends CompareParams {
  ideology_distribution?: string;
}

export const runComparisonSimulation = async (
  params: CompareParams
): Promise<SimulationCompareResult> => {
  try {
    const response = await axios.post<SimulationCompareResult>(
      `${API_BASE_URL}/simulations/compare`,
      params,
      { headers: getAuthHeader() }
    );
    return response.data;
  } catch (error) {
    console.error('Failed to run comparison simulation', error);
    throw error;
  }
};

export const runStrategicImpactAnalysis = async (
  params: StrategicImpactParams
): Promise<StrategicImpactPoint[]> => {
  try {
    const response = await axios.post<{ results: StrategicImpactPoint[] }>(
      `${API_BASE_URL}/simulations/strategic-impact`,
      params,
      { headers: getAuthHeader() }
    );
    return response.data.results;
  } catch (error) {
    console.error('Failed to run strategic impact analysis', error);
    throw error;
  }
};

export const getCondorcetMatrix = async (
  params: CondorcetMatrixParams
): Promise<CondorcetMatrixResult> => {
  try {
    const response = await axios.post<CondorcetMatrixResult>(
      `${API_BASE_URL}/simulations/condorcet-matrix`,
      params,
      { headers: getAuthHeader() }
    );
    return response.data;
  } catch (error) {
    console.error('Failed to get Condorcet matrix', error);
    throw error;
  }
};

export interface SensitivityParams {
  base_config: {
    num_voters?: number;
    candidates?: string[];
    ideology_distribution?: string;
  };
  variable: 'ideology_distribution' | 'num_voters' | 'strategic_pct';
  values: (string | number)[];
}

export const getSensitivityAnalysis = async (
  params: SensitivityParams
): Promise<SensitivityResult> => {
  try {
    const response = await axios.post<SensitivityResult>(
      `${API_BASE_URL}/simulations/sensitivity`,
      params,
      { headers: getAuthHeader() }
    );
    return response.data;
  } catch (error) {
    console.error('Failed to run sensitivity analysis', error);
    throw error;
  }
};
