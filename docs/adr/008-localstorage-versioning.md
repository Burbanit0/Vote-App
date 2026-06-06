# ADR 008 — Versioned localStorage via Zustand persist

**Status:** Accepted (Phase 5, 2026-05)

## Context

Election config, UI preferences, and pinned perturbations are persisted client-side
so a refresh keeps the user's work. With hand-rolled `localStorage` reads, a shape
change could feed stale/incompatible data into the app and crash a panel.

## Decision

Persist client state through the **Zustand stores** that own it. Stores hydrate from
localStorage at module init and expose a `hydrate()` for test isolation. Persisted
slices carry a schema version so a bumped version can migrate or discard old payloads
rather than trusting them blindly.

## Consequences

- One place per concern reads/writes storage (the store), not scattered call sites.
- Tests reset via `useXStore.setState(reset)` in `beforeEach`.
- Recalled persisted state reflects when it was written — version it, validate it, and
  never assume a field that an older build may not have stored.
