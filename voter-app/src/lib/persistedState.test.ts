import { describe, it, expect } from 'vitest';
import {
  STORAGE_VERSION,
  isNewerThanThisBuild,
  readStored,
  sanitizeConfig,
  sanitizePlayground,
  withVersion,
} from './persistedState';
import { DEFAULT_CONFIG, DEFAULT_PLAYGROUND } from '../stores/useElectionStore';

const read = (v: unknown) => readStored(JSON.stringify(v));

describe('readStored — what a stored value may be', () => {
  it('has nothing to read for no value, malformed JSON, or a non-object', () => {
    expect(readStored(null)).toBeNull();
    expect(readStored('')).toBeNull();
    expect(readStored('{not json')).toBeNull();
    expect(readStored('42')).toBeNull();
    expect(readStored('null')).toBeNull();
    expect(readStored('[1,2]')).toBeNull();
    expect(readStored('"text"')).toBeNull();
  });

  it('reads the shape written before versioning (no version) as it is', () => {
    expect(read({ num_voters: 120 })).toEqual({ num_voters: 120 });
  });

  it('reads the current version, and the version a round trip writes', () => {
    expect(read({ version: STORAGE_VERSION, seed: 3 })).toEqual({
      version: STORAGE_VERSION,
      seed: 3,
    });
    const written = withVersion({ seed: 3 });
    expect(written).toEqual({ seed: 3, version: STORAGE_VERSION });
    expect(readStored(JSON.stringify(written))).toEqual(written);
  });

  it('ignores a version from a newer build, and one that is not a whole number', () => {
    expect(read({ version: STORAGE_VERSION + 1, seed: 3 })).toBeNull();
    expect(read({ version: '1', seed: 3 })).toBeNull();
    expect(read({ version: 1.5, seed: 3 })).toBeNull();
    expect(read({ version: -1, seed: 3 })).toBeNull();
    expect(read({ version: null, seed: 3 })).toBeNull();
  });
});

describe('isNewerThanThisBuild', () => {
  it('is true only for a stored object whose version is above this build', () => {
    expect(isNewerThanThisBuild(JSON.stringify({ version: STORAGE_VERSION + 1 }))).toBe(true);
    expect(isNewerThanThisBuild(JSON.stringify({ version: STORAGE_VERSION }))).toBe(false);
    expect(isNewerThanThisBuild(JSON.stringify({ seed: 1 }))).toBe(false);
    expect(isNewerThanThisBuild(JSON.stringify({ version: 'x' }))).toBe(false);
    expect(isNewerThanThisBuild(JSON.stringify([9]))).toBe(false);
    expect(isNewerThanThisBuild('{not json')).toBe(false);
    expect(isNewerThanThisBuild(null)).toBe(false);
  });
});

