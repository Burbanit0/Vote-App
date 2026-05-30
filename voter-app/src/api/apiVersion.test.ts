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
      'election/divergence', 'election/interpret',
      'election/quadratic-funding', 'election/liquid-democracy',
      'election/conviction-voting', 'election/power-indices',
      'theory/arrow', 'theory/iia-rate',
      'theory/plott-chaos', 'theory/judgment-aggregation',
      'theory/agenda-manipulation', 'theory/apportionment',
      'theory/sen-paradox', 'theory/manipulation-analysis',
      'theory/majority-tyranny', 'theory/democratic-backsliding',
      'theory/intergenerational', 'theory/epistocracy',
      'theory/identity-voting', 'theory/assumption-testing',
      'theory/collective-will',
      'scenarios',
      'simulations', 'simulations/simulate_voters',
      'simulations/simulate_candidates', 'simulations/get_closest_candidate',
      'simulations/simulate_utility', 'simulations/calculate_utility',
      'simulations/get_utility_matrix', 'simulations/get_voter_segments',
      'simulations/what-if', 'simulations/campaign',
    ]) {
      expect(apiPath(slug)).toBe(`/api/v2/${slug}`);
    }
  });

  it('keeps non-migrated endpoints on /api/*', () => {
    expect(apiPath('users/me')).toBe('/api/users/me');
    expect(apiPath('scenarios/gallery')).toBe('/api/scenarios/gallery');
    expect(apiPath('export/pdf')).toBe('/api/export/pdf');
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
  it('contains 35 election + 15 theory + scenarios + 10 /simulations', () => {
    expect(MIGRATED_ENDPOINTS.size).toBe(61);
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
      'election/divergence', 'election/interpret',
      'election/quadratic-funding', 'election/liquid-democracy',
      'election/conviction-voting', 'election/power-indices',
      'theory/arrow', 'theory/iia-rate',
      'theory/plott-chaos', 'theory/judgment-aggregation',
      'theory/agenda-manipulation', 'theory/apportionment',
      'theory/sen-paradox', 'theory/manipulation-analysis',
      'theory/majority-tyranny', 'theory/democratic-backsliding',
      'theory/intergenerational', 'theory/epistocracy',
      'theory/identity-voting', 'theory/assumption-testing',
      'theory/collective-will',
      'scenarios',
      'simulations', 'simulations/simulate_voters',
      'simulations/simulate_candidates', 'simulations/get_closest_candidate',
      'simulations/simulate_utility', 'simulations/calculate_utility',
      'simulations/get_utility_matrix', 'simulations/get_voter_segments',
      'simulations/what-if', 'simulations/campaign',
    ]) {
      expect(MIGRATED_ENDPOINTS.has(slug)).toBe(true);
    }
  });
});
