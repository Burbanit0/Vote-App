import {
  DEFAULT_LENS,
  POLITY_LENSES,
  parseCitizen,
  parseLens,
  parseWholeNumberParam,
  pickRun,
} from './urlState';

describe('polity URL state', () => {
  it('reads a known lens and falls back to the default otherwise', () => {
    expect(POLITY_LENSES).toContain('vote');
    expect(parseLens('vote')).toBe('vote');
    expect(parseLens('nonsense')).toBe(DEFAULT_LENS);
    expect(parseLens(null)).toBe(DEFAULT_LENS);
  });

  it('keeps a citizen only when they exist in the population', () => {
    expect(parseCitizen('3', 40)).toBe(3);
    expect(parseCitizen('40', 40)).toBeNull();
    expect(parseCitizen('x', 40)).toBeNull();
    expect(parseCitizen(null, 40)).toBeNull();
  });

  it('reads a whole number from the URL, and nothing else', () => {
    expect(parseWholeNumberParam('12')).toBe(12);
    expect(parseWholeNumberParam(null)).toBeNull();
    expect(parseWholeNumberParam('-1')).toBeNull();
    expect(parseWholeNumberParam('3.5')).toBeNull();
    expect(parseWholeNumberParam('abc')).toBeNull();
  });

  it('shows the requested run when listed, the first run otherwise', () => {
    expect(pickRun('b', ['a', 'b'])).toBe('b');
    expect(pickRun('zz', ['a', 'b'])).toBe('a');
    expect(pickRun(null, ['a'])).toBe('a');
    expect(pickRun('a', [])).toBeNull();
  });
});
