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
- Tests frontend + coverage >= 30%
- Tests backend + coverage >= 30%

### 3. Ouvrir une PR vers develop

```bash
git push origin feature/ma-feature
# Ouvrir la PR : feature/ma-feature -> develop
```

**La CI vérifie automatiquement :**

| Vérification | Bloque la PR si... |
|---|---|
| Branch Policy | Branche source sans préfixe valide |
| Frontend CI | Tests échouent ou coverage < 30% |
| Backend CI | Tests échouent ou coverage < 30% |
| npm audit | CVE haute détectée |
| OpenAPI Contract | `openapi.gen.json` / `types.gen.ts` désynchronisés du code (route/schéma modifié sans régénération — voir `scripts/check_openapi_drift.sh`) |

### 4. Release : develop → main

Uniquement via le workflow **Release Vote Lab** :
- GitHub → Actions → "Release Vote Lab" → Run workflow
- Choisir `patch`, `minor` ou `major`

Le workflow exige `ci-frontend`, `ci-backend` **et `e2e` (Playwright)** verts
avant de taguer/pousser sur `main` — c'est le seul endroit où la suite E2E
tourne automatiquement (trop lente pour chaque PR `develop`, mais une release
est justement le moment peu fréquent où elle a sa place).

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

---

## Ce qui se passe automatiquement

| Quand | Vérification | Bloque |
|---|---|---|
| `git commit` | detect-secrets, bandit, flake8, eslint, npm audit | Oui |
| `git push` | Tests + coverage (front + back) | Oui |
| PR ouverte | Branch Policy, CI complète, build | Oui |

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
| Coverage frontend (lines) | 30% | `voter-app/jest.config.cjs` |
| Coverage backend | 30% | `backend-ci-cd-pipeline.yml` |
| npm audit severity | high | `npm audit --audit-level=high` |
| Bandit severity | medium+ | `-ll` dans args bandit |

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
