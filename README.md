# Vote Lab

A civic research sandbox for voting theory — demonstrating empirically that **the
choice of voting method changes the winner**, and exploring what happens when
campaign dynamics, blank votes, information asymmetry, and social contagion all act
on the same electorate.

> Full theory reference: [THEORY.md](THEORY.md) · User guide: [GUIDE_UTILISATEUR.md](GUIDE_UTILISATEUR.md)

---

## What it does

Vote Lab is built around **one instrument** — the Playground — where you configure a
complete election and watch it through several lenses at once:

- Run the same ballots through **29 voting methods** and compare who wins
- A **5-moment rail** — Électorat → Méthode → Stratégie → Campagne → Bilan — walks a
  full election from population to verdict, with a **Dirigeant ↔ Assemblée** toggle
  (single-winner vs proportional parliament)
- **Drag candidates** on the ideological map and watch win-zones redraw live; switch
  analytical **lenses** (winner, manipulation, probability, criteria) over the map
- **14 guided stories** replay a specific paradox step by step on the live instrument
  (spoiler effect, monotonicity failure, later-no-harm, blank-vote regimes…)
- Study strategic voting, blank-vote contagion, campaign trajectories, valence, and
  real-election backtests (France 2002, USA 1992, Germany 2021…) as analytical panels
- **Vote yourself** in a real 41-voter election under 5 ballot languages at
  `/a-vous-de-jouer`

The **Laboratoire** (`/laboratoire`) gathers 62 fiches of deeper, on-demand content
(paradoxes, impossibility theorems, alternative governance systems, behavioural
realism) reading the **same election state** as the Playground — configure once,
explore in depth.

---

## Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (uvicorn) — **stateless**, no SQL DB, no auth · Redis (compute cache only) |
| WebSockets | python-socketio (ASGI, Monte Carlo streaming) |
| Frontend | React 19 · TypeScript · React Router v7 · Vite |
| Data/State | TanStack Query + openapi-fetch (typed) · Zustand stores |
| UI | Tailwind v4 + shadcn/ui (hand-written primitives in `src/components/ui/`) |
| Charts | SVG-native (playground) · Recharts · D3 (Voronoi, hexbin) |
| i18n | i18next (FR / EN toggle, persisted, lazy-loaded) |
| PWA | vite-plugin-pwa · Workbox (offline, installable) |
| Tests | Vitest (unit) · Playwright (E2E + axe-core a11y) |
| Type checking | mypy strict on `api/` |
| CI/CD | GitHub Actions (path-based triggers for backend and frontend) |

---

## Quick Start

### Everything at once (one command)

```bash
npm run setup   # once — installs frontend deps + backend Python deps
npm run dev     # backend (uvicorn :4434) + frontend (Vite :3000), colour-prefixed
```

`npm run dev` runs the backend directly with uvicorn. The app is stateless — no
database — so this is the full experience. Ctrl+C once stops both. Run a single side
with `npm run dev:backend` or `npm run dev:frontend`.

