import { apiPath } from './apiVersion';

describe('apiPath', () => {
  it('prefixes a bare slug with /api/v2/', () => {
    expect(apiPath('election/simulate')).toBe('/api/v2/election/simulate');
    expect(apiPath('scenarios')).toBe('/api/v2/scenarios');
    expect(apiPath('simulations/compare')).toBe('/api/v2/simulations/compare');
  });

  it('strips a leading slash', () => {
    expect(apiPath('/election/simulate')).toBe('/api/v2/election/simulate');
  });

  it('normalises an already-qualified path (idempotent)', () => {
    expect(apiPath('/api/v2/election/simulate')).toBe('/api/v2/election/simulate');
    expect(apiPath('api/v2/scenarios')).toBe('/api/v2/scenarios');
    expect(apiPath('api/election/abstention')).toBe('/api/v2/election/abstention');
  });
});
