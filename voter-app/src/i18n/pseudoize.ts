// Pseudo-localization: transforms a translation tree's strings into a
// synthetic "pseudo" locale that's accented and ~35% longer than the source.
// Layout bugs (truncation, overflow, wrapping) show up against THIS before a
// real second language or a future one exposes them for real — the whole
// point is to break things early and on purpose (Lot 7,
// PLAN_SOLIDITE_TECHNIQUE.md). Shared by scripts/gen-pseudo-locale.ts (which
// writes the checked-in `pseudo.ts`/`playground.pseudo.ts` files) and
// pseudoize.test.ts (which re-derives the tree in-memory and diffs it
// against those checked-in files to catch drift after `fr.ts` edits).

const ACCENTS: Record<string, string> = {
  a: 'á',
  e: 'é',
  i: 'í',
  o: 'ó',
  u: 'ú',
  A: 'Á',
  E: 'É',
  I: 'Í',
  O: 'Ó',
  U: 'Ú',
  n: 'ñ',
  c: 'ç',
};

function accentize(segment: string): string {
  return [...segment].map((ch) => ACCENTS[ch] ?? ch).join('');
}

// Padding character repeated to simulate a ~35% longer language (German,
// Finnish, ... routinely run 30-40% longer than English/French for the same
// meaning) — visually distinct from real text so it can't be mistaken for it.
function padFor(segment: string): string {
  const len = Math.ceil(segment.length * 0.35);
  return len > 0 ? '~'.repeat(len) : '';
}

/**
 * Pseudoize a single translation string. Keeps `{{interpolation}}` tokens
 * byte-for-byte (i18next must still find them at runtime); wraps the whole
 * result in brackets so truncation/clipping is visible at a glance, and so
 * e2e tests can wait for the pseudo bundle to actually be active by
 * asserting the bracket character is on the page.
 */
export function pseudoizeString(value: string): string {
  if (value === '') return value;
  const parts = value.split(/(\{\{[^}]+\}\})/g);
  const body = parts
    .map((part) => (part.startsWith('{{') ? part : `${accentize(part)}${padFor(part)}`))
    .join('');
  return `⟦${body}⟧`;
}

/** Recursively pseudoize every string leaf of a translation tree, preserving its shape. */
export function pseudoizeTree<T>(tree: T): T {
  if (typeof tree === 'string') {
    return pseudoizeString(tree) as unknown as T;
  }
  if (Array.isArray(tree)) {
    return tree.map((item) => pseudoizeTree(item)) as unknown as T;
  }
  if (tree !== null && typeof tree === 'object') {
    const out: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(tree as Record<string, unknown>)) {
      out[key] = pseudoizeTree(value);
    }
    return out as T;
  }
  return tree;
}
