import {
  apiPath,
  shouldForceV1,
  MIGRATED_ENDPOINTS,
  FORCE_V1_LS_KEY,
} from './apiVersion';

describe('apiPath', () => {
  beforeEach(() => {
    localStorage.clear();
    // Wipe any ?apiV1=... from previous tests
    window.history.replaceState({}, '', '/');
  });

  it('routes migrated endpoints to /api/v2/*', () => {
    expect(apiPath('election/simulate')).toBe('/api/v2/election/simulate');
    expect(apiPath('election/combined-effects')).toBe('/api/v2/election/combined-effects');
    expect(apiPath('election/campaign-sensitivity')).toBe('/api/v2/election/campaign-sensitivity');
    expect(apiPath('election/coalition')).toBe('/api/v2/election/coalition');
    expect(apiPath('election/abstention')).toBe('/api/v2/election/abstention');
    expect(apiPath('election/nota')).toBe('/api/v2/election/nota');
    expect(apiPath('election/ballot-complexity')).toBe('/api/v2/election/ballot-complexity');
    expect(apiPath('election/shy-voter')).toBe('/api/v2/election/shy-voter');
    expect(apiPath('election/electoral-fatigue')).toBe('/api/v2/election/electoral-fatigue');
  });

  it('keeps non-migrated endpoints on /api/*', () => {
    expect(apiPath('election/simulate-pipeline')).toBe('/api/election/simulate-pipeline');
    expect(apiPath('election/historical-replay')).toBe('/api/election/historical-replay');
    expect(apiPath('election/cascade')).toBe('/api/election/cascade');
    expect(apiPath('theory/arrow')).toBe('/api/theory/arrow');
  });

  it('strips leading slash from slug', () => {
    expect(apiPath('/election/simulate')).toBe('/api/v2/election/simulate');
  });

  it('strips a stray api/ prefix from slug', () => {
    expect(apiPath('api/election/simulate')).toBe('/api/v2/election/simulate');
    expect(apiPath('api/v2/election/simulate')).toBe('/api/v2/election/simulate');
  });

  it('respects opts.v1 override', () => {
    expect(apiPath('election/simulate', { v1: true })).toBe('/api/election/simulate');
  });

  it('falls back to v1 when localStorage flag is set', () => {
    localStorage.setItem(FORCE_V1_LS_KEY, 'true');
    expect(apiPath('election/simulate')).toBe('/api/election/simulate');
    expect(apiPath('election/combined-effects')).toBe('/api/election/combined-effects');
    expect(apiPath('election/coalition')).toBe('/api/election/coalition');
  });

  it('falls back to v1 when ?apiV1=1 is in the URL', () => {
    window.history.replaceState({}, '', '/?apiV1=1');
    expect(apiPath('election/simulate')).toBe('/api/election/simulate');
  });

  it('query param has precedence over absence of localStorage', () => {
    window.history.replaceState({}, '', '/?apiV1=1');
    expect(shouldForceV1()).toBe(true);
  });
});

describe('MIGRATED_ENDPOINTS registry', () => {
  it('contains the 9 endpoints migrated through Phase 3 batch 3', () => {
    expect(MIGRATED_ENDPOINTS.size).toBe(9);
    for (const slug of [
      'election/simulate', 'election/combined-effects',
      'election/campaign-sensitivity', 'election/coalition',
      'election/abstention',
      'election/nota', 'election/ballot-complexity',
      'election/shy-voter', 'election/electoral-fatigue',
    ]) {
      expect(MIGRATED_ENDPOINTS.has(slug)).toBe(true);
    }
  });
});
