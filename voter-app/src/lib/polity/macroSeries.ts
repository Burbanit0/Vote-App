/**
 * lib/polity/macroSeries.ts — the run's curves as chart rows, pure.
 *
 * The API's standings and elections carry null wherever the journal holds no
 * reading; rows keep those nulls, so a chart draws a gap there rather than a
 * made-up zero.
 */

export interface StandingInput {
  tick: number;
  president?: number | null;
  legitimacy?: number | null;
  ecart?: number | null;
  mandate_strength?: number | null;
  acts: readonly number[];
}

export interface ElectionInput {
  tick: number;
  outcome: 'elected' | 'no_winner' | 'invalidated';
  winner?: number | null;
  turnout?: number | null;
  blank_share?: number | null;
  blank_source?: 'invalidation_check' | 'ballots' | 'audit_sample' | null;
}

export interface StandingRow {
  tick: number;
  legitimacy: number | null;
  ecart: number | null;
  mandateStrength: number | null;
}

/** Pressure acts journaled in a tick, by act (PressureAct 0–4). */
export interface PressureRow {
  tick: number;
  nothing: number;
  signPetition: number;
  launchPetition: number;
  mobilize: number;
  waitForElection: number;
}

export const PRESSURE_KEYS = [
  'nothing',
  'signPetition',
  'launchPetition',
  'mobilize',
  'waitForElection',
] as const;

export interface ElectionRow {
  tick: number;
  outcome: ElectionInput['outcome'];
  winner: number | null;
  turnout: number | null;
  blankShare: number | null;
  blankSource: NonNullable<ElectionInput['blank_source']> | null;
}

export function standingRows(standings: readonly StandingInput[]): StandingRow[] {
  return standings.map((s) => ({
    tick: s.tick,
    legitimacy: s.legitimacy ?? null,
    ecart: s.ecart ?? null,
    mandateStrength: s.mandate_strength ?? null,
  }));
}

export function pressureRows(standings: readonly StandingInput[]): PressureRow[] {
  return standings.map((s) => {
    const row = { tick: s.tick } as PressureRow;
    PRESSURE_KEYS.forEach((key, act) => {
      row[key] = s.acts[act] ?? 0;
    });
    return row;
  });
}

export function electionRows(elections: readonly ElectionInput[]): ElectionRow[] {
  return elections.map((e) => ({
    tick: e.tick,
    outcome: e.outcome,
    winner: e.winner ?? null,
    turnout: e.turnout ?? null,
    blankShare: e.blank_share ?? null,
    blankSource: e.blank_source ?? null,
  }));
}

/** Whether any tick carries a legitimacy reading (there is none before a first president). */
export function hasStanding(rows: readonly StandingRow[]): boolean {
  return rows.some((r) => r.legitimacy !== null || r.ecart !== null || r.mandateStrength !== null);
}

/** The tick a chart click lands on: its active label, when it is a whole tick. */
export function clickedTick(
  state: { activeLabel?: string | number } | null | undefined
): number | null {
  const label = state?.activeLabel;
  const tick = typeof label === 'number' ? label : Number(label);
  return label !== undefined && Number.isInteger(tick) && tick >= 0 ? tick : null;
}
