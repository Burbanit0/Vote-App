# Architecture Decision Records

Concise records of the load-bearing decisions made during the Vote Lab strategic
refactor (Phases 0–7, see [`STRATEGIC_REFACTOR_PLAN.md`](../../STRATEGIC_REFACTOR_PLAN.md)).
Each ADR is one decision: its context, the choice, and the consequences we accepted.

| # | Decision | Status |
|---|---|---|
| [001](001-fastapi-over-flask.md) | FastAPI over Flask | Accepted |
| [002](002-pydantic-source-of-truth.md) | Pydantic as the contract source of truth | Accepted |
| [003](003-tanstack-query-zustand.md) | TanStack Query + Zustand for client data/state | Accepted |
| [004](004-tailwind-shadcn-over-bootstrap.md) | Tailwind + shadcn/ui over Bootstrap | Accepted |
| [005](005-recharts-only.md) | Recharts as the only chart library | Accepted |
| [006](006-strangler-fig.md) | Strangler-fig migration (not big-bang) | Accepted |
| [007](007-layered-backend.md) | Layered backend (routes → domain → engine) | Accepted |
| [008](008-localstorage-versioning.md) | Versioned localStorage via Zustand persist | Accepted |
| [009](009-i18n-namespacing.md) | i18next with lazy-loaded language bundles | Accepted |
| [010](010-observability.md) | Sentry + structured logging | Accepted |
