// src/types.ts

export interface Party {
  id: number;
  name: string;
  description: string;
}

export interface PartyMembersProps {
  partyId: number;
}

export interface User {
  id: number;
  access_token: string;
  username: string;
  role: string;
  created_at: string;
  user_id: number;
  first_name: string;
  last_name: string;
}

export interface Profile_ {
  id: number;
  username: string;
  first_name: string;
  last_name: string;
  role: string;
  is_admin: boolean;
  party_id: number | null;
}

// --- Simulation types ---

export interface CandidateSimu {
  id: number;
  name: string;
  party: string;
  party_lean: number;
  ideology_position: number;
  policies: Record<string, number>;
  charisma: number;
  scandals: number;
  campaign_funds: number;
  experience: number;
  popularity: number;
}

export type Gender = 'male' | 'female';
export type Region = 'urban' | 'suburban' | 'rural';
export type Income = 'low' | 'middle' | 'high';
export type PartySimu = 'Green' | 'Conservative' | 'Liberal' | 'Independent';
export type Education = 'none' | 'high_school' | 'bachelor' | 'master' | 'phd';
export type Employment = 'employed' | 'unemployed' | 'self_employed' | 'retired';
/** @deprecated Use Employment */
export type Employement = Employment;
export type Family = 'single' | 'with_children' | 'retired';
export type Ethnicity = 'native' | 'immigrant';
export type Religion = 'religious' | 'non_religious';

export interface VoterSimu {
  id: number;
  age: number;
  region: Region;
  income: Income;
  gender: Gender;
  education: Education;
  employment_status: Employment;
  religion: Religion;
  family_status: Family;
  ethnicity_immigration: Ethnicity;
  political_lean: number;
  political_lean_normalized: number;
  issue_priorities: Record<string, number>;
  issue_positions: Record<string, number>;
  party_loyalty: number;
  preferred_party: PartySimu;
  likelihood_to_vote: number;
  mood: number;
  strategic_propensity: number;
  voting_style: 'sincere' | 'strategic';
}

export interface ScoreVotingResult {
  method: string;
  winner?: string;
  details: any;
}

export interface ScoreVotingResults {
  simple_score: ScoreVotingResult;
  star_voting: ScoreVotingResult;
  median_voting: ScoreVotingResult;
  mean_median_hybrid: ScoreVotingResult;
  variance_based: ScoreVotingResult;
  score_distribution: ScoreVotingResult;
  bayesian_regret: ScoreVotingResult;
}

// --- Simulation scenarios ---

export interface ScenarioSummary {
  id: number;
  name: string;
  created_at: string;
  config: Record<string, any>;
}

export interface ScenarioDetail extends ScenarioSummary {
  results: Record<string, any> | null;
}

// --- Sensitivity analysis ---

export interface SensitivityPoint {
  value: string | number;
  condorcet_winner: string | null;
  winners_by_method: Record<string, string | null>;
  regret_by_method: Record<string, number | null>;
  error?: string;
}

export interface SensitivityResult {
  variable: string;
  values: (string | number)[];
  results: SensitivityPoint[];
}

// --- Condorcet matrix ---

export interface CondorcetDuel {
  pct_a: number;
  pct_b: number;
  winner: string;
}

export interface CondorcetMatrixResult {
  candidates: string[];
  matrix: Record<string, Record<string, CondorcetDuel>>;
  condorcet_winner: string | null;
  condorcet_cycles: string[][];
}

// --- Arrow criteria ---

export interface MethodCriteria {
  winner: string | null;
  condorcet_winner: boolean | null;
  condorcet_loser: boolean | null;
  monotonicity: boolean | null;
  iia: boolean | null;
  iia_violation_rate: number | null;
  majority: boolean | null;
  reversal_symmetry: boolean | null;
}

export interface ArrowCriteriaResult {
  methods: Record<string, MethodCriteria>;
  summary: {
    most_criteria_satisfied: string;
    least_criteria_satisfied: string;
    criteria_satisfaction_count: Record<string, number>;
  };
}

// --- Simulation comparison ---

export interface MethodComparison {
  winner: string | null;
  bayesian_regret: number | null;
  condorcet_consistent: boolean | null;
  majority_satisfaction: number | null;
  strategic_vulnerability: number | null;
}

export interface SimulationCompareResult {
  condorcet_winner: string | null;
  methods: Record<string, MethodComparison>;
}

export interface StrategicImpactPoint {
  strategic_pct: number;
  methods: Record<string, number | null>;
}
