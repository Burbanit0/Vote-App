# Plan de durcissement CI — Vote-App / La Fourmilière

> État vérifié directement sur `develop` (tarball `codeload.github.com`, commit HEAD au
> 2026-08-25), pas sur un résumé. La suite `api/tests/test_polity_*.py` a été exécutée
> localement pour obtenir un vrai chiffre de couverture plutôt qu'une estimation.
>
> Légende de statut (convention reprise de `polity-simulation-design.md`) :
> 🟢 fait/résolu · 🟡 partiel ou décision à prendre · 🔴 pas fait / ouvert

---

## 0. Contrainte structurante à respecter dans tout ce plan

**`develop` ne mergera vers `main` qu'à la fin de la feature polity, pas avant.**
Conséquence directe : toute action qui supposait un merge `develop → main` pour
« rattraper » `main` est **écartée**. Le point 1 ci-dessous a été réécrit en
conséquence — la solution retenue n'implique aucun merge de code, uniquement un
réglage GitHub.

---

## A. Bilan des deux audits précédents (CI + liste d'outils)

### A1. Audit CI initial

| Point relevé | Statut vérifié sur `develop` |
|---|---|
| Aucun scan de sécurité périodique | 🟢 Résolu — `audit.yml` a maintenant `schedule: cron "0 6 * * 1"` en plus de push/PR |
| Pas de Dependabot | 🔴 Toujours absent — aucun `.github/dependabot.yml` |
| E2E en `workflow_dispatch` seul | 🟢 Résolu — `e2e.yml` tourne maintenant sur `pull_request` (paths ciblés) |
| Seuil de couverture 30% | 🟢 Largement dépassé — backend `--cov-fail-under=90`, frontend verrouillé aux valeurs mesurées (84.57/86.28/74.77/75.98%) |
| `pip-audit` en `continue-on-error: true` | 🔴 Toujours vrai, incohérent avec `npm audit --audit-level=high` qui bloque côté frontend |

### A2. Liste d'outils proposée

| Outil | Statut vérifié |
|---|---|
| Hypothesis (Condorcet, monotonicité) | 🟢 Fait côté moteur de vote — 🔴 **pas étendu au module polity** (zéro `@given` dans `test_polity_*.py`) |
| Mutation testing (mutmut/Stryker) | 🟡 Planchers actifs (62%/76%) mais ne gate aucune PR ; voir détails en B |
| radon / xenon | 🟢 Adopté — `xenon -a A` gate la complexité moyenne dans `audit.yml` |
| ADR | 🟢 Adopté — `docs/adr/ADR-001-serving-layer-ollama-vs-llama-server.md` + backlog |
| Devcontainer | 🔴 Pas fait |
| MkDocs Material | 🔴 Pas fait |
| Justfile / Makefile | 🔴 Pas fait (`ci-local/run-ci.sh` + `.ps1` couvrent une partie du besoin) |
| DVC | 🔴 Pas fait |
| Tracker d'expériences (MLflow/Sacred/W&B) | 🔴 Rien dans `requirements*.txt` |
| Liquid Democracy / Conviction Voting | 🔴 Toujours pas implémenté malgré le prompt préparé |

---

## B. Ce qui a été découvert en regardant `develop` en direct

1. **`mutation-testing.yml` est en partie inerte.** Le fichier documente lui-même le
   problème : `schedule` et `workflow_dispatch` sont résolus par GitHub contre la
   branche par défaut du repo, qui est `main` — or `main` est 215 commits derrière
   `develop`, donc le workflow n'y existe pas. Le cron du lundi ne s'est jamais
   déclenché, `gh workflow run` répond 404. Seul le trigger `push` (résolu contre la
   ref réellement poussée) fonctionne aujourd'hui.

2. **Le module polity est bien plus avancé qu'un squelette v0** : `fast_api_voter/api/domain/polity/`
   contient 19 fichiers réels — `legitimacy.py` (v4), `shock.py` (v5), `social_graph.py`
   (v6), `sortition_chamber.py` + `accountability.py` (le v6bis clos), `llm_behavior_engine.py`
   (2547 lignes, candidature/campagne/coalition déjà codées).

