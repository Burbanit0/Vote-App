import { pseudoizeString, pseudoizeTree } from './pseudoize';
import fr from './locales/fr';
import pseudo from './locales/pseudo';
import pgFr from './locales/playground.fr';
import pgPseudo from './locales/playground.pseudo';
import i18n, { loadLanguage } from './index';

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

  test('pseudoizes every string in an array leaf', () => {
    const result = pseudoizeTree(['a', 'b']);
    expect(result).toEqual([pseudoizeString('a'), pseudoizeString('b')]);
  });

  test('passes through a non-string, non-object leaf unchanged', () => {
    // Defensive branch: fr.ts/playground.fr.ts never contain these, but
    // pseudoizeTree is a shared, exported utility (also used by
    // scripts/gen-pseudo-locale.ts) typed over unknown input shapes.
    expect(pseudoizeTree(null)).toBeNull();
    expect(pseudoizeTree(42)).toBe(42);
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

// loadLanguage('pseudo') exercises the same lazy-load path as 'en' (already
// covered by setupTests.ts's global `await loadLanguage('en')`), but nothing
// else calls it with 'pseudo' — the app's own language switcher never offers
// it (see src/i18n/index.ts's comment on `lazyLoaders.pseudo`).
describe('loadLanguage("pseudo")', () => {
  test('registers both the translation and playground pseudo bundles', async () => {
    await loadLanguage('pseudo');
    expect(i18n.hasResourceBundle('pseudo', 'translation')).toBe(true);
    expect(i18n.hasResourceBundle('pseudo', 'playground')).toBe(true);
    expect(i18n.getResourceBundle('pseudo', 'translation').nav.simulator).toBe(
      pseudo.nav.simulator
    );
  });
});
