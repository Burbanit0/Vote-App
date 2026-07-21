// stories.ts — scripted "histoires" that walk a voting-theory phenomenon through
// the REAL instrument, one beat at a time. A story is pure data: each step is a
// patch applied to the live playground state (config + playground knobs + the
// counting rule + which moment is in focus). The player (StoryPlayer.tsx) is thin
// and drives the same context setters the user drives by hand — no parallel state,
// no smuggled model. This is GuidedFooter's pattern applied to phenomena instead
// of UI moments.
//
// Positions are chosen so the claimed beats actually hold on the seeded
// electorate; `stories.test.ts` locks every load-bearing outcome (spoiler flip,
// centre squeeze, method divergence…) so a drifted coordinate fails CI rather
// than silently lying to the visitor.

import type { ElectionConfig, PlaygroundMode, PlaygroundState } from '../stores/useElectionStore';
import type { Rule } from './playgroundVoting';
import type { Community } from './playgroundElectorate';
import type { MomentId } from '../components/playground/MomentRail';

/** One beat: a state patch + a sentence. Every field is optional — a step patches
 *  only what changes from the previous beat. `beatKey` resolves in the `playground`
 *  i18n namespace under `stories.<storyId>.steps`. */
export interface StoryStep {
  id: string;
  beatKey: string;
  /** Focus a moment (drives the left panel + the map lens, as a manual click would). */
  moment?: MomentId;
  /** Leader vs assembly. */
  mode?: PlaygroundMode;
  /** The counting rule shown on the instrument (leader mode). */
  rule?: Rule;
  /** Shared-electorate patch (candidate positions, voter count, seed, ideology…). */
  config?: Partial<ElectionConfig>;
  /** Playground-knob patch (space/dims, electorate, strategy…). */
  playground?: Partial<PlaygroundState>;
}

export interface Story {
  id: string;
  titleKey: string;
  taglineKey: string;
  /** lucide icon name resolved in the picker (kept as data so the lib stays UI-free). */
  icon: string;
  /** Which instrument the story narrates — the picker only offers the current one. */
  mode: PlaygroundMode;
  steps: StoryStep[];
}

// Shared spatial spaces (full objects — setPlayground replaces `space` wholesale).
const LINE = (label: string, valence = false) => ({
  space: { dims: 1 as const, axisLabels: [label], valenceEnabled: valence },
});
const PLANE = {
  space: { dims: 2 as const, axisLabels: ['Économique', 'Sociétal'], valenceEnabled: false },
};

// ── Story 1 — the spoiler effect ────────────────────────────────────────────
// Two candidates → a third that can't win still changes who does; the rule, not
// the electorate, decides whether that happens.
const SPOILER_2 = [
  { name: 'Gore', x: -0.35, y: 0 },
  { name: 'Bush', x: 0.55, y: 0 },
];
const SPOILER_3 = [
  { name: 'Nader', x: -0.8, y: 0 },
  { name: 'Gore', x: -0.35, y: 0 },
  { name: 'Bush', x: 0.55, y: 0 },
];
// A bimodal ("polarized") electorate is what makes a spoiler real: Nader + Gore
// split the left hump while Bush owns the right one. A single Gaussian electorate
// is near-single-peaked and simply elects the centrist — no spoiler to show.
const SPOILER_ELECTORATE = { num_voters: 500, seed: 7, ideology: 'polarized' };

// ── Story 2 — the centre squeeze ────────────────────────────────────────────
const SQUEEZE = [
  { name: 'Gauche', x: -0.55, y: 0 },
  { name: 'Centre', x: 0.0, y: 0 },
  { name: 'Droite', x: 0.55, y: 0 },
];
const SQUEEZE_ELECTORATE = { num_voters: 400, seed: 11, ideology: 'polarized' };

// ── Story 3 — the Condorcet paradox: "it depends who counts" ─────────────────
// Three candidates, one electorate — yet plurality, IRV and approval each crown a
// DIFFERENT winner. A single Gaussian is near-single-peaked and can't do this, so
// the electorate is a composed mixture of three rotated blocs (rock-paper-scissors
// preferences), the honest way to produce a genuine majority paradox.
const PARADOX = [
  { name: 'Alice', x: 0.0, y: 0.7 },
  { name: 'Bob', x: 0.7, y: -0.5 },
  { name: 'Carol', x: -0.7, y: -0.5 },
];
const paradoxBloc = (id: string, label: string, x: number, y: number): Community => ({
  id,
  label,
  x,
  y,
  z: 0,
  spread: 0.05,
  weight: 1,
  turnout: 1,
});
const PARADOX_ELECTORATE = { num_voters: 600, seed: 42, ideology: 'polarized' };
const PARADOX_COMPOSED: PlaygroundState['electorate'] = {
  mode: 'composed',
  correlation: 0,
  noise: 0,
  communities: [
    paradoxBloc('g1', 'Bloc A→B', 0.2, 0.25),
    paradoxBloc('g2', 'Bloc B→C', 0.42, -0.45),
    paradoxBloc('g3', 'Bloc C→A', -0.52, -0.18),
  ],
};

