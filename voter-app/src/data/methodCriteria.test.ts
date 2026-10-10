import { describe, it, expect } from 'vitest';
import {
  METHOD_CRITERIA,
  METHOD_CRITERIA_ENTRIES,
  CRITERION_KEYS,
  loadVerdicts,
} from './methodCriteria';
import registry from './method_criteria.json';
import { LEADER_RULES } from '../lib/scorecard';
import { RULE_LABELS } from '../lib/playgroundVoting';
import { RANDOM_BALLOT_PROPS } from '../lib/playgroundCriteria';

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

describe('the criteria registry (method_criteria.json, PLAN_BEYOND_CI W1.2)', () => {
  const cells = Object.entries(METHOD_CRITERIA_ENTRIES).flatMap(([rule, row]) =>
    CRITERION_KEYS.map((key) => ({ at: `${rule}.${key}`, ...row[key] }))
  );

  it('has every rule, and nothing else', () => {
    // RULE_LABELS is a Record<Rule, ...> tsc keeps complete: a rule added to the union
    // without a registry entry fails here.
    expect(Object.keys(METHOD_CRITERIA).sort()).toEqual(Object.keys(RULE_LABELS).sort());
    expect(Object.keys(METHOD_CRITERIA).sort()).toEqual([...LEADER_RULES].sort());
  });

  it('marks how each verdict is known', () => {
    for (const cell of cells) {
      expect(['engine-tested', 'literature', 'variant'], cell.at).toContain(cell.basis);
      // A test is an engine-tested cell's source; 'conditional' is never what an engine set says.
      if (cell.basis === 'engine-tested') expect(cell.verdict, cell.at).not.toBe('conditional');
      if (cell.basis === 'variant') expect(cell.note, cell.at).toBeTruthy();
    }
  });

  it("agrees with the map lens's stated properties of random ballot", () => {
    const lens: [
      keyof typeof RANDOM_BALLOT_PROPS,
      keyof (typeof METHOD_CRITERIA)['random_ballot'],
    ][] = [
      ['condorcet', 'condorcet_winner'],
      ['condorcet_loser', 'condorcet_loser'],
      ['majority', 'majority'],
      ['monotonic', 'monotonicity'],
      ['iia', 'iia'],
      ['reversal', 'reversal'],
    ];
    for (const [lensKey, key] of lens) {
      const stated = RANDOM_BALLOT_PROPS[lensKey];
      if (stated === null) continue; // the lens calls it not meaningful for a lottery
      expect(METHOD_CRITERIA.random_ballot[key], key).toBe(stated ? 'yes' : 'no');
    }
  });
});

describe('the registry loader refuses what the matrix could not show', () => {
  // A copy of the real registry with one thing broken.
  const broken = (edit: (reg: Record<string, unknown>) => void) => {
    const reg = structuredClone(registry) as unknown as Record<string, unknown>;
    edit(reg);
    return () => loadVerdicts(reg as unknown as typeof registry);
  };
  const plurality = (reg: Record<string, unknown>) =>
    (reg.rules as Record<string, Record<string, Record<string, unknown>>>).plurality;

  it('accepts the real registry', () => {
    expect(loadVerdicts()).toEqual(METHOD_CRITERIA);
  });

  it('refuses criteria in another order or set', () => {
    expect(broken((reg) => (reg.criteria as string[]).reverse())).toThrow(/criteria .* are not/);
  });

  it('refuses an unknown criterion', () => {
    expect(broken((reg) => (plurality(reg).fairness = { verdict: 'yes' }))).toThrow(
      /plurality has unknown criteria fairness/
    );
  });

  it('refuses a missing or unknown verdict', () => {
    expect(broken((reg) => (plurality(reg)[CRITERION_KEYS[0]].verdict = 'maybe'))).toThrow(
      /verdict maybe/
    );
    expect(broken((reg) => delete plurality(reg)[CRITERION_KEYS[0]])).toThrow(/verdict undefined/);
  });
});
