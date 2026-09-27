// Playground metadata — labels + stated scorecard conventions, shared by the
// page shell, the moment panels and the Bilan readout so the selector, the
// scorecard title and the values lens stay in sync.

const PARLIAMENT_AXIS_META: { key: string; label: string; hint: string }[] = [
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

export const defaultWeights = (keys: readonly string[]): Record<string, number> =>
  Object.fromEntries(keys.map((k) => [k, 0.5]));
