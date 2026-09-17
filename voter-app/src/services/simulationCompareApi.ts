import { MonteCarloResult, VoteStepsResult } from '../types';

import { apiPost } from '../api/client';

export interface MonteCarloParams {
  num_voters?: number;
  candidates?: string[];
  ideology_distribution?: string;
  num_runs?: number;
}

export const getMonteCarlo = (params: MonteCarloParams): Promise<MonteCarloResult> =>
  apiPost<MonteCarloResult>('/api/v2/simulations/monte-carlo', params);

export interface VoteStepsParams {
  method: string;
  num_voters: number;
  // Accept either name strings (backend auto-positions) or full candidate
  // objects with positions to match the main election simulation exactly.
  candidates: Array<string | { name: string; x: number; y: number }>;
  ideology: string;
  seed: number;
}

export const getVoteSteps = (params: VoteStepsParams): Promise<VoteStepsResult> =>
  apiPost<VoteStepsResult>('/api/v2/simulations/vote-steps', params);
