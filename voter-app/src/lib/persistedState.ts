/**
 * Versioned, validated persistence for the election config and the playground slice.
 *
 * What is stored is the state itself plus a `version` number. Reading it back never trusts the
 * shape: `JSON.parse` returns whatever a previous build, a hand edit, another tab or a
 * corrupted write left behind, and a cast (`as ElectionConfig`) would let a missing field, a
 * string where a number belongs, or `NaN` reach the engine and the canvases.
 *
 * - No `version` is the first shape the app ever wrote (before versioning): read as version 0,
 *   field by field, so nobody loses what they saved.
 * - A `version` above `STORAGE_VERSION` was written by a newer build whose shape this one does
 *   not know: it is ignored (defaults), never read in part, and never deleted here.
 * - Every field is checked against its type and its range, and a bad one falls back to the
 *   default for that field alone, so one bad knob does not reset the whole scenario.
 *
 * Bump `STORAGE_VERSION` when a stored field changes meaning (a rename, a unit change), and
 * migrate older shapes in `readStored`'s caller; adding a field needs no bump (a missing
 * field takes its default).
 */
import { BLANK_LENSES } from './blankVote';
import { MAX_CANDIDATES, MAX_NAME_LENGTH, MIN_CANDIDATES } from './candidateEditing';
import type {
  Apportionment,
  AssemblyStructure,
  Behavior,
  BallotType,
  ElectionCandidate,
  ElectionConfig,
  ElectorateComposition,
  PlaygroundMode,
  PlaygroundState,
  PrefSource,
} from './electionTypes';
import type { Community } from './playgroundElectorate';

export const STORAGE_VERSION = 1;

/** The voter distributions the sampler and the API know. */
const IDEOLOGIES = ['random', 'centrist', 'polarized', 'left_skewed', 'right_skewed'] as const;

type Json = Record<string, unknown>;

const isObject = (v: unknown): v is Json =>
  typeof v === 'object' && v !== null && !Array.isArray(v);

/** The object to store: the state and the version that wrote it. */
export function withVersion<T extends object>(state: T): T & { version: number } {
  return { ...state, version: STORAGE_VERSION };
}

/**
 * The stored object, or null when there is nothing usable: no value, malformed JSON, not an
 * object, or a version this build does not know (newer than its own, or not a whole number).
 */
export function readStored(raw: string | null): Json | null {
  if (!raw) return null;
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return null;
  }
  if (!isObject(parsed)) return null;
  const { version } = parsed;
  if (version === undefined) return parsed; // the shape written before versioning
  if (
    !Number.isInteger(version) ||
    (version as number) < 0 ||
    (version as number) > STORAGE_VERSION
  )
    return null;
  return parsed;
}

/**
 * True when what is stored there was written by a newer build. The writers leave it alone: an
 * older build that overwrote it (with defaults plus one edit) would destroy what the newer build
 * saved, which the user gets back by opening the newer build again.
 */
export function isNewerThanThisBuild(raw: string | null): boolean {
  if (!raw) return false;
  try {
    const parsed: unknown = JSON.parse(raw);
    return (
      isObject(parsed) && typeof parsed.version === 'number' && parsed.version > STORAGE_VERSION
    );
  } catch {
    return false;
  }
}

// ── Field checks: each returns the value when it is valid, the fallback otherwise ──────────

const num = (v: unknown, fallback: number, min: number, max: number): number =>
  typeof v === 'number' && Number.isFinite(v) ? Math.min(max, Math.max(min, v)) : fallback;

const int = (v: unknown, fallback: number, min: number, max: number): number =>
  typeof v === 'number' && Number.isFinite(v)
    ? Math.min(max, Math.max(min, Math.round(v)))
    : fallback;

const bool = (v: unknown, fallback: boolean): boolean => (typeof v === 'boolean' ? v : fallback);

const oneOf = <T extends string>(v: unknown, allowed: readonly T[], fallback: T): T =>
  typeof v === 'string' && (allowed as readonly string[]).includes(v) ? (v as T) : fallback;

/** A string kept as it is when short enough, cut when too long (a label is never replaced). */
const text = (v: unknown, fallback: string, maxLength: number): string =>
  typeof v === 'string' ? v.slice(0, maxLength) : fallback;

/** The allowed values of a union, from a map the compiler checks lists every member. */
const keysOf = <T extends string>(map: Record<T, true>): T[] => Object.keys(map) as T[];

const record = (v: unknown, fallback: Json): Json => (isObject(v) ? v : fallback);

const numberRecord = (v: unknown, fallback: Record<string, number>): Record<string, number> => {
  if (!isObject(v)) return fallback;
  const out: Record<string, number> = {};
  for (const [k, x] of Object.entries(v))
    if (typeof x === 'number' && Number.isFinite(x)) out[k] = x;
  return out;
};

// ── The election config ─────────────────────────────────────────────────────────────────────

const isNumber = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v);

