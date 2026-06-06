# ADR 003 — TanStack Query + Zustand for client data/state

**Status:** Accepted (Phase 5, 2026-05)

## Context

~60 panels did direct `axios` calls with copy-pasted `useState(data/loading/error)`
+ `useEffect` boilerplate (no shared cache, dedup, or invalidation), and client
state lived in **8 React Contexts** that re-rendered in cascades.

## Decision

- **Server state → TanStack Query v5 + openapi-fetch** (`src/api/client.ts` typed
  against `types.gen.ts`; `$api.useQuery/useMutation`). A middleware attaches the JWT.
  **axios fully removed.**
- **Client state → 4 Zustand stores** (`useAuthStore`, `useUIStore`, `useLabStore`,
  `useElectionStore`), consolidating the 8 contexts. Stores self-hydrate from
  localStorage at module init (no Providers). `src/context/` was deleted.

## Consequences

- Shared cache/dedup/invalidation for free; panels shrink to a `useMutation` call.
- Convenience hooks select fields **one at a time** (`useStore(s => s.x)`) — never
  return a fresh composite object from one selector (breaks snapshot caching).
- The openapi-fetch middleware reads the token from `useAuthStore`.
- WebSocket Monte Carlo streaming stays outside TanStack (it's a socket, not a query).
