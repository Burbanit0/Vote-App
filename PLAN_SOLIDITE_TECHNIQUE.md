# PLAN — Solidité technique & exploration outillée

> Plan d'exécution auto-suffisant, écrit pour être repris étape par étape (par
> moi ou par un agent) sans contexte préalable. **Une branche `feat/*` + une PR
> par item**, contre `develop`, merge `--no-ff` — comme le mandate `CLAUDE.md`.
>
> **Date d'ouverture** : 2026-09-07
> **État de départ** : `develop` à `a5cb7ce`, tous les gates verts
> (`ci-local/run-ci.sh all` : Backend CI, Frontend CI, Playwright E2E, Security
> Audit — 1789 tests backend, 91 % de couverture, 0 vulnérabilité Trivy,
> 0 secret Gitleaks).

---

## Pourquoi ce plan existe

Vote-App poursuit deux explorations en parallèle, et ce plan sert les deux :

1. **Une exploration des méthodes de vote** — 26 méthodes en parité verrouillée
   entre deux implémentations, une théorie formelle documentée, un objectif
   pédagogique.
2. **Une exploration des technologies et pratiques de développement** — qu'est-ce
   qui tient vraiment la route sur un projet réel, qu'est-ce qui coûte plus
   qu'il ne rapporte, qu'est-ce qui trouve des bugs que rien d'autre ne trouve.

La seconde exploration n'a de valeur que si elle est **documentée honnêtement,
échecs compris**. Un outil essayé et rejeté avec une raison précise vaut autant
qu'un outil adopté — souvent plus, parce que personne ne publie ses rejets.

D'où le principe directeur de ce plan :

> **Chaque item est une expérience, pas une tâche.** Elle se termine par un
> verdict écrit (adopté / rejeté / suspendu) accompagné de ce qu'elle a
> réellement trouvé et de ce qu'elle a réellement coûté.

### Les deux axes de notation

Chaque item est noté sur deux axes indépendants, parce qu'ils ne se recouvrent
pas dans un projet exploratoire :

| Axe | Notation | Ce que ça mesure |
|---|---|---|
| **Solidité** | ⭐ à ⭐⭐⭐ | Ce que ça apporte à la robustesse réelle du code |
| **Récit** | 📝 à 📝📝📝 | La richesse de ce qu'il y aura à raconter à l'issue |

Un item ⭐📝📝📝 (peu solide, très racontable — ex. Z3) mérite d'être fait **ici**
alors qu'il ne le mériterait pas sur un projet purement produit. C'est
précisément ce qui distingue ce plan d'un plan de durcissement classique.

**Effort** : `S` (≤ 1 h) · `M` (une demi-journée) · `L` (1 jour ou plus).

---

## Lot 0 — Le dispositif de documentation *(à faire en premier)*

Ce lot passe avant tout le reste : c'est lui qui transforme les 11 lots suivants
en matière partageable au lieu d'une suite de commits. Le faire après, c'est
reconstituer de mémoire ce qu'on a trouvé — donc mal.

### 0.1 — Séparer les surfaces de documentation

Le repo a déjà plusieurs supports qui se chevauchent mal. À clarifier une fois
pour toutes, dans un court `docs/README.md` :

| Surface | Rôle | Rythme | Existe ? |
|---|---|---|---|
| `docs/journal/JOURNAL_DE_BORD.md` | Chronologie narrative, par session de travail | Par session | ✅ |
| `docs/exploration/EXP-*.md` | Par expérience/outil : verdict + enseignement transférable | Par expérience | ❌ à créer |
| `docs/adr/` | Décisions d'architecture engageantes, avec alternatives écartées | Rare | ✅ (polity seulement — à ouvrir à l'app) |
| `CODE_AUDIT.md` | État de santé daté du code, rejouable | Par passe de nettoyage | ✅ |
| `docs/journal/commits.jsonl` | Trace machine exhaustive, générée — archéologie et alimentation des autres surfaces | Par commit (auto) | ❌ à créer (§0.5) |
| Mémoire Claude polity | Écueils rechargés d'office à chaque session — le seul support qui empêche *réellement* la répétition | Par écueil rencontré | ✅ (manuel → à automatiser, §0.5) |

**Effort** S · Solidité ⭐ · Récit 📝📝

### 0.2 — Créer `docs/exploration/` avec son gabarit

Un fichier par expérience, gabarit fixe :

```markdown
# EXP-00X — <Outil> : <ce qu'on cherchait à savoir>

- **Date** · **Statut** : adopté | rejeté | suspendu · **Coût réel** : Xh
- **Verdict en une phrase** :

## Hypothèse de départ
Ce que j'espérais que ça trouve, avant de commencer.

## Protocole
Ce que j'ai fait exactement (commandes, config, périmètre).

## Ce que ça a trouvé
Les vraies trouvailles, avec des liens vers les commits/PR de correction.
Zéro trouvaille est un résultat valide et intéressant.

## Ce que ça a coûté
Temps d'installation, temps CI ajouté, faux positifs, charge de maintenance.

## Verdict et pourquoi
## Ce que j'en retiens (transférable à un autre projet)
```

La dernière section est la charge utile du partage : elle doit tenir debout
pour quelqu'un qui ne connaît pas Vote-App.

**Effort** S · Solidité ⭐ · Récit 📝📝📝

### 0.3 — L'index des verdicts

`docs/exploration/README.md` : un tableau `EXP | Outil | Domaine | Verdict |
Trouvailles réelles | Coût`. Mis à jour à chaque expérience close.

**C'est le livrable partageable du projet** : « j'ai essayé ~25 outils de qualité
sur un vrai projet, voilà lesquels ont trouvé quelque chose ». Ce tableau
n'existe nulle part ailleurs parce que personne ne tient le compte de ses rejets.

**Effort** S · Solidité ⭐ · Récit 📝📝📝

### 0.4 — Commande `/log-experiment` + agent `experiment-writer`

Sur le modèle exact de `/log-session` + `journal-writer` déjà en place : l'agent
lit le diff, les résultats d'outil et la conversation, puis rédige le carnet
d'expérience selon le gabarit, à valider avant application.

**Effort** M · Solidité ⭐ · Récit 📝📝

### 0.5 — Capture automatique par commit dans le worktree polity

**Origine** : `/log-session` + `journal-writer` ont d'abord été construits pour
résumer les expérimentations du worktree `Vote-App-polity`. L'objectif reste le
même, mais il n'est atteint qu'à moitié : le récapitulatif dépend de la
discipline de le lancer. Objectif visé : **chaque commit du worktree polity
alimente automatiquement une trace, pour ne pas refaire en boucle les mêmes
erreurs.**

#### Les contraintes réelles, vérifiées

| Fait | Conséquence de conception |
|---|---|
| **Les hooks git sont partagés entre worktrees** — depuis polity, `git rev-parse --git-path hooks` → `/home/burbanit0/Vote-App/.git/hooks` | Un `post-commit` **doit se garder** sur le worktree/la branche, sinon il se déclenche aussi sur les commits de `develop`. |
| **361 commits sur 30 jours** (~12/jour) | Un recap LLM par commit = ~360 entrées/mois. C'est le volume qui **tue** la relecture : le remède deviendrait le mal. |
| **La mémoire polity existe déjà** (~20 fichiers, namespace propre) et contient déjà des écueils (« awakening-gate landmine », « DuckDB `->>` precedence gotcha ») | Le mécanisme anti-boucle **existe** — il est alimenté à la main, et par lot. Le travail est de l'automatiser, pas de le réinventer. |
| Le worktree polity a **déjà des hooks Claude** `PreToolUse` (garde graphify) | Le pattern est connu et en service : on l'étend, on n'introduit pas un concept neuf. |

#### L'architecture en trois étages

La distinction structurante : **le log sert l'archéologie et le récit ; la
mémoire sert la non-répétition.** Un fichier de log qu'il faut penser à relire
n'empêche aucune boucle — la mémoire, elle, se recharge d'office à chaque
session. « Un recap par commit » mélange ces deux besoins ; les séparer les sert
tous les deux.

**Étage 1 — Capture exhaustive, par commit, sans LLM** · `M` · ⭐⭐⭐ 📝📝