describe('sanitizeConfig', () => {
  it('returns the fallback when nothing was stored', () => {
    expect(sanitizeConfig(null, DEFAULT_CONFIG)).toBe(DEFAULT_CONFIG);
  });

  it('round-trips a valid config, and drops the version and unknown keys', () => {
    const valid = {
      ...DEFAULT_CONFIG,
      num_voters: 120,
      seed: 7,
      ideology: 'polarized',
      description: 'd',
      phenomenon: 'p',
      candidates: [
        { name: 'A', x: -0.5, y: 0.1, z: 0.2, valence: 0.3 },
        { name: 'B', x: 0.5, y: -0.1 },
      ],
      information_model: { ...DEFAULT_CONFIG.information_model, media_bias: { A: 0.2 } },
    };
    const out = sanitizeConfig({ ...valid, version: 1, stray: true }, DEFAULT_CONFIG);
    expect(out).toEqual(valid);
    expect('version' in out || 'stray' in out).toBe(false);
  });

  it('trims names and clamps positions, and keeps a name counted in code points', () => {
    const emoji = '😀'.repeat(40); // 80 UTF-16 units, 40 code points: a valid name
    const out = sanitizeConfig(
      {
        candidates: [
          { name: ' Ann ', x: 5, y: -5 },
          { name: emoji, x: 0.2, y: 0.2 },
        ],
      },
      DEFAULT_CONFIG
    );
    expect(out.candidates).toEqual([
      { name: 'Ann', x: 1, y: -1 },
      { name: emoji, x: 0.2, y: 0.2 },
    ]);
  });

  it('takes the whole candidate list or none: one bad, repeated or surplus candidate rejects it', () => {
    const ok = { name: 'Ok', x: 0, y: 0 };
    const other = { name: 'Other', x: 0, y: 0 };
    const bad = [
      null,
      'x',
      { name: '', x: 0, y: 0 },
      { name: '   ', x: 0, y: 0 },
      { name: 3, x: 0, y: 0 },
      { name: '😀'.repeat(65), x: 0, y: 0 },
      { name: 'NoX', y: 0 },
      { name: 'NoY', x: 0 },
      { name: 'NaN', x: Number.NaN, y: 0 },
      { name: 'Inf', x: 0, y: Number.POSITIVE_INFINITY },
    ];
    for (const one of bad)
      expect(sanitizeConfig({ candidates: [ok, other, one] }, DEFAULT_CONFIG).candidates).toBe(
        DEFAULT_CONFIG.candidates
      );
    const dup = { name: 'Ok', x: 1, y: 1 };
    expect(sanitizeConfig({ candidates: [ok, other, dup] }, DEFAULT_CONFIG).candidates).toBe(
      DEFAULT_CONFIG.candidates
    );
    expect(sanitizeConfig({ candidates: [ok] }, DEFAULT_CONFIG).candidates).toBe(
      DEFAULT_CONFIG.candidates
    );
    expect(sanitizeConfig({ candidates: 'nope' }, DEFAULT_CONFIG).candidates).toBe(
      DEFAULT_CONFIG.candidates
    );
    const nine = Array.from({ length: 9 }, (_, i) => ({ name: `C${i}`, x: 0, y: 0 }));
    expect(sanitizeConfig({ candidates: nine }, DEFAULT_CONFIG).candidates).toBe(
      DEFAULT_CONFIG.candidates
    );
    expect(
      sanitizeConfig({ candidates: nine.slice(0, 8) }, DEFAULT_CONFIG).candidates
    ).toHaveLength(8);
  });

  it('ignores a bad z or valence, and clamps a good one', () => {
    const [first, second] = sanitizeConfig(
      {
        candidates: [
          { name: 'A', x: 0, y: 0, z: 'high', valence: Number.NaN },
          { name: 'B', x: 0, y: 0, z: 9, valence: -9 },
        ],
      },
      DEFAULT_CONFIG
    ).candidates;
    expect(first).toEqual({ name: 'A', x: 0, y: 0 });
    expect(second).toEqual({ name: 'B', x: 0, y: 0, z: 1, valence: -1 });
  });

  it('puts a bad number, string or flag back to its default, one field at a time', () => {
    const out = sanitizeConfig(
      {
        candidates: [
          { name: 'A', x: 0, y: 0 },
          { name: 'B', x: 1, y: 1 },
        ],
        num_voters: 'many',
        ideology: 12,
        seed: Number.NaN,
        blank_vote: { enabled: 'yes', rule: 'bogus', contagion: { beta: 'x', network: 3 } },
        information_model: { enabled: 1, media_bias: [1], voter_segments: 'x' },
        campaign: { enabled: null, num_days: Number.POSITIVE_INFINITY, polling_effect: 'x' },
      },
      DEFAULT_CONFIG
    );
    expect(out).toEqual({
      ...DEFAULT_CONFIG,
      candidates: [
        { name: 'A', x: 0, y: 0 },
        { name: 'B', x: 1, y: 1 },
      ],
    });
  });

  it('clamps numbers to their range, rounds whole ones, and drops non-numeric bias entries', () => {
    const out = sanitizeConfig(
      {
        num_voters: 99999,
        seed: -4.4,
        ideology: 'bimodal',
        blank_vote: { contagion: { beta: 9, gamma: -1 } },
        information_model: {
          media_bias: { Alice: 0.5, Bob: 'x', Carol: Number.NaN, Ghost: 0.9 },
          voter_segments: { low_info: 2, medium_info: -2, high_info: 0.5 },
        },
        campaign: { num_days: 0.2, polling_effect: 7 },
        description: 'x'.repeat(601),
      },
      DEFAULT_CONFIG
    );
    expect(out.num_voters).toBe(1000);
    expect(out.seed).toBe(0);
    expect(out.ideology).toBe(DEFAULT_CONFIG.ideology);
    expect(out.blank_vote.contagion).toMatchObject({ beta: 1, gamma: 0 });
    // Non-numeric entries go, and so does a bias for a candidate who is not there.
    expect(out.information_model.media_bias).toEqual({ Alice: 0.5 });
    expect(out.information_model.voter_segments).toEqual({
      low_info: 1,
      medium_info: 0,
      high_info: 0.5,
    });
    expect(out.campaign).toMatchObject({ num_days: 1, polling_effect: 1 });
    expect(out.description).toBe('x'.repeat(600)); // cut, not dropped
    expect(sanitizeConfig({ num_voters: 4 }, DEFAULT_CONFIG).num_voters).toBe(10);
    expect(sanitizeConfig({ num_voters: 333.4 }, DEFAULT_CONFIG).num_voters).toBe(333);
  });

  it('keeps every voter distribution the app knows, and a seed the seed field accepts', () => {
    for (const ideology of ['random', 'centrist', 'polarized', 'left_skewed', 'right_skewed'])
      expect(sanitizeConfig({ ideology }, DEFAULT_CONFIG).ideology).toBe(ideology);
    // The field has a minimum of 0 and no maximum: a seed typed in must come back as typed.
    expect(sanitizeConfig({ seed: 3_000_000_000 }, DEFAULT_CONFIG).seed).toBe(3_000_000_000);
  });

  it('keeps a bias only for candidates that are there, whichever list the candidates came from', () => {
    const out = sanitizeConfig(
      { candidates: 'broken', information_model: { media_bias: { Alice: 0.1, Zed: 0.2 } } },
      DEFAULT_CONFIG
    );
    expect(out.candidates).toBe(DEFAULT_CONFIG.candidates);
    expect(out.information_model.media_bias).toEqual({ Alice: 0.1 });
  });

  it('accepts every blank-vote rule and contagion network the app has', () => {
    const out = sanitizeConfig(
      {
        blank_vote: {
          enabled: true,
          rule: 'threshold_30',
          contagion: { enabled: true, network: 'block' },
        },
      },
      DEFAULT_CONFIG
    );
    expect(out.blank_vote).toMatchObject({
      enabled: true,
      rule: 'threshold_30',
      contagion: { enabled: true, network: 'block' },
    });
  });
});

