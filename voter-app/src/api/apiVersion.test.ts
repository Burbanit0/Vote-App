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
    for (const slug of [
      'election/simulate', 'election/combined-effects',
      'election/campaign-sensitivity', 'election/coalition', 'election/abstention',
      'election/nota', 'election/ballot-complexity', 'election/shy-voter',
      'election/electoral-fatigue',
      'election/cascade', 'election/behavioral-biases',
      'election/choice-overload', 'election/deliberation',
      'election/jury', 'election/hotelling',
      'election/polarization', 'election/sortition',
      'election/affective-polarization', 'election/demographic-turnout',
      'election/compulsory-voting', 'election/party-dynamics',
      'election/simulate-pipeline', 'election/districts',
      'election/primary', 'election/stv',
      'election/adaptive', 'election/historical-replay',
      'election/gerrymander', 'election/multiwinner_compare',
    ]) {
      expect(apiPath(slug)).toBe(`/api/v2/${slug}`);
    }
  });

  it('keeps non-migrated endpoints on /api/*', () => {
    expect(apiPath('election/quadratic-funding')).toBe('/api/election/quadratic-funding');
    expect(apiPath('election/liquid-democracy')).toBe('/api/election/liquid-democracy');
    expect(apiPath('election/power-indices')).toBe('/api/election/power-indices');
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
  it('contains the 29 endpoints migrated through Phase 3 batch 8', () => {
    expect(MIGRATED_ENDPOINTS.size).toBe(29);
    for (const slug of [
      'election/simulate', 'election/combined-effects',
      'election/campaign-sensitivity', 'election/coalition',
      'election/abstention',
      'election/nota', 'election/ballot-complexity',
      'election/shy-voter', 'election/electoral-fatigue',
      'election/cascade', 'election/behavioral-biases',
      'election/choice-overload', 'election/deliberation',
      'election/jury', 'election/hotelling',
      'election/polarization', 'election/sortition',
      'election/affective-polarization', 'election/demographic-turnout',
      'election/compulsory-voting', 'election/party-dynamics',
      'election/simulate-pipeline', 'election/districts',
      'election/primary', 'election/stv',
      'election/adaptive', 'election/historical-replay',
      'election/gerrymander', 'election/multiwinner_compare',
    ]) {
      expect(MIGRATED_ENDPOINTS.has(slug)).toBe(true);
    }
  });
});
