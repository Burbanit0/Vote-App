/**
 * useElectionStore — global election config slice (Phase 5.4).
 *
 * Source of truth for the Election Lab config + active scenario metadata
 * (was ElectionContext, the app's spine — ~35 consumers). `stores/useElectionStore`
 * is now a thin shim over this store so every `useElection()` consumer + the
 * <ElectionProvider> in App.tsx keep working until 5.5 deletes the shim.
 *
 * Persistence: localStorage['votelab_election_config'] (written on each mutation,
 * re-read by hydrate() on mount).
 */
import React, { useEffect } from 'react';
import { create } from 'zustand';
import type { Community } from '../lib/playgroundElectorate';
import { track } from '../lib/analytics';

export type { Community };

/** A composable electorate: a mixture of communities + axis correlation. */
export interface ElectorateComposition {
  mode: 'simple' | 'composed';
  correlation: number;
  /** Global measurement/polling jitter in [0,1] (blurs observed positions). */
  noise: number;
  communities: Community[];
}

// ── Types ─────────────────────────────────────────────────────────────────────

export interface ElectionCandidate {
  name: string;
  x: number;
  y: number;
  /** Optional 3rd ideological axis (playground dims=3). Defaults to 0. */
  z?: number;
  /** Stokes valence: non-spatial quality in [-1,1], applied only when
   *  space.valenceEnabled. Lifts utility for every voter (−distance + valence). */
  valence?: number;
}

export interface ElectionConfig {
  candidates: ElectionCandidate[];
  num_voters: number;
  ideology: string;
  seed: number;
  blank_vote: {
    enabled: boolean;
    rule: 'symbolic' | 'competitive' | 'threshold_30';
    contagion: {
      enabled: boolean;
      beta: number;
      gamma: number;
      network: 'random' | 'watts_strogatz' | 'block';
    };
  };
  information_model: {
    enabled: boolean;
    media_bias: Record<string, number>;
    voter_segments: { low_info: number; medium_info: number; high_info: number };
  };
  campaign: {
    enabled: boolean;
    num_days: number;
    polling_effect: number;
  };
  description?: string;
  phenomenon?: string;
}

export interface ScenarioMeta {
  id: string;
  name: string;
  description: string;
  phenomenon: string;
}

const _BLANK_OFF = {
  enabled: false,
  rule: 'symbolic' as const,
  contagion: { enabled: false, beta: 0.15, gamma: 0.1, network: 'random' as const },
};
const _INFO_OFF = {
  enabled: false,
  media_bias: {},
  voter_segments: { low_info: 0.3, medium_info: 0.5, high_info: 0.2 },
};
const _CAMP_OFF = { enabled: false, num_days: 30, polling_effect: 0.3 };

export const DEFAULT_CONFIG: ElectionConfig = {
  candidates: [
    { name: 'Alice', x: -0.5, y: -0.2 },
    { name: 'Bob', x: 0.5, y: 0.2 },
    { name: 'Carol', x: 0.0, y: 0.3 },
  ],
  num_voters: 300,
  ideology: 'random',
  seed: 42,
  blank_vote: _BLANK_OFF,
  information_model: _INFO_OFF,
  campaign: _CAMP_OFF,
};

// ── Pre-built scenarios ───────────────────────────────────────────────────────

