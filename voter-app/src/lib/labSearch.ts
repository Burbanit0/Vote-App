// labSearch — the Laboratoire's search box: which fiches match what was typed. Accents and case do
// not matter ("electorat" finds "Électorat"), and every word typed must be found (order free), so
// "vote blanc" and "blanc vote" are the same question.

/** Lower-cased, with the accents taken off. */
export const fold = (s: string): string => s.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase();

/** Whether every word of `query` appears in `haystack`; an empty query matches everything. */
export function matchesQuery(haystack: string, query: string): boolean {
  const words = fold(query).split(/\s+/).filter(Boolean);
  const text = fold(haystack);
  return words.every((w) => text.includes(w));
}
