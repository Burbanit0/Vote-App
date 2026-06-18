// scenarioInfo — pedagogical content for the playground's synthetic starting
// points (the "Point de départ" presets). Consumed by <ScenarioInfo>: a ⓘ next
// to each preset button reveals what the scenario is, the lesson it sets up, and
// what to watch once it's loaded. Keyed by PLAYGROUND_PRESETS id.

export interface ScenarioCopy {
  name: string;
  /** What this electorate/field actually is. */
  what: string;
  /** The phenomenon or lesson it is built to surface. */
  demonstrates: string;
  /** What to do / watch once it's loaded. */
  watch: string;
}

export interface ScenarioEntry {
  fr: ScenarioCopy;
  en: ScenarioCopy;
}

export const SCENARIO_INFO: Record<string, ScenarioEntry> = {
  two_party: {
    fr: {
      name: 'Bipartisme',
      what: 'Deux camps répartis sur un seul axe gauche–droite, électorat unimodal.',
      demonstrates:
        'Le théorème de l’électeur médian : presque toutes les méthodes convergent vers le centre.',
      watch: 'Basculez de méthode : le vainqueur bouge peu — l’accord inter-méthodes est élevé.',
    },
    en: {
      name: 'Two-party',
      what: 'Two camps on a single left–right axis, a unimodal electorate.',
      demonstrates: 'The median-voter theorem: almost every method converges on the centre.',
      watch: 'Switch methods: the winner barely moves — inter-method agreement is high.',
    },
  },
  fragmented: {
    fr: {
      name: 'Multipartisme fragmenté',
      what: 'Six partis répartis en 2D, sans majorité naturelle.',
      demonstrates:
        'L’effet des seuils, de la règle d’apportionnement et la nécessité de coalitions.',
      watch: 'Passez en mode Parlement : comparez PR / FPTP / MMP et la taille des coalitions.',
    },
    en: {
      name: 'Fragmented multi-party',
      what: 'Six parties spread in 2-D, with no natural majority.',
      demonstrates:
        'The impact of thresholds, the apportionment rule, and the need for coalitions.',
      watch: 'Switch to Parliament mode: compare PR / FPTP / MMP and coalition sizes.',
    },
  },
  single_issue: {
    fr: {
      name: 'Enjeu unique',
      what: 'Trois options sur un seul axe (1D) — un référendum à plusieurs choix.',
      demonstrates:
        'La clarté du votant médian quand les préférences sont à pic unique (single-peaked).',
      watch: 'Le vainqueur de Condorcet existe presque toujours ici : le taux de cycle reste bas.',
    },
    en: {
      name: 'Single issue',
      what: 'Three options on one axis (1-D) — a multi-choice referendum.',
      demonstrates: 'The clarity of the median voter when preferences are single-peaked.',
      watch: 'A Condorcet winner almost always exists here: the cycle rate stays low.',
    },
  },
  france2002_like: {
    fr: {
      name: 'France 2002 (synthétique)',
      what: 'Gauche fragmentée face à des extrêmes polarisés, sur le modèle de la présidentielle 2002.',
      demonstrates:
        'L’effet « spoiler » et l’échec de la pluralité / des deux tours à élire le vainqueur de Condorcet.',
      watch:
        'Comparez pluralité et Condorcet : un centriste battu au 1er tour peut gagner tous les duels.',
    },
    en: {
      name: 'France 2002 (synthetic)',
      what: 'A fragmented left against polarised extremes, modelled on the 2002 presidential race.',
      demonstrates:
        'The spoiler effect and how plurality / two-round can miss the Condorcet winner.',
      watch:
        'Compare plurality and Condorcet: a centrist knocked out in round 1 may win every duel.',
    },
  },
};

export type ScenarioLang = 'fr' | 'en';

export function getScenarioInfo(id: string): ScenarioEntry | null {
  return SCENARIO_INFO[id] ?? null;
}
