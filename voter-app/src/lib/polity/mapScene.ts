/**
 * lib/polity/mapScene.ts — what the population map draws at one tick, pure
 * (ADR-013).
 *
 * The scene is computed once per tick, lens, selection and size, then drawn by
 * drawScene on the canvas and by the SVG overlay above it. Both read the
 * same pixel projection, so a citizen's point and their selection ring can't
 * drift apart. Every code has a shape as well as a colour, so the map reads
 * without colour and in print.
 */
import type { PolityLens } from './urlState';

export type PointShape = 'circle' | 'ring' | 'square' | 'triangle' | 'diamond' | 'cross';

/** Okabe–Ito: distinguishable under the common colour-vision deficiencies. */
export const MAP_COLORS = {
  muted: '#9ca3af',
  faint: '#d1d5db',
  orange: '#e69f00',
  sky: '#56b4e9',
  green: '#009e73',
  yellow: '#f0e442',
  blue: '#0072b2',
  vermillion: '#d55e00',
  purple: '#cc79a7',
  black: '#1f2937',
} as const;
type MapColor = keyof typeof MAP_COLORS;

const PARTY_COLORS: readonly MapColor[] = [
  'blue',
  'orange',
  'green',
  'purple',
  'sky',
  'vermillion',
  'yellow',
];

export interface MapPoint {
  id: number;
  x: number;
  y: number;
  shape: PointShape;
  color: MapColor;
  /** The legend entry this point counts toward. */
  legend: string;
}

export interface LegendEntry {
  key: string;
  shape: PointShape;
  color: MapColor;
  count: number;
}

interface FrameCodes {
  status: readonly number[];
  chamber: readonly number[];
  act: readonly number[];
  vote: readonly number[];
  candidacy: readonly number[];
}

export interface SceneInput {
  citizens: readonly (readonly number[])[];
  frame: FrameCodes;
  citizenParties: readonly (number | null)[];
  parties: readonly { party_id: number; xy: readonly number[] }[];
  president: {
    citizen_id: number;
    xy: readonly number[];
    pledged_xy?: readonly number[] | null;
  } | null;
}

export interface Scene {
  width: number;
  height: number;
  points: MapPoint[];
  legend: LegendEntry[];
  parties: { partyId: number; x: number; y: number; color: MapColor }[];
  president: {
    id: number;
    x: number;
    y: number;
    pledgedX: number | null;
    pledgedY: number | null;
  } | null;
  /** Pixel position of a map coordinate (for the SVG overlay and axes). */
  project: (xy: readonly number[]) => [number, number];
}

export const MAP_PADDING = 24;

type Style = [legend: string, shape: PointShape, color: MapColor];

const ACTIVITY: Record<number, Style> = {
  0: ['elector', 'circle', 'muted'],
  1: ['candidate', 'triangle', 'orange'],
  2: ['elected', 'diamond', 'vermillion'],
};
const ACT: Record<number, Style> = {
  [-1]: ['notConsulted', 'circle', 'faint'],
  0: ['nothing', 'ring', 'muted'],
  1: ['signPetition', 'diamond', 'sky'],
  2: ['launchPetition', 'triangle', 'blue'],
  3: ['mobilize', 'square', 'vermillion'],
  4: ['waitForElection', 'cross', 'green'],
};
const VOTE: Record<number, Style> = {
  [-1]: ['noBallot', 'circle', 'faint'],
  0: ['blank', 'ring', 'black'],
  1: ['forWinner', 'circle', 'green'],
  2: ['forOther', 'square', 'orange'],
};
const CANDIDACY: Record<number, Style> = {
  [-1]: ['notAsked', 'circle', 'faint'],
  0: ['declined', 'cross', 'muted'],
  1: ['declared', 'ring', 'sky'],
  2: ['nominationLost', 'triangle', 'purple'],
  3: ['standing', 'square', 'orange'],
  4: ['electedCandidate', 'diamond', 'vermillion'],
};

