// labSearch — the Laboratoire's search box: which fiches match what was typed. Accents and case do
// not matter ("electorat" finds "Électorat"), and every word typed must be found (order free), so
// "vote blanc" and "blanc vote" are the same question.

/** Lower-cased, with the accents taken off and the ligatures spelt out ("œuvre" is "oeuvre"). */
export const fold = (s: string): string =>
  s
    .normalize('NFD')
    .replace(/\p{M}/gu, '')
    .toLowerCase()
    .replace(/œ/g, 'oe')
    .replace(/æ/g, 'ae')
    .replace(/ß/g, 'ss');

const wordsOf = (query: string): string[] => fold(query).split(/\s+/).filter(Boolean);

/** Whether `query` holds anything to look for: a lone accent or a blank is not a search. */
export const hasWords = (query: string): boolean => wordsOf(query).length > 0;

/** Whether every word of `query` appears in `haystack`; an empty query matches everything. */
export function matchesQuery(haystack: string, query: string): boolean {
  const text = fold(haystack);
  return wordsOf(query).every((w) => text.includes(w));
}
