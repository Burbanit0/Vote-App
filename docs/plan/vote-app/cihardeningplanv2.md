# Plan de durcissement CI — Vote-App / La Fourmilière (v2)

> État vérifié directement sur `develop` (tarball `codeload.github.com`, commit HEAD au
> 2026-08-25), pas sur un résumé. La suite `api/tests/test_polity_*.py` a été exécutée
> localement pour obtenir un vrai chiffre de couverture plutôt qu'une estimation.
>
> **v2 (2026-08-25) :** revue par une seconde session Claude, avec re-vérification live
> de `develop` (qui a encore bougé entre-temps — PR #186 `refactor/decompose-workers` et
> PR #187 `ci/fix-mutation-testing-gates` sont mergées). Les ajouts sont marqués 🆕 et
> laissent le contenu original intact ; seule la numérotation de la section C et le
> lettrage à partir de D ont dû être décalés pour les intégrer proprement.
>
> Légende de statut (convention reprise de `polity-simulation-design.md`) :
> 🟢 fait/résolu · 🟡 partiel ou décision à prendre · 🔴 pas fait / ouvert · 🆕 ajout v2

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

7. 🆕 **Aucun `concurrency:` group sur 7 des 9 workflows.** Vérifié en direct sur
   `develop` : seuls `e2e.yml` et `mutation-testing.yml` déclarent un `concurrency:`.
   `backend-ci-cd-pipeline.yml` (le job de 12-17 min, cf. discussion CI antérieure),
   `frontend-ci-cd-pipeline.yml`, `audit.yml`, `openapi-contract.yml`, `release.yml`,
   `branch-policy.yml`, `merge-to-main.yml` n'en ont aucun. Conséquence concrète :
   pusher plusieurs commits rapprochés sur une même PR fait tourner plusieurs fois en
   parallèle le job le plus long au lieu d'annuler les runs devenus obsolètes —
   gaspillage direct du budget qu'on vient de réduire avec `pytest-xdist`.

8. 🆕 **Les checks requis de branch protection sont fragiles aux renommages de job.**
   Un check requis GitHub Actions est lié au **nom littéral** du `name:` d'un job, pas
   à un identifiant stable. Ce n'est pas théorique : dans la session précédente, le job
   `"Code Quality (dead code & duplication)"` de `audit.yml` a été renommé en
   `"Code Quality (dead code, duplication & complexity)"` en ajoutant radon/xenon. Si ce
   nom avait déjà été inscrit comme check requis à ce moment-là (ce qui est justement
   l'objet du point P0.2 ci-dessous), la branch protection se serait retrouvée à
   attendre indéfiniment un check qui ne se déclenche plus jamais sous l'ancien nom.

9. 🆕 **`refactor/decompose-workers` (PR #186) et `ci/fix-mutation-testing-gates`
   (PR #187) sont mergées depuis la rédaction de la v1 de ce plan.** La première change
   potentiellement le terrain de la décision du point 8/11 (exclusion mutmut de
   `workers.py`, couplage `TestClient`) — à revérifier avant de trancher, pas à
   supposer inchangé. La seconde a déjà réparé et durci les planchers de mutation
   testing mentionnés en A2, donc une partie du diagnostic du point 1 ci-dessus a pu
   évoluer entre la v1 et la v2 de ce plan — le point P0.1 (branche par défaut) reste
   néanmoins valide indépendamment, `schedule`/`workflow_dispatch` continuant de se
   résoudre contre la branche par défaut quel que soit l'état des gates.

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
   🆕 *Synergie* : ça aligne gratuitement le futur `dependabot.yml` du point 3 —
   Dependabot cible la branche par défaut sauf `target-branch:` explicite, donc pointer
   le défaut sur `develop` évite d'avoir à le préciser.
   🆕 *Vérification avant bascule* : s'assurer qu'aucun badge CI dans `README.md` ni
   aucune instruction de clone ne suppose implicitement `main` comme branche par
   défaut, pour ne pas casser une doc silencieusement.

2. **Activer la protection de branche sur `develop`** (c'est elle qui compte tant que
   `main` n'a pas bougé) : statuts requis = job `test` de `backend-ci-cd-pipeline.yml`,
   `frontend-ci-cd-pipeline.yml`, `e2e.yml`, `openapi-contract.yml`, jobs de `audit.yml`
   (semgrep, gitleaks, trivy, code-quality, codeql). Ne pas y mettre
   `mutation-testing.yml` tant qu'il ne tourne pas sur `pull_request` — un check requis
   qui ne se déclenche jamais bloquerait indéfiniment.
   🆕 *Règle à documenter en même temps* (voir B8) : tout renommage d'un `name:` de job
   dans ces workflows doit être accompagné de la mise à jour de la liste des checks
   requis dans le même geste — sinon la protection se bloque silencieusement sur un nom
   de check qui n'existe plus.

### Priorité 1 — cette semaine, pas de nouvelle dépendance

3. `.github/dependabot.yml` — pip (`fast_api_voter/requirements.txt`), npm
   (`voter-app`), écosystème `github-actions` (actions déjà épinglées par hash,
   Dependabot proposera les mises à jour de hash).
   🆕 *Alternative à considérer* : Renovate plutôt que Dependabot si vous voulez du
   groupement de PRs configurable et un format de commit conforme à votre convention
   Conventional Commits existante — Dependabot ne fait ni l'un ni l'autre nativement.
   Pas un blocage, juste un arbitrage à faire avant d'écrire le fichier plutôt
   qu'après.
4. Retirer `continue-on-error: true` de l'étape `pip-audit` dans
   `backend-ci-cd-pipeline.yml`, ou a minima le faire bloquer sur high/critical comme
   `npm audit --audit-level=high` côté frontend — cohérence entre les deux stacks.
   🆕 *Pré-check avant de flipper* : lancer `pip-audit --requirement
   fast_api_voter/requirements.txt` en local d'abord, pour confirmer qu'aucune CVE
   non-patchable n'est déjà en attente — sinon le passage en bloquant casse toutes les
   PR dès le prochain push, plutôt que de gater un vrai changement. Même méthodologie
   que celle utilisée pour rendre `openapi-contract.yml` bloquant (vérifié zéro drift
   avant de gater).
5. 🆕 **Ajouter un `concurrency:` group aux 7 workflows qui n'en ont pas** (voir B7) :
   `backend-ci-cd-pipeline.yml`, `frontend-ci-cd-pipeline.yml`, `audit.yml`,
   `openapi-contract.yml`, `release.yml`, `branch-policy.yml`, `merge-to-main.yml`.
   ```yaml
   concurrency:
     group: ${{ github.workflow }}-${{ github.ref }}
     cancel-in-progress: true
   ```
   Coût quasi nul (5 lignes par fichier), aucune nouvelle dépendance, gain direct sur
   le temps d'attente et le budget de minutes CI dès qu'une PR reçoit plusieurs pushs
   rapprochés.
6. 🆕 **Documenter la CI dans un fichier unique.** 9 workflows aujourd'hui — sans une
   table trigger/gate/bloquant-ou-pas/durée quelque part, la seule source de vérité
   redevient "lire les 9 YAML". À ajouter à la racine (pas dans `docs/`, qui est
   gitignoré dans ce repo) comme `CODE_AUDIT.md`, ou en nouvelle section de
   `CONTRIBUTING.md`.
7. Chantier cardinal — déjà scopé dans le repo (`pyproject.toml` le nomme
   explicitement) : étendre le harness de parité + les tests pour les 6 règles
   nommées de `simulation_score_utils.py`.

### Priorité 2 — extensions issues des découvertes du jour

8. Étendre le scope `mutmut` aux fichiers **déterministes** de `polity/` —
   `ballot_and_aggregation.py`, `institutional_clock.py`, `legitimacy.py`, `config.py`.
   La justification originale ("polity trop instable pour mutmut") ne tient
   probablement plus pour ces fichiers-là vu la maturité actuelle (v6b clos, 99% de
   couverture). Laisser `llm_behavior_engine.py`/`llm_client.py` en dehors — muter du
   code qui appelle un LLM est peu informatif.
9. Étendre Hypothesis au module polity — `legitimacy.py` est le candidat naturel
   (bornes de `L(t)`, invariant déjà identifié dans nos échanges précédents), puis
   `ballot_and_aggregation.py` pour la parité d'agrégation.

### Priorité 3 — une vraie décision, pas de l'exécution

10. `workers.py` : documenter l'exclusion mutmut comme définitive et argumentée dans
    `traceability.md` (même traitement que Liquid Democracy) **ou** investir dans
    l'extraction de la logique pure d'Arrow/Gibbard-Satterthwaite hors de la
    dépendance `TestClient` pour la rendre mutable. Arbitrage coût/bénéfice à faire,
    pas un chantier à lancer par défaut.
    🆕 *À revérifier avant de trancher* (voir B9) : `refactor/decompose-workers`
    (PR #186) vient d'être mergée — vérifier si elle a déjà extrait une partie de la
    logique pure hors du couplage `TestClient`, ce qui changerait le coût réel de
    l'option "refactorer" par rapport à ce qui était vrai au moment de la v1 de ce
    plan.

---

## D. 🆕 Relecture de code par agents

Champ distinct de la CI YAML — complémentaire, pas un remplacement des scanners
déterministes déjà en place (Semgrep/CodeQL/Bandit couvrent les patterns connus ; un
reviewer LLM attrape des problèmes de logique métier ou d'autorisation que les
scanners par pattern ne voient pas).

11. 🆕 Utiliser systématiquement les skills déjà disponibles dans cet environnement
    avant de merger une PR volumineuse générée avec assistance LLM : `/code-review`
    (bugs + simplification/réutilisation/efficacité, niveau d'effort réglable, peut
    commenter directement en ligne sur une PR avec `--comment` ou appliquer les fixes
    avec `--fix`) et `/security-review`. Zéro configuration requise, disponible
    immédiatement.
12. 🆕 Étudier l'activation d'un "PR Steward" Claude persistant sur le repo — surveille
    une PR en continu (CI rouge, commentaires de review) et agit sans qu'une session
    ait à le driver manuellement à chaque fois. Se configure via l'app GitHub Claude
    Code plutôt que par un fichier du repo — à creuser séparément si l'idée intéresse.
13. 🆕 (optionnel) Envisager un reviewer IA indépendant en complément — CodeRabbit ou
    Sourcery — si un second avis distinct de Claude est souhaité sur les PR.

---

## E. Suivi

- [ ] Branche par défaut GitHub → `develop` (vérifier README/badges avant bascule)
- [ ] Protection de branche activée sur `develop`
- [ ] 🆕 Règle "renommer un job = mettre à jour les checks requis" documentée
- [ ] `.github/dependabot.yml` ajouté (🆕 arbitrage Dependabot vs Renovate fait avant)
- [ ] `pip-audit` ne tourne plus en `continue-on-error` (🆕 pré-check CVE fait avant)
- [ ] 🆕 `concurrency:` ajouté aux 7 workflows qui n'en ont pas
- [ ] 🆕 Carte CI (trigger/gate/bloquant/durée, 9 workflows) documentée
- [ ] Chantier cardinal (6 règles `simulation_score_utils.py`) lancé
- [ ] Scope `mutmut` étendu aux fichiers déterministes de `polity/`
- [ ] Hypothesis étendu à `legitimacy.py` (bornes de `L(t)`)
- [ ] Décision prise sur `workers.py` (🆕 re-vérifiée contre PR #186 avant de trancher)
- [ ] 🆕 `/code-review` et `/security-review` utilisés en pratique avant les grosses PR
- [ ] 🆕 Décision prise sur l'activation d'un PR Steward persistant
- [ ] Merge `develop → main` — **seulement à la fin de la feature polity**, revoir ce
      plan à ce moment-là (le point 1 redevient inutile une fois `main` à jour, mais
      ne fait pas de mal à laisser en place)
