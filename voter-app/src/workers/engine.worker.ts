/// <reference lib="webworker" />
// The backend's engine in the visitor's browser (PLAN_BEYOND_CI W6, option A; EXP-023):
// Pyodide runs fast_api_voter/api/browser.py, the server's own routers, from engine.zip
// (built next to the static build by fast_api_voter/scripts/build_browser_engine.py).
// It answers { id, method, path, query, body } with { id, status, body }, one at a time.

const PYODIDE = 'https://cdn.jsdelivr.net/pyodide/v314.0.7/full/';
// What api/browser.py takes from Pyodide's own build (PYODIDE in build_browser_engine.py);
// their dependencies come with them.
const PACKAGES = ['numpy', 'pydantic'];

interface PyResult {
  toJs: () => [number, string];
  destroy: () => void;
}
type Handle = (method: string, path: string, query: string, body: string) => Promise<PyResult>;

async function boot(): Promise<Handle> {
  const { loadPyodide } = await import(/* @vite-ignore */ `${PYODIDE}pyodide.mjs`);
  const py = await loadPyodide({ indexURL: PYODIDE });
  await py.loadPackage(PACKAGES, { messageCallback: () => {} });
  const bundle = await fetch(
    new URL(`${import.meta.env.BASE_URL}engine.zip`, self.location.origin)
  );
  if (!bundle.ok) throw new Error(`engine.zip: ${bundle.status}`);
  py.unpackArchive(await bundle.arrayBuffer(), 'zip', { extractDir: '/engine' });
  py.runPython("import sys; sys.path.insert(0, '/engine')");
  return py.pyimport('api.browser').handle as Handle;
}

let ready: Promise<Handle> | undefined;

self.onmessage = async (
  e: MessageEvent<{ id: number; method: string; path: string; query: string; body: string }>
) => {
  const { id, method, path, query, body } = e.data;
  try {
    ready ??= boot();
    const result = await (await ready)(method, path, query, body);
    const [status, text] = result.toJs();
    result.destroy();
    self.postMessage({ id, status, body: text });
  } catch (err) {
    // The engine could not start (offline, the CDN or engine.zip unreachable): a 503, as a
    // server that is down would give, so the panels show their own error state.
    ready = undefined;
    self.postMessage({
      id,
      status: 503,
      body: JSON.stringify({ detail: `Engine unavailable: ${err}` }),
    });
  }
};
