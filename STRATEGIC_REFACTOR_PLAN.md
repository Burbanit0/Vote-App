# Vote Lab — Plan de refactor stratégique complet

> Rédigé le 2026-05-23. Ce document propose un refactor profond du projet en 12 semaines, en partant de la stack actuelle pour arriver à une stack moderne, typée de bout en bout, et conçue pour scaler — tout en gardant le projet fonctionnel pendant la transition (stratégie *strangler fig*, pas de big bang).
>
> **Décisions validées le 2026-05-23** :
> - ✅ **Gel complet des features** pendant les 12 semaines
> - ✅ **Backend cible : FastAPI** (retire eventlet complètement)
> - ✅ **UI cible : Tailwind v4 + shadcn/ui** (remplace Bootstrap)
> - ⚠️ **Pas de monitoring d'erreurs** pour l'instant (Sentry repoussé à plus tard) — implique discipline accrue sur tests + typage strict, et fallback `logging` propre à mettre en place
> - ⏳ **Domaine de production** : à décider en Phase 7
>
> Voir aussi :
> - [PRE_PUBLIC_CHECKLIST.md](PRE_PUBLIC_CHECKLIST.md) — items à régler avant ouverture publique (orthogonal à ce plan)
> - [CODE_AUDIT_CHECKLIST.md](CODE_AUDIT_CHECKLIST.md) — refactor tactique court-terme (déjà exécuté à 60 %)

---

## 🎯 Vision — la stack cible

| Layer | Actuel | Cible | Raison du changement |
|---|---|---|---|
| **Backend framework** | Flask 3.1 + eventlet | **FastAPI 0.115+ + uvicorn** | Eventlet officiellement déprécié. FastAPI = async natif, Pydantic baked-in, OpenAPI auto, typage compile-time |
| **Validation** | `int(data.get(...))` partout | **Pydantic v2** | Validation déclarative, error messages auto, génération de schéma TypeScript |
| **ORM** | SQLAlchemy 2.0 (API legacy) | **SQLAlchemy 2.0 async (API moderne)** | Compatible FastAPI, typed query builder |
| **Auth backend** | Flask-JWT-Extended maison | **fastapi-users** ou **AuthX** | Battle-tested, OAuth + JWT + refresh tokens intégrés |
| **WebSockets** | flask-socketio + eventlet | **FastAPI WebSockets natifs** | Plus de monkey-patching, async natif |
| **Background jobs** | `eventlet.tpool` ad-hoc | **FastAPI BackgroundTasks** + Redis queue (RQ) si besoin | Découplé, observable |
| **Cache** | Redis (sous-utilisé) | **fastapi-cache2** | Décorateurs propres, invalidation propre |
| **Tests backend** | pytest + flask test client | **pytest + httpx + pytest-asyncio** | Async-friendly |
| **Frontend framework** | React 19 ✅ | **React 19 ✅** | Aucune raison de changer |
| **TypeScript** | strict ✅ | **strict ✅** | Excellent état actuel |
| **Build** | Vite ✅ | **Vite ✅** | Reste — code-splitting déjà en place (A1) |
| **State serveur** | axios + useState dispersés | **TanStack Query v5** | Cache, dedup, stale-while-revalidate, devtools |
| **State client** | 8 React Contexts | **Zustand** (4 KB, sélecteurs ciblés) | Pas de re-renders en cascade |
| **API client** | axios.post manuels | **openapi-typescript + ky** | Types générés depuis l'OpenAPI backend = une seule source de vérité |
| **UI components** | Bootstrap 5 + react-bootstrap | **Tailwind v4 + shadcn/ui** | Standard 2025, headless, no bundle bloat, copies into repo (pas de dépendance) |
| **Charts** | Recharts + chart.js + d3 + react-google-charts (4 libs!) | **Recharts + d3-delaunay/hexbin** | Consolidé, ~700 KB de bundle économisés |
| **PDF export** | jspdf + html2canvas (1 MB côté client) | **WeasyPrint backend** (`POST /api/export/pdf`) | Qualité parfaite, bundle frontend −1 MB |
| **Tests frontend** | Jest 30 | **Vitest** | 3-5× plus rapide, intégration native Vite |
| **i18n** | i18next monolithique (2×2 746 lignes) | **i18next + namespaces par feature** | Lazy-load des traductions par route |
| **Observabilité backend** | rien | **Sentry + structlog** (JSON logs) | Visibilité prod indispensable pour un projet public |
| **Observabilité frontend** | rien | **Sentry React** | Erreurs utilisateurs remontées automatiquement |
| **CI/CD** | GitHub Actions (HS) | **GitHub Actions (compte réglé) OU self-hosted runner** | Bloquant pour accepter des PR externes |
| **Infrastructure** | docker-compose dev | **+ Dockerfile prod multi-stage + Caddy/nginx reverse proxy + cron pg_dump** | Prérequis pour héberger en prod |

