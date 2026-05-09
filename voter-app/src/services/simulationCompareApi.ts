import axios from 'axios';
import {
  ArrowCriteriaResult,
  BandwagonResult,
  MonteCarloResult,
  MultiwinnerResult,
  RealElectionResult,
  RealElectionSummary,
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

export interface BandwagonParams extends CompareParams {
  num_rounds?: number;
  influence_strength?: number;
  seed?: number | null;
}

export const getBandwagonAnalysis = async (
  params: BandwagonParams
): Promise<BandwagonResult> => {
  try {
    const response = await axios.post<BandwagonResult>(
      `${API_BASE_URL}/simulations/bandwagon`,
      params,
      { headers: getAuthHeader() }
    );
    return response.data;
  } catch (error) {
    console.error('Failed to run bandwagon simulation', error);
    throw error;
  }
};

export const getArrowCriteria = async (
  params: CompareParams
): Promise<ArrowCriteriaResult> => {
  try {
    const response = await axios.post<ArrowCriteriaResult>(
      `${API_BASE_URL}/simulations/arrow-criteria`,
      params,
      { headers: getAuthHeader() }
    );
    return response.data;
  } catch (error) {
    console.error('Failed to run Arrow criteria check', error);
    throw error;
  }
};

export interface MultiwinnerParams {
  party_votes: Record<string, number>;
  num_seats: number;
  mode?: 'proportional' | 'stv';
}

export const getMultiwinner = async (
  params: MultiwinnerParams
): Promise<MultiwinnerResult> => {
  try {
    const response = await axios.post<MultiwinnerResult>(
      `${API_BASE_URL}/simulations/multiwinner`,
      params,
      { headers: getAuthHeader() }
    );
    return response.data;
  } catch (error) {
    console.error('Failed to run multi-winner analysis', error);
    throw error;
  }
};

export interface MonteCarloParams extends CompareParams {
  num_runs?: number;
}

export const getMonteCarlo = async (
  params: MonteCarloParams
): Promise<MonteCarloResult> => {
  try {
    const response = await axios.post<MonteCarloResult>(
      `${API_BASE_URL}/simulations/monte-carlo`,
      params,
      { headers: getAuthHeader() }
    );
    return response.data;
  } catch (error) {
    console.error('Failed to run Monte Carlo simulation', error);
    throw error;
  }
};

export const getRealElections = async (): Promise<RealElectionSummary[]> => {
  try {
    const response = await axios.get<RealElectionSummary[]>(
      `${API_BASE_URL}/simulations/real-elections`,
      { headers: getAuthHeader() }
    );
    return response.data;
  } catch (error) {
    console.error('Failed to fetch real elections list', error);
    throw error;
  }
};

export const analyzeRealElection = async (
  electionName: string,
  numVoters: number = 1000
): Promise<RealElectionResult> => {
  try {
    const response = await axios.post<RealElectionResult>(
      `${API_BASE_URL}/simulations/real-election`,
      { election_name: electionName, num_voters: numVoters },
      { headers: getAuthHeader() }
    );
    return response.data;
  } catch (error) {
    console.error('Failed to analyse real election', error);
    throw error;
  }
};

// ── Scenario builder ───────────────────────────────────────────────────────

export interface ScenarioCandidate {
  name: string;
  ideology: number;
  positions: { economy: number; environment: number; social: number };
  is_blank?: boolean;
}

export interface ScenarioParams {
  candidates: ScenarioCandidate[];
  electorate: { num_voters: number; ideology_preset: string; dissatisfaction_rate: number };
  blank_rule: string;
  methods: string[];
}

export interface ScenarioMethodResult {
  winner: string | null;
  bayesian_regret: number | null;
  blank_rule_applied?: {
    winner: string | null;
    blank_triggered: boolean;
    consequence: string;
    blank_pct: number;
    rule: string;
  };
}

export interface ScenarioResult {
  without_blank: {
    condorcet_winner: string | null;
    methods: Record<string, Pick<ScenarioMethodResult, 'winner' | 'bayesian_regret'>>;
  };
  with_blank: {
    condorcet_winner: string | null;
    blank_pct: number;
    methods: Record<string, ScenarioMethodResult>;
  };
}

export const runScenario = async (params: ScenarioParams): Promise<ScenarioResult> => {
  try {
    const response = await axios.post<ScenarioResult>(
      `${API_BASE_URL}/simulations/scenario`,
      params,
      { headers: getAuthHeader() }
    );
    return response.data;
  } catch (error) {
    console.error('Failed to run scenario', error);
    throw error;
  }
};
