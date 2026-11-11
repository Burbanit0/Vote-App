import type { ElectionConfig, PlaygroundState } from '../stores/useElectionStore';

// The /assembly request body, and the composed-electorate payload every parliament-side
// endpoint shares. Its own module so the live-assembly hook, which keys its refetch on exactly
// this body, imports it without pulling in the API call (tests mock assemblyApi).

/** Composed electorate (community mixture) → backend payload, only when active.
 * When 'simple', returns null so the backend keeps the ideology preset cloud.
 * Shared by every parliament-side endpoint so they all read the same electorate. */
export function electoratePayload(pg: PlaygroundState) {
  const e = pg.electorate;
  if (e.mode !== 'composed') return null;
  return {
    mode: 'composed' as const,
    correlation: e.correlation,
    noise: e.noise,
    communities: e.communities.map((c) => ({
      id: c.id,
      label: c.label,
      x: c.x,
      y: c.y,
      z: c.z ?? 0,
      spread: c.spread,
      weight: c.weight,
      turnout: c.turnout,
    })),
  };
}

/** Build the `extra="forbid"` request body from shared electorate + assembly knobs. */
export function toAssemblyPayload(config: ElectionConfig, pg: PlaygroundState) {
  return {
    parties: config.candidates.map((c) => ({ name: c.name, x: c.x, y: c.y })),
    num_voters: config.num_voters,
    ideology: config.ideology,
    seed: config.seed,
    structure: pg.assembly.structure,
    seats: pg.assembly.seats,
    threshold: pg.assembly.threshold,
    apportionment: pg.assembly.apportionment,
    strategic_desertion: pg.assembly.strategic_desertion,
    turnout: { model: pg.turnout.model, intensity: pg.turnout.intensity },
    electorate: electoratePayload(pg),
  };
}