---

## 🧭 Stratégie de migration : *Strangler Fig* (pas de big bang)

L'erreur à éviter : un "rewrite from scratch" sur 4 mois qui ne livre rien. La stratégie *strangler fig* :

1. **FastAPI est monté en parallèle** de Flask, derrière le même reverse proxy
   - `/api/v1/*` → Flask (existant)
   - `/api/v2/*` → FastAPI (nouveau)
2. **Une route à la fois est migrée** : extraction → réécriture FastAPI → frontend bascule sur v2 → la version Flask est supprimée
3. **Le frontend découvre la migration automatiquement** : `openapi-typescript` régénère les types à chaque commit du backend, donc tout changement d'API est visible compile-time
4. **Quand toutes les routes sont migrées**, Flask est retiré et `/api/v2/*` devient `/api/*`

**Bénéfices** :
- L'app reste **toujours déployable** pendant la transition
- Tu peux **arrêter à n'importe quelle étape** et avoir un état cohérent
- Les **régressions sont localisées** à la dernière route migrée
- **Pas de "merge hell"** sur une branche `rewrite/` qui diverge pendant 3 mois

**Coût** :
- Double maintenance temporaire (mais limitée à ~6 semaines en Phase 3)
- Discipline requise : ne jamais ajouter de feature à l'ancien Flask pendant la migration

---

## 📅 Plan en 12 semaines (10-15 h/semaine pour 1 dev)

### Phase 0 — Filet de sécurité (semaine 1)

**Objectif** : avant tout refactor, on règle les irritants et on pose les fondations d'observabilité minimale (sans Sentry — décision validée).

- [ ] **Logging structuré backend** (1 h) — *remplacement minimal du monitoring*
  - Installer `structlog` + config JSON logs
  - Tous les `current_app.logger.exception(...)` → `log.error(event, exc_info=...)` structuré
  - Permet `grep`/jq propre des logs en prod, et migration future vers Sentry/Loki triviale
