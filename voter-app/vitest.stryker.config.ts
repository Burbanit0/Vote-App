import base from './vitest.config';

// Vitest config used ONLY by Stryker (see stryker.config.json).
//
// Stryker re-runs the suite once per surviving mutant. Running all 1693 tests
// each time would make a full pass take hours for no signal: the mutants live in
// src/lib/playgroundVoting.ts, and nothing outside these two files asserts on its
// output. Narrowing `include` is what keeps the run measured in minutes.
//
// Both files are included on purpose:
//  - playgroundVoting.test.ts     — the unit assertions (hand-written profiles)
//  - playgroundVoting.parity.test.ts — the golden fixtures generated from the
//    Python engine. This is the stronger of the two: a mutant that changes any
//    winner on 60 ordinal + 60 cardinal profiles dies here. Excluding it would
//    have measured the weaker half of the harness and reported a worse score
//    than the code actually has.
//
// Spread, not mergeConfig: mergeConfig CONCATENATES arrays, so the base `include`
// (src/**/*.test.{ts,tsx}) stayed in and Stryker's dry run executed all ~180 test
// files from its .stryker-tmp sandbox. One of them reads docs/research/bibliography.bib,
// which the sandbox does not copy: the dry run failed and no mutation score was
// computed from 2026-10-12.
export default {
  ...base,
  test: {
    ...base.test,
    include: ['src/lib/playgroundVoting.test.ts', 'src/lib/playgroundVoting.parity.test.ts'],
    coverage: { ...base.test?.coverage, enabled: false },
  },
};
