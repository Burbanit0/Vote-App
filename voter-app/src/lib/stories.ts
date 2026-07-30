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
import type { NamedPt, Rule } from './playgroundVoting';
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

// ── Story 7 — the clone strategy (Borda's Achilles heel) ────────────────────
// A camp can steal an election by fielding a near-identical ally. Borda hands
// out partial credit for being someone's second choice; the clone siphons that
// credit away from the true majority winner. Condorcet (pairwise) and IRV
// (first-choice transfers) never look at "second choice" that way, so the same
// trick does nothing to them — a clean demonstration of independence of clones.
const CLONE_A = { name: 'A', x: -0.5, y: 0 };
const CLONE_A2 = { name: 'A2', x: -0.65, y: 0 };
const CLONE_B = { name: 'B', x: 0.5, y: 0 };
const clonesBloc = (id: string, x: number, weight: number): Community => ({
  id,
  label: id,
  x,
  y: 0,
  z: 0,
  spread: 0.12,
  weight,
  turnout: 1,
});
const CLONES_ELECTORATE = { num_voters: 500, seed: 42, ideology: 'random' };
const CLONES_COMPOSED: PlaygroundState['electorate'] = {
  mode: 'composed',
  correlation: 0,
  noise: 0,
  communities: [clonesBloc('P', CLONE_A.x, 0.46), clonesBloc('Q', CLONE_B.x, 0.54)],
};

// ── Story 7 — the blank vote: same result, four fates ──────────────────────
// Camille wins comfortably among those who picked someone — but most of the
// electorate is far from BOTH candidates and rejects the whole field. Three
// constitutional regimes read the identical result three different ways:
// today's law elects Camille anyway (blank excluded from the count); count
// the blank and the mandate evaporates; treat it as a candidate and it wins
// outright. Same voters, same ballots — the regime alone decides.
const REJET_CANDS = [
  { name: 'Camille', x: -0.15, y: 0 },
  { name: 'Farid', x: 0.15, y: 0 },
];
const REJET_ELECTORATE = { num_voters: 300, seed: 42, ideology: 'random' };
const rejetBloc = (
  id: string,
  label: string,
  x: number,
  y: number,
  spread: number,
  weight: number
): Community => ({ id, label, x, y, z: 0, spread, weight, turnout: 1 });
const REJET_COMPOSED: PlaygroundState['electorate'] = {
  mode: 'composed',
  correlation: 0,
  noise: 0,
  communities: [
    rejetBloc('main', 'Grand public', -0.25, 0, 0.08, 0.35),
    rejetBloc('rejet', 'Rejettent tout le monde', 0, -0.9, 0.12, 0.65),
  ],
};
// setPlayground merges shallowly, so `blank` must be a full object each time.
const BLANK = (lens: 'france_today' | 'in_exprimes' | 'competitive'): PlaygroundState['blank'] => ({
  enabled: true,
  intensity: 0.7,
  lens,
});

