// Node harness for the W6 spike: load Pyodide, the engine bundle, run the three routes.
import { loadPyodide } from 'pyodide';
import { readFileSync, writeFileSync } from 'node:fs';

try {
const [bundle, payloads, out] = process.argv.slice(2);
const t0 = performance.now();
const py = await loadPyodide();
const tCore = performance.now();
await py.loadPackage(['numpy', 'pydantic']);
const tPkg = performance.now();
py.unpackArchive(new Uint8Array(readFileSync(bundle)), 'zip', { extractDir: '/engine' });
py.runPython("import sys; sys.path.insert(0, '/engine')");
py.runPython('import pyodide_spike');
const tImport = performance.now();
const handle = py.globals.get('pyodide_spike') ? py.pyimport('pyodide_spike').handle : null;
const results = {};
for (const [path, body] of Object.entries(JSON.parse(readFileSync(payloads, 'utf8')))) {
  const times = [];
  let res;
  for (let i = 0; i < 3; i++) {
    const t = performance.now();
    res = handle(path, JSON.stringify(body)).toJs();
    times.push(Math.round(performance.now() - t));
  }
  results[path] = { status: res[0], body: JSON.parse(res[1]), ms: times };
}
console.log("wasm heap MB", Math.round(py._module.HEAP8.length / 1e6), "rss MB", Math.round(process.memoryUsage().rss / 1e6));
console.log(JSON.stringify({ load_core_ms: Math.round(tCore - t0), load_pkgs_ms: Math.round(tPkg - tCore), import_ms: Math.round(tImport - tPkg), calls_ms: Object.fromEntries(Object.entries(results).map(([k, v]) => [k, [v.status, v.ms]])) }));
writeFileSync(out, JSON.stringify(Object.fromEntries(Object.entries(results).map(([k, v]) => [k, v.body]))));
} catch (e) {
  console.error('ERR', String(e.message ?? e).slice(-2500));
  process.exit(1);
}
