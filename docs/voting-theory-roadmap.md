# Prompt — Voting-theory coverage gaps (tiered implementation spec)

> Paste this as the opening prompt of a Claude Code session in the Vote Lab repo.
> It is self-contained: it states the mission, the conventions to follow, and a
> tiered backlog of voting-theory topics the app does **not** yet cover. Implement
> top-down (Tier 1 first); ship each item as its own green, mergeable change.

---

## Role & context

You are extending **Vote Lab**, a personal voting-theory research/education app whose
thesis is: **the choice of voting method changes the winner**, and a good method
**minimizes the incentive to vote strategically**. Every feature should make one of
those two ideas visible and interactive.

**Stack (already in place — follow it, don't reinvent):**
- **Backend** — FastAPI, layered: `routes/` (thin HTTP) → `domain/` (pure workers,
  `(data: dict) -> (body, status)`, zero FastAPI/DB imports) → `engine/` (the 17
  voting methods + metrics, in `api/engine/utils/`). Pydantic schemas in `api/schemas/`.
  Tests in `api/tests/` (pytest + httpx). Run: `FLASK_ENV=testing python -m pytest`;
  `python -m mypy api/ --ignore-missing-imports`.
- **Frontend** — React 19 + TS + **Tailwind v4 + shadcn primitives** in
  `src/components/ui/`. Panels call `$api.useMutation('post', '/api/v2/.../slug')`
  (typed by `src/api/types.gen.ts`, regenerated via `npm run gen:api`). Shared panels
  live in `src/components/shared/`. The hub is `src/pages/ElectionLabPage.tsx`. Tests:
  Vitest, mock `../../../api/client`, render under `makeTestQueryClient()`.

**Recipe for a new backend endpoint** (from CLAUDE.md):
1. pure worker `(data: dict) -> (body, status)` in `api/domain/election/…`
2. Pydantic request/response schema in `api/schemas/`
3. thin route in `api/routes/election.py` with a `response_model`
4. pytest in `api/tests/`. Keep `domain/` + `engine/` framework-free.

**Recipe for a new Lab tab** (in `ElectionLabPage.tsx`):
1. import the panel; add an entry to the `TABS` array `{ key, icon, label: t('electionLab.tabX'), group }`
2. add `key: <Panel/>` to the `tabContent` map
3. add `electionLab.tabX` to `src/i18n/locales/en.ts` **and** `fr.ts`
4. **Create a new tab group `pathology`** in `GROUP_META` (alongside `see` / `perturb`
   / `variant`) for the Tier-1 items below — label e.g. "Pathologies" / "Paradoxes",
   colour `#dc3545` (red).

**Per item:** worker + schema + route + pytest (backend), panel + Lab tab + i18n +
Vitest (frontend). Verify each: backend `pytest` + `mypy`; frontend `tsc --noEmit`,
the panel's Vitest file, `npm run build`. Commit per item on a `feat/*` branch.

---

## TIER 1 — Pathology demonstrators (flagship, build first)

These are the famous "the method betrays the voter" results. Each is a new tab in the
new **`pathology`** group. The app currently only *names* these in quiz/criterion
copy — none is demonstrated interactively.

### T1.1 — Monotonicity paradox (non-monotonicity of IRV/STV)  ★ flagship
- **Theory:** under IRV/STV, ranking a candidate *higher* can make them *lose* (or
  ranking lower can make them win) — the monotonicity criterion fails. Real cases:
  Burlington VT 2009, Alaska 2022 (Palin/Begich/Peltola).
- **Backend** `POST /api/v2/election/monotonicity`: given an electorate (reuse the
  standard config: candidates x/y, num_voters, ideology, seed), either (a) **search**
  random/perturbed ballot profiles for a non-monotone instance, or (b) fall back to a
  curated 3-candidate pedagogical profile. Return: the base IRV result + round-by-round
  tallies, the "raise the winner on k ballots" modified profile, the new IRV result,
  and a boolean `paradox_found` with the bloc size moved.
- **Frontend panel:** show the base IRV elimination rounds; a slider/button "promote
  candidate X on N ballots"; render the *new* elimination rounds side by side; highlight
  the flipped winner. One-line takeaway: "honest support hurt the candidate."
- **Acceptance:** a reproducible profile where promoting the winner flips the result;
  works for the curated example with no search needed.

### T1.2 — No-show / participation paradox
- **Theory:** a voter (or bloc) is strictly **better off abstaining** than voting
  sincerely. Moulin (1988): every Condorcet-consistent method fails participation with
  ≥4 candidates.
- **Backend** `POST /api/v2/election/no-show`: find (search or curated) a bloc whose
  sincere participation yields outcome A but whose abstention yields a *more preferred*
  outcome B under a chosen Condorcet method (Schulze/minimax). Return both outcomes, the
  bloc's preference order, and `paradox_found`.
- **Frontend:** toggle "bloc votes / bloc abstains" → winner flips to something the bloc
  prefers; annotate why. Distinguish clearly from the existing *abstention* tab (that is
  demobilization; this is "your sincere vote backfires").
- **Acceptance:** a curated ≥4-candidate Condorcet example where abstention helps the bloc.

### T1.3 — Spoiler effect / clone independence (vote-splitting)
- **Theory:** adding a candidate similar to an existing one ("clone") splits the vote
  and flips the winner under plurality, while clone-independent methods (Condorcet,
  approval, STV, Ranked Pairs) are unaffected. Real cases: Nader 2000, Perot 1992.
- **Backend** `POST /api/v2/election/spoiler`: take the electorate, inject a clone of a
  chosen candidate (near-identical x/y), and return the winner **per method** before vs
  after the clone, flagging which methods changed (`clone_dependent`) vs held
  (`clone_independent`).
- **Frontend:** a "drop a clone next to candidate X" control on the ideology map; a
  before/after winner table across all 17 methods, colour-coded by whether the clone
  changed the result. This is the thesis ("method changes the winner") in one screen.
- **Acceptance:** plurality flips, Condorcet/approval/STV hold, on the same electorate.

---

## TIER 2 — Reference & modern frontier

### T2.1 — Criteria-compliance matrix (high reference value)
- A single sortable table: **17 methods × ~12 criteria** — Condorcet winner, Condorcet
  loser, majority, monotonicity, participation, IIA, clone-independence, reversal
  symmetry, later-no-harm, consistency/reinforcement, Pareto, resolvability. Cells are
  ✓/✗ from the established literature (static data is fine for the matrix), and **each ✗
  is clickable** to generate/show a concrete counterexample (reuse the Tier-1 workers
  where they exist: monotonicity, participation, clone). Lives in `see` or a new
  `reference` group. Make the static criteria table a typed data module so it's auditable.

### T2.2 — Method of Equal Shares / participatory-budgeting proportionality
- **Theory:** PB selects a set of projects under a budget; the **Method of Equal Shares
  (MES)** gives each voter an equal share of budget and yields proportional, fair
  outcomes (used in Paris, Polish cities). Contrast with greedy/utilitarian knapsack.
- **Backend** `POST /api/v2/election/participatory-budget`: inputs = projects (cost +
  approvals), total budget; outputs = funded set under MES vs greedy, plus a fairness/
  proportionality metric. Reuse the quadratic-funding plumbing where sensible.
- **Frontend:** project list with costs/approvals + budget slider; show which projects
  each rule funds and why MES is "more proportional."

### T2.3 — Justified Representation (JR / PJR / EJR) for multi-winner approval
- **Theory:** axioms for multi-winner approval committees (Aziz, Sánchez-Fernández,
  Brill et al.). You already have **Phragmén** — add a checker that, for a committee,
  reports whether JR / PJR / EJR hold, and contrasts a committee from a proportional
  rule vs a utilitarian one.
- **Backend** `POST /api/v2/election/justified-representation`: inputs = approval ballots
  + committee size; outputs = committees from a couple of rules + per-axiom pass/fail +
  the violating cohesive group when it fails.

---

## TIER 3 — Spatial-model depth & smaller gaps (nice-to-have)

- **Directional theory (Rabinowitz–Macdonald) vs proximity:** the spatial model is
  currently proximity-only; add a directional utility mode and let users compare which
  candidate wins under each behavioural assumption (+ optional **valence** term).
- **May's theorem:** a small interactive showing that for **2** alternatives, simple
  majority is the *unique* rule satisfying anonymity + neutrality + positive
  responsiveness — i.e. why the pathologies above only bite with ≥3 candidates.
- **Apportionment paradoxes:** you compute apportionment already — add the **Alabama**,
  **population**, and **new-states** paradox demonstrations (Hamilton's method), and
  contrast with divisor methods (Jefferson/D'Hondt, Webster/Sainte-Laguë).
- **Single-crossing / value-restriction** domains as companions to the existing
  single-peaked (Black) coverage.

---

## Sequencing & deliverables

1. **Tier 1 first** (T1.1 → T1.2 → T1.3): add the `pathology` group, ship each tab as a
   separate green commit. T1.1 (monotonicity) is the flagship — do it first.
2. **Tier 2** (T2.1 reference matrix, then T2.2 / T2.3).
3. **Tier 3** opportunistically.

For every item: backend worker+schema+route+pytest, then `npm run gen:api`, then
panel+tab+i18n+Vitest; keep `tsc`, `pytest`, `mypy`, and `npm run build` green; commit
per item; merge `feat/*` → `develop` (`--no-ff`). Do **not** push to `main`.

**Definition of done for the whole effort:** the three Tier-1 pathology tabs live in a
"Pathologies" group, each reproducibly demonstrates its paradox on a curated example,
and the criteria-compliance matrix cross-links to them.
