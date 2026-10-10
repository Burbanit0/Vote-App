// W6 spike: with ?engine=pyodide in the URL, three routes run in Pyodide in a Web Worker
// (workers/pyEngine.worker.ts) instead of on the backend. Read once, at load, so the
// flag outlives the Lab rewriting its query string.
const PORTED = new Set([
  '/api/v2/election/stv',
  '/api/v2/election/polarization',
  '/api/v2/tech/polis',
]);
const on =
  typeof location !== 'undefined' &&
  new URLSearchParams(location.search).get('engine') === 'pyodide';

type Reply = { id: number; status: number; body: string };
const pending = new Map<number, (r: Reply) => void>();
let worker: Worker | undefined;
let seq = 0;

function call(path: string, body: string): Promise<Reply> {
  if (!worker) {
    worker = new Worker(new URL('../workers/pyEngine.worker.ts', import.meta.url), {
      type: 'module',
    });
    worker.onmessage = (e: MessageEvent<Reply>) => {
      pending.get(e.data.id)?.(e.data);
      pending.delete(e.data.id);
    };
  }
  const id = ++seq;
  return new Promise((resolve) => {
    pending.set(id, resolve);
    worker!.postMessage({ id, path, body });
  });
}

async function viaWorker(path: string, request: Request): Promise<Response> {
  const { status, body } = await call(path, await request.text());
  return new Response(body, { status, headers: { 'Content-Type': 'application/json' } });
}

export async function pyFetch(request: Request): Promise<Response> {
  const path = new URL(request.url).pathname;
  if (!PORTED.has(path)) return fetch(request);
  const t0 = performance.now();
  const res = on ? await viaWorker(path, request) : await fetch(request);
  // Read by scripts/spike-pyodide.mjs, for either engine.
  const g = globalThis as { engineCalls?: object[] };
  (g.engineCalls ??= []).push({
    path,
    engine: on ? 'pyodide' : 'backend',
    ms: Math.round(performance.now() - t0),
    status: res.status,
  });
  return res;
}
