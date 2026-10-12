import { gzipSync } from 'node:zlib';
import { createStaticPolity } from './staticPolity';

const KEY = '0123456789abcdef';
const BASE = `http://localhost/api/v2/polity/runs/${KEY}`;
const gz = (value: unknown) => new Uint8Array(gzipSync(JSON.stringify(value)));

/** An export of one run: 5 ticks in chunks of 3, 3 citizens in files of 2. */
const EXPORT: Record<string, BodyInit> = {
  'runs.json': JSON.stringify({ runs: [{ key: KEY }] }),
  [`${KEY}/run.json.gz`]: gz({
    overview: { key: KEY, population: 3 },
    frames: { '0-2': { from_tick: 0 }, '3-4': { from_tick: 3 } },
    citizens_per_file: 2,
  }),
  [`${KEY}/citizens-0.json.gz`]: gz({ 0: { citizen_id: 0 }, 1: { citizen_id: 1 } }),
  // As a host that gunzips on the way (Content-Encoding) hands it over.
  [`${KEY}/citizens-1.json.gz`]: JSON.stringify({ 2: { citizen_id: 2 } }),
};

let fetched: string[];

beforeEach(() => {
  fetched = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: URL) => {
      const path = url.pathname.replace('/polity-data/', '');
      fetched.push(path);
      return path in EXPORT ? new Response(EXPORT[path]) : new Response('', { status: 404 });
    })
  );
});

afterEach(() => vi.unstubAllGlobals());

const ask = (polity: ReturnType<typeof createStaticPolity>, url: string) => polity(new URL(url));

describe('createStaticPolity', () => {
  it('answers the runs, an overview, a chunk of frames and citizens from the export', async () => {
    const polity = createStaticPolity();
    expect(await ask(polity, 'http://localhost/api/v2/polity/runs')).toEqual({
      status: 200,
      body: { runs: [{ key: KEY }] },
    });
    expect((await ask(polity, BASE)).body).toEqual({ key: KEY, population: 3 });
    expect((await ask(polity, `${BASE}/frames?from_tick=3&to_tick=4`)).body).toEqual({
      from_tick: 3,
    });
    expect((await ask(polity, `${BASE}/citizens/1`)).body).toEqual({ citizen_id: 1 });
    expect((await ask(polity, `${BASE}/citizens/2`)).body).toEqual({ citizen_id: 2 });
    // Each file once; a citizen loads only its own file.
    expect(fetched).toEqual([
      'runs.json',
      `${KEY}/run.json.gz`,
      `${KEY}/citizens-0.json.gz`,
      `${KEY}/citizens-1.json.gz`,
    ]);
  });

  it('answers 404 for what the export does not hold, without fetching it', async () => {
    const polity = createStaticPolity();
    // Not a run: answered before anything is fetched.
    expect((await ask(polity, 'http://localhost/api/v2/polity/elsewhere')).status).toBe(404);
    expect(fetched).toEqual([]);
    for (const url of [
      'http://localhost/api/v2/polity/runs/fedcba9876543210',
      `${BASE}/frames?from_tick=1&to_tick=2`,
      `${BASE}/citizens/3`,
    ]) {
      expect(await ask(polity, url)).toEqual({ status: 404, body: { detail: 'Not Found' } });
    }
    expect(fetched).toEqual(['runs.json', `${KEY}/run.json.gz`]);
  });

  it('answers 404 for a citizen its file lacks, not an empty answer', async () => {
    EXPORT[`${KEY}/citizens-0.json.gz`] = gz({ 0: { citizen_id: 0 } });
    try {
      expect((await ask(createStaticPolity(), `${BASE}/citizens/1`)).status).toBe(404);
    } finally {
      EXPORT[`${KEY}/citizens-0.json.gz`] = gz({ 0: { citizen_id: 0 }, 1: { citizen_id: 1 } });
    }
  });

  it('throws when a file cannot be downloaded, and tries it again next time', async () => {
    const polity = createStaticPolity();
    vi.mocked(fetch).mockResolvedValueOnce(new Response('', { status: 500 }));
    await expect(ask(polity, 'http://localhost/api/v2/polity/runs')).rejects.toThrow(
      'polity-data/runs.json: 500'
    );
    expect((await ask(polity, 'http://localhost/api/v2/polity/runs')).status).toBe(200);
  });
});
