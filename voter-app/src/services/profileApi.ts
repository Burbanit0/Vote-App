import { apiPost } from '../api/client';
import { ElectionConfig, PlaygroundState } from '../stores/useElectionStore';

// Lab reshape P1 — the profile-as-interface endpoint. Every method runs over a
// preference profile built from a user-chosen source; cycle_rate is the
// paradox read-out that exposes how conclusions depend on the assumptions.

export interface ProfileSimulateResult {
  methods: Record<string, { winner: string | null }>;
  condorcet_winner: string | null;
  inter_method_agreement: number;
  cycle_rate: number;
  candidate_names: string[];
  display_points: number[][];
  candidate_points: number[][] | null;
  num_voters: number;
}

/** Build the `extra="forbid"` request body from shared electorate + playground knobs. */
export function toProfilePayload(config: ElectionConfig, pg: PlaygroundState) {
  return {
    source: pg.prefSource,
    candidates: config.candidates.map((c) => ({ name: c.name, x: c.x, y: c.y })),
    num_voters: config.num_voters,
    dims: pg.space.dims,
    valence: pg.space.valenceEnabled,
    behavior: pg.behavior,
    source_params: pg.prefParams,
    seed: config.seed,
  };
}

export async function runProfileSimulate(
  config: ElectionConfig,
  pg: PlaygroundState
): Promise<ProfileSimulateResult> {
  return apiPost<ProfileSimulateResult>(
    '/api/v2/election/profile-simulate',
    toProfilePayload(config, pg)
  );
}
