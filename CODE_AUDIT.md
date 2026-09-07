# Audit code — code mort, duplication & garde-fous "vibe coding"

*Première édition : 2026-08-20. Section complexité cyclomatique (radon/xenon)
ajoutée le 2026-08-21. À relancer et mettre à jour après chaque passe de
nettoyage significative (voir "Prochaines étapes" en bas de page).*

*Mise à jour du 2026-09-06 : outils relancés après la passe de 14 PR qui a
supprimé l'arbre mort `voter-app/src/components/Simulation/` (~16 500 lignes)
et corrigé plusieurs des points relevés ci-dessous (voir §3 et §7 — tous les
"quick wins" de la première édition sont désormais traités). Chiffres
recalculés à partir de `.github/quality-baseline.json` et d'une exécution
directe de `vulture`/`knip`/`jscpd`/`radon` sur le HEAD actuel de `develop`.*

## Résumé exécutif

Le repo `Vote-App` (backend FastAPI `fast_api_voter/`, frontend React/TS
`voter-app/`) a été très largement construit avec assistance LLM. L'outillage
**sécurité** est déjà solide (Semgrep, Gitleaks, Trivy, CodeQL, bandit,
pip-audit, npm audit — tous câblés en pre-commit/CI). Il manquait en revanche
tout détecteur de **code mort**, de **duplication** et de **dépendances
inutilisées** — les trois angles morts typiques du code généré par LLM par
petites itérations. Cet audit comble ces trois lacunes avec `vulture`
(Python), `knip` (TS) et `jscpd` (cross-langage), livre les résultats
curatés ci-dessous, et câble les trois outils en **mode informationnel
uniquement** dans `scripts/audit.sh` et une nouvelle CI job non-bloquante.
Une mise à jour du 2026-08-21 ajoute un quatrième outil dans le même job,
`radon`/`xenon`, pour la **complexité cyclomatique** — un angle mort
supplémentaire (flake8 est volontairement scopé à `E9,F`, sans règle de
complexité) qui confirme et affine le diagnostic de fragmentation
architecturale posé par jscpd (§4) : la même famille de fichiers
`workers*.py` concentre aussi les fonctions les plus complexes du repo.

**Verdict global : plutôt sain.** La duplication littérale est faible
(0,64 % des lignes scannées au 2026-09-06, en baisse depuis 0,81 % en août),
le code mort backend détecté à haute confiance a été entièrement corrigé
(0 cas restant, voir §3), le code mort frontend haute-confiance reste minime
(9 fichiers, composition différente de l'édition d'août — voir §3), et il n'y
a ni `console.log` oublié ni `eslint-disable` ni TODO/FIXME qui traînent. Le
vrai risque n'est
pas la duplication copiée-collée mais la **fragmentation architecturale** :
plusieurs familles de fichiers parallèles (`workers*.py`, `components/shared/`
à plat) qui grossissent indépendamment plutôt que de s'étendre — un
symptôme classique d'ajouts LLM successifs sans passe de consolidation.

---

## 1. Garde-fous déjà en place (avant cet audit)

| Catégorie | Outils | Portée | Bloquant ? |
|---|---|---|---|
| Secrets | detect-secrets (pre-commit), Gitleaks (CI) | tout le repo | Oui |
| SAST | Semgrep (multi-config), Bandit (Python), CodeQL (non-gating) | tout le repo | Semgrep/Bandit oui, CodeQL non |
| Dépendances/conteneurs/CVE | Trivy, pip-audit (informationnel), npm audit | tout le repo | Trivy/npm audit oui |
| Lint Python | flake8 (scope `E9,F` — syntaxe + pyflakes uniquement) | `fast_api_voter/*.py` | Oui |
| Types Python | mypy strict | `fast_api_voter/api/` | Oui |
| Lint TS/React | ESLint 9 (flat config, react/hooks/a11y/prettier) + `eslint-plugin-unused-imports` | `voter-app/src` | Oui |
| Types TS | `tsc --noEmit` | `voter-app` | Oui |
| Tests | pytest (coverage ≥ 90 % en CI et en pre-commit), vitest | les deux stacks | Oui |
| Politique de branches | naming, source `develop`→`main`, Conventional Commits | PRs | Oui (naming/source) |

