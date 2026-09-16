// eslint-plugin-sonarjs overlay (Lot 6.6, PLAN_SOLIDITE_TECHNIQUE.md) — run
// separately from the blocking `eslint.config.js` via `npm run lint:sonarjs`
// / scripts/audit.sh --quality; none of its rules are enabled in the
// blocking config (see the note below on why that config registers the
// plugin anyway). Informational only: 307 findings on first run, dominated
// by cognitive-load style suggestions (no-nested-conditional,
// cognitive-complexity, parameterized-tests) rather than correctness bugs —
// see PLAN_SOLIDITE_TECHNIQUE.md §6.6 for the full breakdown and why this
// isn't merged into the blocking config the way jsx-a11y/unused-imports were
// (those started this same "informational baseline burned to zero" journey,
// but at a backlog small enough to actually finish).
import base from './eslint.config.js';
import sonarjs from 'eslint-plugin-sonarjs';

// base now registers the `sonarjs` plugin key too (eslint.config.js, so that
// `// eslint-disable-next-line sonarjs/<rule>` comments resolve there without
// erroring on files it also lints) -- with none of its rules turned on.
// sonarjs.configs.recommended carries its own `plugins: { sonarjs }` entry;
// flat config accepts the same plugin key registered twice only when both
// point at the exact same object, so re-declare it here from this file's own
// `sonarjs` import (the same reference eslint.config.js registers) rather
// than reusing whatever object sonarjs.configs.recommended.plugins.sonarjs
// happens to be internally.
export default [
  ...base,
  { ...sonarjs.configs.recommended, plugins: { sonarjs } },
  // This overlay spreads the full base config above, so react-hooks/exhaustive-deps
  // and rules-of-hooks (enabled as `warn` there — PLAN_SURFACE_EXTERIEURE.md §2.J)
  // would get counted into check_quality_ratchet.sh's "sonarjs" total too, despite
  // not being sonarjs findings at all. They're already visible via the blocking
  // `npm run lint` output; off here only so this overlay's count keeps meaning
  // what its name says.
  { rules: { 'react-hooks/exhaustive-deps': 'off', 'react-hooks/rules-of-hooks': 'off' } },
];
