import type { ElectionConfig, PlaygroundState } from '../stores/useElectionStore';

// The /profile-simulate request body, built from the shared electorate + playground knobs.
// Its own module so that both the API call (profileApi) and the live-diagnostics hook, which
// keys its refetch on exactly this body, can import it without one dragging in the other.

/** Build the `extra="forbid"` request body from shared electorate + playground knobs.
 *  Keyed on by useProfileDiagnostics: whatever is sent here is what triggers a refetch. */
export function toProfilePayload(
  config: ElectionConfig,
  pg: PlaygroundState,
  computeStrategic = false
) {
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
