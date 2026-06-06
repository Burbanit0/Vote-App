# ADR 006 — Strangler-fig migration, not big-bang

**Status:** Accepted (Phase 0, 2026-05)

## Context

The refactor touched the backend framework, async DB, the data/state layer, and the
entire UI toolkit. A single big-bang rewrite would have made the app undeployable for
weeks and bundled unrelated risk.

## Decision

Use the **strangler-fig** pattern: stand the new implementation up alongside the old,
migrate surface incrementally, and keep the app deployable at every step. URLs stayed
stable across the backend migration (`/api/v2/*`, `/api/v1/*`) so the frontend was
untouched; the UI migration ran component-by-component with Bootstrap and Tailwind
coexisting (see [ADR 004](004-tailwind-shadcn-over-bootstrap.md)).

## Consequences

- Every phase ended green (typecheck + tests + build) and mergeable.
- Branch strategy `feat/* → develop → main`; large UI work used one long-lived branch
  by explicit choice, accepting merge-divergence risk over partial-UI merges.
- The cost is transient duplication (two stacks live at once) and discipline around
  coexistence shims (cascade layers, compatibility wrappers) that are removed at the end.
