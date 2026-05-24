# Vote Lab — Checklist code (architecture & perf)

> Audit du 2026-05-23 (branche `develop` à 6f9ae98).
> Coche au fur et à mesure. Pour les bloquants sécurité / mise en public, voir [PRE_PUBLIC_CHECKLIST.md](PRE_PUBLIC_CHECKLIST.md).
> Les actions sont classées par **impact / effort**, pas par dépendance — tu peux attaquer dans l'ordre qui te plaît.

---

## 🟥 Impact élevé / effort faible (à faire en premier)

### [ ] A1. `React.lazy()` sur les 8 pages lourdes
**Pourquoi** : 0 route lazy actuellement, bundle initial = **2.37 MB** (un seul `index-*.js`). Le visiteur de la HomePage télécharge tout.
**Gain attendu** : bundle initial ÷ 6 (~400 KB).

Dans [voter-app/src/App.tsx](voter-app/src/App.tsx) :

```ts
import React, { Suspense } from 'react';
import { Spinner } from 'react-bootstrap';

// Eager (HomePage, Login, Register, AuthGuard, Navbar — restent eager)
import HomePage from './pages/HomePage';
import Login from './pages/Login';
import Register from './pages/Register';

// Lazy (toutes les pages lourdes)
const ElectionLabPage         = React.lazy(() => import('./pages/ElectionLabPage'));
const TheoryPage              = React.lazy(() => import('./pages/TheoryPage'));
const SimulationComparePage   = React.lazy(() => import('./pages/SimulationComparePage'));
const SimulationPage          = React.lazy(() => import('./pages/SimulationPage'));
const CampaignSimulatorPage   = React.lazy(() => import('./pages/CampaignSimulatorPage'));
const TechDemocracyPage       = React.lazy(() => import('./pages/TechDemocracyPage'));
const QuadraticFundingPage    = React.lazy(() => import('./pages/QuadraticFundingPage'));
const WhatIfPage              = React.lazy(() => import('./pages/WhatIfPage'));
const TeacherPresentationPage = React.lazy(() => import('./pages/TeacherPresentationPage'));
const ScenarioBuilderPage     = React.lazy(() => import('./pages/ScenarioBuilderPage'));
const ScenarioGalleryPage     = React.lazy(() => import('./pages/ScenarioGalleryPage'));
const ConstitutionalCrisisPage = React.lazy(() => import('./pages/ConstitutionalCrisisPage'));
const BlankContagionPage      = React.lazy(() => import('./pages/BlankContagionPage'));
const InternationalRegimesPage = React.lazy(() => import('./pages/InternationalRegimesPage'));
const ApiDocsPage             = React.lazy(() => import('./pages/ApiDocsPage'));
const QuizPage                = React.lazy(() => import('./pages/QuizPage'));
const PartyDynamicsPage       = React.lazy(() => import('./pages/PartyDynamicsPage'));
const SortitionPage           = React.lazy(() => import('./pages/SortitionPage'));

// Wrap <Routes> dans <Suspense>
<Suspense fallback={<div className="text-center py-5"><Spinner /></div>}>
  <Routes>...</Routes>
</Suspense>
```

Et ajouter dans [vite.config.ts](voter-app/vite.config.ts) :

```ts
build: {
  outDir: 'build',
  sourcemap: false,
  rollupOptions: {
    output: {
      manualChunks: {
        recharts: ['recharts'],
        d3:       ['d3-delaunay', 'd3-hexbin', 'd3-force'],
        pdf:      ['jspdf', 'html2canvas'],
        bootstrap: ['react-bootstrap', 'bootstrap'],
      },
    },
  },
},
```

Vérif après build :
```bash
cd voter-app && npm run build
ls -lah build/assets/*.js | sort -k5 -h
```

### [ ] A2. Wrapper `tpool.execute` sur les 34 endpoints compute-bound
**Pourquoi** : actuellement utilisé sur **/simulate uniquement**. Les 34 autres (combined-effects, historical-replay, jury, adaptive, etc.) bloquent l'event loop eventlet pendant tout leur calcul → tous les WebSockets et les autres requêtes sont bloqués.

Créer dans `flask_voter_app/app/utils/decorators.py` :

