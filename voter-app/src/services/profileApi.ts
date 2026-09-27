import { apiPost } from '../api/client';
import { ElectionConfig, PlaygroundState } from '../stores/useElectionStore';

// Lab reshape P1 — the profile-as-interface endpoint. Every method runs over a
// preference profile built from a user-chosen source; cycle_rate is the
// paradox read-out that exposes how conclusions depend on the assumptions.

export interface ProfileSimulateResult {
  methods: Record<
    string,
    { winner: string | null; strategic_vulnerability?: number | null; no_show?: boolean | null }
  >;
  condorcet_winner: string | null;
  inter_method_agreement: number;
  cycle_rate: number;
  candidate_names: string[];
  display_points: number[][];
  candidate_points: number[][] | null;
  num_voters: number;
  /** Share of the electorate that voted (1 = full turnout). */
  turnout_rate: number;
  // FA-1 — the ballot layer
  ballot_type: string;
  ballot_expressiveness: number;
  ballot_cognitive_load: number;
  /** Voter #0's projected ballot (candidate → expressed value). */
  sample_ballot: Record<string, number>;
  /** Methods whose winner differs from the full-information ballot. */
  winner_flips: string[];
  /** Methods that cannot honestly run on this ballot (excluded). */
  incompatible_methods: string[];
}

/** Build the `extra="forbid"` request body from shared electorate + playground knobs. */
function toProfilePayload(config: ElectionConfig, pg: PlaygroundState, computeStrategic = false) {
  return {
    source: pg.prefSource,
    candidates: config.candidates.map((c) => ({ name: c.name, x: c.x, y: c.y, z: c.z ?? 0 })),
    num_voters: config.num_voters,
    dims: pg.space.dims,
    valence: pg.space.valenceEnabled,
    behavior: pg.behavior,
    source_params: pg.prefParams,
    ballot: {
      type: pg.ballot.type,
      truncate_at: pg.ballot.type === 'rank_truncated' ? pg.ballot.truncate_at : null,
      score_levels: pg.ballot.score_levels,
    },
    turnout: { model: pg.turnout.model, intensity: pg.turnout.intensity },
    electorate:
      pg.electorate.mode === 'composed'
        ? {
            mode: 'composed' as const,
            correlation: pg.electorate.correlation,
            noise: pg.electorate.noise,
            communities: pg.electorate.communities.map((c) => ({
              id: c.id,
              label: c.label,
              x: c.x,
              y: c.y,
              z: c.z ?? 0,
              spread: c.spread,
              weight: c.weight,
              turnout: c.turnout,
            })),
          }
        : null,
    compute_strategic: computeStrategic,
    seed: config.seed,
  };
}

/** `computeStrategic` opts into the slow per-method Gibbard–Satterthwaite
 * manipulability pass (the on-demand strategic module); off for the live call. */
export async function runProfileSimulate(
  config: ElectionConfig,
  pg: PlaygroundState,
  computeStrategic = false
): Promise<ProfileSimulateResult> {
  return apiPost<ProfileSimulateResult>(
    '/api/v2/election/profile-simulate',
    toProfilePayload(config, pg, computeStrategic)
  );
}
