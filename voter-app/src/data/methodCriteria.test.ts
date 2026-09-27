import { describe, it, expect } from 'vitest';
import { METHOD_CRITERIA } from './methodCriteria';

// Guard-rail added after an audit (PLAN_SURFACE_EXTERIEURE.md §2.B) found
// `condorcet` (Copeland) carrying an unearned `participation: 'yes'` —
// contradicted by THEORY.md §4.6 (Moulin, 1988: no Condorcet-consistent
// method fully satisfies participation) and by its own neighbours in this
// same table (minimax, schulze — both Condorcet-consistent, both already
// 'no'). This can't diff arbitrary THEORY.md prose against the table
// generically, but Moulin's theorem is a real structural invariant on the
// data itself, so it's encoded directly: it would have failed on the bug
// this item fixed, and catches the same class of regression on any method
// added later.
describe('METHOD_CRITERIA invariants (THEORY.md)', () => {
  it('no Condorcet-consistent method fully satisfies participation (Moulin, 1988)', () => {
    for (const [rule, row] of Object.entries(METHOD_CRITERIA)) {
      if (row.condorcet_winner === 'yes') {
        expect(
          row.participation,
          `${rule} always elects the Condorcet winner, so per Moulin (1988) ` +
            `it cannot fully satisfy participation — THEORY.md §4.6`
        ).not.toBe('yes');
      }
    }
  });
});
