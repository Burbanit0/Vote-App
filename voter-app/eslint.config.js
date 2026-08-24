import js from '@eslint/js';
import globals from 'globals';
import react from 'eslint-plugin-react';
import reactHooks from 'eslint-plugin-react-hooks';
import prettier from 'eslint-plugin-prettier';
import tseslint from '@typescript-eslint/eslint-plugin';
import parser from '@typescript-eslint/parser';
import jsxA11y from 'eslint-plugin-jsx-a11y';
import unusedImports from 'eslint-plugin-unused-imports';

export default [
  js.configs.recommended,
  {
    files: ['**/*.{js,jsx,ts,tsx}'],
    languageOptions: {
      globals: {
        ...globals.browser,
        // jest globals cover describe/it/expect/beforeEach/…; add the Vitest
        // helpers the migrated tests use (the `globals` pkg here has no `vitest`
        // preset).
        ...globals.jest,
        vi: 'readonly',
        vitest: 'readonly',
      },
      parser: parser,
      parserOptions: {
        ecmaFeatures: {
          jsx: true,
        },
        ecmaVersion: 'latest',
        sourceType: 'module',
      },
    },
    plugins: {
      react,
      'react-hooks': reactHooks,
      '@typescript-eslint': tseslint,
      prettier,
      'jsx-a11y': jsxA11y,
      'unused-imports': unusedImports,
    },
    rules: {
      'react/react-in-jsx-scope': 'off',
      '@typescript-eslint/explicit-module-boundary-types': 'off',
      // TypeScript already resolves identifiers + reports unused symbols far more
      // accurately than the base rules, which false-positive on type-signature
      // params and Node/worker globals. Defer to the TS-aware rule and the compiler.
      'no-undef': 'off',
      'no-unused-vars': 'off',
      // unused-imports auto-removes dead imports (fixable); the TS rule keeps
      // flagging dead locals/params (underscore-prefixed names are intentional).
      '@typescript-eslint/no-unused-vars': 'off',
      'unused-imports/no-unused-imports': 'error',
      // Dead local vars/params are a code smell: the backlog was burned down to
      // zero, so this now blocks (underscore-prefixed names stay intentional).
      'unused-imports/no-unused-vars': [
        'error',
        {
          args: 'after-used',
          argsIgnorePattern: '^_',
          varsIgnorePattern: '^_',
          caughtErrors: 'none',
          ignoreRestSiblings: true,
        },
      ],
      'prettier/prettier': ['error', { endOfLine: 'auto' }],
      // WCAG 2.1 AA accessibility rules. The alt-text / interactive-supports-focus
      // / label-has-associated-control backlog was burned down to zero, so these
      // now block (ratcheted from 'warn' → 'error').
      'jsx-a11y/alt-text': 'error',
      'jsx-a11y/aria-props': 'error',
      'jsx-a11y/aria-proptypes': 'error',
      'jsx-a11y/aria-role': 'error',
      'jsx-a11y/aria-unsupported-elements': 'error',
      'jsx-a11y/interactive-supports-focus': 'error',
      'jsx-a11y/label-has-associated-control': 'error',
      'jsx-a11y/no-noninteractive-element-interactions': 'warn',
      'jsx-a11y/no-redundant-roles': 'error',
    },
    settings: {
      react: {
        version: 'detect',
      },
    },
  },
  {
    // Repo tooling (scripts/check-flaky.mjs …): Node, not the browser. The main
    // block above only matches .js/.jsx/.ts/.tsx, so .mjs would otherwise fall
    // through to js.configs.recommended with browser-only globals.
    files: ['scripts/**/*.{mjs,cjs,js}'],
    languageOptions: {
      globals: { ...globals.node },
      sourceType: 'module',
      ecmaVersion: 'latest',
    },
  },
  {
    // A Web Worker has no `window`. Importing a React component into one pulls in
    // React + i18next + the UI kit, all of which touch `window` at module init —
    // the worker then dies on start-up with "window is not defined" and every
    // dispatch to it fails silently (that is exactly what happened to the
    // Monte-Carlo fiche: simulationWorker.ts imported IdeologyHeatmap,
    // MethodSimilarityGraph and MethodRaceBar just to reuse three pure functions).
    // Workers import from src/lib/ only — see src/lib/simulationKernels.ts.
    files: ['src/workers/**/*.{ts,js}'],
    rules: {
      'no-restricted-imports': [
        'error',
        {
          paths: [
            { name: 'react', message: 'A worker has no DOM. Keep pure logic in src/lib/.' },
            { name: 'react-dom', message: 'A worker has no DOM. Keep pure logic in src/lib/.' },
            {
              name: 'react-i18next',
              message: 'i18next touches window at init. Workers stay UI-free.',
            },
            { name: 'i18next', message: 'i18next touches window at init. Workers stay UI-free.' },
          ],
          patterns: [
            {
              group: ['**/components/**', '@/components/**', '**/hooks/**', '@/hooks/**'],
              message:
                'Importing a component/hook into a worker loads React at worker start-up ' +
                '("window is not defined"). Extract the pure part into src/lib/ and import that.',
            },
          ],
        },
      ],
    },
  },
  {
    ignores: [
      'dist/',
      'build/',
      'coverage/',
      'playwright-report/',
      'node_modules/',
      'src/api/types.gen.ts',
    ],
  },
];
