import { describe, it, expect } from 'vitest';
import ATLAS, {
  ATLAS_METHODS,
  METHOD_COLOR,
  BLANK_COLOR,
  type AtlasMethod,
} from './electoralAtlas';
import regimes, { type BlankVoteStatus } from '../data/blankVoteRegimes';

// Integrity gate for the globe's data: valid enums, in-range coordinates, and no
// blank status that contradicts the sourced regimes dataset.

const METHODS = new Set<AtlasMethod>(ATLAS_METHODS);
const BLANK_STATUSES = new Set<BlankVoteStatus>(regimes.map((r) => r.legal_status));

describe('electoralAtlas', () => {
  it('has a decent spread of democracies', () => {
    expect(ATLAS.length).toBeGreaterThanOrEqual(20);
  });

  it('every entry is well-formed: known method, in-range lat/lon, a source', () => {
    for (const e of ATLAS) {
      expect(METHODS.has(e.method), `${e.country} method`).toBe(true);
      expect(e.lat, `${e.country} lat`).toBeGreaterThanOrEqual(-90);
      expect(e.lat, `${e.country} lat`).toBeLessThanOrEqual(90);
      expect(e.lon, `${e.country} lon`).toBeGreaterThanOrEqual(-180);
      expect(e.lon, `${e.country} lon`).toBeLessThanOrEqual(180);
      expect(e.source, `${e.country} source`).toBeTruthy();
      expect(e.flag, `${e.country} flag`).toBeTruthy();
    }
  });

  it('a blankStatus, when set, is a real status and matches the regimes dataset', () => {
    const byCountry = new Map(regimes.map((r) => [r.country, r.legal_status]));
    for (const e of ATLAS) {
      if (!e.blankStatus) continue;
      expect(BLANK_STATUSES.has(e.blankStatus), `${e.country} status valid`).toBe(true);
      // If the country is also in the sourced regimes file, they must agree.
      const known = byCountry.get(e.country);
      if (known) expect(e.blankStatus, `${e.country} agrees with regimes`).toBe(known);
    }
  });

  it('every method and every blank status has a colour', () => {
    for (const m of ATLAS_METHODS) expect(METHOD_COLOR[m], m).toMatch(/^#/);
    for (const s of BLANK_STATUSES) expect(BLANK_COLOR[s], s).toMatch(/^#/);
  });

  it('the blank-vote stars are present and correctly typed', () => {
    const uy = ATLAS.find((e) => e.country === 'Uruguay');
    const co = ATLAS.find((e) => e.country === 'Colombie');
    expect(uy?.blankStatus).toBe('competitive');
    expect(co?.blankStatus).toBe('threshold');
  });
});
