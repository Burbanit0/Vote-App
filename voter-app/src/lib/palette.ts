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

// ── Laboratoire panels ───────────────────────────────────────────────────────
//
// The fiches predate CANDIDATE_PALETTE and carry their own, darker set. Fifteen
// of them had a byte-identical `candColor(name, names)` copied in, over four
// palettes that all start `#005CAB #C8590A #007A33` and then disagree. The
// lookup is shared below; the palettes are kept apart on purpose, because
// merging them would change which colour a candidate gets — a visual decision,
// not a refactor. Naming them here at least makes the divergence visible.
//
// They are NOT CANDIDATE_PALETTE: these are tuned for the fiches' light cards,
// and unifying the two is the same open visual question, one level up.

/** Six colours. The most common fiche set (8 panels). */
export const LAB_PALETTE: string[] = [
  '#005CAB', // blue
  '#C8590A', // orange
  '#007A33', // green
  '#6c757d', // grey
  '#9b59b6', // purple
  '#e67e22', // amber
];

/** LAB_PALETTE plus two, for panels that can show more than six (STV, multiwinner). */
export const LAB_PALETTE_WIDE: string[] = [...LAB_PALETTE, '#2A9D8F', '#E76F51'];

/** Six, but no grey and ending pink. Differs from LAB_PALETTE from index 3 on. */
export const LAB_PALETTE_PINK: string[] = [
  '#005CAB',
  '#C8590A',
  '#007A33',
  '#9b59b6',
  '#e67e22',
  '#e83e8c',
];

/** LAB_PALETTE_PINK without the pink — five colours (deliberation). */
export const LAB_PALETTE_FIVE: string[] = LAB_PALETTE_PINK.slice(0, 5);

/**
 * Colour for `name`, by its position in `names`.
 *
 * `#888` when the name is absent: `indexOf` returns -1, and `-1 % n` is -1 in
 * JS, so the lookup would be `undefined` rather than wrapping to the last
 * entry. Every copy of this had the same fallback; it is load-bearing.
 */
export const colorByName = (name: string, names: string[], palette: string[]): string =>
  palette[names.indexOf(name) % palette.length] ?? '#888';
