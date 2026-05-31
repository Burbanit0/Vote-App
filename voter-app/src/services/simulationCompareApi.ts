import {
  ArrowCriteriaResult,
  BandwagonResult,
  IdeologyMapResult,
  MonteCarloResult,
  VoteStepsResult,
  MultiwinnerResult,
  RealElectionResult,
  RealElectionSummary,
  SimulationCompareResult,
  StrategicImpactPoint,
  CondorcetMatrixResult,
  SensitivityResult,
} from '../types';

import { apiGet, apiPost } from '../api/client';

export interface InformationModelConfig {
  enabled: boolean;
  media_bias: Record<string, number>;   // str(candidate_idx) → [-1, 1]
  voter_segments: {
    low_info: number;
    medium_info: number;
    high_info: number;
  };
}

export interface CompareParams {
  num_voters?: number;
  candidates?: string[];
  ideology_distribution?: string;
  information_model?: InformationModelConfig;
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
    return await apiPost<SimulationCompareResult>('/api/v2/simulations/compare', params);
  } catch (error) {
    console.error('Failed to run comparison simulation', error);
    throw error;
  }
};

export const runStrategicImpactAnalysis = async (
  params: StrategicImpactParams
): Promise<StrategicImpactPoint[]> => {
  try {
    const data = await apiPost<{ results: StrategicImpactPoint[] }>(
      '/api/v2/simulations/strategic-impact', params,
    );
    return data.results;
  } catch (error) {
    console.error('Failed to run strategic impact analysis', error);
    throw error;
  }
};

export const getCondorcetMatrix = async (
  params: CondorcetMatrixParams
): Promise<CondorcetMatrixResult> => {
  try {
    return await apiPost<CondorcetMatrixResult>('/api/v2/simulations/condorcet-matrix', params);
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
    return await apiPost<SensitivityResult>('/api/v2/simulations/sensitivity', params);
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
    return await apiPost<BandwagonResult>('/api/v2/simulations/bandwagon', params);
  } catch (error) {
    console.error('Failed to run bandwagon simulation', error);
    throw error;
  }
};

export const getArrowCriteria = async (
  params: CompareParams
): Promise<ArrowCriteriaResult> => {
  try {
    return await apiPost<ArrowCriteriaResult>('/api/v2/simulations/arrow-criteria', params);
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
    return await apiPost<MultiwinnerResult>('/api/v2/simulations/multiwinner', params);
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
    return await apiPost<MonteCarloResult>('/api/v2/simulations/monte-carlo', params);
  } catch (error) {
    console.error('Failed to run Monte Carlo simulation', error);
    throw error;
  }
};

export interface IdeologyMapParams {
  num_voters: number;
  candidates: { name: string; x: number; y: number }[];
  ideology: string;
  seed: number;
  method_a: string;
  method_b: string;
}

export const getIdeologyMap = async (
  params: IdeologyMapParams
): Promise<IdeologyMapResult> => {
  try {
    return await apiPost<IdeologyMapResult>('/api/v2/simulations/ideology-map', params);
  } catch (error) {
    console.error('Failed to fetch ideology map', error);
    throw error;
  }
};

export interface VoteStepsParams {
  method: string;
  num_voters: number;
  // Accept either name strings (backend auto-positions) or full candidate
  // objects with positions to match the main election simulation exactly.
  candidates: Array<string | { name: string; x: number; y: number }>;
  ideology: string;
  seed: number;
}

export const getVoteSteps = async (params: VoteStepsParams): Promise<VoteStepsResult> => {
  return apiPost<VoteStepsResult>('/api/v2/simulations/vote-steps', params);
};

export interface BlankHistoryPoint {
  year: number;
  blank_pct: number;
  context: string;
}

export interface BlankHistoryResult {
  country: string;
  display_name: string;
  note: string;
  series: BlankHistoryPoint[];
}

export const getBlankHistory = async (
  country: string,
): Promise<BlankHistoryResult> => {
  return apiGet<BlankHistoryResult>('/api/v2/simulations/blank-history', { country });
};

export const getRealElections = async (): Promise<RealElectionSummary[]> => {
  try {
    return await apiGet<RealElectionSummary[]>('/api/v2/simulations/real-elections');
  } catch (error) {
    console.error('Failed to fetch real elections list', error);
    throw error;
  }
};

export const analyzeRealElection = async (
  electionName: string,
  numVoters: number = 1000,
  blankVote: boolean = false,
): Promise<RealElectionResult> => {
  try {
    return await apiPost<RealElectionResult>('/api/v2/simulations/real-election', {
      election_name: electionName, num_voters: numVoters, blank_vote: blankVote,
    });
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

// ── Constitutional crisis ──────────────────────────────────────────────────

export interface ConstitutionalParams {
  initial_election: {
    candidates: ScenarioCandidate[];
    electorate: { num_voters: number; ideology_preset: string; dissatisfaction_rate: number };
    blank_rule: string;
  };
  blank_triggered: boolean;
  scenario_type: 'new_election' | 'provisional' | 'dissolution';
  params: Record<string, unknown>;
}

export interface ConstitutionalResult {
  scenario_type: string;
  // Scenario A
  round1?: ScenarioResult['with_blank'];
  round2?: ScenarioResult['with_blank'];
  round2_candidate_names?: string[];
  // Scenario B
  before_drift?: ScenarioResult['with_blank'];
  after_drift?: ScenarioResult['with_blank'];
  drift_applied?: number;
  duration?: number;
  // Scenario C
  initial_methods?: ScenarioResult['without_blank'];
  multiwinner?: Record<string, unknown>;
  uninominal_winner?: string | null;
  party_votes?: Record<string, number>;
  num_seats?: number;
  // Common
  conclusion: string;
}

export const runConstitutionalScenario = async (
  params: ConstitutionalParams
): Promise<ConstitutionalResult> => {
  try {
    return await apiPost<ConstitutionalResult>('/api/v2/simulations/constitutional-scenario', params);
  } catch (error) {
    console.error('Failed to run constitutional scenario', error);
    throw error;
  }
};

export const runScenario = async (params: ScenarioParams): Promise<ScenarioResult> => {
  try {
    return await apiPost<ScenarioResult>('/api/v2/simulations/scenario', params);
  } catch (error) {
    console.error('Failed to run scenario', error);
    throw error;
  }
};
