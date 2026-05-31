import { apiPost } from '../api/client';

// ── Types ──────────────────────────────────────────────────────────────────

export type VariantParam = 'num_voters' | 'num_candidates' | 'blank_pct' | 'polarization';

export interface WhatIfBase {
  num_candidates?: number;
  num_voters?: number;
  blank_pct?: number;
  ideology_distribution?: string;
}

export interface WhatIfRequest {
  base: WhatIfBase;
  variant_param: VariantParam;
  variant_values: number[];
}

export interface MethodResult {
  winner: string | null;
  score: number | null;   // majority_satisfaction × 100
  regret: number | null;  // bayesian_regret
}

export interface WhatIfDataPoint {
  value: number;
  methods: Record<string, MethodResult>;
  condorcet_winner: string | null;
  error?: string;
}

export interface WhatIfResponse {
  variant_param: VariantParam;
  results: WhatIfDataPoint[];
}

// ── API call ───────────────────────────────────────────────────────────────

export async function runWhatIf(params: WhatIfRequest): Promise<WhatIfResponse> {
  return apiPost<WhatIfResponse>('/api/v2/simulations/what-if', params);
}