// ── Story 4 — the "vote utile" arms race ────────────────────────────────────
const UTILE = [
  { name: 'Gauche', x: -0.55, y: 0 },
  { name: 'Écolo', x: -0.3, y: 0 },
  { name: 'Droite', x: 0.45, y: 0 },
];
const UTILE_ELECTORATE = { num_voters: 400, seed: 23, ideology: 'random' };

// ── Story 5 — majority vs welfare (valence) ─────────────────────────────────
// A near-median candidate wins on position alone; a slightly-off but far
// higher-quality candidate wins once valence (non-spatial quality) is switched on.
const VALENCE = [
  { name: 'Sortant', x: -0.1, y: 0, valence: -0.2 },
  { name: 'Réformateur', x: 0.4, y: 0, valence: 0.8 },
];
const VALENCE_ELECTORATE = { num_voters: 400, seed: 5, ideology: 'random' };

// ── Story 6 — one electorate, several verdicts ──────────────────────────────
// A messy real-flavoured field (France 2002, 8 candidates): plurality crowns
// Chirac, the runoff/IRV family crowns Jospin, the consensus methods crown
// Bayrou — same voters, three different presidents depending on the method.
const FIVE = [
  { name: 'Chirac', x: 0.3, y: 0.4 },
  { name: 'Jospin', x: -0.4, y: -0.3 },
  { name: 'Le Pen', x: 0.8, y: 0.8 },
  { name: 'Bayrou', x: 0.1, y: 0.1 },
  { name: 'Chevènement', x: -0.2, y: 0.1 },
  { name: 'Mégret', x: 0.9, y: 0.9 },
  { name: 'Taubira', x: -0.7, y: -0.6 },
  { name: 'Besancenot', x: -0.8, y: -0.5 },
];
const FIVE_ELECTORATE = { num_voters: 500, seed: 2002, ideology: 'polarized' };

// ── Parliament stories (mode: 'parliament') ──────────────────────────────────
// Seats are allocated by the BACKEND (/api/v2/election/assembly), so unlike the
// leader stories these beats can't be locked by a client-side winner assertion.
// They were written against real runs of that worker on this exact field/seed;
// the figures quoted in each beat are recorded in the comments below so a future
// engine change that invalidates them is at least visible in review.
const PARL = [
  { name: 'Gauche', x: -0.55, y: -0.2 },
  { name: 'Verts', x: -0.35, y: 0.45 },
  { name: 'Centre', x: 0.0, y: 0.0 },
  { name: 'Droite', x: 0.5, y: 0.15 },
  { name: 'Souverainistes', x: 0.85, y: 0.75 },
];
// Vote shares on this seed: Gauche .205 · Verts .194 · Centre .353 · Droite .214
// · Souverainistes .034 (the one party the 5 % threshold bites).
const PARL_ELECTORATE = { num_voters: 1000, seed: 17, ideology: 'random' };

// setPlayground merges shallowly, so an `assembly` patch must be a full object.
const ASM = (patch: Partial<PlaygroundState['assembly']>): PlaygroundState['assembly'] => ({
  structure: 'pr',
  seats: 100,
  threshold: 0.05,
  apportionment: 'dhondt',
  num_districts: 1,
  strategic_desertion: false,
  ...patch,
});

