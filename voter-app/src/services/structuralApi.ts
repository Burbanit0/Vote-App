import { apiPost } from '../api/client';
import { ElectionConfig } from '../stores/useElectionStore';

// Frontier FC-2 — structural (un)fairness: malapportionment, efficiency gap,
// Penrose square-root council, cumulative vs bloc at-large voting.

export interface MalapportionmentOut {
  pop_per_seat_ratio: number;
  gallagher_equal: number | null;
  gallagher_skewed: number | null;
  min_share_majority_equal: number;
  min_share_majority_skewed: number;
}

export interface EfficiencyGapOut {
  party_a: string;
  party_b: string;
  gap: number;
  wasted_a: number;
  wasted_b: number;
}

export interface CumulativeOut {
  at_large_seats: number;
  largest_party: string;
  seats_bloc: Record<string, number>;
  seats_cumulative: Record<string, number>;
  minority_seats_bloc: number;
  minority_seats_cumulative: number;
}

export interface StructuralFairnessResult {
  districts: number;
  malapportionment: MalapportionmentOut;
  efficiency_gap: EfficiencyGapOut;
  penrose: Record<string, number>;
  cumulative: CumulativeOut;
}

export async function runStructuralFairness(
  config: ElectionConfig,
  malapportionment: number,
  districts = 20,
  atLargeSeats = 5
): Promise<StructuralFairnessResult> {
  return apiPost<StructuralFairnessResult>('/api/v2/election/structural-fairness', {
    parties: config.candidates.map((c) => ({ name: c.name, x: c.x, y: c.y })),
    num_voters: config.num_voters,
    ideology: config.ideology,
    seed: config.seed,
    districts,
    malapportionment,
    at_large_seats: atLargeSeats,
  });
}
