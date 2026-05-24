# Vote Lab — Checklist avant ouverture publique

> Audit initial : 2026-05-23 (branche `develop` à 6f9ae98).
> **Dernière mise à jour : 2026-05-23 après vagues 1-3 du sprint perf/refactor** (branche `develop` à 18 commits d'avance sur `origin/develop`).
> Coche au fur et à mesure. Les blocs `bash` sont prévus pour être copiés/collés depuis la racine du repo.

---

## 📊 État après vagues 1-3 du sprint perf/refactor

| # | Item | Statut |
|---|------|--------|
| 1 | LICENSE | 🔴 à faire |
| 2 | CI/CD désactivée | 🔴 à faire |
| 3 | 4 endpoints lourds sans rate limit | ✅ **réglé** (A2, commit 618556b) |
| 4 | 16 tests frontend en échec | 🔴 à faire |
| 5 | Test backend flake | 🟠 à faire |
| 6 | Lint frontend (14 670 issues) | 🟠 à faire |
| 7 | mypy backend (78 → **52** erreurs) | 🟠 partiellement amélioré (B3) |
| 8 | 6 vulnérabilités npm | 🟠 à faire |
| 9 | Bundle frontend monolithique | ✅ **réglé** (A1, commit a6497ad) |
| 10 | Élaguer 86 branches locales | 🟡 à faire |
| 11 | `.gitignore` artefacts | 🟡 à faire |
| 12 | Pytest warnings (1063 → 1217) | 🟡 à faire — **a empiré légèrement** (à creuser) |
| 13 | Découper `theory.py` | 🟡 à faire (`election.py` partiellement découpé en B3) |
| 14 | Aligner le README | 🟡 à faire |
| 15 | `git gc --aggressive` | 🟡 à faire |

**Bilan** : 2 bloquants réglés (#3 et #9), 1 partiellement (#7). 2 bloquants critiques restent (#1 LICENSE et #2 CI/CD). #4 frontend tests reste bloquant.

---

## 🔴 Bloquants — à régler AVANT de rendre public

### [ ] 1. Ajouter un fichier LICENSE
**Pourquoi** : sans licence, le projet est "all rights reserved" par défaut → personne ne peut légalement le forker, contribuer ou le redéployer.
**Décision à prendre** : MIT (permissif) ou Apache-2.0 (permissif + clause brevets explicite). MIT recommandé pour un projet de recherche civique.

```bash
# Génère une LICENSE MIT (remplacer "Burban Gaultier" et l'année si besoin)
curl -s https://api.github.com/licenses/mit \
  | python -c "import json,sys; print(json.load(sys.stdin)['body'])" \
  | sed "s/\[year\]/$(date +%Y)/; s/\[fullname\]/Burban Gaultier/" \
  > LICENSE

# Mettre à jour package.json
cd voter-app
npm pkg set license=MIT
cd ..
```

### [ ] 2. Régler la CI/CD (actuellement désactivée — billing GitHub Actions)
**Symptôme** : 8 dernières runs en `failure` avec "*The job was not started because recent account payments have failed*".
**Options** :
- (a) Régler le compte GitHub (Settings → Billing & plans)
- (b) Migrer vers un runner self-hosted
- (c) Désactiver temporairement les workflows pour ne pas afficher de croix rouge sur le README public

Option (c), désactivation temporaire propre :
```bash
mkdir -p .github/workflows-disabled
git mv .github/workflows/backend-ci-cd-pipeline.yml .github/workflows-disabled/
git mv .github/workflows/frontend-ci-cd-pipeline.yml .github/workflows-disabled/
git mv .github/workflows/e2e.yml .github/workflows-disabled/
git mv .github/workflows/release.yml .github/workflows-disabled/
git mv .github/workflows/merge-to-main.yml .github/workflows-disabled/
git mv .github/workflows/branch-policy.yml .github/workflows-disabled/
git commit -m "ci: temporarily move workflows out of .github/workflows (billing)"
```

### [x] ~~3. Rate-limiter 4 endpoints lourds orphelins dans `election.py`~~ ✅ FAIT
**Réglé en A2** (commit `618556b` `feat/perf-a2-heavy-endpoint`).

- `POST /api/election/combined-effects` — désormais `@sim_limiter.limit("5 per minute")` + `@heavy_endpoint`
- `POST /api/election/campaign-sensitivity` — `@sim_limiter.limit("10 per minute")` + `@heavy_endpoint`
- `POST /api/election/simulate-pipeline` — `@sim_limiter.limit("10 per minute")` + `@heavy_endpoint`
- `POST /api/election/interpret` — `@sim_limiter.limit("30 per minute")` (text-only, pas de tpool)

Vérif :
```bash
grep -nA2 "^@election_bp.route.*\(campaign-sensitivity\|combined-effects\|simulate-pipeline\|interpret\)" \
  flask_voter_app/app/routes/election/__init__.py | grep -A1 sim_limiter | head -20
```

### [ ] 4. Réparer les 16 tests frontend qui échouent (8 suites)
**Cause commune** : `TS1343: 'import.meta' meta-property...` dans `useSimulationWorker.ts` → suites qui ne mockent pas le hook. Voir CLAUDE.md.

Suites à corriger :
```
src/App.test.tsx
src/pages/__tests__/ElectionLabPage.test.tsx
src/pages/__tests__/TechDemocracyPage.test.tsx
src/components/Simulation/__tests__/IdeologyHeatmap.test.tsx
src/components/Simulation/__tests__/IdeologyMapChart.test.tsx
src/components/Simulation/__tests__/MethodSimilarityGraph.test.tsx
src/components/Simulation/__tests__/MonteCarloResults.test.tsx
src/components/shared/__tests__/PolarizationPanel.test.tsx
```

Pattern à appliquer en tête de chaque suite concernée :
```ts
jest.mock('../../../hooks/useSimulationWorker', () => ({
  useSimulationWorker: () => ({ dispatch: jest.fn().mockResolvedValue({}) }),
}));
```

Vérif finale :
```bash
cd voter-app && npm test 2>&1 | tail -5
```

---

## 🟠 Avertissements importants — à corriger rapidement après ouverture

### [ ] 5. Test backend `test_compare_with_blank_rule` flake
Passe en isolation, échoue dans la suite complète (HTTP 500). Fuite d'état entre tests. **Toujours présent** après les vagues 1-3 (vu sur les 4 runs full-suite — toujours le même unique test qui flake).
```bash
cd flask_voter_app
FLASK_ENV=testing python -m pytest tests/test_api_public.py::test_compare_with_blank_rule -v
# Si OK en isolation, lancer juste avant pour repérer la pollution :
FLASK_ENV=testing python -m pytest tests/test_api_public.py -v
```

### [ ] 6. Lint frontend (14 670 issues, dont 14 266 auto-fixables)
```bash
cd voter-app
npx eslint . --ext .ts,.tsx --fix
# Inspecter les ~400 vraies erreurs restantes (no-unused-vars, no-undef, exhaustive-deps)
npm run lint 2>&1 | grep -v prettier | grep error
```

### [⚠] 7. mypy backend — partiellement amélioré (78 → **52** erreurs)
**Amélioration en B3** (commit `3f68af1`) : le nettoyage d'imports inutilisés dans `election.py` lors de la conversion en package a réduit le compte de 78 à 52.

Distribution actuelle : `election/__init__.py` 49, `tech.py` 3 (theory.py n'a pas été touché — 28 attendus).
Majorité = annotations génériques manquantes (`set` → `set[str]`, `Counter` → `Counter[str]`, `tuple` → `tuple[int, int]`).
2 vrais bugs dans `theory.py` lignes ~2695, 2715, 2719 (return types incohérents) — toujours là.

```bash
cd flask_voter_app
python -m mypy app/routes/election/ --ignore-missing-imports 2>&1 | head -20
python -m mypy app/routes/theory.py --ignore-missing-imports 2>&1 | grep -v "type-arg"
```

### [ ] 8. 6 vulnérabilités npm modérées (`ws`, cascade socket.io)
```bash
cd voter-app
npm audit fix       # PAS --force, l'update est mineure
npm audit           # confirmer 0 vulnérabilités
```

### [x] ~~9. Bundle frontend monolithique (2.37 MB en un seul chunk)~~ ✅ FAIT
**Réglé en A1** (commit `a6497ad` `feat/perf-a1-lazy-routes`).

19 pages désormais lazy via `React.lazy()`, plus `manualChunks` Vite pour recharts/d3/jspdf/bootstrap. Bundle initial HomePage : **2 365 KB → 598 KB** (~250 KB gzip, ÷2.5). Le vendor `pdf` (jspdf+html2canvas, 600 KB) ne se charge que lors d'un export ; `recharts` (413 KB) que sur une page graphique.

Vérif :
```bash
cd voter-app && npm run build 2>&1 | grep -E "build/assets.*\.js" | sort -k4 -h
```

---

## 🟡 Nettoyage cosmétique — à faire quand tu veux

### [ ] 10. Élaguer les 86 branches locales
Note : depuis les vagues 1-3, **6 nouvelles branches** `feat/perf-*` ont été créées et mergées. Toutes éligibles au nettoyage.

```bash
# Liste les branches mergées dans develop
git branch --merged develop | grep -vE "develop|main|\*"

# Les supprimer toutes (vérifier la liste d'abord !)
git branch --merged develop | grep -vE "develop|main|\*" | xargs -r git branch -d

# Côté remote (faire le tri sur GitHub manuellement, ou :)
# git push origin --delete <branch-name>
```

### [ ] 11. `.gitignore` les artefacts qui n'ont rien à faire en git
```bash
cat >> .gitignore <<'EOF'

# Coverage artifacts
htmlcov/
.coverage
*.cover

# Build documentation PDF (regénérables)
*.pdf
EOF

# Retirer du tracking (les fichiers restent localement)
git rm --cached -r htmlcov/ 2>/dev/null || true
git rm --cached .coverage 2>/dev/null || true
git rm --cached THEORY.pdf GUIDE_UTILISATEUR.pdf 2>/dev/null || true

git commit -m "chore: gitignore coverage and PDF artifacts"
```

### [ ] 12. Pytest warnings (1063 → **1217**)
**Augmentation légère** entre l'audit initial (1063) et le dernier run (1217). À creuser — probablement les nouveaux tests cache/service qui exercent du code SQLAlchemy/eventlet jusque-là peu couvert.

```bash
cd flask_voter_app
FLASK_ENV=testing python -m pytest tests/ -q --tb=no 2>&1 \
  | grep -E "Warning" | sort | uniq -c | sort -rn | head -20
```

### [ ] 13. Découper `theory.py` (2 887 lignes, 28 erreurs mypy, 6% coverage)
**Note** : la chiffre initial de "1384 lignes" était fausse — `wc -l` donne 2 887. Toujours candidat n°1 au refactor.

`election.py` (7 080 lignes) a été partiellement traité en B3 : converti en package `election/` avec `_helpers.py` extrait. Découper la suite de ses 35 routes dans des sous-modules thématiques reste à faire — voir CODE_AUDIT_CHECKLIST item B3.

Pour `theory.py` : éclater en sous-blueprints (`theory_paradox.py`, `theory_aggregation.py`, etc.).

### [ ] 14. Aligner le README avec la réalité
Le README "Quick Start" promet un démarrage Docker en 2 commandes. Avec CI HS et tests en échec, l'expérience d'arrivée ne correspond pas. Une fois les bloquants 1-4 réglés, vérifier qu'un `git clone && cd Vote-App && cp .env.example .env && docker-compose up` marche réellement.

### [ ] 15. Optionnel : `git gc --aggressive` (repo à 930 MB)
Pas tant le code en lui-même que `.git` + venvs + node_modules. Vérifier :
```bash
du -sh .git node_modules voter-app/node_modules flask_voter_app/venv 2>/dev/null
git gc --aggressive --prune=now
```

---

## 🟢 Ce qui va déjà bien (à NE PAS toucher)

| Aspect | Constat initial | Constat actuel |
|---|---|---|
| Coverage backend | 93.70 % | **93.73 %** (+0.03 grâce aux nouveaux tests cache + service) |
| `create_app()` | Refuse les `SECRET_KEY` par défaut en prod | inchangé ✓ |
| CORS | Origines explicites, pas de wildcard | inchangé ✓ |
| Auth | JWT + bcrypt + rate limit login | inchangé ✓ |
| Pre-commit | detect-secrets, bandit, mypy, flake8, eslint, npm audit | inchangé ✓ |
| Code dangereux | 0 `eval`/`exec`/`pickle.loads`/`subprocess` backend | inchangé ✓ |
| Historique secrets | `git log --all` propre, jamais de `.env` commité | inchangé ✓ |
| Deps Python | Pins explicites contre CVE Dependabot | inchangé ✓ |
| Documentation | README + CLAUDE + CONTRIBUTING + GUIDE + THEORY + AGENTS | **+ CODE_AUDIT_CHECKLIST.md + shared/README.md + votingMethods/index.ts** |
| Tests frontend | (non comptés à l'audit initial) | **+ 60 nouveaux tests verts** (theme, hooks, lab, useApi, useScenarioPersistence) |

---

## Ordre d'exécution recommandé (mis à jour)

**Sprint « pre-public » restant** : **1 → 2 → 4**, puis 8.
(items 3 et 9 désormais réglés ✅)

**Sprint « post-public J+7 »** : 5, 6, 7 (52 erreurs restantes).

**Plus tard** : 10, 11, 12, 13, 14, 15.

Une fois tout coché, supprimer ce fichier ou le déplacer dans `docs/audit/`.

---

## Annexe — commits d'avance sur `origin/develop`

Vague 1 (perf) :
- `a6497ad` perf(frontend): A1 — lazy routes + manual chunks → résout #9
- `618556b` perf(backend): A2 — heavy_endpoint decorator → résout #3
- `3d52997` feat(theme): A3 — design tokens + PageContainer
- `bf73c23` perf(backend): B1 — Redis result cache

Vague 2 (architecture) :
- `947dcf7` feat(hooks): B2 — useApi / useApiAction hooks
- `3f68af1` refactor(backend): B3 — election.py en package → −26 erreurs mypy
- `ca37dcd` refactor(backend): C1 — extract ElectionService

Vague 3 (organisation) :
- `8c23d2d` refactor(frontend): C3 — sub-folders in components/shared/
- `5cd3103` refactor(frontend): C5 — useScenarioPersistence
- `fd6aa8e` refactor(frontend): C2 — split VotingMethodVisualizations (3/12)

À pousser via `git push origin develop` quand prêt.
