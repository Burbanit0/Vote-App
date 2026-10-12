import { readFileSync } from 'node:fs';
import { describe, it, expect } from 'vitest';
import { LEADER_RULES } from '../lib/scorecard';
import { ALL_EXPERIMENTS } from '../components/lab/labCatalog';
import fr from './locales/fr';
import en from './locales/en';

// The home page, the static meta tags and the PWA manifest state how many methods and
// fiches there are. They can't import the live lists (the home page is the eager
// bundle; index.html and the manifest are static), so they carry literals, and this
// test keeps every literal equal to the lists. They had drifted to 15, 17 and 47.
const read = (p: string) => readFileSync(new URL(p, import.meta.url), 'utf8');

describe('method and fiche counts shown to users', () => {
  const methods = LEADER_RULES.length;
  const fiches = ALL_EXPERIMENTS.length;

  it('the home page states the real counts', () => {
    expect(fr.home.reassure).toContain(`${methods} méthodes`);
    expect(en.home.reassure).toContain(`${methods} methods`);
    expect(fr.home.labLede).toContain(`${fiches} fiches`);
    expect(en.home.labLede).toContain(`${fiches} fiches`);
  });

  it('the meta tags and the PWA manifest state the real method count', () => {
    const counts = (s: string) =>
      [...s.matchAll(/(\d{1,4}) méthodes de vote/g)].map((m) => Number(m[1]));
    const html = counts(read('../../index.html'));
    const manifest = counts(read('../../vite.config.ts'));
    expect(html).toHaveLength(3);
    expect(manifest).toHaveLength(1);
    for (const n of [...html, ...manifest]) expect(n).toBe(methods);
  });
});
