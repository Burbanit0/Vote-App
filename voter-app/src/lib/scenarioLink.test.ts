import { describe, expect, it } from 'vitest';
import { DEFAULT_CONFIG, DEFAULT_PLAYGROUND } from '../stores/useElectionStore';
import type { ElectionConfig, PlaygroundState } from './electionTypes';
import {
  LINK_VERSION,
  readScenarioLink,
  scenarioHash,
  scenarioUrl,
  type ScenarioLink,
} from './scenarioLink';

const base: ScenarioLink = {
  config: DEFAULT_CONFIG,
  playground: DEFAULT_PLAYGROUND,
  rule: 'plurality',
  moment: 'electorate',
  lens: 'winner',
};

// A token as another build, a hand edit or a stranger could write it.
const token = (payload: unknown) =>
  `#s=${btoa(JSON.stringify(payload)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')}`;
const v1 = (extra: Record<string, unknown>) => token({ v: LINK_VERSION, ...extra });

const edited: ScenarioLink = {
  config: {
    ...DEFAULT_CONFIG,
    candidates: [
      { name: 'Zoé', x: -0.8, y: 0.1 },
      { name: '😀 Émile', x: 0.4, y: -0.3, valence: 0.2 },
    ],
    num_voters: 500,
    seed: 7,
    description: 'Un scénario',
  },
  playground: {
    ...DEFAULT_PLAYGROUND,
    mode: 'parliament',
    behavior: 'strategic',
    ballot: { type: 'score', truncate_at: 2, score_levels: 9 },
    assembly: { ...DEFAULT_PLAYGROUND.assembly, seats: 150 },
  },
  rule: 'schulze',
  moment: 'bilan',
  lens: 'criteria',
};

