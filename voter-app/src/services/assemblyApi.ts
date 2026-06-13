import { apiPost } from '../api/client';
import { ElectionConfig, PlaygroundState } from '../stores/useElectionStore';

// Lab reshape P3 — the party-level assembly endpoint. One shared electorate;
// votes → seats under PR / FPTP / MMP with proportionality, fragmentation,
// wasted-vote and coalition read-outs.

export interface AssemblyParty {
  name: string;
  x: number;
  y: number;
  votes: number;
  vote_share: number;
  seats: number;
  seat_share: number;
  district_seats: number;
  excluded_by_threshold: boolean;
}

export interface AssemblyCoalition {
  parties: string[];
  seats: number;
  span: number;
}

export interface AssemblyResult {
  structure: string;
  assembly_size: number;
  majority: number;
  threshold_waived: boolean;
  parties: AssemblyParty[];
  gallagher_index: number | null;
  effective_parties_votes: number | null;
  effective_parties_seats: number | null;
  wasted_vote_share: number;
  coalitions: AssemblyCoalition[];
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
  };
}

export async function runAssembly(
  config: ElectionConfig,
  pg: PlaygroundState
): Promise<AssemblyResult> {
  return apiPost<AssemblyResult>('/api/v2/election/assembly', toAssemblyPayload(config, pg));
}

// ── Assembly scorecard (Lab reshape P5) ──────────────────────────────────────

export interface AxisBand {
  mean: number;
  lo: number;
  hi: number;
}

export interface AssemblyScorecardResult {
  replications: number;
  /** structure (pr|fptp|mmp) → axis → band */
  structures: Record<string, Record<string, AxisBand>>;
}

/** All three structures are scored at once, so `structure` is not sent. */
export function toScorecardPayload(config: ElectionConfig, pg: PlaygroundState) {
  return {
    parties: config.candidates.map((c) => ({ name: c.name, x: c.x, y: c.y })),
    num_voters: config.num_voters,
    ideology: config.ideology,
    seed: config.seed,
    seats: pg.assembly.seats,
    threshold: pg.assembly.threshold,
    apportionment: pg.assembly.apportionment,
    strategic_desertion: pg.assembly.strategic_desertion,
    replications: 24,
  };
}

export async function runAssemblyScorecard(
  config: ElectionConfig,
  pg: PlaygroundState
): Promise<AssemblyScorecardResult> {
  return apiPost<AssemblyScorecardResult>(
    '/api/v2/election/assembly-scorecard',
    toScorecardPayload(config, pg)
  );
}

// ── Temporal mode (frontier FA-3) ────────────────────────────────────────────

export interface TemporalPartyState {
  name: string;
  x: number;
  y: number;
  vote_share: number;
  seats: number;
}

export interface TemporalRound {
  round: number;
  parties: TemporalPartyState[];
  winner: string;
  enp_votes: number | null;
  enp_seats: number | null;
  gallagher: number | null;
  polarization: number;
  alternation: boolean;
  congruence_gap: number;
}

export interface TemporalResult {
  rounds: TemporalRound[];
  alternation_rate: number;
  enp_votes_initial: number | null;
  enp_votes_final: number | null;
  polarization_initial: number;
  polarization_final: number;
}

/** N sequential elections; `structure` overrides the playground knob so the
 * panel can compare two systems from the same start. */
export async function runTemporal(
  config: ElectionConfig,
  pg: PlaygroundState,
  structure?: string,
  rounds = 20
): Promise<TemporalResult> {
  return apiPost<TemporalResult>('/api/v2/election/temporal', {
    parties: config.candidates.map((c) => ({ name: c.name, x: c.x, y: c.y })),
    num_voters: config.num_voters,
    ideology: config.ideology,
    seed: config.seed,
    structure: structure ?? pg.assembly.structure,
    seats: pg.assembly.seats,
    threshold: pg.assembly.threshold,
    apportionment: pg.assembly.apportionment,
    strategic_desertion: pg.assembly.strategic_desertion,
    rounds,
  });
}
