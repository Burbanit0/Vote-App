# EXP-023 — Pyodide in a Web Worker vs the Fly container: where the engine runs once hosted

- **Date**: 2026-10-10 · **Status**: open, for the owner's decision (PLAN_BEYOND_CI W6) ·
  **Real cost**: about two hours in one session; the spike is the branch
  `spike/pyodide-hosting` (commit `c735ca57`, not for merging) · **Token cost**: not
  measured
- **Verdict in one sentence**: the backend engine runs unchanged in Pyodide, with the same
  results, at a one-time download of about 11 MB, ~2 s of startup per visit, and 1.3–2×
  the native compute time; that removes the one-machine ceiling that the Fly container
  hits with a class.

## Starting hypothesis

There is no hosted instance, and the teacher trial is a projector demo because
hands-on use waits for W6 (D10). The plan asks whether the non-Polity engine can run in
the visitor's browser (Pyodide, in a Web Worker) for 2–3 Lab fiches, compared with the
container on Fly as `PLAN_SURFACE_EXTERIEURE` §2.A and §2.D leave it.

## Protocol

- **The fiches:** 51 of the 63 Lab fiches call the backend, and every route is the same
  three layers: a pydantic request model, a domain worker taking a dict, and a response
  model. Three were ported:
  - **Polis** (`/tech/polis`), numpy only;
  - **STV** (`/election/stv`), cheap, on the shared electorate path;
  - **Polarization** (`/election/polarization`), 75 runs of `compare_all_methods`.
- **The worker:**
  - **Runtime:** Pyodide 314.0.7 (Python 3.14.2, numpy 2.4.6, pydantic 2.12.5) from the
    jsDelivr CDN.
  - **Engine:** a 351 KB bundle of `api/`, without its web, socket, polity and test layers,
    plus structlog.
  - **Dispatch:** `pyodide_spike.handle()` runs each route as FastAPI does: request model,
    worker, response model.
  - **Wiring:** a `fetch` hook on the API client sends the three paths to the worker when
    the URL has `?engine=pyodide`.
- **Same results?** The same dispatcher ran in CPython (the backend's venv: numpy 2.5.3,
  pydantic 2.13.5) and in Pyodide under Node, on the same payloads. The replies were
  compared value by value.
- **Timings:** `voter-app/scripts/spike-pyodide.mjs` opens each fiche on a production
  build, in a fresh browser context per engine, and runs it twice.

## What it found

**It runs, with the same results.**
- **STV and Polarization:** the same values. The only differences are a few numbers
  written `1` on one side and `1.0` on the other, which are equal once parsed.
- **Polis:** the second PCA axis comes out mirrored (303 values, `y` against `−y`). That is
  a backend defect, not Pyodide's. `numpy.linalg.svd` leaves each axis's sign to the
  LAPACK build, so the backend's Polis map can already flip between machines. A sign
  convention in `_pca_2d` fixes it (scikit-learn's `svd_flip`).

**What a visitor pays** (desktop, local network):

| | Backend | Pyodide |
|---|---|---|
| First visit, downloaded | 0.6 MB | 11.9 MB (Pyodide 6.0, numpy 2.9, pydantic 1.8, engine 0.35) |
| Startup per visit, from the HTTP cache | — | ~2 s (core 0.9–1.1 s, packages 0.2 s, engine import 0.8 s) |
| Polis, warm | 16 ms | 20 ms |
| STV, warm (5 candidates, Node and CPython) | 16 ms | 30–35 ms |
| Polarization, warm | 1.03 s | 1.65 s |
| Memory | server | 54 MB of wasm heap after the three routes |

scipy is not needed: only Polity imports it. It would have added 13.9 MB.

**The Fly side, for comparison** (`fly.toml`, EXP-007 via §2.D): one `shared-cpu-1x`
machine with 512 MB, scaling to zero. It saturates near 1.0–1.3 requests per second, and
at 8 simultaneous users a call takes 25–30 s, with no error shown. A class of 25 opening
the same fiche is past that ceiling. Pyodide has no shared ceiling: each device computes
its own.

**What a full port would still need:**
- **Every route:** a table line each, since all follow the same pattern.
- **The Lab page's own calls:** the page always calls `/election/profile-simulate`, plus
  `/election/assembly` and `/election/assembly-scorecard` in Assemblée mode. Same
  closure, but without them the page still needs a server.
- **The Monte Carlo fiche:** it streams over Socket.IO, and its fallback uses a thread
  pool (`simulations/advanced.py:73`), which Pyodide cannot start.
- **Polity's explorer:** it reads run files from the server, so it would need a static
  export.
- **Keeping both runtimes in step:** a CI check running the routes under Pyodide,
  because its numpy and pydantic lag the backend's by a minor version.

**Found on the way:**
- **The plan's claim was wrong.** It said the modules "import only numpy, scipy,
  pydantic and the stdlib". In fact they need numpy and structlog; pydantic only for the
  schemas; scipy not at all.
- **The STV fiche fails on the default electorate.** Its seat count starts at 3, while
  the slider stops at 2 for three candidates, and the backend refuses 3 seats with three
  candidates.

## What it cost

The spike took about two hours. A full port would cost the work listed above, and keeping
it would cost a second runtime to test against.

**Not measured:**
- **Real phones and iOS Safari.** CPU throttling through the page's DevTools session
  slows only the page's main thread, not the worker. The worker's compute on a phone is
  an estimate: the plan's 4× puts Polarization near 6–7 s.
- **A school's network.** 25 devices loading 11 MB at once is about 280 MB through one
  connection on the first visit.
- **Long sessions.** Memory was only read after three calls.

## Verdict and why

**The owner decides** (W6: "a one-page memo, and the owner decides").

**My recommendation** for the use W6 serves, a class working hands-on, is **static
hosting with the engine in Pyodide.**
- **For it:**
  - it removes the one-machine ceiling, and the server's abuse surface with it (§2.A,
    §2.D);
  - it needs static hosting only, with no server to pay for or watch.
- **Against it:**
  - one 11 MB download per device;
  - about 2 s to start on each visit;
  - slower compute on phones.

**If yes,** the next steps are, in order:
1. the dispatcher for every route, and the Lab page's own calls;
2. a CI check running the routes under Pyodide;
3. the Monte Carlo without threads;
4. a real-phone measurement before the teacher trial.

**If the Fly container instead,** §2.D's "busy" state is the minimum, and a load test at
class size has to come before the trial.

## What I take from it

- **Same results, compared value by value.** Checking that the two runtimes return equal
  values found a sign flip that a "does it render" test would have missed. It is a
  backend defect that any change of machine could expose.
- **Read the import closure, not the requirements file.** scipy was in the plan's list
  and in the lockfile, but no ported path imports it, and it was half of the download.
