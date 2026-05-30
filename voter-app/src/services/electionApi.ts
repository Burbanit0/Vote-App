import axios from 'axios';
import { ElectionConfig } from '../context/ElectionContext';
import { apiPath } from '../api/apiVersion';

const API_BASE = process.env.VITE_API_URL || 'http://localhost:4434';

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
  // Routed to FastAPI /api/v2/election/simulate when migrated; falls back to
  // Flask /api/election/simulate via the rollback switch (see apiVersion.ts).
  const response = await axios.post<ElectionResult>(
    `${API_BASE}${apiPath('election/simulate')}`,
    config,
  );
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
  const response = await axios.post<DivergenceResult>(
    `${API_BASE}${apiPath('election/divergence')}`,
    params,
  );
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

// ── Combined effects types ────────────────────────────────────────────────────

export interface CombinedEffectsCombination {
  id:                      string;
  blank:                   boolean;
  campaign:                boolean;
  information_model:       boolean;
  plurality_winner:        string | null;
  condorcet_winner:        string | null;
  inter_method_agreement:  number;
  winner_differs_from_base: boolean;
}

export interface CombinedEffectsResult {
  base_winner:               string | null;
  combinations:              CombinedEffectsCombination[];
  factor_deltas:             Record<string, number>;  // % points
  most_disruptive_factor:    string;
  least_disruptive_factor:   string;
  max_disruption_combination: string;
}

export async function fetchCombinedEffects(
  params: Record<string, unknown>
): Promise<CombinedEffectsResult> {
  const response = await axios.post<CombinedEffectsResult>(
    `${API_BASE}${apiPath('election/combined-effects')}`,
    params,
  );
  return response.data;
}

// ── Interpret types ───────────────────────────────────────────────────────────

export interface MethodGroup {
  winner:  string;
  methods: string[];
  pct:     number;
}

export interface InterpretResult {
  headline:           string;
  condorcet_analysis: string;
  divergence_reason:  string;
  method_groups:      MethodGroup[];
  best_by_regret:     string | null;
  worst_by_regret:    string | null;
  blank_analysis:     string | null;
  pedagogical_note:   string;
  key_facts:          string[];
}

export async function interpretElection(
  simulateResult: ElectionResult,
  lang: 'fr' | 'en' = 'fr'
): Promise<InterpretResult> {
  const response = await axios.post<InterpretResult>(
    `${API_BASE}${apiPath('election/interpret')}`,
    { ...simulateResult, lang }
  );
  return response.data;
}

export async function fetchCampaignSensitivity(
  params: CampaignSensitivityParams
): Promise<CampaignSensitivityResult> {
  const response = await axios.post<CampaignSensitivityResult>(
    `${API_BASE}${apiPath('election/campaign-sensitivity')}`,
    params,
  );
  return response.data;
}