export const SCENARIOS: Record<string, ElectionConfig> = {
  default: DEFAULT_CONFIG,

  france2002: {
    ...DEFAULT_CONFIG,
    candidates: [
      { name: 'Chirac', x: 0.3, y: 0.4 },
      { name: 'Jospin', x: -0.4, y: -0.3 },
      { name: 'Le Pen', x: 0.8, y: 0.8 },
      { name: 'Bayrou', x: 0.1, y: 0.1 },
      { name: 'Chevènement', x: -0.2, y: 0.1 },
      { name: 'Mégret', x: 0.9, y: 0.9 },
      { name: 'Taubira', x: -0.7, y: -0.6 },
      { name: 'Besancenot', x: -0.8, y: -0.5 },
    ],
    num_voters: 500,
    ideology: 'polarized',
    seed: 2002,
    blank_vote: {
      enabled: true,
      rule: 'symbolic',
      contagion: { enabled: false, beta: 0.1, gamma: 0.1, network: 'random' },
    },
    information_model: _INFO_OFF,
    campaign: { enabled: true, num_days: 30, polling_effect: 0.35 },
    description:
      'La gauche fragmentée en 6 candidats élimine Jospin dès le 1er tour, laissant Le Pen en 2e position face à Chirac.',
    phenomenon: 'Paradoxe de Condorcet',
  },

  usa1992: {
    ...DEFAULT_CONFIG,
    candidates: [
      { name: 'Clinton', x: -0.2, y: -0.1 },
      { name: 'Bush', x: 0.4, y: 0.5 },
      { name: 'Perot', x: 0.1, y: 0.0 },
    ],
    num_voters: 500,
    ideology: 'random',
    seed: 1992,
    blank_vote: _BLANK_OFF,
    information_model: _INFO_OFF,
    campaign: { enabled: true, num_days: 28, polling_effect: 0.4 },
    description:
      "Perot capture 19% des voix en tant que tiers candidat, fragmentant le vote et permettant à Clinton de l'emporter avec 43%.",
    phenomenon: 'Effet spoiler',
  },

  germany2021: {
    ...DEFAULT_CONFIG,
    candidates: [
      { name: 'Scholz (SPD)', x: -0.1, y: -0.1 },
      { name: 'Laschet (CDU)', x: 0.2, y: 0.3 },
      { name: 'Baerbock (Verts)', x: -0.3, y: -0.4 },
      { name: 'Lindner (FDP)', x: 0.3, y: 0.0 },
      { name: 'Weidel (AfD)', x: 0.8, y: 0.7 },
      { name: 'Bartsch (Gauche)', x: -0.7, y: -0.3 },
    ],
    num_voters: 500,
    ideology: 'centrist',
    seed: 2021,
    blank_vote: _BLANK_OFF,
    information_model: _INFO_OFF,
    campaign: { enabled: true, num_days: 28, polling_effect: 0.3 },
    description:
      'Six partis, aucun dépassant 30% — les méthodes consensuelles (Borda, Schulze) avantagent les candidats du centre qui feraient de bons partenaires de coalition.',
    phenomenon: 'Fragmentation & coalition',
  },

  condorcet_cycle: {
    ...DEFAULT_CONFIG,
    candidates: [
      { name: 'Alice', x: -0.5, y: 0.3 },
      { name: 'Bob', x: 0.4, y: -0.2 },
      { name: 'Carol', x: 0.0, y: -0.5 },
    ],
    num_voters: 500,
    ideology: 'polarized',
    seed: 314,
    blank_vote: _BLANK_OFF,
    information_model: _INFO_OFF,
    campaign: _CAMP_OFF,
    description:
      "Configuration artificielle illustrant le cycle d'Arrow : Alice bat Bob, Bob bat Carol, Carol bat Alice — aucune méthode ne peut s'appuyer sur un consensus transitif.",
    phenomenon: "Cycle d'Arrow (intransitivité)",
  },

  consensus: {
    ...DEFAULT_CONFIG,
    candidates: [
      { name: 'Centre', x: 0.0, y: 0.0 },
      { name: 'Gauche Mod.', x: -0.3, y: -0.2 },
      { name: 'Droite Mod.', x: 0.3, y: 0.2 },
    ],
    num_voters: 500,
    ideology: 'centrist',
    seed: 77,
    blank_vote: _BLANK_OFF,
    information_model: _INFO_OFF,
    campaign: _CAMP_OFF,
    description:
      "Le candidat du centre bat les deux autres en duel direct — il est le vainqueur de Condorcet. Toutes les méthodes consensuelles s'accordent sur ce résultat.",
    phenomenon: 'Consensus parfait (Condorcet)',
  },

  france2022: {
    ...DEFAULT_CONFIG,
    candidates: [
      { name: 'Macron', x: 0.1, y: 0.2 },
      { name: 'Le Pen', x: 0.8, y: 0.7 },
      { name: 'Mélenchon', x: -0.8, y: -0.5 },
      { name: 'Zemmour', x: 0.9, y: 0.9 },
      { name: 'Pécresse', x: 0.4, y: 0.4 },
    ],
    num_voters: 400,
    ideology: 'polarized',
    seed: 2022,
    blank_vote: {
      enabled: true,
      rule: 'competitive',
      contagion: { enabled: false, beta: 0.15, gamma: 0.1, network: 'random' },
    },
    campaign: { enabled: true, num_days: 30, polling_effect: 0.4 },
    information_model: {
      enabled: false,
      media_bias: {},
      voter_segments: { low_info: 0.35, medium_info: 0.45, high_info: 0.2 },
    },
    description:
      'Cinq candidats polarisés, vote blanc activé en mode compétitif, campagne de 30 jours.',
    phenomenon: 'Fragmentation & vote blanc',
  },

  crisis: {
    ...DEFAULT_CONFIG,
    candidates: [
      { name: 'Alice', x: -0.6, y: -0.3 },
      { name: 'Bob', x: 0.6, y: 0.3 },
      { name: 'Carol', x: 0.0, y: 0.5 },
    ],
    num_voters: 300,
    ideology: 'polarized',
    seed: 99,
    blank_vote: {
      enabled: true,
      rule: 'competitive',
      contagion: { enabled: true, beta: 0.4, gamma: 0.08, network: 'watts_strogatz' },
    },
    campaign: _CAMP_OFF,
    information_model: _INFO_OFF,
    description:
      "Vote blanc contagieux (β=0.4) avec règle compétitive — le vote blanc peut remporter l'élection.",
    phenomenon: 'Crise constitutionnelle',
  },
};

