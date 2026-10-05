import { censusSpans, groupEntries } from './biography';

const year = (y: number, role = 'electeur', party: number | null = 3) => ({
  year: y,
  role,
  office: 'aucun',
  party,
});

describe('censusSpans', () => {
  it('folds consecutive years that read the same into one span', () => {
    expect(censusSpans([year(0), year(1), year(2), year(3, 'elu'), year(4)])).toEqual([
      { ...year(0), to: 2 },
      { ...year(3, 'elu'), to: 3 },
      { ...year(4), to: 4 },
    ]);
  });

  it('starts a new span on a party change or a missing year', () => {
    expect(censusSpans([year(0), year(1, 'electeur', null), year(3, 'electeur', null)])).toEqual([
      { ...year(0), to: 0 },
      { ...year(1, 'electeur', null), to: 1 },
      { ...year(3, 'electeur', null), to: 3 },
    ]);
    expect(censusSpans([])).toEqual([]);
  });
});

describe('groupEntries', () => {
  const entry = (tick: number, event_type = 'chamber_deliberation', extra = {}) => ({
    tick,
    event_type,
    role: 'actor',
    motif: 101,
    rationale: null,
    ...extra,
  });

  it('tells a repeat once, with every tick, in order of first occurrence', () => {
    const groups = groupEntries([
      entry(4),
      entry(5, 'pressure_action'),
      entry(6),
      entry(7, 'chamber_deliberation', { motif: 102 }),
      entry(9),
    ]);
    expect(groups.map((g) => [g.entry.event_type, g.entry.motif, g.ticks])).toEqual([
      ['chamber_deliberation', 101, [4, 6, 9]],
      ['pressure_action', 101, [5]],
      ['chamber_deliberation', 102, [7]],
    ]);
  });

  it('keeps apart what says something of its own', () => {
    const groups = groupEntries([
      entry(1, 'chamber_deliberation', { rationale: 'the bill is fair' }),
      entry(2, 'chamber_deliberation', { rationale: 'the bill is fair' }),
      entry(3, 'agent_turn'),
      entry(4, 'agent_turn'),
      entry(5, 'forum_post'),
      entry(6, 'forum_post'),
      entry(7, 'chamber_deliberation', { role: 'listed' }),
    ]);
    expect(groups.map((g) => g.ticks)).toEqual([[1], [2], [3], [4], [5], [6], [7]]);
  });
});
