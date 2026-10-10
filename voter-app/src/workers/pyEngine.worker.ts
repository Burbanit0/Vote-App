/// <reference lib="webworker" />
// W6 spike: the backend engine in Pyodide. Loads Pyodide, numpy and pydantic from the
// CDN and the engine bundle (public/pyengine.zip, built by
// `python -m pyodide_spike.build_bundle`), then answers { id, path, body } with
// { id, status, body }, as the FastAPI route would.
const PYODIDE = 'https://cdn.jsdelivr.net/pyodide/v314.0.7/full/';

type Handle = (path: string, body: string) => { toJs: () => [number, string] };

const ready: Promise<Handle> = (async () => {
  const t0 = performance.now();
  const { loadPyodide } = await import(/* @vite-ignore */ `${PYODIDE}pyodide.mjs`);
  const py = await loadPyodide({ indexURL: PYODIDE });
  const tCore = performance.now();
  await py.loadPackage(['numpy', 'pydantic']);
  const tPkgs = performance.now();
  py.unpackArchive(await (await fetch('/pyengine.zip')).arrayBuffer(), 'zip', {
    extractDir: '/engine',
  });
  py.runPython("import sys; sys.path.insert(0, '/engine')");
  const handle = py.pyimport('pyodide_spike').handle as Handle;
  const ms = (a: number, b: number) => Math.round(b - a);
  console.info(
    `[pyodide] ready: core ${ms(t0, tCore)} ms, packages ${ms(tCore, tPkgs)} ms, ` +
      `engine ${ms(tPkgs, performance.now())} ms`
  );
  return handle;
})();

self.onmessage = async (e: MessageEvent<{ id: number; path: string; body: string }>) => {
  const { id, path, body } = e.data;
  try {
    const handle = await ready;
    const t = performance.now();
    const [status, out] = handle(path, body).toJs();
    console.info(`[pyodide] ${path} ${status} in ${Math.round(performance.now() - t)} ms`);
    self.postMessage({ id, status, body: out });
  } catch (err) {
    self.postMessage({ id, status: 500, body: JSON.stringify({ detail: String(err) }) });
  }
};
