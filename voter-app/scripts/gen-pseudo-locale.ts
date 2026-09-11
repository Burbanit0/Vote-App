#!/usr/bin/env npx jiti
/**
 * gen-pseudo-locale.ts — regenerate the checked-in pseudo-locale files from
 * the real `fr.ts` / `playground.fr.ts` source of truth.
 *
 * `pseudo.ts` / `playground.pseudo.ts` are GENERATED ARTIFACTS (same status
 * as `src/api/types.gen.ts`) — never hand-edit them. `src/i18n/
 * pseudoize.test.ts` re-derives the tree in-memory and fails if it no longer
 * matches what's checked in, so this needs re-running whenever `fr.ts` or
 * `playground.fr.ts` changes.
 *
 * Usage: npm run gen:pseudo-locale
 * (jiti runs this .ts file directly — no separate build step needed.)
 */
import { writeFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import fr from '../src/i18n/locales/fr';
import pgFr from '../src/i18n/locales/playground.fr';
import { pseudoizeTree } from '../src/i18n/pseudoize';

function serialize(node: unknown, indent = 0): string {
  const pad = '  '.repeat(indent);
  const padIn = '  '.repeat(indent + 1);
  if (typeof node === 'string') return JSON.stringify(node);
  if (Array.isArray(node)) {
    return `[${node.map((v) => serialize(v, indent + 1)).join(', ')}]`;
  }
  if (node !== null && typeof node === 'object') {
    const entries = Object.entries(node as Record<string, unknown>)
      .map(([k, v]) => {
        const key = /^[A-Za-z_$][\w$]*$/.test(k) ? k : JSON.stringify(k);
        return `${padIn}${key}: ${serialize(v, indent + 1)},`;
      })
      .join('\n');
    return `{\n${entries}\n${pad}}`;
  }
  return JSON.stringify(node);
}

function generate(
  data: unknown,
  outPath: string,
  typeName: string,
  typeSourceModule: string,
  varName: string
): void {
  const pseudo = pseudoizeTree(data);
  const header = [
    '// GENERATED FILE — do not edit by hand.',
    '// Regenerate with: npx jiti scripts/gen-pseudo-locale.ts',
    `import type { ${typeName} } from '${typeSourceModule}';`,
    '',
    `const ${varName}: ${typeName} = ${serialize(pseudo)};`,
    '',
    `export default ${varName};`,
    '',
  ].join('\n');
  writeFileSync(outPath, header);
  console.log(`Wrote ${outPath}`);
}

generate(
  fr,
  new URL('../src/i18n/locales/pseudo.ts', import.meta.url).pathname,
  'TranslationKeys',
  './fr',
  'pseudo'
);
generate(
  pgFr,
  new URL('../src/i18n/locales/playground.pseudo.ts', import.meta.url).pathname,
  'PlaygroundKeys',
  './playground.fr',
  'pgPseudo'
);

execFileSync(
  'npx',
  [
    'prettier',
    '--config',
    new URL('../.prettierrc', import.meta.url).pathname,
    '--write',
    new URL('../src/i18n/locales/pseudo.ts', import.meta.url).pathname,
    new URL('../src/i18n/locales/playground.pseudo.ts', import.meta.url).pathname,
  ],
  { stdio: 'inherit' }
);
