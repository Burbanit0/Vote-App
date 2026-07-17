import { describe, it, expect } from 'vitest';
import { LAB_FAMILIES, ALL_EXPERIMENTS, locateExperiment, DEFAULT_EXPERIMENT } from '../labCatalog';
import pgFr from '../../../i18n/locales/playground.fr';
import pgEn from '../../../i18n/locales/playground.en';

// The redesign's honesty gate: the old Laboratoire held 48 anchor leaves, the
// strategy panel's five modules, ballot, values, the methods matrix and the
// gallery. This test hardcodes every former leaf testid — if a fiche is dropped
// during any future reshuffle, the build fails instead of the content silently
// vanishing.

const FORMER_LEAVES = [
  // MechanismsAnchor
  'mech-jury',
  'mech-nota',
  'mech-liquid',
  'mech-sortition',
  'mech-deliberation',
  'mech-conviction',
  'mech-epistocracy',
  'mech-identity',
  // SystemsAnchor
  'sys-coalition',
  'sys-multiwinner',
  'sys-districts',
  'sys-gerrymander',
  'sys-stv',
  'sys-ballot',
  'sys-pipeline',
  // CampaignAnchor
  'dyn-hotelling',
  'dyn-campaign',
  'dyn-polarization',
  'dyn-party',
  // TemporalDynamicsAnchor
  'tdyn-adaptive',
  'tdyn-replay',
  'tdyn-primary',
  'tdyn-cascade',
  'tdyn-fatigue',
  // BehavioralRealismAnchor
  'breal-biases',
  'breal-shyvoter',
  'breal-overload',
  'breal-compulsory',
  'breal-demographic',
  'breal-affective',
  // TheoryAnchor
  'thy-sen',
  'thy-judgment',
  'thy-agenda',
  'thy-tyranny',
  'thy-apportionment',
  'thy-power',
  'thy-backsliding',
  'thy-intergen',
  'thy-polis',
  // AnalysisAnchor
  'ana-montecarlo',
  'ana-manipulability',
  'ana-manipulation',
  'ana-collective',
  'ana-assumptions',
  'ana-combined',
  // ResultsAnchor
  'res-table',
  'res-animation',
  'res-real-election',
];

const EXTRAS = [
  'lab-matrix',
  'lab-gallery',
  'lab-ballot',
  'lab-values',
  'strat-sincerity',
  'strat-vuln',
  'strat-equilibrium',
  'anchor-vse',
  'anchor-abstention',
];

const resolve = (bundle: Record<string, unknown>, dotted: string): unknown =>
  dotted.split('.').reduce<unknown>((o, k) => (o as Record<string, unknown>)?.[k], bundle);

describe('labCatalog — nothing was lost in the redesign', () => {
  it('carries every former anchor leaf, verbatim by id', () => {
    const ids = new Set(ALL_EXPERIMENTS.map((e) => e.id));
    for (const leaf of FORMER_LEAVES) expect(ids.has(leaf), leaf).toBe(true);
  });

  it('carries the split strategy panel, ballot, values, matrix and gallery', () => {
    const ids = new Set(ALL_EXPERIMENTS.map((e) => e.id));
    for (const id of EXTRAS) expect(ids.has(id), id).toBe(true);
  });

  it('is exactly the old inventory — 57 fiches, unique ids, nothing smuggled in or out', () => {
    expect(ALL_EXPERIMENTS).toHaveLength(FORMER_LEAVES.length + EXTRAS.length); // 57
    expect(new Set(ALL_EXPERIMENTS.map((e) => e.id)).size).toBe(ALL_EXPERIMENTS.length);
  });

  it('every title, subtitle and intro key resolves in FR and EN', () => {
    const keys: string[] = [];
    for (const f of LAB_FAMILIES) {
      keys.push(f.labelKey);
      for (const g of f.groups) {
        keys.push(g.titleKey);
        if (g.subtitleKey) keys.push(g.subtitleKey);
        if (g.introKey) keys.push(g.introKey);
        for (const e of g.experiments) keys.push(e.titleKey);
      }
    }
    for (const k of keys) {
      expect(resolve(pgFr, k), `FR missing ${k}`).toBeTypeOf('string');
      expect(resolve(pgEn, k), `EN missing ${k}`).toBeTypeOf('string');
    }
  });

  it('locateExperiment finds the default and returns family + group context', () => {
    const d = locateExperiment(DEFAULT_EXPERIMENT);
    expect(d?.family.id).toBe('methods');
    expect(locateExperiment('thy-sen')?.family.id).toBe('theory');
    expect(locateExperiment('nope')).toBeNull();
  });

  it('every experiment exposes a preload for hover-prefetch', () => {
    for (const e of ALL_EXPERIMENTS) expect(typeof e.preload, e.id).toBe('function');
  });
});