**Confirmé absent avant cet audit :** aucune détection de code mort
cross-fichier (au-delà des imports non utilisés dans un seul fichier côté
TS), aucune détection de duplication, aucune détection de dépendance
inutilisée. `flake8` est volontairement scopé à `E9,F` (pas de règles de
complexité/style), donc pas de garde-fou "fichier trop long" ou "fonction
trop complexe" côté backend non plus.

---

## 2. Garde-fous ajoutés par cet audit

| Outil | Rôle | Config | Lancer en local |
|---|---|---|---|
| `vulture` 2.16 | Code mort backend | `fast_api_voter/pyproject.toml` `[tool.vulture]` + `.vulture_whitelist.py` | `cd fast_api_voter && python -m vulture api/ .vulture_whitelist.py --config pyproject.toml` |
| `knip` 6.x | Fichiers/exports/types/dépendances inutilisés frontend | `voter-app/knip.json` | `cd voter-app && npm run knip` |
| `jscpd` 5.x | Duplication cross-langage (Python + TS) | `.jscpd.json` (racine) | `npx jscpd --config .jscpd.json fast_api_voter/api voter-app/src` |
| `radon` 6.0.1 / `xenon` 0.9.3 | Complexité cyclomatique backend | flags CLI (pas de fichier dédié) | `cd fast_api_voter && python -m radon cc api/ -e "api/tests/*" -n C -s` |

**Câblage :**
- `scripts/audit.sh` (mode `--quality` ou complet) exécute les trois outils
  et ajoute leurs résultats à `audit-reports/SUMMARY.md`, **sans jamais faire
  échouer le script** sur ces trois-là (comportement identique à celui déjà
  en place pour les autres scanners informationnels du script).
- `.github/workflows/audit.yml` a un job **"Code Quality (dead code,
  duplication & complexity)"** qui tourne sur les mêmes triggers que le reste
  du workflow (push/PR main+develop, cron hebdo, merge queue), publie les
  résultats en résumé de run (`$GITHUB_STEP_SUMMARY`) et en artifact
  téléchargeable. Chaque outil individuel reste `continue-on-error: true`,
  mais **le job bloque désormais réellement** via deux gates ajoutés depuis
  l'édition d'août (voir §8, mis à jour) : `scripts/check_quality_ratchet.sh`
  compare les 4 compteurs à `.github/quality-baseline.json` et fait échouer
  le job si l'un d'eux **augmente** (la dette peut baisser, jamais grossir),
  et un second step fait échouer le job si la moyenne `xenon` retombe
  sous le rang A.
- **Volontairement absent de `.pre-commit-config.yaml`** : les hooks
  pre-commit actuels bloquent tous le commit ; ajouter ces trois outils là
  maintenant casserait l'expérience dev avant la passe de nettoyage. Voir
  "Critères de passage en mode bloquant" en fin de document.

---

## 3. Code mort

### Backend (vulture, `--min-confidence 80`)