// ── Playground slice (Lab reshape Phase P0) ───────────────────────────────────
//
// The two-mode playground ("Elect a leader" vs "Compose a parliament") shares the
// electorate (config above); only the question, rules, scorecard and viz differ.
// These knobs are the user-configurable assumptions — nothing is smuggled in.

export type PlaygroundMode = 'leader' | 'parliament';
export type PrefSource =
  | 'spatial'
  | 'single_peaked'
  | 'impartial'
  | 'iac'
  | 'mallows'
  | 'urn'
  | 'plackett_luce'
  | 'didi'
  | 'stratification'
  | 'handcrafted';

/** Spatial sources place candidates in the ideological space (draggable map);
 *  the rest are statistical cultures with no given geometry (biplot, read-only). */
export const SPATIAL_SOURCES: ReadonlySet<PrefSource> = new Set<PrefSource>([
  'spatial',
  'single_peaked',
]);
export const isSpatialSource = (s: PrefSource): boolean => SPATIAL_SOURCES.has(s);
export type Behavior = 'sincere' | 'strategic' | 'mixed';
export type AssemblyStructure = 'pr' | 'fptp' | 'mmp';
export type Apportionment = 'dhondt' | 'sainte_lague';
export type BallotType =
  | 'full'
  | 'choose_one'
  | 'approve'
  | 'rank_full'
  | 'rank_truncated'
  | 'score'
  | 'grade'
  | 'cumulative';

export interface PlaygroundState {
  mode: PlaygroundMode;
  space: { dims: 1 | 2 | 3; axisLabels: string[]; valenceEnabled: boolean };
  behavior: Behavior;
  /** Which insincere ballot a tempted conviction bloc casts (leader map). */
  stratTactic: 'compromise' | 'burying';
  /** Size of the coordinating conviction bloc, as a share of the electorate. */
  stratShare: number;
  prefSource: PrefSource;
  prefParams: Record<string, number>;
  /** FA-1: how voters may EXPRESS preferences — separate from the counting rule. */
  ballot: { type: BallotType; truncate_at: number; score_levels: number };
  /** Electorate realism: differential turnout (Downsian abstention). */
  turnout: { model: 'full' | 'alienation' | 'indifference'; intensity: number };
  /** Composable electorate (community mixture); 'simple' = the ideology Gaussian. */
  electorate: ElectorateComposition;
  assembly: {
    structure: AssemblyStructure;
    seats: number;
    threshold: number;
    apportionment: Apportionment;
    num_districts: number;
    /** Duverger demo (P4): voters desert non-viable parties. */
    strategic_desertion: boolean;
  };
}

const _co = (
  id: string,
  label: string,
  x: number,
  y: number,
  spread: number,
  weight: number,
  turnout: number,
  z = 0
): Community => ({ id, label, x, y, z, spread, weight, turnout });

/** Electorate composition presets — from textbook shapes to "near-real". */
export const ELECTORATE_PRESETS: Record<
  string,
  { label: string; correlation: number; communities: Community[] }
