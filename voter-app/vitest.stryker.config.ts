import base from './vitest.config';
import { mergeConfig } from 'vitest/config';

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
export default mergeConfig(base, {
  test: {
    include: ['src/lib/playgroundVoting.test.ts', 'src/lib/playgroundVoting.parity.test.ts'],
    coverage: { enabled: false },
  },
});
