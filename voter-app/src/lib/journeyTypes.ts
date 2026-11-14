/**
 * Where the visitor is in the playground, as plain values: the moment of the journey and the
 * lens of the central map. They live here, apart from the components that name them, so the
 * modules that read or write them (the scenario link) need not import a component.
 */
export const MOMENT_IDS = ['electorate', 'method', 'strategy', 'campaign', 'bilan'] as const;
export type MomentId = (typeof MOMENT_IDS)[number];

export const LENSES = ['winner', 'manipulation', 'probability', 'criteria'] as const;
export type Lens = (typeof LENSES)[number];