/** A coordinate in [-1, 1] when `v` is a number, else nothing to set. */
const optionalCoordinate = (v: unknown): number | undefined =>
  isNumber(v) ? num(v, 0, -1, 1) : undefined;

/** One stored candidate, or null when it is not usable (no name, a bad position). */
function parseCandidate(item: unknown): ElectionCandidate | null {
  if (!isObject(item)) return null;
  const name = typeof item.name === 'string' ? item.name.trim() : '';
  // Code points, as the editor and the backend count them (an emoji is one, not two units).
  if (!name || Array.from(name).length > MAX_NAME_LENGTH) return null;
  if (!isNumber(item.x) || !isNumber(item.y)) return null;
  const candidate: ElectionCandidate = {
    name,
    x: num(item.x, 0, -1, 1),
    y: num(item.y, 0, -1, 1),
  };
  const z = optionalCoordinate(item.z);
  const valence = optionalCoordinate(item.valence);
  if (z !== undefined) candidate.z = z;
  if (valence !== undefined) candidate.valence = valence;
  return candidate;
}

/**
 * The whole list or nothing: a list with one unusable, repeated or surplus candidate is not the
 * scenario that was saved, and keeping part of it would be a different election presented as the
 * same one.
 */
function sanitizeCandidates(v: unknown, fallback: ElectionCandidate[]): ElectionCandidate[] {
  if (!Array.isArray(v) || v.length < MIN_CANDIDATES || v.length > MAX_CANDIDATES) return fallback;
  const out = v.map(parseCandidate);
  const names = new Set(out.map((c) => c?.name));
  if (out.some((c) => c === null) || names.size !== out.length) return fallback;
  return out as ElectionCandidate[];
}

/** An election config read back from storage, every field checked, `fallback` where it is not. */
export function sanitizeConfig(raw: Json | null, fallback: ElectionConfig): ElectionConfig {
  if (!raw) return fallback;
  const blank = record(raw.blank_vote, {});
  const contagion = record(blank.contagion, {});
  const info = record(raw.information_model, {});
  const segments = record(info.voter_segments, {});
  const campaign = record(raw.campaign, {});
  const fb = fallback;
  const config: ElectionConfig = {
    candidates: sanitizeCandidates(raw.candidates, fb.candidates),
    num_voters: int(raw.num_voters, fb.num_voters, 10, 1000),
    ideology: oneOf(raw.ideology, IDEOLOGIES, fb.ideology as (typeof IDEOLOGIES)[number]),
    seed: int(raw.seed, fb.seed, 0, Number.MAX_SAFE_INTEGER),
    blank_vote: {
      enabled: bool(blank.enabled, fb.blank_vote.enabled),
      rule: oneOf(blank.rule, ['symbolic', 'competitive', 'threshold_30'], fb.blank_vote.rule),
      contagion: {
        enabled: bool(contagion.enabled, fb.blank_vote.contagion.enabled),
        beta: num(contagion.beta, fb.blank_vote.contagion.beta, 0, 1),
        gamma: num(contagion.gamma, fb.blank_vote.contagion.gamma, 0, 1),
        network: oneOf(
          contagion.network,
          ['random', 'watts_strogatz', 'block'],
          fb.blank_vote.contagion.network
        ),
      },
    },
    information_model: {
      enabled: bool(info.enabled, fb.information_model.enabled),
      media_bias: numberRecord(info.media_bias, fb.information_model.media_bias),
      voter_segments: {
        low_info: num(segments.low_info, fb.information_model.voter_segments.low_info, 0, 1),
        medium_info: num(
          segments.medium_info,
          fb.information_model.voter_segments.medium_info,
          0,
          1
        ),
        high_info: num(segments.high_info, fb.information_model.voter_segments.high_info, 0, 1),
      },
    },
    campaign: {
      enabled: bool(campaign.enabled, fb.campaign.enabled),
      num_days: int(campaign.num_days, fb.campaign.num_days, 1, 365),
      polling_effect: num(campaign.polling_effect, fb.campaign.polling_effect, 0, 1),
    },
  };
  // A bias is about a candidate: keep only those of the candidates that are there.
  const names = new Set(config.candidates.map((c) => c.name));
  config.information_model.media_bias = Object.fromEntries(
    Object.entries(config.information_model.media_bias).filter(([name]) => names.has(name))
  );
  if (typeof raw.description === 'string') config.description = text(raw.description, '', 600);
  if (typeof raw.phenomenon === 'string') config.phenomenon = text(raw.phenomenon, '', 200);
  return config;
}

// ── The playground slice ────────────────────────────────────────────────────────────────────

const PREF_SOURCES = keysOf<PrefSource>({
  spatial: true,
  single_peaked: true,
  impartial: true,
  iac: true,
  mallows: true,
  urn: true,
  plackett_luce: true,
  didi: true,
  stratification: true,
  handcrafted: true,
});

const BALLOT_TYPES = keysOf<BallotType>({
  full: true,
  choose_one: true,
  approve: true,
  rank_full: true,
  rank_truncated: true,
  score: true,
  grade: true,
  cumulative: true,
});

