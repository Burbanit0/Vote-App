import axios from 'axios';
import { ElectionConfig } from '../context/ElectionContext';

const API_BASE = process.env.VITE_API_URL || 'http://localhost:4433';

export interface MethodResult {
  winner:                string | null;
  winner_with_blank?:    string | null;
  blank_triggered?:      boolean;
  bayesian_regret:       number | null;
  majority_satisfaction: number | null;
  condorcet_consistent:  boolean | null;
}

export interface ElectionResult {
  config:                 ElectionConfig;
  voters_snapshot:        { id: number; x: number; y: number; blank_threshold_final: number }[];
  candidates:             { name: string; x: number; y: number; party: string }[];
  methods:                Record<string, MethodResult>;
  condorcet_winner:       string | null;
  blank_rate:             number;
  campaign_trajectory:    Record<string, unknown> | null;
  inter_method_agreement: number;
  condorcet_exists:       boolean;
}

export async function simulateElection(config: ElectionConfig): Promise<ElectionResult> {
  const response = await axios.post<ElectionResult>(`${API_BASE}/api/election/simulate`, config);
  return response.data;
}
