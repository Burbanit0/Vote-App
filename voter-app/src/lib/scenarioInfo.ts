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

const SCENARIO_INFO: Record<string, ScenarioEntry> = {
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
  usa2000_like: {
    fr: {
      name: 'USA 2000 (synthétique)',
      what: 'Trois candidats sur un axe 1D : Nader (gauche) spoile Gore (centre-gauche) face à Bush (droite).',
      demonstrates:
        "L'effet spoiler : Nader prend des voix à Gore, Bush gagne en pluralité alors que Gore est le vainqueur de Condorcet.",
      watch:
        "Comparez Pluralité et Condorcet / IRV — le résultat s'inverse. Nader a-t-il « coûté » l'élection à Gore ?",
    },
    en: {
      name: 'USA 2000 (synthetic)',
      what: 'Three candidates on a 1D axis: Nader (left) spoils Gore (centre-left) against Bush (right).',
      demonstrates:
        'The spoiler effect: Nader draws votes from Gore, Bush wins plurality even though Gore is the Condorcet winner.',
      watch:
        'Compare Plurality vs Condorcet / IRV — the result flips. Did Nader "cost" Gore the election?',
    },
  },
  weimar1932_like: {
    fr: {
      name: 'Weimar 1932 (synthétique)',
      what: 'Cinq partis en 2D (économique × autoritaire) : deux extrêmes dominants (KPD, NSDAP) et un centre fragmenté (SPD, Zentrum, DNVP).',
      demonstrates:
        'Une PR sans seuil produit une assemblée où les extrêmes — qui ne peuvent pas gouverner ensemble — représentent la majorité.',
      watch:
        "Passez en mode Parlement, seuil à 0 % : aucune coalition stable sans l'un des extrêmes. Ajoutez un seuil à 5 % : le paysage change.",
    },
    en: {
      name: 'Weimar 1932 (synthetic)',
      what: 'Five parties in 2D (economic × authoritarian): two dominant extremes (KPD, NSDAP) and a fragmented centre (SPD, Zentrum, DNVP).',
      demonstrates:
        'A PR system with no threshold produces an assembly where the extremes — who cannot govern together — hold a majority.',
      watch:
        'Switch to Parliament mode, threshold at 0%: no stable coalition without an extreme. Add a 5% threshold: the landscape shifts.',
    },
  },
};