describe('sanitizePlayground', () => {
  it('returns the fallback when nothing was stored', () => {
    expect(sanitizePlayground(null, DEFAULT_PLAYGROUND)).toBe(DEFAULT_PLAYGROUND);
  });

  it('round-trips the default slice, and a non-default one', () => {
    expect(sanitizePlayground({ ...DEFAULT_PLAYGROUND, version: 1 }, DEFAULT_PLAYGROUND)).toEqual(
      DEFAULT_PLAYGROUND
    );
    const other = {
      ...DEFAULT_PLAYGROUND,
      mode: 'parliament' as const,
      space: { dims: 3 as const, axisLabels: ['a', 'b', 'c'], valenceEnabled: true },
      behavior: 'mixed' as const,
      stratTactic: 'burying' as const,
      stratShare: 0.4,
      prefSource: 'mallows' as const,
      prefParams: { phi: 0.7 },
      ballot: { type: 'rank_truncated' as const, truncate_at: 2, score_levels: 9 },
      turnout: { model: 'alienation' as const, intensity: 0.9 },
      blank: { enabled: true, intensity: 0.2, lens: 'threshold' as const },
      electorate: {
        mode: 'composed' as const,
        correlation: -0.3,
        noise: 0.1,
        communities: [
          { id: 'a', label: 'A', x: 0, y: 0, z: 0.5, spread: 0.2, weight: 2, turnout: 0.8 },
        ],
      },
      assembly: {
        structure: 'mmp' as const,
        seats: 120,
        threshold: 0.03,
        apportionment: 'sainte_lague' as const,
        num_districts: 5,
        strategic_desertion: true,
      },
    };
    expect(sanitizePlayground(other, DEFAULT_PLAYGROUND)).toEqual(other);
  });

  it('keeps a stored older shape: a missing slice or knob takes its default', () => {
    const out = sanitizePlayground(
      { mode: 'parliament', assembly: { seats: 60 }, space: { dims: 1 } },
      DEFAULT_PLAYGROUND
    );
    expect(out.mode).toBe('parliament');
    expect(out.assembly).toEqual({ ...DEFAULT_PLAYGROUND.assembly, seats: 60 });
    expect(out.space).toEqual({ ...DEFAULT_PLAYGROUND.space, dims: 1 });
    expect(out.ballot).toEqual(DEFAULT_PLAYGROUND.ballot);
  });

  it('puts every wrong type or value back to its default', () => {
    const junk = {
      mode: 'bogus',
      space: { dims: 7, axisLabels: [1, 2], valenceEnabled: 'x' },
      behavior: 3,
      stratTactic: null,
      stratShare: 'x',
      prefSource: 'nope',
      prefParams: [1],
      ballot: { type: 'nope', truncate_at: 'x', score_levels: Number.NaN },
      turnout: { model: 'nope', intensity: 'x' },
      blank: { enabled: 1, intensity: null, lens: 'nope' },
      electorate: { mode: 'nope', correlation: 'x', noise: 'x', communities: [] },
      assembly: {
        structure: 'nope',
        seats: 'x',
        threshold: 'x',
        apportionment: 3,
        num_districts: 'x',
        strategic_desertion: 'x',
      },
    };
    expect(sanitizePlayground(junk, DEFAULT_PLAYGROUND)).toEqual(DEFAULT_PLAYGROUND);
    expect(
      sanitizePlayground({ space: 5, ballot: 'x', electorate: 'x' }, DEFAULT_PLAYGROUND)
    ).toEqual(DEFAULT_PLAYGROUND);
  });

  it('checks the axis labels: one to three strings of reasonable length', () => {
    const labels = (axisLabels: unknown) =>
      sanitizePlayground({ space: { axisLabels } }, DEFAULT_PLAYGROUND).space.axisLabels;
    expect(labels(['x'])).toEqual(['x']);
    expect(labels([])).toEqual(DEFAULT_PLAYGROUND.space.axisLabels);
    expect(labels(['a', 'b', 'c', 'd'])).toEqual(DEFAULT_PLAYGROUND.space.axisLabels);
    expect(labels(['x'.repeat(61)])).toEqual(DEFAULT_PLAYGROUND.space.axisLabels);
  });

  it('clamps the numeric knobs to their range', () => {
    const out = sanitizePlayground(
      {
        stratShare: 4,
        ballot: { truncate_at: 50, score_levels: 1 },
        turnout: { intensity: -1 },
        blank: { intensity: 9 },
        electorate: { correlation: 3, noise: -3 },
        assembly: { seats: 0, threshold: 2, num_districts: 500 },
      },
      DEFAULT_PLAYGROUND
    );
    expect(out.stratShare).toBe(1);
    expect(out.ballot).toMatchObject({ truncate_at: 8, score_levels: 2 });
    expect(out.turnout.intensity).toBe(0);
    expect(out.blank.intensity).toBe(1);
    expect(out.electorate).toMatchObject({ correlation: 1, noise: 0 });
    expect(out.assembly).toMatchObject({ seats: 1, threshold: 1, num_districts: 100 });
  });

  it('checks each community, drops the unusable ones, and keeps the default blocs if none is left', () => {
    const community = (extra: object) => ({
      id: 'a',
      label: 'A',
      x: 0,
      y: 0,
      spread: 0.2,
      weight: 1,
      turnout: 0.9,
      ...extra,
    });
    const communities = (list: unknown) =>
      sanitizePlayground({ electorate: { communities: list } }, DEFAULT_PLAYGROUND).electorate
        .communities;
    expect(
      communities([
        null,
        community({ id: '' }),
        community({ id: 3 }),
        community({ x: 'x' }),
        community({ y: Number.NaN }),
        community({ x: Number.POSITIVE_INFINITY }),
      ])
    ).toBe(DEFAULT_PLAYGROUND.electorate.communities);
    expect(communities('x')).toBe(DEFAULT_PLAYGROUND.electorate.communities);
    const kept = communities([
      community({ label: 'L'.repeat(70), spread: 9, weight: -5, turnout: 5, x: 3, z: 'x' }),
      community({ id: 'a' }),
      community({ id: 'b', z: 2, weight: 0 }),
      community({ id: 'c', label: 9 }),
    ]);
    expect(kept).toEqual([
      { id: 'a', label: 'L'.repeat(60), x: 1, y: 0, spread: 1, weight: 0, turnout: 1 },
      { id: 'b', label: 'A', x: 0, y: 0, spread: 0.2, weight: 0, turnout: 0.9, z: 1 },
      { id: 'c', label: 'c', x: 0, y: 0, spread: 0.2, weight: 1, turnout: 0.9 },
    ]);
    // The composer lets a user add as many blocs as they like: none is cut on reload.
    const many = Array.from({ length: 40 }, (_, i) => community({ id: `c${i}` }));
    expect(communities(many)).toHaveLength(40);
  });
});
