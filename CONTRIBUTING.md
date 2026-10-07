# Vote Lab — Stratégie de branches & qualité

## Modèle de branches

```
main          ← branche officielle, dernière version release
  ↑ PR develop → main uniquement (via workflow Release)
develop       ← branche par défaut de GitHub ; ne reçoit que des
  ↑             synchronisations depuis polity (chore/sync-polity-into-develop-<date>,
  ↑             un vrai commit de merge)
polity        ← branche de travail
  ↑ PR feat/* | fix/* | refactor/* | ci/* | chore/* | ... → polity
polity-ui     ← intégration de l'explorateur de runs (<type>/polity-ui-*)
```

**Règle absolue** : on ne push jamais directement sur `main`, `develop` ni
`polity`, et on ne réécrit jamais leur historique publié. Tout changement passe
par une PR soumise à validation CI. Les déclencheurs `schedule` et
`workflow_run` (crons, alerte `polity-red`, tableau de bord CI) sont lus depuis
la branche par défaut (`develop`) : une modification de ces workflows ne prend
effet qu'après la synchronisation suivante vers `develop`.

---

## Nommage des branches

| Préfixe | Quand l'utiliser |
|---|---|
| `feature/` ou `feat/` | Nouvelle fonctionnalité |
| `fix/` ou `bugfix/` | Correction de bug |
| `hotfix/` | Correctif urgent |
| `refactor/` | Refactoring sans changement visible |
| `chore/` | Mise à jour dépendances, configuration |
| `docs/` | Documentation uniquement |
| `test/` | Ajout / amélioration de tests |
| `ci/` | Modifications de la CI/CD |
| `perf/` | Amélioration de performance |
| `dependabot/` | Mises à jour automatiques (Dependabot — préfixe imposé, pas de choix) |

Un correctif de sécurité prend une branche `fix/` (ou `hotfix/`) : `security` n'existe
que comme préfixe de **titre** de PR (`security: …`), pas de branche — `branch-policy.yml`
refuse une branche `security/…`.

**Exemple :** `git checkout -b feature/vote-blanc-toggle`

---

## Workflow complet

### 1. Créer une branche depuis polity

```bash
git checkout polity && git pull origin polity
git checkout -b feat/ma-feature
```

### 2. Développer & commiter

Les hooks pre-commit vérifient à chaque `git commit` :
- Secrets / credentials, sécurité Python (bandit), linting, npm audit

Et à chaque `git push` :
- Tests frontend + coverage (seuils de `vitest.config.ts`)
- Tests backend + coverage >= 90 %

### 3. Vérifier, puis ouvrir une PR vers polity

Avant d'ouvrir la PR : `/verify "<la demande d'origine, mot pour mot>"` (dans
Claude Code) lance `scripts/fast-gate.sh` puis l'agent `spec-checker`, qui ne
voit que la demande et le diff. Un `FAIL` (quelque chose de demandé manque) =
pas de PR. Une section `SKIPPED` de fast-gate (par exemple un `python3` plus
ancien que le `python_version` de `mypy.ini`, ou des dépendances absentes)
n'est pas un succès. Le modèle de PR demande `## Demande` (mot pour mot),
`## Critères d'acceptation`, `## Preuves` (commandes réellement lancées et leur
sortie) et une ligne **Non vérifié** obligatoire (« rien » seulement si c'est
vrai).

```bash
git push origin feat/ma-feature
# Ouvrir la PR : feat/ma-feature -> polity
```

La liste exacte des checks requis d'une branche :
`bash scripts/setup-branch-protection.sh --print-contexts polity`.
<!-- [[[cog
import cog, ci_facts
n = {b: len(ci_facts.required_contexts(b)) for b in ci_facts.BRANCHES}
cog.outl(f"Aujourd'hui : {n['polity']} sur `polity`, {n['develop']} sur `develop`, {n['main']} sur `main`,")
cog.outl(f"{n['polity-ui']} sur `polity-ui` (généré depuis le script, vérifié par `scripts/check_generated_docs.sh`).")
]]] -->
Aujourd'hui : 16 sur `polity`, 16 sur `develop`, 14 sur `main`,
13 sur `polity-ui` (généré depuis le script, vérifié par `scripts/check_generated_docs.sh`).
<!-- [[[end]]] -->

**La CI vérifie automatiquement :**

| Vérification | Bloque la PR si... |
|---|---|
| Branch Policy | Branche source sans préfixe valide, titre hors Conventional Commits, ou un motif de chemin protégé de `.mergify.yml` qui ne correspond plus à aucun fichier |
| High-risk review gate | La PR touche un chemin à risque (workflows, `.claude/`, moteur de vote, baselines…) ou affaiblit la suite de tests, tant que le propriétaire n'a pas commenté `/reviewed <sha>` sur le commit de tête (voir plus bas) |
| Workflow lint | actionlint (+ shellcheck), zizmor `--offline` (medium et plus) ou les tests des hooks `.claude/hooks/tests` échouent ; le job est sauté si aucun workflow ni hook ne change |
| CI health check | Instantané `.github/ci-health.json` périmé, workflow surveillé en échec ou inerte, ou protection de branche en dérive |
| Frontend CI | Tests échouent, coverage sous les seuils, ou eslint rapporte une erreur |
| Backend CI | Tests échouent, coverage < 90 %, une ligne modifiée non couverte (diff-cover 100 %), mypy, ruff, ou la couche `routes → domain → engine` en erreur |
| npm audit | CVE haute détectée, hors exception datée de `.github/npm-audit-allowlist.json` (une exception expirée fait aussi échouer) |
| E2E (Playwright) | Un parcours utilisateur casse sur Chromium, Firefox, WebKit ou mobile — **ou passe seulement au second essai** (voir « Tests E2E » plus bas) |
| Generated Artifacts Contract | `openapi.gen.json` / `types.gen.ts`, `engineParity.json` **ou** les blocs de doc générés désynchronisés du code (voir `scripts/check_openapi_drift.sh`, `scripts/check_engine_parity_drift.sh` et `scripts/check_generated_docs.sh`) |
| Engine perf ceilings | Une règle de vote (`simulation_ranked_utils.py`/`simulation_score_utils.py`) dépasse son plafond de temps absolu — généreux exprès (100-500 ms, 15-500x la mesure réelle), pensé pour attraper une régression algorithmique, pas du bruit machine (voir `fast_api_voter/api/tests/test_engine_benchmarks.py`) |
| Quality ratchet | La dette vulture/radon/deptry/knip/jscpd/sonarjs, ou le nombre d'erreurs mypy strict sur `fast_api_voter/scripts/*.py` (`mypy_scripts`), a augmenté ; ou la complexité moyenne passe sous le rang A (`xenon -a A`) (voir « Code mort » plus bas) |
| Dependency Review | La PR introduit une dépendance vulnérable (sévérité high+) — complète Dependabot, qui ne scanne que l'existant, pas ce qu'une PR ajoute |

