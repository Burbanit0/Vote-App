// campaignScenarios.ts — the perturbation models that drive the /campagne
// instrument. Each is a pure, deterministic, client-side `DriftFn` so the
// central graphs (map + trajectory) move instantly when you pick a scenario or
// scrub the timeline — the same role the rule selector plays in the playground.
//
// All three operate on candidate positions (they feed the shared metrics in
// campaignTimeline.ts). Heavier, backend-computed phenomena (cascade, fatigue,
// adaptive…) stay in the page's "Explorations approfondies" drawer; a new
// graph-driving scenario is just one more entry here.

import { driftCandidates } from './playgroundDynamics';
import { makeBestResponseDrift, type BestResponseCtx } from './candidateDynamics';
import type { DriftFn } from './campaignTimeline';
import type { NamedPt, Pt } from './playgroundVoting';

// Convergence (Hotelling–Downs): vote-seekers move toward the median voter.
const hotelling: DriftFn = (base, target, t, s) =>
  t > 0 ? driftCandidates(base, target, t, s) : base;

// Divergence: candidates harden, moving AWAY from the median toward their own side.
const harden: DriftFn = (base, target, t, s) =>
  base.map((c) => ({
    name: c.name,
    x: c.x + (c.x - target.x) * t * s,
    y: c.y + (c.y - (target.y ?? 0)) * t * s,
    z: (c.z ?? 0) + ((c.z ?? 0) - (target.z ?? 0)) * t * s,
  }));

// Polls: convergence perturbed by volatility that peaks mid-campaign and settles
// by election day. Deterministic per-candidate offset (golden-angle), so the
// motion is reproducible — not random noise that flickers on every render.
const GOLDEN = 2.399963229728653;
const polls: DriftFn = (base, target, t, s) => {
  const wobble = Math.sin(t * Math.PI) * 0.12 * s; // 0 at J0 and J-end, max at mid
  return hotelling(base, target, t, s).map((c, i) => ({
    name: c.name,
    x: c.x + Math.cos(i * GOLDEN) * wobble,
    y: (c.y ?? 0) + Math.sin(i * GOLDEN) * wobble,
    z: c.z,
  }));
};

export interface CampaignScenario {
  id: string;
  label: string;
  blurb: string;
  /** A static, rule-independent script: position is a closed form of `t`. */
  drift?: DriftFn;
  /** Scenarios whose motion depends on the ELECTORATE and the RULE build their
   *  DriftFn once per (electorate, rule, strength) — see makeBestResponseDrift.
   *  Takes precedence over `drift`. */
  makeDrift?: (ctx: BestResponseCtx) => DriftFn;
}

export const CAMPAIGN_SCENARIOS: CampaignScenario[] = [
  {
    id: 'derive',
    label: 'Dérive (Hotelling)',
    blurb: 'Les candidats convergent vers l’électeur médian.',
    drift: hotelling,
  },
  {
    id: 'sondages',
    label: 'Sondages',
    blurb: 'Convergence perturbée par la volatilité des sondages (pic à mi-campagne).',
    drift: polls,
  },
  {
    id: 'durcissement',
    label: 'Durcissement',
    blurb: 'Les candidats radicalisent leurs positions (s’éloignent du médian).',
    drift: harden,
  },
  {
    // The Downsian game rather than a script: each candidate hill-climbs to its
    // own best position GIVEN the rule, so the equilibrium changes when the rule
    // does. (Hotelling 1929, Downs 1957; Myerson–Weber 1993 for the rule effect.)
    id: 'meilleure_reponse',
    label: 'Meilleure réponse (Downs)',
    blurb: 'Chaque candidat se déplace là où il maximise son score — sous LA règle choisie.',
    makeDrift: makeBestResponseDrift,
  },
];

/** Resolve a scenario's drift, building the rule-dependent ones on demand. */
export function driftOf(scenario: CampaignScenario, ctx: BestResponseCtx): DriftFn | undefined {
  return scenario.makeDrift ? scenario.makeDrift(ctx) : scenario.drift;
}

export const DEFAULT_SCENARIO = CAMPAIGN_SCENARIOS[0];

// ── tiny self-check (ponytail: the money path) ──
// At J0 every scenario returns the base positions; by J-end derive pulls inward
// and harden pushes outward.
export function __selfCheck(): boolean {
  const base: NamedPt[] = [{ name: 'A', x: 0.8, y: 0 }];
  const target: Pt = { x: 0, y: 0, z: 0 };
  // Rule-dependent scenarios need a context to build; a two-voter stub is enough
  // to assert the J0 identity that every scenario must honour.
  const ctx: BestResponseCtx = {
    voters: [
      { x: 0, y: 0, z: 0 },
      { x: 0.2, y: 0, z: 0 },
    ],
    candidates: base,
    rule: 'plurality',
    dims: 2,
    strength: 0.6,
  };
  const at0 = CAMPAIGN_SCENARIOS.every((sc) => {
    const d = driftOf(sc, ctx);
    return !!d && Math.abs(d(base, target, 0, 0.6)[0].x - 0.8) < 1e-9;
  });
  const inward = hotelling(base, target, 1, 0.6)[0].x < 0.8;
  const outward = harden(base, target, 1, 0.6)[0].x > 0.8;
  return at0 && inward && outward;
}