> = {
  two_blocs: {
    label: 'Bipolaire',
    correlation: 0,
    communities: [
      _co('g', 'Gauche', -0.55, -0.1, 0.18, 1, 0.9),
      _co('d', 'Droite', 0.55, 0.15, 0.18, 1, 0.9),
    ],
  },
  three_poles: {
    label: 'Trois pôles',
    correlation: 0,
    communities: [
      _co('g', 'Gauche', -0.6, -0.1, 0.16, 1, 0.9),
      _co('c', 'Centre', 0.0, 0.0, 0.16, 1, 0.85),
      _co('d', 'Droite', 0.6, 0.2, 0.16, 1, 0.9),
    ],
  },
  center_extremes: {
    label: 'Centre + extrêmes',
    correlation: 0,
    communities: [
      _co('c', 'Centre', 0.0, 0.0, 0.22, 3, 0.85),
      _co('xg', 'Extrême g.', -0.85, -0.5, 0.1, 1, 0.95),
      _co('xd', 'Extrême d.', 0.85, 0.7, 0.1, 1, 0.95),
    ],
  },
  fragmented: {
    label: 'Fragmenté (6)',
    correlation: 0.2,
    communities: [
      _co('verts', 'Verts', -0.3, -0.45, 0.12, 1, 0.85),
      _co('soc', 'Sociaux', -0.55, -0.05, 0.13, 1.2, 0.88),
      _co('cen', 'Centre', 0.0, 0.0, 0.13, 1, 0.8),
      _co('lib', 'Libéraux', 0.35, 0.0, 0.12, 1, 0.85),
      _co('con', 'Conserv.', 0.55, 0.35, 0.13, 1.1, 0.9),
      _co('rad', 'Droite rad.', 0.85, 0.7, 0.1, 0.8, 0.92),
    ],
  },
  realistic: {
    label: 'Proche du réel',
    correlation: 0.35,
    communities: [
      _co('metro', 'Métropoles progressistes', -0.45, -0.4, 0.22, 1.6, 0.78),
      _co('periurb', 'Périurbain modéré', 0.1, 0.0, 0.28, 2.2, 0.7),
      _co('rural', 'Rural conservateur', 0.55, 0.45, 0.2, 1.4, 0.82),
      _co('jeunes', 'Jeunes désengagés', -0.25, -0.1, 0.35, 1.2, 0.45),
      _co('aines', 'Aînés assidus', 0.35, 0.25, 0.18, 1.5, 0.92),
    ],
  },
  polarized: {
    // Two tight, distant blocs with strongly correlated axes — affective
    // polarisation: the two camps diverge on every dimension at once.
    label: 'Polarisé',
    correlation: 0.8,
    communities: [
      _co('camp_a', 'Camp A', -0.7, -0.55, 0.12, 1, 0.92),
      _co('camp_b', 'Camp B', 0.7, 0.55, 0.12, 1, 0.92),
    ],
  },
  nordic: {
    // Consensus electorate: several moderate, overlapping blocs near the centre,
    // uniformly high turnout — short distances, few cleavages.
    label: 'Consensus nordique',
    correlation: 0.1,
    communities: [
      _co('soc_dem', 'Sociaux-dém.', -0.3, -0.1, 0.2, 1.4, 0.86),
      _co('verts', 'Verts/centre-g.', -0.15, -0.3, 0.18, 1, 0.84),
      _co('centre', 'Centre/agrariens', 0.05, 0.05, 0.2, 1.1, 0.85),
      _co('conserv', 'Conservateurs', 0.3, 0.2, 0.2, 1.2, 0.87),
    ],
  },
  cleavages_3d: {
    // A 3rd-axis preset: blocs that AGREE on the economic/social plane but split
    // on a hidden axis (e.g. centre↔périphérie, ouverture↔fermeture). Visible
    // only with the map set to 3 dimensions.
    label: '3 clivages (3D)',
    correlation: 0.2,
    communities: [
      _co('open', 'Ouverts', -0.3, -0.1, 0.16, 1.2, 0.85, 0.7),
      _co('closed', 'Repliés', 0.3, 0.2, 0.16, 1.2, 0.85, -0.7),
      _co('pragmat', 'Pragmatiques', 0.0, 0.0, 0.18, 1, 0.8, 0.0),
    ],
  },
};

export const DEFAULT_PLAYGROUND: PlaygroundState = {
  mode: 'leader',
  space: { dims: 2, axisLabels: ['Économique', 'Sociétal'], valenceEnabled: false },
  behavior: 'sincere',
  stratTactic: 'compromise',
  stratShare: 0.2,
  prefSource: 'spatial',
  prefParams: {},
  ballot: { type: 'full', truncate_at: 3, score_levels: 6 },
  turnout: { model: 'full', intensity: 0.5 },
  electorate: {
    mode: 'simple',
    correlation: ELECTORATE_PRESETS.three_poles.correlation,
    noise: 0,
    communities: ELECTORATE_PRESETS.three_poles.communities,
  },
  assembly: {
    structure: 'pr',
    seats: 100,
    threshold: 0.05,
    apportionment: 'dhondt',
    num_districts: 1,
    strategic_desertion: false,
  },
};

export interface PlaygroundPreset {
  id: string;
  label: string;
  description: string;
  /** 'model' = abstract textbook scenario. 'election' = inspired by a real historical
   *  election but positions are synthetic, not reconstructed from actual ballots. */
  category: 'model' | 'election';
  playground: Partial<PlaygroundState>;
  electorate: Partial<ElectionConfig>;
}

