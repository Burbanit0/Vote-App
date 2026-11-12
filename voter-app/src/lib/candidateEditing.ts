import type { ElectionCandidate, ElectionConfig } from '../stores/useElectionStore';

// Editing the candidate (or party) list: the pure part. The backend takes 2 to 8 candidates with
// unique names of 1 to 64 characters (`UniqueCandidates`, `CandidateSpec`), and the palette has
// eight colours, so those are the editor's limits too: the request never has to be refused.

export const MIN_CANDIDATES = 2;
export const MAX_CANDIDATES = 8;
export const MAX_NAME_LENGTH = 64;

export type NameProblem = 'empty' | 'tooLong' | 'duplicate';

/** Why `raw` cannot name a candidate next to `others`, or null. Names are compared as the backend
 *  compares them (exactly, after trimming): "alice" and "Alice" are two candidates. */
export function nameProblem(raw: string, others: readonly string[]): NameProblem | null {
  const name = raw.trim();
  if (name === '') return 'empty';
  // Code points, as the backend counts them (an emoji is one, not two UTF-16 units).
  if (Array.from(name).length > MAX_NAME_LENGTH) return 'tooLong';
  return others.includes(name) ? 'duplicate' : null;
}

/** "Candidate 4": the first `${base} ${n}` nobody has yet, counting up from the next free number. */
export function nextName(base: string, existing: readonly string[]): string {
  const taken = new Set(existing);
  for (let n = existing.length + 1; ; n++) {
    const name = `${base} ${n}`;
    if (!taken.has(name)) return name;
  }
}

type Place = { x: number; y: number; z: number };

// A coarse grid inside the domain cube, a little short of the walls: candidates sit there.
// Built from whole hundredths, so every value is an exact two-decimal one (-0.6, not -0.6000000000000001).
const GRID = Array.from({ length: 13 }, (_, i) => (-90 + i * 15) / 100);

/** Squared distance between two points, over the first `dims` axes only. */
function distanceSq(a: Place, b: Place, dims: 1 | 2 | 3): number {
  const dx = a.x - b.x;
  const dy = dims >= 2 ? a.y - b.y : 0;
  const dz = dims >= 3 ? a.z - b.z : 0;
  return dx * dx + dy * dy + dz * dz;
}

/**
 * Where a new candidate goes: the grid point farthest from every existing one in the dimensions
 * in play (1-D: on the line; 2-D: in the plane; 3-D: in the cube). A newcomer in the biggest gap
 * does not land on top of anyone, so it is visible at once and splits the field instead of
 * hiding in it. Deterministic: the first of equally good points wins.
 */
export function placeNewcomer(existing: readonly ElectionCandidate[], dims: 1 | 2 | 3): Place {
  const others: Place[] = existing.map((c) => ({ x: c.x, y: c.y, z: c.z ?? 0 }));
  const ys = dims >= 2 ? GRID : [0];
  const zs = dims >= 3 ? GRID : [0];
  let best: Place = { x: 0, y: 0, z: 0 };
  let bestGap = -1;
  for (const x of GRID) {
    for (const y of ys) {
      for (const z of zs) {
        const here = { x, y, z };
        const gap = Math.min(...others.map((o) => distanceSq(here, o, dims)));
        if (gap > bestGap) {
          bestGap = gap;
          best = here;
        }
      }
    }
  }
  return best;
}

export const canAdd = (count: number): boolean => count < MAX_CANDIDATES;
export const canRemove = (count: number): boolean => count > MIN_CANDIDATES;

type Patch = Pick<ElectionConfig, 'candidates' | 'information_model'>;

/** `information_model.media_bias` is keyed by candidate name: carry it along a rename or a removal. */
function withBias(
  config: ElectionConfig,
  candidates: ElectionCandidate[],
  rekey: (bias: Record<string, number>) => Record<string, number>
): Patch {
  const bias = config.information_model.media_bias;
  return {
    candidates,
    information_model: { ...config.information_model, media_bias: rekey({ ...bias }) },
  };
}

/** The config patch that appends `newcomer` (see `placeNewcomer`). */
export function addCandidate(
  config: ElectionConfig,
  newcomer: ElectionCandidate
): Pick<ElectionConfig, 'candidates'> {
  return { candidates: [...config.candidates, newcomer] };
}

/** The config patch that drops the candidate at `index`. */
export function removeCandidate(config: ElectionConfig, index: number): Patch {
  const gone = config.candidates[index].name;
  return withBias(
    config,
    config.candidates.filter((_, i) => i !== index),
    (bias) => {
      delete bias[gone];
      return bias;
    }
  );
}

/** The config patch that renames the candidate at `index` to `name` (trimmed). */
export function renameCandidate(config: ElectionConfig, index: number, name: string): Patch {
  const old = config.candidates[index].name;
  const next = name.trim();
  return withBias(
    config,
    config.candidates.map((c, i) => (i === index ? { ...c, name: next } : c)),
    (bias) => {
      // Whatever sat under the new name belonged to nobody (names are unique): never inherit it.
      if (old in bias) {
        bias[next] = bias[old];
        delete bias[old];
      } else {
        delete bias[next];
      }
      return bias;
    }
  );
}