/** The lens's style for citizen `id`: legend key, shape and colour. */
export function styleOf(lens: PolityLens, input: SceneInput, id: number): Style {
  const { frame } = input;
  switch (lens) {
    case 'activity': {
      const [legend, shape, color] = ACTIVITY[frame.status[id]] ?? ACTIVITY[0];
      // A seated elector shows the chamber; a candidate or the president keeps their status.
      return frame.chamber[id] && frame.status[id] === 0
        ? ['chamber', 'square', 'purple']
        : [legend, shape, color];
    }
    case 'act':
      return ACT[frame.act[id]] ?? ACT[-1];
    case 'vote':
      return VOTE[frame.vote[id]] ?? VOTE[-1];
    case 'candidacy':
      return CANDIDACY[frame.candidacy[id]] ?? CANDIDACY[-1];
    case 'party': {
      const party = input.citizenParties[id];
      return party === null || party === undefined
        ? ['noParty', 'ring', 'muted']
        : [`party${party}`, 'circle', PARTY_COLORS[party % PARTY_COLORS.length]];
    }
  }
}

function bounds(input: SceneInput): [number, number, number, number] {
  const xs: number[] = [];
  const ys: number[] = [];
  const add = (xy: readonly number[] | null | undefined) => {
    if (xy) {
      xs.push(xy[0]);
      ys.push(xy[1]);
    }
  };
  input.citizens.forEach(add);
  input.parties.forEach((p) => add(p.xy));
  add(input.president?.xy);
  add(input.president?.pledged_xy);
  if (xs.length === 0) return [-1, -1, 1, 1];
  return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
}

export function buildScene(
  input: SceneInput,
  lens: PolityLens,
  width: number,
  height: number
): Scene {
  const [minX, minY, maxX, maxY] = bounds(input);
  const spanX = Math.max(maxX - minX, 1e-9);
  const spanY = Math.max(maxY - minY, 1e-9);
  // One scale for both axes: distances on the map mean the same thing in every direction.
  const scale = Math.min((width - 2 * MAP_PADDING) / spanX, (height - 2 * MAP_PADDING) / spanY);
  const offsetX = (width - scale * spanX) / 2;
  const offsetY = (height - scale * spanY) / 2;
  // Up is the second axis's positive direction, as on any chart.
  const project = (xy: readonly number[]): [number, number] => [
    offsetX + (xy[0] - minX) * scale,
    height - (offsetY + (xy[1] - minY) * scale),
  ];

  const counts = new Map<string, LegendEntry>();
  const points = input.citizens.map((xy, id) => {
    const [legend, shape, color] = styleOf(lens, input, id);
    const entry = counts.get(legend) ?? { key: legend, shape, color, count: 0 };
    entry.count += 1;
    counts.set(legend, entry);
    const [x, y] = project(xy);
    return { id, x, y, shape, color, legend };
  });

  const president = input.president;
  const pledged = president?.pledged_xy ? project(president.pledged_xy) : null;
  return {
    width,
    height,
    points,
    legend: [...counts.values()],
    parties: input.parties.map((p) => {
      const [x, y] = project(p.xy);
      return { partyId: p.party_id, x, y, color: PARTY_COLORS[p.party_id % PARTY_COLORS.length] };
    }),
    president: president
      ? {
          id: president.citizen_id,
          ...xyOf(project(president.xy)),
          pledgedX: pledged?.[0] ?? null,
          pledgedY: pledged?.[1] ?? null,
        }
      : null,
    project,
  };
}

function xyOf([x, y]: [number, number]): { x: number; y: number } {
  return { x, y };
}

/** The census positions in force at `year`: the latest recorded at or before it (the first otherwise). */
export function censusAt<T extends { year: number }>(
  censuses: readonly T[],
  year: number
): T | undefined {
  let found: T | undefined;
  for (const census of censuses) {
    if (census.year <= year && (!found || census.year > found.year)) found = census;
  }
  return found ?? censuses[0];
}
