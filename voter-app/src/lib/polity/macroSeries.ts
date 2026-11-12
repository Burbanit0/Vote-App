/**
 * lib/polity/macroSeries.ts — the run's curves as chart rows, pure.
 *
 * The API's standings and elections carry null (or nothing) wherever the journal
 * holds no reading. The charts take them as they come: Recharts draws a gap
 * there rather than a made-up zero.
 */

export interface StandingInput {
  tick: number;
  president?: number | null;
  legitimacy?: number | null;
  ecart?: number | null;
  mandate_strength?: number | null;
  approval?: number | null;
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

export function pressureRows(standings: readonly StandingInput[]): PressureRow[] {
  return standings.map((s) => {
    const row = { tick: s.tick } as PressureRow;
    PRESSURE_KEYS.forEach((key, act) => {
      row[key] = s.acts[act] ?? 0;
    });
    return row;
  });
}

/** Whether any tick carries a legitimacy reading (there is none before a first president). */
export function hasStanding(standings: readonly StandingInput[]): boolean {
  return standings.some(
    (s) => s.legitimacy != null || s.ecart != null || s.mandate_strength != null
  );
}

/** The tick a chart click lands on: its active label, when it is a whole tick. */
export function clickedTick(
  state: { activeLabel?: string | number } | null | undefined
): number | null {
  const label = state?.activeLabel;
  const tick = typeof label === 'number' ? label : Number(label);
  return label !== undefined && Number.isInteger(tick) && tick >= 0 ? tick : null;
}
