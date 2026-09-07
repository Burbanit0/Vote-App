# voter-app — Vote Lab frontend

React 19 + TypeScript + Vite + Tailwind v4 frontend for Vote Lab. See the
[repository README](../README.md) for the product overview and
[CLAUDE.md](../CLAUDE.md) for architecture and contributor conventions.

## Setup

```bash
npm install
```

## Available scripts

Run from this directory (`voter-app/`):

| Script | What it does |
|---|---|
| `npm start` | Vite dev server (`http://localhost:3000`), proxies `/api` and `/socket.io` to the backend on `:4434` |
| `npm run build` | `tsc --noEmit && vite build` — production bundle in `build/` |
| `npm run preview` | Serve the production build locally |
| `npm test` | Vitest unit tests, single run (`npm run test:watch` for watch mode, `npm run test:coverage` for coverage) |
| `npm run lint` | ESLint over `.js/.jsx/.ts/.tsx` — 0 errors is the CI gate |
| `npm run test:e2e` | Playwright end-to-end suite (Chromium + Firefox); needs the backend running on `:4434` |
| `npm run test:a11y` | axe-core accessibility checks only |
| `npm run gen:api` | Regenerate `src/api/types.gen.ts` from the backend's OpenAPI schema |
| `npm run knip` | Unused files/exports/dependencies report |

From the repository root, `npm run dev` starts the FastAPI backend and this
frontend together.

## Learn more

- Product overview, stack, routes, deploy: [../README.md](../README.md)
- Agent/contributor conventions, the gate commands, the dual voting engine, the
  playground architecture: [../CLAUDE.md](../CLAUDE.md)
