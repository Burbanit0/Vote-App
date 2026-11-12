import { runName, unfinished } from './runs';

const run = (relative_path: string, run_id = 'seed-1') => ({ relative_path, run_id });

describe('runName', () => {
  it('drops the run/<run_id> the runner nests a run in', () => {
    expect(runName(run('s41/p0-a0-t0.02/seed-1/run/seed-1'))).toBe('s41/p0-a0-t0.02/seed-1');
  });

  it('keeps a path that is not nested, or nested under another id', () => {
    expect(runName(run('explorer-fixture', 'explorer-fixture'))).toBe('explorer-fixture');
    expect(runName(run('a/run/seed-10'))).toBe('a/run/seed-10');
  });
});

describe('unfinished', () => {
  it('says how far a run got short of its plan', () => {
    expect(unfinished({ ...run('a'), ticks_reached: 12, ticks_planned: 32 })).toEqual({
      reached: 12,
      planned: 32,
    });
    expect(unfinished({ ...run('a'), ticks_reached: 0, ticks_planned: 32 })).toEqual({
      reached: 0,
      planned: 32,
    });
  });

  it('is null for a run that ran its plan, or does not say', () => {
    expect(unfinished({ ...run('a'), ticks_reached: 32, ticks_planned: 32 })).toBeNull();
    expect(unfinished({ ...run('a'), ticks_reached: null, ticks_planned: 32 })).toBeNull();
    expect(unfinished(run('a'))).toBeNull();
  });
});
