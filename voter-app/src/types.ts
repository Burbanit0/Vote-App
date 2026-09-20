// --- Monte Carlo ---

interface MethodMonteCarloStats {
  winner_distribution: Record<string, number>;
  /** Every candidate tied for most runs won; empty when no run had a winner. */
  most_common_winner: string[];
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

// ── Vote steps ────────────────────────────────────────────────────────────────

export interface IRVRound {
  round: number;
  scores?: Record<string, number>;
  eliminated?: string | null;
  transfers?: Record<string, number> | null;
  /** On the final round; null when every remaining candidate ties for last. */
  winner?: string | null;
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
