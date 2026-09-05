# 📌 Plan d'Amélioration de la CI/CD - Vote-App

---

## **🎯 Objectif Global**
Passer d’une CI/CD **solide mais perfectible** (⭐⭐⭐⭐) à une **CI/CD de classe mondiale** (⭐⭐⭐⭐⭐), avec :
- ✅ **Fiabilité accrue** (zéro régression critique en production).
- ✅ **Performances optimisées** (temps d’exécution divisé par 2).
- ✅ **Sécurité renforcée** (zéro vulnérabilité critique non bloquée).
- ✅ **Qualité du code améliorée** (seuils de mutation et couverture à 90%+).
- ✅ **Maintenabilité et visibilité** (documentation complète, tableau de bord centralisé).

---

## **📅 Roadmap Globale**

| **Phase** | **Durée** | **Objectifs** | **Priorité** | **Responsable** |
|-----------|----------|--------------|--------------|-----------------|
| **Phase 0 : Audit et Préparation** | 1 semaine | Analyser l’existant, documenter, prioriser. | ⭐⭐⭐⭐⭐ | Matthieu Burban |
| **Phase 1 : Corrections Critiques** | 2 semaines | Résoudre les problèmes bloquants (E2E, sécurité, mutation testing). | ⭐⭐⭐⭐⭐ | Matthieu Burban + Équipe Dev |
| **Phase 2 : Optimisation des Performances** | 3 semaines | Réduire les temps d’exécution et les coûts. | ⭐⭐⭐⭐ | Équipe DevOps |
| **Phase 3 : Qualité et Sécurité** | 4 semaines | Améliorer la qualité du code et la sécurité. | ⭐⭐⭐⭐ | Équipe Dev + Sécurité |
| **Phase 4 : Automatisation Avancée** | 4 semaines | Automatiser le déploiement et les releases. | ⭐⭐⭐ | Équipe DevOps |
| **Phase 5 : Monitoring et Maintenance** | Continu | Suivre, améliorer, documenter. | ⭐⭐ | Équipe DevOps |

---

---

## **📝 Phase 0 : Audit et Préparation (1 semaine)**
**Objectif** : Comprendre l’existant, documenter, et prioriser les actions.

### **📌 Tâches**

| **ID** | **Tâche** | **Description** | **Livrable** | **Responsable** | **Échéance** | **Statut** |
|--------|-----------|----------------|--------------|-----------------|--------------|------------|
| **P0-1** | Audit complet de la CI/CD | Lister tous les workflows, leurs déclencheurs, leurs dépendances, et leurs temps d’exécution. | Document `CI_CD_AUDIT.md` | Matthieu Burban | J+1 | ⬜ |
| **P0-2** | Cartographie des problèmes | Identifier et classer tous les problèmes (fiabilité, performance, sécurité, qualité). | Tableau des problèmes (Notion/Excel) | Matthieu Burban | J+2 | ⬜ |
| **P0-3** | Priorisation des actions | Classer les actions par **impact** et **complexité** (matrice Eisenhower). | Roadmap priorisée | Matthieu Burban | J+3 | ⬜ |
| **P0-4** | Documentation de l’existant | Documenter chaque workflow, son rôle, ses seuils, et ses dépendances. | Fichier `CI_CD.md` dans `.github/` | Matthieu Burban | J+5 | ⬜ |
| **P0-5** | Configuration de l’environnement | Vérifier que tous les outils (GitHub Actions, Dependabot, etc.) sont correctement configurés. | Rapport de configuration | Équipe DevOps | J+7 | ⬜ |

---

### **📊 Livrables**

#### **1. `CI_CD_AUDIT.md`**
Document détaillant :
- Liste des workflows avec leurs déclencheurs, temps d’exécution, dépendances, et outils utilisés.
- Exemple de structure :
  ```markdown
  ## Audit CI/CD - Vote-App

  ### Workflows
  | Nom | Déclencheur | Temps moyen | Dépendances | Outils |
  |-----|-------------|-------------|-------------|-------|
  | `backend-ci-cd-pipeline.yml` | Push/PR (backend) | 8-14 min | Aucun | Flake8, Bandit, pytest, mypy |
  | `e2e.yml` | Push/PR | 1-20 min | Backend + Frontend | Playwright |
  | `mutation-testing.yml` | Push (develop) | 40-120 min | Aucun | mutmut, Stryker |
  ```

#### **2. Tableau des problèmes**

| **Problème** | **Type** | **Impact** | **Complexité** | **Priorité** | **Solution proposée** |
|-------------|----------|------------|----------------|--------------|-----------------------|
| Tests E2E non bloquants | Fiabilité | ⭐⭐⭐⭐⭐ | Faible | ⭐⭐⭐⭐⭐ | Ajouter comme `required check` |
| `pip-audit` non bloquant | Sécurité | ⭐⭐⭐⭐⭐ | Faible | ⭐⭐⭐⭐⭐ | Supprimer `continue-on-error` |
| Mutation testing jamais exécuté sur PR | Qualité | ⭐⭐⭐⭐ | Moyenne | ⭐⭐⭐⭐ | Déclencher sur PR (sous-ensemble) |

