// eslint-plugin-sonarjs overlay (Lot 6.6, PLAN_SOLIDITE_TECHNIQUE.md) — run
// separately from the blocking `eslint.config.js` via `npm run lint:sonarjs`
// / scripts/audit.sh --quality. Informational only: 307 findings on first
// run, dominated by cognitive-load style suggestions (no-nested-conditional,
// cognitive-complexity, parameterized-tests) rather than correctness bugs —
// see PLAN_SOLIDITE_TECHNIQUE.md §6.6 for the full breakdown and why this
// isn't merged into the blocking config the way jsx-a11y/unused-imports were
// (those started this same "informational baseline burned to zero" journey,
// but at a backlog small enough to actually finish).
import base from './eslint.config.js';
import sonarjs from 'eslint-plugin-sonarjs';

export default [...base, sonarjs.configs.recommended];