3. **Couverture réelle du module polity, mesurée localement** (1162 passed / 41 skipped,
   `test_polity_llm_live.py` auto-skip sans Ollama réel) :
   ```
   TOTAL   2790 stmts   26 miss   99% cover
   ```
   11 fichiers sur 20 à 100%. Ça répond positivement à la question qu'on s'était posée
   ("le module qui grossit vite pourrait cacher ses trous derrière la moyenne globale
   de 90%") — empiriquement ce n'est pas le cas, pas besoin d'un seuil séparé pour l'instant.

4. **Le chantier cardinal est déjà scopé et chiffré dans le repo lui-même** :
   `simulation_score_utils.py` reste à 51,7% de survivants (284/549, inchangé) même
   après avoir élargi la sélection de tests de 14+2 à 25 fichiers (qui, elle, a fait
   passer `simulation_ranked_utils.py` de 58,9% à 71,3%). Les 6 règles non couvertes
   sont nommées : `median_voting`, `mean_median_hybrid`, `variance_based`,
   `score_distribution_analysis`, `majority_judgment`, `evaluative`.

5. **L'exclusion de `workers.py` de mutmut est un vrai blocage diagnostiqué**, pas un
   oubli : mutmut 3.7.0 réexécute pytest in-process, et tout test `TestClient` casse
   de façon reproductible (NumPy reload + anyio cancel-scope invalide), alors que le
   même run pytest hors mutmut passe proprement.

6. **Aucun fichier n'encode la protection de branche** — elle ne peut vivre que dans
   GitHub Settings, invisible depuis le code.

---

## C. Plan d'action, priorisé et adapté à la contrainte "pas de merge vers main"

### Priorité 0 — réglages seuls, aucun merge de code, ~30 min

1. **Changer la branche par défaut du repo vers `develop` dans Settings.**
   C'est la solution qui remplace le merge : `schedule`/`workflow_dispatch` se
   résolvent contre la branche par défaut, pas contre une branche en particulier —
   changer ce réglage répare `mutation-testing.yml` sans toucher à `main` ni pousser
   la feature polity partiellement où que ce soit. Cohérent avec un gitflow où
   `develop` est la branche vivante pendant que `main` attend la fin d'une feature
   longue.
2. **Activer la protection de branche sur `develop`** (c'est elle qui compte tant que
   `main` n'a pas bougé) : statuts requis = job `test` de `backend-ci-cd-pipeline.yml`,
   `frontend-ci-cd-pipeline.yml`, `e2e.yml`, `openapi-contract.yml`, jobs de `audit.yml`
   (semgrep, gitleaks, trivy, code-quality, codeql). Ne pas y mettre
   `mutation-testing.yml` tant qu'il ne tourne pas sur `pull_request` — un check requis
   qui ne se déclenche jamais bloquerait indéfiniment.

### Priorité 1 — cette semaine, pas de nouvelle dépendance

3. `.github/dependabot.yml` — pip (`fast_api_voter/requirements.txt`), npm
   (`voter-app`), écosystème `github-actions` (actions déjà épinglées par hash,
   Dependabot proposera les mises à jour de hash).
4. Retirer `continue-on-error: true` de l'étape `pip-audit` dans
   `backend-ci-cd-pipeline.yml`, ou a minima le faire bloquer sur high/critical comme
   `npm audit --audit-level=high` côté frontend — cohérence entre les deux stacks.
5. Chantier cardinal — déjà scopé dans le repo (`pyproject.toml` le nomme
   explicitement) : étendre le harness de parité + les tests pour les 6 règles
   nommées de `simulation_score_utils.py`.

### Priorité 2 — extensions issues des découvertes du jour

6. Étendre le scope `mutmut` aux fichiers **déterministes** de `polity/` —
   `ballot_and_aggregation.py`, `institutional_clock.py`, `legitimacy.py`, `config.py`.
   La justification originale ("polity trop instable pour mutmut") ne tient
   probablement plus pour ces fichiers-là vu la maturité actuelle (v6b clos, 99% de
   couverture). Laisser `llm_behavior_engine.py`/`llm_client.py` en dehors — muter du
   code qui appelle un LLM est peu informatif.
7. Étendre Hypothesis au module polity — `legitimacy.py` est le candidat naturel
   (bornes de `L(t)`, invariant déjà identifié dans nos échanges précédents), puis
   `ballot_and_aggregation.py` pour la parité d'agrégation.

### Priorité 3 — une vraie décision, pas de l'exécution

8. `workers.py` : documenter l'exclusion mutmut comme définitive et argumentée dans
   `traceability.md` (même traitement que Liquid Democracy) **ou** investir dans
   l'extraction de la logique pure d'Arrow/Gibbard-Satterthwaite hors de la
   dépendance `TestClient` pour la rendre mutable. Arbitrage coût/bénéfice à faire,
   pas un chantier à lancer par défaut.

---

## D. Suivi

- [ ] Branche par défaut GitHub → `develop`
- [ ] Protection de branche activée sur `develop`
- [ ] `.github/dependabot.yml` ajouté
- [ ] `pip-audit` ne tourne plus en `continue-on-error`
- [ ] Chantier cardinal (6 règles `simulation_score_utils.py`) lancé
- [ ] Scope `mutmut` étendu aux fichiers déterministes de `polity/`
- [ ] Hypothesis étendu à `legitimacy.py` (bornes de `L(t)`)
- [ ] Décision prise sur `workers.py` (documentée ou refactorée)
- [ ] Merge `develop → main` — **seulement à la fin de la feature polity**, revoir ce
      plan à ce moment-là (le point 1 redevient inutile une fois `main` à jour, mais
      ne fait pas de mal à laisser en place)
