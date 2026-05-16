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

// ── Divergence types ──────────────────────────────────────────────────────────

export interface DivergenceMethodResult {
  winner:           string | null;
  winner_after_rule?: string | null;
  blank_triggered?:  boolean;
}

export interface DivergenceRunResult {
  methods:               Record<string, DivergenceMethodResult>;
  inter_method_agreement: number;
  condorcet_winner:      string | null;
  blank_rate?:           number;
}

export interface DivergenceResult {
  without_blank:       DivergenceRunResult;
  with_blank:          DivergenceRunResult;
  delta_agreement:     number;
  methods_changed:     string[];
  pct_methods_changed: number;
  blank_rule:          string;
}

export interface DivergenceParams {
  candidates:  { name: string; x: number; y: number }[];
  num_voters:  number;
  ideology:    string;
  seed:        number;
  blank_vote:  {
    rule:      string;
    contagion: { enabled: boolean; beta: number; gamma: number; network: string };
  };
}

export async function fetchDivergence(params: DivergenceParams): Promise<DivergenceResult> {
  const response = await axios.post<DivergenceResult>(`${API_BASE}/api/election/divergence`, params);
  return response.data;
}

// ── Campaign sensitivity types ────────────────────────────────────────────────

export interface CampaignSnapshotMethod {
  winner:           string | null;
  vote_share:       number;
  winner_after_rule?: string | null;
}

export interface CampaignSnapshot {
  day:                   number;
  methods:               Record<string, CampaignSnapshotMethod>;
  inter_method_agreement: number;
}

export interface MethodStability {
  winner_changes:  number;
  final_winner:    string | null;
  stability_score: number;
}

export interface CampaignSensitivityResult {
  snapshots:           CampaignSnapshot[];
  method_stability:    Record<string, MethodStability>;
  most_stable_method:  string | null;
  least_stable_method: string | null;
}

export interface CampaignSensitivityParams {
  candidates:    { name: string; x: number; y: number }[];
  num_voters:    number;
  ideology:      string;
  seed:          number;
  campaign:      { num_days: number; polling_effect: number };
  blank_vote:    { enabled: boolean; rule: string; contagion: { enabled: boolean; beta: number; gamma: number; network: string } };
  snapshot_days: (number | 'final')[];
}

export async function fetchCampaignSensitivity(
  params: CampaignSensitivityParams
): Promise<CampaignSensitivityResult> {
  const response = await axios.post<CampaignSensitivityResult>(
    `${API_BASE}/api/election/campaign-sensitivity`,
    params
  );
  return response.data;
}
