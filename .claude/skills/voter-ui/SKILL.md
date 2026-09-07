---
name: voter-ui
description: Conventions for the Vote-App React/TypeScript frontend (voter-app/), especially the Playground (5-moment instrument) and Laboratoire pages. Use when building or changing components, charts, or the central visualisations — covers the SVG-native vs Recharts split, the form-lock performance invariant, lazy + hover-prefetch, the "don't denature the playground" rule, the Tailwind v4 + shadcn system, i18n, and the gates. Pair with the general `frontend-design` skill for visual direction.
---

# voter-ui — Vote-App frontend conventions

Stack: **React 19 + TypeScript + Vite + Tailwind v4 + shadcn**. Data layer: **TanStack Query
+ openapi-fetch** (`src/api/client.ts`, typed on `src/api/types.gen.ts`). State: **Zustand**
stores in `src/stores/` for global app state; the Playground's own state is the exception —
it flows through a dedicated React Context (`usePlaygroundCtx`, see below), not a store.
Services in `src/services/*` wrap endpoints.
For *visual* direction (palette, type, avoiding templated looks) use the **`frontend-design`**
skill; this skill is about *this app's* structure and its non-obvious traps.

## Two visual tiers — pick the right one

- **Central canvases are raw SVG**, hand-written for instant, dependency-free render:
  `LeaderCanvas`, `ParliamentCanvas`, `CampaignTimeline`, the scorecard, win-region maps.
  New in-place visualisation (a sparkline, a band, an overlay) → **native SVG**, like the
  campaign "value of the result" trajectory. Do NOT reach for Recharts here.
- **Recharts only inside `Collapsible`-gated exploration panels**, never in the always-mounted
  central canvases. It is heavy and isolated as its **own manual chunk**
  (`vite.config.ts` `manualChunks`) — idle-prefetched once on the playground
  (`PlaygroundController.tsx`), and per-fiche hover/focus-prefetched on the Laboratoire (see
  the form-lock invariant below for the difference).

## The form-lock invariant (the #1 thing not to break)

Tests enforce it (`PlaygroundPage.test.tsx`): **at first paint, only the `*-toggle`s are in
the DOM** — no heavy panel is mounted. Rules:

- Heavy panels mount **only when their `Collapsible` opens** (`{open && <div>{children}</div>}`);
  the default lens (`winner`) does **zero extra compute**. Adding a panel must not mount
  anything at first paint or add a network fetch there.
- Playground moment panels themselves are plain, eagerly-bundled components — there is no
  per-panel code-splitting inside the Playground (that pattern was retired along with the old
  `Leaf` component). Recharts is still isolated as its **own manual chunk**
  (`vite.config.ts` `manualChunks`), warmed once via an idle-callback prefetch
  (`requestIdleCallback` → `import('recharts')`) in `PlaygroundController.tsx` rather than a
  per-panel hover trigger.
- **Lazy + hover-prefetch** is the Laboratoire's pattern, not the Playground's: each fiche in
  `components/lab/labCatalog.tsx` is `lazyWithPreload(() => import(...))`, and its chip wires
  `onMouseEnter`/`onFocus={preload}` so hovering warms the chunk before the click. Use it for
  every new Laboratoire fiche.
- Give every testable element a stable `data-testid`; the form-lock + reveal tests key off them.

## "Don't denature the playground" — add depth in place

The Playground (`src/pages/PlaygroundPage.tsx` + `components/playground/*` + `lib/playground*.ts`)
is one shared electorate with two questions (Dirigeant vs Assemblée), every assumption a knob.
It is a **5-moment instrument** — Électorat → Méthode → Stratégie → Campagne → Bilan
(`components/playground/moments/*Moment.tsx`). **All state and derivations live in
`PlaygroundController.tsx`** and flow through one context (`usePlaygroundCtx`); moment panels
and the instrument are thin consumers. When adding voting-theory features:

- A **new method** is "free" — add a `Rule` in `lib/playgroundVoting.ts` (type + `RULE_LABELS`
  + a client `winRegion`) and it auto-renders in the win-region map, Scorecard, Pareto, and
  gets its ⓘ `MethodInfo`. Mirror it on the backend (`engine/utils/simulation_*`).
- A **new effect** is a **lens** on the central map (a small `Vue`/lens selector), not a new
  expanding drawer. Effects must be **visible/animated in the central graphs** and combine with
  the existing knobs (rule, drag a candidate, the campaign scrubber).
- **Advanced / heavy content goes to `/laboratoire`** (`src/pages/LaboratoirePage.tsx`), not the
  playground. The 2026 simplification pass split the surface in two: the playground stays the
  clean < 2-min thesis walk (essential controls only), and the Laboratoire gathers the deep
  explorations (paradoxes, theory anchors, behavioural realism, the +12 exotic methods) by theme.
  It reads the **same** electorate via `usePlaygroundCtx` — configure in the playground, explore
  in the lab, no double state. Campaign/temporal dynamics are now the **Campagne moment** inside
  the rail (`/campagne` redirects to `/playground`; `CampaignDynamicsPage` is gone).

## Design system & i18n

- Tailwind v4 (preflight on; Bootstrap retired). shadcn primitives are **hand-written** in
  `src/components/ui/` (Card, Badge, Button, …) — reuse them, match their idioms.
- Bilingual **fr/en** via i18next (lazy-loaded, persisted). User-facing copy is primarily
  French. General-namespace keys go in `src/i18n/locales/{fr,en}.ts`; Playground/Laboratoire
  copy uses the `playground` namespace (`useTranslation('playground')`) and belongs in
  `src/i18n/locales/playground.{fr,en}.ts` instead — `playground.fr.ts` is the source of
  truth and `playground.en.ts` must mirror it key-for-key (tsc enforces this).

## Gates (run from `voter-app/`)

```bash
npx tsc --noEmit     # BLOCKING
npm run lint         # eslint — BLOCKING in CI (frontend-ci runs it with 0 errors expected)
npm test             # Vitest — includes the form-lock tests; keep them green
npm run build        # tsc + vite build (confirm Recharts stays its own chunk)
```

- **Both tsc and lint block** (frontend-ci-cd-pipeline.yml runs `npm run lint` with no
  continue-on-error; 0 errors is the gate). Run `npx prettier --write` on files you touch
  (multi-prop JSX gets reformatted; expect it).
- Regenerate API types after a backend contract change: `npm run gen:api`.
- Run the app: `npm start` (Vite, API base `:4434`), or `npm run dev` from the repo root for
  backend + frontend together.

## Keep client/server algorithms in sync

`lib/playgroundVoting.ts` / `scorecard.ts` / `campaignTimeline.ts` mirror backend voting math
so the central views compute instantly. If you change a rule client-side, change it on the
backend (and vice-versa) so both surfaces agree — see the `voter-api` skill.
