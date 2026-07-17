// palette.ts — one candidate identity, everywhere.
//
// A candidate's colour is identity: the blue dot you dragged on the map must
// still be the blue line on the campaign trajectory and the blue slice in the
// bilan. Before this file, `const PALETTE = [...]` was copy-pasted into eight
// components with FOUR different sets of hex codes, so the same candidate changed
// colour as you moved between surfaces — index 0 was #2563eb on the map, #4e79a7
// on the campaign timeline, #005CAB in the Lab panels and #60a5fa in the composer.
//
// The canonical set is the one the central map already used: it is the app's
// signature surface, so keeping it means the instrument people know does not
// shift under them — only the surfaces that disagreed with it move.
//
// Colours are deliberately fixed hex, not theme tokens: they encode *data*
// (which candidate), not chrome, so they must stay stable across light/dark.
// These sit at roughly the Tailwind-600 level, which keeps contrast acceptable
// on both the light card and the dark "ink lab" background.

// Mutable string[] on purpose: consumers pass it straight into props typed as
// string[] (e.g. the 3-D scene's per-candidate colours).
export const CANDIDATE_PALETTE: string[] = [
  '#2563eb', // blue
  '#dc2626', // red
  '#16a34a', // green
  '#9333ea', // purple
  '#ea580c', // orange
  '#0891b2', // cyan
  '#ca8a04', // amber
  '#db2777', // pink
];

/** A hypothetical entrant (win-region probe) — deliberately outside the set. */
export const ENTRY_COLOR = '#fbbf24';

/** Stable colour for candidate `i`; wraps for fields larger than the palette. */
export const candidateColor = (i: number): string =>
  CANDIDATE_PALETTE[
    ((i % CANDIDATE_PALETTE.length) + CANDIDATE_PALETTE.length) % CANDIDATE_PALETTE.length
  ];

/** Colour for a candidate looked up by name, or a neutral grey when unknown. */
export const candidateColorByName = (name: string | null, names: string[]): string => {
  if (!name) return '#9ca3af';
  const i = names.indexOf(name);
  return i >= 0 ? candidateColor(i) : '#9ca3af';
};