#### **3. Roadmap priorisée**
Utiliser une **matrice Eisenhower** pour classer les actions :
- **Urgent et Important** (Phase 1) : Corrections critiques.
- **Important mais non urgent** (Phase 2-3) : Optimisations et améliorations.
- **Urgent mais non important** (Phase 4) : Automatisation avancée.
- **Ni urgent ni important** (Phase 5) : Maintenance continue.

#### **4. `CI_CD.md`**
Documentation complète de la CI/CD, incluant :
- Architecture globale.
- Rôle de chaque workflow.
- Comment ajouter un nouveau test ou outil.
- Comment déclencher manuellement un workflow.
- Qui contacter en cas de problème.

---

### **✅ Critères de succès**
- [ ] Tous les workflows sont documentés.
- [ ] Tous les problèmes sont identifiés et priorisés.
- [ ] L’équipe comprend la CI/CD actuelle et ses limites.

---

---

## **🚀 Phase 1 : Corrections Critiques (2 semaines)**
**Objectif** : Résoudre les problèmes **bloquants** qui impactent la fiabilité, la sécurité et la qualité.

---

### **📌 Tâches**

| **ID** | **Tâche** | **Description** | **Livrable** | **Responsable** | **Échéance** | **Statut** |
|--------|-----------|----------------|--------------|-----------------|--------------|------------|
| **P1-1** | Rendre les tests E2E bloquants | Ajouter `e2e` comme `required check` dans la protection de branche. | Mise à jour de `branch-policy.yml` | Équipe DevOps | J+2 | ⬜ |
| **P1-2** | Rendre `pip-audit` bloquant | Supprimer `continue-on-error: true` dans `backend-ci-cd-pipeline.yml`. | Mise à jour du workflow | Équipe Dev | J+2 | ⬜ |
| **P1-3** | Rendre Trivy bloquant pour les dépendances | Modifier `audit.yml` pour échouer sur toutes les vulnérabilités. | Mise à jour du workflow | Équipe Sécurité | J+3 | ⬜ |
| **P1-4** | Corriger `mutation-testing.yml` | Changer la branche de déclenchement de `main` à `develop`. | Mise à jour du workflow | Matthieu Burban | J+1 | ⬜ |
| **P1-5** | Mettre à jour Node.js pour Stryker | Passer à Node 22 dans `mutation-testing.yml`. | Mise à jour du workflow | Équipe Dev | J+2 | ⬜ |
| **P1-6** | Ajouter des retries automatiques | Configurer `retry` pour les jobs flaky (E2E, mutation testing). | Mise à jour des workflows | Équipe DevOps | J+3 | ⬜ |
| **P1-7** | Vérifier les dépendances de Stryker | S’assurer que `@stryker-mutator/core@10.0.0` est compatible avec le projet. | Rapport de compatibilité | Équipe Dev | J+4 | ⬜ |
| **P1-8** | Tester les corrections | Exécuter tous les workflows pour valider les changements. | Rapport de test | Équipe QA | J+5 | ⬜ |

---

### **📝 Détails des tâches**

#### **P1-1 : Rendre les tests E2E bloquants**
**Objectif** : Empêcher les merges si les tests E2E échouent.
**Actions** :
1. Modifier `.github/workflows/branch-policy.yml` pour ajouter une vérification que `e2e.yml` a réussi.
   ```yaml
   - name: Check E2E passed
     if: github.base_ref == 'develop' || github.base_ref == 'main'
     run: |
       STATUS=$(curl -s -H "Authorization: token ${{ secrets.GITHUB_TOKEN }}" \
         "https://api.github.com/repos/${{ github.repository }}/actions/runs?workflow_id=e2e.yml&head_sha=${{ github.sha }}" | \
         jq -r '.workflow_runs[0].conclusion')
       if [ "$STATUS" != "success" ]; then
         echo "❌ Les tests E2E ont échoué ou ne sont pas terminés."
         exit 1
       fi
   ```
