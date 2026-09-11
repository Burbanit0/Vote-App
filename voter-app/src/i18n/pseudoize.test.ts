import { pseudoizeString, pseudoizeTree } from './pseudoize';
import fr from './locales/fr';
import pseudo from './locales/pseudo';
import pgFr from './locales/playground.fr';
import pgPseudo from './locales/playground.pseudo';

describe('pseudoizeString', () => {
  test('wraps the result in brackets', () => {
    expect(pseudoizeString('Bonjour')).toMatch(/^⟦.*⟧$/);
  });

  test('accents vowels and pads for length', () => {
    const result = pseudoizeString('vote');
    expect(result).toContain('v');
    expect(result).toContain('ó'); // the accented 'o'
    expect(result.length).toBeGreaterThan('⟦vote⟧'.length);
  });

  test('keeps interpolation placeholders byte-for-byte', () => {
    const result = pseudoizeString('{{count}} voix sur {{total}}');
    expect(result).toContain('{{count}}');
    expect(result).toContain('{{total}}');
  });

  test('leaves an empty string empty', () => {
    expect(pseudoizeString('')).toBe('');
  });
});

describe('pseudoizeTree', () => {
  test('preserves nested object shape', () => {
    const tree = { a: 'x', b: { c: 'y' } };
    const result = pseudoizeTree(tree);
    expect(Object.keys(result)).toEqual(['a', 'b']);
    expect(Object.keys(result.b)).toEqual(['c']);
  });
});

// Drift check: `pseudo.ts` / `playground.pseudo.ts` are generated artifacts
// (see scripts/gen-pseudo-locale.ts's header) — this fails loudly if `fr.ts`
// / `playground.fr.ts` changed without re-running the generator, the same
// role i18n.test.ts's fr/en parity tests play for the hand-maintained
// locales.
describe('pseudo-locale is in sync with fr.ts', () => {
  test('translation namespace matches what regenerating now would produce', () => {
    expect(pseudo).toEqual(pseudoizeTree(fr));
  });

  test('playground namespace matches what regenerating now would produce', () => {
    expect(pgPseudo).toEqual(pseudoizeTree(pgFr));
  });
});