// ── Story 8 — non-monotonicity: winning support, losing the election ────────
// A phenomenon internal to a SINGLE rule (unlike every story above, which
// compares rules on one electorate): under IRV, a swing bloc that promotes a
// candidate from their 2nd choice to their 1st can cause that SAME candidate
// to lose. Built from exact permutation blocs (an "anchor" point per full
// ranking, tight spread) rather than a free-form spatial field, so first-
// preference counts are exact and hand-verifiable:
//   base (34): Nora>Yanis>Karim · yanisBase (27): Yanis>Nora>Karim
//   karimBase (20): Karim>Yanis>Nora · swing (10): Karim>Nora>Yanis → Nora>Karim>Yanis
// Before: Yanis fewest (29%) is eliminated, transfers to Nora (61% vs Karim's
// 30%) → Nora wins. After the swing bloc promotes Nora to 1st (her first-place
// share rises 38%→49%), Karim becomes fewest instead and HIS transfer goes to
// Yanis (his 2nd choice) → Yanis wins. Nora gained votes and lost the election.
const MONO_NORA: NamedPt = { name: 'Nora', x: 0.0, y: 0.8 };
const MONO_KARIM: NamedPt = { name: 'Karim', x: 0.7, y: -0.5 };
const MONO_YANIS: NamedPt = { name: 'Yanis', x: -0.7, y: -0.5 };
const MONO_CANDS = [MONO_NORA, MONO_KARIM, MONO_YANIS];
// Anchor a bloc so its ballot is exactly X≻Y≻Z (closest to X, then Y, then Z).
const permAnchor = (X: NamedPt, Y: NamedPt, Z: NamedPt) => ({
  x: 0.75 * X.x + 0.2 * Y.x + 0.05 * Z.x,
  y: 0.75 * X.y + 0.2 * Y.y + 0.05 * Z.y,
});
const permBloc = (
  id: string,
  label: string,
  pos: { x: number; y: number },
  weight: number
): Community => ({
  id,
  label,
  x: pos.x,
  y: pos.y,
  z: 0,
  spread: 0.02,
  weight,
  turnout: 1,
});
const MONO_ELECTORATE = { num_voters: 6000, seed: 123, ideology: 'random' };
const MONO_BASE = permBloc(
  'base',
  'Base de Nora (Nora≻Yanis≻Karim)',
  permAnchor(MONO_NORA, MONO_YANIS, MONO_KARIM),
  34
);
const MONO_YANIS_BASE = permBloc(
  'yanisBase',
  'Base de Yanis (Yanis≻Nora≻Karim)',
  permAnchor(MONO_YANIS, MONO_NORA, MONO_KARIM),
  27
);
const MONO_KARIM_BASE = permBloc(
  'karimBase',
  'Base de Karim (Karim≻Yanis≻Nora)',
  permAnchor(MONO_KARIM, MONO_YANIS, MONO_NORA),
  20
);
const MONO_SWING_BEFORE = permBloc(
  'swing',
  'Indécis (Karim≻Nora≻Yanis)',
  permAnchor(MONO_KARIM, MONO_NORA, MONO_YANIS),
  10
);
const MONO_SWING_AFTER = permBloc(
  'swing',
  'Indécis, convaincus (Nora≻Karim≻Yanis)',
  permAnchor(MONO_NORA, MONO_KARIM, MONO_YANIS),
  10
);
const MONO_BEFORE: PlaygroundState['electorate'] = {
  mode: 'composed',
  correlation: 0,
  noise: 0,
  communities: [MONO_BASE, MONO_YANIS_BASE, MONO_KARIM_BASE, MONO_SWING_BEFORE],
};
const MONO_AFTER: PlaygroundState['electorate'] = {
  mode: 'composed',
  correlation: 0,
  noise: 0,
  communities: [MONO_BASE, MONO_YANIS_BASE, MONO_KARIM_BASE, MONO_SWING_AFTER],
};

// ── Story 9 — reversal symmetry: the same winner, upside down ───────────────
// A candidate adored by a large loyal base but ranked LAST by everyone else
// wins plurality both ways: as cast, and with EVERY ballot flipped end to end.
// Reversing a ballot turns each voter's last choice into their first, so a
// candidate who was already the most-rejected elsewhere becomes the new
// front-runner of the reversed field too — plurality only ever looks at
// whoever is "first", so it cannot tell "beloved" from "despised" apart.
//   avant:   Malik≻Sami≻Inès (40) · Inès≻Sami≻Malik (32) · Sami≻Inès≻Malik (28)
//   inverse: Inès≻Sami≻Malik (40) · Malik≻Sami≻Inès (32) · Malik≻Inès≻Sami (28)
// (the "inverse" blocs are literally each "avant" bloc's ranking reversed)
const REV_MALIK: NamedPt = { name: 'Malik', x: 0.0, y: 0.75 };
const REV_INES: NamedPt = { name: 'Inès', x: 0.65, y: -0.45 };
const REV_SAMI: NamedPt = { name: 'Sami', x: -0.65, y: -0.45 };
const REV_CANDS = [REV_MALIK, REV_INES, REV_SAMI];
const REV_AVANT: PlaygroundState['electorate'] = {
  mode: 'composed',
  correlation: 0,
  noise: 0,
  communities: [
    permBloc(
      'base',
      'Base de Malik (Malik≻Sami≻Inès)',
      permAnchor(REV_MALIK, REV_SAMI, REV_INES),
      40
    ),
    permBloc(
      'centreInes',
      'Centre (Inès≻Sami≻Malik)',
      permAnchor(REV_INES, REV_SAMI, REV_MALIK),
      32
    ),
    permBloc(
      'centreSami',
      'Centre (Sami≻Inès≻Malik)',
      permAnchor(REV_SAMI, REV_INES, REV_MALIK),
      28
    ),
  ],
};
const REV_INVERSE: PlaygroundState['electorate'] = {
  mode: 'composed',
  correlation: 0,
  noise: 0,
  communities: [
    permBloc(
      'base-rev',
      'Base de Malik, bulletin renversé',
      permAnchor(REV_INES, REV_SAMI, REV_MALIK),
      40
    ),
    permBloc(
      'centreInes-rev',
      'Centre, bulletin renversé',
      permAnchor(REV_MALIK, REV_SAMI, REV_INES),
      32
    ),
    permBloc(
      'centreSami-rev',
      'Centre, bulletin renversé',
      permAnchor(REV_MALIK, REV_INES, REV_SAMI),
      28
    ),
  ],
};