**Consultatif (n'empêche pas le merge, mais se lit) :**

| Vérification | Ce qu'elle signale |
|---|---|
| Red on base | Pour une PR `feat/`/`fix/`, aucun des tests nouveaux ou modifiés n'échoue sur le code de la base : ils ne couvrent pas le changement. Pour `refactor/`, un fichier de test a changé (`scripts/check_red_on_base.py`) |
| Diff Mutation | Mutants survivants (Stryker / mutmut) sur les seules lignes modifiées par la PR, en commentaire unique par outil : chacun est une ligne modifiée qu'aucun test n'attraperait (`scripts/mutation_diff.py`) |

### 4. Release : develop → main

Uniquement via le workflow **Release Vote Lab** :
- GitHub → Actions → "Release Vote Lab" → Run workflow
- Choisir `patch`, `minor` ou `major`

Le workflow exige `ci-frontend`, `ci-backend` **et `e2e` (Playwright)** verts
avant de taguer/pousser sur `main`. La suite E2E tourne aussi sur chaque PR
vers `polity` et `develop` : la réserver à la release avait laissé les specs
pourrir deux mois face à une UI qui avait bougé.

Aucune PR vers `main` n'est acceptée depuis une branche autre que `develop`.

---

## Setup local (une seule fois)

```bash
# Dev tools
pip install -r fast_api_voter/requirements-dev.txt
cd voter-app && npm install

# Hooks git (obligatoire)
pip install pre-commit
pre-commit install
pre-commit install --hook-type pre-push
pre-commit install --hook-type post-commit
```

### Setup admin (droits admin GitHub requis)

```bash
bash scripts/setup-branch-protection.sh            # main + develop
bash scripts/setup-branch-protection.sh polity     # puis polity (et polity-ui)
bash scripts/setup-branch-protection.sh --print-contexts polity   # liste seule, ne touche à rien
bash scripts/setup-branch-protection.sh --print-checks polity     # l'entrée appliquée (gate épinglé si REVIEW_GATE_APP_ID)
```

Le script refuse d'exiger un check tant que le workflow qui le poste ne tourne
pas sur les PR vers la branche visée (sur sa copie **et** sur celle de
`develop`) : un check requis que rien ne poste bloquerait toutes les PR (#205).

**Merge queue** : [Mergify](https://mergify.com) (`.mergify.yml`), pas la
merge queue native GitHub — celle-ci est réservée aux repos publics
*organisation*, indisponible sur un repo à compte personnel comme celui-ci
(confirmé en direct par un 422 sur l'API rulesets). Mergify est gratuit pour
l'open source ; installer l'app GitHub sur le repo
(github.com/apps/mergify/installations/new) suffit — elle détecte
automatiquement les `required_status_checks` de la branch protection
ci-dessus et les injecte comme conditions de merge, aucune duplication dans
`.mergify.yml`. Chaque PR dont les checks passent est mise en file et
mergée automatiquement (`auto_merge_conditions: true`) — **sauf** une PR vers
`polity` ou `develop` qui touche un chemin à risque (moteur de vote, workflows,
`.claude/`, scripts et configs de gates, allowlists des scanners, oracles de
test régénérés : liste exhaustive dans `.mergify.yml`), ou qui affaiblit les
tests (moins de tests dans les fichiers de test modifiés, ou un
`skip`/`only`/`xfail` ajouté : `scripts/check_test_integrity.py`, une analyse
statique qui n'exécute jamais le code de la PR). Celle-ci attend que le
mainteneur commente `/reviewed <sha>` avec le commit de tête relu :
`human-review.yml` pose alors un statut `human-review` sur *ce* commit et
libère le statut requis `High-risk review gate` (rouge tant que la PR n'est pas
relue ; c'est lui qui bloque la file Mergify), et tout nouveau commit doit
être relu à nouveau, sauf une simple mise à jour depuis la branche de base
(par Mergify ou par le bouton « Update branch » du mainteneur) qui n'apporte
que des commits déjà fusionnés. Quand la PR régénère un oracle de test (fixture de
parité, golden polity, contrat OpenAPI, baselines, captures), le résumé du run
du gate explique ce qui a changé (`scripts/oracle_diff_report.py` : quelle
règle élit qui, quelles valeurs ont bougé) : c'est ce changement de
comportement qu'il faut relire. Seul le propriétaire du repo peut
approuver ; un agent ne doit jamais le faire. Si vous renommez un fichier
protégé, mettez son motif à jour dans la même PR (`branch-policy.yml` échoue
sinon, via `scripts/check_mergify_protected_paths.py`). Les PR mergées sont retestées contre
l'état à jour de la branche cible avant de vraiment merger (évite la classe de
problème "verte mais `mergeable_state: behind`", vécue en direct sur la PR
#188). `scripts/setup-branch-protection.sh` garde *"Require branches to be up
to date before merging"* (`strict: true`) sur chaque branche protégée, par
décision du propriétaire (2026-10-07). Le prix : Mergify ne peut ni grouper ni
tester en parallèle avec `strict` (`batch_size: 1` et `max_parallel_checks: 1`
dans `.mergify.yml`), donc la file traite une PR à la fois. Le gain : un merge
fait à la main, hors de la file, doit lui aussi être à jour de la branche cible.

#### GitHub App de la revue (statut infalsifiable)

Sans elle, n'importe quel workflow du repo peut poser un statut nommé
`High-risk review gate` ou `human-review` avec son `GITHUB_TOKEN`, y compris le
workflow `pull_request` d'une PR. Avec elle, `human-review.yml` poste ces
statuts avec le jeton de l'App, la protection de branche n'accepte le gate que
de cette App, et un `human-review` ne compte que s'il vient d'elle. Mise en
place, **dans cet ordre** (en inverser deux peut bloquer toutes les PR) :

1. **Créer l'App** : Settings (du compte) → Developer settings → GitHub Apps →
   New GitHub App. Nom libre (par ex. `vote-app-review-gate`), Homepage URL :
   le repo, **Webhook décoché**. Permissions de dépôt : *Commit statuses* →
   Read and write, rien d'autre. « Only on this account ». Créer.
2. Sur la page de l'App : noter l'**App ID** (numérique) et le **Client ID**,
   puis *Generate a private key* (un `.pem` est téléchargé).
3. *Install App* → ce compte → *Only select repositories* → `Vote-App`.
4. **Environnement** : Settings du repo → Environments → New environment
   `review-gate` (ou l'éditer : le workflow le crée vide à son premier run). *Deployment branches and tags* → **Protected branches
   only**. Y ajouter le secret d'environnement `REVIEW_GATE_APP_KEY` = tout le
   contenu du `.pem` (puis supprimer le fichier local).
5. **Variable du repo** : Settings → Secrets and variables → Actions →
   Variables : `REVIEW_GATE_APP_CLIENT_ID` = le Client ID. À partir de là, un
   `human-review` ne compte que s'il vient de l'App : une PR à risque relue
   avant cette étape doit être relue à nouveau (`/reviewed <sha>`).
6. Vérifier sur la PR suivante vers `polity` : le statut `High-risk review gate`
   doit apparaître posté par l'App (son avatar, « vote-app-review-gate »), pas
   par GitHub Actions. Le workflow tourne depuis `develop` : la PR qui l'a
   introduit doit déjà y être synchronisée.
7. **Épingler** l'App dans la protection (le script refuse tant que la copie de
   `human-review.yml` sur `develop` ne poste pas avec l'App) :

   ```bash
   REVIEW_GATE_APP_ID=<App ID> bash scripts/setup-branch-protection.sh polity
   REVIEW_GATE_APP_ID=<App ID> bash scripts/setup-branch-protection.sh develop
   ```

   Le script vérifie d'abord que le dernier `High-risk review gate` posé sur une
   PR vers `polity`/`develop` vient bien de l'App portant cet id. Une PR ouverte
   dont le gate date d'avant l'étape 5 (posé par GitHub Actions) ne compte plus :
   il suffit d'un nouveau commit ou d'un « Update branch » pour qu'il soit reposé.
8. **Seulement après l'étape 7**, ajouter la variable du repo
   `REVIEW_GATE_APP_ID` = l'App ID : l'audit CI-health quotidien la lit et signale
   toute protection où le gate n'est pas épinglé sur cette App (l'ajouter plus
   tôt ferait passer l'audit au rouge en attendant l'épinglage).

Retour arrière, dans cet ordre : supprimer la variable `REVIEW_GATE_APP_ID`,
relancer le script sans elle (le gate redevient « toute source »), puis supprimer
`REVIEW_GATE_APP_CLIENT_ID` (le workflow reposte avec `GITHUB_TOKEN`). Limite qui reste : un agent qui utiliserait les
identifiants du propriétaire peut commenter `/reviewed` en son nom ; c'est aux
hooks de `.claude/` de l'interdire.

---

## Ce qui se passe automatiquement

| Quand | Vérification | Bloque |
|---|---|---|
| `git commit` | detect-secrets, bandit, ruff, eslint, npm audit | Oui |
| `git push` | Tests + coverage (front + back) | Oui |
| PR ouverte | Les checks requis (`scripts/setup-branch-protection.sh --print-contexts polity`), dont `High-risk review gate` et `Workflow lint` ; plus les jobs consultatifs Red on base et Diff Mutation | Oui pour les requis |

---

## Carte des workflows CI

<!-- [[[cog
import cog, ci_facts
ci_facts.require_workflow_table_in_sync(cog.inFile)
n = len(ci_facts.workflow_files())
cog.outl(f"{n} fichiers dans `.github/workflows/`, une ligne chacun dans la table ci-dessous (nombre")
cog.outl("généré ; `scripts/check_generated_docs.sh` échoue si un workflow n'a pas sa ligne, ou si")
cog.outl("une ligne nomme un workflow qui n'existe plus).")
]]] -->
23 fichiers dans `.github/workflows/`, une ligne chacun dans la table ci-dessous (nombre
généré ; `scripts/check_generated_docs.sh` échoue si un workflow n'a pas sa ligne, ou si
une ligne nomme un workflow qui n'existe plus).
<!-- [[[end]]] -->
Sans une table à jour ici, la seule source de vérité redevient « lire tous
les YAML ». Si vous changez un déclencheur
ou un gate, mettez cette table à jour dans la même PR. Sauf mention contraire,
« push/PR » couvre `develop`, `main`, `polity` et `polity-ui`.

| Workflow | Déclencheur | Gate quand il tourne ? | Check requis (branch protection `polity` et `develop`) ? | Durée typique |
|---|---|---|---|---|
| `backend-ci-cd-pipeline.yml` (Backend CI) | push/PR, toujours (le filtre `paths` vit maintenant dans un job `changes` interne, pas au niveau du déclencheur) | Oui, quand `fast_api_voter/**` a changé — sinon le job `test` est `skipped` | Oui | ~12-14 min (skip quasi instantané sinon) |
| `frontend-ci-cd-pipeline.yml` (Frontend CI) | push/PR, toujours (même schéma `changes`) | Oui, quand `voter-app/**` a changé — sinon `skipped` | Oui | ~2-3 min (skip quasi instantané sinon) |
| `e2e.yml` (E2E Tests) | push (`develop`, `polity`, `polity-ui`) / PR + `workflow_dispatch` + `workflow_call` (depuis `release.yml`), toujours (même schéma `changes` ; dispatch/call ignorent le filtre) | Oui, quand `voter-app/**`/`fast_api_voter/**` a changé (hors scripts, tests backend et `.md`), ou toujours pour dispatch/call — sinon `skipped`. Deux jobs requis : `Playwright E2E` (qui fusionne les rapports des deux shards `Playwright E2E (shard 1/2)` et `(shard 2/2)`, et échoue si l'un d'eux n'a pas réussi) et `Playwright/Docker image version sync` (tag de l'image Docker = version de `@playwright/test`, image épinglée aussi par digest, vérifié auprès du registre quand `e2e.yml` ou `package.json` change) ; `Visual regression` ne l'est pas | Oui (les deux) | ~11 min avant le découpage en shards, ~6-7 min visés après (timeout : 20 min par shard) |
| `branch-policy.yml` (Branch Policy) | PR | Oui : préfixe de branche, nommage des PR vers `polity`/`polity-ui`, format du titre (Conventional Commits), source pour les PR vers `main` (`Check source is develop`), motifs de chemins protégés de `.mergify.yml` et tests `scripts/tests` | Oui | ~10-30 s |
| `openapi-contract.yml` (Generated Artifacts Contract) | push/PR, toujours (même schéma `changes`) | Oui, quand un fichier du contrat a changé — sinon `skipped` | Oui | ~1 min (skip quasi instantané sinon) |
| `dependency-review.yml` (Dependency Review) | PR | Oui — sévérité `high`+ introduite par la PR | Oui | ~15-30 s |
| `audit.yml` (Security Audit) | push/PR + cron lundi 06:00 UTC | Semgrep/Trivy/Secret Scan : oui · CodeQL : le job doit terminer mais ne bloque pas sur ses trouvailles (elles atterrissent dans l'onglet Security) · code mort/duplication/complexité (vulture/radon/deptry/knip/jscpd/sonarjs, mypy strict sur `fast_api_voter/scripts/*.py`) : non-bloquant sauf régression du cliquet (`quality-baseline.json`) ou complexité moyenne sous le rang A (`xenon -a A`) · scan d'image Docker + SBOM (`image-scan`) : non-bloquant, et ne tourne que sur push `develop`/`polity` ou cron — jamais sur une PR (build de l'image, coûte plusieurs minutes) | Oui (les 4 jobs gating + les 2 jobs CodeQL du matrix — `image-scan` n'est pas requis) | ~2-3 min sur PR (le run cron/push `develop`, qui inclut `image-scan`, est plus long et indépendant d'une PR) |
| `mutation-testing.yml` (Mutation Testing) | push sur `develop`/`polity` (paths engine uniquement) + `workflow_dispatch` + cron lundi 04:17 UTC | Oui, hors PR : le run échoue (et l'alerte `polity-red` s'ouvre) si Stryker passe sous `thresholds.break` (80) ou si le score mutmut baisse au-delà du bruit (`check_mutation_score.sh`) | Non — ne se déclenche jamais sur PR | mutmut ~40 min-3h · Stryker jusqu'à ~2h30 en cold-cache (`timeout-minutes: 240`), moins avec le cache `--incremental` une fois chaud |
| `schemathesis.yml` (Schemathesis Contract Fuzzing) | push sur `develop`/`polity` (paths `fast_api_voter/api/**`) + `workflow_dispatch` + cron lundi 05:38 UTC | Non — jamais bloquant | Non — ne se déclenche jamais sur PR | ~220s (~3.5-4 min) en local, non re-mesuré sur un runner GitHub réel (`timeout-minutes: 45` par prudence) |
| `flaky-check-backend.yml` (Backend Flaky Test Hunt) | push sur `develop`/`polity` (paths `fast_api_voter/api/**`) + `workflow_dispatch` + cron quotidien 03:13 UTC | Non — jamais bloquant | Non — ne se déclenche jamais sur PR | ~1 min en local (3 exécutions parallélisées `-n auto`, ~16-18s chacune) |
| `release.yml` (🚀 Release Vote Lab) | `workflow_dispatch` uniquement | N/A — pas de PR, gate lui-même sur CI+E2E avant de taguer `main` | N/A | dépend de `ci-frontend`/`ci-backend`/`e2e` + publication |
| `scorecard.yml` (OpenSSF Scorecard) | push `develop` + cron mardi 07:30 UTC + changement de règle de protection + `workflow_dispatch` | Non — score publié dans l'onglet Security, jamais bloquant | Non | ~1-2 min |
| `workflow-lint.yml` (Workflow Lint) | push/PR sur `polity`/`develop`, toujours (schéma `changes`) | Oui : actionlint (+ shellcheck), zizmor `--offline` (medium et plus ; une trouvaille acceptée porte un commentaire `# zizmor: ignore[règle]` avec sa raison, en fin de la ligne signalée elle-même) et les tests des hooks `.claude/hooks/tests`. Job `skipped` si aucun workflow/hook ne change ; lancé quand même si la détection échoue | Oui (`Workflow lint`, pas sur `main`) | ~1 min |
| `zizmor-online.yml` (zizmor online) | cron mardi 05:37 UTC (copie de `develop`, audite `polity`) + push `develop`/`polity` touchant `.github/workflows/` + `workflow_dispatch` | Non — audits zizmor en ligne (SHA imposteur, ref ambiguë, action vulnérable connue) ; une issue `zizmor-online` reste ouverte tant qu'il y a des trouvailles ; un run en échec est signalé par `polity red alert` | Non | ~1 min |
| `human-review.yml` (Human review attestation) | `pull_request_target` (PR vers `polity`/`develop`) + `issue_comment` | Oui : pose le statut `High-risk review gate`, rouge sur une PR à chemin à risque ou qui affaiblit les tests jusqu'au `/reviewed <sha>` du propriétaire | Oui (pas sur `main` ni `polity-ui`) | quelques secondes |
| `ci-health.yml` (CI Health Watchdog) | PR (`main`/`develop`/`polity`) + push `develop` + cron quotidien 08:07 UTC + `workflow_dispatch` | Job `CI health check` : oui (vérifie l'instantané `.github/ci-health.json`) · job `audit` : ouvre/rafraîchit la PR `chore/ci-health-snapshot` | Oui (aussi sur `main`) | <1 min |
| `red-on-base.yml` (Red on base) | PR vers `polity`/`develop` | Non — consultatif (voir le tableau des checks plus haut) | Non | ~2-5 min |
| `mutation-diff.yml` (Diff Mutation) | PR vers `polity` | Non — consultatif ; jeton en lecture seule, le résumé part en artefact | Non | quelques minutes, selon les lignes modifiées |
| `mutation-diff-comment.yml` (Diff Mutation comment) | `workflow_run` de Diff Mutation (copie de `develop`) | Non — poste le résumé de chaque outil en commentaire unique, sans exécuter le code de la PR | Non | quelques secondes |
| `atheris-fuzzing.yml` (Coverage-Guided Fuzzing) | push `develop`/`polity` (moteur, parseurs LLM) + cron jeudi 04:44 UTC + `workflow_dispatch` | Non — jamais sur PR | Non | variable |
| `dast.yml` (DAST — ZAP Baseline) | push `develop`/`polity` + cron nocturne 02:42 UTC + `workflow_dispatch` | Non — jamais sur PR | Non | variable |
| `branch-red-alert.yml` (polity red alert) | `workflow_run` des workflows surveillés + cron quotidien 09:23 UTC + `workflow_dispatch` (copie de `develop`) | Non — tient une issue `polity-red` ouverte tant qu'un workflow surveillé est rouge sur `polity` | Non | <1 min |
| `ci-dashboard.yml` (CI Dashboard) | `workflow_run` (`polity`/`develop`) + cron horaire + lundi 06:47 UTC + `workflow_dispatch` (copie de `develop`) | Non — tableau de bord GitHub Pages et issue `CI weekly report` le lundi | Non | ~1-2 min |

**`merge-to-main.yml` (Check Merge Source) a été supprimé** : son unique
vérification ("seule `develop` peut merger dans `main`") faisait double emploi
avec l'étape `Check source is develop (PRs to main)` de `branch-policy.yml`
ci-dessus — mais sous `pull_request_target` plutôt que le `pull_request` plus
sûr utilisé par `branch-policy.yml`, sans bloc `permissions:`. Son job
(`check-branch`) n'était pas dans la liste des checks requis de `develop` —
suppression sans impact sur `scripts/setup-branch-protection.sh`. (`main` est
protégée par `protect_main` : PR obligatoire, mêmes checks requis que
`develop` sans la porte de revue ni Workflow lint, qui ne tournent pas sur les
PR vers `main`, 0 approbation, `enforce_admins: false` comme `polity` et
`develop`, mais `strict: false` : le commit de merge de chaque release reste sur
`main` sans revenir dans `develop`, donc avec `strict` la PR de release suivante
serait toujours « en retard ». `release.yml` n'y pousse plus rien : la version vient de
`voter-app/package.json`, montée par une PR, et le job ne pousse que le tag.
Voir le skill `release`.)

**Comment Backend/Frontend CI, E2E et OpenAPI Contract sont devenus des checks
requis malgré leur portée `paths`** : les quatre étaient auparavant scopés par
un `paths:` au niveau du déclencheur (`on.push`/`on.pull_request`). Une PR qui
n'y touchait pas (docs, config CI, ce fichier) ne les déclenchait jamais — et
un check requis qui ne se déclenche jamais bloque la PR indéfiniment. Confirmé
en direct : la PR #205 (un fix de `branch-policy.yml` + `CONTRIBUTING.md`)
s'est retrouvée bloquée exactement comme ça, ce qui les avait fait exclure de
`scripts/setup-branch-protection.sh` à l'époque. Le vrai correctif : le filtre
`paths:` vit maintenant dans un job `changes` (via `dorny/paths-filter`) à
l'intérieur de chaque workflow, pas au niveau du déclencheur — le workflow se
déclenche donc toujours (le check-run existe toujours), et c'est le job réel
qui devient `skipped` quand rien de pertinent n'a changé. GitHub traite un
check requis `skipped` comme un succès, donc la PR n'est plus jamais bloquée
indéfiniment. **Piège à éviter** : si vous réintroduisez un `paths:` au niveau
`on.push`/`on.pull_request` sur l'un de ces quatre fichiers, retirez-le
d'abord de `REQUIRED_CONTEXTS` dans `scripts/setup-branch-protection.sh` — sinon
c'est exactement le bug de la PR #205 qui revient.

`schedule`, `workflow_dispatch`, `workflow_run`, `issue_comment` et
`pull_request_target` sont résolus par GitHub contre la **branche par défaut du
dépôt** (`develop`), pas contre la branche où vit le fichier. Un changement
d'un de ces workflows (crons, `branch-red-alert.yml`, `ci-dashboard.yml`,
`human-review.yml`…) ne prend effet qu'après la synchronisation `polity →
develop` suivante. Les crons des tests profonds sortent `polity` eux-mêmes
(`ref: polity`), pour tester la branche de travail.

---

## Titre de PR — Conventional Commits

```
type(scope): description courte
```

Types valides : `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `ci`, `security`, `perf`

**Exemple :** `feat(blank-vote): add threshold_30 rule to scenario builder`

---

## Seuils qualité

| Métrique | Seuil | Fichier |
|---|---|---|
| Coverage frontend | lines 86 % · statements 84 % · functions 75 % · branches 74 % | `voter-app/vitest.config.ts` (`test.coverage.thresholds`) |
| Coverage backend | 90 % | `fast_api_voter/pyproject.toml` (`--cov-fail-under`) |
| eslint | 0 **erreur** (les warnings passent) | `voter-app/eslint.config.js` |
| ruff | 0 sur `F` (pyflakes — erreurs de nom, imports morts…) et `NPY002` | `fast_api_voter/pyproject.toml` |
| mypy | strict, 0 erreur sur `api/` | `fast_api_voter/mypy.ini` |
| Couches `routes → domain → engine` | bloquant, 0 import remontant | `fast_api_voter/pyproject.toml` (`[tool.importlinter]`) |
| `src/lib` pur (pas de dépendance vers `components`/`pages`) | bloquant, 0 violation | `voter-app/.dependency-cruiser.json` |
| Tests e2e instables | 0 — un test qui ne passe qu'au *retry* fait échouer la PR | `voter-app/scripts/check-flaky.mjs` |
| Dette qualité (vulture/radon/deptry/knip/jscpd/sonarjs, et `mypy_scripts` : erreurs mypy strict sur `fast_api_voter/scripts/*.py`, sans ses sous-dossiers) | ne doit jamais augmenter (ni baisser sans `--update`) | `.github/quality-baseline.json` via `scripts/check_quality_ratchet.sh` |
| Complexité moyenne (radon) | rang A, bloquant | `xenon -a A` dans `audit.yml` |
| Couverture des lignes modifiées | 100 %, bloquant (backend et frontend) | `diff-cover` dans les workflows Backend/Frontend CI |
| Score de mutation backend | ne baisse pas au-delà du bruit (hors PR) | `.github/mutation-baseline.json` via `scripts/check_mutation_score.sh` |
| npm audit severity | high (arbre complet, exceptions datées) | `npm run audit:gate` + `.github/npm-audit-allowlist.json` |
| Bandit severity | medium+ | `-ll` dans args bandit |
| Licence des dépendances de *production* | allow-list MIT/BSD/Apache/MPL-2.0/PSF-2.0-like, 0 exception | `fast_api_voter/scripts/check_license_compliance.sh` (backend, venv isolé) ; `license-checker-rseidelsohn --production --onlyAllow` (frontend, `frontend-ci-cd-pipeline.yml`) |
| Perf moteur de vote (pytest-benchmark) | plafond absolu par palier de complexité : 100 ms (tallies O(n)/cardinal), 500 ms (élimination/appariement/Kemeny) — pas une comparaison à une baseline stockée (voir `docs/exploration/EXP-006-pytest-benchmark-engine-perf.md`) | `fast_api_voter/api/tests/test_engine_benchmarks.py` |

> Ces seuils sont ceux appliqués par la CI. Le tableau a déjà menti pendant
> plusieurs mois (il annonçait 30 % et un `jest.config.cjs` supprimé lors du
> passage à Vitest) — si vous changez un seuil, changez cette ligne dans la
> même PR.

---

## Tests E2E (Playwright) — et comment ils restent à jour

```bash
cd fast_api_voter && uvicorn api.main:app --port 4434   # Assemblée + 2 fiches du Lab en ont besoin
cd voter-app && npm run test:e2e                        # chromium + firefox + webkit + mobile
```

La suite a déjà pourri une fois : 5 specs figées sur une UI qui avait bougé
pendant deux mois, chaque test brûlant son timeout de 60 s jusqu'à ce que le job
soit tué à 25 min sans rapport. Trois garde-fous, dans l'ordre d'efficacité :

1. **Elle tourne sur chaque PR** (`e2e.yml`, déclenché par tout changement dans
   `voter-app/` ou `fast_api_voter/`, hors scripts, tests backend et `.md`). Une dérive se voit en une PR, pas en deux
   mois. C'est 90 % du sujet.
2. **Les routes sont des données.** `voter-app/src/routes.ts` liste les surfaces
   et les redirections ; `App.tsx` en dérive ses `<Route>` et
   `tests/e2e/routes.ts` importe la même table. Ajouter une route la fait
   couvrir ; une surface sans ancre de test fait échouer le run.
3. **On s'accroche aux `data-testid`**, jamais aux classes CSS ni aux chaînes
   traduites — les deux bougent (la migration Tailwind avait invalidé tous les
   sélecteurs `.card`/`.badge` de l'ancienne suite). Les tests tournent en
   `fr-FR` mais assertent sur des testids.

Corollaire : **si vous supprimez un `data-testid` ou une route, la PR devient
rouge** — c'est voulu, c'est le seul moment où mettre le test à jour coûte
presque rien.

**Un test instable fait échouer la PR.** La CI relance chaque test une fois
(`retries: 1`) ; un test qui échoue puis passe était jusqu'ici rapporté vert,
sans le moindre signal — c'est exactement le mécanisme par lequel une suite se
dégrade en silence. `scripts/check-flaky.mjs` lit le rapport JSON de Playwright
et fait échouer le job en nommant les tests concernés. Un test instable se
répare ou se supprime ; il ne se tolère pas.

### Régression visuelle (Lot 7)

```bash
cd fast_api_voter && uvicorn api.main:app --port 4434   # ParliamentCanvas en a besoin
cd voter-app && npm run test:visual                     # comparaison rapide, environnement local
cd voter-app && npm run test:visual:docker               # comparaison faisant foi (image Docker épinglée)
cd voter-app && npm run test:visual:docker:update         # régénère les baselines dans cette même image
```

`tests/e2e/visual.spec.ts` (config séparée, `playwright.visual.config.ts`) —
capture les 5 surfaces de `routes.ts` plus les deux types de carte
(`LeaderCanvas`/`ParliamentCanvas`). **`npm run test:visual` local est une
vérification rapide, pas la vérité** : les comparaisons de pixels ne sont
fiables que si la baseline et la comparaison rendent dans le même
environnement au bit près (polices, anti-aliasing) — la CI et les commandes
`:docker` tournent toutes dans la même image Playwright officielle, épinglée
à la version exacte de `@playwright/test`. Ne jamais committer une baseline
générée hors de cette image ; `npm run test:visual:docker:update` la
régénère correctement. Détail complet (pourquoi le serveur de dev est
inutilisable ici, pourquoi `ParliamentCanvas` a besoin du backend, comment
une tolérance de pixels mal calibrée a été détectée) :
[`docs/exploration/EXP-004-regression-visuelle-playwright-screenshots.md`](docs/exploration/EXP-004-regression-visuelle-playwright-screenshots.md).

---

## Code mort, duplication & conventions "vibe coding"

Une grande partie de ce repo est écrite avec l'aide de LLM (Claude Code &
autres). Ces outils rapportent leurs trouvailles sans jamais faire échouer
leur propre étape (voir [`CODE_AUDIT.md`](docs/plan/vote-app/CODE_AUDIT.md)
pour l'état des lieux) :

| Outil | Détecte | Lancer en local |
|---|---|---|
| `vulture` | Code mort backend (fonctions, variables, imports jamais utilisés) | `cd fast_api_voter && python -m vulture api/ .vulture_whitelist.py --config pyproject.toml` |
| `radon`/`xenon` | Complexité cyclomatique backend (fonctions trop ramifiées) | `cd fast_api_voter && python -m radon cc api/ -e "api/tests/*" -n C -s` |
| `deptry` | Dépendances Python déclarées-mais-inutilisées / utilisées-mais-non-déclarées | `cd fast_api_voter && python -m deptry .` (config dans `pyproject.toml`'s `[tool.deptry]`) |
| `knip` | Fichiers/exports/dépendances inutilisés côté frontend | `cd voter-app && npm run knip` |
| `jscpd` | Duplication de code cross-langage (Python + TS) | `npx jscpd --config .jscpd.json fast_api_voter/api voter-app/src` |

`dependency-cruiser` n'est **pas** dans ce tableau : contrairement aux outils
ci-dessus (dette non-bloquante suivie par le cliquet), c'est un vrai gate —
voir le tableau « Seuils qualité » plus haut et `voter-app/.dependency-
cruiser.json`. Équivalent frontend d'`import-linter` : `src/lib` (libs pures,
voir CLAUDE.md — section Playground) ne doit jamais importer depuis
`src/components` ou `src/pages`. Épinglé en `17.4.3` (pas la dernière
majeure) : `18.x` exige Node `^22||^24||>=26` — était bloqué tant que la CI
tournait sur Node 20 (EOL 2026-04-30), débloqué par le passage de la CI à
Node 24 (2026-09) mais pas encore tenté ; bump à essayer séparément, pas
mécaniquement en même temps que le changement de runtime. `npm run
depcruise` en local.

Tous tournent aussi dans `scripts/audit.sh` (mode `--quality` ou complet)
et dans le job CI *Code Quality* de `audit.yml`.

**Ce qui bloque, c'est le cliquet.** Les outils ci-dessus restent non-bloquants
(échouer sur l'arriéré existant ferait simplement désactiver le job), mais
`scripts/check_quality_ratchet.sh` compare leurs comptes à
`.github/quality-baseline.json` et **échoue si un compte augmente**. La dette
existante est acquise, la dette neuve ne l'est pas.

Si votre PR fait *baisser* un compte, le cliquet échoue aussi — c'est voulu, une
baseline que seul un humain pense à resserrer ne se resserre jamais :

```bash
git merge origin/polity                       # ← indispensable, voir ci-dessous
./scripts/check_quality_ratchet.sh --update   # puis committez .github/quality-baseline.json
```

**Mesurez toujours sur une branche à jour.** La CI lance ces outils sur le
résultat de merge de la PR : une branche coupée avant le merge de quelqu'un
d'autre produit des comptes que la CI ne reproduira pas.

Un faux positif se réduit au silence à la source (`.vulture_whitelist.py`,
`fast_api_voter/pyproject.toml`'s `[tool.deptry.per_rule_ignores]`,
`voter-app/knip.json`, `.jscpd.json`), pas en remontant la baseline. Un script
lancé par la CI mais importé par personne — `voter-app/scripts/check-flaky.mjs`
en est un — est un faux positif knip : il s'ajoute à `ignore`.

### Règles Semgrep custom (Lot 2)

`.semgrep/vote-app-rules.yml` — les jeux de règles génériques de Semgrep
(`p/python`, `p/security-audit`, …) ne connaissent pas les conventions
propres à ce repo. Deux règles maison, **bloquantes**, tournent dans la même
étape gating que le reste de Semgrep (`audit.yml`) :

- `v2-router-missing-rate-limit` — tout `APIRouter(prefix="/api/v2/...")` doit
  porter `dependencies=[Depends(check_v2_rate_limit)]` (sauf `/api/v2/health`,
  une sonde de vivacité). Trouvé et corrigé en écrivant la règle : `tech.py`,
  `theory.py`, `export.py` n'avaient aucune limite de débit.
- `except-exception-without-log` — un `except Exception` sans appel `log.*`
  dans le bloc est un bug avalé en silence. Scope limité à
  `fast_api_voter/api/` (pas tout le repo — voir le commentaire dans le
  fichier de règles). Trouvé et corrigé : 18 sites muets sur 9 fichiers.

Une troisième règle prévue au plan initial (« aucun worker n'importe
`api.routes` ») n'a pas été dupliquée ici : `import-linter` (voir plus haut)
l'applique déjà via une vraie analyse du graphe d'imports, plus précise
qu'un pattern-match.

### Fuzzing du contrat API (Schemathesis, Lot 3)

`openapi.gen.json` a un gate de drift (`openapi-contract.yml`) contre ce que
FastAPI *déclare*, mais rien ne vérifiait que l'implémentation tient
réellement cette promesse. `api/tests/test_schema_contract.py` génère des
requêtes valides pour chacune des 69 opérations (au 2026-10-07) et vérifie que la réponse
correspond aux codes/schémas documentés :

```bash
cd fast_api_voter && python -m pytest api/tests/test_schema_contract.py -v -o addopts=""
```

`-o addopts=""` est nécessaire : par défaut ce fichier est exclu de
`pytest api/tests` (voir `pyproject.toml`). Un run complet mesure ~220s (~3.5-4 min) en
local (mode de génération POSITIVE uniquement, entiers lourds plafonnés à
100, pas de phase de shrink — voir le docstring du fichier pour le détail de
chaque choix), mais ce chiffre n'a pas été revérifié sur un vrai runner
GitHub Actions — le fuzzing HTTP a plus de variance qu'un lint/typecheck
déterministe. Par prudence il tourne dans son propre workflow,
`schemathesis.yml`, jamais bloquant et jamais sur PR (même tradeoff que
`mutation-testing.yml`).

**`KNOWN_FAILURES` est un cliquet nommé, pas un silence.** Contrairement au
cliquet générique (`.github/quality-baseline.json`, un simple compte par
outil), chaque entrée est un couple `endpoint: raison`, classée
`[timeout]`/`[loose-req]`/`[resp-shape]`/`[validator]` — un lecteur peut voir
*quel* endpoint a de la dette et pourquoi, sans relancer l'outil. Écrire ce
fichier a trouvé et corrigé 3 bugs réels en route (voir `CODE_AUDIT.md` pour
le détail) avant qu'ils ne rejoignent la liste des exceptions.

### Preuve exhaustive de parité front/back sur les petits profils (Lot 4.3)

La parité front/back (CLAUDE.md) reposait sur 60 scénarios *aléatoires* (voir
`fast_api_voter/scripts/gen_engine_parity.py`) filtrés par `strict_winner` —
un profil n'est comparé que si le gagnant backend survit à 200 relabellings,
pour ignorer les cas décidés par un tie-break plutôt que par l'algorithme.
Problème : ce filtre saute aussi, par construction, tous les profils où le
gagnant backend est `None` ou dépend d'une égalité — exactement là où des
divergences front/back peuvent se cacher.

Pour n ≤ 4 candidats et m ≤ 5 électeurs, l'espace des profils est fini et
petit : grâce à l'anonymat des règles (`test_anonymity.py`), il se réduit à
des multi-ensembles de bulletins (118 754 profils pour n=4 seul, calculables
en ~28s côté backend). Comparaison **exhaustive et non filtrée** :
gagnant backend Python contre `ruleWinnerFromRanks` (front), gagnant exact
exigé y compris `None`/égalité — pas seulement « les deux s'accordent quand
c'est non-ambigu ».

**Résultat : 5 méthodes sur 21 divergeaient réellement**, chacune investiguée
et corrigée (détail complet dans `PLAN_SOLIDITE_TECHNIQUE.md`, § 4.3) :
`condorcet` (mauvaise fonction backend comparée — `get_condorcet_winner` le
critère strict, pas `get_copeland_winner` la méthode que le front implémente
réellement, plus un départage de égalité différent une fois corrigé),
`two_round` (égalité de second tour mal départagée), `benham`/`smith_irv`
(fallback alphabétique du backend sur égalité totale non répliqué côté front),
et `dowdall` (un vrai bug **backend** cette fois : `Fraction` neutralisé par
un `defaultdict(float)`, réintroduisant le bug de précision flottante que le
code prétendait éviter — trouvé par la comparaison avec le front, qui lui
était déjà protégé).

Une nouvelle clé du fixture, `exhaustiveScenarios` (voir
`generate_exhaustive_scenarios` dans `gen_engine_parity.py`), committe les 481
profils exhaustifs pour n≤3 — gagnants **bruts**, pas filtrés par
`strict_winner`, pour ne jamais remasquer cette classe de bug. Régénérée et
vérifiée à chaque PR comme le reste du fixture :

```bash
cd voter-app && npx vitest run src/lib/playgroundVoting.parity.test.ts
```

n=4 (98 280 profils de plus, ~60 Mo de JSON une fois sérialisé) n'est pas
committé — vérifié une fois en développement, mais un fixture de cette taille
ralentirait `check_engine_parity_drift.sh` sur chaque PR pour couvrir la même
classe de bug qu'une tranche n≤3 beaucoup plus petite détecte déjà.

### Oracle tiers pour le moteur de vote (`pref_voting`, Lot 4.2)

La parité front/back (CLAUDE.md) compare *mes deux* implémentations, qui
peuvent être fausses **ensemble** — un bug dans les deux moteurs à la fois ne
serait jamais détecté. `pref_voting` (Pacuit & Holliday) est une bibliothèque
académique de théorie du choix social, indépendante du code de ce repo :
croiser nos 21 méthodes ordinales contre les siennes casse cette corrélation
d'erreur.

**`pref_voting` n'est pas une dépendance du projet** — elle requiert Python
`<3.14` (elle dépend de `numba`), incompatible avec le `3.14` de
`fast_api_voter`. La passe s'est faite dans un venv jetable séparé
(`~/.pyenv/versions/3.11.16` + `pip install pref_voting`), avec un script à
deux étapes : un premier process (le venv normal du projet) sérialise des
profils aléatoires et les gagnants de notre moteur en JSON, un second
(le venv `pref_voting`) relit ce JSON et compare chaque gagnant à l'ensemble
des gagnants (avec égalités) que retourne la méthode équivalente de
`pref_voting` — comparaison **« mon gagnant ∈ l'ensemble oracle »**, pas
égalité stricte, puisque les conventions de tie-break diffèrent
légitimement entre implémentations indépendantes.

3000 profils (3-4 candidats, 3-11 électeurs) × 21 méthodes : **18/21 sans
aucun écart.** Les 4 écarts trouvés, tous investigués à la main avant
conclusion (détail complet dans `PLAN_SOLIDITE_TECHNIQUE.md`, § 4.2) :

- `dowdall` (1 écart) : pas un bug ici — un artefact de précision flottante
  **dans `pref_voting` lui-même** (deux candidats exactement à égalité en
  fractions exactes, mais l'ordre de sommation en flottant de la lib casse
  l'égalité par un epsilon).
- `baldwin` et `raynaud` (11 et 27 écarts) : bugs réels, corrigés — les deux
  n'éliminaient qu'un seul candidat par tour au lieu de tous les candidats à
  égalité pour le pire score/la pire défaite, contrairement à `get_irv_winner`/
  `get_nanson_winner` dans le même fichier.
- `smith_irv` (75 écarts, le plus fréquent) : bug réel dans `_smith_set` (test
  de dominance qui ignorait les égalités pairwise) et dans
  `get_smith_irv_winner` (l'ensemble de Smith était recalculé à chaque tour
  au lieu d'une seule fois — pas la définition standard de Smith-IRV/Tideman's
  Alternative). Une fois corrigé, `smith_irv` s'est révélé réellement
  clone-indépendant — voir la note dans la section suivante.

Chaque correctif backend a son miroir dans `playgroundVoting.ts`/
`voteTrace.ts` (parité front/back oblige) ; `engineParity.json` régénéré et le
test de parité repassé au vert après coup.

### Matrice axiomatique de théorie du choix social (Lot 4.1)

`api/tests/test_voting_criteria_matrix.py` vérifie, pour chacune des 21
méthodes ordinales verrouillées en parité (voir CLAUDE.md — moteur de vote
double), lesquels des 7 critères classiques de la théorie du choix social
(Condorcet gagnant, Condorcet perdant, majorité, unanimité, Pareto,
indépendance des clones, monotonie) elle satisfait et lesquels elle viole. Un
test qui prouve qu'une méthode **viole** un critère est aussi précieux qu'un
test de succès : il documente la théorie *et* détecte une implémentation
devenue accidentellement plus « bien élevée » qu'elle ne le garantit
réellement — `test_anonymity.py` en était déjà le germe, généralisé ici en
matrice méthode × critère :

```bash
cd fast_api_voter && python -m pytest api/tests/test_voting_criteria_matrix.py -o addopts="" -q
```

**Méthodologie.** La classification n'est pas tirée de mémoire : chaque
cellule vient d'abord d'une exploration empirique jetable (quelques centaines
de profils aléatoires par méthode/critère), puis chaque « satisfait » est
reformulé en test `@given` (Hypothesis, `derandomize=True` pour la
reproductibilité — confirmé stable sur plusieurs process et plusieurs valeurs
de `PYTHONHASHSEED`) qui fait foi en dernier ressort. Le premier passage
d'exploration a sous-échantillonné 4 cellules : `ranked_pairs`, `river` et
`smith_irv` semblaient satisfaire l'indépendance des clones, et `nanson`
semblait satisfaire la monotonie. Les quatre échouent en réalité, mais
seulement sur des profils dégénérés à égalité parfaite (marges pairwise ou
votes de premier choix exactement à égalité) — assez rares pour n'être
trouvés que par la recherche par réduction (« shrinking ») de Hypothesis sur
le test complet, pas par un tirage aléatoire à quelques centaines d'essais.
Les 4 contre-exemples ont été vérifiés à la main (script indépendant) avant
d'être épinglés dans le fichier. `smith_irv` en est ressorti une seconde
fois lors du Lot 4.2 (oracle tiers) : son échec d'indépendance aux clones
était en fait un symptôme d'un vrai bug dans `_smith_set`/
`get_smith_irv_winner` (voir plus haut, § oracle tiers) — une fois corrigé,
`smith_irv` satisfait réellement le critère, et est repassé côté « satisfait »
dans ce fichier.

Hors périmètre pour cette passe : participation et symétrie par renversement.
Du signal réel existe pour les deux, mais aussi du bruit lié aux égalités de
score (un profil avec un tie exact peut faire comparer deux résultats
structurellement différents comme identiques, sans que ce soit une vraie
violation d'axiome) — démêler « violation réelle » de « tie-break
coïncidental » cellule par cellule demande une passe plus soigneuse que
celle-ci. Suivi nommé, pas deviné.

### Matrice axiomatique côté client (`fast-check`, Lot 4.4)

`voter-app/src/lib/playgroundVoting.axioms.test.ts` reporte les 7 mêmes
critères contre `ruleWinnerFromRanks` — l'autre moitié du contrat de parité,
qui n'avait aucun test à propriétés. Domaine volontairement plus large que
la matrice Python : n ∈ [3,6] candidats (`_profiles4` fige n=4) et m ∈
[3,25] électeurs — hors de la boîte n≤4/m≤5 déjà prouvée exhaustive par le
Lot 4.3, pour que ce fichier gagne sa place sur du terrain neuf plutôt que
de re-prouver ce qui l'est déjà :

```bash
cd voter-app && npx vitest run src/lib/playgroundVoting.axioms.test.ts
```

La classification n'est pas recopiée aveuglément de Python — rejouée
réellement sur ce domaine plus large, ce qui a trouvé **6 corrections
réelles**, toutes vérifiées à la main contre le backend (détail complet
dans `PLAN_SOLIDITE_TECHNIQUE.md`, § 4.4) : `baldwin` échoue l'indépendance
aux clones mais seulement à n=6 (hors de portée de la stratégie Python figée
à 4 candidats) ; `condorcet` (Copeland côté client — une fonction différente
de la clé Python du même nom, voir le fichier) échoue aussi l'indépendance
aux clones, un cas d'école pour un score net victoires-défaites ; `irv`,
`coombs`, `benham` et `raynaud` élisent chacun un perdant de Condorcet dans
des profils que les 200 exemples Hypothesis fixes de Python n'avaient
jamais échantillonnés. Ce dernier groupe a révélé le critère « perdant de
Condorcet » plus fuyant que prévu, d'où un balayage Python direct à plus
gros volume (~15-24k profils/méthode) qui a tranché une septième cellule
(`dowdall` × majorité) et confirmé le reste de la matrice.

**Reproductibilité.** `fast-check` tire une seed aléatoire par défaut à
chaque run — exactement ce qui a permis de trouver ces 6 corrections
pendant le développement, mais inacceptable pour un test committé (un échec
flaky qui trouve parfois un vrai bug reste un run flaky). Seed fixée une
fois l'exploration terminée, même leçon que `derandomize=True` pour
Hypothesis (Lot 4.1/4.2).

### Contre-exemples de la littérature (Lot 4.5)

`fast_api_voter/api/tests/test_literature_counterexamples.py` — quatre
résultats classiques de la théorie du choix social, chacun sourcé (clé
BibTeX dans `docs/research/bibliography.bib`, prose pédagogique dans
`THEORY.md` §4) et vérifié à la main sur ce moteur avant d'être committé :
le paradoxe de Condorcet (1785), le désaccord des règles positionnelles
(Saari, 1995), la motivation de Ranked Pairs contre la non-indépendance aux
clones de Copeland (Tideman, 1987 — réutilise un contre-exemple déjà trouvé
au Lot 4.4), et le paradoxe du non-vote (Fishburn & Brams, 1983), qui clôt
une petite tranche nommée du critère de participation resté hors périmètre
au Lot 4.1.

```bash
cd fast_api_voter && python -m pytest api/tests/test_literature_counterexamples.py -o addopts="" -v
```

Avant d'écrire quoi que ce soit ici : vérifié que le cas le plus évident (une
vraie élection où la méthode change le vainqueur) n'était pas déjà couvert
en double — il l'était déjà (`voter-app/src/lib/realElections.ts`,
Burlington 2009 / Alaska 2022, sourcé PrefLib et arXiv). Le trou réel était
les exemples synthétiques classiques, absents des deux moteurs jusqu'ici.

### Preuves formelles Z3 (Lot 4.6, expérience à risque assumé)

`fast_api_voter/api/tests/test_z3_formal_proofs.py` (`z3-solver` en
dépendance de dev) — au lieu d'échantillonner des profils concrets, encode
les décomptes de voix comme des variables entières **symboliques** et
demande au solveur SMT s'il existe un contre-exemple. `unsat` = preuve
qu'aucun n'existe, pour **tous** les électorats possibles à un nombre de
candidats donné, pas un échantillon aussi grand soit-il :

```bash
cd fast_api_voter && python -m pytest api/tests/test_z3_formal_proofs.py -o addopts="" -v
```

Deux méthodes seulement (minimax, Schulze), un seul critère (Condorcet
gagnant) — le fichier prouve littéralement tout électorat jusqu'à n=7
candidats, en quelques secondes en CI. Une troisième cible (IRV) a produit
un résultat silencieusement **faux** avant d'être corrigée — encodage plus
fragile pour un gain déjà obtenu autrement, donc non committé. Carnet
complet (le faux résultat, comment il a été détecté, ce qui a fini par
marcher) : [`docs/exploration/EXP-002-z3-formal-voting-proofs.md`](docs/exploration/EXP-002-z3-formal-voting-proofs.md).

### Score de mutation (informationnel)

La couverture mesure les lignes *exécutées*, pas les lignes *assertées* — un
test sans `expect` la fait monter autant qu'un vrai. Le workflow
`mutation-testing.yml` (jamais sur une PR, mais rouge sur une régression) mesure la différence sur les deux
moitiés du moteur de vote :

```bash
cd fast_api_voter && python -m mutmut run   # backend  (Linux/WSL uniquement)
cd voter-app && npm run test:mutation       # frontend (Stryker)
```

Il se déclenche sur **push vers `develop` ou `polity` touchant un fichier
moteur** (un score de mutation ne peut bouger que si le code muté bouge), en cron
le lundi à 04:17 UTC et à la demande. Le cliquet `scripts/check_mutation_score.sh`
(baseline `.github/mutation-baseline.json`) n'échoue que sur une vraie baisse,
jamais sur une hausse : après une amélioration, lancez-le avec `--update` sur le
log du run et committez la baseline.

Sur chaque PR vers `polity`, **`mutation-diff.yml`** (consultatif) ne mute que
les lignes (Stryker) ou les fonctions (mutmut) que la PR modifie ; chaque
mutant survivant est une ligne modifiée qu'aucun test n'attraperait. Ses jobs
exécutent le code de la PR, donc sans jeton d'écriture : le commentaire unique
par outil est posté ensuite par `mutation-diff-comment.yml` (`workflow_run`,
depuis `develop`).

> **Piège GitHub Actions à connaître.** `schedule` et `workflow_dispatch` sont
> résolus contre la **branche par défaut** (`develop`), pas contre celle où vit
> le fichier : un cron ajouté sur `polity` ne tourne qu'après la synchronisation
> vers `develop`. `push` et `pull_request`, eux, utilisent le fichier de la
> branche poussée.

### Ordre de test aléatoire et chasse au flake (Lot 5)

`pytest-randomly` (dépendance de dev) mélange l'ordre des tests à **chaque**
run, local ou CI, sans configuration — un ordre de collecte figé masque les
tests couplés par un état partagé (global de module, fixture mal isolée),
exactement le genre de piège déjà rencontré une fois avec le rate limiter
partagé entre tests.

Un run isolé ne montre qu'**un seul** ordre parmi des millions possibles ;
le signal de flakiness vient de comparer plusieurs runs entre eux, pas d'un
run réussi. `scripts/check_flaky_backend.py` relance la suite complète 3
fois (process indépendants, seed `pytest-randomly` différente à chaque
fois) et diffe le résultat de chaque test entre les 3 runs :

```bash
python scripts/check_flaky_backend.py --runs 3
```

`.github/workflows/flaky-check-backend.yml` l'exécute nightly + sur push
`develop`/`polity` touchant le moteur + `workflow_dispatch`, jamais bloquant sur PR
(coût de 3 passes complètes, pas de place dans un gate par PR). Détecteur
vérifié en direct sur un couplage synthétique injecté avant de lui faire
confiance ; 3 exécutions réelles de la suite complète pendant le
développement de ce script : 0 flake trouvé.

**Limite assumée** : le script tourne avec `-n auto` (comme la suite
normale) pour rester à l'échelle de la minute plutôt que de la dizaine de
minutes. Un couplage qui n'existe qu'entre deux tests d'un même *worker*
xdist peut, selon la façon dont xdist les répartit, échouer (ou réussir) de
façon constante au lieu de varier d'un run à l'autre — ce script ne le
détecterait pas comme flaky. Un échec constant reste néanmoins visible : il
est attrapé par la suite normale à la prochaine PR qui touche ce code,
donc rien ne reste durablement invisible, juste classé différemment.

### Snapshots de sortie riche (`syrupy`, Lot 5)

`api/tests/test_compare_all_methods_snapshot.py` — le rapport de
`compare_all_methods` (26 méthodes × 5 champs chacune) capturé en un seul
snapshot lisible (`api/tests/__snapshots__/*.ambr`) plutôt qu'en
assertions champ par champ, incomplètes par construction (on ne teste que
les champs auxquels on a pensé) ou illisibles à l'échelle (26 méthodes à
la main). Le diff d'un futur changement est exactement ce qui a changé,
relu par un humain au moment du commit :

```bash
cd fast_api_voter && python -m pytest api/tests/test_compare_all_methods_snapshot.py -o addopts="" --snapshot-update  # régénérer après un changement voulu
```

`create_voter`/`create_candidate` tirent de `random`/`numpy.random`
globaux sans paramètre de seed propre — indispensable de fixer les deux
explicitement avant de construire l'électorat, sinon le snapshot ne
capture rien de stable (vérifié sur 3 runs consécutifs avant de committer).

**Règles de processus pour limiter la dérive à l'usage d'un LLM :**

- Avant de créer un nouveau fichier du type `xxx_v2.py`, `workers_yyy.py` ou
  un nouveau composant dans `components/shared/`, chercher s'il existe déjà
  un module ou composant à étendre plutôt qu'à dupliquer (`grep`/recherche
  par domaine avant de générer du code neuf).
- Un fichier qui dépasse ~500 lignes est un signal pour se demander s'il faut
  le découper, pas une fatalité à laisser grossir PR après PR.
- `except Exception` (ou `except:`) nu est à éviter : capturer l'exception
  précise, ou documenter pourquoi le catch-all est nécessaire (voir
  `# noqa: BLE001` dans `api/sockets/__init__.py` comme modèle).
- Avant une PR volumineuse générée avec assistance LLM, lancer
  `./scripts/audit.sh --quality` et relire au moins les sections vulture /
  radon / deptry / knip / jscpd du résumé.

### Audit des commentaires — heuristique + passe sémantique (Lot 6.1)

Un commentaire est du code non compilé, non testé, jamais vérifié — la seule
zone du dépôt où une affirmation fausse peut survivre indéfiniment sans que
rien ne la signale. Deux outils, complémentaires, pas concurrents :

```bash
python scripts/audit_stale_comments.py                       # régénère docs/comment-audit/candidates.md
python scripts/audit_stale_comments.py --threshold-days 90    # seuil plus large
```

`audit_stale_comments.py` compare la date `git blame` d'un bloc de
commentaire à celle du code qui le suit — un écart significatif *présélectionne*
les candidats à relire, il ne prouve rien à lui seul (sur l'échantillon
vérifié en phase 1, seuls 15 des 329 candidats présélectionnés se sont
révélés effectivement faux une fois le contenu relu). Le tri final entre
**périmé** (corriger/supprimer), **redondant** (supprimer), **archéologique**
(migrer vers `docs/exploration/`) et **pourquoi** (garder, non négociable)
exige de lire le commentaire et le code, pas seulement leurs dates — voir
[`docs/exploration/EXP-001-audit-commentaires-heuristique-git-blame.md`](docs/exploration/EXP-001-audit-commentaires-heuristique-git-blame.md)
et [`docs/comment-audit/README.md`](docs/comment-audit/README.md) pour le
détail des deux passes et leur verdict chiffré. Le motif dominant trouvé en
2026-09 n'était pas l'usure isolée mais des commentaires figés à un stade de
migration révolu (Flask, Jest) — un signal à surveiller après toute
migration future : chercher spécifiquement les commentaires qui hedgent
encore pour l'ancien état une fois la migration terminée.

### Couverture *runtime* sous e2e (Lot 6.5)

La couverture unitaire (pytest-cov, Vitest) mesure ce qu'un test atteint en
appelant une fonction directement — pas ce qu'un vrai parcours utilisateur
déclenche jamais. `scripts/e2e_coverage.sh` fait tourner la vraie suite
Playwright avec le backend sous `coverage.py` et le frontend instrumenté par
Istanbul (`vite-plugin-istanbul`, actif seulement si `E2E_COVERAGE=true` —
zéro effet sur un build/dev normal), et produit deux rapports séparés de la
couverture unitaire :

```bash
./scripts/e2e_coverage.sh                # chromium + firefox
./scripts/e2e_coverage.sh --chromium-only
```

Diagnostique seulement, jamais un gate (script manuel, pas de workflow CI —
même non-bloquant) : l'instrumentation fait échouer de façon reproductible
un test de simulation client CPU-intensif sous la parallélisation par défaut
de la suite (timeout à 30 s sur firefox, 2/2 runs), un coût de stabilité qui
n'a pas sa place dans une suite qui tourne à chaque nightly. Détail complet
(les deux pièges de mécanisme trouvés en le construisant, les chiffres par
fichier, le raisonnement complet derrière le choix "manuel") :
[`docs/exploration/EXP-003-couverture-runtime-e2e.md`](docs/exploration/EXP-003-couverture-runtime-e2e.md).

### Charge — le vrai plafond du pool de threads (Lot 8.2)

`fast_api_voter/scripts/loadtest_v2_engine.py` (Locust) répond à une
question précise : le rate-limit `/api/v2` (120/min, `api/core/
ratelimit.py`) a été calibré au jugé contre un flake e2e, pas contre une
mesure de charge — que se passe-t-il *vraiment* quand plusieurs simulations
lourdes tournent en même temps ?

```bash
cd fast_api_voter
uvicorn api.main:app --port 4436 &          # un port dédié — vérifiez qu'il
curl -X POST http://localhost:4436/api/v2/simulations/monte-carlo -d '{}'  # est bien le vôtre avant de faire confiance aux résultats
uvx --from locust==2.46.5 locust -f scripts/loadtest_v2_engine.py --headless \
    -u 16 -r 4 -t 30s --host http://localhost:4436 --csv=/tmp/loadtest
```

Diagnostique seulement, jamais un gate (même raisonnement que la couverture
runtime ci-dessus : un test de charge est cher, lent, et sa mesure dépend de
la machine — un seuil calibré ici n'aurait aucun sens sur un runner GitHub
partagé). Verdict et chiffres réels (le pool de 4 workers partagés
`api/core/worker_dispatch.py` sature bien avant le rate-limit dès qu'un
endpoint fait un calcul non-trivial, et la dégradation se voit d'abord en
latence — pas en erreurs) :
[`docs/exploration/EXP-007-locust-v2-thread-pool-ceiling.md`](docs/exploration/EXP-007-locust-v2-thread-pool-ceiling.md).

---

## Commandes utiles

```bash
pre-commit run --all-files                              # lancer tous les hooks
detect-secrets scan --update .secrets.baseline         # mettre a jour la baseline
cd voter-app && npm test -- --coverage                 # coverage frontend
cd fast_api_voter && python -m pytest api/tests -n auto --cov=api  # coverage backend
pip-audit --requirement fast_api_voter/requirements.lock.txt --no-deps --disable-pip  # CVE Python
./scripts/check_openapi_drift.sh                        # contrat API à jour ?
```
