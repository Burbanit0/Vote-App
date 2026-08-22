// src/types.ts

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

export interface ScoreVote {
  voter_id: number;
  scores: Record<string, number>;
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

export interface ScoreVotingComparisonProps {
  scores: ScoreVote[];
  candidates: string[];
  results: ScoreVotingResults;
}

// --- Simulation scenarios ---

export interface ScenarioSummary {
  id: number;
  name: string;
  created_at: string;
  config: Record<string, unknown>;
}

/** Compact, display-ready summary of a saved scenario's results. */
export interface ScenarioResultsSummary {
  winners?: Record<string, string>;
  note?: string;
}

export interface ScenarioDetail extends ScenarioSummary {
  results: Record<string, unknown> | null;
  results_summary?: ScenarioResultsSummary | null;
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

// --- Monte Carlo ---

export interface MethodMonteCarloStats {
  winner_distribution: Record<string, number>;
  most_common_winner: string | null;
  winner_stability: number;
  bayesian_regret_mean: number | null;
  bayesian_regret_std: number | null;
  bayesian_regret_ci_95: [number | null, number | null];
  majority_satisfaction_mean: number | null;
  majority_satisfaction_ci_95: [number | null, number | null];
  condorcet_compliance_rate: number | null;
}

export interface MonteCarloResult {
  num_runs: number;
  num_voters_per_run: number;
  config: Record<string, any>;
  methods: Record<string, MethodMonteCarloStats>;
  condorcet_winner_exists_rate: number;
  inter_method_agreement: Record<string, number>;
}

// --- Real election analysis ---

export interface RealElectionSummary {
  key: string;
  name: string;
  year: number;
  country: string;
}

export interface RealElectionDivergence {
  method: string;
  winner: string | null;
  differs_from_plurality: boolean;
}

export interface BlankVoteRuleOutcome {
  blank_wins?: boolean;
  winner: string | null;
  triggered: boolean;
  consequence: string;
}

export interface BlankVoteAnalysis {
  estimated_blank_pct: number;
  competitive: BlankVoteRuleOutcome;
  threshold_30: BlankVoteRuleOutcome;
}

export interface MethodBlankRuleOutcome {
  winner: string | null;
  blank_triggered: boolean;
  consequence: string;
  blank_pct: number;
  rule: string;
}

export interface RealElectionResult {
  election: {
    key: string;
    name: string;
    year: number;
    country: string;
    description: string;
    source: string;
    candidates: { name: string; party: string }[];
    estimated_blank_pct?: number;
  };
  plurality_winner: string;
  first_round_results: Record<string, number>;
  methods: Record<string, string | null>;
  methods_with_blank?: Record<string, string | null>;
  methods_with_blank_rule?: Record<string, MethodBlankRuleOutcome>;
  divergences: RealElectionDivergence[];
  summary: {
    methods_with_different_winner: number;
    total_methods_with_winner: number;
  };
  blank_vote_analysis?: BlankVoteAnalysis;
}

// --- Multi-winner proportional methods ---

export interface ProportionalityMetrics {
  gallagher_index: number | null;
  largest_deviation: { party: string; deviation: number } | null;
  effective_parties_votes: number | null;
  effective_parties_seats: number | null;
}

export interface MethodSeats {
  seats: Record<string, number>;
  metrics: ProportionalityMetrics;
}

export interface MultiwinnerResult {
  dhondt: MethodSeats;
  sainte_lague: MethodSeats;
  largest_remainder_hare: MethodSeats;
  largest_remainder_droop: MethodSeats;
  stv?: { winners: string[]; seats: Record<string, number> };
  comparison: {
    most_proportional: string | null;
    least_proportional: string | null;
    gallagher_ranking: string[];
  };
  party_votes: Record<string, number>;
  num_seats: number;
}

// --- Bandwagon simulation ---

export interface BandwagonMethodData {
  winner: string | null;
  bayesian_regret: number | null;
}

export interface BandwagonRound {
  round: number;
  poll_standings: Record<string, number>;
  methods: Record<string, BandwagonMethodData>;
  voter_lean_distribution: {
    mean: number;
    std: number;
    polarization_index: number;
  };
}

export interface BandwagonResult {
  num_rounds: number;
  influence_strength: number;
  rounds: BandwagonRound[];
  convergence_round: number | null;
  amplification_by_method: Record<string, number>;
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

export interface InformationModelResult {
  enabled: boolean;
  sincere_winner?: string | null;
  perceived_winner?: string | null;
  information_gap?: number;
  sincere_condorcet_winner?: string | null;
  winners_differ?: boolean;
}

export interface SimulationCompareResult {
  condorcet_winner: string | null;
  methods: Record<string, MethodComparison>;
  information_model?: InformationModelResult;
}

export interface StrategicImpactPoint {
  strategic_pct: number;
  methods: Record<string, number | null>;
}

// ── Vote steps ────────────────────────────────────────────────────────────────

export interface IRVRound {
  round: number;
  scores?: Record<string, number>;
  eliminated?: string | null;
  transfers?: Record<string, number> | null;
  winner?: string;
}

export interface BordaStep {
  rank: number;
  points_awarded: number;
  tally: Record<string, number>;
}

export type VoteStepsResult =
  | { method: 'irv'; rounds: IRVRound[] }
  | { method: 'borda'; num_candidates: number; steps: BordaStep[]; winner: string | null }
  | { method: 'plurality'; first_choices: Record<string, number>; winner: string | null }
  | {
      method: 'schulze';
      duel_matrix: Record<string, Record<string, number>>;
      path_matrix: Record<string, Record<string, number>>;
      winner: string | null;
    }
  | {
      method: 'approval';
      threshold_used: number;
      approval_scores: Record<string, number>;
      winner: string | null;
    };

// ── Ideology map ──────────────────────────────────────────────────────────────

export interface IdeologyMapVoter {
  id: number;
  x: number;
  y: number;
  utility_winner_a: number;
  utility_winner_b: number;
  prefers_a: boolean;
}

export interface IdeologyMapCandidate {
  name: string;
  x: number;
  y: number;
  party: string;
}

export interface IdeologyMapResult {
  voters: IdeologyMapVoter[];
  candidates: IdeologyMapCandidate[];
  winner_a: string | null;
  winner_b: string | null;
  method_a: string;
  method_b: string;
  condorcet_winner: string | null;
  pct_better_off_with_a: number;
  pct_better_off_with_b: number;
}