- [ ] **Healthcheck endpoint** (30 min) — `GET /api/health` : check DB + Redis + return status
- [ ] **Error boundary frontend renforcée** (1 h) — log à la console en dev, affiche un message propre en prod, expose un bouton "copier la stack trace pour le dev"
- [ ] **Régler les 16 tests frontend cassés** (PRE_PUBLIC #4, ~3 h)
  - Mock `useSimulationWorker` dans les 8 suites concernées
- [ ] **Régler la CI/CD** (PRE_PUBLIC #2, durée variable)
  - Soit billing GitHub Actions, soit migration self-hosted runner
- [ ] **Ajouter LICENSE** (PRE_PUBLIC #1, 5 min)
- [ ] **Bootstrap script** (`scripts/bootstrap.sh`) pour onboarder un nouveau dev en 1 commande
- [ ] **Production Dockerfile** multi-stage (build optimisé, image finale ~150 MB)
- [ ] **Cleanup .gitignore + 86 branches** (PRE_PUBLIC #10, #11, 30 min)

**Livrables** : un repo propre, observable, accueillant pour un nouveau contributeur.
**Rien n'est cassé**, on a juste ajouté des fondations.

---

### Phase 1 — Contrats typés (semaine 2)

**Objectif** : avant de réécrire le backend, on définit les contrats Pydantic des 5 endpoints les plus utilisés. Ça force à voir les incohérences actuelles.

- [ ] **Introduire Pydantic v2** côté Flask (compatible)
  - `pip install pydantic`
  - Créer `app/schemas/election.py` avec :
    - `SimulateRequest`, `SimulateResponse`
    - `CombinedEffectsRequest`, `CombinedEffectsResponse`
    - `CampaignSensitivityRequest`, `CampaignSensitivityResponse`
    - `AbstentionRequest`, `AbstentionResponse`
    - `CoalitionRequest`, `CoalitionResponse`
- [ ] **Adapter ces 5 routes** pour valider l'entrée et typer la sortie via Pydantic
- [ ] **Générer le schéma OpenAPI** à partir des Pydantic models (script `scripts/gen_openapi.py`)
- [ ] **Installer openapi-typescript** côté frontend
  - `npm i -D openapi-typescript`
  - `scripts/gen_api_types.sh` qui régénère `src/api/types.ts`
- [ ] **Migrer les 5 panels concernés** pour utiliser ces types générés au lieu de leurs `interface` maison

**Livrables** : la première source de vérité partagée frontend ↔ backend.
**Bénéfice immédiat** : tu vas découvrir 5-10 incohérences cachées entre les types frontend et la réalité backend.

---

### Phase 2 — Scaffolding FastAPI parallèle (semaines 3-4)

**Objectif** : poser l'architecture FastAPI + migrer la première route (`/simulate`) comme proof of concept.

```
flask_voter_app/
├── app/                    # Flask actuel — reste opérationnel
└── api_v2/                 # ── NOUVEAU FastAPI ─────────────
    ├── main.py             # FastAPI app instance
    ├── core/
    │   ├── config.py       # Settings Pydantic (env vars)
    │   ├── security.py     # JWT, password hashing
    │   ├── deps.py         # Dependency injection (DB, auth, …)
    │   └── observability.py # Sentry + structlog setup
    ├── domain/             # ── PURE LOGIC ─────────────────
    │   └── election/
    │       ├── simulate.py # Pure functions, 0 dependency on Flask/FastAPI/DB
    │       ├── methods.py  # The 17 voting methods
    │       └── models.py   # Pure Pydantic models (Candidate, Voter, Result)
    ├── services/           # ── ORCHESTRATION ──────────────
    │   └── election_service.py
    ├── repositories/       # ── DB ADAPTERS ────────────────
    │   ├── user_repository.py
    │   └── scenario_repository.py
    ├── schemas/            # ── HTTP CONTRACTS ─────────────
    │   ├── election.py
    │   └── auth.py
    ├── routes/             # ── HTTP HANDLERS ──────────────
    │   ├── election.py
    │   ├── auth.py
    │   └── scenarios.py
    └── tests/
```

- [ ] **Setup FastAPI** + uvicorn + structlog
- [ ] **Reverse proxy local** : Caddy (1 fichier de config) qui route `/api/v1/*` → Flask:4433 et `/api/v2/*` → FastAPI:8000
- [ ] **Extraire le domain layer** de `_simulate_worker` :
  - `domain/election/simulate.py` — pure Python, 0 import Flask, 0 import DB
  - Testable directement avec pytest, sans serveur HTTP
- [ ] **Service layer** `services/election_service.py` qui orchestre le domain
- [ ] **Schema layer** `schemas/election.py` (déjà fait en Phase 1, on importe)
- [ ] **Route layer** `routes/election.py` — *thin*, juste valide + appelle service + retourne
- [ ] **Cache via fastapi-cache2** sur `/simulate`
- [ ] **Frontend** : `services/electionApi.ts` bascule sur `/api/v2/election/simulate`

**Livrables** :
- FastAPI live à côté de Flask
- Une route migrée et fonctionnelle
- L'architecture de référence pour les 49 autres routes

---

### Phase 3 — Migration des 35 endpoints Election (semaines 5-6)

**Objectif** : migrer toutes les routes `/api/election/*` une par une.

Pour chaque route, le workflow est :
1. Définir le schéma Pydantic (si pas déjà fait)
2. Extraire la logique dans `domain/election/<nom>.py` (pure functions)
3. Créer le service correspondant
4. Créer la route FastAPI
5. Tester (httpx + pytest-asyncio)
6. Frontend bascule sur la v2
7. Supprimer la route Flask correspondante

**Ordre recommandé** (du plus simple au plus complexe) :
- Semaine 5 :
  - [ ] `/sortition`, `/jury`, `/hotelling`, `/polarization` (routes simples)
  - [ ] `/abstention`, `/cascade`, `/behavioral-biases`, `/shy-voter`, `/electoral-fatigue` (Perturbers simples)
  - [ ] `/nota`, `/ballot-complexity`, `/deliberation`, `/choice-overload`
- Semaine 6 :
  - [ ] `/coalition`, `/districts`, `/primary`, `/stv`, `/multiwinner_compare`, `/gerrymander`
  - [ ] `/campaign-sensitivity`, `/combined-effects`, `/historical-replay`, `/adaptive`
  - [ ] `/simulate-pipeline` (animation — peut nécessiter un endpoint streaming SSE)
  - [ ] `/quadratic-funding`, `/liquid-democracy`, `/conviction-voting`
  - [ ] `/affective-polarization`, `/power-indices`, `/divergence`, `/interpret`, `/demographic-turnout`, `/compulsory-voting`, `/party-dynamics`

**Bénéfice à mi-parcours** : `election.py` (7 080 lignes) est complètement supprimé. Le code équivalent en FastAPI fait ~3 500 lignes (Pydantic + domain extraction tuent les `int(data.get(...))` partout).

---

### Phase 4 — Migration des 15 routes Theory + Auth + Scenarios (semaine 7)

- [ ] **15 routes `theory.py`** — même workflow que Phase 3
- [ ] **Auth** : migration vers **fastapi-users**
  - JWT + refresh tokens
  - OAuth Google/GitHub géré nativement
  - bcrypt préservé (backward-compatible avec les passwords existants)
- [ ] **Scenarios CRUD** : routes triviales, ~1 jour
- [ ] **WebSockets Monte Carlo** : réécriture sur FastAPI WebSockets natifs (drop flask-socketio)
- [ ] **Retirer Flask** : suppression de `flask_voter_app/app/`, renommage `api_v2/` → `api/`, mise à jour du Caddyfile

**Livrables** : Flask + eventlet + flask-socketio totalement retirés. Plus une seule deprecation warning.

---

### Phase 5 — Frontend state + data layer (semaines 8-9)

**Objectif** : remplacer les 8 contextes + 49 panels avec axios direct par un pattern unifié.

- [ ] **Adopter TanStack Query v5**
  ```bash
  cd voter-app && npm i @tanstack/react-query @tanstack/react-query-devtools
  ```
- [ ] **Generer les hooks API typés** depuis l'OpenAPI :
  ```bash
  npm i -D openapi-fetch openapi-typescript
  # scripts/gen_api_hooks.sh
  ```
- [ ] **Migrer les 49 panels** progressivement :
  - Avant : `useApiAction(fetchAbstention)` (notre Sprint B2)
  - Après : `useAbstentionMutation()` (généré, typé, cached)
- [ ] **Adopter Zustand** pour le state client non-server
  ```bash
  npm i zustand
  ```
- [ ] **Consolider les 8 contextes en 3-4 stores Zustand** :
  - `useAuthStore` (User, login, logout)
  - `useUIStore` (theme, expertMode, teacherMode, language)
  - `useElectionStore` (config — remplace ElectionContext)
  - `useLabStore` (pinned perturbations, animation broadcast — remplace 2 contextes)
- [ ] **Retirer React Context** sauf ceux dont la API "Provider injection" est strictement nécessaire (rare)

**Bénéfice** : moins de re-renders en cascade, cache HTTP automatique partagé, DX immensément meilleure pour les futures features.

---

### Phase 6 — UI modernisation (semaines 10-11)

**Objectif** : migrer de Bootstrap à Tailwind + shadcn/ui de façon incrémentale.

- [ ] **Setup Tailwind v4** + shadcn/ui CLI
  ```bash
  npm i -D tailwindcss @tailwindcss/vite
  npx shadcn@latest init
  ```
- [ ] **Stratégie** : Bootstrap et Tailwind coexistent pendant la migration
  - Marquer chaque page migrée avec `data-style="tailwind"`
  - Migrer une page à la fois
- [ ] **Composants shadcn à installer** (au fur et à mesure) :
  - Button, Card, Dialog, Dropdown, Form, Input, Select, Tabs, Toast, Tooltip
- [ ] **Réutiliser les tokens du Sprint A3** : `theme/tokens.ts` reste la source de vérité ; juste exposé via Tailwind config
- [ ] **Migrer les pages dans l'ordre d'usage** :
  - HomePage, ElectionLabPage, TheoryPage (les plus visibles)
  - Puis les autres au fil de l'eau
- [ ] **Quand toutes les pages sont migrées** : retirer `bootstrap` et `react-bootstrap` du package.json (−116 KB de bundle)

**En parallèle** :
- [ ] **Migrer Jest → Vitest** (1 jour, gain énorme en speed de feedback)
- [ ] **Supprimer chart.js + react-chartjs-2 + react-google-charts**
  - Migrer les 12 visualisations restantes de `votingMethods/` vers Recharts
  - Tu commences à 3/12 grâce à C2
- [ ] **i18n par feature** :
  - Splitter `fr.ts` et `en.ts` en `locales/<lang>/{common,lab,theory,perturbers,...}.json`
  - Lazy-loader par route via `i18next-http-backend`

---

### Phase 7 — Polish public (semaine 12)

**Objectif** : derniers détails avant ouverture publique.

**État (2026-06-04)** : volet *code/docs* terminé et mergé dans `develop`. Les items
restants sont *deploy-time* (comptes externes / secrets / environnement live), pas du
code — listés ci-dessous comme ⏳ deferred.

- [~] **PDF export côté backend** — **reporté** (décision utilisateur : non prioritaire) :
  - Nouveau endpoint FastAPI `/api/export/pdf` avec WeasyPrint
  - Frontend supprime `jspdf` + `html2canvas` (−1 MB)
- [x] **Décisions sur les 9 pages secondaires** (fait) :
  - **Absorbées dans le Lab** (onglets + redirection de route) : PartyDynamics, Sortition
  - **Supprimées** (orphelines, hors Navbar, recouvrement avec onglets Lab) :
    BlankContagion, CampaignSimulator, ConstitutionalCrisis
  - **Gardées dans le Navbar** : WhatIf, Quiz, InternationalRegimes, TechDemocracy
- [~] **Sécurité** :
  - [x] `security.txt` (`voter-app/public/.well-known/security.txt`)
  - ⏳ hCaptcha / Cloudflare Turnstile sur `/register` + `/login` (besoin de clés)
  - ⏳ Content Security Policy headers (à régler en prod — l'app utilise bcp de styles inline)
- [~] **Operational** :
  - [x] Healthcheck `GET /api/v2/health` (Redis + uptime + version ; **DB ping ⏳**)
  - ⏳ Status page (UptimeRobot free tier) — externe
  - ⏳ Backup `pg_dump` quotidien (cron dans le compose prod)
- [x] **ADR (Architecture Decision Records)** — `docs/adr/` créé avec 10 ADR concis :
    - 001 — Pourquoi FastAPI plutôt que Flask
    - 002 — Pourquoi Pydantic comme source de vérité
    - 003 — Pourquoi TanStack Query + Zustand
    - 004 — Pourquoi Tailwind + shadcn plutôt que Bootstrap
    - 005 — Pourquoi Recharts seul (drop chart.js, d3 partiel)
    - 006 — Strategy: Strangler fig vs Big bang
    - 007 — Architecture en couches (domain/service/route)
    - 008 — Schema localStorage versioning
    - 009 — Internationalization namespacing
    - 010 — Observability stack (Sentry + structlog)
- [x] **README aligné sur la réalité** : stack table corrigée (FastAPI, Tailwind+shadcn,
  TanStack/Zustand, Vitest ; Bootstrap/Flask/Jest retirés). `./scripts/bootstrap.sh`
  end-to-end reste ⏳ à valider en prod.

---

## ⚠️ Registre des risques

| Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|
| **Eventlet fait quelque chose de subtil qui ne marche pas en asyncio** | Moyen | Élevé | Phase 2 garde Flask vivant ; chaque route est testée avant retrait Flask |
| **Pydantic révèle des bugs de typage actuels** | Élevé | Faible | C'est *le but*. Allouer 2 jours de buffer en Phase 1 |
| **Tailwind migration prend 2× plus de temps qu'estimé** | Élevé | Moyen | Bootstrap reste fonctionnel pendant la migration. Pas de cut-off forcé |
| **TanStack Query change de comportement vs axios direct** | Faible | Moyen | Migrer 1 panel à la fois, tester chacun avant de continuer |
| **Solo dev → motivation flanche après 6 semaines** | Moyen | Élevé | Le découpage en phases hebdo permet d'arrêter et de reprendre. Strangler fig = pas d'engagement irréversible avant la Phase 4 |
| **Régression silencieuse en prod** | Faible (avec Sentry) | Élevé | Sentry installé en Phase 0 = première chose qu'on voit |
| **Décision design tardive bloque la migration** | Faible | Moyen | ADR écrites au fur et à mesure (Phase 7), pas en fin |

---

## 🟢 Ce que ce plan NE change PAS (volontairement)

| Choix | Pourquoi le garder |
|---|---|
| **React 19** | Récent, stable, ton équipe (toi) le connaît parfaitement |
| **TypeScript strict** | Base saine — 0 erreur après Sprint 3 |
| **Vite** | Build rapide, code-splitting déjà fait |
| **Postgres + Redis** | Standard absolu pour le domaine |
| **bcrypt** | Implémentation correcte, compatible avec fastapi-users |
| **i18next** | Lourd mais maintenable. Pas de raison de migrer (juste mieux organiser) |
| **PWA** | Différenciant, déjà configuré |
| **Pre-commit hooks** | Excellent (detect-secrets, bandit, mypy, flake8). À conserver |
| **pytest** | Migrer juste vers async ; pas changer de framework |
| **Playwright E2E** | Best-in-class |
| **Recharts + d3-delaunay/hexbin** | Conserver Recharts + le sous-set d3 pour Voronoi/hexbin |
| **Docker Compose dev** | Excellent DX local |
| **Le concept Lab + Central View** | C'est ton produit. À renforcer, pas à toucher |

---

## ✅ Critères de succès

Le refactor est un succès si à la fin :

1. **0 deprecation warning** au démarrage et dans les tests
2. **Schéma OpenAPI auto-généré** à chaque commit, frontend types régénérés automatiquement
3. **Frontend bundle initial < 500 KB gzip** (vs ~250 KB actuels après A1, mais Tailwind devrait économiser ~100 KB via le purge)
4. **Backend p95 latency < 50 ms** pour `/simulate` (vs ~200-500 ms aujourd'hui sans cache)
5. **TypeScript strict + mypy strict** activés en CI, 0 erreur
6. **Sentry capture > 95 %** des erreurs prod (à mesurer)
7. **Test coverage backend ≥ 90 %**, frontend ≥ 70 %
8. **Setup d'un nouveau contributeur** en < 10 min via `bootstrap.sh`
9. **10 ADR** documentant les choix structurants
10. **Aucune feature retirée** (sauf décision explicite Phase 7)

---

## 🚀 Comment démarrer

Si tu valides ce plan, le premier vrai geste c'est **Phase 0**. Concrètement, semaine 1 :

```bash
# Lundi : Sentry + LICENSE + CI
git checkout -b phase0/foundations
# Suit la TODO list de Phase 0

# Mercredi : Tests cassés + bootstrap.sh
git checkout -b phase0/fix-broken-tests
# Mock useSimulationWorker dans les 8 suites

# Vendredi : Production Dockerfile + cleanup
git checkout -b phase0/production-dockerfile
```

Chaque phase = 1 branche `phase<N>/<topic>` qui merge dans `develop` quand le sous-objectif est livré.

**Tu peux t'arrêter à n'importe quelle phase** et avoir un état cohérent :
- Après Phase 0 → projet "investor-ready" sans refactor de stack
- Après Phase 2 → preuve de concept FastAPI déployable
- Après Phase 4 → backend complètement modernisé, frontend inchangé
- Après Phase 6 → projet entièrement modernisé

---

## 📐 Métriques de pilotage à suivre par phase

À mesurer avant Phase 0 (baseline) puis à chaque fin de phase :

| Métrique | Comment mesurer | Baseline |
|---|---|---|
| Lignes de code backend | `find flask_voter_app/app -name "*.py" \| xargs wc -l` | ~21 000 |
| Lignes de code frontend (hors tests) | `find voter-app/src -name "*.ts*" -not -name "*.test.*" \| xargs wc -l` | ~60 000 |
| Bundle initial gzip | `npm run build` → main chunk | ~250 KB |
| Coverage backend | `pytest --cov` | 93.73 % |
| Coverage frontend | `npm test -- --coverage` | (à mesurer) |
| Erreurs mypy | `mypy app/` | 52 |
| Erreurs ESLint (hors prettier) | `npm run lint \| grep -v prettier` | ~400 |
| Vulnérabilités npm | `npm audit` | 6 moderate |
| Temps de build frontend | `time npm run build` | (à mesurer) |
| Temps de test backend | `time pytest` | ~2 min |

---

## 💰 Coût estimé

**Temps** : 100-150 h de travail solo (10-15 h × 10-12 semaines).
**Coûts $$$** : 
- Sentry free tier : 0 €/mois
- GitHub Actions billing : à clarifier
- Hébergement prod (quand le moment viendra) : 5-20 €/mois (Hetzner / DigitalOcean droplet + Postgres managé optionnel)
- **Pas de licence payante requise** par le plan

---

## 🎬 Décision à prendre

Avant de commencer Phase 0, à valider :

1. **Es-tu OK pour ne PAS ajouter de nouvelles features pendant 8-12 semaines ?** (Le refactor seul prend déjà toute la bande passante)
2. **Es-tu OK pour qu'une partie de l'app soit "en chantier" pendant la migration ?** (Phases 2-4 surtout)
3. **Tailwind vs Mantine vs stay-Bootstrap** : préférence ?
4. **Sentry vs autre (Glitchtip self-hosted, Bugsnag…)** : préférence ?
5. **Domaine de production prévu** ? (pour la config CORS, OAuth callbacks, Caddyfile)

Une fois ces 5 décisions prises, Phase 0 peut démarrer le jour même.
