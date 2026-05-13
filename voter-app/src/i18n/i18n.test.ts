import fr from './locales/fr';
import en from './locales/en';

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
    if (missing.length > 0) {
      throw new Error(`Missing en keys:\n${missing.join('\n')}`);
    }
  });

  test('all en keys exist in fr', () => {
    const missing = enKeys.filter((k) => !frKeys.includes(k));
    if (missing.length > 0) {
      throw new Error(`Missing fr keys:\n${missing.join('\n')}`);
    }
  });

  test('no empty string values in fr', () => {
    const empty = frKeys.filter((k) => {
      const parts = k.split('.');
      let val: unknown = fr;
      for (const p of parts) val = (val as Record<string, unknown>)[p];
      return val === '';
    });
    if (empty.length > 0) {
      throw new Error(`Empty fr values:\n${empty.join('\n')}`);
    }
  });

  test('no empty string values in en', () => {
    const empty = enKeys.filter((k) => {
      const parts = k.split('.');
      let val: unknown = en;
      for (const p of parts) val = (val as Record<string, unknown>)[p];
      return val === '';
    });
    if (empty.length > 0) {
      throw new Error(`Empty en values:\n${empty.join('\n')}`);
    }
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

    if (mismatches.length > 0) {
      throw new Error(`Interpolation placeholder mismatches:\n${mismatches.join('\n')}`);
    }
  });
});
