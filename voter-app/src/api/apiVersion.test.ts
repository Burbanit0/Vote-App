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
  });

  it('keeps non-migrated endpoints on /api/*', () => {
    expect(apiPath('election/abstention')).toBe('/api/election/abstention');
    expect(apiPath('election/coalition')).toBe('/api/election/coalition');
    expect(apiPath('election/simulate-pipeline')).toBe('/api/election/simulate-pipeline');
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
  it('contains exactly the 3 endpoints migrated in Phases 2-3 batch 1', () => {
    expect(MIGRATED_ENDPOINTS.size).toBe(3);
    expect(MIGRATED_ENDPOINTS.has('election/simulate')).toBe(true);
    expect(MIGRATED_ENDPOINTS.has('election/combined-effects')).toBe(true);
    expect(MIGRATED_ENDPOINTS.has('election/campaign-sensitivity')).toBe(true);
  });
});