export const STORIES: Story[] = [
  {
    id: 'spoiler',
    titleKey: 'stories.spoiler.title',
    taglineKey: 'stories.spoiler.tagline',
    icon: 'Ghost',
    mode: 'leader',
    steps: [
      {
        id: 'duel',
        beatKey: 'stories.spoiler.steps.duel',
        mode: 'leader',
        rule: 'plurality',
        moment: 'method',
        playground: LINE('Gauche–Droite'),
        config: { candidates: SPOILER_2, ...SPOILER_ELECTORATE },
      },
      {
        id: 'enter',
        beatKey: 'stories.spoiler.steps.enter',
        rule: 'plurality',
        config: { candidates: SPOILER_3, ...SPOILER_ELECTORATE },
      },
      {
        id: 'irv',
        beatKey: 'stories.spoiler.steps.irv',
        rule: 'irv',
        config: { candidates: SPOILER_3, ...SPOILER_ELECTORATE },
      },
      {
        id: 'condorcet',
        beatKey: 'stories.spoiler.steps.condorcet',
        rule: 'condorcet',
        config: { candidates: SPOILER_3, ...SPOILER_ELECTORATE },
      },
    ],
  },
  {
    id: 'squeeze',
    titleKey: 'stories.squeeze.title',
    taglineKey: 'stories.squeeze.tagline',
    icon: 'Minimize2',
    mode: 'leader',
    steps: [
      {
        id: 'field',
        beatKey: 'stories.squeeze.steps.field',
        mode: 'leader',
        rule: 'plurality',
        moment: 'method',
        playground: LINE('Gauche–Droite'),
        config: { candidates: SQUEEZE, ...SQUEEZE_ELECTORATE },
      },
      {
        id: 'condorcet',
        beatKey: 'stories.squeeze.steps.condorcet',
        rule: 'condorcet',
        config: { candidates: SQUEEZE, ...SQUEEZE_ELECTORATE },
      },
      {
        id: 'irv',
        beatKey: 'stories.squeeze.steps.irv',
        rule: 'irv',
        config: { candidates: SQUEEZE, ...SQUEEZE_ELECTORATE },
      },
    ],
  },
  {
    id: 'paradox',
    titleKey: 'stories.paradox.title',
    taglineKey: 'stories.paradox.tagline',
    icon: 'RefreshCw',
    mode: 'leader',
    steps: [
      {
        id: 'plurality',
        beatKey: 'stories.paradox.steps.plurality',
        mode: 'leader',
        rule: 'plurality',
        moment: 'method',
        playground: { space: PLANE.space, electorate: PARADOX_COMPOSED },
        config: { candidates: PARADOX, ...PARADOX_ELECTORATE },
      },
      {
        id: 'irv',
        beatKey: 'stories.paradox.steps.irv',
        rule: 'irv',
        config: { candidates: PARADOX, ...PARADOX_ELECTORATE },
      },
      {
        id: 'approval',
        beatKey: 'stories.paradox.steps.approval',
        rule: 'approval',
        config: { candidates: PARADOX, ...PARADOX_ELECTORATE },
      },
      {
        id: 'condorcet',
        beatKey: 'stories.paradox.steps.condorcet',
        rule: 'condorcet',
        config: { candidates: PARADOX, ...PARADOX_ELECTORATE },
      },
    ],
  },
  {
    id: 'utile',
    titleKey: 'stories.utile.title',
    taglineKey: 'stories.utile.tagline',
    icon: 'Swords',
    mode: 'leader',
    steps: [
      {
        id: 'sincere',
        beatKey: 'stories.utile.steps.sincere',
        mode: 'leader',
        rule: 'plurality',
        moment: 'strategy',
        playground: LINE('Gauche–Droite'),
        config: { candidates: UTILE, ...UTILE_ELECTORATE },
      },
      {
        id: 'tempt',
        beatKey: 'stories.utile.steps.tempt',
        rule: 'plurality',
        config: { candidates: UTILE, ...UTILE_ELECTORATE },
      },
      {
        id: 'approval',
        beatKey: 'stories.utile.steps.approval',
        rule: 'approval',
        config: { candidates: UTILE, ...UTILE_ELECTORATE },
      },
      {
        id: 'irv',
        beatKey: 'stories.utile.steps.irv',
        rule: 'irv',
        config: { candidates: UTILE, ...UTILE_ELECTORATE },
      },
    ],
  },
  {
    id: 'valence',
    titleKey: 'stories.valence.title',
    taglineKey: 'stories.valence.tagline',
    icon: 'Sparkles',
    mode: 'leader',
    steps: [
      {
        id: 'position',
        beatKey: 'stories.valence.steps.position',
        mode: 'leader',
        rule: 'plurality',
        moment: 'bilan',
        playground: LINE('Gauche–Droite', false),
        config: { candidates: VALENCE, ...VALENCE_ELECTORATE },
      },
      {
        id: 'quality',
        beatKey: 'stories.valence.steps.quality',
        rule: 'plurality',
        playground: LINE('Gauche–Droite', true),
        config: { candidates: VALENCE, ...VALENCE_ELECTORATE },
      },
    ],
  },
  {
    id: 'five',
    titleKey: 'stories.five.title',
    taglineKey: 'stories.five.tagline',
    icon: 'Shuffle',
    mode: 'leader',
    steps: [
      {
        id: 'plurality',
        beatKey: 'stories.five.steps.plurality',
        mode: 'leader',
        rule: 'plurality',
        moment: 'bilan',
        playground: PLANE,
        config: { candidates: FIVE, ...FIVE_ELECTORATE },
      },
      {
        id: 'irv',
        beatKey: 'stories.five.steps.irv',
        rule: 'irv',
        config: { candidates: FIVE, ...FIVE_ELECTORATE },
      },
      {
        id: 'borda',
        beatKey: 'stories.five.steps.borda',
        rule: 'borda',
        config: { candidates: FIVE, ...FIVE_ELECTORATE },
      },
      {
        id: 'condorcet',
        beatKey: 'stories.five.steps.condorcet',
        rule: 'condorcet',
        config: { candidates: FIVE, ...FIVE_ELECTORATE },
      },
      {
        id: 'approval',
        beatKey: 'stories.five.steps.approval',
        rule: 'approval',
        config: { candidates: FIVE, ...FIVE_ELECTORATE },
      },
    ],
  },

  // ── Parliament 1 — the threshold ───────────────────────────────────────────
  // thr 0 %: Souverainistes 3 seats, Gallagher .008 · thr 5 %: 0 seats, 3.4 % of
  // votes wasted, Gallagher .028 · + desertion: their voters leave for Droite
  // (.214 → .246), wasted back to 0.
  {
    id: 'seuil',
    titleKey: 'stories.seuil.title',
    taglineKey: 'stories.seuil.tagline',
    icon: 'Scissors',
    mode: 'parliament',
    steps: [
      {
        id: 'pur',
        beatKey: 'stories.seuil.steps.pur',
        mode: 'parliament',
        moment: 'method',
        playground: { space: PLANE.space, assembly: ASM({ threshold: 0 }) },
        config: { candidates: PARL, ...PARL_ELECTORATE },
      },
      {
        id: 'barre',
        beatKey: 'stories.seuil.steps.barre',
        playground: { assembly: ASM({ threshold: 0.05 }) },
      },
      {
        id: 'desertion',
        beatKey: 'stories.seuil.steps.desertion',
        playground: { assembly: ASM({ threshold: 0.05, strategic_desertion: true }) },
      },
    ],
  },

  // ── Parliament 2 — one vote, three parliaments ─────────────────────────────
  // PR: Gallagher .028, 3.4 % wasted · FPTP: Centre 35 % of votes → 41 % of
  // seats, Verts 19 % → 9 %, 30.5 % wasted, Gallagher .097 · MMP: top-up seats
  // restore proportionality (Gallagher .028) while keeping local members.
  {
    id: 'structures',
    titleKey: 'stories.structures.title',
    taglineKey: 'stories.structures.tagline',
    icon: 'Landmark',
    mode: 'parliament',
    steps: [
      {
        id: 'pr',
        beatKey: 'stories.structures.steps.pr',
        mode: 'parliament',
        moment: 'method',
        playground: { space: PLANE.space, assembly: ASM({ structure: 'pr' }) },
        config: { candidates: PARL, ...PARL_ELECTORATE },
      },
      {
        id: 'fptp',
        beatKey: 'stories.structures.steps.fptp',
        playground: { assembly: ASM({ structure: 'fptp' }) },
      },
      {
        id: 'mmp',
        beatKey: 'stories.structures.steps.mmp',
        playground: { assembly: ASM({ structure: 'mmp' }) },
      },
    ],
  },

  // ── Parliament 3 — the divisor ─────────────────────────────────────────────
  // 21 seats, no threshold. D'Hondt: Centre 8 / Souverainistes 0 (Gallagher .037)
  // · Sainte-Laguë: Centre 7 / Souverainistes 1 (Gallagher .026).
  {
    id: 'diviseur',
    titleKey: 'stories.diviseur.title',
    taglineKey: 'stories.diviseur.tagline',
    icon: 'Divide',
    mode: 'parliament',
    steps: [
      {
        id: 'dhondt',
        beatKey: 'stories.diviseur.steps.dhondt',
        mode: 'parliament',
        moment: 'method',
        playground: {
          space: PLANE.space,
          assembly: ASM({ seats: 21, threshold: 0, apportionment: 'dhondt' }),
        },
        config: { candidates: PARL, ...PARL_ELECTORATE },
      },
      {
        id: 'sainteLague',
        beatKey: 'stories.diviseur.steps.sainteLague',
        playground: { assembly: ASM({ seats: 21, threshold: 0, apportionment: 'sainte_lague' }) },
      },
    ],
  },
];

export const storyById = (id: string): Story | undefined => STORIES.find((s) => s.id === id);

/** The picker only offers the instrument you're actually looking at. */
export const storiesForMode = (mode: PlaygroundMode): Story[] =>
  STORIES.filter((s) => s.mode === mode);
