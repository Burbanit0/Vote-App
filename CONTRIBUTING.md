# Vote Lab — Qualité & contribution

## Setup local (une seule fois)

```bash
# 1. Backend
pip install -r flask_voter_app/requirements.txt
pip install -r flask_voter_app/requirements-dev.txt

# 2. Frontend
cd voter-app && npm install

# 3. Hooks pre-commit + pre-push (obligatoire)
pip install pre-commit
pre-commit install                        # hooks sur git commit
pre-commit install --hook-type pre-push   # hooks sur git push
```

## Ce qui se passe à chaque commit

| Vérification | Outil | Bloque ? |
|---|---|---|
| Espaces en fin de ligne, encodage | pre-commit-hooks | ✓ |
| Conflits de merge oubliés | pre-commit-hooks | ✓ |
| Secrets / credentials | detect-secrets | ✓ |
| Python SAST (injections, mauvaises pratiques) | bandit | ✓ |
| Python linting | flake8 | ✓ |
| TypeScript/React linting | eslint | ✓ |
| Vulnérabilités npm (high+) | npm audit | ✓ |

## Ce qui se passe à chaque push

| Vérification | Outil | Seuil |
|---|---|---|
| Tests frontend + coverage | jest | ≥ 30% lignes |
| Tests backend + coverage | pytest-cov | ≥ 30% lignes |

## Ce que la CI vérifie (sur chaque PR)

- Tout ce qui est ci-dessus
- Build Vite complet
- `pip-audit` (CVE Python)
- Bandit en mode rapport

## Augmenter les seuils de coverage

Modifier dans :
- `voter-app/jest.config.cjs` → `coverageThreshold.global`
- `.github/workflows/backend-ci-cd-pipeline.yml` → `--cov-fail-under=X`
- `.pre-commit-config.yaml` → `--cov-fail-under=X`

## Créer la baseline detect-secrets (si nouveaux fichiers)

```bash
detect-secrets scan --update .secrets.baseline
```

## Lancer tous les hooks manuellement

```bash
pre-commit run --all-files
```
