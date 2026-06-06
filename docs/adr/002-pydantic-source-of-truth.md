# ADR 002 — Pydantic as the contract source of truth

**Status:** Accepted (Phase 6, 2026-06)

## Context

After moving to FastAPI, request bodies were validated by Pydantic but most routes
returned bare `Dict` passthroughs. The frontend still typed responses with
hand-written interfaces that drifted from reality, kept in sync only by casts
(`as unknown as T`).

## Decision

Give **every** `/api/v2` and `/api/v1` endpoint a precise Pydantic `response_model`
(nested models, not `Dict`). The FastAPI OpenAPI schema is the single contract;
`npm run gen:api` regenerates `src/api/types.gen.ts` from it, and panels consume the
generated types directly (the hand-written interfaces + casts were dropped).

## Consequences

- One source of truth: a backend shape change surfaces as a TypeScript error in the
  frontend after `gen:api`.
- "Tighten then drop": models were re-modelled precisely first, then the casts removed.
- Workers stay pure (`(data: dict) -> (body, status)`); the route layer attaches the
  `response_model`. Pydantic-`None` pitfalls (optional fields) are handled at the route.
- `slowapi`-decorated routes must NOT use `from __future__ import annotations` (it
  breaks body introspection).