**Prerequisites:** [Node.js](https://nodejs.org/) 20+ and
[Python](https://www.python.org/) 3.11+. [Docker](https://www.docker.com/) only if you
want the containerised stack below.

### Docker

```bash
git clone https://github.com/Burbanit0/Vote-App.git
cd Vote-App
cp fast_api_voter/.env.example fast_api_voter/.env   # defaults work locally
cd fast_api_voter && docker-compose up --build       # FastAPI :4434 · Redis :6379 (cache only)
cd ../voter-app && npm install && npm start           # Vite → :3000
```

### Deploy (public — single container)

The root `Dockerfile` builds the frontend and serves it **and** the API from one
FastAPI process, so the whole app ships as a single stateless image (no Redis, no
DB — Redis is an optional cache):

```bash
docker build -t votelab:prod .        # from repo root
docker run -p 4434:4434 votelab:prod  # → http://localhost:4434  (app + API + websockets)
```

**Fly.io** (`fly.toml` included):

```bash
fly launch --no-deploy   # once — claims a unique app name, updates [app] in fly.toml
fly deploy               # builds the Dockerfile and ships it
```

Public URL: `https://<app>.fly.dev`. No env vars are required. The container scales
to zero when idle (free allowance); set `min_machines_running = 1` in `fly.toml` for
an always-warm demo, or `REDIS_URL` if you later add a cache.

---

## Development

### Backend (`fast_api_voter/`)

```bash
python -m pytest api/tests -o addopts="" -q   # unit tests (-o addopts="" skips the coverage gate)
mypy api/                                      # strict, must stay clean
flake8                                         # E9/F errors are gating
```

### Frontend (`voter-app/`)

```bash
npm test                 # Vitest unit tests
npm run test:e2e         # Playwright (Chromium + Firefox)
npm run test:a11y        # axe-core WCAG 2.1 AA audit
npm run build            # tsc --noEmit && vite build (PWA manifest + service worker)
npm run lint             # eslint (0 errors is gating)
```

`ci-local/` is a Dockerised harness that mirrors GitHub CI — run it before opening
PRs when in doubt.

### Analytics (optional)

Anonymous, cookie-less usage measurement via self-hosted Umami — disabled unless
both `VITE_UMAMI_*` vars are set in a production build. Setup, event vocabulary
and privacy posture: [`analytics/README.md`](analytics/README.md).

---

## Routes

The app is anonymous (no accounts), with three real destinations:

| Route | Description |
|---|---|
| `/` | Home — thesis landing, routes into the Playground |
| `/decouvrir` | Two-minute on-ramp for visitors who only know one voting method |
| `/playground` | **The instrument** — 5-moment rail, ideological map + lenses, Dirigeant/Assemblée |
| `/laboratoire` | Everything deeper — theory, paradoxes, mechanisms, systems, behavioural realism (reads the same electorate state as the Playground) |
| `/a-vous-de-jouer` | Vote yourself in a real election under 5 ballot languages |

All retired routes (`/theory`, `/what-if`, `/quiz`, `/quadratic-funding`,
`/tech-democracy`, `/regimes-internationaux`, `/election-lab`, `/campagne`,
`/galerie`, `/scenario-builder`, `/simulation/compare`, old account routes) redirect
to `/playground` or `/laboratoire` — their content was folded into those two. The
former teacher-mode slide export was removed outright (no route, no redirect).

---

## Voting Methods (29)

All 29 rules — majoritarian, positional, 11 Condorcet variants, and cardinal — are
selectable in the Playground and defined in [THEORY.md §2](THEORY.md). Each rule
exists in **two implementations** — a fast client engine
(`voter-app/src/lib/playgroundVoting.ts`) and the authoritative backend engine
(`fast_api_voter/api/engine/utils/`) — kept identical by a golden-fixture parity test.

---

## Blank Vote Rules

| Rule | Effect |
|---|---|
| `symbolic` | Counted but never affects outcome (current French law) |
| `competitive` | Blank is a full candidate — can win |
| `threshold_30` | Election invalidated if blank > 30 % |
| `majority_required` | Winner must beat blank in a pairwise duel |

---

## Public API (`/api/v1/`)

Rate-limited (60 req/min), no authentication.

```
GET  /api/v1/methods           # method list with descriptions
GET  /api/v2/openapi.json      # OpenAPI 3.0 spec
POST /api/v2/election/...      # authoritative election + simulation endpoints
```

The frontend consumes the OpenAPI schema via a typed `openapi-fetch` client
(`npm run gen:api` regenerates `src/api/types.gen.ts`).

---

## Architecture

```
fast_api_voter/api/          # FastAPI backend — stateless (no DB, no auth)
├── main.py                  # FastAPI app + CORS + slowapi + Socket.IO ASGI wrap
├── routes/                  # thin HTTP adapters — election, simulations, theory,
│                            #   tech, export, public (/api/v1), health
├── domain/                  # pure compute workers (0 import FastAPI)
│   ├── election/  simulations/  theory/
├── engine/utils/            # the simulation engine (0 import FastAPI)
│   ├── simulation_ranked_utils.py     # ordinal algorithms
│   ├── simulation_score_utils.py      # score algorithms
│   ├── simulation_multiwinner_utils.py# proportional / parliament
│   ├── simulation_metrics.py          # compare_all_methods(), Bayesian regret
│   ├── campaign_dynamics.py  blank_contagion.py  information_model.py
│   ├── gibbard_satterthwaite.py  quadratic_voting.py  arrow_criteria.py
│   └── demographic_data.py  real_election_data.py  cache.py (Redis)
├── core/ (config, ratelimit)  schemas/  sockets/  tests/

voter-app/src/
├── pages/                   # HomePage, PlaygroundPage, LaboratoirePage, …
├── components/playground/   # the instrument: PlaygroundController (state hub) +
│                            #   moment panels, LeaderCanvas/ParliamentCanvas, lenses
├── lib/                     # pure analytical libs (playgroundVoting, scorecard,
│                            #   sincerity, criteria, campaign, valence…) + parity fixtures
├── stores/                  # Zustand stores
└── services/  hooks/  i18n/
```

See [CLAUDE.md](CLAUDE.md) for the agent-facing map of gates, the dual engine, and
the playground architecture.

---

## Workflow

```
main       ← stable releases (develop → main)
develop    ← integration branch
feat/xxx   ← one branch per step → PR to develop (merged --no-ff)
```

Public repo (MIT). See [CONTRIBUTING.md](CONTRIBUTING.md) and
[SECURITY.md](SECURITY.md).