```python
from functools import wraps
from typing import Callable, Any
from eventlet import tpool
from flask import jsonify, request, current_app, Response

def heavy_endpoint(worker: Callable[[dict], tuple[dict, int]]):
    """Decorator: run a compute-bound worker in a real OS thread via eventlet's
    tpool, so the eventlet event loop stays responsive to WebSockets and
    concurrent HTTP requests. Worker signature: (data: dict) -> (body, status).
    """
    @wraps(worker)
    def wrapped() -> tuple[Response, int]:
        data = request.get_json() or {}
        try:
            body, status = tpool.execute(worker, data)
            return jsonify(body), status
        except Exception:
            current_app.logger.exception(f"{worker.__name__} crashed")
            return jsonify({"error": "Internal error"}), 500
    return wrapped
```

Refactorer les endpoints lourds (modèle) :

```python
# Avant
@election_bp.route("/combined-effects", methods=["POST"])
@sim_limiter.limit("5 per minute")
def combined_effects() -> tuple[Response, int]:
    data = request.get_json() or {}
    # ... 200 lignes de calcul direct ...
    return jsonify(result), 200

# Après
def _combined_effects_worker(data: dict) -> tuple[dict, int]:
    # ... 200 lignes de calcul (extraites telles quelles) ...
    return result, 200

@election_bp.route("/combined-effects", methods=["POST"])
@sim_limiter.limit("5 per minute")
@heavy_endpoint
def combined_effects():
    return _combined_effects_worker
```

Liste des endpoints à passer en `heavy_endpoint` (à faire en plusieurs PR pour rester reviewable) :
- `/combined-effects` (matrice 2³, ~8 simulations)
- `/historical-replay` (N jours × méthodes)
- `/jury` (N runs Monte Carlo)
- `/adaptive` (N rounds itératifs)
- `/campaign-sensitivity`
- `/simulate-pipeline`
- Tous les `/perturb-*` lourds dans `election.py`

### [ ] A3. Centraliser couleurs / layout dans `theme/tokens.ts`
**Pourquoi** : 1 397 codes hex en dur dans `components/` + `pages/`. Couleurs récurrentes détectées : `#6c757d` (180×), `#dc3545` (165×), `#198754` (101×), `#005CAB` (72×), `#0d6efd` (58×). Page widths : `500/680/900/960/1100/1200/1300/1400` éparpillés.

Créer `voter-app/src/theme/tokens.ts` :

```ts
export const COLORS = {
  brand: {
    primary:   '#005CAB',  // bleu Vote Lab
    secondary: '#C8590A',  // orange contraste
    accent:    '#7B2D8B',  // violet (Condorcet, multi-winners)
  },
  party: {
    Green:        '#007A33',
    Liberal:      '#005CAB',
    Conservative: '#C8590A',
    Independent:  '#6c757d',
  },
  status: {
    success: '#198754',
    danger:  '#dc3545',
    warning: '#ffc107',
    info:    '#0dcaf0',
  },
  neutral: {
    50:  '#f8f9fa',
    100: '#e9ecef',
    200: '#dee2e6',
    400: '#adb5bd',
    600: '#6c757d',
    700: '#495057',
    900: '#212529',
  },
} as const;

export const LAYOUT = {
  pageNarrow: 680,    // forms, quiz, OAuth callback
  pageMedium: 960,    // articles, theory pages, API docs
  pageWide:   1200,   // dashboards, gallery
  pageFull:   1400,   // Lab, Simulator
} as const;

export const SPACING = {
  xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32,
} as const;
```

Optionnel : créer un `<PageContainer variant="narrow|medium|wide|full">` dans `components/shared/ui/` pour remplacer les `<Container style={{ maxWidth: ... }}>`.

Lint anti-couleurs en dur (optionnel) :
```bash
cd voter-app && npm i -D eslint-plugin-no-hardcoded-colors
# puis ajouter la règle dans .eslintrc
```

---

## 🟧 Impact élevé / effort moyen

