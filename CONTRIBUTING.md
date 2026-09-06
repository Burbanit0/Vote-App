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
| Backend CI | Tests échouent, coverage < 90 %, mypy ou flake8 en erreur |
| npm audit | CVE haute détectée |
| E2E (Playwright) | Un parcours utilisateur casse sur Chromium ou Firefox — **ou passe seulement au second essai** (voir « Tests E2E » plus bas) |
| Generated Artifacts Contract | `openapi.gen.json` / `types.gen.ts` **ou** `engineParity.json` désynchronisés du code (voir `scripts/check_openapi_drift.sh` et `scripts/check_engine_parity_drift.sh`) |
| Quality ratchet | La dette vulture/radon/knip/jscpd a augmenté (voir « Code mort » plus bas) |
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

**Merge queue** : à activer manuellement (Settings → Branches → règle
`develop` → "Require merge queue") — l'API classique de branch protection
utilisée par le script ci-dessus n'expose pas ce réglage. Une fois activé,
chaque PR en file est retestée contre l'état à jour de `develop` avant de
vraiment merger (évite la classe de problème "verte mais `mergeable_state:
behind`", vécue en direct sur la PR #188). `audit.yml` déclare déjà le
trigger `merge_group:` nécessaire ; `branch-policy.yml` en est
délibérément exclu (voir sa carte plus bas). Pendant la configuration,
vérifiez dans l'écran du merge queue que seuls les checks qui déclarent
`merge_group:` sont listés comme requis pour la file — un check requis qui
ne le déclare pas peut bloquer la file indéfiniment (même risque que celui
déjà documenté pour les checks scopés par `paths:`).

---

## Ce qui se passe automatiquement

| Quand | Vérification | Bloque |
|---|---|---|
| `git commit` | detect-secrets, bandit, flake8, eslint, npm audit | Oui |
| `git push` | Tests + coverage (front + back) | Oui |
| PR ouverte | Branch Policy, CI complète, build | Oui |

---

## Carte des 10 workflows CI

10 fichiers dans `.github/workflows/` — sans une table à jour ici, la seule
source de vérité redevient "lire les 10 YAML". Si vous changez un déclencheur
ou un gate, mettez cette table à jour dans la même PR.

| Workflow | Déclencheur | Gate quand il tourne ? | Check requis (branch protection `develop`) ? | Durée typique |
|---|---|---|---|---|
| `backend-ci-cd-pipeline.yml` (Backend CI) | push/PR sur `develop`/`main`, toujours (le filtre `paths` vit maintenant dans un job `changes` interne, pas au niveau du déclencheur) | Oui, quand `fast_api_voter/**` a changé — sinon le job `test` est `skipped` | Oui | ~12-14 min (skip quasi instantané sinon) |
| `frontend-ci-cd-pipeline.yml` (Frontend CI) | push/PR sur `develop`/`main`, toujours (même schéma `changes`) | Oui, quand `voter-app/**` a changé — sinon `skipped` | Oui | ~2-3 min (skip quasi instantané sinon) |
| `e2e.yml` (E2E Tests) | push/PR + `workflow_dispatch` + `workflow_call` (depuis `release.yml`), toujours (même schéma `changes` ; dispatch/call ignorent le filtre) | Oui, quand `voter-app/**`/`fast_api_voter/**` a changé, ou toujours pour dispatch/call — sinon `skipped` | Oui | ~5-7 min (peut aller jusqu'au timeout de 25 min si une régression casse plusieurs specs en cascade) |
| `branch-policy.yml` (Branch Policy) | PR | Oui, y compris le format du titre (Conventional Commits — plus un simple avertissement) et la source pour les PR vers `main` (`Check source is develop`) | Oui | ~10-30 s |
| `openapi-contract.yml` (Generated Artifacts Contract) | push/PR, toujours (même schéma `changes`) | Oui, quand un fichier du contrat a changé — sinon `skipped` | Oui | ~1 min (skip quasi instantané sinon) |
| `dependency-review.yml` (Dependency Review) | PR sur `develop`/`main` | Oui — sévérité `high`+ introduite par la PR | Oui | ~15-30 s |
| `audit.yml` (Security Audit) | push/PR + cron lundi 06:00 UTC + `merge_group` | Semgrep/Trivy/Secret Scan : oui · CodeQL : le job doit terminer mais ne bloque pas sur ses trouvailles (elles atterrissent dans l'onglet Security) · code mort/duplication/complexité (vulture/radon/knip/jscpd) : non-bloquant sauf régression du cliquet (`quality-baseline.json`) · scan d'image Docker + SBOM (`image-scan`) : non-bloquant, et ne tourne que sur push `develop`/cron — jamais sur une PR (build de 2 images, coûte plusieurs minutes) | Oui (les 4 jobs gating + les 2 jobs CodeQL du matrix — `image-scan` n'est pas requis) | ~2-3 min sur PR (le run cron/push `develop`, qui inclut `image-scan`, est plus long et indépendant d'une PR) |
| `mutation-testing.yml` (Mutation Testing) | push sur `develop` (paths engine uniquement) + `workflow_dispatch` + cron lundi 04:17 UTC | Non — jamais bloquant | Non — ne se déclenche jamais sur PR | mutmut ~40 min-3h · Stryker jusqu'à ~2h30 en cold-cache (`timeout-minutes: 240`), moins avec le cache `--incremental` une fois chaud |
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

`schedule`/`workflow_dispatch` (utilisés par `mutation-testing.yml` et
`audit.yml`) sont résolus par GitHub contre la **branche par défaut du
dépôt**, pas contre une branche en particulier — un workflow qui n'existe que
sur une branche non-défaut ne se déclenche jamais sur ces deux triggers, même
s'il est mergé et présent dans le fichier.

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
| Coverage frontend | lines 85 % · statements 80 % · functions 75 % · branches 70 % | `voter-app/vitest.config.ts` (`test.coverage.thresholds`) |
| Coverage backend | 85 % | `fast_api_voter/pyproject.toml` (`--cov-fail-under`) |
| eslint | 0 **erreur** (les warnings passent) | `voter-app/eslint.config.js` |
| flake8 | 0 sur `E9,F` (erreurs de syntaxe et de nom) | `backend-ci-cd-pipeline.yml` |
| mypy | strict, 0 erreur sur `api/` | `fast_api_voter/mypy.ini` |
| Tests e2e instables | 0 — un test qui ne passe qu'au *retry* fait échouer la PR | `voter-app/scripts/check-flaky.mjs` |
| Dette qualité (vulture/radon/knip/jscpd) | ne doit jamais augmenter | `.github/quality-baseline.json` |
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
| `knip` | Fichiers/exports/dépendances inutilisés côté frontend | `cd voter-app && npm run knip` |
| `jscpd` | Duplication de code cross-langage (Python + TS) | `npx jscpd --config .jscpd.json fast_api_voter/api voter-app/src` |

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
`voter-app/knip.json`, `.jscpd.json`), pas en remontant la baseline. Un script
lancé par la CI mais importé par personne — `voter-app/scripts/check-flaky.mjs`
en est un — est un faux positif knip : il s'ajoute à `ignore`.

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
  radon / knip / jscpd du résumé.

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
