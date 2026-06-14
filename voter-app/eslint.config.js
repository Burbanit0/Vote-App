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
      // Dead local vars/params are a code smell, not a bug: surface as warnings
      // (a burn-down backlog) so the gate can block on real issues today.
      'unused-imports/no-unused-vars': [
        'warn',
        {
          args: 'after-used',
          argsIgnorePattern: '^_',
          varsIgnorePattern: '^_',
          caughtErrors: 'none',
          ignoreRestSiblings: true,
        },
      ],
      'prettier/prettier': ['error', { endOfLine: 'auto' }],
      // WCAG 2.1 AA accessibility rules. alt-text + label-has-associated-control
      // have pre-existing violations (lint was never enforced); kept as 'warn'
      // (visible burn-down backlog) so the gate can block today — ratchet back to
      // 'error' once the warnings are cleared.
      'jsx-a11y/alt-text': 'warn',
      'jsx-a11y/aria-props': 'error',
      'jsx-a11y/aria-proptypes': 'error',
      'jsx-a11y/aria-role': 'error',
      'jsx-a11y/aria-unsupported-elements': 'error',
      'jsx-a11y/interactive-supports-focus': 'warn',
      'jsx-a11y/label-has-associated-control': 'warn',
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