Un `post-commit` gardé sur le worktree polity écrit une ligne dans un JSONL
append-only (`docs/journal/commits.jsonl`) : sha, date, branche, message,
fichiers touchés, stats, plus les signaux propres à polity (un fichier de
résultats d'acceptance a-t-il bougé ? un paramètre de config ?).

Coût nul, aucune latence, **jamais bloquant** (`|| true` systématique — un hook
ne doit jamais empêcher un commit). C'est la trace d'archéologie exhaustive,
celle qui permet de répondre à « quand ai-je touché ce paramètre, et
combien de fois ? ».

**Étage 2 — Récit par session/lot, avec LLM** · `S` · ⭐ 📝📝📝

`/log-session` existe déjà : il est simplement **alimenté par l'étage 1** au
lieu de reconstituer de mémoire. La granularité narrative reste la session ou le
lot — c'est déjà celle de la mémoire polity (`v5_lot1`, `v5_lot2`…), donc la
granularité naturelle du projet.

**Étage 3 — Mémoire d'écueils, alimentée automatiquement** · `M` · ⭐⭐⭐ 📝📝📝

**C'est l'étage qui sert réellement l'objectif anti-boucle.** Quand l'étage 1
détecte un signal d'échec, le pipeline propose une entrée dans le namespace
mémoire polity (`~/.claude/projects/-home-burbanit0-Vote-App-polity/memory/`) —
donc rechargée d'office à chaque session, sans effort de relecture.

Signaux détectables **sans LLM**, à partir du seul JSONL :

- un `revert`, ou un commit qui annule le précédent ;
- un message contenant `fix`/`revert`/`retry`/`workaround` ;
- **l'oscillation d'un paramètre** — même fichier de config modifié N fois en
  M jours : signature d'une recherche à tâtons, donc d'un écueil non compris ;
- un nouveau fichier de résultats d'acceptance : chaque run porte un verdict à
  capter ;
- **le signal le plus utile** : un commit qui touche un fichier déjà cité dans
  une mémoire d'écueil existante.

Ce dernier point justifie à lui seul le dispositif : un hook `PreToolUse` — sur
le modèle exact de la garde graphify déjà en service — peut **prévenir au moment
où tu touches une zone documentée comme piégeuse**, avant l'erreur, et non après.

#### Points d'implémentation à ne pas rater

- Garde de worktree obligatoire dans le `post-commit` (hooks partagés).
- Jamais bloquant, jamais d'appel réseau synchrone au commit.
- Enrichissement LLM **différé et par lot** (`/recap` traite les commits non
  encore résumés), jamais au fil du commit : pas d'appel LLM sur un « wip typo ».
- Répartition develop/polity conforme à la règle établie : le mécanisme
  générique (script, commande) sur `develop`, l'activation et les mémoires
  d'écueils côté polity.
- `commits.jsonl` est un artefact **généré** : jamais édité à la main.

### 0.6 — Ouvrir les ADR côté application

`docs/adr/` ne contient que des ADR polity. Les décisions structurantes de
l'app (le double moteur et sa parité, le choix SVG natif vs Recharts, l'archi
en 5 moments du Playground, le refus d'authentification) ne sont documentées
nulle part comme *décisions avec alternatives écartées*. Les écrire
rétroactivement — c'est de la reconstitution assumée, à signaler comme telle.

**Effort** M · Solidité ⭐⭐ · Récit 📝📝📝

---

## Lot 1 — Quick wins d'infrastructure

Effort minime, bénéfice immédiat, débloque le confort de tous les lots suivants.

| Item | Pourquoi ici | Effort | Solidité | Récit | Statut |
|---|---|---|---|---|---|
| **Groupes Dependabot** (`groups:`) | `dependabot.yml` n'a aucun groupe → les 13 PR en cascade du 06/09 auraient été 2-3 PR. Cause racine identifiée, correctif de 20 min. | S | ⭐⭐⭐ | 📝📝 | ✅ PR #321 |
| **Merge queue** | Résout structurellement l'invalidation en cascade (« doit être à jour avec develop ») : la queue rebase et teste en série toute seule. | S | ⭐⭐⭐ | 📝📝 | ✅ **fait et vérifié en direct** (PR #338, mergée par `app/mergify` en 15s, 0 intervention manuelle). Native GitHub bloquée (réservée aux repos publics *organisation* — 422 confirmé) ; pivot Mergify (gratuit OSS). Effet de bord utile : drift réel trouvé et corrigé — `develop` n'avait que 5 checks requis sur les 12 documentés (`scripts/setup-branch-protection.sh`), restauré en direct. `strict` (« up to date ») désactivé sur `develop` — Mergify l'a lui-même signalé bloquant en direct (« Configuration not compatible with a branch protection setting ») avant de fonctionner ; `required_status_checks` reste injecté automatiquement, pas dupliqué dans `.mergify.yml` |
| **Ruff** (remplace flake8) | ~100× plus rapide, couvre flake8 + isort + pyupgrade + bugbear + une partie de bandit. Le meilleur ratio du plan. | S | ⭐⭐⭐ | 📝📝 | ✅ swap fidèle fait ; isort/pyupgrade/bugbear pas activés (scope creep — voir note du `[tool.ruff]`) |
| **`uv`** (remplace pip en CI) | Installation Python drastiquement plus rapide + lockfile reproductible (aujourd'hui `requirements.txt` épinglé à la main). | M | ⭐⭐ | 📝📝 | ✅ swap fidèle fait (5 workflows + 4 Dockerfiles, vérifié par build Docker réel de chacun) ; `requirements.txt` reste la source de vérité, pas de migration `uv.lock`/`pyproject` — la reproductibilité de lockfile reste à faire, scope creep écarté comme pour Ruff |
| **Cache CI** (npm / pip / couches Docker) | Boucle de feedback plus courte sur tous les lots suivants. | S | ⭐⭐ | 📝 | ✅ npm/pip déjà en place partout (vérifié) ; couches Docker ajoutées pour `image-scan` |
| **`diff-cover`** | Exiger 100 % de couverture *sur les lignes modifiées d'une PR* — bien plus mordant qu'un seuil global à 90 % qu'on atteint en diluant. | S | ⭐⭐⭐ | 📝📝 | ✅ Backend CI + Frontend CI, gate PR uniquement ; lcov (frontend) demande un préfixe de chemin (`voter-app/`) que Cobertura (backend) n'a pas besoin — testé en local dans les deux sens (ligne couverte/non couverte) avant push ; pas de mirroir `ci-local/` (pas de branche de base dans une image Docker) |
| **Codecov** | Commentaire de couverture par PR + tendance visible dans le temps. | S | ⭐ | 📝 | ✅ compte + `CODECOV_TOKEN` créés par l'utilisateur ; upload backend+frontend câblé, `codecov.yml` (informational: true des deux côtés — diff-cover reste le seul gate réel), validé via `codecov.io/validate` |
| **`act`** | Lancer les workflows GitHub en local, complète `ci-local/`. | S | ⭐ | 📝📝 | ✅ installé sans sudo, `.actrc` + `ci-local/act-pr-event.json` ajoutés, testé en vrai contre `openapi-contract.yml` (job non couvert par `ci-local/`) ; limites documentées (paths-filter interroge l'API GitHub, secrets absents, CodeQL/Scorecard non exécutables) |

---

## Lot 2 — Rendre les conventions exécutables

Le repo a beaucoup de règles **écrites** (`CLAUDE.md`, skills) que rien
n'applique. Ce lot les transforme en garde-fous. Angle de récit : *« combien de
mes conventions documentées étaient déjà violées sans que je le sache ? »* —
avec un chiffre réel à la clé.

| Item | Pourquoi ici | Effort | Solidité | Récit | Statut |
|---|---|---|---|---|---|
| **`import-linter`** | La couche `route → domain → engine` du skill `voter-api` n'est qu'une convention. import-linter la rend bloquante. | M | ⭐⭐⭐ | 📝📝📝 | ✅ contrat `layers` dans `pyproject.toml`, gate bloquant en CI + `ci-local/`, 0 violation trouvée (déjà propre). `api.core`/`api.schemas`/`api.sockets` volontairement hors contrat — le skill ne documente que routes→domain→engine |
| **Règles Semgrep custom** | Semgrep tourne avec des règles génériques. Écrire les miennes : « aucun worker n'importe `api.routes` », « tout endpoint v2 a un rate-limit », « pas de `except Exception` sans log » — soit exactement les 3 bugs corrigés le 06/09, transformés en anti-récidive. | M | ⭐⭐⭐ | 📝📝📝 | ✅ 2 règles bloquantes dans `.semgrep/vote-app-rules.yml` (la 3e est déjà couverte par import-linter, pas dupliquée). Les deux ont trouvé de la vraie dette en les écrivant : 3 routers v2 sans rate-limit (corrigé), 18 `except Exception` muets sur 9 fichiers (corrigés) — pas laissé en baseline |
| **`dependency-cruiser`** ou `eslint-plugin-boundaries` | Équivalent front : règles d'architecture sur les imports + cycles. | M | ⭐⭐ | 📝📝 | ✅ règle `lib-is-pure` bloquante dans `.dependency-cruiser.json` (`src/lib` ne doit pas importer `src/components`/`src/pages`, cf. CLAUDE.md — Playground), gate CI + `ci-local/`, imports type-only exemptés. Baseline propre (287 modules, 1558 deps, 0 violation), règle vérifiée en direct sur une violation synthétique injectée puis retirée. Épinglé `17.4.3` : `18.x` exige Node ≥22, ce repo est encore sur Node 20 |
| **`deptry`** | Équivalent de knip pour Python (deps déclarées inutilisées / utilisées non déclarées). Détection présente côté front, absente côté back. | S | ⭐⭐ | 📝📝 | ✅ scope `api/` (exclut `scripts/` polity + `api/tests/`, par design de l'outil), baseline 0, `[tool.deptry]` dans `pyproject.toml`, câblé dans le cliquet qualité. Effet de bord : `ruff`/`pytest*` dupliqués dans `requirements.txt` retirés, `Dockerfile` dev installe désormais `requirements-dev.txt` aussi |
| **Hooks Claude** (`settings.json`) | `PreToolUse` **bloquant** sur `engineParity.json` → rend impossible l'édition manuelle que `CLAUDE.md` interdit par écrit ; `PostToolUse` sur le moteur → rappel de régénérer la parité. ~~Le `.claude/` n'a aucun hook aujourd'hui~~ *(faux — les garde-fous graphify existaient déjà, corrigé)*. | M | ⭐⭐⭐ | 📝📝📝 | ✅ les deux hooks ajoutés (`.claude/hooks/*.py`), **testés en direct** : une vraie tentative d'`Edit` sur `engineParity.json` a été rejetée par le hook (pas juste simulée), checksum du fichier inchangé après |
| **`madge`** | Cycles d'imports front + visualisation du graphe. | S | ⭐ | 📝 | ✅ `npm run madge:circular` + `scripts/audit.sh --quality`, informationnel (pas dans le cliquet, vu son ⭐ bas). 1 cycle trouvé (`useSimulationWorker.ts` ↔ `IdeologyHeatmap.tsx`), bénin — `import type` uniquement, éliminé à la compilation. Visualisation du graphe documentée mais pas générée (nécessite `graphviz`/`dot`, indisponible sans sudo) |

---

## Lot 3 — Le contrat API et la résilience

| Item | Pourquoi ici | Effort | Solidité | Récit | Statut |
|---|---|---|---|---|---|
| **Schemathesis** | `openapi.gen.json` est versionné avec un gate de drift, mais **le contrat n'est jamais vérifié contre l'implémentation**. Schemathesis génère des centaines de requêtes depuis le schéma, fuzze, et vérifie la conformité des réponses. Chaînon manquant le plus évident du projet. | M | ⭐⭐⭐ | 📝📝📝 | ✅ `api/tests/test_schema_contract.py` + workflow dédié `schemathesis.yml` (pas dans `backend-ci-cd-pipeline.yml` par prudence — un run complet mesure ~220s (~3.5-4 min) en local mais n'a pas été revérifié sur un runner GitHub réel). Génération `derandomize=True` + `seed=` fixe pour la reproductibilité (une première tentative avec `derandomize=True` seul ne suffisait pas d'un process à l'autre — `PYTHONHASHSEED` non fixé fausse la dérivation de graine de Hypothesis ; un `seed=` explicite au niveau du `Config` schemathesis, qui ne passe pas par `hash()`, règle le problème). A trouvé et corrigé 6 bugs réels avant d'être mergé : (1) codes de statut atteignables mais jamais documentés (400/404/500/503) sur les 7 routers — corrigé via `responses=` + schéma `ErrorDetail` partagé ; (2) crash `IndexError` sur `/theory/identity-voting` (le schéma acceptait 2 candidats, le worker en exige 3) — corrigé en remontant `min_length` ; (3) crash `max() iterable argument is empty` sur `/assembly`, `/assembly-scorecard`, `/temporal`, `/structural-fairness` quand deux partis partagent un nom (collision de clé dict) — corrigé par un `field_validator` rejetant les doublons ; (4) crash `TypeError`/`IndexError` sur `/campaign-sensitivity` (`snapshot_days` mal typé `List[Any]` + bornes non vérifiées, un jour négatif de grande magnitude débordait l'indexation Python) — corrigé en typant `List[Union[int, Literal["final"]]]` et en bornant des deux côtés (`max(0, min(...))`) ; (5) crash `AttributeError` sur `/choice-overload` (`heuristic_weights` explicitement `null` contournait le défaut de `.get()`) — corrigé en `or {}` ; (6) crash `AttributeError` sur `/tech/polis` (le schéma promet `List[str]`, le worker traitait chaque élément comme un dict) — corrigé pour accepter les deux formes. Le reste (~40 endpoints) est de la dette pré-existante trackée nommément dans `KNOWN_FAILURES` (requêtes délibérément peu typées, timeouts sur des simulations lourdes — recoupe directement l'item "Timeouts & backpressure" ci-dessous), pas noyée dans un chiffre global |
| **Test du rate-limit (429)** | La valeur 120/min a été calibrée après deux échecs e2e — mais rien ne teste que la limite se déclenche vraiment. | S | ⭐⭐ | 📝📝 | ✅ `api/tests/test_ratelimit_v2.py` — 122 requêtes vers `/api/v2/simulations/get_closest_candidate` (corps par défaut valide, donc pas de bruit lié à la validation), assertion qu'un 429 apparaît. Le v1 (`/simulate` 10/min, `/compare` 5/min) avait déjà ses tests dans `test_public_v1.py::TestRateLimits` ; seul le v2 (120/min, `check_v2_rate_limit`) manquait |
| **Résilience Redis** | Le rate-limiter dépend de Redis. Que se passe-t-il quand il tombe ? Aujourd'hui : inconnu. | M | ⭐⭐⭐ | 📝📝📝 | ✅ Testé en direct contre un Redis injoignable : sans correctif, `redis.exceptions.ConnectionError` remontait non attrapée hors des internals de `slowapi`, transformée par le handler générique en 500 — Redis indisponible mettait hors service toute la surface `/api/v2` (tous les routers partagent `check_v2_rate_limit`) et `/api/v1`, pas seulement la protection anti-abus. Corrigé par `swallow_errors=True` sur le `Limiter` (fail *open*, pas *closed*) + un vrai gap découvert dans `slowapi` : même avec `swallow_errors=True`, l'injection des en-têtes de réponse lit `request.state.view_rate_limit` sans condition, qui n'est jamais posé si le check a été avalé — corrigé par un middleware `main.py` qui le pré-initialise à `None` avant toute dépendance de route. Cache Redis (`api/engine/utils/cache.py`) déjà résilient de son côté (try/except déjà en place à l'écriture, aucun changement nécessaire). Régression épinglée par `api/tests/test_ratelimit_resilience.py`, confirmée en échouant sans le correctif |
| **Timeouts & backpressure** | Sémaphore limitant les simulations concurrentes + `asyncio.wait_for` sur les workers, au lieu de saturer le pool de threads. | M | ⭐⭐⭐ | 📝📝 | ✅ `api/core/worker_dispatch.py` — `run_bounded`/`run_worker_bounded` bornent tout `asyncio.to_thread` de l'app derrière UN sémaphore partagé (4, aligné sur le `ThreadPoolExecutor(max_workers=min(4, num_runs))` déjà utilisé en interne par le worker Monte Carlo) + un timeout de **180s** (aucun bug, juste le vrai coût de calcul aux bornes déjà documentées). Calibré deux fois : une première valeur de 90s (mesurée en local isolé sur Monte Carlo à bornes max = 34s et `/election/coalition` à bornes max = 57s) a **échoué en CI réelle** — `/simulations/what-if` plafonné à ses 10 valeurs documentées prend 71s en local isolé, sans contention, et a dépassé 90s sous `pytest-xdist` sur un runner GitHub Actions plus lent et partagé (PR #349, `test_caps_at_10_values`). 180s laisse une vraie marge au-dessus du pire cas observé *en CI*, pas seulement en local. Limitation connue et documentée, pas un bug : Python ne peut pas tuer un vrai thread OS — le slot du sémaphore se libère immédiatement au timeout, mais le thread orphelin continue en arrière-plan jusqu'à sa fin naturelle. Les 6 routers ont été migrés (`election.py`, `simulations.py`, `tech.py`, `theory.py`, `public.py`, `export.py`) ; la logique de mapping `(body, status) → HTTPException`, dupliquée dans 4 fichiers, a été factorisée dans `raise_for_status` (évite une régression jscpd que la duplication aurait sinon introduite). Effet de bord : `election.py` avait un `_run_passthrough` mort (0 appelant) — supprimé. Testé : `test_worker_dispatch.py` (sémaphore + timeout en isolation, y compris une preuve directe que la concurrence est bornée) + `test_worker_timeout_routes.py` (un timeout traverse bien chaque router jusqu'à un 503 propre) |
| **Déconnexion Socket.IO en plein run** | Partiellement testé le 06/09, à compléter (client qui coupe, run orphelin). | S | ⭐⭐ | 📝 | ✅ Le « run orphelin » était un vrai bug, pas juste un trou de test : le handler `disconnect` ne faisait que `.pop()` le flag d'arrêt (l'effacer), sans jamais le mettre à `True` — la boucle Monte Carlo d'un client déconnecté continuait donc à tourner jusqu'à `num_iterations` (jusqu'à 10 000 itérations de calcul réel), sans plus personne à qui envoyer les événements. Corrigé en une ligne (`_stop_flags[sid] = True` au lieu de `.pop()`) — la boucle a déjà son propre check `if _stop_flags.get(sid):` à chaque itération, il ne recevait juste jamais le signal. `test_disconnect_stops_the_orphaned_run` (nouveau) compte les vrais appels `_run_one` avant/après déconnexion pour le prouver — rejoué contre le code d'avant le correctif pour confirmer une vraie régression (595 appels au lieu de <20) |

---

## Lot 4 — Le domaine électoral *(le cœur exploratoire)*

**C'est le lot à plus forte valeur du plan, et le plus spécifique à ce projet.**
Les critères de la théorie du choix social sont littéralement des propriétés
testables — un levier que presque aucun repo ne possède.

### 4.1 — Tests axiomatiques systématiques ⭐⭐⭐ 📝📝📝 · `L`

Pour chacune des 26 méthodes, vérifier les critères qu'elle **doit** satisfaire
*et ceux qu'elle doit violer* : Condorcet, majorité, monotonie, participation,
indépendance des clones, symétrie par renversement, Pareto, unanimité.

Un test qui vérifie qu'**IRV échoue la monotonie** est aussi précieux qu'un test
de succès : il documente la théorie *et* détecte une implémentation qui
deviendrait accidentellement monotone — donc fausse. `test_anonymity.py` est
déjà ce germe, à généraliser en matrice méthode × critère.

Sous-produit : cette matrice est **directement publiable** comme contenu
pédagogique, et recoupe `THEORY.md`.

✅ **Fait.** `fast_api_voter/api/tests/test_voting_criteria_matrix.py` — 21
méthodes ordinales (le sous-ensemble du parity set de CLAUDE.md défini sur des
classements ; les 5 méthodes cardinales — score/STAR/cumulative/maximin/nash —
sont hors périmètre, ces critères étant définis sur des classements) × 7 des 8
critères prévus (participation et symétrie par renversement reportés, voir
plus bas). Méthodologie détaillée dans `CONTRIBUTING.md` et le docstring du
fichier ; résumé : classification jamais tirée de mémoire, découverte par
fuzzing puis verrouillée en tests `@given` (Hypothesis, `derandomize=True`,
reproductibilité confirmée sur plusieurs process et plusieurs
`PYTHONHASHSEED`). Trouvailles réelles, chacune vérifiée à la main avant
d'être épinglée : (1) `minimax` est Condorcet-cohérent pour les gagnants mais
peut élire un authentique perdant de Condorcet (candidat qui perd chaque
duel pairwise) — propriété réelle mais peu citée de la méthode
Simpson-Kramer, pas un bug ; (2) une première exploration sous-échantillonnée
(~100-240 profils aléatoires par cellule) a classé à tort `ranked_pairs`,
`river` et `smith_irv` comme satisfaisant l'indépendance des clones, et
`nanson` comme satisfaisant la monotonie — les quatre violent en réalité leur
critère, mais seulement sur des profils dégénérés à égalité parfaite (marges
pairwise ou votes de premier choix exactement à égalité), assez rares pour
n'être trouvés que par la recherche par réduction de Hypothesis sur le test
`@given` complet, pas par l'exploration initiale à faible échantillon — la
classification finale fait foi via les tests eux-mêmes, pas via le script
d'exploration jetable. Reporté nommément (pas deviné) : participation et
symétrie par renversement, où le signal réel se mélange à du bruit de
tie-break qui demande une passe dédiée pour être démêlé cellule par cellule.

### 4.2 — Oracle tiers (`pref_voting` / `abcvoting`) ⭐⭐⭐ 📝📝📝 · `M`

La parité actuelle compare *mes deux* implémentations — qui peuvent être fausses
**ensemble**. Croiser avec une bibliothèque académique indépendante (celle de
Pacuit & Holliday) casse cette corrélation d'erreur. Tout écart est soit un bug
chez moi, soit une divergence de convention à documenter — les deux sont du bon
contenu.

✅ **Fait.** `pref_voting` (Pacuit & Holliday) installé dans un venv jetable
séparé (Python 3.11 — la lib dépend de `numba`, incompatible avec le Python
3.14 du projet ; **pas** intégré en dépendance permanente ni en CI pour cette
raison, contrairement à Schemathesis — passe exploratoire ponctuelle plutôt
qu'un nouveau gate). Les 21 méthodes ordinales ont toutes un équivalent direct
dans `pref_voting` (mapping documenté dans le script d'exploration) ; les 3
cas ambigus (`bucklin`→`simplified_bucklin` pas `bucklin`, `nanson`→
`strict_nanson` pas `weak_nanson`, `two_round`→`plurality_with_runoff_put`)
ont été désambiguïsés en lisant le docstring/source de la lib avant de choisir.

3000 profils aléatoires (3-4 candidats, 3-11 électeurs) × 21 méthodes, chaque
gagnant de MON moteur comparé à l'ensemble des gagnants (avec égalités) de
`pref_voting` — comparaison "mon gagnant ∈ l'ensemble oracle", pas égalité
stricte, puisque les conventions de tie-break diffèrent légitimement entre
implémentations indépendantes. **18/21 méthodes : 0 écart.** 4 écarts trouvés
et intégralement investigués à la main :

- **`dowdall`** (1 écart) : PAS un bug chez moi — un artefact de précision
  flottante DANS l'oracle. Le profil trouvé a deux candidats exactement à
  égalité (43/6 vérifié en fractions exactes), mais l'addition en flottant de
  `pref_voting` (ordre de sommation différent du mien) casse l'égalité par un
  epsilon et ne retourne qu'un seul gagnant au lieu des deux. Reproduit et
  confirmé par un script indépendant ; rien à corriger côté Vote-App.
- **`baldwin`** (11 écarts) et **`raynaud`** (27 écarts) : bugs réels,
  corrigés. Les deux méthodes n'éliminaient qu'UN candidat par tour (le pire,
  départage alphabétique) au lieu de TOUS les candidats à égalité pour le pire
  score/pire défaite simultanément — contrairement à `get_irv_winner` et
  `get_nanson_winner` dans ce même fichier, qui éliminaient déjà tout le
  groupe à égalité. Corrigé pour aligner Baldwin et Raynaud sur cette
  convention (déjà interne au projet, et celle de `pref_voting`) ; les deux
  moteurs (backend + `playgroundVoting.ts`/`voteTrace.ts` pour le rejeu)
  mis à jour, `engineParity.json` régénéré, parity test au vert.
- **`smith_irv`** (75 écarts, le plus fréquent) : bug réel dans `_smith_set`
  — son test de dominance ne vérifiait que « personne à l'extérieur ne bat
  quelqu'un à l'intérieur », pas « tout le monde à l'intérieur bat tout le
  monde à l'extérieur » (les deux coïncident sauf en présence d'égalités
  pairwise, où le test bugué valide un ensemble de Smith trop petit). Second
  bug indépendant : `get_smith_irv_winner` recalculait l'ensemble de Smith à
  CHAQUE tour d'élimination au lieu de le calculer UNE FOIS sur le champ
  complet (la vraie définition de Smith-IRV/Tideman's Alternative, confirmée
  par le code source de `pref_voting`). Les deux corrigés ; effet de bord
  intéressant, confirmé par recherche exhaustive (Hypothesis + recherche
  aléatoire, 0 contre-exemple trouvé après correctif) : smith_irv **satisfait
  bel et bien** l'indépendance aux clones une fois l'algorithme correct — le
  contre-exemple épinglé en Lot 4.1 était un artefact du bug, pas une
  propriété réelle de la méthode. `test_voting_criteria_matrix.py` mis à jour
  en conséquence (classification ET docstring).

Régression `jscpd` trouvée et corrigée en cours de route (33→34 clones) : le
calcul de "pire défaite pairwise" dupliqué entre `winRaynaud` et sa trace de
rejeu (`voteTrace.ts`) — factorisé dans `raynaudWorstLoss`, exportée et
partagée, cliquet revenu à 33.

`abcvoting` (méthodes multi-gagnants) non exploré dans cette passe — les 21
méthodes verrouillées sont toutes mono-gagnant ; laissé pour une éventuelle
extension si Vote-App verrouille un jour une méthode multi-gagnants dans le
parity set.

### 4.3 — Vérification exhaustive des petits cas ⭐⭐⭐ 📝📝📝 · `M`

Pour n ≤ 4 candidats et m ≤ 5 électeurs, l'espace des profils est **fini et
petit**. On passe de « 60 scénarios aléatoires » à une **preuve exhaustive**
front/back sur tout le domaine borné. Gain de confiance considérable pour un
coût dérisoire.

✅ **Fait — et le plus rentable des trois items du Lot 4 jusqu'ici.** Grâce à
l'anonymat des règles (déjà établi par `test_anonymity.py`), l'espace des
profils se réduit à des multi-ensembles de bulletins
(`itertools.combinations_with_replacement` sur les n! bulletins possibles) :
118 754 profils pour n=4/m≤5, calculables en ~28s côté backend seul — l'idée
du plan (« coût dérisoire ») était juste. Comparaison directe **backend Python
↔ frontend `ruleWinnerFromRanks`**, gagnant exact (y compris `None`/tie),
`npx tsx` pour exécuter le TS côté script (pas de dépendance ajoutée).

**2 503 935 comparaisons (119 235 profils × 21 méthodes), 5 méthodes en
écart réel — chacune investiguée et corrigée à la main :**

- **`condorcet`** (23 840 écarts — le plus fréquent, invisible jusqu'ici) :
  `gen_engine_parity.py` comparait la mauvaise fonction backend.
  `RULE_LABELS` du front étiquette explicitement cette règle « Condorcet
  (Copeland) » — elle résout toujours un gagnant (méthode de Copeland) —
  alors que le script comparait contre `get_condorcet_winner`, le critère
  **strict** (`Optional[str]`, souvent `None`). Les deux ne peuvent diverger
  que quand `get_condorcet_winner` retourne `None` — un cas que le fixture
  historique (échantillon aléatoire + filtre `strict_winner` qui saute
  justement les gagnants `None`) ne testait jamais. Remappé sur
  `get_copeland_winner`, la vraie fonction jumelle.
- **Même écart, deuxième couche** (5 821 restants après le remappage) :
  `get_copeland_winner` départage les égalités par total de victoires puis
  alphabétique ; `winCondorcet` (front) départageait par Borda — deux choix
  légitimes mais différents. Front aligné sur le départage du backend
  (autoritaire, CLAUDE.md).
- **`two_round`** (3036 écarts) : sur une égalité EXACTE au second tour,
  `av >= bv ? a : b` favorisait silencieusement le leader du premier tour
  plutôt que de départager alphabétiquement comme le backend. Corrigé.
- **`benham`** et **`smith_irv`** (4217 et 5075 écarts) : sur une égalité
  totale (plus aucune élimination possible), le front retournait -1 (« pas de
  gagnant ») alors que le backend retombe sur le survivant alphabétiquement
  premier — un choix documenté explicitement dans le docstring de chacune de
  ces deux fonctions backend, différent (et non partagé) de celui d'IRV/Coombs
  qui, eux, retournent bien `None`. Front aligné sur ce fallback backend ;
  `playgroundVoting.test.ts` mis à jour (le test figeait l'ancien -1 comme
  comportement voulu pour les 4 méthodes d'un coup).
- **`dowdall`** (70 écarts) : vrai bug backend, cette fois-ci **chez nous**
  (pas dans un tiers comme au Lot 4.2). `get_dowdall_winner` utilisait
  `Fraction` pour rester exact — mais `defaultdict(float)` réintroduit
  silencieusement le flottant dès la première addition (`0.0 + Fraction(1,k)`
  redevient un float via `Fraction.__radd__`), recréant exactement le bug que
  le commentaire du fichier dit vouloir éviter. Le frontend, lui, était déjà
  protégé (mise à l'échelle par `lcm(1..m)` pour rester en entiers exacts) —
  ironie du sort, c'est la comparaison exhaustive avec le front qui a trouvé
  le bug côté back. Corrigé en `defaultdict(Fraction)`.

**Fixture permanente** (`voter-app/src/lib/__fixtures__/engineParity.json`,
nouvelle clé `exhaustiveScenarios`) : les 481 profils exhaustifs pour n≤3
(m≤5), gagnants **bruts** (pas filtrés par `strict_winner` — ce filtre aurait
justement masqué 4 des 5 bugs ci-dessus), régénérés et vérifiés à chaque PR
par `check_engine_parity_drift.sh` comme le reste du fixture. n=4 (98 280
profils de plus, ~60 Mo de JSON) volontairement **non committé** : vérifié une
fois en développement (0 écart après correctifs), mais un ajout de cette
taille au fixture ralentirait `check_engine_parity_drift.sh` sur *chaque* PR
pour couvrir la même classe de bugs qu'une tranche n≤3 beaucoup plus petite
détecte déjà.

### 4.4 — `fast-check` côté TypeScript ⭐⭐⭐ 📝📝 · `M`

Hypothesis couvre le Python ; `playgroundVoting.ts` — l'autre moitié du contrat
de parité — n'a aucun test à propriétés.

✅ **Fait — et le plus rentable des quatre premiers items du Lot 4 en
rapport trouvailles/effort.** `voter-app/src/lib/playgroundVoting.axioms.test.ts`
(nouveau, `fast-check` en devDependency) reporte les 7 critères de la matrice
Python contre `ruleWinnerFromRanks`, mais sur un domaine plus large que
l'exhaustif du Lot 4.3 : n ∈ [3,6] candidats, m ∈ [3,25] électeurs (Python
`_profiles4` fige n=4 exactement). La classification satisfait/viole n'est
**pas recopiée aveuglément** — vérifiée en la rejouant réellement sur ce
domaine plus large, seed fixe pour la reproductibilité (même leçon que
Lot 4.1/4.2 : `derandomize`/seed non fixé retrouve des choses différentes à
chaque run — littéralement observé ici avant de fixer la seed, voir plus bas).

**Six corrections réelles trouvées, toutes vérifiées à la main contre le
backend et corrigées dans `test_voting_criteria_matrix.py`** (donc pas des
particularités du seul moteur front) :

- **`baldwin`** échoue l'indépendance aux clones, mais seulement à partir de
  n=6 — un nombre de candidats que la stratégie Hypothesis de Python (figée
  à exactement 4) ne génère structurellement jamais.
- **`condorcet` (Copeland sur le front)** échoue aussi l'indépendance aux
  clones — mais ceci n'est PAS une correction de la classification Python :
  la clé `"condorcet"` du fichier Python désigne `get_condorcet_winner` (le
  critère strict), une fonction différente de la règle front `condorcet`
  (Copeland, étiquetée « Condorcet (Copeland) » dans `RULE_LABELS`). Un
  score net victoires-défaites comme celui de Copeland est un cas d'école de
  méthode manipulable par clonage — confirmé indépendamment côté backend
  (`get_copeland_winner`), classification propre à ce fichier TS.
- **`irv`, `coombs`, `benham`, `raynaud`** élisent chacun un perdant de
  Condorcet dans des profils spécifiques — pas un problème de nombre de
  candidats cette fois, juste des profils que les 200 exemples Hypothesis
  figés de Python n'avaient jamais échantillonnés.

**Effet de bord important : ce dernier groupe a révélé que le critère
« perdant de Condorcet » était bien plus fuyant que prévu.** Plutôt que de
corriger au coup par coup à chaque nouvelle seed `fast-check`, un balayage
systématique direct en Python (~15 000-24 000 profils par méthode/critère,
au lieu des 200 exemples Hypothesis fixes) a permis de trancher les 7
critères une bonne fois : Condorcet gagnant, Pareto et monotonie
correspondent exactement à la classification existante ; indépendance aux
clones aussi, à `baldwin` près (déjà trouvé) ; majorité avait UNE cellule de
plus à corriger — `dowdall` (même famille que la faiblesse déjà connue de
Borda : une règle positionnelle peut perdre face à une majorité si son score
s'égalise exactement avec un rival, un cas assez rare — 2 sur ~6500 essais
— pour avoir échappé aux 200 exemples Hypothesis aussi).

Ce balayage plus volumineux reste un échantillon plus large, pas une preuve
exhaustive comme celle du Lot 4.3 — si une recherche encore plus large
trouverait une 7e cellule reste une question ouverte, nommée plutôt que
poursuivie indéfiniment (même logique que le report de participation/
symétrie par renversement au Lot 4.1).

### 4.5 — Contre-exemples de la littérature comme fixtures nommées ⭐⭐ 📝📝📝 · `M`

Paradoxe de Condorcet, exemples de manipulation Borda, profils de Saari…
chaque exemple classique devient une fixture nommée et sourcée (clé BibTeX de
`docs/research/`). Double emploi test + pédagogie.

✅ **Fait.** Avant d'écrire quoi que ce soit, vérifié que le cas le plus
évident (une élection réelle où méthode ⇒ vainqueur différent) était déjà
couvert : le backtest Burlington 2009 / Alaska 2022 (`voter-app/src/lib/
realElections.ts`, sourcé PrefLib 00005 et arXiv:2303.00108) existe déjà,
testé, cité — refaire la même chose aurait été du travail en double. Le
vrai trou était les **exemples synthétiques classiques**, absents des deux
moteurs. Quatre ajoutés dans
`fast_api_voter/api/tests/test_literature_counterexamples.py`, chacun
vérifié à la main avant d'être committé, chacun sourcé (nouvelles clés
BibTeX `saari1995`, `tideman1987`, `fishburn_brams1983` ajoutées à
`docs/research/bibliography.bib` **et** à `THEORY.md` §11, qui les partage) :

- **Paradoxe de Condorcet** (Condorcet, 1785, déjà cité) — le cycle
  fondateur à 3 électeurs/3 candidats, déjà décrit en THEORY.md §4.1,
  maintenant testé et lié depuis là.
- **Désaccord des règles positionnelles** (Saari, 1995) — un profil minimal
  de 4 bulletins (trouvé par recherche exhaustive sur tous les profils
  jusqu'à 17 bulletins) où pluralité, Borda et anti-pluralité élisent
  chacune un candidat différent sur les mêmes préférences. Nouvelle
  sous-section THEORY.md §4.5.
- **Motivation de Ranked Pairs** (Tideman, 1987) — réutilise le contre-
  exemple de non-indépendance aux clones de Copeland déjà trouvé au
  Lot 4.4, en le recadrant comme LE problème que Tideman a conçu Ranked
  Pairs pour résoudre : même profil, même clonage, Copeland change de
  vainqueur, Ranked Pairs non. Documenté sur la fiche Copeland de
  THEORY.md §2.1.
- **Paradoxe du non-vote** (Fishburn & Brams, 1983) — clôt une petite
  tranche, nommée et sourcée, du critère de participation que le Lot 4.1
  avait reporté en bloc (le fuzzing complet reste hors périmètre, mais au
  moins UN exemple canonique, vérifié à la main tour par tour, est
  maintenant permanent). Un électeur dont le bulletin sincère élit son
  DERNIER choix, alors que s'abstenir aurait élu son 2e choix — trouvé par
  recherche (2 millions de profils synthétiques), retenu pour sa taille
  (8 bulletins) après avoir écarté des exemples plus grands. Nouvelle
  sous-section THEORY.md §4.6.

**Effet de bord** : en cherchant la formulation exacte de la propriété de
Ranked Pairs/River pour cette fixture, une survivance de Lot 4.1/4.2 a été
repérée dans THEORY.md — la fiche Ranked Pairs affirmait « indépendante des
clones » sans la réserve du cas générique (marges non exactement égales),
alors que le Lot 4.2 avait déjà trouvé et documenté l'exception dégénérée
dans le fichier de tests. Corrigé au passage (§2.4), avec renvoi vers le
test qui pin le contre-exemple.

### 4.6 — Z3 / model checking ⭐ 📝📝📝 · `L` *(expérience à risque assumé)*

Prouver l'équivalence de deux implémentations sur des configurations bornées
plutôt que d'échantillonner. **Peut très bien échouer** (encodage trop lourd,
explosion combinatoire) — et un échec documenté « voilà pourquoi le SMT ne passe
pas à l'échelle sur ce problème » est un excellent carnet d'expérience.

✅ **Fait — verdict : adopté partiellement.** Carnet complet dans
[`docs/exploration/EXP-002-z3-formal-voting-proofs.md`](docs/exploration/EXP-002-z3-formal-voting-proofs.md).
Résumé : `z3-solver` encode les décomptes de voix comme des variables
entières symboliques (pas des profils concrets) et prouve — au lieu
d'échantillonner — qu'aucun électorat, quelle que soit sa taille, ne peut
violer une propriété donnée. **Minimax et Schulze respectent le critère de
Condorcet pour TOUS les électorats possibles** jusqu'à n=7 candidats
(`unsat` en moins d'une minute) — plus fort que tout ce que les Lots
4.1-4.4 avaient établi sur ce point précis, puisque ceux-ci vérifient
toujours un nombre *fini* de profils, aussi grand soit-il.

**Le risque assumé par le plan s'est matérialisé, mais pas comme prévu**
— pas une explosion combinatoire (Z3 n'a jamais peiné à raisonner), mais
un encodage IRV **silencieusement faux** : un premier essai a "prouvé"
qu'IRV ne peut jamais élire un perdant de Condorcet, ce qui contredit un
contre-exemple déjà vérifié à la main au Lot 4.4
(`test_condorcet_loser_irv_can_be_violated`). La cause : la règle de
départage de ce moteur (éliminer TOUS les candidats à égalité au minimum,
pas un minimum strict unique) manquait dans l'encodage — Z3 a fidèlement
prouvé une propriété vraie d'une règle *différente* de la vraie
`get_irv_winner`. Une fois corrigé (revérifié contre le contre-exemple
connu avant de refaire confiance à quoi que ce soit), Z3 a aussi trouvé un
contre-exemple à 7 bulletins **prouvé minimal** — une garantie
qu'aucun échantillonnage ne peut offrir par construction.

**Ce qui est committé** : `fast_api_voter/api/tests/test_z3_formal_proofs.py`
(minimax + Schulze uniquement, ~5s en CI) et `z3-solver` en dépendance de
dev (aucun conflit de version Python, contrairement à `pref_voting` au
Lot 4.2). L'encodage IRV corrigé n'est **pas** committé — plus fragile
(plus de branchements, plus de façons de mal représenter une règle réelle)
pour un gain déjà obtenu autrement par les Lots 4.1-4.4 ; documenté en
détail dans le carnet d'expérience plutôt que maintenu comme code
permanent.

---

## Lot 5 — Robustesse des tests eux-mêmes

*Qui teste les tests ?* Angle de récit fort : la couverture à 91 % ment-elle ?

| Item | Pourquoi ici | Effort | Solidité | Récit | Statut |
|---|---|---|---|---|---|
| **Score de mutation ciblé + gating** | mutmut/Stryker tournent mais sont informatifs. Un seuil *par module critique* (le moteur uniquement) vaut mieux qu'un score global mou. | M | ⭐⭐⭐ | 📝📝📝 | ✅ déjà fait (chantier antérieur au présent plan, PR #177/#187/#214 et suivantes) — `mutmut` scopé à `simulation_ranked_utils.py`/`simulation_score_utils.py` (plancher 70%, `[tool.mutmut]` dans `pyproject.toml`), Stryker scopé à `playgroundVoting.ts` (`thresholds.break: 80`, `stryker.config.json`) ; les deux gatent réellement (`continue-on-error` retiré, confirmé dans `mutation-testing.yml`) |
| **`pytest-randomly`** | Ordre d'exécution aléatoire → révèle les tests couplés par effet de bord (déjà rencontré avec le limiter partagé). | S | ⭐⭐ | 📝📝 | ✅ `pytest-randomly==5.0.0` en dépendance de dev, actif sur chaque run local/CI dès l'installation (aucune config requise) |
| **Chasse au flake nocturne** | Relancer la suite N fois et tracker l'instabilité. Le « flaky check » existe en e2e, rien côté backend. | M | ⭐⭐ | 📝📝 | ✅ `scripts/check_flaky_backend.py` + `.github/workflows/flaky-check-backend.yml` (nightly + push develop + `workflow_dispatch`) — détail sous le tableau |
| **Régénérabilité de `engineParity.json`** | Un job qui régénère et diffe prouverait que le fichier n'a pas été édité à la main — aujourd'hui c'est une règle écrite, rien ne l'applique. | S | ⭐⭐⭐ | 📝📝 | ✅ déjà fait (chantier antérieur, PR #172) — `scripts/check_engine_parity_drift.sh`, gate CI (`openapi-contract.yml`'s « Generated artifacts in sync » job), vérifié en vrai à chaque PR de ce plan touchant le moteur (Lots 4.2-4.4) |
| **`syrupy`** (snapshots pytest) | Sorties de simulation riches, plus lisibles qu'des assertions à la main. | S | ⭐ | 📝 | ✅ `api/tests/test_compare_all_methods_snapshot.py` — le rapport `compare_all_methods` (26 méthodes × 5 champs) capturé en un seul snapshot `.ambr` lisible (345 lignes), plutôt que des assertions champ par champ. `random.seed`/`np.random.seed` fixées explicitement avant construction de l'électorat (`create_voter`/`create_candidate` n'ont pas de paramètre de seed propre) — stabilité vérifiée sur 3 runs consécutifs |

**Chasse au flake nocturne, détail.** `scripts/check_flaky_backend.py` relance
la suite 3× (chacune un process indépendant, un ordre `pytest-randomly`
différent à chaque fois — pas des retries dans le même process, qui ne
verraient pas un couplage lié à l'ordre de *collecte*), et diffe le résultat
de chaque test entre les 3 exécutions. Détecteur vérifié en direct sur un
couplage synthétique injecté (un test qui lit un état de module écrit par
un autre) avant de lui faire confiance — le genre de vérification que ce
projet applique systématiquement à ses propres détecteurs.

Piège rencontré en le construisant : la première version passait
`-o addopts=""` sans rien d'autre, ce qui supprime aussi bien le
`--ignore` du fichier Schemathesis lent que la parallélisation `-n auto` du
`addopts` par défaut — un run séquentiel de la suite complète (avec le
fichier lent en plus) est passé de ~80s à ~1000s, soit ~50 minutes pour 3
runs. Corrigé en réinjectant explicitement les deux. Effet de bord accepté,
documenté dans le script : avec `-n auto`, un couplage qui n'existe qu'au
sein d'un même *worker* peut atterrir sur des workers différents à chaque
run et donc échouer (ou réussir) de façon constante plutôt que de varier —
ce script ne le détecterait pas comme flaky, mais un échec constant est de
toute façon déjà attrapé par la suite normale à chaque PR, donc rien ne
reste durablement invisible.

**3 exécutions réelles de la suite complète (1974 tests, ~16-18s chacune)
lancées pendant ce développement : 0 flake trouvé.**

---

## Lot 6 — Ce que l'analyse statique ne voit pas

| Item | Pourquoi ici | Effort | Solidité | Récit | Statut |
|---|---|---|---|---|---|
| **Couverture *runtime*** (Istanbul sur e2e + `coverage.py`) | Trouve le code jamais exécuté **même en usage réel** — angle mort total de vulture/knip qui sont statiques. Après avoir supprimé 16 500 lignes mortes, la question « qu'est-ce qui reste inatteignable ? » est légitime. | M | ⭐⭐⭐ | 📝📝📝 | ✅ backend 34,4 %, frontend 63,15 % en usage réel (voir §6.5) |
| **`basedpyright`/pyright** | Moteur d'inférence différent de mypy → attrape d'autres choses. Combien, sur un code déjà mypy-strict-clean ? Bonne question d'expérience. | S | ⭐⭐ | 📝📝📝 | ✅ 2 vrais bugs trouvés et corrigés (voir §6.2) |
| **`refurb`** + **`perflint`** | Modernisation Python et anti-patterns de perf — pertinent sur un moteur CPU-bound. | S | ⭐ | 📝📝 | ✅ 145 + 85 findings, informationnel (voir §6.3) |
| **`type-coverage`** (TS) | % de code réellement typé (les `any` implicites que `tsc` laisse passer). | S | ⭐⭐ | 📝📝 | ✅ 99,58 % (voir §6.4) |
| **`eslint-plugin-sonarjs`** | Complexité cognitive (≠ cyclomatique, déjà mesurée par radon) + bugs courants. | S | ⭐⭐ | 📝 | ✅ 2 bugs d'affichage corrigés, 304 findings informationnels (voir §6.6) |
| **`pip-licenses` / `license-checker`** | Conformité de licences sur un repo public MIT. | S | ⭐ | 📝 | ✅ 0 violation, promu en **gate bloquant** (voir §6.7) |

### 6.1 — Audit de pertinence des commentaires · `L` · ⭐⭐ 📝📝📝

Aucun outil du repo ne regarde les commentaires. Ils sont pourtant du **code
non compilé, non testé, jamais vérifié** — la seule zone du projet où une
affirmation fausse peut survivre indéfiniment sans que rien ne la signale.

**Poids mesuré** (2026-09-07) : ~174 k tokens côté `fast_api_voter/api`
(26,6 % du volume) et ~79 k côté `voter-app/src` (9,5 %), soit **~253 k tokens
de commentaires et docstrings**.

**L'audit trie en quatre catégories, avec un traitement distinct :**

| Catégorie | Traitement | Justification |
|---|---|---|
| **Périmé** — décrit du code qui a changé | Corriger ou supprimer | Activement nuisible : induit en erreur humains et agents. La passe de doc du 06/09 (PR #313) a traité ce problème au niveau des fichiers `.md` ; personne ne l'a jamais fait au niveau des commentaires. |
| **Redondant** — paraphrase le code | Supprimer | Coût pur, zéro information. Sur du code typé mypy-strict, un docstring qui répète la signature n'apporte rien. |
| **Archéologique** — récit d'une session (« le 25/08, essayé X, échoué parce que… ») | **Migrer vers `docs/exploration/`** | C'est du carnet d'expérience égaré dans du code source (cf. Lot 0.2). |
| **« Pourquoi »** — contrainte, bug passé, alternative écartée | **Garder en place, non négociable** | C'est le mécanisme anti-répétition du Lot 0.5 à l'échelle de la ligne. Le docstring de `api/core/ratelimit.py` expliquant *pourquoi 120/min et pas 30* est ce qui empêche de le « ré-optimiser » à 30 et de recasser l'e2e. |

**Cadrage explicite — ce que cet audit n'est pas** : ce n'est pas un projet
d'économie de tokens, et il ne consiste pas à *déplacer* les commentaires hors
du code. L'hypothèse a été mesurée puis écartée : `package-lock.json` seul
(~155 k tokens) coûte plus cher que l'intégralité des commentaires du frontend
(~79 k), et son exclusion via `.claudeignore` (§12.2) est gratuite et sans
risque. Surtout, un commentaire voyage **dans le même diff** que le code qu'il
explique — pas un fichier récap, qui dérive. Sortir les « pourquoi » du code
fabriquerait à grande échelle exactement la dérive que la PR #313 a passé une
session à réparer. Le bénéfice visé ici est la **justesse**, pas le volume ;
la réduction de tokens n'est qu'un effet de bord des catégories « redondant »
et « archéologique ».

**La mesure à publier** : *« j'ai audité 253 k tokens de commentaires — quelle
proportion mentait ? »* Ce chiffre n'existe nulle part, et il se prête à une
méthode reproductible sur d'autres projets.

**Piste d'outillage** : pas d'outil établi pour la détection de commentaires
périmés. Deux approches à essayer et à comparer dans le carnet d'expérience —
(a) heuristique par `git log` : commentaire dont la dernière modification est
nettement plus ancienne que celle des lignes de code qu'il surplombe ;
(b) passe LLM par lot sur des blocs `(commentaire, code)`. Le contraste entre
les deux est lui-même un bon contenu.

✅ **Fait.** Phase 1 (heuristique `git blame`, [EXP-001](docs/exploration/
EXP-001-audit-commentaires-heuristique-git-blame.md)) avait présélectionné
**329 candidats** sur ~5 200 blocs scrutés. Phase 2 (passe sémantique) : 6
agents en parallèle, un par tranche de ~55 candidats, chacun lisant le
commentaire **et** le code environnant (pas seulement les dates) pour
trancher entre les quatre catégories du plan — aucune classification prise
pour argent comptant sans vérification du contenu réel (grep de la fonction
citée, comptage manuel d'un décompte annoncé, relecture de la formule
décrite), dans la continuité de la méthode du Lot 4.

**Résultat, sur les 329 candidats** :

| Catégorie | Nombre | Traitement |
|---|---|---|
| **Périmé** (factuellement faux) | 15 | Corrigé |
| **Redondant** (paraphrase pure) | 59 | Supprimé |
| **Archéologique** (récit de session) | 0 | — |
| **Pourquoi** (contrainte/rationale) | 45 | Gardé tel quel |
| **Toujours-valide** (vrai négatif) | 210 | Aucune action |

**La mesure demandée par le plan** : sur les candidats déjà présélectionnés
comme suspects par l'heuristique temporelle, **4,6 % (15/329) étaient
effectivement faux** — le reste du signal temporel de phase 1 était du bruit
(code qui bouge sans rapport, cf. le 0/5 de phase 1). Rapporté à l'ensemble
des ~5 200 blocs de commentaires du dépôt, ça descend sous 0,3 % de
commentaires confirmés menteurs — la très large majorité des commentaires de
ce dépôt décrit fidèlement le code qu'elle surplombe. Le vrai motif commun
aux 15 Périmé n'est pas l'usure ordinaire mais la **migration non
nettoyée** : 5 commentaires évoquaient encore Flask (retiré depuis, cf.
CLAUDE.md) ou Jest (jamais utilisé ici, le projet tourne sous Vitest) comme
s'ils étaient encore d'actualité — un mode de péremption bien plus
systématique qu'un simple oubli isolé. Les autres étaient des erreurs
factuelles ponctuelles (une formule mal décrite, un décompte de "fiches"
resté à 57 alors que le fichier en contient 62, une référence à un composant
supprimé). **0 Archéologique** : ce dépôt n'a jamais laissé de récit de
session dans son code source — cohérent avec la discipline déjà en place
(carnet d'expérience séparé depuis le Lot 0.2).

74 commentaires corrigés/supprimés au total, sur 44 fichiers (11 backend,
33 frontend). `ruff`/`mypy`/pytest (1975 tests) et `tsc`/`vitest` (1697
tests)/`eslint` restent verts après coup — seuls des commentaires ont
changé, jamais le code qu'ils décrivaient. Détail complet (fichier, ligne,
avant/après) dans l'historique de la PR ; [`docs/comment-audit/README.md`](
docs/comment-audit/README.md) porte le verdict de synthèse des deux phases.

### 6.2 — `basedpyright` comme second avis ⭐⭐ 📝📝📝 · `S`

✅ **Fait.** Scope aligné sur celui de `mypy` (`api/` hors `api/tests/`,
config dans `[tool.basedpyright]` de `pyproject.toml`, mode `standard` —
le mode `strict`/`all` de basedpyright est nettement plus agressif que
`mypy --strict` sur la propagation des types `Unknown`, ce qui aurait noyé
le signal sous ~15 000 avertissements rien que sur les stubs manquants de
`z3` dans les tests). Résultat brut : **50 erreurs**, qui se répartissent
en 3 groupes très inégaux — 2 vrais bugs (corrigés, cf. ci-dessous, ce qui
ramène le compte définitif à **34**), 32 faux positifs pydantic et 2 faux
positifs isolés :

- **2 vrais bugs, trouvés et corrigés** — invisibles à `mypy --strict` par
  construction : `reportPossiblyUnboundVariable` n'a pas d'équivalent
  activé par défaut dans le bundle `--strict` de mypy (il faudrait
  `--enable-error-code possibly-undefined` explicitement, absent de
  `mypy.ini`).
  - `api/domain/simulations/base.py` (`_simulate_votes_worker`, endpoint
    legacy `POST /api/v2/simulations`) : `simulationType` est testé par
    sous-chaîne (`"votes" in simulation_type`, etc.), pas par enum. Un
    premier `if/elif/elif` mutuellement exclusif calcule les données, mais
    un second groupe de `if` indépendants (pas `elif`) retestait les mêmes
    sous-chaînes pour assembler la réponse — une valeur contenant plusieurs
    mots-clés à la fois (`"ranked_scores"`, `"votes_scores"`, …) entrait
    dans une deuxième branche dont les variables n'avaient jamais été
    assignées. **Confirmé en direct** : une requête HTTP réelle avec
    `simulationType: "ranked_scores"` plantait avec
    `UnboundLocalError: cannot access local variable 'voters_n'`, 500 non
    géré. Corrigé en assemblant chaque bloc de réponse directement dans la
    branche qui calcule ses données (plus de second test indépendant
    possible) ; test de non-régression paramétré ajouté
    (`test_multi_keyword_simulation_type_does_not_crash`). Cet endpoint est
    exactement celui que Schemathesis (Lot 3) ne peut pas fuzzer utilement
    — `KNOWN_FAILURES` le liste `[loose-req]`, schéma volontairement peu
    typé — donc un angle mort réel du filet Lot 3, comblé ici par un outil
    différent.
  - `api/domain/polity/run_polity_simulation.py` : une liste `nominees = []`
    sans annotation, remplie sous garde `if nominee is None: continue`
    puis relue plus loin avec accès `.citizen_id`/`.pledged_platform`/etc. —
    basedpyright infère `list[Citizen | None]` faute d'annotation explicite
    et signale un accès possible sur `None`. Corrigé par une annotation
    `nominees: list[Citizen] = []` documentant l'invariant déjà garanti par
    la garde.
- **32 faux positifs pydantic, tous de la même origine** : `mypy.ini`
  déclare `plugins = pydantic.mypy`, qui comprend `Field(default, ge=, le=)`
  et `Field(default_factory=SomeModel)` comme fournissant un défaut réel.
  basedpyright n'a pas d'équivalent — son support natif de
  `@dataclass_transform` (PEP 681) ne résout pas systématiquement les
  surcharges de `Field()` combinant un défaut positionnel et des
  contraintes de validation (`ge=`/`le=`/`min_length=`/…). Résultat :
  18× `reportArgumentType` sur `Field(default_factory=SomeConfigClass)`
  (idiome pydantic standard pour une config imbriquée entièrement
  optionnelle) et 14× `reportCallIssue` sur des paramètres qui ont
  pourtant un défaut (`BacksliddingCandidate(name=..., x=...)` sans `y`
  signalé comme argument manquant alors que
  `y: float = Field(0.0, ge=-1.0, le=1.0)`). Vérifié à la main sur
  plusieurs cas : aucun n'est un vrai défaut de valeur manquant, tous
  fonctionnent correctement à l'exécution.
- **2 faux positifs isolés, même famille de cause** (le vérificateur ne
  peut pas prouver une invariante garantie par du code qu'il a bien vu,
  mais dont il ne fait pas la synthèse jusqu'au point d'usage) :
  - `active` possiblement non lié dans `workers_mechanisms.py`
    (`_abstention_worker`) — `num_rounds` y est borné en dur
    (`max(1, min(5, ...))`) avant la boucle qui l'utilise, donc toujours
    ≥ 1 en pratique ; basedpyright ne peut pas prouver cette invariante
    arithmétique locale.
  - `theory/workers.py`'s `_irv` helper : `remaining.remove(last)` où
    `last` vient de `Counter[str | None].most_common()[-1][0]` — le
    `None` a pourtant déjà été retiré juste avant par
    `tally.pop(None, None)`, mais basedpyright ne réduit pas le type
    `Counter[str | None]` après un `.pop()` sur une clé précise (aucun
    vérificateur de type Python courant ne le fait — ce n'est pas
    spécifique à basedpyright).
  Les deux laissés tels quels (pas de `# pyright: ignore` ajouté pour des
  cas isolés et bien compris individuellement).

Outil informationnel (comme vulture/radon/deptry), pas un nouveau gate
bloquant — `./scripts/audit.sh --quality` le lance et publie le compte
dans son rapport. Les 34 faux positifs restants (32 pydantic + 2 isolés)
sont un baseline connu, documenté ici plutôt que supprimé ligne par ligne.

### 6.3 — `refurb` + `perflint` ⭐ 📝📝 · `S`

✅ **Fait, informationnel uniquement** — l'item le moins prioritaire du lot
(⭐ solitaire), traité à la hauteur de son propre budget : câblé, mesuré,
documenté, **pas** corrigé ligne par ligne (145 + 85 findings, une
campagne de correction aurait dépassé de très loin l'effort `S` annoncé).

- **`refurb`** (`[tool.refurb]`, `pyproject.toml`) : **145 findings**, dont
  77 (plus de la moitié) une seule et même suggestion `FURB123` —
  `dict(x)`/`list(x)` → `x.copy()`. Un vrai gain, même minuscule, sur un
  moteur CPU-bound (`.copy()` évite le dispatch générique du constructeur
  `dict`/`list`) mais purement mécanique et réparti sur ~30 fichiers —
  laissé en baseline à corriger incrémentalement plutôt qu'en un seul
  diff géant. Le reste (14× `lambda x: x[k]` → `operator.itemgetter(k)`,
  quelques `in [x, y, z]` → `in (x, y, z)`, …) est du même ordre :
  correct, sans risque, mais zéro urgence.
- **`perflint`** (plugin pylint, `[tool.pylint.main]`/`["messages
  control"]`) : la règle par défaut la plus bruyante,
  `loop-invariant-statement`, désactivée après l'avoir laissée tourner une
  fois — **1 593 occurrences à elle seule** sur les boucles denses
  par-électeur/par-candidat de ce moteur, très majoritairement des accès
  d'attribut/indexation que pylint ne peut pas prouver invariants,
  pas de vraies invariantes de boucle déplaçables. Avec ce seul filtre
  retiré : **85 findings** exploitables (55 `use-tuple-over-list`, 12
  `use-list-copy`, 9 `use-list-comprehension`, 9
  `use-dict-comprehension`) ; zéro occurrence des règles les plus
  concrètes (`unnecessary-list-cast`, `incorrect-dictionary-iterator`,
  `memoryview-over-bytes`, `dotted-import-in-loop`,
  `loop-global-usage`) — déjà propre sur ces axes-là.

Les deux tournent via `./scripts/audit.sh --quality` (sections dédiées),
comme vulture/radon/deptry — aucun gate ajouté.

### 6.4 — `type-coverage` ⭐⭐ 📝📝 · `S`

✅ **Fait, informationnel.** `npx type-coverage` nu plante sur ce dépôt
(`Cannot read properties of undefined (reading 'Unknown')`) — le cache
isolé de `npx` résout sa **propre** copie de `typescript`, incompatible
avec le paquet lui-même ; installé comme vraie devDependency de
`voter-app` (résout alors le `typescript@5.9.3` du projet), le problème
disparaît. Piège suffisamment non-évident pour être noté explicitement
dans `scripts/audit.sh` (commentaire inline) plutôt que redécouvert plus
tard.

**Résultat mesuré : 99,58 %** (146 940 / 147 548 positions typées), 608
`any` implicites au total — 328 dans des fichiers de test (essentiellement
des mocks Recharts/fetch typés `any` par choix, un idiome de test
standard, pas une lacune), **280 dans du code source réel**, réparties sur
28 fichiers. Aucun fichier généré (`src/api/types.gen.ts`) dans la liste —
déjà 100 % typé. Câblé dans `./scripts/audit.sh --quality`, pas de gate
bloquant ajouté (même traitement que le reste du Lot 6) ; l'outil expose
nativement un mécanisme de cliquet (`--at-least`/`--update-if-higher`,
qui écrirait un seuil dans `package.json`) qui rendrait une régression
future bloquante à coût quasi nul — noté ici comme suite possible plutôt
qu'ajouté maintenant, pour rester à la hauteur de l'effort `S` annoncé par
cet item.

### 6.5 — Couverture *runtime* : ce qui reste inatteignable en usage réel · `M` · ⭐⭐⭐ 📝📝📝

✅ **Fait**, en script manuel (pas un gate CI — voir la justification dans
le carnet). Backend : `coverage.py` autour d'un petit point d'entrée dédié
(`fast_api_voter/scripts/run_e2e_coverage_server.py`) plutôt qu'autour
d'`uvicorn` directement — nécessaire car `uvicorn` se re-signale lui-même
en fin d'arrêt gracieux (idiome délibéré pour un code de sortie correct),
ce qui contourne l'`atexit` dont dépend la sauvegarde de `coverage.py`, un
piège qui aurait rendu tout le chantier silencieusement inopérant sans
vérification directe (fichier `.coverage` absent malgré des logs d'arrêt
parfaitement propres). Frontend : Istanbul (`vite-plugin-istanbul@9.0.1`),
qui s'installe et fonctionne sans réserve sur **Vite 8.2.2** malgré
l'avertissement du plan — l'écosystème a rattrapé Vite 8 depuis, et
Istanbul a l'avantage de fonctionner sur les deux projets Playwright
(chromium **et** firefox), contrairement à l'API V8 de Playwright
(`page.coverage`, Chromium seulement) prévue comme repli.

**La mesure** : sous la vraie suite e2e, le backend n'exécute que **34 %**
de ses lignes (contre 91,56 % en unitaire) et le frontend **63 %** (contre
87,05 %). Deux trouvailles concrètes, vérifiées à la main plutôt que
prises pour argent comptant :

- `api/domain/polity/*` (2 813 lignes, ~19 % du backend, ~99 % unitaire) :
  **0 % e2e**, et pour cause — `api/main.py` n'enregistre aucune route
  `polity` (`grep` direct, zéro résultat) et le frontend n'y fait aucune
  référence. Un sous-système de recherche entier, entièrement testé,
  structurellement hors du produit qu'un utilisateur réel touche.
- `/simulation/compare` (retiré du routage vers `/playground` depuis
  `voter-app/src/routes.ts`) a toujours une route backend vivante
  (`POST /compare`, la couverture unitaire la **plus basse** du backend à
  65 %, 7 % en e2e) et un hook frontend (`useDebouncedSimulation.ts`) à
  100 % de fonctions couvertes par son propre test — et **invisible à
  `knip`**, dont le graphe de reachabilité considère un import depuis un
  fichier de test comme un usage valide. Ni la détection statique ni la
  couverture unitaire, seules ou combinées, ne pouvaient signaler ce cas ;
  il a fallu la question « une route le monte-t-elle réellement ? ».

Détail complet (protocole, deux pièges de mécanisme trouvés et corrigés
en vérifiant plutôt qu'en faisant confiance, chiffres par fichier, coût de
l'instrumentation et pourquoi ça reste manuel) dans
[EXP-003](docs/exploration/EXP-003-couverture-runtime-e2e.md).
`scripts/e2e_coverage.sh` reste disponible pour une prochaine passe de
nettoyage, à la demande.

### 6.6 — `eslint-plugin-sonarjs` ⭐⭐ 📝 · `S`

✅ **Fait, informationnel + 2 vrais bugs corrigés au passage.**
`jsx-a11y`/`unused-imports` sont bloquants dans `eslint.config.js`
aujourd'hui, mais seulement parce que leur backlog a été ramené à zéro
avant de les activer (commentaires du fichier lui-même) — le même chemin
n'est pas praticable ici à l'échelle de l'effort `S` annoncé : **307
findings** sur la première passe (`voter-app/eslint.sonarjs.config.js`,
config séparée de la config bloquante, lancée via `npm run lint:sonarjs` /
`./scripts/audit.sh --quality`), dominés par des suggestions de charge
cognitive plutôt que des bugs : `no-nested-conditional` (103),
`parameterized-tests` (39, suggère `it.each` plutôt que des `it()`
répétés), `cognitive-complexity` (38), `prefer-specific-assertions` (33,
ex. `toHaveLength(n)` plutôt que `toBe(n)` sur un `.length`).

Les 5 occurrences de `no-all-duplicated-branches` (un opérateur ternaire
dont les deux branches renvoient la même valeur) vérifiées une par une
plutôt que classées en bloc — **2 étaient de vrais bugs d'affichage,
corrigés** :

- `DeliberationPanel.tsx:295` — `regret_improvement >= 0 ? '' : ''`
  n'affichait jamais de signe « + », alors que la ligne parallèle juste
  au-dessus (`polarization_change >= 0 ? '+' : ''`) le fait pour la même
  famille de badges. Corrigé (`'+' : ''`) ; le test existant
  (`DeliberationPanel.test.tsx`) ne vérifie que la présence du badge, pas
  son texte exact, donc rien à mettre à jour côté tests.
- `AnimatedVoteCount.tsx:449` — `isEliminated ? '#dc3545' : isWinner ?
  color : color` : la branche `isWinner` ne changeait jamais rien (les
  deux issues valent `color`), en plus d'être imbriquée
  (`no-nested-conditional` sur la même ligne). Simplifié en `isEliminated
  ? '#dc3545' : color` — comportement de rendu strictement identique (le
  vainqueur reste déjà signalé par le 🏆 et le libellé « (vainqueur) »
  juste à côté), juste le code mort retiré.

Les 3 autres `no-all-duplicated-branches` sont dans des fixtures de test
(`PartyDynamicsPanel.test.tsx`, `PrimarySimulator.test.tsx`,
`SortitionPanel.test.tsx`) — un champ de mock à valeur constante des deux
côtés d'un ternaire vestige, sans effet sur ce que le test vérifie
réellement. `no-identical-functions` (1) : un vrai doublon de fermeture
`reaches` entre Ranked Pairs et River dans `playgroundVoting.ts` — réel,
mais dédupliquer un helper dans ce fichier précis exige de re-passer la
suite de parité moteur (`CLAUDE.md` — « the dual voting engine, keep it in
sync ») pour un gain cosmétique ; laissé en baseline, hors budget `S`.
`no-trivial-assertions` (1) : un `expect(true).toBe(true)` déjà commenté
comme placeholder assumé (`IdeologyHeatmap.test.tsx`) — pas un oubli.

**304 findings restants** après les deux corrections. Câblé dans
`./scripts/audit.sh --quality`, pas de gate ajouté à `eslint.config.js` —
même traitement informationnel que le reste du Lot 6.

### 6.7 — `pip-licenses` / `license-checker` ⭐ 📝 · `S`

✅ **Fait — le seul item du Lot 6 promu en gate CI bloquant**, pas
informationnel : contrairement à refurb/perflint/sonarjs (des centaines de
findings de style), la conformité de licence part d'une **baseline déjà à
zéro** une fois correctement scopée aux dépendances de *production* — le
même chemin que `jsx-a11y`/`unused-imports` (backlog nul avant activation),
mais atteint directement plutôt qu'à corriger.

**Le scope compte tout** : un premier passage sur l'environnement complet
(prod + dev mélangés) trouvait 4 paquets GPL/LGPL (`pylint`, `refurb`,
leur dépendance `astroid`, et `semgrep`) — tous des outils de dev ajoutés
pendant ce Lot 6 ou déjà présents, jamais distribués avec l'application.
Confirmé en isolant un venv propre avec `pip install -r requirements.txt`
seul (39 paquets, aucune dépendance de dev) : **zéro** licence GPL/AGPL/
LGPL, uniquement MIT/BSD/Apache/MPL-2.0/PSF-2.0. Côté frontend, `license-
checker-rseidelsohn` (fork maintenu — l'original `license-checker` est
abandonné) avec `--production` (exclut les devDependencies nativement,
contrairement à Python qui n'a pas cette distinction) : 283 paquets, même
verdict, aucune licence restrictive. Deux faux signaux vérifiés à la main
avant d'être écartés : `pip-licenses` classait `face`/`peewee` (dépendances
transitives de `semgrep`) en « UNKNOWN » — lu directement le fichier
`LICENSE` installé de chacun (BSD et MIT respectivement) plutôt que de
laisser planer le doute ; `license-checker-rseidelsohn` classait
`voter-app` lui-même en « UNLICENSED » alors que son `package.json` déclare
`"license": "MIT"` — un artefact du scan sur le paquet racine, exclu
explicitement (`--excludePackages`).

**Le gate** (`fast_api_voter/scripts/check_license_compliance.sh`,
backend ; une invocation `license-checker-rseidelsohn --production
--onlyAllow` en CI, frontend) tourne dans un venv **isolé**, pas le venv
combiné prod+dev partagé par le reste de la CI — sinon les 4 paquets GPL/
LGPL des outils de dev feraient échouer le gate à chaque run, ou pire,
forceraient à les allow-lister explicitement et à perdre tout le sens du
contrôle. Câblé en étape bloquante dans `backend-ci-cd-pipeline.yml` et
`frontend-ci-cd-pipeline.yml`, et dans `scripts/audit.sh` (section
gating, pas informationnelle comme le reste du Lot 6). Vérifié à la main
avec un test négatif (`--allow-only="MIT"` seul) avant de faire confiance
au code de sortie : `slowapi` (MIT License, orthographe différente de
`MIT`) fait bien échouer le gate — confirmant qu'il a des dents et pas
seulement une liste blanche assez large pour ne jamais mordre.

---

## Lot 7 — Surfaces perçues par l'utilisateur

| Item | Pourquoi ici | Effort | Solidité | Récit | Statut |
|---|---|---|---|---|---|
| **a11y sur *toutes* les routes** | `routes.ts` est déjà « data » — boucler dessus et échouer si une surface n'est pas auditée, même mécanique que l'anti-rot e2e existant. | M | ⭐⭐⭐ | 📝📝 | ✅ déjà fait (voir sous le tableau) |
| **Régression visuelle** (Playwright screenshots / Lost Pixel) | L'app est quasi entièrement visuelle (SVG, cartes, Recharts) et **rien** ne détecte qu'une carte s'affiche de travers. | M | ⭐⭐⭐ | 📝📝📝 | ✅ Playwright natif (Docker épinglé), gate CI (voir sous le tableau) |
| **Viewport mobile en e2e** | App pédagogique → usage mobile probable, zéro test mobile aujourd'hui. | M | ⭐⭐ | 📝📝 | ✅ `tests/e2e/mobile.spec.ts` + projet `mobile` (voir sous le tableau) |
| **`i18next-parser`** + `eslint-plugin-i18next` | Clés orphelines/manquantes et chaînes en dur (5 encore trouvées à la main le 06/09). | M | ⭐⭐ | 📝📝 | ✅ `i18next-cli lint` (voir sous le tableau) |
| **Pseudo-locale à chaînes longues** | Casse les layouts avant que l'anglais ou une future langue ne le fasse. | S | ⭐⭐ | 📝📝📝 | ✅ `pseudo.ts` + `tests/e2e/pseudo-locale.spec.ts` (voir sous le tableau) |
| **Webkit en e2e** | Seuls chromium et firefox tournent aujourd'hui. | S | ⭐⭐ | 📝 | ⏳ bloqué — dépendances système manquantes (`sudo npx playwright install-deps` requis, pas de sudo sans mot de passe dans cet environnement) |

**a11y sur toutes les routes, détail.** Vérifié avant de commencer à
construire quoi que ce soit (même discipline que le Lot 4.5) : le mécanisme
décrit par cet item — boucler sur `routes.ts`, échouer si une surface n'a
pas d'ancre — **existe déjà**, écrit le 2026-08-22
(`test(e2e): make the route table the single source of truth`, avant même
ce plan) et étendu le 2026-09-06. `tests/e2e/accessibility.spec.ts` audite
avec `axe-core` (WCAG 2.1 AA) chacune des 5 `SURFACES` de `src/routes.ts`
individuellement, plus `assertEverySurfaceAnchored()` qui fait échouer la
suite si une route est ajoutée sans ancre `data-testid`, plus le mode sombre
du playground et l'opérabilité clavier (rail des moments, candidats/partis
déplaçables aux flèches). Rejoué en direct : **10/10 tests passent**
(`npx playwright test tests/e2e/accessibility.spec.ts`, ~15s). Rien à
construire — l'écart entre l'intitulé de cet item et l'état réel du code
n'avait simplement jamais été vérifié.

**Régression visuelle, détail.** Deux candidats évalués : le mécanisme natif
de Playwright (`toHaveScreenshot`) contre Lost Pixel. Ce dernier écarté sans
essai — vérification de maintenance faite *avant* d'installer quoi que ce
soit (même réflexe que le fork `license-checker-rseidelsohn` au Lot 6.7) :
Lost Pixel a annoncé le 22/04/2026 que l'équipe rejoignait Figma et
arrêtait le produit, dépôt archivé le jour même. Le vrai travail n'était pas
le choix de l'outil mais la stabilité : nouveau `playwright.visual.config.ts`
(séparé de la config e2e existante), baselines générées et comparées
**uniquement** dans l'image Docker officielle Playwright épinglée à la
version exacte de `@playwright/test` (`mcr.microsoft.com/playwright:v1.62.1-
noble`) — la seule façon trouvée de ne pas dépendre du hasard de ce que
`ubuntu-latest` rend un jour donné. Quatre pièges réels trouvés et corrigés
en le faisant échouer en vrai, pas en le supposant robuste : un flash de
légende intermittent au montage (`FlipReveal.tsx`, ~1 échec/3 runs, tracé à
un race dépendant de React Strict Mode) : réglé par une attente de son cycle
de vie fixe plutôt qu'un polling optimiste ; un timeout du serveur de dev
sans rapport avec le rendu (compilation à la demande d'un chunk lazy) : réglé
en testant contre le vrai build de prod ; `ParliamentCanvas` qui, sans
backend, n'affiche pas un hémicycle légèrement décalé mais son propre état
d'erreur permanent (« hémicycle indisponible ») — aurait verrouillé un bug
structurel incapable d'échouer un jour ; et surtout une tolérance
`maxDiffPixelRatio: 0.01` choisie « par prudence » qui, vérifiée contre une
régression injectée (couleur d'un marqueur changée en dur), s'est révélée
laisser passer exactement ce genre de régression (0,07 % des pixels d'une
carte) — supprimée, la même injection échoue alors proprement. Stabilité
mesurée, pas supposée : 8/8 runs natifs et 6/6 runs Docker consécutifs à
zéro échec sous la config finale. Câblé en job CI séparé
(`visual-regression` dans `e2e.yml`, backend + frontend, aucun besoin de la
suite e2e fonctionnelle) — réserve honnête : le mécanisme `container:`
GitHub Actions n'a pas pu être observé sur un vrai run (pas de droit de push
dans ce worktree), donc recommandé de ne l'ajouter aux *required status
checks* qu'après son premier run réel. Deux pièges supplémentaires trouvés
en rebasant sur `develop` juste avant le merge (donc après la rédaction
initiale de cette fiche, pas hypothétiques) : le `testIgnore` de
`playwright.visual.config.ts` posé au niveau racine de
`playwright.config.ts` ne s'appliquait en réalité jamais — chaque projet
(`chromium`/`firefox`) déclare son propre `testIgnore` (pour
`mobile.spec.ts`, ajouté par un autre item de ce même Lot 7 mergé entre-
temps) qui **remplace** celui de la racine au lieu de s'y ajouter ; confirmé
en rejouant `npx playwright test` après rebase (241 tests au lieu de 227,
`visual.spec.ts` exécuté hors Docker). Et `scripts/test-visual-docker.sh`
laissait des fichiers appartenant à `root` dans le dépôt (conteneur lancé
sans `--user`), cassant silencieusement la commande suivante lancée en tant
qu'utilisateur normal. Les deux corrigés, suite par défaut revérifiée à 227
tests et suite Docker à 7/7. Carnet complet (les six pièges, le détail de la
vérification du détecteur) :
[`docs/exploration/EXP-004-regression-visuelle-playwright-screenshots.md`](docs/exploration/EXP-004-regression-visuelle-playwright-screenshots.md).

**`i18next-parser` + `eslint-plugin-i18next`, détail.** `i18next-parser`
est officiellement déprécié (avertissement npm à l'installation : « use
i18next-cli instead ») — jamais adopté, même règle que
`license-checker` → `license-checker-rseidelsohn`. Bascule vers
`i18next-cli`, ce qui a demandé trois correctifs successifs avant d'avoir
un outil qui tourne réellement en CI :
1. Les versions récentes exigent Node ≥22 (`execa` récent dépend de
   `Set.prototype.union`, ES2024) — or `frontend-ci-cd-pipeline.yml` épingle
   Node 20, comme le poste local. Épinglé sur `i18next-cli@1.0.0` (la
   première version, sans `execa` en dépendance directe).
2. `npm audit` a quand même signalé `glob@11.0.0-11.0.3` (injection de
   commande, GHSA-5j98-mcp5-4vw2) dans les dépendances transitives de cette
   version. `npm audit fix` naïf réintroduisait le blocage Node 22 (bump
   d'`execa`) — corrigé en ciblant `glob` seul via `overrides` (même motif
   déjà en place pour `typescript`/`ws`/`js-yaml`/…), vérifié 0
   vulnérabilité **et** CLI toujours fonctionnel sur Node 20.
3. Le pattern d'exclusion `'!src/**/*.test.{ts,tsx}'` était silencieusement
   ignoré (le `glob()` interne à `i18next-cli` ne route pas les entrées
   `!`-préfixées comme des exclusions depuis glob v9+) — remplacé par un
   extglob POSIX dans un seul motif (`!(*.test|*.d)`), vérifié directement
   via un script Node ad-hoc avant de faire confiance à la config.

`i18next.config.ts` (nouveau, racine `voter-app/`) configure `lint` — la
détection de chaînes en dur, pas l'extraction/écriture de fichiers de
ressources (voir ci-dessous pourquoi). Bruit de fond énorme au départ (2927
trouvailles) : l'app étant SVG-native (skill `voter-ui`), l'écrasante
majorité était des attributs de présentation SVG (`fill`, `stroke`,
`textAnchor`, `viewBox`, …), pas du texte utilisateur. `ignoredAttributes`
réduit ça à 714 en deux passes (props génériques, puis ~40 attributs SVG).
Deux vraies trouvailles corrigées dans le lot : `aria-label="Close"` en dur
(anglais, alors que l'app démarre en français) dans les primitives
partagées `components/ui/modal.tsx` et `components/ui/alert.tsx` — jamais
`useTranslation`, remplacées par `t('common.close')`, la même clé déjà
utilisée par `DatasetExportModal.tsx`. Les 714 restants sont dominés par du
bruit générique et des littéraux de clé interne (`"fptp"`, `"irv"`,
`"module-electorate"`, …) — informationnel via `scripts/audit.sh`, même
statut que sonarjs/refurb/perflint (Lot 6).

**Périmètre explicitement réduit : pas de détection clés
orphelines/manquantes.** Les commandes `status`/`extract`/`types` de
`i18next-cli` supposent toutes un `output` uniforme
`{{namespace}}.{{language}}.ts` (confirmé en lisant `node_modules/
i18next-cli/types/types.d.ts` directement) — incompatible avec la
convention réelle du projet, où le namespace par défaut n'a pas de préfixe
(`src/i18n/locales/fr.ts`) alors qu'un namespace nommé en a un
(`playground.fr.ts`). `status` tourne mais rapporte des chiffres non
fiables (cherche `translation.fr.ts`, qui n'existe pas). Réorganiser la
disposition des fichiers i18n du projet pour coller à l'outil a été jugé
hors périmètre de cet item — même discipline que « ne pas adopter un outil
qui force à casser une convention du projet ». La détection de chaînes en
dur (la moitié qui a trouvé les 2 vraies erreurs ci-dessus) reste la
livraison de cet item.

**Pseudo-locale à chaînes longues, détail.** `src/i18n/pseudoize.ts` accentue
chaque chaîne, la rallonge d'environ 35 % (motif `~~~`) et l'encadre de
`⟦…⟧` — les marqueurs de crochets servent à la fois de repère visuel de
troncature et d'ancre pour qu'un test e2e sache que le bundle pseudo est
bien actif (pas juste le fallback français). Les tokens `{{interpolation}}`
sont préservés tels quels. `pseudo.ts` / `playground.pseudo.ts` sont des
artefacts générés (même statut que `src/api/types.gen.ts`) — `scripts/
gen-pseudo-locale.ts` (exécuté via `npx jiti`, ajouté en dépendance
explicite plutôt que de compter sur sa présence transitive via
tailwindcss ; `npm run gen:pseudo-locale`) les régénère depuis `fr.ts`/
`playground.fr.ts`, et `src/i18n/pseudoize.test.ts` regénère l'arbre en
mémoire et le compare à ce qui est commité — échoue bruyamment si `fr.ts`
change sans régénération, même rôle que les tests de parité fr/en
existants.

Le locale `pseudo` est câblé dans `src/i18n/index.ts` avec le même
mécanisme de lazy-loading que `en` (jamais dans le bundle principal),
mais **jamais exposé dans le sélecteur de langue de l'app** — seulement
atteignable en écrivant `pseudo` dans `localStorage.votelab_lang` (la même
clé que lit déjà `i18next-browser-languagedetector`), ce que fait
`tests/e2e/pseudo-locale.spec.ts` via `page.addInitScript` avant chaque
navigation. Les 5 `SURFACES` de `routes.ts` sont balayées et chacune est
vérifiée sans dépassement horizontal de page
(`document.documentElement.scrollWidth` vs `clientWidth`, tolérance 2px) —
un test qui a effectivement pris deux round-trips pour être fiable.
D'abord une fausse piste : une première exécution donnait de faux échecs à
cause d'un `vite preview` déjà présent sur le port 3000 de cet
environnement, que `reuseExistingServer` réutilisait silencieusement au
lieu de démarrer le vrai serveur de dev — diagnostiqué en traçant
`localStorage` et `i18next` directement dans le navigateur avant de
conclure à un bug applicatif ; identifié après coup comme le propre
conteneur Docker de l'item « Régression visuelle » ci-dessus (`--network=
host`), tournant en parallèle dans le même environnement, pas un processus
extérieur à cette session. Ensuite un vrai bug, trouvé seulement en CI (pas
reproductible en local, fonts différentes) : `/decouvrir` dépassait de 62px
en largeur sous firefox. Cause réelle, indépendante de l'environnement :
`padFor()` collait tout le padding `~~~~` en un seul bloc à la fin de la
phrase entière plutôt que par mot — un unique « mot » artificiellement
long et non-sécable, un mode de défaillance qu'aucune vraie langue ne
produit (les langues plus longues ont des mots plus longs, pas un mot
géant en fin de phrase). Corrigé en distribuant le padding mot par mot
(`pseudoizeSegment` découpe sur les espaces). Les 5 tests passent contre le
vrai serveur, chromium + firefox (10 tests) après ce correctif.

---

## Lot 8 — Performance

| Item | Pourquoi ici | Effort | Solidité | Récit | Statut |
|---|---|---|---|---|---|
| **`pytest-benchmark` + seuils** | Une régression de perf sur `simulation_ranked_utils` est aujourd'hui totalement invisible. | M | ⭐⭐⭐ | 📝📝 | ✅ gate CI bloquant, seuils absolus (voir sous le tableau) |
| **Charge (k6 ou Locust)** | Le rate-limit 120/min a été calibré au jugé ; un test de charge donne le vrai plafond du pool de threads. | M | ⭐⭐⭐ | 📝📝📝 | ✅ script manuel Locust, pas de gate CI (voir sous le tableau) |
| **Invariant de perf du form-lock** | Documenté dans le skill `voter-ui`, jamais mesuré. React Profiler + assertion. | M | ⭐⭐ | 📝📝📝 | ✅ `PlaygroundPage.perf.test.tsx` (voir sous le tableau) |
| **Budget de bundle** | Seuil de taille sur le build Vite, échec si dépassement. | S | ⭐⭐ | 📝 | ✅ `size-limit` câblé dans `npm run build` (voir sous le tableau) |

**`pytest-benchmark` + seuils, détail.** `api/tests/test_engine_benchmarks.py`
— 27 cas (les 21 méthodes ordinales du set de parité `gen_engine_parity.py`,
Kemeny-Young exact/approximation séparés, les 5 méthodes cardinales), tous
mesurés à 1000 électeurs / 8 candidats (le vrai plafond de production,
`api/schemas/election.py`), pas des tailles arbitraires. Deux faits vérifiés
avant de choisir le design, pas supposés : `pytest-benchmark` désactive sa
mesure de temps sous `pytest-xdist` (utilisé par la suite normale via
`-n auto`, `backend-ci-cd-pipeline.yml`) — vérifié en direct que ça fait
planter chaque test (`AttributeError`) plutôt que de passer sans rien
mesurer, mais reste la mauvaise invocation dans les deux cas — donc invocation dédiée, comme
`test_schema_contract.py`/Schemathesis (`--ignore` dans `pyproject.toml`,
son propre step CI, mirroré dans `ci-local/backend.Dockerfile`) ; et la
comparaison relative à une baseline stockée
(`--benchmark-autosave`/`--benchmark-compare-fail`) est un piège de
flakiness connu sur un runner CI partagé — confirmé, pas assumé, par
recherche des modes de défaillance documentés de l'outil. D'où le choix :
**plafonds absolus généreux** (100 ms pour les tallies O(n)/le scoring
cardinal, 500 ms pour l'élimination/l'appariement/Kemeny), même philosophie
que le `timeout: 30_000` de la suite e2e — toutes les méthodes mesurées
tiennent en moins de 14 ms au plafond de production, laissant 15-160x de
marge. Détecteur vérifié en direct (même discipline que ce plan applique
systématiquement, EXP-002/EXP-004) : une régression O(n²) injectée dans
`get_copeland_winner` (boucle redondante sur l'électorat) a fait passer sa
moyenne de 3,7 ms à 1101,6 ms — détectée, puis le code retiré et revérifié
vert. Effet de bord trouvé pendant ce travail : en relançant les benchmarks
pendant qu'un serveur + Locust tournaient en parallèle (item suivant), les
mêmes mesures ont varié de 20-50 % — une preuve directe, sur cette machine,
que le bruit d'exécution est réel et qu'un plafond absolu large l'absorbe
sans discussion, là où une comparaison relative à pourcentage serré en
aurait fait un faux positif. Détail complet, y compris le protocole de
recherche sur la fragilité CI de l'outil :
[`docs/exploration/EXP-006-pytest-benchmark-engine-perf.md`](docs/exploration/EXP-006-pytest-benchmark-engine-perf.md).

**Charge (Locust), détail.** Python retenu sur k6 : le backend est un
projet Python de bout en bout, `locust` s'installe dans le même venv que le
reste des dépendances de dev (`requirements-dev.txt`) sans nouveau langage
ni toolchain — k6 (JS/Go) aurait été défendable mais sans bénéfice net ici.
Lecture du code AVANT tout scénario de charge
(`api/core/worker_dispatch.py`) : chaque route `/api/v2` est `async def`
mais délègue son calcul via `asyncio.to_thread` derrière un **sémaphore
partagé unique** (`MAX_CONCURRENT_WORKERS = 4`), pas l'exécuteur par défaut
— et ce sémaphore est global au process, alors que le rate-limit
(`check_v2_rate_limit`, 120/min) est **par chemin** (`key_style="url"`) et
par IP. C'est cette asymétrie que le test de charge devait vraiment
mesurer, pas juste « ça tient à combien de req/s ». `scripts/
loadtest_v2_engine.py` : une classe de trafic léger réaliste
(`profile-simulate`, l'endpoint que 120/min a explicitement été calibré
contre, cf. le docstring de `ratelimit.py`) + une classe Monte-Carlo dont le
temps de service (~1 s) s'auto-limite naturellement sous 120/min même en
boucle fermée — ce qui permet de monter en concurrence sans jamais déclencher
LE rate-limit de ce chemin, isolant ainsi la saturation du sémaphore de
celle du rate-limit. Quatre paliers réels (`-u` doublé à chaque fois) :
latence médiane 3,0 s (4 utilisateurs) → 7,2 s (10) → 14,0 s (20) → 25-30 s
(40) — croissance quasi linéaire avec la concurrence au-delà des 4 slots du
sémaphore, **zéro 429/503 sur toute la plage testée**. La vraie trouvaille :
le rate-limit par-chemin ne protège structurellement pas une ressource
VRAIMENT partagée entre chemins — aucun réglage du chiffre 120 n'aurait pu
corriger ça, et le premier symptôme visible d'une vraie surcharge ici est
une page qui semble geler, pas une erreur. Deux pièges de méthode trouvés et
corrigés avant de faire confiance aux chiffres : un premier jet tournait
sans le savoir contre un process tiers déjà présent sur le port `:4434`
(collision de port silencieuse, un quasi-doublon du même piège déjà
documenté par EXP-003 dans ce repo) ; un deuxième calibrage (les deux
classes en boucle quasi fermée) mesurait en réalité le rate-limit, pas le
sémaphore (45 % d'échecs, 100 % des 429), corrigé en s'appuyant sur l'ordre
réel des dépendances FastAPI (rate-limit avant le sémaphore) confirmé en
lisant le code. **Script manuel, pas de gate CI** — même raisonnement
qu'EXP-003 (coût réel, chiffre spécifique à la machine qui l'exécute,
documenté dans `CONTRIBUTING.md` § « Charge »). Détail complet, chiffres et
protocole : [`docs/exploration/EXP-007-locust-v2-thread-pool-ceiling.md`](docs/exploration/EXP-007-locust-v2-thread-pool-ceiling.md).

**Invariant de perf du form-lock, détail.** Le skill `voter-ui` documente le
form-lock depuis longtemps (« à first paint, seuls les `*-toggle` sont dans le
DOM ») et `PlaygroundPage.test.tsx` en vérifie déjà la **forme** (des testids
précis absents du DOM) — mais rien ne le mesurait. Avant d'écrire une seule
assertion, deux approches naïves ont été essayées contre le vrai environnement
de test (Vitest + jsdom) et **rejetées avec des chiffres réels**, pas par
principe :

- **Un plafond en millisecondes absolues sur le premier rendu** : sur 8 runs
  consécutifs du même code inchangé, le premier commit va de **58 ms (à froid,
  JIT/modules pas encore chauds) à ~13 ms (à chaud)** — un facteur ×4.5 de pur
  bruit d'environnement, qui noierait n'importe quelle régression assez petite
  pour être plausible. Ce projet s'est déjà fait piéger une fois par exactement
  cette catégorie d'erreur (calibration des timeouts CI, Lot 3 « Timeouts &
  backpressure ») ; pas la peine de recommencer.
- **Mesurer une régression injectée** (monter `ElectorateComposer` sans son
  `Collapsible`, en double) montre la même chose autrement : la fenêtre de
  durée observée (13,5-20,7 ms) **chevauche entièrement** la fenêtre de la
  baseline (12,4-23,2 ms) — un vrai doublon de panneau, mesuré honnêtement, ne
  ressort pas du bruit.

Ce qui a survécu, vérifié en injectant de vraies régressions puis en confirmant
un retour au vert après retrait (même discipline que EXP-004 « Lost Pixel » du
Lot 7) :

- **Invariant de comptage de commits** : à first paint, exactement **2**
  commits synchrones (le montage, puis le passage `loading: true` du hook de
  diagnostics live) — stable sur 8+ runs, y compris avec la régression
  d'ElectorateComposer ci-dessus injectée (toujours 2 : monter un panneau en
  trop n'ajoute pas de commit, il alourdit juste le premier). Ce que ce
  compteur détecte réellement, prouvé par une seconde injection : une chaîne
  d'effets eager non liés à une interaction (`useEffect` → `setState` → un
  second `useEffect` qui en dépend) fait bien passer le compte à **3**,
  détecté par l'assertion, confirmé revenir à 2 après retrait.
- **Comparaison relative de coût** : ouvrir un panneau `Collapsible` trivial
  (formulaire, pas de calcul) coûte 0,7-3,1 ms ; ouvrir la lentille de
  probabilité (vrai calcul client, attendu comme le fait déjà
  `PlaygroundPage.test.tsx`) coûte 7,5-16,8 ms — un ratio de **×5,4 à ×11,7**
  sur 6 mesures indépendantes. Le seuil retenu (×3) est délibérément sous la
  pire valeur observée, pas calé sur la moyenne — même marge de sécurité que
  les seuils CI du Lot 3.

Trouvaille méthodologique, documentée dans le fichier de test et dans
EXP-004 : **le Profiler de React ne mesure que la phase de rendu/commit,
jamais le corps d'un effet** — un calcul lourd glissé dans un `useEffect` (pas
dans le rendu lui-même) est invisible au Profiler, quel que soit son coût CPU
réel. Vérifié en injectant une boucle de 20M itérations dans un effet de
montage : zéro changement mesurable sur `actualDuration`. C'est pour ça que
l'invariant de comptage de commits (qui, lui, réagit à un effet qui déclenche
un état) et le test de forme déjà existant (qui réagit à un DOM qui apparaît)
restent complémentaires du Profiler, pas redondants avec lui.

**Budget de bundle, détail.** Baseline mesurée sur un vrai `npm run build`
avant de choisir un chiffre (jamais inventé) : 121 chunks JS, **3 004 492
octets bruts**, **938 786 octets gzip** (mesure manuelle `gzip -c | wc -c`,
pour comparaison) — le rapport Vite signale déjà, sans y toucher, que 2 chunks
dépassent son `chunkSizeWarningLimit` par défaut (500 kB) : `recharts`
(590 kB) et le chunk vendor principal `index` (580 kB), tous deux attendus
(une lib de graphiques + React/router/zustand/tanstack-query, pas du code
applicatif ballonné). `build.chunkSizeWarningLimit` seul ne fait qu'avertir,
jamais échouer — donc pas suffisant tel quel pour « échec si dépassement »
demandé par l'item.

Outillage : `bundlesize` (dernier publié 2024-03, **>2 ans**, abandonné —
écarté) et `vite-plugin-bundlesize` (dernier publié il y a ~1 an, mainteneur
seul, signal modeste) rejetés sur la fraîcheur, même réflexe que le rejet de
Lost Pixel (EXP-004, Lot 7) et le remplacement `license-checker` →
`license-checker-rseidelsohn` (Lot 6.7). `rollup-plugin-visualizer` et
`vite-bundle-analyzer` sont bien maintenus (publiés il y a 4-6 semaines) mais
sont des outils de **visualisation**, pas de gate à seuil. **`size-limit`**
(Andrey Sitnik — mainteneur connu de l'écosystème PostCSS/Autoprefixer),
publié il y a ~6 semaines, `@size-limit/file` en plugin (mesure par glob sur
des fichiers déjà construits, indépendant du bundler — exactement le besoin
ici puisque `build/` est déjà produit par Vite) : adopté.

**Piège de version trouvé en l'installant, pas juste supposé** : `npm install`
sans épingler résout `size-limit@12.1.0` alors que `@size-limit/file@13.0.3`
(la dernière version publiée du plugin) déclare une peer-dependency **exacte**
sur `size-limit@13.0.3` — un `npm ls` après coup confirme l'arbre invalide
(`ELSPROBLEMS`). Cause trouvée en creusant : `size-limit@13.0.3` a relevé son
exigence Node à `^22.18.0 || ^24.0.0 || >=26.0.0`, laissant tomber le Node 20
sur lequel ce dépôt tourne encore (même contrainte, déjà rencontrée et déjà
documentée pour `dependency-cruiser` au Lot 2 — « 18.x exige Node ≥22 »).
Résolu en épinglant la **paire exacte compatible** `size-limit@12.1.0` +
`@size-limit/file@12.1.0` (peer-dependency exacte vérifiée, aucune version en
caret) plutôt que la dernière publiée — aucune règle Dependabot `ignore`
ajoutée (le dépôt n'en a pour aucun autre pin de ce type non plus ; ce
paragraphe sert la même fonction que le commentaire du Lot 2 pour
dependency-cruiser, à relire si Dependabot propose la bascule 13.x).

**Le budget retenu : 1 MB (brotli), mesuré à 810,88 kB aujourd'hui — une marge
de ~23 %.** `size-limit` mesure en brotli par défaut (pas gzip) ; sur ce
build, brotli descend à 810,88 kB contre 951,57 kB en gzip (~15 % de mieux),
cohérent avec l'écart habituel entre les deux algorithmes. 1 MB laisse de la
place à une vraie croissance de fonctionnalités sans être assez large pour ne
jamais mordre — même logique de marge que le Lot 3 (« pas si juste que la
croissance légitime casse la CI en boucle, pas si large que ça ne veuille rien
dire »). Câblé dans `npm run build` lui-même
(`tsc --noEmit && vite build && npm run build:size`, `build:size` = `size-limit`)
plutôt qu'en étape CI séparée : `frontend-ci-cd-pipeline.yml` appelle déjà
`npm run build` sans modification, donc le gate est actif sur chaque PR sans
toucher au workflow.

**Vérifié en injectant une vraie régression** (deux chunks dupliqués dans
`build/assets/`, portant le total mesuré à 1,1 MB) : `size-limit` échoue avec
`exit 1` et un message précis (« Package size limit has exceeded by 99.25 kB »)
— retiré, retour au vert confirmé (`exit 0`, 810,88 kB). Piège opérationnel
noté en le vérifiant : `npx size-limit | tail` masque le vrai code de sortie
derrière celui de `tail` dans le pipeline — vérifié avec `$?` juste après la
commande, sans pipe, avant de faire confiance au signal.

---

## Lot 9 — Sécurité approfondie

| Item | Pourquoi ici | Effort | Solidité | Récit | Statut |
|---|---|---|---|---|---|
| **DAST — ZAP baseline** | SAST (Semgrep/CodeQL) ne voit que le code, jamais le comportement de l'app qui tourne. | M | ⭐⭐ | 📝📝 | ✅ `.github/workflows/dast.yml`, nightly + push:develop, non-gating (voir sous le tableau) |
| **Fuzzing à couverture** (`atheris` ou `hypofuzz`) | Bien plus profond qu'Hypothesis seul sur le moteur et les parseurs. | L | ⭐⭐ | 📝📝📝 | ✅ `atheris`, 2 harnais + workflow CI planifié, 4 bugs réels trouvés et corrigés (voir sous le tableau) |
| **`guarddog`** (Datadog) | Détecte les paquets *malveillants* (typosquatting, install-scripts hostiles) — angle mort de pip-audit/Trivy qui ne voient que les CVE connues. | S | ⭐⭐ | 📝📝📝 | ✅ CI (cron + push develop, informational — voir sous le tableau) |
| **`trufflehog`** | Secrets **vérifiés actifs**, pas juste des motifs (complète gitleaks + detect-secrets). | S | ⭐ | 📝 | ✅ local + CI, informational (voir sous le tableau) |
| **OSV-Scanner** | Base de vulnérabilités différente de Trivy, recouvrement imparfait. Mesurer l'écart réel est une bonne expérience. | S | ⭐ | 📝📝📝 | ✅ local + CI, informational (voir sous le tableau) |
| **Signature d'images + provenance SLSA** (cosign/sigstore) | Suite logique du SBOM + Scorecard déjà en place. | M | ⭐⭐ | 📝📝📝 | ✅ SBOM signé (cosign, keyless) + provenance SLSA (`attest-build-provenance`), pas l'image (voir sous le tableau) |
| **`minimumReleaseAge`** (via Renovate) | Attendre 3-7 j avant d'adopter une release : vraie défense contre les paquets compromis. | S | ⭐⭐⭐ | 📝📝 | ✅ déjà satisfait (Dependabot `cooldown`, sans migration — voir sous le tableau) |

**`guarddog` + `trufflehog` + OSV-Scanner, détail.** Les trois exécutés pour de
vrai contre l'état réel de ce dépôt (pas juste `--help`), avec vérification
manuelle d'un échantillon de trouvailles — même discipline que le reste de ce
plan (EXP-004/EXP-006 : faire échouer/confirmer le détecteur avant de lui
faire confiance).

*TruffleHog* : scan filesystem scopé au code source réel (`api/`, `scripts/`,
`src/`, `tests/`, `docs/` — 1297 chunks, 10,3 Mo) — **0 secret vérifié-actif,
0 même non-vérifié**, 66,9 ms. Câblé en `--results=verified` uniquement (le
`--results` par défaut inclut aussi unverified/unknown, du bruit que Gitleaks
+ detect-secrets couvrent déjà par motif) : complète Gitleaks avec une
vérification live contre l'API du fournisseur plutôt qu'un second passage
regex. Local (`scripts/audit.sh`) + CI (`trufflesecurity/trufflehog`,
nouveau step non-bloquant dans le job `gitleaks` existant de `audit.yml`).

*OSV-Scanner* : comparaison réelle avec Trivy — [`docs/exploration/
EXP-009-osv-scanner-vs-trivy-overlap.md`](docs/exploration/EXP-009-osv-scanner-vs-trivy-overlap.md)
pour le protocole et les chiffres complets. Verdict court : **0 vs 0** sur
l'état actuel des dépendances (cross-vérifié aussi avec pip-audit, 0) — pas un
écart nul par construction, un écart nul *mesuré*, confirmé par un détecteur
dont la sensibilité a été vérifiée en direct (deux paquets sciemment
obsolètes, `urllib3==1.26.4`/`Jinja2==2.4.1`, remontent chacun 18 CVE réels).
Piège d'environnement trouvé et contourné, pas contourné en silence : la
source de données par défaut d'OSV-Scanner (`deps.dev`, résolution gRPC) a
timeout dans cette session sandboxée alors que l'API REST du même service
répond en 200 ms — `--data-source native` évite ce chemin gRPC (utilisé ici
en local ET en CI, pour que les deux restent comparables). Un deuxième piège,
propre à un *worktree* git (pas au dépôt) : `osv-scanner scan source -r .`
trouve silencieusement 0 source de paquets depuis ce worktree, alors que les
mêmes lockfiles sont trouvés sans problème via `-L` explicite ou depuis une
copie hors-worktree — `scripts/audit.sh` utilise `-L` par fichier pour cette
raison (plus rapide de toute façon, pas besoin d'exclure `node_modules`/`.venv`).
Local + CI (job `osv-scanner`, workflow réutilisable officiel des
mainteneurs, non-bloquant).

*`guarddog`* : pas de carnet d'expérience dédié (item bas-cérémonie — un
outil trouve quelque chose ou pas contre un dépôt propre), mais vérifié pour
de vrai contre l'état réel de ce dépôt, pas juste `--help`. **Quatre
trouvailles réelles**, aucune un paquet malveillant :

- Le parseur de `guarddog pypi verify` rejette silencieusement toute ligne
  `requirements.txt` dont le commentaire inline suit un nombre de espaces
  interprété comme faisant partie du spécificateur de version — **11 lignes
  sur 15** de `fast_api_voter/requirements.txt` (le style de commentaire
  documentant chaque CVE/raison de pin, voir n'importe quelle ligne du
  fichier) échouaient silencieusement (`This entry will be ignored`) avant
  correctif. `scripts/audit.sh` et le job CI passent désormais par une copie
  temporaire des commentaires inline retirés (`sed`), jamais le fichier
  source lui-même — **15/15** lignes analysées après correctif, vérifié.
- Sur les 15 paquets de production analysés (après correctif), **7 signaux**
  de la catégorie `threat-*` (la seule qui compte réellement — les
  `capability-*`, bien plus nombreux — ~50 au total — ne sont que des
  patterns de code normaux comme "ouvre un socket" ou "supprime un fichier")
  sont sortis, sur 5 paquets (`python-dotenv`, `PyYAML`, `slowapi`, `scipy`,
  `numpy`) — **les 7 vérifiés à la main sur le vrai code source, tous de
  vrais faux positifs** : `threat-filesystem-read` sur `python-dotenv` et
  `slowapi` matche la chaîne littérale `".env"` — le fichier que ces
  bibliothèques ont pour rôle explicite de lire ; `threat-runtime-dynamic-loader`
  sur `PyYAML` matche `__import__(` dans le constructeur `!!python/object`
  de son propre loader — une fonctionnalité connue de la bibliothèque, pas un
  ajout suspect ; `threat-filesystem-read` sur `numpy` matche `/etc/shadow`
  dans `numpy/lib/tests/test__datasource.py` — une liste de **chemins de
  test négatif** (`malicious_files = [...]`) que le code est censé *rejeter*,
  pas lire ; `threat-runtime-obfuscation-unicode` sur `numpy` et `scipy`
  matche le caractère unicode légitime `µs` (microseconde) — un stub de
  types (`numpy/__init__.pyi`) et un docstring d'exemple `%timeit`
  (`scipy/optimize/_numdiff.py`), confondus avec un homoglyphe d'obfuscation ;
  `threat-runtime-system-info` sur `scipy` matche `platform.machine()`/
  `platform.uname()` dans son propre test suite (`test_distributions.py`),
  utilisés pour un skip conditionnel par OS, pas une collecte télémétrique.
- Piège d'environnement sans rapport avec le paquet, trouvé deux fois : la
  première tentative PyPI (avant diagnostic) est restée bloquée **18+
  minutes à 0 % CPU** — `/proc/<pid>/net/tcp` a montré une connexion
  `SYN-SENT` figée vers une adresse IPv6 de pypi.org (confirmée par
  résolution inverse), le trafic IPv4 vers le même hôte fonctionnant
  normalement ; contourné en forçant IPv4 au niveau de `socket.getaddrinfo`
  pour le diagnostic PyPI (qui a ensuite abouti, chiffres ci-dessus). Le même
  piège est réapparu côté `guarddog npm verify` (`voter-app/package.json`,
  28 dépendances de prod) malgré ce correctif — `ss` a montré une seconde
  connexion IPv6 `SYN-SENT` distincte, cohérent avec un client HTTP
  asynchrone (`aiohttp`/`aiodns`) qui résout ses propres DNS sans passer par
  `socket.getaddrinfo` — non contourné faute de temps ; le côté npm de cet
  item reste donc **vérifié sur l'interface CLI et le format de sortie
  uniquement**, pas sur un run complet réussi dans cette session. Sans
  confirmation que GitHub Actions partage cette pathologie réseau (peu
  probable — c'est un symptôme de sandbox, pas du paquet ni du dépôt), le job
  CI reste par prudence hors de la boucle PR normale (cron + push `develop`
  seulement, même raisonnement que le job `image-scan` déjà dans ce
  fichier), non-bloquant dans tous les cas.
- `pygit2<1.19` (dépendance de `guarddog`) n'a pas de wheel `cp314` (vérifié
  contre l'index PyPI — les wheels `cp314` n'existent qu'à partir de
  `pygit2==1.20.0`) : installer `guarddog` dans le venv 3.14 réel de ce dépôt
  échouerait. Pas ajouté à `requirements-dev.txt` pour cette raison ; job CI
  dédié avec son propre `actions/setup-python` (3.13).

**DAST — ZAP baseline, détail.** `.github/workflows/dast.yml`, nouveau
workflow dédié (pas un job dans `audit.yml` : c'est le seul scanner du plan
qui a besoin d'une app **réellement démarrée**, backend uvicorn + build/preview
frontend, comme `e2e`/`visual-regression` dans `e2e.yml` — un besoin
structurellement différent des jobs `audit.yml`, qui scannent tous des
fichiers). Mode `baseline` (spider + scan **passif uniquement**, zéro payload
d'attaque) choisi et vérifié avant tout câblage, pas supposé : lu le `--help`
réel de `zap-baseline.py` et la doc zaproxy.org avant d'écrire une ligne de
YAML. `zap-api-scan.py` (mode piloté par `openapi.gen.json`, déjà présent)
a été sérieusement considéré — un import OpenAPI est en théorie plus exhaustif
qu'un spider sur une API pure — mais rejeté : sa propre doc dit qu'il
« imports the definition… and then runs an Active Scan against the URLs
found » et « attempt[s] exploitation » (SQLi, etc.) — exactement le mode
agressif que cet item du plan exclut explicitement, pas une nuance. Action
officielle `zaproxy/action-baseline` (v0.15.0, dernier commit sur `master`
daté du 06/09/2026 — dependabot mergé activement, dépôt non abandonné),
épinglée au SHA du tag comme toutes les autres actions tierces de ce dépôt.

Ciblé sur les **deux** surfaces, dans le même job : le frontend
(`localhost:3000`, build + `vite preview` réel — mêmes commandes que le job
`visual-regression`, pas le serveur de dev) et le backend directement
(`localhost:4434/api/v2/docs`, l'entrée Swagger UI) plutôt qu'un seul scan du
frontend en espérant que le spider découvre l'API par ricochet — vérifié en
direct que ce n'est pas fiable : `EXP-004` avait déjà documenté que la
plupart des pages de l'app ne font aucun appel réseau au montage, et le
spider du frontend seul n'a déclenché **aucune** requête backend observée
dans les logs d'accès pendant tout le run. Cible backend directe = couverture
déterministe, indépendante de ce que le spider frontend explore ou non.

Piège réel trouvé en vérifiant, pas supposé : le spider "moderne" (`-j`,
navigateur headless réel) a **bloqué indéfiniment** sur la SPA (~59 min,
tué à la main, CPU à 0 % après une `TimeoutException` Selenium jamais
récupérée) — retiré. Le spider traditionnel seul suffit : sans exécuter le
moindre JS, il découvre déjà 25 URLs réelles (tous les chunks JS/CSS
référencés en dur dans le HTML brut de `index.html`, `sitemap.xml`,
`robots.txt`, les icônes PWA) et termine en **28,6 s**. Contre le backend
(`/api/v2/docs`), le scan couvre 7 URLs (Swagger UI + ses ressources) en
**~27 s**. Les deux scans + démarrage des deux serveurs tiennent largement
dans le budget CI de 20 min posé (mesuré en local, jamais encore observé sur
un vrai runner GitHub Actions — même réserve honnête qu'EXP-004 pour le job
`container:`).

**Vérifié en injectant une vraie régression**, même discipline que EXP-004/006 :
avant tout correctif, les deux scans trouvaient déjà, sans rien forcer,
`X-Content-Type-Options Header Missing` (l'app n'envoyait strictement aucun
header de sécurité — confirmé par `curl -I` avant d'écrire le moindre test).
Un middleware minimal (`api/main.py`, une ligne, `X-Content-Type-Options:
nosniff`) ajouté comme correctif réel et sert de bascule de vérification :
scan backend re-joué → alerte disparue (WARN-NEW 9→8, PASS 58→59) ; middleware
commenté et backend redémarré → alerte réapparue à l'identique (WARN-NEW de
retour à 9) ; middleware restauré comme état final commité. Cycle complet
détection→disparition→réapparition→retour au vert, prouvé en direct trois
fois, pas supposé après la première. Le reste des alertes trouvées (CSP,
Permissions-Policy, anti-clickjacking, Cross-Origin-*-Policy, SRI — 8 sur le
backend, 9 sur le frontend) reste **non corrigé, documenté** : corriger
l'intégralité de la posture de headers de sécurité est hors du périmètre de
« câbler le scanner DAST », et risquerait de casser des choses (une CSP mal
réglée peut bloquer Tailwind/le service worker/RegimeGlobe) sans le temps de
le vérifier composant par composant — laissé en backlog informationnel
explicite, même traitement que refurb/perflint/sonarjs au Lot 6.

Non-gating (`fail_action: false`) : c'est le seul scanner de sécurité de ce
dépôt qui dépend d'une app réellement démarrée — un vrai nouveau mode de
panne (port déjà pris, serveur lent à démarrer, pull d'image ZAP) qu'aucun
des scanners purement fichiers n'a. Déclenché sur `push: develop` (filtré aux
chemins `voter-app/**`/`fast_api_voter/**`) + `schedule` nightly (02:42 UTC)
+ `workflow_dispatch`, jamais sur `pull_request` — même arbitrage que
`schemathesis.yml`/`mutation-testing.yml`, mêmes raisons (variance de timing
non mesurée sur un vrai runner). Pas de SARIF : l'action officielle n'en
produit pas (issue ouverte non résolue côté `zaproxy/actions-common`), les
convertisseurs tiers trouvés (`action-zap2sarif`, `zaproxy-to-ghas`) n'ont pas
de statut de maintenance vérifié — écartés sans essai, même réflexe que
Lost Pixel/`license-checker` (vérifier avant d'adopter, pas après). Rapport
HTML/JSON/MD téléchargé en artifact CI (2 par run, un par cible) +
comptage récapitulatif dans le step summary (`jq` sur `report_json.json`),
pas de SARIF ni d'issue GitHub auto-créée (`allow_issue_writing: false` —
tous les autres scanners de ce dépôt remontent par artifact/onglet
Security/step-summary, jamais par une issue créée automatiquement).
`scripts/audit.sh` reste inchangé : c'est le seul scanner de sécurité de ce
plan qui a besoin de deux serveurs réellement démarrés (uvicorn + un build
frontend), à l'opposé du principe du script (« déterministe, rapide, sans
état, pour un hook ou une passe locale de quelques secondes ») — ajouter un
scan de plusieurs dizaines de secondes avec deux ports à gérer localement
casserait cette promesse pour tout le monde à chaque appel du script, pas
seulement pour qui veut vérifier la sécurité DAST. Un développeur qui veut le
rejouer en local lance `gh workflow run dast.yml` ou reproduit les deux
commandes `docker run` documentées dans le workflow lui-même. Détail complet,
protocole et pièges :
[`docs/exploration/EXP-010-zap-baseline-dast.md`](docs/exploration/EXP-010-zap-baseline-dast.md).

**Fuzzing à couverture, détail.** `atheris` vs `hypofuzz` tranché sur l'état
réel des deux outils, pas sur la réputation — même discipline que le rejet de
Lost Pixel (EXP-004) et le remplacement `license-checker` →
`license-checker-rseidelsohn` (Lot 6.7) :

- **`hypofuzz`** réutiliserait directement les stratégies Hypothesis déjà
  écrites ici (`test_hypothesis_condorcet.py` etc.) — le fit technique le
  plus naturel sur le papier. Écarté après vérification en direct : sa
  licence (`LicenseRef-HypoFuzz`, pas une licence OSI) restreint l'usage
  gratuit aux projets « non commercialement supportés », interdit toute
  modification/redistribution sans permission écrite, et sa dernière release
  PyPI (25.11.1, novembre 2025) traîne de ~6 mois derrière le dernier commit
  du dépôt (mai 2026) — dépôt non archivé, mais rythme clairement ralenti.
  Rien de disqualifiant en soi pour un usage personnel/pédagogique non
  commercial, mais une ambiguïté que ce dépôt évite déjà systématiquement
  pour ses dépendances de PRODUCTION (`scripts/check_license_compliance.sh`)
  — pas de raison de l'accepter côté dev quand une alternative propre existe.
- **`atheris`** : Apache-2.0 (licence OSI standard), toujours maintenu par
  Google (dépôt non archivé, dernier commit 2026-06-17, `pushedAt` vérifié
  en direct via `gh api`), wheels publiées pour Python 3.11-3.14 —
  **téléchargées et installées avec succès sur le 3.14.7 exact que pin ce
  dépôt**, pas juste lu dans un changelog. Retenu.

**Cible : le moteur (26 règles) + les parseurs LLM (9 fonctions
`decode_*_batch`), pas autre chose.** Grep de tout ce qui ressemble à un
parseur dans `api/` avant d'écrire une ligne de harnais : la quasi-totalité
des hits sont soit de la validation Pydantic sur le corps de requête (déjà
couverte par le Schemathesis du Lot 3), soit du chargement de config/logs
**de confiance** (repo-controlled). Un seul point du backend décode du texte
qui n'est ni l'un ni l'autre : la réponse brute d'un LLM
(`api/domain/polity/llm_client.py`'s `decode_vote_batch` et ses 8 sœurs
quasi-identiques — regex `<think>` strip → `json.loads` → validation
Pydantic → alignement des cid) — c'est le seul « parseur » réel de ce
backend, et la cible exacte que l'item vise.

- `scripts/fuzz_engine.py` — génère des profils de vote délibérément
  malformés (bulletins vides/dupliqués, candidats unicode/vides, enveloppes
  dict sans clé `ranking`, scores NaN/inf) qu'`st.permutations(["A","B","C","D"])`
  (les tests Hypothesis existants) ne peut structurellement jamais produire.
  Pool de candidats volontairement petit et FIXE pour ne pas faire exploser
  le chemin exact O(n!) de Kemeny-Young.
- `scripts/fuzz_llm_parsers.py` — mutation directe des octets bruts d'une
  réponse LLM, corpus de départ (`fuzz_corpus/llm_parsers/seed_*`, committé)
  = quelques payloads réalistes (batch valide, `<think>`-wrappé, JSON
  invalide, prose brute).

**Trois crashes réels trouvés, tous corrigés avec un test de régression
minimal — pas fabriqués pour justifier l'outil :**

1. `calculate_bayesian_regret` : un bulletin vide (`{}`, un votant qui n'a
   noté personne) fait planter `max(vote.values())` avec un `ValueError`
   pour TOUS les candidats, pas juste ce votant — trouvé en 13 exécutions.
   Corrigé : les bulletins vides sont exclus du calcul (numérateur et
   dénominateur), même logique que `vote.get(candidate, 0)` traite déjà un
   candidat absent comme 0 ailleurs dans ce fichier.
2. `get_nanson_winner` / `get_baldwin_winner` : `votes` non vide mais dont
   *chaque* bulletin classe zéro candidat (`[[]]`) fait planter le fallback
   `min(all_cands)` sur une liste vide — trouvé en ~92 exécutions. Corrigé en
   ajoutant la même garde que `get_benham_winner`/`get_smith_irv_winner`
   utilisent déjà juste à côté (`if not all_cands: return None`) —
   incohérence entre fonctions sœurs du même fichier, pas un bug isolé.
3. `get_majority_judgment_winner` : l'ensemble des candidats était dérivé du
   PREMIER votant seulement (`utility_scores[0].keys()`) ; un votant suivant
   notant un candidat que le premier n'avait pas noté faisait planter
   `all_grades[c]` avec un `KeyError` — trouvé en ~85 exécutions. Corrigé en
   réutilisant `_score_candidates` (déjà utilisé par `get_cumulative_winner`/
   `get_maximin_score_winner`/`get_nash_winner` dans le même fichier) pour
   prendre l'union de tous les votants. `get_evaluative_winner` avait
   exactement le même défaut de conception sans planter (un candidat non vu
   par le premier votant disparaissait silencieusement du résultat, jamais
   une exception) — corrigé par cohérence avec la même fonction utilitaire.

Un quatrième bug trouvé en amont du harnais, en lisant le code plutôt qu'en
fuzzant (le premier grep des « parseurs » avant d'écrire quoi que ce soit) :
`decode_vote_batch` et ses 8 sœurs ne rattrapaient que `json.JSONDecodeError`
autour de `json.loads` — un JSON profondément imbriqué (~10⁵ `[` imbriqués,
confirmé reproductible depuis un interpréteur neuf) fait déborder la pile C
du parseur récursif de `json` avec un `RecursionError` NON rattrapé, *avant*
que `json.JSONDecodeError` n'ait sa chance — un LLM bloqué dans une boucle de
répétition dégénérée peut produire exactement cette forme. Corrigé (`except
RecursionError` ajouté aux 9 fonctions) avec un test de régression dédié.
Note méthodologique honnête : une campagne de fuzzing par mutation de bytes
n'aurait probablement pas trouvé ce cas-là seule dans un budget de temps
raisonnable — la couverture d'`atheris` est au niveau du bytecode Python, et
le parseur JSON en C exécute le même bytecode à chaque niveau
d'imbrication, donc rien ne récompense le mutateur pour empiler des
crochets plus profondément.

**Campagne réelle, chiffres mesurés (pas une estimation) :** 5 min par
harnais après les 4 corrections ci-dessus, machine de dev locale. Moteur :
**242 108 exécutions** (804 exec/s), couverture stabilisée à `cov: 1160`
(`ft: 4831`), **zéro nouveau crash**. Parseurs LLM : **44 410 242
exécutions** (147 542 exec/s — beaucoup plus rapide, l'essentiel du temps
se passe dans un `json.loads` qui échoue en microsecondes sur du texte
aléatoire plutôt que dans jusqu'à 25 fonctions de vote), couverture
stabilisée à `cov: 48`, **zéro nouveau crash**. Verdict honnête : sur la taille actuelle de ce code (26 fonctions pures,
~1700 lignes cumulées pour le moteur ; 9 fonctions quasi-identiques pour les
parseurs), la surface explorable sature vite — les 3+1 bugs réels sont
apparus dans les toutes premières secondes de chaque campagne, et 5 minutes
supplémentaires n'ont rien trouvé de nouveau. C'est un résultat cohérent
avec la prémisse de l'item (« plus profond qu'Hypothesis seul ») : les
Hypothesis existants n'auraient structurellement pas pu générer ces 3
formes d'entrée (bulletin vide, candidat asymétrique entre votants,
bulletins tous vides) — mais ça reste modeste en volume de trouvailles, pas
un gisement inépuisable.

**CI : planifié, jamais bloquant, jamais sur PR** — même arbitrage que
`mutation-testing.yml`/`schemathesis.yml` (voir leurs commentaires propres) :
une campagne de fuzzing à couverture n'a de sens qu'avec un vrai budget
temps (minutes, pas secondes), donc pas un gate de PR. `atheris-fuzzing.yml`
: 15 min/harnais, `workflow_dispatch` avec un budget configurable, cron
jeudi 04:44 UTC (le créneau lundi matin a déjà 3 jobs lourds). Corpus
découvert persisté via `actions/cache` (même logique que le cache
incrémental de Stryker) — un crash trouvé en CI est uploadé comme artefact
(90 jours) et rejoue localement avec le même script (`python
scripts/fuzz_engine.py <fichier-crash>`), même discipline de reproductibilité
que `scripts/check_flaky_backend.py`.

Détail complet, harnais, et chiffres :
[`docs/exploration/EXP-011-atheris-coverage-fuzzing.md`](docs/exploration/EXP-011-atheris-coverage-fuzzing.md).

**Signature d'images + provenance SLSA, détail.** Avant d'écrire la moindre
ligne de YAML : les deux images Docker du repo sont-elles publiées quelque
part ? Grep exhaustif de tous les workflows pour un push de registre
(`docker/login-action`, `docker push`, `ghcr`) — une seule occurrence de
`docker/build-push-action`, dans `audit.yml`'s job `image-scan`, avec
`load: true` (démon local du runner, jamais publié) ; `release.yml` lu en
entier ne construit ni ne pousse aucune image (bump de version, tag git,
GitHub Release). **Aucune des deux images n'existe jamais en dehors du job
qui la construit pour la scanner** — signer « l'image » au sens OCI natif
(`cosign sign`, qui pousse un artefact de signature *dans le même registre
que l'image*) n'a donc aucune destination. Le seul artefact réellement
publié par ce job est le SBOM (`actions/upload-artifact`, déjà en place
depuis le Lot 6) — c'est lui qui devient le sujet : `cosign sign-blob`
(keyless, jeton OIDC du job, aucune clé à gérer) pour la signature,
`actions/attest-build-provenance` (`subject-path`, aucun registre requis)
pour la provenance SLSA. `slsa-framework/slsa-github-generator` — l'autre
chemin nommé — écarté après lecture directe de son propre README : *« no
longer actively maintained… we are working on guidance and simpler tooling
to replace it »*, dernière release février 2025, pointant lui-même vers les
GitHub artifact attestations comme remplacement ; sa garantie la plus forte
(SLSA Build L3) exige en plus un workflow réutilisable isolé que ce job
(un `docker build` ordinaire) n'est pas, restructuration non justifiée pour
un item `M`. Les deux actions ajoutées épinglées au commit comme le reste du fichier :
`sigstore/cosign-installer@6f9f17788090df1f26f669e9d70d6ae9567deba6 # v4.1.2`,
`actions/attest-build-provenance@4d101475d8b20a2381f78447822ac1eab6504dd8 # v4.2.2`.
Permissions
ajoutées **au niveau du job** (`id-token: write`, `attestations: write`),
même précédent que `scorecard.yml` — ce qui a obligé à réécrire aussi les
permissions déjà héritées du workflow (`contents`, `security-events`,
`actions: read`), non additives au niveau job. Vérifié en direct en local
avant le câblage CI (cette session n'a pas le droit de pousser de branche,
donc le jeton OIDC ambiant de GitHub Actions ne peut s'exercer pour de vrai
qu'au premier run après merge) : `cosign` v3.1.3 et `syft` v1.51.1 installés
sans sudo, vraie image frontend construite (95,2 MB), vrai SBOM généré
(1 038 650 octets, 71 paquets), signature + `verify-blob` réussis (code 0),
puis **sabotage réel du SBOM signé** (paquet falsifié injecté) →
`verify-blob` échoue correctement (code 1). Piège trouvé en testant le cas
négatif de l'attestation, pas supposé : `cosign verify-blob-attestation
--check-claims=false` renvoyait `Verified OK` même sur le fichier saboté —
ce flag désactive silencieusement la correspondance de hash sujet↔fichier,
pas seulement des métadonnées GitHub annexes comme son nom le suggère ; retiré,
la même vérification échoue bien (code 1). **Confirmé en vrai depuis** : le
merge de cet item a lui-même déclenché le premier run réel du job
(`push` sur `develop`) — les quatre étapes (SBOM, install cosign, signature,
attestation SLSA) sont passées avec succès pour les deux images, jeton OIDC
GitHub Actions réel inclus, plus besoin de la réserve initiale. Détail
complet, protocole et piège :
[`docs/exploration/EXP-008-cosign-slsa-provenance-signing-scope.md`](docs/exploration/EXP-008-cosign-slsa-provenance-signing-scope.md).

**`minimumReleaseAge`, détail — déjà satisfait, pas de migration Renovate.**
Vérification avant tout travail (le point de décision signalé explicitement
pour cet item) : `.github/dependabot.yml` porte déjà `cooldown:
default-days: 7` sur les **6** blocs d'écosystème (pip, npm, github-actions,
3× docker) — ajouté au commit `5c8e2f3` (27/08/2026), *avant* ce Lot 9,
poussé par un finding Semgrep (`dependabot-missing-cooldown`), pas en
réponse à cet item. `cooldown` est la fonctionnalité native de Dependabot
équivalente au `minimumReleaseAge` de Renovate — vérifié contre la doc
officielle GitHub et le changelog du 14/07/2026 (attendre N jours après la
publication d'une release avant de proposer une mise à jour de *version*,
jamais les mises à jour de *sécurité* qui restent immédiates) : GitHub a
rendu un cooldown de **3 jours le défaut global** pour tous les repos
Dependabot sans configuration explicite à partir du 14/07/2026 — le
`cooldown: default-days: 7` de ce dépôt, ajouté le 27/08/2026 (six semaines
*après*, en réaction à un finding Semgrep indépendant, pas en anticipation de
ce défaut), est déjà **plus conservateur** que ce défaut global (7 jours,
dans la fourchette "3-7 j" demandée par cet item lui-même).
Migrer vers Renovate pour la seule granularité par-`packageRule` (l'avantage
réel restant de Renovate sur ce point précis) remplacerait une intégration
Dependabot existante et qui fonctionne — groupement patch/minor par
écosystème (Lot 1), labels, et surtout l'auto-merge Mergify qui détecte
spécifiquement la protection de branche Dependabot (`.mergify.yml`) — par une
migration bien plus disruptive que l'effort `S` annoncé pour cet item ne le
laisse supposer, pour un gain marginal (le dépôt n'a pas de paquet nécessitant
une fenêtre différente des autres). **Rejeté comme migration, satisfait comme
besoin** : aucun changement de configuration nécessaire, le mécanisme demandé
existe déjà et dépasse même la cible.

---

## Lot 10 — Observabilité

| Item | Pourquoi ici | Effort | Solidité | Récit |
|---|---|---|---|---|
| **Sentry ou GlitchTip** | Le handler global ajouté le 06/09 *logge* — mais personne ne lit les logs d'une app pédagogique. Sans collecteur, ce travail ne sert à rien en pratique. | M | ⭐⭐⭐ | 📝📝 |
| **OpenTelemetry** | Traces par endpoint, temps réel par méthode de vote — alimente aussi le Lot 8. | L | ⭐⭐ | 📝📝📝 |
| **`/metrics` Prometheus** + readiness/liveness distincts | `/health` existe mais reste binaire. | M | ⭐⭐ | 📝 |

---

## Lot 11 — Outillage Claude avancé

Le `.claude/` actuel est mince : 2 skills, 1 agent, 1 commande, **0 hook**.
Angle de récit : *« à quoi ressemble un repo réellement outillé pour le
développement assisté par agent ? »* — sujet sur lequel il existe très peu de
retours concrets.

| Item | Pourquoi ici | Effort | Solidité | Récit |
|---|---|---|---|---|
| **Agent `parity-guardian`** | Dès qu'une règle de vote bouge : régénère la parité, lance le test, explique tout écart. | M | ⭐⭐⭐ | 📝📝📝 |
| **Agent `dep-triage`** | Lit les PR Dependabot, classe patch/mineur/majeur, lit les changelogs, propose l'ordre de merge. Répond pile à la douleur du 06/09. | M | ⭐⭐ | 📝📝📝 |
| **Agent `axiom-checker`** | Vérifie qu'une nouvelle méthode de vote arrive avec ses tests axiomatiques (Lot 4.1). | M | ⭐⭐ | 📝📝 |
| **Agent `flake-hunter`** | Isole les tests instables, propose un correctif. | M | ⭐⭐ | 📝📝 |
| **Agent `doc-drift`** | Celui improvisé le 06/09, figé en agent réutilisable + cron mensuel. | S | ⭐⭐ | 📝📝📝 |
| **Skill `voter-testing`** | Comment tester ici : Hypothesis, fixtures de parité, testids e2e, pièges connus. | M | ⭐⭐ | 📝📝 |
| **Skill `voter-ci`** | Diagnostiquer un échec CI, où sont les gates, que faire quand le ratchet casse. | M | ⭐⭐ | 📝📝 |
| **Skill `release`** | Checklist `develop → main`. | S | ⭐⭐ | 📝 |
| **Agents planifiés** | Revue hebdo du diff de la semaine, audit doc mensuel, veille de dépendances. | M | ⭐⭐ | 📝📝📝 |
| **`/code-review ultra`** sur les PR du moteur | Existe déjà, sous-utilisé sur les changements sensibles. | S | ⭐⭐ | 📝📝 |

---

## Lot 12 — Économie de tokens & efficacité du contexte

Lot transversal : **12.1 et 12.2 peuvent démarrer immédiatement**, le reste
s'installe au fil des autres lots.

La garde `graphify` déjà en service dans le worktree polity (`PreToolUse` qui
impose une requête de graphe avant tout grep) appartient déjà à cette famille —
ce lot la généralise plutôt qu'il n'introduit un concept neuf.

Principe directeur : **le levier n'est pas de « parler moins », c'est de ne
jamais charger ce qui n'apporte rien.**

### 12.1 — Mesurer d'abord · `S` · ⭐⭐ 📝📝📝

On n'optimise pas ce qu'on ne mesure pas.

- **Télémétrie OpenTelemetry de Claude Code** : consommation et coût par session.
- **Analyse des transcripts locaux** (`~/.claude/projects/**/*.jsonl`) : ils
  contiennent déjà les usages par tour — exploitables par script maison ou par
  un outil communautaire type `ccusage` (à évaluer, pas à adopter d'office).
- `/cost` en séance pour le retour immédiat.
- **Rattachement au Lot 0.2** : ajouter une ligne « coût en tokens » au gabarit
  de carnet d'expérience. Chaque expérience du plan porte alors son coût réel —
  et le tableau des verdicts (0.3) devient *« ce que chaque outil a trouvé, et
  ce qu'il a coûté »*, ce qui est nettement plus intéressant à partager.

### 12.2 — Ne jamais charger ce qui ne doit pas l'être · `M` · ⭐⭐⭐ 📝📝

Mesure réelle sur ce repo (estimation à ~4 octets/token) :

| Fichier | Poids | Nature |
|---|---|---|
| `voter-app/package-lock.json` | ~155 k tok | généré |
| `fast_api_voter/Electors simulation.ipynb` | ~152 k tok | notebook **avec sorties stockées** |
| `fast_api_voter/openapi.gen.json` | ~116 k tok | généré |
| `voter-app/src/api/types.gen.ts` | ~88 k tok | généré |
| `voter-app/src/lib/__fixtures__/engineParity.json` | ~33 k tok | généré |

**Ces cinq fichiers pèsent ~544 k tokens** — largement plus qu'une fenêtre de
contexte. Une seule lecture intégrale accidentelle de l'un d'eux consomme
l'équivalent de plusieurs heures de travail utile. Aucun n'a de raison d'être lu
en entier : quatre sont des artefacts générés, le cinquième est un notebook dont
l'essentiel du poids est constitué de sorties.

Actions :

- **`.claudeignore`** (absent aujourd'hui) sur les artefacts générés.
- **Hook d'avertissement** sur la lecture intégrale d'un fichier généré, calqué
  sur la garde `graphify` déjà éprouvée.
- **`nbstripout`** en pre-commit sur le notebook : les sorties stockées n'ont
  pas à être versionnées, et représentent ici l'essentiel des 152 k tokens.
- **Rotation du journal** : `JOURNAL_DE_BORD.md` pèse déjà ~42 k tokens et
  croît à chaque session. Archiver par année, sinon **le dispositif
  anti-répétition devient lui-même le poste de dépense** — exactement le piège
  identifié au Lot 0.5.

### 12.3 — Lire moins cher ce qu'on lit quand même · `M` · ⭐⭐ 📝📝📝

| Outil | Gain |
|---|---|
| **`graphify`** | Éprouvé côté polity — évaluer son portage sur `develop`. |
| **`ast-grep`** | Recherche *structurelle* : beaucoup moins de faux positifs que grep, donc beaucoup moins de lecture pour les écarter. |
| **`repomix --compress`** | Empaquette le repo en gardant les signatures sans les corps : vue large à coût réduit. |
| **Cartes de fichier** (signatures seules, via tree-sitter/ast-grep) | S'orienter dans un fichier de 30 k tokens sans le charger. |
| **Lecture par plage** (`offset`/`limit`) | Réflexe par défaut sur les gros fichiers plutôt que la lecture intégrale. |
| **Sorties d'outils courtes** | `pytest -q --tb=short`, `jq` plutôt que du JSON brut, `--stat` plutôt qu'un diff complet. Une sortie verbeuse est un coût récurrent. |

### 12.4 — Architecture de session · `M` · ⭐⭐ 📝📝📝

- **Les sous-agents sont le levier majeur** : le contexte de fouille reste chez
  eux, seul le rapport remonte. Pratiqué le 06/09 (4 agents de documentation en
  parallèle) — à systématiser sur les tâches exploratoires.
- **Un modèle par agent** (`model:` dans le frontmatter des définitions) : les
  agents mécaniques du Lot 11 (`doc-drift`, `dep-triage`) n'ont pas besoin du
  modèle le plus cher ; le jugement, si.
- **Plan mode** pour cadrer avant d'exécuter — évite les allers-retours coûteux.
- Sessions ciblées plutôt que fleuves.

### 12.5 — Cache de prompt · `S` · ⭐⭐ 📝📝

`CLAUDE.md` pèse ~1 200 tokens et est chargé **à chaque requête** : c'est sain
aujourd'hui, l'enjeu est que ça le reste. Un gate CI sur sa taille suffit.
Corollaire : éviter de modifier en cours de session les fichiers chargés
d'office, chaque modification invalidant le cache.

### 12.6 — Le lien avec tout le reste du plan · ⭐⭐⭐ 📝📝📝

**Chaque gate automatisé est un token économisé.** Un linter qui renvoie
l'erreur en trois lignes remplace un tour de conversation entier passé à la
chercher. Vu sous cet angle, les Lots 1 à 9 ne sont pas seulement du
durcissement : ce sont des économies de contexte.

C'est probablement l'angle de récit le plus original de tout le plan —
« j'ai mesuré ce que mon outillage qualité me faisait économiser en tokens » est
un chiffre que personne ne publie.

---

## Lot 13 — Synthèse & partage *(à faire en dernier, il consomme tout le reste)*

| Item | Contenu | Effort | Récit |
|---|---|---|---|
| **Index des verdicts complété** | Le tableau du Lot 0.3, rempli par ~25 expériences réelles. | S | 📝📝📝 |
| **Rétrospective du plan** | Ce plan a-t-il survécu au contact ? Quels items abandonnés, lesquels ajoutés en route, lesquels ont déçu. | M | 📝📝📝 |
| **Les 3-4 histoires les plus partageables** | Candidats naturels : « la couverture à 91 % ment-elle ? » (Lot 5) · « 25 outils de qualité sur un vrai projet, le tableau des verdicts » (Lot 0.3) · « tester une théorie mathématique comme on teste du code » (Lot 4) · « combien de mes conventions écrites étaient déjà violées » (Lot 2). | L | 📝📝📝 |
| **`CODE_AUDIT.md` rejoué** | Nouvelle édition datée après tous les lots, comparaison avec l'édition du 2026-09-06. | S | 📝📝 |
| **README qui raconte** | Le repo est public : rendre visible la double exploration (méthodes de vote *et* pratiques de dev). | M | 📝📝📝 |

---

## Lot 14 — Rembourser la dette trouvée par le Lot 6 *(pas urgent, peut attendre)*

Le Lot 6 a délibérément **mesuré et documenté** sans corriger en masse — chaque
item y est resté à la hauteur de son propre budget `S`/`M`, avec les vrais
bugs trouvés (basedpyright, sonarjs) fixés individuellement mais le gros de
la dette laissé en baseline chiffrée. Ce lot referme la boucle : transformer
les cinq mesures en réduction réelle, avec le même niveau d'exigence que le
reste du plan (rien de mécanique commité sans vérifier que ça reste vert).
Contrairement aux autres lots, **aucun élément ici n'est bloquant ou urgent**
— chaque ligne peut attendre indéfiniment sans risque, elle référence un
outil déjà câblé et un chiffre déjà mesuré, pas une lacune de détection.

| Item | Pourquoi ici | Effort | Solidité | Récit |
|---|---|---|---|---|
| **Typer les `any` restants + activer le cliquet** (280 dans le code source, Lot 6.4) | Seul item du groupe avec un vrai gain de sûreté de typage, pas juste de lisibilité — `type-coverage` expose déjà `--at-least`/`--update-if-higher` mais rien n'est câblé, faute d'une baseline assez haute pour que ça vaille le coût. Réduire d'abord, gater ensuite. | M | ⭐⭐⭐ | 📝📝 |
| **Statuer sur les zones mortes trouvées par le Lot 6.5** (`api/domain/polity/*`, 2 813 lignes 0 % e2e ; `/simulation/compare`, invisible à knip) | Le Lot 6.5 a mesuré l'inatteignabilité, pas décidé quoi en faire. Deux vraies trouvailles qui méritent une décision explicite — réintégrer dans le produit ou supprimer — pas rester indéfiniment dans un angle mort connu. | M | ⭐⭐⭐ | 📝📝📝 |
| **Réduire la dette sonarjs** (304 findings restants, Lot 6.6) | 2 vrais bugs y avaient déjà été trouvés en vérifiant à la main les 5 cas `no-all-duplicated-branches` — les autres catégories (`no-nested-conditional` ×102, `cognitive-complexity` ×38, `parameterized-tests` ×39, `prefer-specific-assertions` ×33) n'ont pas reçu le même traitement individuel, faute de budget. Simplifier les fonctions à plus forte complexité cognitive en particulier est le genre de nettoyage qui prévient le prochain bug de cette famille. | L | ⭐⭐ | 📝📝 |
| **Réduire la dette refurb/perflint** (145 + 85 findings, Lot 6.3) | Le Lot 6.3 a mesuré et documenté sans corriger, hors budget de l'item lui-même. Transformations mécaniques, risque quasi nul (`dict(x)`→`x.copy()`, `lambda`→`operator.itemgetter`, `list`→`tuple` non mutés) — le genre de dette qui ne s'aggrave pas mais ne se résorbe pas non plus toute seule. | M | ⭐⭐ | 📝 |
| **Faire taire les faux positifs basedpyright** (34 restants, Lot 6.2) | Déjà vérifiés faux un par un (32 liés à l'absence d'équivalent du plugin `pydantic.mypy` côté pyright, 2 isolés où le vérificateur ne peut pas prouver une invariante locale) — pas de vraie dette ici, juste du bruit dans le rapport pour un futur contributeur. Le moins prioritaire des cinq ; à ne faire que si `basedpyright` reste consulté régulièrement. | S | ⭐ | 📝 |

---

## Séquencement recommandé

```
Lot 0  (documentation)          ← EN PREMIER, sinon tout le reste est perdu
   ↓
Lot 1  (quick wins)             ← débloque le confort de tous les suivants
   ↓
Lot 2  (conventions exécutables) ─┐
Lot 3  (contrat API + résilience) ├─ indépendants entre eux
Lot 5  (robustesse des tests)     │
Lot 6  (angles morts du statique) ─┘
   ↓
Lot 4  (domaine électoral)      ← le cœur ; mérite d'être fait posément
   ↓
Lot 7 (surfaces) · Lot 8 (perf) · Lot 9 (sécurité) · Lot 10 (observabilité)
   ↓
Lot 11 (outillage Claude)       ← profite de tout ce qui précède
   ↓
Lot 13 (synthèse & partage)

Lot 12 (économie de tokens)     ← TRANSVERSAL : 12.1 et 12.2 dès maintenant,
                                   le reste s'installe au fil des autres lots

Lot 14 (dette du Lot 6)         ← HORS FLUX : après Lot 6, sinon jamais —
                                   aucune urgence, peut se faire n'importe
                                   quand, y compris après Lot 13
```

**Dépendances dures** (le reste est librement réordonnable) :

- Lot 0 avant tout — c'est le dispositif de capture.
- Lot 1 avant les lots lourds en CI (cache, `uv`, groupes Dependabot).
- Lot 4.1 (axiomes) avant Lot 11 `axiom-checker` — l'agent a besoin de la matrice.
- Lot 12.1 (mesure) avant les lots coûteux, sinon on n'a pas de point de
  comparaison pour chiffrer ce qu'ils économisent (§12.6).
- Lot 13 en dernier par construction.
- Lot 14 après Lot 6 (il en réduit les chiffres) — mais sans échéance ; ne
  bloque rien d'autre, y compris Lot 13 (la synthèse peut noter la dette du
  Lot 6 comme « mesurée, pas encore remboursée »).

## Règles d'exécution

- **Une branche `feat/*` + une PR par item**, contre `develop`, merge `--no-ff`.
- Un item se termine par un **carnet d'expérience** (`docs/exploration/EXP-*.md`)
  quand il s'agit d'un outil essayé — pas pour les items purement internes.
- **Un verdict « rejeté » est un succès du plan**, pas un échec : il faut juste
  qu'il soit argumenté avec ce que l'outil a réellement trouvé et coûté.
- Ne pas empiler plus de 2-3 items ouverts en parallèle : la protection de
  branche invalide les PR entre elles (leçon du 06/09).
- Chiffrer avant/après quand c'est possible — un plan d'exploration sans mesure
  ne produit pas de récit crédible.