### [ ] B1. Cache Redis sur `/simulate` et endpoints déterministes
**Pourquoi** : Redis instancié dans `app/__init__.py` mais **jamais utilisé** (`grep redis_client` → 1 résultat = l'instanciation). Or `/simulate(config)` est déterministe (même seed = même résultat) ⇒ candidats parfaits pour caching.
**Gain attendu** : 200-500 ms → 5-20 ms sur requêtes répétées du même utilisateur.

Créer `flask_voter_app/app/utils/cache.py` :

```python
import hashlib
import json
from functools import wraps
from typing import Callable, Any
from flask import current_app
from app import redis_client

def cache_result(prefix: str, ttl_seconds: int = 3600):
    """Cache the (body, status) tuple of a worker by hash of its input data.
    Use on deterministic compute workers, AFTER tpool wrapping if applicable.
    """
    def deco(worker: Callable[[dict], tuple[dict, int]]):
        @wraps(worker)
        def wrapped(data: dict) -> tuple[dict, int]:
            key = f"{prefix}:{hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()}"
            try:
                cached = redis_client.get(key)
                if cached:
                    return json.loads(cached), 200
            except Exception:
                current_app.logger.warning("redis read failed", exc_info=True)

            body, status = worker(data)

            if status == 200:
                try:
                    redis_client.setex(key, ttl_seconds, json.dumps(body))
                except Exception:
                    current_app.logger.warning("redis write failed", exc_info=True)
            return body, status
        return wrapped
    return deco
```

Usage :

```python
@cache_result("election:simulate", ttl_seconds=3600)
def _simulate_worker(data: dict) -> tuple[dict, int]:
    # ... existing logic ...
    return body, status
```

Candidats au caching (tous déterministes) :
- `/simulate`
- `/combined-effects`
- `/divergence`
- `/historical-replay` (avec date dans la clé)
- `/jury` (si seed est dans la requête)

À NE PAS cacher : tout endpoint où le résultat dépend du `time.time()` ou d'un random non-seedé.

### [ ] B2. Centraliser data-fetching — `useApi` ou TanStack Query
**Pourquoi** : 85 fichiers appellent `axios` directement, **49 panels** réimplémentent leur propre `{loading, error}` state. Énorme duplication.

**Option A — `useApi` léger** (1 PR, pas de dépendance) :

```ts
// voter-app/src/hooks/useApi.ts
import { useCallback, useEffect, useState } from 'react';

interface UseApiResult<T> {
  data:     T | null;
  loading:  boolean;
  error:    string | null;
  refetch:  () => void;
}

/**
 * Generic data-fetching hook with loading/error/refetch state.
 * Pass `args=null` to skip the fetch.
 *
 *   const { data, loading, error } = useApi(getAbstention, params, [config]);
 */
export function useApi<T, A>(
  fetcher: (args: A) => Promise<T>,
  args: A | null,
  deps: unknown[] = []
): UseApiResult<T> {
  const [data,    setData]    = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState<string | null>(null);
  const [tick,    setTick]    = useState(0);

  useEffect(() => {
    if (args === null) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetcher(args)
      .then((d) => { if (!cancelled) setData(d); })
      .catch((e) => { if (!cancelled) setError(e?.message ?? 'Unknown error'); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);

  const refetch = useCallback(() => setTick((t) => t + 1), []);
  return { data, loading, error, refetch };
}
```

**Option B — TanStack Query** (recommandé long terme) :

```bash
cd voter-app && npm i @tanstack/react-query
```

Avantages massifs : caching automatique, deduplication des requêtes en vol, stale-while-revalidate, retries, devtools. Couvre 80 % des cas d'usage actuels.

Migration progressive : encapsuler `axios.post(...)` derrière `useQuery` panel par panel.

### [ ] B3. Éclater `election.py` (7 070 lignes, 35 routes, 130 fonctions) en sous-blueprints
**Pourquoi** : god file. Aucun contributeur ne s'y retrouve. 7 000 lignes hétérogènes (perturbations, systèmes électoraux, dynamiques, etc.).

Structure cible :

```
app/routes/election/
├── __init__.py            # election_bp = Blueprint(...); register sub-blueprints
├── core.py                # /simulate, /simulate-pipeline, /divergence, /interpret
├── perturbations.py       # /abstention, /cascade, /behavioral-biases, /shy-voter,
│                          # /ballot-complexity, /electoral-fatigue, /choice-overload,
│                          # /demographic-turnout, /compulsory-voting, /deliberation, /nota
├── electoral_systems.py   # /coalition, /districts, /primary, /stv, /multiwinner_compare,
│                          # /gerrymander, /sortition
├── dynamics.py            # /campaign-sensitivity, /combined-effects, /historical-replay,
│                          # /adaptive, /party-dynamics, /hotelling, /polarization
├── experimental.py        # /jury, /quadratic-funding, /liquid-democracy, /conviction-voting,
│                          # /affective-polarization, /power-indices
└── _helpers.py            # _build_candidate_from_xy, _inter_method_agreement,
                           # _dhondt, _greedy_coalition, etc.
```

**Process recommandé** (PR par PR, jamais en une seule fois) :
1. Créer le dossier `election/` avec `__init__.py` qui définit le Blueprint
2. Déplacer les helpers dans `_helpers.py`
3. Migrer un groupe de routes à la fois (commencer par `experimental.py` qui est probablement le moins couplé)
4. Garder l'ancien `election.py` à côté jusqu'à ce que toutes les routes soient migrées
5. Supprimer l'ancien fichier en dernier
6. Vérifier que les imports dans `app/__init__.py` continuent à fonctionner

Idem ensuite pour `theory.py` (2 887 lignes) → `app/routes/theory/{paradox,power_justice,practical}.py`.

---

## 🟨 Impact moyen / effort élevé

### [ ] C1. Introduire une vraie couche service backend
**Pourquoi** : `app/services/` ne contient qu'un seul fichier (`user_service.py`) avec **0 import depuis les routes**. La business logic est mélangée à la couche HTTP partout.

Structure cible :

```
app/services/
├── user_service.py          (existant)
├── election_service.py      # orchestration des modèles de simulation
├── theory_service.py        # paradoxes, Arrow, Plott, etc.
├── perturbation_service.py  # abstention, cascade, biais, etc.
└── electoral_service.py     # coalition, districts, STV, etc.
```

Pattern :

```python
# app/services/election_service.py
class ElectionService:
    @staticmethod
    def simulate(config: dict) -> dict:
        """Pure orchestration — no Flask, no JSON, just dict in/out."""
        electorate = _build_base_electorate(config)
        methods    = _run_methods_on_electorate(electorate, config)
        # ...
        return {"methods": methods, "condorcet_winner": ..., ...}

# app/routes/election/core.py
@election_bp.route("/simulate", methods=["POST"])
@sim_limiter.limit("20 per minute")
@heavy_endpoint
def simulate():
    return lambda data: (ElectionService.simulate(data), 200)
```

**Avantage** : les tests unitaires peuvent appeler `ElectionService.simulate(config)` directement sans démarrer Flask. Le code de simulation est réutilisable pour des batch jobs, des CLIs, etc.

### [ ] C2. Éclater les god-components frontend
- `components/Simulation/VotingMethodVisualizations.tsx` — **1 684 lignes**, à découper par méthode (`PluralityViz.tsx`, `IRVViz.tsx`, `BordaViz.tsx`, `SchulzeViz.tsx`...)
- `components/Simulation/ScoreVotingVisualizations.tsx` — **1 011 lignes**
- `components/Simulation/UtilityVisualization.tsx` — **906 lignes**
- `components/Simulation/VoterVisualization.tsx` — **802 lignes**

### [ ] C3. Sous-dossiers thématiques dans `components/shared/` (70 fichiers à plat)

```
components/shared/
├── lab/        # LabCentralView, PinToCentralButton, ScenarioIO, LabOnboardingTour, ...
├── perturbers/ # AbstentionPanel, CascadePanel, BehavioralBiasPanel, ...
├── theory/     # PlottChaosPanel, SenParadoxPanel, AgendaManipulationPanel, ...
├── electoral/  # CoalitionPanel, STVPanel, GerrymanderMap, PrimarySimulator, ...
├── ui/         # MetricTooltip, LiveBadge, ToastNotification, ModelAssumptionsBanner
└── animations/ # HistoricalReplay, ElectionPipelineAnimator, AdaptiveVotingPanel
```

Process : déplacer par groupe + `git mv` pour préserver l'historique. Penser à mettre à jour les imports — un `grep -rl "from '.*components/shared/AbstentionPanel'"` localise tout.

### [ ] C4. Éclater `i18n/locales/{fr,en}.ts` (2×2 746 lignes)
Migrer vers le pattern i18next standard :

```
i18n/
├── index.ts                  # i18next.init avec resourcesToBackend
└── locales/
    ├── fr/
    │   ├── common.json
    │   ├── lab.json
    │   ├── theory.json
    │   ├── electionLab.json
    │   ├── onboarding.json
    │   └── ...
    └── en/ (mirror)
```

Bonus : permet le lazy-load des bundles de traductions par route via `i18next-http-backend`.

### [ ] C5. `SimulationComparePage` (965 lignes, 25 `useState`) → `useReducer` ou store local
Trop d'état local pour rester lisible. Soit `useReducer`, soit un store Zustand local à la page.

---

## 🟦 Maintenance / hygiène

### [ ] D1. Compléter les type hints backend (78 erreurs mypy)
Distribution : `election.py` 49, `theory.py` 28, `tech.py` 3.
Majorité = annotations génériques manquantes (`set` → `set[str]`, `Counter` → `Counter[str]`, `tuple` → `tuple[int, int]`).

```bash
cd flask_voter_app
python -m mypy app/routes/election.py --ignore-missing-imports 2>&1 | head -20
# Corriger par lots de 10
```

Activer mypy strict en CI une fois propre.

### [ ] D2. ESLint frontend (14 670 issues, ~14 266 auto-fix Prettier)
```bash
cd voter-app
npx eslint . --ext .ts,.tsx --fix
# Trier les ~400 restantes
npm run lint 2>&1 | grep -v prettier | grep error > /tmp/lint-real.txt
```

### [ ] D3. Service Worker — URL en dur
Dans [vite.config.ts](voter-app/vite.config.ts) :

```ts
urlPattern: /^http:\/\/localhost:4433\/api\/.../  // ❌ ne marche qu'en dev
```

À remplacer par une regex paramétrable via env ou un pattern d'URL relative.

### [ ] D4. PWA cache trop restrictif (2 endpoints)
Élargir le `runtimeCaching` à tous les endpoints idempotents (`/simulate`, `/coalition`, `/scenarios/*`, etc.) avec stratégie `StaleWhileRevalidate`. À coordonner avec le cache Redis backend (B1) pour double couche.

---

## 🟩 Ce qui va déjà bien

| Aspect | Constat |
|---|---|
| Backend coverage | 93.70 % sur 8 816 lignes |
| Eventlet | Bien configuré (monkey_patch en première ligne, async_mode="eventlet") |
| Auth | JWT + bcrypt + OAuth Google/GitHub propre |
| Rate limiting | 91/106 routes (modulo les 4 trous documentés dans PRE_PUBLIC_CHECKLIST) |
| DB | Peu d'accès, pas de N+1 visible |
| Workers Web | `useSimulationWorker` décharge heatmap/matrix hors du main thread |
| Memoization Lab | `MethodsMatrix`, `ActiveModulesBar`, `PinnedPerturbationsPanel` déjà sous `React.memo` (sprint 4) |
| Debouncing | `useDebouncedSimulation` existe |
| Services API | Wrappers existent (juste sous-utilisés) |
| PWA | Configurée (manifest, offline, install prompt) |
| TypeScript | 0 erreur après le cleanup Sprint 3 |

---

## Ordre d'exécution recommandé

**Vague 1 — gros gain perf utilisateur** (1-2 semaines)
A1 (lazy routes) → A2 (tpool wrapper) → A3 (theme tokens) → B1 (cache Redis)

**Vague 2 — gros gain DX** (2-3 semaines)
B2 (useApi / React Query) → B3 (éclater election.py) → C1 (couche service)

**Vague 3 — propreté long terme** (au fil de l'eau)
C2 (éclater god components) → C3 (sous-dossiers shared/) → C4 (i18n par feature) → C5 (refactor SimulationCompare)

**Vague continue — hygiène**
D1 (mypy) → D2 (eslint) → D3/D4 (PWA)

Une fois tout coché, ce fichier peut être archivé dans `docs/audit/`.