**Mise à jour 2026-09-06 : les 2 findings ci-dessous sont corrigés — vulture
à `--min-confidence 80` remonte désormais 0 résultat**, ce qui correspond à
`"vulture": 0` dans `.github/quality-baseline.json`. Conservés ici pour
mémoire (les deux étaient les "quick wins" #1 et #2 du plan d'action, §7) :

| Fichier (à l'époque) | Finding | Statut |
|---|---|---|
| `api/domain/election/workers.py:1086` | Paramètre `ideology_variance` jamais utilisé dans `_run_district_fptp` | ✅ Corrigé — le paramètre alimente désormais le bruit du tirage (`_np.random.normal(0, ideology_variance)`) |
| `api/engine/utils/simulation_voting_utils.py:967` | Code inatteignable après un `return` (un `import json` + écriture d'un fichier debug) | ✅ Corrigé — la fonction se termine proprement au `return`, le code mort a été supprimé |

À confiance par défaut (60 %), vulture remonte ~800 résultats, mais
l'écrasante majorité (679 "unused variable") sont des **faux positifs
Enum** : les classes `IntEnum`/`Enum` de `api/domain/polity/codebook.py`,
`citizen.py`, etc. dont les membres sont consommés par itération
(`for x in EnumClass`) plutôt que par référence nommée — vulture ne sait
pas résoudre ce pattern. Le reste à 60 % contient un mélange de :
- **handlers FastAPI décorés** (`api/routes/election.py` — ~20 endpoints
  `@router.post(...)`) et **validators pydantic** (`api/domain/polity/llm_schemas.py`
  — `@field_validator`/`@model_validator`) : faux positifs, vulture ne voit
  pas l'enregistrement par décorateur (déjà filtrés par `ignore_decorators`
  dans la config ajoutée).
- **quelques fonctions génuinement mortes**, confirmées par recherche
  manuelle (zéro référence ailleurs dans le repo) :
  `api/domain/public.py:369 write_openapi_json`,
  `api/domain/simulations/advanced.py:299 _blank_wins_any`,
  `api/engine/population_simulation.py:54,62 simulate_population` /
  `generate_coord_candidates`,
  `api/engine/utils/demographic_data.py:106 sample_political_lean`,
  `api/engine/utils/simulation_score_utils.py:597 run_all_score_voting_methods`,
  `api/engine/utils/utils.py:105,135,171,227 bucklin_voting` /
  `two_round_system` / `schulze_method` / `score_voting` (à vérifier au cas
  par cas — certaines de ces implémentations de méthodes de vote peuvent
  être gardées intentionnellement comme référence/futur usage, à trancher
  avec l'équipe plutôt qu'à supprimer automatiquement).

### Frontend (knip)

**Mise à jour 2026-09-06 — chiffres recalculés (`npm run knip`, total 104,
== `.github/quality-baseline.json`).** Toutes les lignes de l'édition d'août
ont été traitées (voir §7) ; le tableau ci-dessous est un nouvel état, pas
une correction du précédent — la composition a changé (nouveaux fichiers
inutilisés apparus depuis, indépendants de cette passe de nettoyage) :

| Catégorie | Compte | Détail |
|---|---|---|
| Fichiers inutilisés | 9 | `components/research/BlankVoteTimeSeries.tsx`, `components/shared/EmptyChart.tsx`, `components/ui/{accordion,bootstrap-tabs,pagination,tabs,tooltip-overlay}.tsx`, `data/methodReferences.ts`, `services/index.ts` |
| Dépendances déclarées jamais importées | 1 | `@radix-ui/react-tabs` |
| Dépendances utilisées mais absentes de `package.json` | 0 | Corrigé : `d3-delaunay` est déclaré (`package.json`), `@eslint/js`/`globals` aussi — les 3 findings de l'édition d'août sont résolus |
| Exports jamais importés ailleurs | 1 valeur + 93 types | La valeur : `CardTitle` (`components/ui/card.tsx`). Les types viennent toujours majoritairement de `components/ui/*` (kit shadcn/ui) et de `src/api/index.ts`/`src/types.ts` (types larges générés/partagés, partiellement utilisés par construction) |
| Export dupliqué | 0 | Corrigé : `src/components/ui/instrument.tsx` n'exporte plus que `Instrument` en nommé |

**Priorité d'action suggérée :** aucun finding "risque réel" cette fois-ci
(la catégorie dépendance-non-déclarée est vide) — les 9 fichiers inutilisés
et la dépendance `@radix-ui/react-tabs` sont des suppressions sûres et
rapides. Les exports/types "inutilisés" du kit UI et des fichiers de types
larges restent à laisser tels quels sauf audit plus fin — faux positifs
structurels d'un pattern "bibliothèque de composants", comme en août.

---

## 4. Duplication (jscpd)

**Taux global (2026-09-06) : 0,64 % des lignes dupliquées** (641 lignes /
100 105 scannées, 34 clones — `.github/quality-baseline.json` fixe
`jscpd_clones` à 34), sur `fast_api_voter/api` + `voter-app/src` (tests,
fixtures, locales i18n et fichiers générés exclus de la mesure). En baisse
par rapport à l'édition d'août (0,81 %, 914/112 979, 49 clones) — la
suppression de l'arbre `Simulation/` mort a réduit les lignes scannées de
~13 000 sans ajouter de duplication neuve. C'est un taux bas — la
duplication littérale n'est pas le problème principal de ce repo.

Les clones ne sont pas dispersés aléatoirement : ils se concentrent presque
tous dans la famille de fichiers `api/domain/election/workers*.py`
(`workers.py`, `workers_advanced.py`, `workers_behavioral.py`,
`workers_dynamics.py`, `workers_mechanisms.py`, `workers_playground.py` —
6 fichiers, 7 851 lignes cumulées au 2026-09-06, était 7 250 en août) :

| Bloc dupliqué | Avec | Lignes |
|---|---|---|
| `election_service.py:77-92` | `workers.py:739-754` | 16 |
| `election_service.py:153-169` | `workers.py:222-233` | 17 |
| `workers_advanced.py:354-371` | `workers_advanced.py:1061-1078` (interne) | 18 |
| `workers_advanced.py:355-371` | `workers_behavioral.py:37-53` | 17 |
| `workers_behavioral.py:37-53` | `workers_behavioral.py:1217-1233` (interne) | 17 |
| `workers_behavioral.py:37-53` | `workers_dynamics.py:632-648` | 17 |
| `workers_behavioral.py:163-179` | `workers_behavioral.py:874-890` (interne) | 17 |
| `workers_behavioral.py:873-890` | `workers_behavioral.py:1362-1379` (interne) | 18 |
| `workers_dynamics.py:84-100` | `workers_mechanisms.py:646-662` | 17 |
| `workers_mechanisms.py:97-113` | `workers_mechanisms.py:648-664` (interne) | 17 |
| `workers_mechanisms.py:812-831` | `workers_mechanisms.py:1063-1082` (interne) | 20 |
| `simulation_ranked_utils.py:163-178` | `simulation_ranked_utils.py:982-997` (interne) | 16 |
| `routes/simulations.py:69-121` | `schemas/__init__.py:96-148` | 53 |

(Snapshot du 2026-09-06 — lignes recalculées après la suppression de l'arbre
`Simulation/`; deux des dix clones de l'édition d'août — `election_service.py`
vs `workers.py` — sont restés identiques au caractère près, les autres ont
simplement glissé de quelques lignes avec la croissance des fichiers
`workers*.py`.) Le clone `llm_client.py` (Ollama vs vLLM, §polity) de
l'édition d'août n'apparaît plus dans ce scan. Deux clones sont nouveaux
depuis août : un doublon interne dans `simulation_ranked_utils.py` (16
lignes, la famille `get_*_winner` déjà signalée en §5/§7) et un bloc de 53
lignes entre `routes/simulations.py` et `schemas/__init__.py` — le plus long
clone actuellement détecté dans le repo.

C'est une preuve concrète, pas seulement une intuition sur la taille des
fichiers : du code a bien été copié-collé **entre** ces fichiers workers
plutôt que factorisé, et `election_service.py` duplique de la logique déjà
présente dans `workers.py`.

**Note positive :** `voter-app/src/api/client.ts` (client typé généré) vs
`voter-app/src/services/*Api.ts` (wrappers domaine) **n'est pas** une
duplication — le fichier `client.ts` documente lui-même explicitement le
wrapper `apiPost`/`apiGet`/`apiDelete` comme "Legacy service-layer helper"
utilisé par les services historiques, pendant que les nouveaux appels
passent par le client typé directement. Bon exemple de dette assumée et
documentée plutôt que dupliquée en silence.

---

## 5. Complexité cyclomatique (radon/xenon)

**Moyenne globale saine : A (4.73) sur 1173 blocs analysés au 2026-09-06**
(`radon cc api/ -a`, tests exclus — était A (4.89) sur 1119 blocs en août ;
`radon_c_plus` reste à 137 dans `.github/quality-baseline.json`, inchangé)
— la complexité n'est pas un problème généralisé. Mais comme pour la
duplication (§4), les cas extrêmes ne sont pas dispersés au hasard : ils
confirment et affinent le même diagnostic de fragmentation architecturale.

**Les 6 fonctions les plus complexes du repo (rang F, la pire note radon) au
2026-09-06** — en baisse depuis les 9 de l'édition d'août : trois ont été
démontées en fonctions plus petites entre-temps (voir note sous le tableau) :

| Fichier | Fonction | Rang (score) |
|---|---|---|
| `api/domain/polity/indexer.py:266` | `index_events` | F (81) — la plus complexe de tout le repo, et en hausse (était F 70 en août) |
| `api/domain/theory/workers.py:1478` | `_democratic_backsliding_worker` | F (45) |
| `api/domain/election/workers.py:557` | `_interpret_worker` | F (44) |
| `api/domain/theory/workers.py:2159` | `_identity_voting_worker` | F (44) |
| `api/domain/polity/run_polity_simulation.py:1493` | `_run_accountability_phase` | F (44) |
| `api/sockets/__init__.py:91` | `start_monte_carlo` | F (41) |

**Amélioré depuis l'édition d'août** : `_power_indices_worker`
(`workers_advanced.py`, était F 59) est retombé à **B (8)** — un helper
`_pi_forbidden_pairs` en a été extrait — ; `_demographic_turnout_worker`
(`workers_advanced.py`, était F 53) est retombé à **B (7)** — de même avec un
`_dt_winner` extrait — ; `_liquid_democracy_worker` (`workers_behavioral.py`,
était F 44) est retombé à **C (19)**. À l'inverse, `index_events` a empiré
(F 70 → F 81) : c'est la seule fonction de la liste qui a grossi plutôt que
d'être découpée depuis l'édition d'août.

4 des 6 fonctions rang F restantes appartiennent à la même famille déjà
pointée en §4/§6 : les fichiers `workers*.py` (`election/workers.py`) et
`domain/theory/workers.py` / `domain/polity/run_polity_simulation.py`. Ce
n'est pas une coïncidence : ce sont les fichiers qui ont le plus grossi par
ajouts successifs sans passe de consolidation (voir aussi la taille en §6).
La duplication et la complexité sont deux symptômes du même mécanisme.

Au rang C (seuil d'attention, ~50 fonctions) domine un autre pattern, plus
bénin : les fonctions `get_*_winner` de
`api/engine/utils/simulation_ranked_utils.py` (17 fonctions rang C-D,
ex. `get_schulze_winner` D-29, `get_split_cycle_winner` D-27,
`get_nanson_winner` D-22). Complexité attendue pour des algorithmes de
dépouillement (Schulze, Split Cycle...) intrinsèquement branchus — pas un
signal de code à refactorer en priorité. Point notable : c'est exactement le
fichier ciblé par la baseline mutation-testing de la PR #157 (score ≈62 %),
et 9 de ces fonctions `get_*_winner` n'ont pas de test dédié — la complexité
mesurée ici recoupe indépendamment ce gap de test déjà identifié.

`xenon` tourne deux fois dans le job CI : une fois en rapport pur avec des
seuils permissifs (`-b F -m F -a F`, jamais d'échec, pour ne pas court-
circuiter les étapes suivantes du job en cas de crash), puis une seconde fois
en **gate réel** (`-b F -m F -a A`, ajouté depuis l'édition d'août) qui fait
échouer le job si la moyenne globale du repo retombe sous le rang A — la
moyenne actuelle (A, 4.73, §5 ci-dessus) passe avec de la marge. `-b`/`-m`
restent à F (jamais d'échec par bloc/module) tant que les 6 fonctions rang F
et les fonctions rang E n'ont pas été décomposées — voir §8 pour la suite
envisagée.

---

## 6. Autres odeurs "vibe coding"

- **Fichiers massifs** (candidats à un découpage) — comptes au 2026-09-06,
  tous en croissance depuis août sauf mention contraire :
  - Backend : `domain/polity/llm_behavior_engine.py` (2582 lignes, était
    2195), `domain/polity/run_polity_simulation.py` (1851, était 1520),
    `domain/election/workers_behavioral.py` (1849, était 1653),
    `domain/election/workers_advanced.py` (1519, était 1299),
    `domain/election/workers.py` (1486, était 1483 — stable),
    `domain/election/workers_mechanisms.py` (1171 — inchangé).
  - Frontend : `pages/AVousDeJouerPage.tsx` (1196 — inchangé),
    `lib/playgroundVoting.ts` (1133, était 1120),
    `stores/useElectionStore.tsx` (998 — inchangé, store React monolithique).
    `components/Simulation/VotingMethodVisualizations.tsx` (1109, cité en
    août) a été supprimé avec le reste de l'arbre `Simulation/` mort — ce
    candidat au découpage n'existe plus, il a été effacé en bloc.
- **`except Exception`/`except:` nu** : 42 occurrences dans le backend, hors
  tests (était 39 en août — légère hausse avec le code ajouté depuis).
  Pattern classique de LLM qui "protège" au lieu de traiter la cause ou de
  capturer une exception précise ; toujours pas de passe de centralisation
  faite (voir §7).
- **`components/shared/` à plat** : 66 fichiers `.tsx` sans sous-dossier
  thématique au 2026-09-06 (51 fichiers `*Panel.tsx` au total dans le repo) —
  en forte baisse depuis les 123/99 d'août, la suppression de l'arbre
  `Simulation/` ayant emporté au passage `MethodTooltip.tsx` et d'autres
  fichiers de ce dossier qui ne servaient qu'à la page morte. Le
  sous-dossier lui-même n'a pas été réorganisé par thème pour autant — le
  chantier §7 reste valable, juste sur un périmètre plus petit qu'en août.
- **Dette déjà documentée par l'équipe** :
  `fast_api_voter/scripts/polity_v2_consolidation_handoff.md` montre qu'une
  passe de consolidation sur `domain/polity/` a déjà été identifiée comme
  nécessaire après le merge de la v2 (PRs #120-122) — bon signal
  d'auto-conscience, à rapprocher du plan d'action ci-dessous plutôt qu'à
  refaire de zéro.
- **Signaux positifs** : zéro `TODO`/`FIXME`/`XXX`/`HACK` dans tout le code
  Python et TS, zéro `console.log` résiduel hors tests, zéro
  `eslint-disable`, zéro `print()` de debug backend. Le lint TS
  (`eslint`) et le typage (`tsc --noEmit`) passent tous les deux à 0 erreur
  au moment de cet audit.

---

## 7. Plan d'action priorisé

**Non exécuté dans cet audit** (scope = analyse + garde-fous, pas
refactor) — à traiter dans une passe de nettoyage dédiée.

**Quick wins (faible risque, haute confiance) — les 5 traitées le 2026-09-06 :**
1. ✅ Corriger `simulation_voting_utils.py:967` (code mort après `return`) —
   fait, la fonction se termine proprement au `return` (voir §3).
2. ✅ Décider du sort de `ideology_variance` dans `workers.py:1086` — fait,
   le paramètre est branché sur le bruit du tirage (voir §3).
3. ✅ Ajouter `d3-delaunay` à `voter-app/package.json` — fait, déclaré en
   dépendance directe.
4. ✅ Supprimer les 8 fichiers frontend inutilisés + les 2 dépendances
   mortes (`@radix-ui/react-label`, `@react-oauth/google`) — fait, les 10
   sont supprimés du repo (le nouveau lot de 9 fichiers/1 dépendance
   inutilisés en §3 est apparu indépendamment depuis, pas une régression sur
   ce point).
5. ✅ Trancher les fonctions backend à zéro référence
   (`write_openapi_json`, `_blank_wins_any`, `simulate_population`,
   `generate_coord_candidates`, `sample_political_lean`,
   `run_all_score_voting_methods`, `bucklin_voting`, `two_round_system`,
   `schulze_method`) — fait, les 9 fonctions ont été supprimées (aucune
   trace dans `api/` au 2026-09-06).

**Chantiers plus lourds (à planifier, pas à improviser en une PR) :**
1. Factoriser les blocs dupliqués identifiés en §4 entre les fichiers
   `workers*.py` et entre `election_service.py`/`workers.py`.
2. Évaluer une consolidation architecturale de `domain/election/workers*.py`
   (toujours 6 fichiers, 7 851 lignes cumulées au 2026-09-06, contre 7 250 en
   août) — probablement vers un découpage par responsabilité plutôt
   que par ordre chronologique d'ajout. Trois des 9 rangs F d'août ont déjà
   été démontés depuis (`_power_indices_worker`, `_demographic_turnout_worker`,
   `_liquid_democracy_worker` — voir §5) ; les 6 restants (dont 4 dans cette
   même famille de fichiers élargie) restent un bon point de départ concret
   pour prioriser la suite.
3. Réorganiser `components/shared/` (66 fichiers au 2026-09-06, en forte
   baisse depuis les 123 d'août — voir §6) en sous-dossiers thématiques.
4. Reprendre `polity_v2_consolidation_handoff.md` comme point de départ pour
   la consolidation de `domain/polity/`.
5. Centraliser la gestion d'erreurs pour réduire les `except Exception` nus
   (backend, 42 au 2026-09-06 — voir §6) — probablement via un décorateur ou
   un context manager partagé plutôt qu'un correctif fichier par fichier.
6. Ajouter les tests manquants pour les 9 fonctions `get_*_winner` de
   `simulation_ranked_utils.py` sans couverture dédiée (recoupement §5 /
   PR #157) avant de refactorer ce fichier — éviter de casser une méthode de
   vote silencieusement pendant le découpage.

---

## 8. Critères de passage en mode bloquant

**Mise à jour 2026-09-06 : cette section décrivait une décision de ne rien
bloquer, qui n'est plus la situation actuelle.** Depuis l'édition d'août,
`scripts/check_quality_ratchet.sh` a été ajouté au job `code-quality` : les 4
outils restent individuellement `continue-on-error`, mais le job **échoue
désormais réellement** si `vulture`/`radon`/`knip`/`jscpd` augmentent par
rapport à `.github/quality-baseline.json` (la dette peut baisser, jamais
grossir), et un second gate fait échouer le job si la moyenne `xenon` retombe
sous le rang A (voir §2 et §5). Les seuils "d'entrée en mode bloquant"
ci-dessous restent utiles comme prochaine étape (un seuil absolu plutôt
qu'un ratchet relatif), et certains sont déjà atteints en pratique :

- **vulture** : critère (0 finding à `--min-confidence 80`) **atteint** au
  2026-09-06 (voir §3) — pas encore promu en hook pre-commit bloquant (même
  modèle que `flake8`/`mypy` existants), qui reste l'étape suivante logique
  maintenant que le critère est rempli.
- **knip** : critère visé = dépendances "unused"/"unlisted" à 0. Au
  2026-09-06 : "unlisted" (utilisées mais non déclarées) est à 0 — corrigé
  depuis août ; "unused" (déclarées mais jamais importées) est à 1
  (`@radix-ui/react-tabs`, voir §3), donc pas encore tout à fait atteint.
  Les fichiers/exports inutilisés peuvent rester informationnels plus
  longtemps vu le volume de faux positifs structurels (kit UI, types larges).
- **jscpd** : pas de seuil de blocage global recommandé (le taux global est
  déjà bas, et a encore baissé depuis août — voir §4) — plutôt un
  `--ignore-pattern` ciblé une fois les clones de §4 résorbés, pour empêcher
  toute nouvelle duplication du même style dans `workers*.py`.
- **radon/xenon** : le gate "moyenne globale ≥ rang A" proposé ici est
  désormais en place (voir ci-dessus). Reste à envisager : une fois les 6
  fonctions rang F de §5 découpées sous D, resserrer `xenon` avec des seuils
  par bloc/module (`-b D -m D -a B` : aucun bloc pire que D, moyenne de
  module pire que D, moyenne globale pire que B) plutôt que la seule moyenne
  globale actuelle — qui laisse de la marge (A, 4.73) sans pénaliser les
  algorithmes de vote intrinsèquement branchus (`simulation_ranked_utils.py`).

---

## Reproduire cet audit

```bash
# Backend — code mort
cd fast_api_voter && python -m vulture api/ .vulture_whitelist.py --config pyproject.toml

# Backend — complexité cyclomatique
cd fast_api_voter && python -m radon cc api/ -e "api/tests/*" -n C -s
cd fast_api_voter && python -m radon cc api/ -e "api/tests/*" -a   # moyenne globale

# Frontend
cd voter-app && npm run knip

# Duplication cross-langage (depuis la racine)
npx jscpd --config .jscpd.json fast_api_voter/api voter-app/src

# Ou tout en un coup (résultats agrégés dans audit-reports/SUMMARY.md)
./scripts/audit.sh --quality
```