describe('scenarioHash / readScenarioLink', () => {
  it('reads back what it wrote: the config, the playground, the rule, the moment and the lens', () => {
    expect(readScenarioLink(scenarioHash(edited))).toEqual(edited);
  });

  it('reads back the default scenario', () => {
    expect(readScenarioLink(scenarioHash(base))).toEqual(base);
  });

  it('keeps accents and emoji in names', () => {
    const names = readScenarioLink(scenarioHash(edited))?.config.candidates.map((c) => c.name);
    expect(names).toEqual(['Zoé', '😀 Émile']);
  });

  it('leaves out the groups of settings that equal the default, so a link stays short', () => {
    const payload = (hash: string) =>
      JSON.parse(atob(hash.slice(3).replace(/-/g, '+').replace(/_/g, '/')));
    expect(payload(scenarioHash(base))).toMatchObject({ c: {}, p: {} });
    const { c, p } = payload(scenarioHash(edited));
    expect(Object.keys(c).sort()).toEqual(['candidates', 'description', 'num_voters', 'seed']);
    expect(Object.keys(p).sort()).toEqual(['assembly', 'ballot', 'behavior', 'mode']);
  });

  it('writes a token that is safe in a URL: no +, / or =, and reads it back', () => {
    // '>>>' and '???' are the bytes that standard base64 writes with '+' and '/'.
    const link: ScenarioLink = {
      ...base,
      config: {
        ...DEFAULT_CONFIG,
        candidates: [
          { name: '>>>>>>', x: 0, y: 0 },
          { name: '??????', x: 0.5, y: 0.5 },
        ],
      },
    };
    const hash = scenarioHash(link);
    expect(hash.slice(3)).toMatch(/^[A-Za-z0-9_-]+$/);
    expect(readScenarioLink(hash)).toEqual(link);
    // Unpadded, as written: the reader must not need the '=' back.
    expect(hash.length % 4).not.toBe(0);
  });

  it('reads a token that is padded, as base64url may be', () => {
    const json = JSON.stringify({ v: LINK_VERSION, c: { description: 'ab' } });
    expect(btoa(json)).toMatch(/=$/);
    expect(readScenarioLink(`#s=${btoa(json)}`)?.config.description).toBe('ab');
  });

  it('refuses JSON that is not valid UTF-8, instead of reading it with replacement characters', () => {
    expect(readScenarioLink(`#s=${btoa('{"v":1,"c":{"description":"\xff"}}')}`)).toBeNull();
  });

  it('reads a hash with other parameters, and without its leading #', () => {
    const hash = scenarioHash(edited);
    expect(readScenarioLink(`#x=1&${hash.slice(1)}`)).toEqual(edited);
    expect(readScenarioLink(hash.slice(1))).toEqual(edited);
  });

  it.each([
    ['an empty hash', ''],
    ['a hash with no token', '#section'],
    ['an empty token', '#s='],
    ['a token that is not base64', '#s=%%%'],
    ['a token that is not JSON', `#s=${btoa('not json')}`],
    ['a token that is not UTF-8', `#s=${btoa('\xff\xfe')}`],
    ['JSON that is not an object', token([1, 2])],
    ['JSON that is null', token(null)],
    ['an object with no version', token({ c: {}, p: {} })],
    ['a newer format', token({ v: LINK_VERSION + 1, c: {}, p: {} })],
    ['a version that is not a number', token({ v: '1' })],
  ])('is not a scenario: %s', (_name, hash) => {
    expect(readScenarioLink(hash)).toBeNull();
  });

  it('checks every field: a bad one takes its default, the rest are kept', () => {
    const link = readScenarioLink(
      v1({
        c: { num_voters: 'many', seed: 9, ideology: 'nonsense' },
        p: { behavior: 'strategic', stratShare: 5, mode: 'neither' },
        r: 'not_a_rule',
        m: 'nowhere',
        l: 'x-ray',
      })
    );
    expect(link?.config.num_voters).toBe(DEFAULT_CONFIG.num_voters);
    expect(link?.config.ideology).toBe(DEFAULT_CONFIG.ideology);
    expect(link?.config.seed).toBe(9);
    expect(link?.playground.behavior).toBe('strategic');
    expect(link?.playground.stratShare).toBe(1);
    expect(link?.playground.mode).toBe(DEFAULT_PLAYGROUND.mode);
    expect(link?.rule).toBe('plurality');
    expect(link?.moment).toBe('electorate');
    expect(link?.lens).toBe('winner');
  });

  it.each(['toString', 'constructor', '__proto__', 7, null])(
    'does not take %s for a rule',
    (rule) => {
      expect(readScenarioLink(v1({ r: rule }))?.rule).toBe('plurality');
    }
  );

  it('takes the defaults when the settings are missing or not objects', () => {
    expect(readScenarioLink(v1({}))).toEqual(base);
    expect(readScenarioLink(v1({ c: 'x', p: [1] }))).toEqual(base);
  });

  it('refuses a candidate list that is not usable, and keeps the default one', () => {
    const link = readScenarioLink(
      v1({ c: { candidates: [{ name: 'Solo', x: 0, y: 0 }] }, r: 'borda' })
    );
    expect(link?.config.candidates).toEqual(DEFAULT_CONFIG.candidates);
    expect(link?.rule).toBe('borda');
  });

  it('does not let a link make a description or a phenomenon the config did not have', () => {
    const link = readScenarioLink(scenarioHash(base));
    expect(link?.config).not.toHaveProperty('description');
    expect(link?.config).not.toHaveProperty('phenomenon');
  });

  it('carries a setting that equals the default of another group', () => {
    const config: ElectionConfig = { ...DEFAULT_CONFIG, seed: DEFAULT_CONFIG.seed + 1 };
    const playground: PlaygroundState = { ...DEFAULT_PLAYGROUND, stratShare: 0.9 };
    const link = readScenarioLink(scenarioHash({ ...base, config, playground }));
    expect(link?.config.seed).toBe(DEFAULT_CONFIG.seed + 1);
    expect(link?.config.num_voters).toBe(DEFAULT_CONFIG.num_voters);
    expect(link?.playground.stratShare).toBe(0.9);
  });
});

describe('scenarioUrl', () => {
  it('is this page, without its query or hash, then the hash', () => {
    const url = scenarioUrl(edited, { origin: 'https://vote.example', pathname: '/playground' });
    expect(url).toBe(`https://vote.example/playground${scenarioHash(edited)}`);
  });
});