const MODES = keysOf<PlaygroundMode>({ leader: true, parliament: true });
const BEHAVIORS = keysOf<Behavior>({ sincere: true, strategic: true, mixed: true });
const STRUCTURES = keysOf<AssemblyStructure>({ pr: true, fptp: true, mmp: true });
const APPORTIONMENTS = keysOf<Apportionment>({ dhondt: true, sainte_lague: true });

/** One stored community, or null when it is not usable (no id, a bad centre). */
function parseCommunity(item: unknown): Community | null {
  if (!isObject(item)) return null;
  const id = typeof item.id === 'string' ? item.id : '';
  if (!id || !isNumber(item.x) || !isNumber(item.y)) return null;
  const community: Community = {
    id,
    label: text(item.label, id, 60),
    x: num(item.x, 0, -1, 1),
    y: num(item.y, 0, -1, 1),
    spread: num(item.spread, 0.18, 0.01, 1),
    weight: num(item.weight, 1, 0, 1000),
    turnout: num(item.turnout, 0.9, 0, 1),
  };
  const z = optionalCoordinate(item.z);
  if (z !== undefined) community.z = z;
  return community;
}

function sanitizeCommunities(v: unknown, fallback: Community[]): Community[] {
  if (!Array.isArray(v)) return fallback;
  const ids = new Set<string>();
  const out: Community[] = [];
  for (const item of v) {
    const community = parseCommunity(item);
    if (!community || ids.has(community.id)) continue;
    ids.add(community.id);
    out.push(community);
  }
  return out.length > 0 ? out : fallback;
}

function sanitizeElectorate(v: unknown, fb: ElectorateComposition): ElectorateComposition {
  const e = record(v, {});
  return {
    mode: oneOf(e.mode, ['simple', 'composed'], fb.mode),
    correlation: num(e.correlation, fb.correlation, -1, 1),
    noise: num(e.noise, fb.noise, 0, 1),
    communities: sanitizeCommunities(e.communities, fb.communities),
  };
}

/** A playground slice read back from storage, every field checked, `fallback` where it is not. */
export function sanitizePlayground(raw: Json | null, fallback: PlaygroundState): PlaygroundState {
  if (!raw) return fallback;
  const fb = fallback;
  const space = record(raw.space, {});
  const ballot = record(raw.ballot, {});
  const turnout = record(raw.turnout, {});
  const blank = record(raw.blank, {});
  const assembly = record(raw.assembly, {});
  const labels =
    Array.isArray(space.axisLabels) &&
    space.axisLabels.length > 0 &&
    space.axisLabels.length <= 3 &&
    space.axisLabels.every((l) => typeof l === 'string' && l.length <= 60)
      ? (space.axisLabels as string[])
      : fb.space.axisLabels;
  return {
    mode: oneOf(raw.mode, MODES, fb.mode),
    space: {
      dims: space.dims === 1 || space.dims === 2 || space.dims === 3 ? space.dims : fb.space.dims,
      axisLabels: labels,
      valenceEnabled: bool(space.valenceEnabled, fb.space.valenceEnabled),
    },
    behavior: oneOf(raw.behavior, BEHAVIORS, fb.behavior),
    stratTactic: oneOf(raw.stratTactic, ['compromise', 'burying'], fb.stratTactic),
    stratShare: num(raw.stratShare, fb.stratShare, 0, 1),
    prefSource: oneOf(raw.prefSource, PREF_SOURCES, fb.prefSource),
    prefParams: numberRecord(raw.prefParams, fb.prefParams),
    ballot: {
      type: oneOf(ballot.type, BALLOT_TYPES, fb.ballot.type),
      truncate_at: int(ballot.truncate_at, fb.ballot.truncate_at, 1, MAX_CANDIDATES),
      score_levels: int(ballot.score_levels, fb.ballot.score_levels, 2, 20),
    },
    turnout: {
      model: oneOf(turnout.model, ['full', 'alienation', 'indifference'], fb.turnout.model),
      intensity: num(turnout.intensity, fb.turnout.intensity, 0, 1),
    },
    blank: {
      enabled: bool(blank.enabled, fb.blank.enabled),
      intensity: num(blank.intensity, fb.blank.intensity, 0, 1),
      lens: oneOf(blank.lens, BLANK_LENSES, fb.blank.lens),
    },
    electorate: sanitizeElectorate(raw.electorate, fb.electorate),
    assembly: {
      structure: oneOf(assembly.structure, STRUCTURES, fb.assembly.structure),
      seats: int(assembly.seats, fb.assembly.seats, 1, 1000),
      threshold: num(assembly.threshold, fb.assembly.threshold, 0, 1),
      apportionment: oneOf(assembly.apportionment, APPORTIONMENTS, fb.assembly.apportionment),
      num_districts: int(assembly.num_districts, fb.assembly.num_districts, 1, 100),
      strategic_desertion: bool(assembly.strategic_desertion, fb.assembly.strategic_desertion),
    },
  };
}