/**
 * Synthetic starting states — defaults you override, never data and never walls.
 * Each preset seeds BOTH the shared electorate and the playground knobs.
 */
export const PLAYGROUND_PRESETS: PlaygroundPreset[] = [
  {
    id: 'two_party',
    label: 'Bipartisme',
    description: 'Deux camps sur un axe gauche–droite — le terrain du votant médian.',
    category: 'model',
    playground: {
      mode: 'leader',
      space: { dims: 1, axisLabels: ['Gauche–Droite'], valenceEnabled: false },
      prefSource: 'spatial',
    },
    electorate: {
      candidates: [
        { name: 'Gauche', x: -0.5, y: 0 },
        { name: 'Droite', x: 0.5, y: 0 },
      ],
      num_voters: 400,
      ideology: 'random',
    },
  },
  {
    id: 'fragmented',
    label: 'Multipartisme fragmenté',
    description: 'Six partis en 2D — proportionnelle, seuils et coalitions.',
    category: 'model',
    playground: {
      mode: 'parliament',
      space: { dims: 2, axisLabels: ['Économique', 'Sociétal'], valenceEnabled: false },
      prefSource: 'spatial',
      assembly: {
        structure: 'pr',
        seats: 100,
        threshold: 0.05,
        apportionment: 'dhondt',
        num_districts: 1,
        strategic_desertion: false,
      },
    },
    electorate: {
      candidates: [
        { name: 'Verts', x: -0.3, y: -0.4 },
        { name: 'Soc.', x: -0.5, y: -0.1 },
        { name: 'Centre', x: 0.0, y: 0.0 },
        { name: 'Libéraux', x: 0.3, y: 0.0 },
        { name: 'Cons.', x: 0.5, y: 0.3 },
        { name: 'Droite rad.', x: 0.8, y: 0.7 },
      ],
      num_voters: 600,
      ideology: 'polarized',
    },
  },
  {
    id: 'single_issue',
    label: 'Enjeu unique',
    description: 'Trois options sur un seul axe — la clarté du votant médian.',
    category: 'model',
    playground: {
      mode: 'leader',
      space: { dims: 1, axisLabels: ['Pour ↔ Contre'], valenceEnabled: false },
      prefSource: 'spatial',
    },
    electorate: {
      candidates: [
        { name: 'Pour', x: -0.6, y: 0 },
        { name: 'Compromis', x: 0.0, y: 0 },
        { name: 'Contre', x: 0.6, y: 0 },
      ],
      num_voters: 300,
      ideology: 'centrist',
    },
  },
  {
    id: 'france2002_like',
    label: 'France 2002 (synthétique)',
    description: 'Gauche fragmentée, extrêmes polarisés — le terrain du spoiler.',
    category: 'election',
    playground: {
      mode: 'leader',
      space: { dims: 2, axisLabels: ['Économique', 'Sociétal'], valenceEnabled: false },
      prefSource: 'spatial',
    },
    electorate: {
      candidates: SCENARIOS.france2002.candidates,
      num_voters: 500,
      ideology: 'polarized',
    },
  },
  {
    id: 'usa2000_like',
    label: 'USA 2000 (synthétique)',
    description: 'Nader spoile Gore — Bush gagne en pluralité malgré Gore vainqueur de Condorcet.',
    category: 'election',
    playground: {
      mode: 'leader',
      space: { dims: 1, axisLabels: ['Gauche–Droite'], valenceEnabled: false },
      prefSource: 'spatial',
    },
    electorate: {
      candidates: [
        { name: 'Nader', x: -0.7, y: 0 },
        { name: 'Gore', x: -0.1, y: 0 },
        { name: 'Bush', x: 0.6, y: 0 },
      ],
      num_voters: 400,
      ideology: 'random',
    },
  },
  {
    id: 'weimar1932_like',
    label: 'Weimar 1932 (synthétique)',
    description: 'Cinq partis polarisés, PR sans seuil — aucune majorité sans les extrêmes.',
    category: 'election',
    playground: {
      mode: 'parliament',
      space: { dims: 2, axisLabels: ['Économique', 'Autoritaire'], valenceEnabled: false },
      prefSource: 'spatial',
      assembly: {
        structure: 'pr',
        seats: 100,
        threshold: 0,
        apportionment: 'dhondt',
        num_districts: 1,
        strategic_desertion: false,
      },
    },
    electorate: {
      candidates: [
        { name: 'KPD', x: -0.85, y: 0.5 },
        { name: 'SPD', x: -0.4, y: -0.1 },
        { name: 'Zentrum', x: 0.0, y: 0.15 },
        { name: 'DNVP', x: 0.55, y: 0.35 },
        { name: 'NSDAP', x: 0.45, y: 0.85 },
      ],
      num_voters: 600,
      ideology: 'polarized',
    },
  },
];

