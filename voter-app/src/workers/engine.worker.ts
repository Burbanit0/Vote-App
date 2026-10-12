/// <reference lib="webworker" />
// The backend's engine in the visitor's browser (PLAN_BEYOND_CI W6, option A; EXP-023):
// Pyodide runs fast_api_voter/api/browser.py, the server's own routers, from engine.zip
// (built next to the static build by fast_api_voter/scripts/build_browser_engine.py).
// One request at a time, in order: { id, method, path, query, body } gets { id, started }
// when it begins, then { id, status, body } (see Reply in api/browserEngine.ts).

const PYODIDE = 'https://cdn.jsdelivr.net/pyodide/v314.0.7/full/';

interface PyResult {
  toJs: () => [number, string];
  destroy: () => void;
}
type Handle = (method: string, path: string, query: string, body: string) => Promise<PyResult>;
interface Request {
  id: number;
  method: string;
  path: string;
  query: string;
  body: string;
}

async function boot(): Promise<Handle> {
  const { loadPyodide } = await import(/* @vite-ignore */ `${PYODIDE}pyodide.mjs`);
  const [py, bundle] = await Promise.all([
    loadPyodide({ indexURL: PYODIDE }),
    fetch(new URL(`${import.meta.env.BASE_URL}engine.zip`, self.location.origin)),
  ]);
  if (!bundle.ok) throw new Error(`engine.zip: ${bundle.status}`);
  py.unpackArchive(await bundle.arrayBuffer(), 'zip', { extractDir: '/engine' });
  // The packages the bundle takes from Pyodide's own build, as the bundle builder lists them.
  const { packages } = JSON.parse(py.FS.readFile('/engine/engine.json', { encoding: 'utf8' }));
  await py.loadPackage(packages, { messageCallback: () => {} });
  py.runPython("import sys; sys.path.insert(0, '/engine')");
  return py.pyimport('api.browser').handle as Handle;
}

// Started once, on the first request. If it fails, every request gets `fatal`, and the
// page replaces this worker: a retry here would pile Pyodide instances up in one worker.
let engine: Promise<Handle> | undefined;
const cancelled = new Set<number>();
let queue: Promise<void> = Promise.resolve();

async function run({ id, method, path, query, body }: Request): Promise<void> {
  if (cancelled.delete(id)) return;
  let handle: Handle;
  try {
    handle = await (engine ??= boot());
  } catch (err) {
    // Offline, or the CDN or engine.zip unreachable: a 503, as a server that is down.
    const detail = `Engine unavailable: ${err}`;
    self.postMessage({ id, fatal: true, status: 503, body: JSON.stringify({ detail }) });
    return;
  }
  self.postMessage({ id, started: true });
  try {
    const result = await handle(method, path, query, body);
    const [status, text] = result.toJs();
    result.destroy();
    self.postMessage({ id, status, body: text });
  } catch {
    // Past the app's own catch-all: the server's 500.
    self.postMessage({
      id,
      status: 500,
      body: JSON.stringify({ detail: 'Internal server error' }),
    });
  }
}

self.onmessage = (e: MessageEvent<Request | { cancel: number }>) => {
  if ('cancel' in e.data) {
    cancelled.add(e.data.cancel);
  } else {
    const request = e.data;
    queue = queue.then(() => run(request));
  }
};
