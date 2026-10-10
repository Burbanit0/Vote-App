# W6 spike: the engine in Pyodide

The code behind [EXP-023](../../docs/exploration/EXP-023-pyodide-web-worker-vs-fly-container.md).
Not merged: a spike branch.

- `__init__.py`: `handle(path, body)`, three `/api/v2` routes run as FastAPI runs them.
- `build_bundle.py`: zips `api/` (without its web, socket, polity and test layers), this
  package and structlog for Pyodide.
- `node_run.mjs` and `native_run.py`: the same three calls (`payloads.json`) in Pyodide
  under Node and in CPython, three times each, writing each one's replies for an exact
  comparison.
- The browser side: `voter-app/src/workers/pyEngine.worker.ts`, the fetch hook in
  `voter-app/src/api/pyEngine.ts` (`?engine=pyodide`), and
  `voter-app/scripts/spike-pyodide.mjs`, which times three Lab fiches on both engines.

From `fast_api_voter/`, with the venv:

    python -m pyodide_spike.build_bundle /tmp/pyengine.zip
    python pyodide_spike/native_run.py . pyodide_spike/payloads.json /tmp/native.json
    npm i pyodide@314.0.7   # in a scratch dir, then run node_run.mjs from there:
    node node_run.mjs /tmp/pyengine.zip payloads.json /tmp/pyodide.json
