# Vote Lab — Stratégie de branches & qualité

## Modèle de branches

```
main          ← branche officielle, dernière version release
  ↑ PR develop → main uniquement (via workflow Release)
develop       ← branche d'intégration
  ↑ PR feature/* | fix/* | hotfix/* | ... → develop
feature/xxx   ← nouvelle fonctionnalité
fix/xxx       ← correction de bug
hotfix/xxx    ← correctif urgent
```

**Règle absolue** : on ne push jamais directement sur `main` ni `develop`.
Tout changement passe par une PR soumise à validation CI.

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
| `security/` | Correctif sécurité |
| `dependabot/` | Mises à jour automatiques (Dependabot — préfixe imposé, pas de choix) |

**Exemple :** `git checkout -b feature/vote-blanc-toggle`

---

## Workflow complet

### 1. Créer une branche depuis develop

```bash
git checkout develop && git pull origin develop
git checkout -b feature/ma-feature
```

### 2. Développer & commiter

Les hooks pre-commit vérifient à chaque `git commit` :
- Secrets / credentials, sécurité Python (bandit), linting, npm audit

Et à chaque `git push` :
- Tests frontend + coverage (seuils de `vitest.config.ts`)
- Tests backend + coverage >= 90 %

### 3. Ouvrir une PR vers develop

```bash
git push origin feature/ma-feature
# Ouvrir la PR : feature/ma-feature -> develop
```

**La CI vérifie automatiquement :**

| Vérification | Bloque la PR si... |
|---|---|
| Branch Policy | Branche source sans préfixe valide |
| Frontend CI | Tests échouent, coverage sous les seuils, ou eslint rapporte une erreur |
| Backend CI | Tests échouent, coverage < 90 %, mypy, ruff, ou la couche `routes → domain → engine` en erreur |
| npm audit | CVE haute détectée |
| E2E (Playwright) | Un parcours utilisateur casse sur Chromium ou Firefox — **ou passe seulement au second essai** (voir « Tests E2E » plus bas) |
| Generated Artifacts Contract | `openapi.gen.json` / `types.gen.ts` **ou** `engineParity.json` désynchronisés du code (voir `scripts/check_openapi_drift.sh` et `scripts/check_engine_parity_drift.sh`) |
| Quality ratchet | La dette vulture/radon/deptry/knip/jscpd a augmenté (voir « Code mort » plus bas) |
| Dependency Review | La PR introduit une dépendance vulnérable (sévérité high+) — complète Dependabot, qui ne scanne que l'existant, pas ce qu'une PR ajoute |

### 4. Release : develop → main

Uniquement via le workflow **Release Vote Lab** :
- GitHub → Actions → "Release Vote Lab" → Run workflow
- Choisir `patch`, `minor` ou `major`

