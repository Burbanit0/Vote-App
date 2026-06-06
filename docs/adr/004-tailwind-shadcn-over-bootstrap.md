# ADR 004 — Tailwind + shadcn/ui over Bootstrap

**Status:** Accepted (Phase 6, 2026-06)

## Context

The UI was Bootstrap 5 + react-bootstrap across 134 files. react-bootstrap added a
runtime dependency and a component API we did not control, and theming went through
`var(--bs-*)` overrides rather than a design-token system.

## Decision

Migrate to **Tailwind v4 + hand-written shadcn-style primitives** in
`src/components/ui/`. We own every primitive (button, card, grid, form-controls,
modal, tabs, accordion, dropdown, toast, pagination, navbar, …); several replicate
the react-bootstrap compound API (e.g. `Modal.Header`, `Accordion.Item`) so the
migration was largely an import-swap. `bootstrap` + `react-bootstrap` were removed.

## Consequences

- During migration Bootstrap + Tailwind **coexisted** via CSS cascade layers
  (`@layer bootstrap, …, utilities`) so Tailwind won collisions on migrated
  components while un-migrated pages were untouched; preflight stayed off until the end.
- Final state: full `@import "tailwindcss"` (preflight on). Legacy `var(--bs-*)`
  inline styles still resolve via vars redefined in `tailwind.css`.
- The grid (`Container/Row/Col`) reimplements Bootstrap's 12-col flex grid; `Col`
  width classes are literal strings so Tailwind's scanner emits them.
- Design tokens live as CSS vars in `:root` + `[data-bs-theme='dark']`.