// ── Helpers ───────────────────────────────────────────────────────────────────

const LS_KEY = 'votelab_election_config';
const LS_PLAYGROUND_KEY = 'votelab_playground';

function deepSet(obj: unknown, path: string, value: unknown): unknown {
  const parts = path.split('.');
  if (parts.length === 1) return { ...(obj as object), [parts[0]]: value };
  const [head, ...rest] = parts;
  const parent = obj as Record<string, unknown>;
  return { ...parent, [head]: deepSet(parent[head] ?? {}, rest.join('.'), value) };
}

function loadConfig(): ElectionConfig {
  try {
    const raw = localStorage.getItem(LS_KEY);
    return raw ? (JSON.parse(raw) as ElectionConfig) : DEFAULT_CONFIG;
  } catch {
    return DEFAULT_CONFIG;
  }
}

function saveConfig(config: ElectionConfig): void {
  try {
    localStorage.setItem(LS_KEY, JSON.stringify(config));
  } catch {
    /* ignore */
  }
}

function loadPlayground(): PlaygroundState {
  try {
    const raw = localStorage.getItem(LS_PLAYGROUND_KEY);
    if (!raw) return DEFAULT_PLAYGROUND;
    const parsed = JSON.parse(raw) as Partial<PlaygroundState>;
    // Merge over defaults (nested slices too) so a stored older shape keeps
    // every knob present — e.g. assembly.strategic_desertion added in P4.
    return {
      ...DEFAULT_PLAYGROUND,
      ...parsed,
      space: { ...DEFAULT_PLAYGROUND.space, ...(parsed.space ?? {}) },
      ballot: { ...DEFAULT_PLAYGROUND.ballot, ...(parsed.ballot ?? {}) },
      turnout: { ...DEFAULT_PLAYGROUND.turnout, ...(parsed.turnout ?? {}) },
      electorate: { ...DEFAULT_PLAYGROUND.electorate, ...(parsed.electorate ?? {}) },
      assembly: { ...DEFAULT_PLAYGROUND.assembly, ...(parsed.assembly ?? {}) },
    };
  } catch {
    return DEFAULT_PLAYGROUND;
  }
}

function savePlayground(pg: PlaygroundState): void {
  try {
    localStorage.setItem(LS_PLAYGROUND_KEY, JSON.stringify(pg));
  } catch {
    /* ignore */
  }
}

// ── Store ─────────────────────────────────────────────────────────────────

export const SCENARIO_NAMES = Object.keys(SCENARIOS);

interface ElectionState {
  config: ElectionConfig;
  scenarioMeta: ScenarioMeta | null;
  playground: PlaygroundState;
  setConfig: (patch: Partial<ElectionConfig>) => void;
  setConfigDeep: (path: string, value: unknown) => void;
  replaceConfig: (next: ElectionConfig) => void;
  resetConfig: () => void;
  applyScenario: (name: string) => void;
  clearScenarioMeta: () => void;
  setMode: (mode: PlaygroundMode) => void;
  setPlayground: (patch: Partial<PlaygroundState>) => void;
  setPlaygroundDeep: (path: string, value: unknown) => void;
  applyPreset: (id: string) => void;
  setElectorate: (patch: Partial<ElectorateComposition>) => void;
  updateCommunity: (id: string, patch: Partial<Community>) => void;
  addCommunity: () => void;
  removeCommunity: (id: string) => void;
  applyElectoratePreset: (id: string) => void;
  hydrate: () => void;
}