Le workflow exige `ci-frontend`, `ci-backend` **et `e2e` (Playwright)** verts
avant de taguer/pousser sur `main`. La suite E2E tourne aussi sur chaque PR
`develop` : la réserver à la release avait laissé les specs pourrir deux mois
face à une UI qui avait bougé.

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
```

### Setup admin (droits admin GitHub requis)

```bash
bash scripts/setup-branch-protection.sh
```

**Merge queue** : [Mergify](https://mergify.com) (`.mergify.yml`), pas la
merge queue native GitHub — celle-ci est réservée aux repos publics
*organisation*, indisponible sur un repo à compte personnel comme celui-ci
(confirmé en direct par un 422 sur l'API rulesets). Mergify est gratuit pour
l'open source ; installer l'app GitHub sur le repo
(github.com/apps/mergify/installations/new) suffit — elle détecte
automatiquement les `required_status_checks` de la branch protection
ci-dessus et les injecte comme conditions de merge, aucune duplication dans
`.mergify.yml`. Chaque PR dont les checks passent est mise en file et
mergée automatiquement (`auto_merge_conditions: true`), retestée contre
l'état à jour de `develop` avant de vraiment merger (évite la classe de
problème "verte mais `mergeable_state: behind`", vécue en direct sur la PR
#188). Une fois Mergify vérifié en marche, désactiver *"Require branches to
be up to date before merging"* (`strict`) sur la branch protection —
Mergify le documente lui-même comme incompatible avec ses checks
parallèles, et re-teste de toute façon contre la dernière version avant de
merger.

---

## Ce qui se passe automatiquement

| Quand | Vérification | Bloque |
|---|---|---|
| `git commit` | detect-secrets, bandit, ruff, eslint, npm audit | Oui |
| `git push` | Tests + coverage (front + back) | Oui |
| PR ouverte | Branch Policy, CI complète, build | Oui |

---

## Carte des 11 workflows CI

11 fichiers dans `.github/workflows/` — sans une table à jour ici, la seule
source de vérité redevient "lire les 11 YAML". Si vous changez un déclencheur
ou un gate, mettez cette table à jour dans la même PR.

| Workflow | Déclencheur | Gate quand il tourne ? | Check requis (branch protection `develop`) ? | Durée typique |
|---|---|---|---|---|
| `backend-ci-cd-pipeline.yml` (Backend CI) | push/PR sur `develop`/`main`, toujours (le filtre `paths` vit maintenant dans un job `changes` interne, pas au niveau du déclencheur) | Oui, quand `fast_api_voter/**` a changé — sinon le job `test` est `skipped` | Oui | ~12-14 min (skip quasi instantané sinon) |
| `frontend-ci-cd-pipeline.yml` (Frontend CI) | push/PR sur `develop`/`main`, toujours (même schéma `changes`) | Oui, quand `voter-app/**` a changé — sinon `skipped` | Oui | ~2-3 min (skip quasi instantané sinon) |
| `e2e.yml` (E2E Tests) | push/PR + `workflow_dispatch` + `workflow_call` (depuis `release.yml`), toujours (même schéma `changes` ; dispatch/call ignorent le filtre) | Oui, quand `voter-app/**`/`fast_api_voter/**` a changé, ou toujours pour dispatch/call — sinon `skipped` | Oui | ~5-7 min (peut aller jusqu'au timeout de 25 min si une régression casse plusieurs specs en cascade) |
| `branch-policy.yml` (Branch Policy) | PR | Oui, y compris le format du titre (Conventional Commits — plus un simple avertissement) et la source pour les PR vers `main` (`Check source is develop`) | Oui | ~10-30 s |
| `openapi-contract.yml` (Generated Artifacts Contract) | push/PR, toujours (même schéma `changes`) | Oui, quand un fichier du contrat a changé — sinon `skipped` | Oui | ~1 min (skip quasi instantané sinon) |
| `dependency-review.yml` (Dependency Review) | PR sur `develop`/`main` | Oui — sévérité `high`+ introduite par la PR | Oui | ~15-30 s |
| `audit.yml` (Security Audit) | push/PR + cron lundi 06:00 UTC + `merge_group` | Semgrep/Trivy/Secret Scan : oui · CodeQL : le job doit terminer mais ne bloque pas sur ses trouvailles (elles atterrissent dans l'onglet Security) · code mort/duplication/complexité (vulture/radon/deptry/knip/jscpd) : non-bloquant sauf régression du cliquet (`quality-baseline.json`) · scan d'image Docker + SBOM (`image-scan`) : non-bloquant, et ne tourne que sur push `develop`/cron — jamais sur une PR (build de 2 images, coûte plusieurs minutes) | Oui (les 4 jobs gating + les 2 jobs CodeQL du matrix — `image-scan` n'est pas requis) | ~2-3 min sur PR (le run cron/push `develop`, qui inclut `image-scan`, est plus long et indépendant d'une PR) |
| `mutation-testing.yml` (Mutation Testing) | push sur `develop` (paths engine uniquement) + `workflow_dispatch` + cron lundi 04:17 UTC | Non — jamais bloquant | Non — ne se déclenche jamais sur PR | mutmut ~40 min-3h · Stryker jusqu'à ~2h30 en cold-cache (`timeout-minutes: 240`), moins avec le cache `--incremental` une fois chaud |
| `schemathesis.yml` (Schemathesis Contract Fuzzing) | push sur `develop` (paths `fast_api_voter/api/**`) + `workflow_dispatch` + cron lundi 05:38 UTC | Non — jamais bloquant | Non — ne se déclenche jamais sur PR | ~220s (~3.5-4 min) en local, non re-mesuré sur un runner GitHub réel (`timeout-minutes: 45` par prudence) |
| `flaky-check-backend.yml` (Backend Flaky Test Hunt) | push sur `develop` (paths `fast_api_voter/api/**`) + `workflow_dispatch` + cron quotidien 03:13 UTC | Non — jamais bloquant | Non — ne se déclenche jamais sur PR | ~1 min en local (3 exécutions parallélisées `-n auto`, ~16-18s chacune) |
| `release.yml` (🚀 Release Vote Lab) | `workflow_dispatch` uniquement | N/A — pas de PR, gate lui-même sur CI+E2E avant de taguer `main` | N/A | dépend de `ci-frontend`/`ci-backend`/`e2e` + publication |
| `scorecard.yml` (OpenSSF Scorecard) | push `develop` + cron mardi 07:30 UTC + changement de règle de protection + `workflow_dispatch` | Non — score publié dans l'onglet Security, jamais bloquant | Non | ~1-2 min |

**`merge-to-main.yml` (Check Merge Source) a été supprimé** : son unique
vérification ("seule `develop` peut merger dans `main`") faisait double emploi
avec l'étape `Check source is develop (PRs to main)` de `branch-policy.yml`
ci-dessus — mais sous `pull_request_target` plutôt que le `pull_request` plus
sûr utilisé par `branch-policy.yml`, sans bloc `permissions:`. Son job
(`check-branch`) n'était pas dans la liste des checks requis de `develop`, et
`main` elle-même n'a pas de protection de branche configurée — suppression
sans impact sur `scripts/setup-branch-protection.sh`.

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

`schedule`/`workflow_dispatch` (utilisés par `mutation-testing.yml`,
`schemathesis.yml` et `audit.yml`) sont résolus par GitHub contre la **branche
par défaut du dépôt**, pas contre une branche en particulier — un workflow
qui n'existe que sur une branche non-défaut ne se déclenche jamais sur ces
deux triggers, même s'il est mergé et présent dans le fichier. Pour
`schemathesis.yml`, c'est `push: develop` (scopé à `fast_api_voter/api/**`)
qui fait réellement tourner le job aujourd'hui — le cron/dispatch ne
deviendront actifs qu'après un `develop → main`.

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
| ruff | 0 sur `F` (pyflakes — erreurs de nom, imports morts…) | `fast_api_voter/pyproject.toml` |
| mypy | strict, 0 erreur sur `api/` | `fast_api_voter/mypy.ini` |
| Couches `routes → domain → engine` | bloquant, 0 import remontant | `fast_api_voter/pyproject.toml` (`[tool.importlinter]`) |
| `src/lib` pur (pas de dépendance vers `components`/`pages`) | bloquant, 0 violation | `voter-app/.dependency-cruiser.json` |
| Tests e2e instables | 0 — un test qui ne passe qu'au *retry* fait échouer la PR | `voter-app/scripts/check-flaky.mjs` |
| Dette qualité (vulture/radon/deptry/knip/jscpd) | ne doit jamais augmenter | `.github/quality-baseline.json` |
| npm audit severity | high | `npm audit --audit-level=high` |
| Bandit severity | medium+ | `-ll` dans args bandit |

> Ces seuils sont ceux appliqués par la CI. Le tableau a déjà menti pendant
> plusieurs mois (il annonçait 30 % et un `jest.config.cjs` supprimé lors du
> passage à Vitest) — si vous changez un seuil, changez cette ligne dans la
> même PR.

---

## Tests E2E (Playwright) — et comment ils restent à jour

```bash
cd fast_api_voter && uvicorn api.main:app --port 4434   # Assemblée + 2 fiches du Lab en ont besoin
cd voter-app && npm run test:e2e                        # chromium + firefox, ~1,5 min
```

La suite a déjà pourri une fois : 5 specs figées sur une UI qui avait bougé
pendant deux mois, chaque test brûlant son timeout de 60 s jusqu'à ce que le job
soit tué à 25 min sans rapport. Trois garde-fous, dans l'ordre d'efficacité :

1. **Elle tourne sur chaque PR** (`e2e.yml`, déclenché par tout changement dans
   `voter-app/` ou `fast_api_voter/`). Une dérive se voit en une PR, pas en deux
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

---

## Code mort, duplication & conventions "vibe coding"

Une grande partie de ce repo est écrite avec l'aide de LLM (Claude Code &
autres). Ces outils rapportent leurs trouvailles sans jamais faire échouer
leur propre étape (voir [`CODE_AUDIT.md`](CODE_AUDIT.md) pour l'état des
lieux) :

| Outil | Détecte | Lancer en local |
|---|---|---|
| `vulture` | Code mort backend (fonctions, variables, imports jamais utilisés) | `cd fast_api_voter && python -m vulture api/ .vulture_whitelist.py --config pyproject.toml` |
| `radon`/`xenon` | Complexité cyclomatique backend (fonctions trop ramifiées) | `cd fast_api_voter && python -m radon cc api/ -e "api/tests/*" -n C -s` |
| `deptry` | Dépendances Python déclarées-mais-inutilisées / utilisées-mais-non-déclarées | `cd fast_api_voter && python -m deptry .` (config dans `pyproject.toml`'s `[tool.deptry]`) |
| `knip` | Fichiers/exports/dépendances inutilisés côté frontend | `cd voter-app && npm run knip` |
| `madge` | Imports circulaires côté frontend + visualisation du graphe | `cd voter-app && npm run madge:circular` (graphe image : `npx madge --image graph.svg --extensions ts,tsx src`, nécessite `graphviz`) |
| `jscpd` | Duplication de code cross-langage (Python + TS) | `npx jscpd --config .jscpd.json fast_api_voter/api voter-app/src` |

`dependency-cruiser` n'est **pas** dans ce tableau : contrairement aux outils
ci-dessus (dette non-bloquante suivie par le cliquet), c'est un vrai gate —
voir le tableau « Seuils qualité » plus haut et `voter-app/.dependency-
cruiser.json`. Équivalent frontend d'`import-linter` : `src/lib` (libs pures,
voir CLAUDE.md — section Playground) ne doit jamais importer depuis
`src/components` ou `src/pages`. Épinglé en `17.4.3` (pas la dernière
majeure) : `18.x` exige Node `^22||^24||>=26`, ce repo (CI et dev local) est
encore sur Node 20. `npm run depcruise` en local.

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
git rebase develop                            # ← indispensable, voir ci-dessous
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
requêtes valides pour chacune des 95 opérations et vérifie que la réponse
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
`mutation-testing.yml` (jamais bloquant) mesure la différence sur les deux
moitiés du moteur de vote :

```bash
cd fast_api_voter && python -m mutmut run   # backend  (Linux/WSL uniquement)
cd voter-app && npm run test:mutation       # frontend (Stryker)
```

Il se déclenche sur **push vers `develop` touchant un fichier moteur** — un score
de mutation ne peut bouger que si le code muté bouge.

> **Piège GitHub Actions à connaître.** `schedule` et `workflow_dispatch` sont
> résolus contre la **branche par défaut**, pas contre celle où vit le fichier.
> Ce workflow n'existait que sur `develop` : son cron « hebdomadaire » n'a donc
> **jamais tourné une seule fois**, et `gh workflow run` répondait 404. `push` et
> `pull_request`, eux, utilisent le fichier de la branche poussée. Un nouveau
> workflow qui ne serait déclenché que par `schedule`/`workflow_dispatch` sera
> inerte tant que `main` n'aura pas rattrapé `develop`.

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
`develop` touchant le moteur + `workflow_dispatch`, jamais bloquant sur PR
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

---

## Commandes utiles

```bash
pre-commit run --all-files                              # lancer tous les hooks
detect-secrets scan --update .secrets.baseline         # mettre a jour la baseline
cd voter-app && npm test -- --coverage                 # coverage frontend
cd fast_api_voter && python -m pytest tests --cov=app  # coverage backend
pip-audit --requirement fast_api_voter/requirements.txt # CVE Python
./scripts/check_openapi_drift.sh                        # contrat API à jour ?
```
