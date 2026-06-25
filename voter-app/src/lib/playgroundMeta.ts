// Playground metadata — labels + stated scorecard conventions, shared by the
// page shell, the moment panels and the Bilan readout so the selector, the
// scorecard title and the values lens stay in sync.

export const BALLOT_LABELS: Record<string, string> = {
  full: 'Information complète',
  choose_one: 'Choix unique (1 croix)',
  approve: 'Approbation',
  rank_full: 'Classement complet',
  rank_truncated: 'Classement tronqué (top-k)',
  score: 'Notes (échelle)',
  grade: 'Mentions (JM)',
  cumulative: 'Cumulatif (budget de points)',
};

export const LEADER_AXIS_META: { key: string; label: string; hint: string }[] = [
  {
    key: 'condorcet_efficiency',
    label: 'Efficacité Condorcet',
    hint: "Part des ré-échantillonnages (avec vainqueur de Condorcet) où la règle l'élit.",
  },
  {
    key: 'strategic_resistance',
    label: 'Résistance stratégique',
    hint: 'Le vainqueur survit-il à une compression stratégique vers les deux favoris ? (heuristique documentée)',
  },
  {
    key: 'welfare',
    label: 'Bien-être (regret)',
    hint: '1 − regret bayésien normalisé du vainqueur (utilité = −distance).',
  },
  {
    key: 'majority_satisfaction',
    label: 'Satisfaction majoritaire',
    hint: 'Part des électeurs pour qui le vainqueur vaut au moins leur candidat médian.',
  },
  {
    key: 'simplicity',
    label: 'Simplicité',
    hint: 'Convention déclarée : complexité du bulletin et du dépouillement (sans bande).',
  },
  {
    key: 'stability',
    label: 'Stabilité',
    hint: 'Part des ré-échantillonnages élisant le vainqueur modal.',
  },
];

export const PARLIAMENT_AXIS_META: { key: string; label: string; hint: string }[] = [
  {
    key: 'proportionality',
    label: 'Proportionnalité',
    hint: '1 − indice de Gallagher (normalisé).',
  },
  {
    key: 'pluralism',
    label: 'Pluralisme (diversité)',
    hint: 'Part de la diversité des voix (NEP) qui survit en sièges.',
  },
  {
    key: 'effective_votes',
    label: 'Voix utiles',
    hint: '1 − part des voix gaspillées.',
  },
  {
    key: 'minority_representation',
    label: 'Représentation des minorités',
    hint: 'Partis ≥ 3 % des voix détenant au moins un siège.',
  },
  {
    key: 'governability',
    label: 'Gouvernabilité',
    hint: '1 / taille de la plus petite coalition majoritaire.',
  },
  {
    key: 'gerrymander_resistance',
    label: 'Résistance au charcutage',
    hint: 'Stabilité des sièges quand la carte des circonscriptions change (re-découpage x→y).',
  },
];

export const PARLIAMENT_AXES_KEYS = PARLIAMENT_AXIS_META.map((a) => a.key);

export const STRUCTURE_LABELS: Record<string, string> = {
  pr: 'Proportionnelle (listes)',
  fptp: 'Circonscriptions (FPTP)',
  mmp: 'Mixte (MMP)',
};

export const defaultWeights = (keys: readonly string[]): Record<string, number> =>
  Object.fromEntries(keys.map((k) => [k, 0.5]));