export const useElectionStore = create<ElectionState>((set) => ({
  config: loadConfig(),
  scenarioMeta: null,
  playground: loadPlayground(),

  setConfig: (patch) =>
    set((s) => {
      const config = { ...s.config, ...patch };
      saveConfig(config);
      return { config, scenarioMeta: null };
    }),

  setConfigDeep: (path, value) =>
    set((s) => {
      const config = deepSet(s.config, path, value) as ElectionConfig;
      saveConfig(config);
      return { config, scenarioMeta: null };
    }),

  replaceConfig: (next) => {
    saveConfig(next);
    set({ config: next, scenarioMeta: null });
  },

  resetConfig: () => {
    saveConfig(DEFAULT_CONFIG);
    set({ config: DEFAULT_CONFIG, scenarioMeta: null });
  },

  applyScenario: (name) => {
    const scenario = SCENARIOS[name];
    if (!scenario) return;
    saveConfig(scenario);
    set({
      config: scenario,
      scenarioMeta: scenario.description
        ? {
            id: name,
            name,
            description: scenario.description,
            phenomenon: scenario.phenomenon ?? '',
          }
        : null,
    });
  },

  clearScenarioMeta: () => set({ scenarioMeta: null }),

  // ── Playground actions ──────────────────────────────────────────────────
  setMode: (mode) =>
    set((s) => {
      const playground = { ...s.playground, mode };
      savePlayground(playground);
      return { playground };
    }),

  setPlayground: (patch) =>
    set((s) => {
      const playground = { ...s.playground, ...patch };
      savePlayground(playground);
      return { playground };
    }),

  setPlaygroundDeep: (path, value) =>
    set((s) => {
      const playground = deepSet(s.playground, path, value) as PlaygroundState;
      savePlayground(playground);
      return { playground };
    }),

  applyPreset: (id) =>
    set((s) => {
      const preset = PLAYGROUND_PRESETS.find((p) => p.id === id);
      if (!preset) return {};
      track('preset_applied', { preset: id });
      const playground = { ...DEFAULT_PLAYGROUND, ...preset.playground };
      const config = { ...s.config, ...preset.electorate };
      savePlayground(playground);
      saveConfig(config);
      return { playground, config, scenarioMeta: null };
    }),

  // ── Electorate composer actions ─────────────────────────────────────────
  setElectorate: (patch) =>
    set((s) => {
      const playground = { ...s.playground, electorate: { ...s.playground.electorate, ...patch } };
      savePlayground(playground);
      return { playground };
    }),

  updateCommunity: (id, patch) =>
    set((s) => {
      const electorate = {
        ...s.playground.electorate,
        communities: s.playground.electorate.communities.map((c) =>
          c.id === id ? { ...c, ...patch } : c
        ),
      };
      const playground = { ...s.playground, electorate };
      savePlayground(playground);
      return { playground };
    }),

  addCommunity: () =>
    set((s) => {
      const existing = s.playground.electorate.communities;
      const n = existing.length + 1;
      const community: Community = {
        id: `c${Date.now().toString(36)}`,
        label: `Communauté ${n}`,
        x: 0,
        y: 0,
        spread: 0.18,
        weight: 1,
        turnout: 0.85,
      };
      const electorate = { ...s.playground.electorate, communities: [...existing, community] };
      const playground = { ...s.playground, electorate };
      savePlayground(playground);
      return { playground };
    }),

  removeCommunity: (id) =>
    set((s) => {
      const rest = s.playground.electorate.communities.filter((c) => c.id !== id);
      if (rest.length < 1) return {}; // keep at least one bloc
      const electorate = { ...s.playground.electorate, communities: rest };
      const playground = { ...s.playground, electorate };
      savePlayground(playground);
      return { playground };
    }),

  applyElectoratePreset: (id) =>
    set((s) => {
      const preset = ELECTORATE_PRESETS[id];
      if (!preset) return {};
      const electorate: ElectorateComposition = {
        mode: 'composed',
        correlation: preset.correlation,
        noise: s.playground.electorate.noise, // keep the user's measurement noise
        communities: preset.communities.map((c) => ({ ...c })), // deep copy (editable)
      };
      const playground = { ...s.playground, electorate };
      savePlayground(playground);
      return { playground };
    }),

  hydrate: () => set({ config: loadConfig(), playground: loadPlayground() }),
}));

// ── Convenience hook (former ElectionContext API) ─────────────────────────────

export interface ElectionContextValue {
  config: ElectionConfig;
  setConfig: (patch: Partial<ElectionConfig>) => void;
  setConfigDeep: (path: string, value: unknown) => void;
  replaceConfig: (next: ElectionConfig) => void;
  resetConfig: () => void;
  applyScenario: (name: string) => void;
  scenarioNames: string[];
  scenarioMeta: ScenarioMeta | null;
  clearScenarioMeta: () => void;
}

/**
 * Optional provider — the store self-hydrates `config` at module init, so this is
 * only a hydrate-on-mount hook (kept for test isolation + so existing
 * `<ElectionProvider>` wrappers in tests/App keep working). Not required for the
 * store to function.
 */
export const ElectionProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const hydrate = useElectionStore((s) => s.hydrate);
  useEffect(() => {
    hydrate();
  }, [hydrate]);
  return <>{children}</>;
};

