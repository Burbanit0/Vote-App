/**
 * lib/polity/runs.ts — what the run explorer says about a listed run, pure.
 *
 * Run ids repeat across a root (a sweep's `seed-1` in every one of its settings), so a
 * run is named by its directory inside the root. And a run the runner did not finish
 * (stopped, crashed, or still going) says so, instead of passing for a short one.
 */

export interface ListedRun {
  relative_path: string;
  run_id: string;
  ticks_reached?: number | null;
  ticks_planned?: number | null;
}

/** The run's directory inside its root, without the `run/<run_id>` the runner nests its files in. */
export function runName(run: ListedRun): string {
  const nested = `/run/${run.run_id}`;
  return run.relative_path.endsWith(nested)
    ? run.relative_path.slice(0, -nested.length)
    : run.relative_path;
}

/** How far a run got short of its plan; null when it ran every planned tick, or does not say. */
export function unfinished(run: ListedRun): { reached: number; planned: number } | null {
  const { ticks_reached: reached, ticks_planned: planned } = run;
  return typeof reached === 'number' && typeof planned === 'number' && reached < planned
    ? { reached, planned }
    : null;
}