// ── Story 10 — later-no-harm: the approval that costs you your favourite ────
// Under approval voting, a bloc's TRUE favourite never changes — but sincerely
// approving of an acceptable second choice, on top of their favourite (never
// instead of), can hand the win to that second choice. Later-no-harm says
// ranking/approving a later preference should never hurt an earlier one;
// approval voting is one of the well-known methods that fails it (unlike IRV,
// which is later-no-harm-safe by construction — see `monotonie`'s IRV twist
// for a different single-rule self-contradiction).
//   Léa -0.6 · Hugo 0.3 · Zoé 0.9 (a line). Fixed blocs: K -0.85 (25, only
//   ever approves Léa) · H 0.4 (35, only ever approves Hugo/Zoé). Swing bloc
//   G moves -0.7 → -0.3 (still strictly closer to Léa than to Hugo both
//   times — their FIRST preference never moves) but crosses the 50 %
//   normalised-utility approval line for Hugo on the way: 0 %→100 % of G
//   approves Hugo too. Léa's own approval share never changes (61 %); Hugo's
//   rises 39 %→72 % on G's extra approvals alone and overtakes her.
const LNH_LEA: NamedPt = { name: 'Léa', x: -0.6, y: 0 };
const LNH_HUGO: NamedPt = { name: 'Hugo', x: 0.3, y: 0 };
const LNH_ZOE: NamedPt = { name: 'Zoé', x: 0.9, y: 0 };
const LNH_CANDS = [LNH_LEA, LNH_HUGO, LNH_ZOE];
const lnhBloc = (
  id: string,
  label: string,
  x: number,
  spread: number,
  weight: number
): Community => ({
  id,
  label,
  x,
  y: 0,
  z: 0,
  spread,
  weight,
  turnout: 1,
});
const LNH_ELECTORATE = { num_voters: 6000, seed: 88, ideology: 'random' };
const LNH_K = lnhBloc('K', 'Base de Léa', -0.85, 0.06, 25);
const LNH_H = lnhBloc('H', 'Sympathisants de Hugo et Zoé', 0.4, 0.15, 35);
const LNH_AVANT: PlaygroundState['electorate'] = {
  mode: 'composed',
  correlation: 0,
  noise: 0,
  communities: [LNH_K, LNH_H, lnhBloc('G', 'Indécis, n’approuvent que Léa', -0.7, 0.04, 30)],
};
const LNH_APRES: PlaygroundState['electorate'] = {
  mode: 'composed',
  correlation: 0,
  noise: 0,
  communities: [LNH_K, LNH_H, lnhBloc('G', 'Les mêmes, approuvent aussi Hugo', -0.3, 0.04, 30)],
};

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

  {
    id: 'clones',
    titleKey: 'stories.clones.title',
    taglineKey: 'stories.clones.tagline',
    icon: 'Copy',
    mode: 'leader',
    steps: [
      {
        id: 'duel',
        beatKey: 'stories.clones.steps.duel',
        mode: 'leader',
        rule: 'borda',
        moment: 'method',
        playground: { ...LINE('Gauche–Droite'), electorate: CLONES_COMPOSED },
        config: { candidates: [CLONE_A, CLONE_B], ...CLONES_ELECTORATE },
      },
      {
        id: 'clone',
        beatKey: 'stories.clones.steps.clone',
        rule: 'borda',
        config: { candidates: [CLONE_A, CLONE_A2, CLONE_B], ...CLONES_ELECTORATE },
      },
      {
        id: 'condorcet',
        beatKey: 'stories.clones.steps.condorcet',
        rule: 'condorcet',
        config: { candidates: [CLONE_A, CLONE_A2, CLONE_B], ...CLONES_ELECTORATE },
      },
      {
        id: 'irv',
        beatKey: 'stories.clones.steps.irv',
        rule: 'irv',
        config: { candidates: [CLONE_A, CLONE_A2, CLONE_B], ...CLONES_ELECTORATE },
      },
    ],
  },

  {
    id: 'blank',
    titleKey: 'stories.blank.title',
    taglineKey: 'stories.blank.tagline',
    icon: 'Ban',
    mode: 'leader',
    steps: [
      {
        id: 'clean',
        beatKey: 'stories.blank.steps.clean',
        mode: 'leader',
        rule: 'plurality',
        moment: 'method',
        playground: { space: PLANE.space, electorate: REJET_COMPOSED },
        config: { candidates: REJET_CANDS, ...REJET_ELECTORATE },
      },
      {
        id: 'todayLaw',
        beatKey: 'stories.blank.steps.todayLaw',
        moment: 'strategy',
        playground: { blank: BLANK('france_today') },
      },
      {
        id: 'ifCounted',
        beatKey: 'stories.blank.steps.ifCounted',
        playground: { blank: BLANK('in_exprimes') },
      },
      {
        id: 'competitive',
        beatKey: 'stories.blank.steps.competitive',
        playground: { blank: BLANK('competitive') },
      },
    ],
  },

  {
    id: 'monotonie',
    titleKey: 'stories.monotonie.title',
    taglineKey: 'stories.monotonie.tagline',
    icon: 'TrendingUp',
    mode: 'leader',
    steps: [
      {
        id: 'avant',
        beatKey: 'stories.monotonie.steps.avant',
        mode: 'leader',
        rule: 'irv',
        moment: 'method',
        playground: { space: PLANE.space, electorate: MONO_BEFORE },
        config: { candidates: MONO_CANDS, ...MONO_ELECTORATE },
      },
      {
        id: 'apres',
        beatKey: 'stories.monotonie.steps.apres',
        rule: 'irv',
        playground: { electorate: MONO_AFTER },
        config: { candidates: MONO_CANDS, ...MONO_ELECTORATE },
      },
    ],
  },

  {
    id: 'renversement',
    titleKey: 'stories.renversement.title',
    taglineKey: 'stories.renversement.tagline',
    icon: 'Repeat',
    mode: 'leader',
    steps: [
      {
        id: 'avant',
        beatKey: 'stories.renversement.steps.avant',
        mode: 'leader',
        rule: 'plurality',
        moment: 'bilan',
        playground: { space: PLANE.space, electorate: REV_AVANT },
        config: { candidates: REV_CANDS, num_voters: 6000, seed: 55, ideology: 'random' },
      },
      {
        id: 'inverse',
        beatKey: 'stories.renversement.steps.inverse',
        rule: 'plurality',
        playground: { electorate: REV_INVERSE },
        config: { candidates: REV_CANDS, num_voters: 6000, seed: 55, ideology: 'random' },
      },
    ],
  },

  {
    id: 'soutien',
    titleKey: 'stories.soutien.title',
    taglineKey: 'stories.soutien.tagline',
    icon: 'ThumbsUp',
    mode: 'leader',
    steps: [
      {
        id: 'avant',
        beatKey: 'stories.soutien.steps.avant',
        mode: 'leader',
        rule: 'approval',
        moment: 'method',
        playground: { space: LINE('Gauche–Droite').space, electorate: LNH_AVANT },
        config: { candidates: LNH_CANDS, ...LNH_ELECTORATE },
      },
      {
        id: 'apres',
        beatKey: 'stories.soutien.steps.apres',
        rule: 'approval',
        playground: { electorate: LNH_APRES },
        config: { candidates: LNH_CANDS, ...LNH_ELECTORATE },
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