// ── Electorate override (read-only) ─────────────────────────────────────────
//
// A subtree can be pinned to a DIFFERENT electorate than the global store — the
// Laboratoire's side-by-side comparison renders the SAME phenomenon on electorate
// B here. Reads are overridden; writes are no-ops so the compared column cannot
// mutate the real electorate. `useElection`/`usePlayground` are the only store
// entry points (verified), so this reaches every one of the 57 fiches.
interface ElectorateOverrideValue {
  config: ElectionConfig;
  playground: PlaygroundState;
}
const ElectorateOverrideContext = React.createContext<ElectorateOverrideValue | null>(null);

export const ElectorateOverrideProvider: React.FC<{
  config: ElectionConfig;
  playground: PlaygroundState;
  children: React.ReactNode;
}> = ({ config, playground, children }) => {
  const value = React.useMemo(() => ({ config, playground }), [config, playground]);
  return (
    <ElectorateOverrideContext.Provider value={value}>
      {children}
    </ElectorateOverrideContext.Provider>
  );
};

const _noop = () => {};

export function useElection(): ElectionContextValue {
  const override = React.useContext(ElectorateOverrideContext);
  const config = useElectionStore((s) => s.config);
  const setConfig = useElectionStore((s) => s.setConfig);
  const setConfigDeep = useElectionStore((s) => s.setConfigDeep);
  const replaceConfig = useElectionStore((s) => s.replaceConfig);
  const resetConfig = useElectionStore((s) => s.resetConfig);
  const applyScenario = useElectionStore((s) => s.applyScenario);
  const scenarioMeta = useElectionStore((s) => s.scenarioMeta);
  const clearScenarioMeta = useElectionStore((s) => s.clearScenarioMeta);
  if (override) {
    return {
      config: override.config,
      setConfig: _noop,
      setConfigDeep: _noop,
      replaceConfig: _noop,
      resetConfig: _noop,
      applyScenario: _noop,
      scenarioNames: SCENARIO_NAMES,
      scenarioMeta: null,
      clearScenarioMeta: _noop,
    };
  }
  return {
    config,
    setConfig,
    setConfigDeep,
    replaceConfig,
    resetConfig,
    applyScenario,
    scenarioNames: SCENARIO_NAMES,
    scenarioMeta,
    clearScenarioMeta,
  };
}

// ── Playground convenience hook ───────────────────────────────────────────────

export interface PlaygroundContextValue {
  playground: PlaygroundState;
  setMode: (mode: PlaygroundMode) => void;
  setPlayground: (patch: Partial<PlaygroundState>) => void;
  setPlaygroundDeep: (path: string, value: unknown) => void;
  applyPreset: (id: string) => void;
  presets: PlaygroundPreset[];
  setElectorate: (patch: Partial<ElectorateComposition>) => void;
  updateCommunity: (id: string, patch: Partial<Community>) => void;
  addCommunity: () => void;
  removeCommunity: (id: string) => void;
  applyElectoratePreset: (id: string) => void;
}

export function usePlayground(): PlaygroundContextValue {
  const override = React.useContext(ElectorateOverrideContext);
  const playground = useElectionStore((s) => s.playground);
  const setMode = useElectionStore((s) => s.setMode);
  const setPlayground = useElectionStore((s) => s.setPlayground);
  const setPlaygroundDeep = useElectionStore((s) => s.setPlaygroundDeep);
  const applyPreset = useElectionStore((s) => s.applyPreset);
  const setElectorate = useElectionStore((s) => s.setElectorate);
  const updateCommunity = useElectionStore((s) => s.updateCommunity);
  const addCommunity = useElectionStore((s) => s.addCommunity);
  const removeCommunity = useElectionStore((s) => s.removeCommunity);
  const applyElectoratePreset = useElectionStore((s) => s.applyElectoratePreset);
  if (override) {
    return {
      playground: override.playground,
      setMode: _noop,
      setPlayground: _noop,
      setPlaygroundDeep: _noop,
      applyPreset: _noop,
      presets: PLAYGROUND_PRESETS,
      setElectorate: _noop,
      updateCommunity: _noop,
      addCommunity: _noop,
      removeCommunity: _noop,
      applyElectoratePreset: _noop,
    };
  }
  return {
    playground,
    setMode,
    setPlayground,
    setPlaygroundDeep,
    applyPreset,
    presets: PLAYGROUND_PRESETS,
    setElectorate,
    updateCommunity,
    addCommunity,
    removeCommunity,
    applyElectoratePreset,
  };
}
