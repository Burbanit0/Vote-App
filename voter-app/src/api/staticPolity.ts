/**
 * Polity's run explorer in the static build (PLAN_BEYOND_CI W6, option A, step 4).
 *
 * With no server to read run files, /api/v2/polity is answered from runs exported ahead
 * of time by the explorer's own workers (fast_api_voter/scripts/export_polity_runs.py,
 * committed in polity-export/ and copied to the site's polity-data/): runs.json, then per run
 * its overview and frames, and its citizens in files of `citizens_per_file`.
 */
import type { components } from './types.gen';

type Schemas = components['schemas'];

/** An answer as the server would give it. */
export interface Answer {
  status: number;
  body: unknown;
}

interface ExportedRun {
  overview: Schemas['PolityRunOverview'];
  /** By `${from_tick}-${to_tick}`, in the page's chunks (lib/polity/ticks.ts). */
  frames: Record<string, Schemas['PolityFrames']>;
  citizens_per_file: number;
}

const NOT_FOUND: Answer = { status: 404, body: { detail: 'Not Found' } };
const RUN = /^\/api\/v2\/polity\/runs\/([0-9a-f]{16})(\/frames|\/citizens\/(\d+))?$/;
const ok = (body: unknown): Answer => ({ status: 200, body });

/**
 * A file of the export, gunzipped here unless the host already did (Content-Encoding):
 * gzip's first byte, 0x1f, never starts JSON.
 */
async function read(path: string): Promise<unknown> {
  const response = await fetch(
    new URL(`${import.meta.env.BASE_URL}polity-data/${path}`, location.origin)
  );
  if (!response.ok) throw new Error(`polity-data/${path}: ${response.status}`);
  const buffer = await response.arrayBuffer();
  if (new Uint8Array(buffer)[0] !== 0x1f) return JSON.parse(new TextDecoder().decode(buffer));
  const stream = new Response(buffer).body as ReadableStream<Uint8Array<ArrayBuffer>>;
  return new Response(stream.pipeThrough(new DecompressionStream('gzip'))).json();
}

/**
 * Answers a /api/v2/polity request from the export. Only runs, frames and citizens it
 * holds are fetched: a static host with SPA routing answers any other path with the page.
 * A download that fails throws, and is tried again on the next request.
 */
export function createStaticPolity(): (url: URL) => Promise<Answer> {
  const files = new Map<string, Promise<unknown>>();
  // Each file once: a finished run does not change within a visit.
  const load = <T>(path: string): Promise<T> => {
    let file = files.get(path);
    if (!file) {
      file = read(path);
      files.set(path, file);
      file.catch(() => files.delete(path));
    }
    return file as Promise<T>;
  };

  return async (url: URL) => {
    const runList = url.pathname === '/api/v2/polity/runs';
    const [, key, part, citizen] = RUN.exec(url.pathname) ?? [];
    if (!runList && key === undefined) return NOT_FOUND;
    const runs = await load<Schemas['PolityRunList']>('runs.json');
    if (runList) return ok(runs);
    if (!runs.runs.some((run) => run.key === key)) return NOT_FOUND;
    const run = await load<ExportedRun>(`${key}/run.json.gz`);
    if (!part) return ok(run.overview);
    if (citizen === undefined) {
      const span = `${url.searchParams.get('from_tick')}-${url.searchParams.get('to_tick')}`;
      return Object.hasOwn(run.frames, span) ? ok(run.frames[span]) : NOT_FOUND;
    }
    const id = Number(citizen);
    if (id >= run.overview.population) return NOT_FOUND;
    const file = Math.floor(id / run.citizens_per_file);
    const citizens = await load<Record<string, unknown>>(`${key}/citizens-${file}.json.gz`);
    return Object.hasOwn(citizens, id) ? ok(citizens[id]) : NOT_FOUND;
  };
}