2. **Alternative** : Utiliser une action comme [`required-workflow`](https://github.com/marketplace/actions/required-workflow).

**Validation** :
- Ouvrir une PR avec un changement qui casse les tests E2E → **le merge doit être bloqué**.

---

#### **P1-2 : Rendre `pip-audit` bloquant**
**Objectif** : Bloquer les merges si des vulnérabilités critiques sont détectées dans les dépendances Python.
**Actions** :
1. Modifier `backend-ci-cd-pipeline.yml` pour supprimer `continue-on-error: true` :
   ```yaml
   - name: pip-audit (dependency CVEs)
     run: pip-audit --requirement fast_api_voter/requirements.txt
   ```

**Validation** :
- Ajouter une dépendance vulnérable (ex: `starlette==0.49.3`) et vérifier que le workflow échoue.

---

#### **P1-3 : Rendre Trivy bloquant pour les dépendances**
**Objectif** : Bloquer les merges si des vulnérabilités **HIGH/CRITICAL** sont détectées.
**Actions** :
1. Modifier `audit.yml` pour que le job `trivy` échoue sur **toutes les vulnérabilités** :
   ```yaml
   - name: Trivy (gating)
     if: always()
     uses: aquasecurity/trivy-action@master
     with:
       scan-type: fs
       scanners: vuln,secret,misconfig
       severity: UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL
       format: table
       exit-code: "1"
       skip-dirs: voter-app/node_modules,.claude,graphify-out
       trivyignores: .trivyignore.yaml
   ```

**Validation** :
- Ajouter une dépendance vulnérable (ex: `requests==2.25.0`) et vérifier que le workflow échoue.

---

#### **P1-4 : Corriger `mutation-testing.yml`**
**Objectif** : S’assurer que le workflow s’exécute sur `develop` (et non `main`).
**Actions** :
1. Modifier le déclencheur `schedule` et `push` pour cibler `develop` :
   ```yaml
   on:
     push:
       branches: [develop]
       paths: [...]
     schedule:
       - cron: '17 4 * * 1'
   ```

**Validation** :
- Pousser un changement sur `develop` → le workflow doit s’exécuter.

---

#### **P1-5 : Mettre à jour Node.js pour Stryker**
**Objectif** : Passer à Node 22 pour Stryker (requis par `@stryker-mutator/core@10.0.0`).
**Actions** :
1. Modifier `mutation-testing.yml` pour utiliser Node 22 :
   ```yaml
   - uses: actions/setup-node@v7
     with:
       node-version: '22'
       cache: 'npm'
       cache-dependency-path: voter-app/package-lock.json
   ```

**Validation** :
- Exécuter le job `stryker` → doit réussir sans erreur de version.

---

#### **P1-6 : Ajouter des retries automatiques**
**Objectif** : Éviter les échecs dus à des tests flaky (E2E, mutation testing).
**Actions** :
1. Ajouter `retry` dans les workflows `e2e.yml` et `mutation-testing.yml` :
   ```yaml
   jobs:
     e2e:
       name: Playwright E2E
       retry:
         max_attempts: 2
         on: [failure]
   ```

**Validation** :
- Simuler un échec flaky → le workflow doit réessayer.

---

#### **P1-7 : Vérifier les dépendances de Stryker**
**Objectif** : S’assurer que Stryker est compatible avec le projet.
**Actions** :
1. Vérifier la version de `@stryker-mutator/core` dans `voter-app/package.json`. 
2. Tester localement avec Node 22 :
   ```bash
   npx stryker run --dry-run
   ```

**Validation** :
- Stryker doit s’exécuter sans erreur avec Node 22.

---

#### **P1-8 : Tester les corrections**
**Objectif** : Valider que toutes les corrections fonctionnent.
**Actions** :
1. Exécuter tous les workflows modifiés sur une branche de test.
2. Vérifier que :
   - Les tests E2E bloquent bien les merges en cas d’échec.
   - `pip-audit` et Trivy bloquent bien les merges en cas de vulnérabilités.
   - `mutation-testing.yml` s’exécute sur `develop`.
   - Stryker fonctionne avec Node 22.

**Validation** :
- Tous les workflows doivent passer ou échouer comme attendu.

---

### **✅ Critères de succès**
- [ ] Les tests E2E sont **bloquants** pour les merges.
- [ ] `pip-audit` et Trivy **bloquent les merges** en cas de vulnérabilités.
- [ ] `mutation-testing.yml` s’exécute sur `develop`.
- [ ] Stryker fonctionne avec **Node 22**.
- [ ] Les jobs flaky (E2E, mutation testing) ont des **retries automatiques**.

---

---

## **⚡ Phase 2 : Optimisation des Performances (3 semaines)**
**Objectif** : Réduire les **temps d’exécution** et les **coûts GitHub Actions**.

---

### **📌 Tâches**

| **ID** | **Tâche** | **Description** | **Livrable** | **Responsable** | **Échéance** | **Statut** |
|--------|-----------|----------------|--------------|-----------------|--------------|------------|
| **P2-1** | Paralléliser les jobs CI | Exécuter Backend CI et Frontend CI en parallèle. | Workflow unifié `pr-ci-cd.yml` | Équipe DevOps | J+2 | ⬜ |
| **P2-2** | Mettre en cache les builds frontend | Cache du dossier `dist/` pour éviter de rebuild à chaque exécution. | Mise à jour de `frontend-ci-cd-pipeline.yml` | Équipe Dev | J+3 | ⬜ |
| **P2-3** | Désactiver les scans redondants | Supprimer Bandit et pip-audit de `backend-ci-cd-pipeline.yml`. | Mise à jour du workflow | Équipe Dev | J+4 | ⬜ |
| **P2-4** | Optimiser les tests E2E | Paralléliser les tests Playwright et réduire leur portée en PR. | Mise à jour de `e2e.yml` | Équipe Dev | J+5 | ⬜ |
| **P2-5** | Utiliser des runners plus puissants | Passer à des runners avec 8 vCPUs pour les jobs longs. | Mise à jour des workflows | Équipe DevOps | J+6 | ⬜ |
| **P2-6** | Mesurer les temps d’exécution | Ajouter des métriques de temps dans chaque workflow. | Script de logging | Équipe DevOps | J+7 | ⬜ |
| **P2-7** | Optimiser les dépendances | Réduire la taille de `node_modules` et des dépendances Python. | Rapport d’optimisation | Équipe Dev | J+8 | ⬜ |

---

### **📝 Détails des tâches**

#### **P2-1 : Paralléliser les jobs CI**
**Objectif** : Réduire le temps total d’exécution en exécutant Backend CI et Frontend CI en parallèle.
**Actions** :
1. Créer un nouveau workflow `pr-ci-cd.yml` qui :
   - Déclenche Backend CI et Frontend CI en parallèle.
   - Attend que les deux soient terminés avant de lancer les tests E2E.
2. **Exemple** :
   ```yaml
   name: PR CI/CD Pipeline

   on:
     pull_request:
       branches: [develop, main]

   jobs:
     backend:
       uses: ./.github/workflows/backend-ci-cd-pipeline.yml
     frontend:
       uses: ./.github/workflows/frontend-ci-cd-pipeline.yml
     e2e:
       needs: [backend, frontend]
       uses: ./.github/workflows/e2e.yml
   ```

**Validation** :
- Temps d’exécution total réduit de **~30%** (ex: de 20 min à 14 min).

---

#### **P2-2 : Mettre en cache les builds frontend**
**Objectif** : Éviter de rebuild le frontend à chaque exécution.
**Actions** :
1. Ajouter un cache pour le dossier `dist/` dans `frontend-ci-cd-pipeline.yml` :
   ```yaml
   - name: Cache frontend build
     uses: actions/cache@v3
     with:
       path: voter-app/dist
       key: ${{ runner.os }}-build-${{ hashFiles('voter-app/src/**', 'voter-app/package.json') }}
   ```

**Validation** :
- Le build est **skipé** si le cache est valide.

---

#### **P2-3 : Désactiver les scans redondants**
**Objectif** : Éviter les doublons entre `backend-ci-cd-pipeline.yml` et `audit.yml`.
**Actions** :
1. Supprimer les jobs `Bandit` et `pip-audit` de `backend-ci-cd-pipeline.yml`.
2. Supprimer le job `npm audit` de `frontend-ci-cd-pipeline.yml`.

**Validation** :
- Les workflows `backend-ci-cd-pipeline.yml` et `frontend-ci-cd-pipeline.yml` s’exécutent **plus rapidement**.

---

#### **P2-4 : Optimiser les tests E2E**
**Objectif** : Réduire le temps d’exécution des tests E2E.
**Actions** :
1. **Paralléliser les tests Playwright** :
   ```yaml
   - name: Run E2E tests
     run: npx playwright test --workers=4
     working-directory: ./voter-app
   ```
2. **Réduire la portée en PR** :
   - Exécuter **un sous-ensemble des tests** en PR (ex: seulement les tests critiques).
   - Exécuter **tous les tests** sur `develop` et avant une release.

**Validation** :
- Temps d’exécution des tests E2E en PR réduit de **50%** (ex: de 20 min à 10 min).

---

#### **P2-5 : Utiliser des runners plus puissants**
**Objectif** : Accélérer les jobs longs (E2E, mutation testing).
**Actions** :
1. Passer à des runners avec **8 vCPUs** pour les jobs longs :
   ```yaml
   jobs:
     e2e:
       runs-on: ubuntu-24.04  # 8 vCPUs
   ```

**Validation** :
- Temps d’exécution réduit de **20-30%** pour les jobs concernés.

---

#### **P2-6 : Mesurer les temps d’exécution**
**Objectif** : Suivre les performances des workflows.
**Actions** :
1. Ajouter un script pour logger le temps d’exécution de chaque job :
   ```yaml
   - name: Log workflow duration
     run: |
       START_TIME=$(date +%s)
       # ... (le reste du job)
       END_TIME=$(date +%s)
       DURATION=$((END_TIME - START_TIME))
       echo "Workflow duration: ${DURATION} seconds" >> $GITHUB_STEP_SUMMARY
   ```

**Validation** :
- Un tableau de bord montre l’évolution des temps d’exécution.

---

#### **P2-7 : Optimiser les dépendances**
**Objectif** : Réduire la taille des dépendances pour accélérer l’installation.
**Actions** :
1. **Backend** :
   - Utiliser `pip-tools` pour générer des `requirements.txt` minimaux.
   - Supprimer les dépendances inutilisées avec `pip-check` ou `pigar`.
2. **Frontend** :
   - Utiliser `npm prune` pour supprimer les dépendances inutilisées.

**Validation** :
- Taille de `node_modules` et des dépendances Python réduite de **20%**. 

---

### **✅ Critères de succès**
- [ ] Temps d’exécution total des workflows réduit de **30%**. 
- [ ] Coût GitHub Actions réduit de **20%** (moins de minutes d’exécution).
- [ ] Les builds frontend sont **mis en cache**. 
- [ ] Les scans redondants sont **désactivés**. 
- [ ] Les tests E2E sont **parallélisés** et optimisés.

---

---

## **🛡️ Phase 3 : Qualité et Sécurité (4 semaines)**
**Objectif** : Améliorer la **qualité du code** et la **sécurité**.

---

### **📌 Tâches**

| **ID** | **Tâche** | **Description** | **Livrable** | **Responsable** | **Échéance** | **Statut** |
|--------|-----------|----------------|--------------|-----------------|--------------|------------|
| **P3-1** | Augmenter les seuils de mutation | Passer à 85% (Backend) et 90% (Frontend). | Mise à jour des workflows | Équipe Dev | J+2 | ⬜ |
| **P3-2** | Ajouter des tests d’intégration | Tester les interactions entre composants. | Nouveau dossier `tests/integration/` | Équipe Dev | J+5 | ⬜ |
| **P3-3** | Ajouter des tests de performance | Mesurer les performances backend et frontend. | Nouveaux workflows `performance.yml` | Équipe DevOps | J+7 | ⬜ |
| **P3-4** | Scanner les images Docker | Ajouter un scan Trivy pour les images Docker. | Mise à jour de `audit.yml` | Équipe Sécurité | J+3 | ⬜ |
| **P3-5** | Améliorer la couverture de code | Passer à 95% (Backend) et 90% (Frontend). | Mise à jour des workflows | Équipe Dev | J+4 | ⬜ |
| **P3-6** | Ajouter un scan SAST pour YAML | Détecter les configurations dangereuses. | Mise à jour de `audit.yml` | Équipe Sécurité | J+6 | ⬜ |
| **P3-7** | Automatiser les revues de code | Intégrer SonarQube ou CodeClimate. | Nouveau workflow `sonarqube.yml` | Équipe DevOps | J+8 | ⬜ |

---

### **📝 Détails des tâches**

#### **P3-1 : Augmenter les seuils de mutation**
**Objectif** : Améliorer la qualité des tests en augmentant les seuils de mutation.
**Actions** :
1. **Backend** : Passer le seuil de **70%** à **85%** dans `mutation-testing.yml`.
2. **Frontend** : Passer le seuil de **80%** à **90%** dans `stryker.config.json`.
3. **Améliorer les tests** :
   - Ajouter des assertions manquantes.
   - Supprimer le code mort (via `vulture`/`knip`).

**Validation** :
- Les scores de mutation atteignent **85% (Backend)** et **90% (Frontend)**.

---

#### **P3-2 : Ajouter des tests d’intégration**
**Objectif** : Valider les interactions entre les composants backend et frontend.
**Actions** :
1. Créer un nouveau dossier `tests/integration/` avec des tests pour :
   - Les **endpoints API** (ex: soumission d’un vote).
   - Les **scénarios complexes** (ex: simulation avec plusieurs citoyens).
2. **Outils** :
   - **Backend** : `pytest` + `pytest-mock`.
   - **Frontend** : `Vitest` + `Supertest`.

**Validation** :
- **10 nouveaux tests d’intégration** ajoutés.

---

#### **P3-3 : Ajouter des tests de performance**
**Objectif** : Détecter les régressions de performance.
**Actions** :
1. **Backend** : Ajouter un workflow `performance.yml` avec **Locust** pour les tests de charge.
2. **Frontend** : Ajouter **Lighthouse** pour mesurer les performances web.

**Validation** :
- Les tests de performance s’exécutent **sans échec**. 
- Les métriques (temps de réponse, score Lighthouse) sont **suivies**. 

---

#### **P3-4 : Scanner les images Docker**
**Objectif** : Détecter les vulnérabilités dans les images Docker.
**Actions** :
1. Ajouter un job dans `audit.yml` pour scanner les images Docker :
   ```yaml
   - name: Trivy (Docker images)
     uses: aquasecurity/trivy-action@master
     with:
       scan-type: image
       image-ref: ghcr.io/burbanit0/vote-app:latest
       severity: HIGH,CRITICAL
       exit-code: "1"
   ```

**Validation** :
- Le scan détecte les vulnérabilités dans les images Docker.

---

#### **P3-5 : Améliorer la couverture de code**
**Objectif** : Atteindre 95% (Backend) et 90% (Frontend).
**Actions** :
1. **Backend** : Passer le seuil de `--cov-fail-under=90` à `--cov-fail-under=95`.
2. **Frontend** : Passer le seuil de couverture à **90%** dans `vitest.config.ts`.
3. **Identifier les zones non couvertes** avec `pytest --cov-report=html`.

**Validation** :
- Couverture à **95% (Backend)** et **90% (Frontend)**.

---

#### **P3-6 : Ajouter un scan SAST pour YAML**
**Objectif** : Détecter les configurations dangereuses dans les fichiers YAML.
**Actions** :
1. Ajouter un scan Semgrep pour les fichiers YAML dans `audit.yml` :
   ```yaml
   - name: Run Semgrep (YAML)
     run: semgrep --config=p/yaml --sarif-output=semgrep-yaml.sarif --error
   ```

**Validation** :
- Le scan détecte les **mauvaises configurations** (ex: permissions trop larges).

---

#### **P3-7 : Automatiser les revues de code**
**Objectif** : Intégrer SonarQube ou CodeClimate pour des revues de code automatiques.
**Actions** :
1. Créer un nouveau workflow `sonarqube.yml` pour scanner le code avec SonarQube.
2. Configurer SonarQube sur [SonarCloud](https://sonarcloud.io/).

**Validation** :
- Les rapports SonarQube sont **générés et accessibles**. 

---

### **✅ Critères de succès**
- [ ] Seuils de mutation à **85% (Backend)** et **90% (Frontend)**.
- [ ] **10 tests d’intégration** ajoutés.
- [ ] Tests de performance **fonctionnels** (Locust, Lighthouse).
- [ ] Scan des images Docker **intégré**. 
- [ ] Couverture de code à **95% (Backend)** et **90% (Frontend)**.
- [ ] Scan SAST pour YAML **intégré**. 
- [ ] SonarQube/CodeClimate **intégré**. 

---

---

## **🤖 Phase 4 : Automatisation Avancée (4 semaines)**
**Objectif** : Automatiser le **déploiement** et les **releases**.

---

### **📌 Tâches**

| **ID** | **Tâche** | **Description** | **Livrable** | **Responsable** | **Échéance** | **Statut** |
|--------|-----------|----------------|--------------|-----------------|--------------|------------|
| **P4-1** | Automatiser la génération des notes de release | Utiliser GitHub pour générer automatiquement les notes. | Mise à jour de `release.yml` | Équipe DevOps | J+2 | ⬜ |
| **P4-2** | Ajouter des vérifications pré-release | Vérifier la couverture, la qualité, et la sécurité avant une release. | Mise à jour de `release.yml` | Équipe DevOps | J+4 | ⬜ |
| **P4-3** | Automatiser le déploiement sur staging | Déployer automatiquement sur Fly.io après une release. | Nouveau workflow `deploy-staging.yml` | Équipe DevOps | J+6 | ⬜ |
| **P4-4** | Ajouter des canary releases | Déployer sur un sous-ensemble des utilisateurs. | Mise à jour de `release.yml` | Équipe DevOps | J+8 | ⬜ |
| **P4-5** | Automatiser les rollbacks | Revenir à la version précédente en cas d’échec. | Script de rollback | Équipe DevOps | J+10 | ⬜ |
| **P4-6** | Intégrer un outil de feature flags | Permettre des déploiements progressifs. | Intégration de LaunchDarkly/Unleash | Équipe Dev | J+12 | ⬜ |

---

### **📝 Détails des tâches**

#### **P4-1 : Automatiser la génération des notes de release**
**Objectif** : Générer automatiquement les notes de release avec GitHub.
**Actions** :
1. Utiliser `generate_release_notes: true` dans `release.yml`.
2. Personnaliser le template pour inclure les métriques de qualité.

**Validation** :
- Les notes de release sont **générées automatiquement** et incluent les métriques de qualité.

---

#### **P4-2 : Ajouter des vérifications pré-release**
**Objectif** : Vérifier que tout est prêt avant une release.
**Actions** :
1. Ajouter un job `pre_release_checks` dans `release.yml` pour vérifier :
   - La couverture de code.
   - Les scores de mutation.
   - L’absence de vulnérabilités critiques.

**Validation** :
- Une release ne peut pas être créée si les vérifications échouent.

---

#### **P4-3 : Automatiser le déploiement sur staging**
**Objectif** : Déployer automatiquement sur Fly.io après une release.
**Actions** :
1. Créer un nouveau workflow `deploy-staging.yml` qui s’exécute après une release.

**Validation** :
- Le déploiement sur staging est **automatique** après une release.

---

#### **P4-4 : Ajouter des canary releases**
**Objectif** : Déployer sur un sous-ensemble des utilisateurs pour détecter les problèmes.
**Actions** :
1. Intégrer **LaunchDarkly** ou **Unleash** pour activer/désactiver des fonctionnalités.
2. Configurer les flags pour les canary releases.

**Validation** :
- Une canary release est **déployée et testée**. 

---

#### **P4-5 : Automatiser les rollbacks**
**Objectif** : Revenir automatiquement à la version précédente en cas d’échec.
**Actions** :
1. Créer un script `rollback.sh` pour revenir à la version précédente.
2. Ajouter un job de rollback dans `deploy-staging.yml`.

**Validation** :
- Un rollback est **automatique** en cas d’échec du déploiement.

---

#### **P4-6 : Intégrer un outil de feature flags**
**Objectif** : Permettre des déploiements progressifs.
**Actions** :
1. Choisir un outil (LaunchDarkly ou Unleash).
2. Intégrer le SDK dans le frontend et le backend.
3. Configurer les flags.

**Validation** :
- Les feature flags sont **utilisés dans le code**. 

---

### **✅ Critères de succès**
- [ ] Les notes de release sont **générées automatiquement**. 
- [ ] Les vérifications pré-release **bloquent les releases défectueuses**. 
- [ ] Le déploiement sur staging est **automatique**. 
- [ ] Les canary releases sont **intégrées**. 
- [ ] Les rollbacks sont **automatisés**. 
- [ ] Un outil de feature flags est **intégré**. 

---

---

## **📈 Phase 5 : Monitoring et Maintenance (Continu)**
**Objectif** : Suivre, améliorer, et documenter en continu.

---

### **📌 Tâches**

| **ID** | **Tâche** | **Description** | **Livrable** | **Responsable** | **Fréquence** | **Statut** |
|--------|-----------|----------------|--------------|-----------------|---------------|------------|
| **P5-1** | Centraliser les résultats CI/CD | Créer un tableau de bord pour suivre l’historique. | Tableau de bord (Grafana/Allure) | Équipe DevOps | Mensuelle | ⬜ |
| **P5-2** | Ajouter des badges de statut | Afficher l’état de la CI/CD dans le README. | Mise à jour du `README.md` | Matthieu Burban | Ponctuelle | ⬜ |
| **P5-3** | Suivre les métriques CI/CD | Mesurer les temps, coûts, et taux d’échec. | Script de suivi | Équipe DevOps | Mensuelle | ⬜ |
| **P5-4** | Documenter les workflows | Maintenir la documentation à jour. | Mise à jour de `CI_CD.md` | Matthieu Burban | Trimestrielle | ⬜ |
| **P5-5** | Automatiser la mise à jour des actions GitHub | Utiliser Dependabot pour mettre à jour les actions. | Mise à jour de `dependabot.yml` | Équipe DevOps | Mensuelle | ⬜ |
| **P5-6** | Revoir les seuils et règles | Ajuster les seuils en fonction des métriques. | Rapport de revue | Équipe Dev | Trimestrielle | ⬜ |
| **P5-7** | Former l’équipe | Former les nouveaux membres à la CI/CD. | Session de formation | Matthieu Burban | Trimestrielle | ⬜ |

---

### **📝 Détails des tâches**

#### **P5-1 : Centraliser les résultats CI/CD**
**Objectif** : Avoir une vue d’ensemble des résultats CI/CD.
**Actions** :
1. Utiliser **GitHub Insights** (gratuit pour les repos publics).
2. **Option 2** : Configurer **Allure Report** pour les tests.
3. **Option 3** : Configurer **Grafana** pour les métriques personnalisées.

**Validation** :
- Un tableau de bord est **accessible et mis à jour**. 

---

#### **P5-2 : Ajouter des badges de statut**
**Objectif** : Afficher l’état de la CI/CD dans le `README.md`.
**Actions** :
1. Ajouter les badges suivants dans `README.md` :
   ```markdown
   ## 🚀 CI/CD Status

   ![Backend CI](https://github.com/Burbanit0/Vote-App/actions/workflows/backend-ci-cd-pipeline.yml/badge.svg)
   ![Frontend CI](https://github.com/Burbanit0/Vote-App/actions/workflows/frontend-ci-cd-pipeline.yml/badge.svg)
   ![E2E](https://github.com/Burbanit0/Vote-App/actions/workflows/e2e.yml/badge.svg)
   ![Audit](https://github.com/Burbanit0/Vote-App/actions/workflows/audit.yml/badge.svg)
   ![Release](https://github.com/Burbanit0/Vote-App/actions/workflows/release.yml/badge.svg)
   ```

**Validation** :
- Les badges sont **affichés et mis à jour**. 

---

#### **P5-3 : Suivre les métriques CI/CD**
**Objectif** : Mesurer les performances et les coûts.
**Actions** :
1. Utiliser l’API GitHub pour récupérer les temps d’exécution des workflows.
2. Utiliser des outils comme [`github-actions-cost-estimator`](https://github.com/marketplace/actions/github-actions-cost-estimator).

**Validation** :
- Un rapport mensuel montre l’évolution des métriques. 

---

#### **P5-4 : Documenter les workflows**
**Objectif** : Maintenir la documentation à jour.
**Actions** :
1. Mettre à jour `CI_CD.md` avec les nouveaux workflows et changements.

**Validation** :
- La documentation est **à jour et complète**. 

---

#### **P5-5 : Automatiser la mise à jour des actions GitHub**
**Objectif** : Éviter les dépendances obsolètes.
**Actions** :
1. Vérifier que Dependabot est configuré pour mettre à jour les actions GitHub.

**Validation** :
- Les actions GitHub sont **à jour**. 

---

#### **P5-6 : Revoir les seuils et règles**
**Objectif** : Ajuster les seuils en fonction des métriques.
**Actions** :
1. Revoir les seuils trimestriellement (couverture, mutation, complexité).

**Validation** :
- Les seuils sont **optimaux et réalistes**. 

---

#### **P5-7 : Former l’équipe**
**Objectif** : Former les nouveaux membres à la CI/CD.
**Actions** :
1. Organiser une **session de formation** trimestrielle.
2. Documenter les bonnes pratiques dans `CONTRIBUTING.md`.

**Validation** :
- L’équipe **comprend et utilise** la CI/CD efficacement. 

---

### **✅ Critères de succès**
- [ ] Un **tableau de bord CI/CD** est disponible. 
- [ ] Les **badges de statut** sont affichés dans le `README.md`. 
- [ ] Les **métriques CI/CD** sont suivies et analysées. 
- [ ] La **documentation** est à jour. 
- [ ] Les **actions GitHub** sont automatiquement mises à jour. 
- [ ] Les **seuils** sont revus trimestriellement. 
- [ ] L’équipe est **formée** à la CI/CD. 

---

---

## **📊 Tableau de bord de suivi**

---

### **📌 État d’avancement global**

| **Phase** | **Durée** | **Tâches** | **Avancement** | **Statut** | **Responsable** |
|-----------|----------|------------|----------------|------------|-----------------|
| Phase 0 | 1 semaine | 5/5 | 0% | ⏳ À venir | Matthieu Burban |
| Phase 1 | 2 semaines | 8/8 | 0% | ⏳ À venir | Équipe DevOps |
| Phase 2 | 3 semaines | 7/7 | 0% | ⏳ À venir | Équipe DevOps |
| Phase 3 | 4 semaines | 7/7 | 0% | ⏳ À venir | Équipe Dev |
| Phase 4 | 4 semaines | 6/6 | 0% | ⏳ À venir | Équipe DevOps |
| Phase 5 | Continu | 7/7 | 0% | ⏳ À venir | Équipe DevOps |

---

### **📈 Métriques clés**

| **Métrique** | **Valeur actuelle** | **Valeur cible** | **Statut** |
|-------------|---------------------|------------------|------------|
| Temps d’exécution moyen (PR) | 20-30 min | <15 min | ❌ |
| Coût GitHub Actions (mensuel) | $X | $-20% | ❌ |
| Couverture backend | 90% | 95% | ❌ |
| Couverture frontend | 80% | 90% | ❌ |
| Score de mutation backend | 72,9% | 85% | ❌ |
| Score de mutation frontend | 80,82% | 90% | ❌ |
| Nombre de vulnérabilités bloquantes | Y | 0 | ❌ |
| Taux d’échec des workflows | Z% | <5% | ❌ |

---

---

## **💡 Bonnes pratiques à adopter**

1. **Toujours tester les changements CI/CD** :
   - Ouvrir une **branche de test** avant de merger les changements sur `develop`.
   - Vérifier que tous les workflows **passent ou échouent comme attendu**. 

2. **Documenter chaque changement** :
   - Mettre à jour `CI_CD.md` après chaque modification.
   - Ajouter des **commentaires** dans les workflows pour expliquer les choix. 

3. **Suivre les métriques** :
   - Utiliser **GitHub Insights** ou **Grafana** pour suivre les performances.
   - **Revoir les seuils** trimestriellement. 

4. **Former l’équipe** :
   - Organiser des **sessions de formation** régulières.
   - **Documenter les bonnes pratiques** dans `CONTRIBUTING.md`. 

5. **Automatiser au maximum** :
   - Utiliser **Dependabot** pour les mises à jour.
   - **Éviter les tâches manuelles** (ex: génération des notes de release).

---

---

## **📌 Checklist finale**

---

### **✅ Phase 0 : Audit et Préparation**
- [ ] `CI_CD_AUDIT.md` créé et complet.
- [ ] Tableau des problèmes identifiés et priorisés.
- [ ] Roadmap priorisée validée par l’équipe.
- [ ] `CI_CD.md` créé et documenté.
- [ ] Environnement CI/CD vérifié et fonctionnel.

---

### **✅ Phase 1 : Corrections Critiques**
- [ ] Tests E2E **bloquants** pour les merges.
- [ ] `pip-audit` **bloquant** pour les vulnérabilités.
- [ ] Trivy **bloquant** pour les vulnérabilités HIGH/CRITICAL.
- [ ] `mutation-testing.yml` **corrigé** (branche `develop`).
- [ ] Node 22 **utilisé pour Stryker**. 
- [ ] Retries automatiques **ajoutés** pour les jobs flaky.
- [ ] Toutes les corrections **testées et validées**. 

---

### **✅ Phase 2 : Optimisation des Performances**
- [ ] Jobs CI **parallélisés** (Backend + Frontend).
- [ ] Builds frontend **mis en cache**. 
- [ ] Scans redondants **désactivés**. 
- [ ] Tests E2E **optimisés** (parallélisation, sous-ensemble en PR).
- [ ] Runners plus puissants **utilisés** pour les jobs longs.
- [ ] Temps d’exécution **mesurés et suivis**. 
- [ ] Dépendances **optimisées** (taille réduite).

---

### **✅ Phase 3 : Qualité et Sécurité**
- [ ] Seuils de mutation **augmentés** (Backend: 85%, Frontend: 90%).
- [ ] **10 tests d’intégration** ajoutés.
- [ ] Tests de performance **fonctionnels** (Locust, Lighthouse).
- [ ] Scan des images Docker **intégré**. 
- [ ] Couverture de code **améliorée** (Backend: 95%, Frontend: 90%).
- [ ] Scan SAST pour YAML **intégré**. 
- [ ] SonarQube/CodeClimate **intégré**. 

---

### **✅ Phase 4 : Automatisation Avancée**
- [ ] Notes de release **générées automatiquement**. 
- [ ] Vérifications pré-release **bloquantes**. 
- [ ] Déploiement sur staging **automatique**. 
- [ ] Canary releases **intégrées**. 
- [ ] Rollbacks **automatisés**. 
- [ ] Outil de feature flags **intégré**. 

---

### **✅ Phase 5 : Monitoring et Maintenance**
- [ ] Tableau de bord CI/CD **centralisé**. 
- [ ] Badges de statut **affichés dans le README**. 
- [ ] Métriques CI/CD **suivies et analysées**. 
- [ ] Documentation **à jour**. 
- [ ] Actions GitHub **automatiquement mises à jour**. 
- [ ] Seuils **revus trimestriellement**. 
- [ ] Équipe **formée** à la CI/CD. 

---

---

## **🎯 Conclusion**
Ce plan **complet et structuré** permet d’améliorer la CI/CD de **Vote-App** de manière **progressive et mesurable**. En suivant les étapes décrites, tu peux :
1. **Corriger les problèmes critiques** (Phase 1).
2. **Optimiser les performances** (Phase 2).
3. **Améliorer la qualité et la sécurité** (Phase 3).
4. **Automatiser le déploiement** (Phase 4).
5. **Maintenir et améliorer en continu** (Phase 5).

---

### **🚀 Prochaines étapes**
1. **Valider le plan** avec ton équipe.
2. **Commencer par la Phase 0** (Audit et Préparation).
3. **Passer à la Phase 1** (Corrections Critiques) dès que l’audit est terminé.
4. **Suivre l’avancement** avec le tableau de bord.

---

Si tu as besoin d’aide pour implémenter une tâche spécifique ou pour créer des templates de workflows, n’hésite pas à demander ! 😊