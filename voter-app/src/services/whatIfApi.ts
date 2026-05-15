import axios from 'axios';

const API_BASE_URL = process.env.VITE_API_URL || 'http://localhost:4433';

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
  const { data } = await axios.post<WhatIfResponse>(
    `${API_BASE_URL}/simulations/what-if`,
    params,
  );
  return data;
}
