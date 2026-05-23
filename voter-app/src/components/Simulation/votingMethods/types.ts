/**
 * Shared props for every per-method visualisation. Each sub-component
 * (PluralityVisualization, BordaVisualization, IRVVisualization, …)
 * implements its own counting/elimination logic and renders the result
 * with Chart.js, but they all accept the same shape from the parent.
 */
export interface VotingMethodVisualizationProps {
  /** Method slug — informational only (used by the dispatcher above). */
  method:     string;
  /** Full voter rankings: each voter ranks every candidate top-to-bottom. */
  rankings:   Array<{ voter_id: number; ranking: string[] }>;
  /** Candidate names in their original order. */
  candidates: string[];
}

/** Standard 8-colour palette reused across visualisations for consistency. */
export const VIZ_COLORS = [
  '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0',
  '#9966FF', '#FF9F40', '#8AC24A', '#EA5F89',
];