// Electorate-mixture presets (the "Modèles" in the Electorate Composer). Keyed
// by ELECTORATE_PRESETS id — a separate map because the ids overlap with the
// field presets above (e.g. `fragmented` means a different thing here).
const ELECTORATE_INFO: Record<string, ScenarioEntry> = {
  two_blocs: {
    fr: {
      name: 'Bipolaire',
      what: 'Deux communautés opposées sur l’axe gauche–droite, sans centre.',
      demonstrates: 'Le terrain le plus net du votant médian : un seul clivage structurant.',
      watch: 'Le taux de cycle reste quasi nul ; presque toutes les méthodes s’accordent.',
    },
    en: {
      name: 'Bipolar',
      what: 'Two opposed communities on the left–right axis, no centre.',
      demonstrates: 'The cleanest median-voter terrain: a single structuring cleavage.',
      watch: 'The cycle rate stays near zero; almost every method agrees.',
    },
  },
  three_poles: {
    fr: {
      name: 'Trois pôles',
      what: 'Trois blocs d’égale force, aucun majoritaire.',
      demonstrates: 'L’apparition de cycles de Condorcet et la nécessité de coalitions.',
      watch: 'Surveillez le taux de paradoxe : il grimpe dès que les trois pôles s’équilibrent.',
    },
    en: {
      name: 'Three poles',
      what: 'Three equally strong blocs, none a majority.',
      demonstrates: 'The emergence of Condorcet cycles and the need for coalitions.',
      watch: 'Watch the paradox rate: it climbs as the three poles balance out.',
    },
  },
  center_extremes: {
    fr: {
      name: 'Centre + extrêmes',
      what: 'Une masse centrale encadrée par deux extrêmes.',
      demonstrates: 'L’écrasement du centre (« centre squeeze ») et l’effet spoiler.',
      watch:
        'Comparez IRV et Condorcet : l’IRV peut écarter le centre malgré sa large acceptabilité.',
    },
    en: {
      name: 'Centre + extremes',
      what: 'A central mass flanked by two extremes.',
      demonstrates: 'The centre squeeze and the spoiler effect.',
      watch: 'Compare IRV and Condorcet: IRV can drop the centre despite broad acceptability.',
    },
  },
  fragmented: {
    fr: {
      name: 'Fragmenté (6)',
      what: 'Six communautés dispersées, électorat très divisé.',
      demonstrates: 'L’effet des seuils et de la règle d’apportionnement sur la fragmentation.',
      watch: 'En mode Parlement : comparez les indices de Gallagher et les voix gaspillées.',
    },
    en: {
      name: 'Fragmented (6)',
      what: 'Six scattered communities, a very divided electorate.',
      demonstrates: 'How thresholds and the apportionment rule act on fragmentation.',
      watch: 'In Parliament mode: compare Gallagher indices and wasted votes.',
    },
  },
  realistic: {
    fr: {
      name: 'Proche du réel',
      what: 'Mélange asymétrique calibré pour ressembler à un électorat réel.',
      demonstrates:
        'Que les conclusions « propres » des modèles jouets résistent mal au désordre réel.',
      watch: 'Secouez les hypothèses : les bandes de victoire deviennent moins tranchées.',
    },
    en: {
      name: 'Close to reality',
      what: 'An asymmetric mixture tuned to resemble a real electorate.',
      demonstrates: 'That the “clean” conclusions of toy models survive real-world noise poorly.',
      watch: 'Shake the assumptions: win-rate bands get fuzzier.',
    },
  },
  polarized: {
    fr: {
      name: 'Polarisé',
      what: 'Deux camps éloignés, centre quasi vide.',
      demonstrates: 'La polarisation affective et l’instabilité des résultats.',
      watch: 'Ouvrez « Polarisation affective » : la pénalité hors-camp déplace le vainqueur.',
    },
    en: {
      name: 'Polarised',
      what: 'Two distant camps, an almost empty centre.',
      demonstrates: 'Affective polarisation and result instability.',
      watch: 'Open “Affective polarisation”: the out-group penalty shifts the winner.',
    },
  },
  nordic: {
    fr: {
      name: 'Consensus nordique',
      what: 'Plusieurs blocs modérés qui se chevauchent largement.',
      demonstrates: 'Une démocratie consensuelle : proportionnelle, coalitions stables.',
      watch: 'Carte de Lijphart : ce modèle se place côté consensualiste.',
    },
    en: {
      name: 'Nordic consensus',
      what: 'Several moderate, broadly overlapping blocs.',
      demonstrates: 'A consensus democracy: proportional, stable coalitions.',
      watch: 'Lijphart map: this model sits on the consensual side.',
    },
  },
  cleavages_3d: {
    fr: {
      name: '3 clivages (3D)',
      what: 'Trois clivages quasi orthogonaux dans un espace à trois dimensions.',
      demonstrates:
        'Le chaos multidimensionnel (Plott/McKelvey) : plus de point d’équilibre stable.',
      watch: 'Le taux de cycle explose : aucun vainqueur de Condorcet ne tient.',
    },
    en: {
      name: '3 cleavages (3-D)',
      what: 'Three near-orthogonal cleavages in a three-dimensional space.',
      demonstrates: 'Multidimensional chaos (Plott/McKelvey): no stable equilibrium point.',
      watch: 'The cycle rate explodes: no Condorcet winner holds.',
    },
  },
};

export type ScenarioLang = 'fr' | 'en';
export type ScenarioKind = 'scenario' | 'electorate';

export function getScenarioInfo(id: string, kind: ScenarioKind = 'scenario'): ScenarioEntry | null {
  const map = kind === 'electorate' ? ELECTORATE_INFO : SCENARIO_INFO;
  return map[id] ?? null;
}
