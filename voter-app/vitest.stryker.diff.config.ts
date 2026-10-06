import base from './vitest.config';
import { mergeConfig } from 'vitest/config';

// Vitest config used ONLY by Stryker's diff run (stryker.diff.config.json,
// .github/workflows/mutation-diff.yml). Unlike vitest.stryker.config.ts, which
// narrows the suite to the engine's two test files, a diff run can mutate any
// file under src/{lib,hooks,services}, so every unit test stays in: Stryker's
// perTest coverage analysis still runs only the tests that reach each mutant.
export default mergeConfig(base, {
  test: {
    coverage: { enabled: false },
  },
});
