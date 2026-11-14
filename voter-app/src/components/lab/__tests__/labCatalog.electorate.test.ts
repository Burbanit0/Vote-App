import { describe, it, expect } from 'vitest';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { ALL_EXPERIMENTS, READS_ELECTORATE } from '../labCatalog';

// "Compare an electorate" swaps ONE thing under a fiche: the voters the playground draws from its
// communities (`playground.electorate`); the candidates, the voter count, the ideology preset and
// the seed stay. So the comparison means something only on a fiche whose result depends on that
// composition, and the catalogue says which (`readsElectorate`): a fiche without the flag gets no
// Compare button, because its second column would be the first one again.
//
// The flag is data, so it could drift from the code: a fiche that starts reading the composed
// electorate and is not flagged would silently lose its comparison. This test reads the catalogue
// and every fiche's source (following its imports) and fails when the flag and the code disagree.

const SRC = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');
const CATALOG = path.join(SRC, 'components/lab/labCatalog.tsx');
const catalog = readFileSync(CATALOG, 'utf8');

function baseOf(from: string, spec: string): string | null {
  if (spec.startsWith('@/')) return path.join(SRC, spec.slice(2));
  if (spec.startsWith('.')) return path.resolve(path.dirname(from), spec);
  return null;
}

function resolveImport(from: string, spec: string): string | null {
  const base = baseOf(from, spec);
  if (base === null) return null;
  for (const tail of ['.tsx', '.ts', '/index.tsx', '/index.ts']) {
    if (existsSync(base + tail)) return base + tail;
  }
  return null;
}

// Static `import … from '…'` / `export … from '…'`, and dynamic `import('…')`: two small patterns.
const FROM = /(?:import|export)\s[^;]*?from\s*['"]([^'"]+)['"]/gs;
const DYNAMIC = /import\(\s*['"]([^'"]+)['"]\s*\)/g;

/** Every module specifier a source text imports. */
const specifiersOf = (text: string): string[] =>
  [...text.matchAll(FROM), ...text.matchAll(DYNAMIC)].map((m) => m[1]);

/** `file` and every source file it imports, transitively (tests excluded). */
function closure(file: string, seen = new Set<string>()): Set<string> {
  if (seen.has(file)) return seen;
  seen.add(file);
  for (const spec of specifiersOf(readFileSync(file, 'utf8'))) {
    const next = resolveImport(file, spec);
    if (next && !/\.test\.tsx?$/.test(next)) closure(next, seen);
  }
  return seen;
}

// What the composed electorate comes in through: the voters the playground draws (its contexts),
// the playground state's `electorate`, or the request built from it.
const READS = [
  /usePlayground\(\)/,
  /\.electorate\b/,
  /use(?:Instrument|Store|Journey|Scorecard|Playground)Ctx\(/,
  /useMethodSelection\(/,
  /votingVoters|sampleAtSeed/,
];
// The store defines the hooks, and the persistence guard checks what the store reads back from
// localStorage (it names the `electorate` slice to validate it, it draws nobody); the ui kit is
// chrome: none is a reader.
const SKIPPED = [/stores\/useElectionStore\.tsx$/, /lib\/persistedState\.ts$/, /components\/ui\//];
const withoutImports = (text: string) => text.replace(/^import .*$/gm, '');

const reads = (texts: string[]) => texts.some((t) => READS.some((r) => r.test(withoutImports(t))));

// The lazy panels of the catalogue, by the name it gives them.
const panels = new Map<string, string>();
for (const m of catalog.matchAll(
  /const (\w+) = lazyWithPreload\(\s*\(\) => import\('([^']+)'\)/g
)) {
  const file = resolveImport(CATALOG, m[2]);
  if (file) panels.set(m[1], file);
}

/** The source texts a fiche's body is made of: its panel's closure, plus the wrapper's own lines. */
function textsOf(body: string): string[] {
  const files = new Set<string>();
  const own: string[] = [];
  const panel = panels.get(body);
  if (panel) closure(panel, files);
  else {
    // A wrapper body declared in the catalogue: its own lines, and the panel it renders.
    const decl = new RegExp(`const ${body}\\b[\\s\\S]*?(?=\\nconst |\\n// ──)`).exec(catalog)?.[0];
    expect(decl, `wrapper ${body} not found in the catalogue`).toBeTruthy();
    own.push(decl!);
    for (const m of decl!.matchAll(/<(\w+)/g)) {
      const p = panels.get(m[1]);
      if (p) closure(p, files);
    }
  }
  const read = [...files]
    .filter((f) => !SKIPPED.some((s) => s.test(f)))
    .map((f) => readFileSync(f, 'utf8'));
  return [...own, ...read];
}

// id -> body name, as the catalogue declares them: exp('id', 'title.key', Body …)
const bodyOf = new Map<string, string>();
for (const m of catalog.matchAll(/exp\(\s*'([\w-]+)',\s*'[^']+',\s*(\w+)/g)) bodyOf.set(m[1], m[2]);

describe('readsElectorate matches what each fiche reads', () => {
  it('has a source to read for every fiche (the scan covers the whole catalogue)', () => {
    expect([...bodyOf.keys()].sort()).toEqual(ALL_EXPERIMENTS.map((e) => e.id).sort());
  });

  it('flags exactly the fiches whose code reads the composed electorate', () => {
    const scanned = [...bodyOf]
      .filter(([, body]) => reads(textsOf(body)))
      .map(([id]) => id)
      .sort();
    const flagged = ALL_EXPERIMENTS.filter((e) => e.readsElectorate)
      .map((e) => e.id)
      .sort();
    expect(flagged).toEqual(scanned);
  });

  it('names only fiches that exist (a typo in the set would flag nothing)', () => {
    const known = new Set(ALL_EXPERIMENTS.map((e) => e.id));
    expect([...READS_ELECTORATE].filter((id) => !known.has(id))).toEqual([]);
  });

  it('is a minority: most fiches run on the candidates and the ideology preset alone', () => {
    const n = ALL_EXPERIMENTS.filter((e) => e.readsElectorate).length;
    expect(n).toBeGreaterThan(0);
    expect(n).toBeLessThan(ALL_EXPERIMENTS.length / 2);
  });
});
