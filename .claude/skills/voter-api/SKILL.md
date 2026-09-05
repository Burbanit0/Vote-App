---
name: voter-api
description: Conventions for the Vote-App FastAPI backend (fast_api_voter/). Use when adding or changing API endpoints, domain workers, engine utils, or Pydantic schemas — the route→worker→engine layering, the pure-worker contract, where each worker lives, the strict schema/response-model rules, and the blocking mypy/pytest gates.
---

# voter-api — Vote-App backend conventions

The backend is **FastAPI** under `fast_api_voter/` (the name is historical — Flask was
retired). Priority order for this project: **rigour of the voting algorithms >
comparative correctness > security > performance**. It is a study project with no real
users, so favour correctness-by-construction and clear algorithms over hardening.

## Layering (never short-circuit it)

```
api/routes/*          thin HTTP layer: parse request → call worker → return (body, status)
   ↓
api/domain/**         domain WORKERS — pure functions `data: dict -> (body, http_status)`
   ↓                  NO DB coupling, NO FastAPI objects inside a worker
api/engine/utils/*    reusable compute (voting rules, metrics, sampling, paradoxes)
```

A route does almost nothing: validate with a Pydantic schema, hand the dict to a worker,
attach the `response_model`. All real logic lives in a worker; all reusable math lives in
`engine/utils`. **Reuse an engine util before writing new math** — most primitives
(Condorcet, Borda, IRV, Schulze, ranks, sampling, Gini, d'Hondt, agreement) already exist.

## Where a new worker goes (do NOT add back to the monolith)

The former 7.5k-line `workers.py` was decomposed. Put a new election worker in the module
that matches its concern; never grow `workers.py` back:

- `_electorate.py` — shared electorate builders (`_build_base_electorate`, …)
- `_helpers.py` — generic helpers (`gini`, `dhondt`, `inter_method_agreement`, …)
- `workers.py` — **core** simulation only (divergence, campaign, combined, pipeline,
  coalition, districts, primary)
- `workers_playground.py` — profile-simulate, assembly, scorecard, the Lab frontiers
- `workers_mechanisms.py` — adaptive, replay, jury, abstention, STV, gerrymander, multiwinner
- `workers_behavioral.py` — cascade, biases, liquid democracy, NOTA, fatigue, …
- `workers_advanced.py` — turnout, compulsory, sortition, deliberation, power indices
- `workers_dynamics.py` — Hotelling, polarization, quadratic funding, affective

Re-export the worker from `api/domain/election/__init__.py` (the single namespace the
routes import from).

## Schemas — the request contract is strict

- Request schemas: Pydantic with **`extra="forbid"`** (unknown keys are a 422 — intentional).
- Response: define a **`response_model`** and tighten it; the tighten-then-drop-casts pattern
  is established (every `/api/v2` + `/api/v1` endpoint is typed end-to-end).
- **Pydantic-None pitfall:** a field typed non-optional with a `None` default still validates
  `None` through — type the field `Optional[...]` (or give a real default) when `None` is
  genuinely allowed, don't rely on the annotation alone.

## Blocking gates (run from `fast_api_voter/` before every commit)

```bash
python -m pytest                                   # tests + coverage (gate 30% min; actual ~90%)
python -m mypy api/ --config-file mypy.ini         # BLOCKING — api/ is strict-clean, keep it so
```

- **mypy is strict-clean with an empty deferred-ignore list.** Annotate new code. For a
  genuinely-untyped third-party surface (fastapi-users, authlib, python-socketio, numpy edge
  cases) use a **targeted `# type: ignore[code]` at the call site** — never a module-wide
  override.
- `flake8 --config=.flake8 fast_api_voter` is non-blocking (the code uses column-aligned
  style flake8 dislikes). `bandit` gates in CI; `pip-audit` stays informational on purpose.
- Run: `uvicorn api.main:app --port 4434` (the FastAPI instance is `fastapi_app`; `app` is the
  socket.io ASGI wrapper). Or `npm run dev` from the repo root for backend + frontend together.

## Recipe — add an endpoint

1. **Schema** in `api/schemas/*` — request (`extra="forbid"`) + a response model.
2. **Worker** in the matching `workers_*.py` — pure `data: dict -> (body, status)`; reuse
   `engine/utils`; re-export from `domain/election/__init__.py`.
3. **Route** in `api/routes/*` — validate → call worker → `response_model`, mounted on `/api/v2`.
4. **Test** in the matching `tests/` module; keep coverage up.
5. Green `pytest` + **`mypy`** before committing.

## Keep client/server algorithms in sync

Some voting math is **mirrored client-side** (`voter-app/src/lib/playgroundVoting.ts`,
`scorecard.ts`, `campaignTimeline.ts`) so the playground/campaign pages render instantly
without a round-trip. If you change a rule's behaviour on the backend, check whether the
frontend mirror needs the same change so both surfaces agree.
