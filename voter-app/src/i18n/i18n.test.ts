import fr from './locales/fr';
import en from './locales/en';
import polityFr from './locales/polity.fr';
import polityEn from './locales/polity.en';

// Recursively collect all leaf key paths from a nested object
function collectKeys(obj: Record<string, unknown>, prefix = ''): string[] {
  const keys: string[] = [];
  for (const [k, v] of Object.entries(obj)) {
    const path = prefix ? `${prefix}.${k}` : k;
    if (v !== null && typeof v === 'object' && !Array.isArray(v)) {
      keys.push(...collectKeys(v as Record<string, unknown>, path));
    } else {
      keys.push(path);
    }
  }
  return keys;
}

const frKeys = collectKeys(fr as unknown as Record<string, unknown>);
const enKeys = collectKeys(en as unknown as Record<string, unknown>);

describe('i18n parity', () => {
  test('all fr keys exist in en', () => {
    const missing = frKeys.filter((k) => !enKeys.includes(k));
    expect(missing).toEqual([]);
  });

  test('all en keys exist in fr', () => {
    const missing = enKeys.filter((k) => !frKeys.includes(k));
    expect(missing).toEqual([]);
  });

  test('no empty string values in fr', () => {
    const empty = frKeys.filter((k) => {
      const parts = k.split('.');
      let val: unknown = fr;
      for (const p of parts) val = (val as Record<string, unknown>)[p];
      return val === '';
    });
    expect(empty).toEqual([]);
  });

  test('no empty string values in en', () => {
    const empty = enKeys.filter((k) => {
      const parts = k.split('.');
      let val: unknown = en;
      for (const p of parts) val = (val as Record<string, unknown>)[p];
      return val === '';
    });
    expect(empty).toEqual([]);
  });

  test('interpolation placeholders match between fr and en', () => {
    const interpolationRegex = /\{\{(\w+)\}\}/g;
    const mismatches: string[] = [];

    for (const key of frKeys) {
      const parts = key.split('.');
      let frVal: unknown = fr;
      let enVal: unknown = en;
      for (const p of parts) {
        frVal = (frVal as Record<string, unknown>)[p];
        enVal = (enVal as Record<string, unknown>)[p];
      }
      if (typeof frVal !== 'string' || typeof enVal !== 'string') continue;

      const frPlaceholders = [...frVal.matchAll(interpolationRegex)].map((m) => m[1]).sort();
      const enPlaceholders = [...enVal.matchAll(interpolationRegex)].map((m) => m[1]).sort();

      if (JSON.stringify(frPlaceholders) !== JSON.stringify(enPlaceholders)) {
        mismatches.push(`${key}: fr=[${frPlaceholders}] en=[${enPlaceholders}]`);
      }
    }

    expect(mismatches).toEqual([]);
  });
});

// The polity namespace's key parity is enforced by tsc (polity.en.ts is typed on
// polity.fr.ts); what tsc cannot see is an empty string or a placeholder that one
// language dropped.
describe('polity namespace', () => {
  const leaves = (obj: Record<string, unknown>): [string, string][] =>
    collectKeys(obj).map((key) => [
      key,
      key.split('.').reduce<unknown>((v, p) => (v as Record<string, unknown>)[p], obj) as string,
    ]);
  const placeholders = (text: string) =>
    [...text.matchAll(/\{\{(\w+)\}\}/g)].map((m) => m[1]).sort();

  test('no empty strings and the same placeholders in fr and en', () => {
    const fr = new Map(leaves(polityFr as unknown as Record<string, unknown>));
    const en = new Map(leaves(polityEn as unknown as Record<string, unknown>));
    expect([...fr.values(), ...en.values()].filter((v) => v === '')).toEqual([]);
    expect(
      [...fr.keys()].filter(
        (k) => placeholders(fr.get(k)!).join() !== placeholders(en.get(k) ?? '').join()
      )
    ).toEqual([]);
  });
});
