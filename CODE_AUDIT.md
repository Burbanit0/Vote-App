# Audit code — code mort, duplication & garde-fous "vibe coding"

*Première édition : 2026-08-20. Section complexité cyclomatique (radon/xenon)
ajoutée le 2026-08-21. À relancer et mettre à jour après chaque passe de
nettoyage significative (voir "Prochaines étapes" en bas de page).*

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
(0,81 % des lignes scannées), le code mort détecté à haute confiance est
minime (2 cas backend, 8 fichiers frontend), et il n'y a ni `console.log`
oublié ni `eslint-disable` ni TODO/FIXME qui traînent. Le vrai risque n'est
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
| Tests | pytest (coverage ≥ 85 % en CI / ≥ 30 % en pre-push), vitest | les deux stacks | Oui |
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
- `.github/workflows/audit.yml` a un nouveau job **"Code Quality (dead code &
  duplication)"** qui tourne sur les mêmes triggers que le reste du workflow
  (push/PR main+develop, cron hebdo), publie les résultats en résumé de run
  (`$GITHUB_STEP_SUMMARY`) et en artifact téléchargeable, et **ne bloque
  jamais le job** (chaque étape est `continue-on-error: true`).
- **Volontairement absent de `.pre-commit-config.yaml`** : les hooks
  pre-commit actuels bloquent tous le commit ; ajouter ces trois outils là
  maintenant casserait l'expérience dev avant la passe de nettoyage. Voir
  "Critères de passage en mode bloquant" en fin de document.

---

## 3. Code mort

### Backend (vulture, `--min-confidence 80`)

À confiance ≥ 80 %, vulture ne remonte que 2 résultats après filtrage des
faux positifs (dunder-methods `__exit__`, signatures `**kwargs` partagées —
tous documentés et whitelistés dans `.vulture_whitelist.py`) :

| Fichier | Finding | Analyse |
|---|---|---|
| `api/domain/election/workers.py:1086` | Paramètre `ideology_variance` jamais utilisé dans `_run_district_fptp` | Réel — soit le paramètre doit être branché, soit supprimé de la signature |
| `api/engine/utils/simulation_voting_utils.py:967` | Code inatteignable après un `return` (un `import json` + écriture d'un fichier debug) | Réel — code de debug oublié, jamais exécuté |

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

| Catégorie | Compte | Détail |
|---|---|---|
| Fichiers inutilisés | 8 | `components/shared/PoliticalClusterMap.tsx`, `components/Simulation/InformationModelPanel.tsx`, `components/ui/{dialog,input,label}.tsx`, `data/quizQuestions.ts`, `services/whatIfApi.ts`, `theme/index.ts` |
| Dépendances déclarées jamais importées | 2 | `@radix-ui/react-label`, `@react-oauth/google` |
| Dépendances utilisées mais absentes de `package.json` | 3 | `d3-delaunay` (import réel dans `src/utils/voronoiRegions.ts:7` — **risque réel**, ne fonctionne aujourd'hui que parce qu'un autre paquet le tire en transitif), `@eslint/js` et `globals` (utilisés uniquement dans `eslint.config.js`, risque plus faible car dev-only) |
| Exports jamais importés ailleurs | 47 valeurs + 108 types | Beaucoup viennent de `components/ui/*` (kit shadcn/ui — normal qu'une partie de la surface d'un kit de composants ne soit pas utilisée partout, faible priorité) et de `src/types.ts`/`src/api/types.gen.ts` (types larges, partiellement utilisés par construction) |
| Export dupliqué | 1 | `src/components/ui/instrument.tsx` exporte à la fois `Instrument` nommé et en `default` |

**Priorité d'action suggérée :** `d3-delaunay` en dépendance non déclarée
est le finding le plus risqué de cette section (build cassé possible dès que
la résolution transitive change) — à corriger en premier. Les 8 fichiers
inutilisés et les 2 dépendances vraiment mortes sont des suppressions sûres
et rapides. Les exports/types "inutilisés" du kit UI et des fichiers de
types larges sont à laisser tels quels sauf audit plus fin — ce sont des
faux positifs structurels d'un pattern "bibliothèque de composants".

---

## 4. Duplication (jscpd)

**Taux global : 0,81 % des lignes dupliquées** (914 lignes / 112 979
scannées, 49 clones), sur `fast_api_voter/api` + `voter-app/src` (tests,
fixtures, locales i18n et fichiers générés exclus de la mesure). C'est un
taux bas — la duplication littérale n'est pas le problème principal de ce
repo.

Les clones ne sont pas dispersés aléatoirement : ils se concentrent presque
tous dans la famille de fichiers `api/domain/election/workers*.py`
(`workers.py`, `workers_advanced.py`, `workers_behavioral.py`,
`workers_dynamics.py`, `workers_mechanisms.py`, `workers_playground.py` —
6 fichiers, 7 250 lignes cumulées) et dans `api/domain/polity/llm_client.py` :

| Bloc dupliqué | Avec | Lignes |
|---|---|---|
| `election_service.py:77-92` | `workers.py:739-754` | 16 |
| `election_service.py:153-169` | `workers.py:222-233` | 17 |
| `workers_advanced.py:253-270` | `workers_advanced.py:917-934` (interne) | 18 |
| `workers_advanced.py:254-270` | `workers_behavioral.py:161-177` | 17 |
| `workers_behavioral.py:35-51` | `workers_behavioral.py:342-358`, `1133-1149` (interne, x2) | 17 |
| `workers_behavioral.py:35-51` | `workers_dynamics.py:632-648` | 17 |
| `workers_behavioral.py:161-177` | `workers_behavioral.py:789-806` (interne) | 17 |
| `workers_dynamics.py:84-100` | `workers_mechanisms.py:646-662` | 17 |
| `workers_mechanisms.py:97-113` | `workers_mechanisms.py:648-664` (interne) | 17 |
| `llm_client.py:210-228` | `llm_client.py:360-378` (interne — client Ollama vs vLLM) | 19 |

C'est une preuve concrète, pas seulement une intuition sur la taille des
fichiers : du code a bien été copié-collé **entre** ces fichiers workers
plutôt que factorisé, et `election_service.py` duplique de la logique déjà
présente dans `workers.py`. `llm_client.py` a deux classes clientes quasi
identiques (Ollama / vLLM) qui partagent un bloc de 19 lignes non factorisé.

**Note positive :** `voter-app/src/api/client.ts` (client typé généré) vs
`voter-app/src/services/*Api.ts` (wrappers domaine) **n'est pas** une
duplication — le fichier `client.ts` documente lui-même explicitement le
wrapper `apiPost`/`apiGet`/`apiDelete` comme "Legacy service-layer helper"
utilisé par les services historiques, pendant que les nouveaux appels
passent par le client typé directement. Bon exemple de dette assumée et
documentée plutôt que dupliquée en silence.

---

## 5. Complexité cyclomatique (radon/xenon)

**Moyenne globale saine : A (4.89) sur 1119 blocs analysés** (`radon cc
api/ -a`, tests exclus) — la complexité n'est pas un problème généralisé.
Mais comme pour la duplication (§4), les cas extrêmes ne sont pas dispersés
au hasard : ils confirment et affinent le même diagnostic de fragmentation
architecturale.

**Les 9 fonctions les plus complexes du repo (rang F, la pire note radon) :**

| Fichier | Fonction | Rang (score) |
|---|---|---|
| `api/domain/polity/indexer.py:232` | `index_events` | F (70) — la plus complexe de tout le repo |
| `api/domain/election/workers_advanced.py:1120` | `_power_indices_worker` | F (59) |
| `api/domain/election/workers_advanced.py:34` | `_demographic_turnout_worker` | F (53) |
| `api/domain/theory/workers.py:1478` | `_democratic_backsliding_worker` | F (45) |
| `api/domain/polity/run_polity_simulation.py:1181` | `_run_accountability_phase` | F (44) |
| `api/domain/election/workers.py:557` | `_interpret_worker` | F (44) |
| `api/domain/election/workers_behavioral.py:335` | `_liquid_democracy_worker` | F (44) |
| `api/domain/theory/workers.py:2159` | `_identity_voting_worker` | F (44) |
| `api/sockets/__init__.py:88` | `start_monte_carlo` | F (41) |

7 des 9 fonctions rang F appartiennent à la même famille déjà pointée en
§4/§6 : les fichiers `workers*.py` (`workers.py`, `workers_advanced.py`,
`workers_behavioral.py`) et `domain/theory/workers.py` /
`domain/polity/run_polity_simulation.py`. Ce n'est pas une coïncidence : ce
sont les fichiers qui ont le plus grossi par ajouts successifs sans passe de
consolidation (voir aussi la taille en §6). La duplication et la complexité
sont deux symptômes du même mécanisme.

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

`xenon` tourne en parallèle avec des seuils volontairement permissifs
(`-b F -m F -a F`, jamais d'échec) : à ce stade c'est un rapport, pas une
porte — voir §8 pour les seuils envisagés une fois le backlog résorbé.

---

## 6. Autres odeurs "vibe coding"

- **Fichiers massifs** (candidats à un découpage) :
  - Backend : `domain/polity/llm_behavior_engine.py` (2195 lignes),
    `domain/polity/run_polity_simulation.py` (1520),
    `domain/election/workers_behavioral.py` (1653),
    `domain/election/workers.py` (1483),
    `domain/election/workers_advanced.py` (1299),
    `domain/election/workers_mechanisms.py` (1171).
  - Frontend : `pages/AVousDeJouerPage.tsx` (1196),
    `lib/playgroundVoting.ts` (1120),
    `components/Simulation/VotingMethodVisualizations.tsx` (1109),
    `stores/useElectionStore.tsx` (998 — store React monolithique).
- **`except Exception`/`except:` nu** : 39 occurrences dans le backend, hors
  tests, concentrées dans `domain/simulations/compare.py` (7),
  `domain/simulations/base.py` (4), `engine/utils/cache.py` (3). Pattern
  classique de LLM qui "protège" au lieu de traiter la cause ou de capturer
  une exception précise.
- **`components/shared/` à plat** : 123 fichiers `.tsx` sans sous-dossier
  thématique (99 fichiers `*Panel.tsx` au total dans le repo). Chaque
  nouveau concept de simulation a généré un nouveau composant dans ce même
  dossier plutôt que d'être rangé par thème (comportemental, électoral,
  institutionnel...). Pas un problème de code mort ni de duplication en soi,
  mais un coût de navigation et un signal que le rangement n'a jamais suivi
  la croissance.
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

**Quick wins (faible risque, haute confiance) :**
1. Corriger `simulation_voting_utils.py:967` (code mort après `return`).
2. Décider du sort de `ideology_variance` dans `workers.py:1086`.
3. Ajouter `d3-delaunay` à `voter-app/package.json` (dépendance non
   déclarée réellement utilisée en prod).
4. Supprimer les 8 fichiers frontend inutilisés + les 2 dépendances mortes
   (`@radix-ui/react-label`, `@react-oauth/google`).
5. Trancher les fonctions backend à zéro référence
   (`write_openapi_json`, `_blank_wins_any`, `simulate_population`,
   `generate_coord_candidates`, `sample_political_lean`,
   `run_all_score_voting_methods`, `bucklin_voting`, `two_round_system`,
   `schulze_method`) : suppression ou re-rattachement à une route/un test.

**Chantiers plus lourds (à planifier, pas à improviser en une PR) :**
1. Factoriser les blocs dupliqués identifiés en §4 entre les fichiers
   `workers*.py` et entre `election_service.py`/`workers.py`.
2. Évaluer une consolidation architecturale de `domain/election/workers*.py`
   (6 fichiers, 7 250 lignes) — probablement vers un découpage par
   responsabilité plutôt que par ordre chronologique d'ajout. Les 9 rangs F
   de §5 (dont 5 dans cette même famille de fichiers) sont un bon point de
   départ concret pour prioriser quelles fonctions découper en premier.
3. Réorganiser `components/shared/` (123 fichiers) en sous-dossiers
   thématiques.
4. Reprendre `polity_v2_consolidation_handoff.md` comme point de départ pour
   la consolidation de `domain/polity/`.
5. Centraliser la gestion d'erreurs pour réduire les 39 `except Exception`
   nus (backend) — probablement via un décorateur ou un context manager
   partagé plutôt qu'un correctif fichier par fichier.
6. Ajouter les tests manquants pour les 9 fonctions `get_*_winner` de
   `simulation_ranked_utils.py` sans couverture dédiée (recoupement §5 /
   PR #157) avant de refactorer ce fichier — éviter de casser une méthode de
   vote silencieusement pendant le découpage.

---

## 8. Critères de passage en mode bloquant

Décision déjà actée : ne pas rendre `vulture`/`knip`/`jscpd`/`radon`/`xenon`
bloquants tant que le backlog actuel n'est pas résorbé. Suggestion de seuils
pour franchir cette étape (à ajuster selon rythme de nettoyage réel) :

- **vulture** : 0 finding restant à `--min-confidence 80` → ajouter comme
  hook pre-commit bloquant (même modèle que `flake8`/`mypy` existants).
- **knip** : dépendances "unused"/"unlisted" à 0 (le plus urgent — un build
  cassé est un vrai risque) avant de bloquer sur les fichiers/exports
  inutilisés, qui peuvent rester informationnels plus longtemps vu le volume
  de faux positifs structurels (kit UI, types larges).
- **jscpd** : pas de seuil de blocage global recommandé (le taux global est
  déjà bas) — plutôt un `--ignore-pattern` ciblé une fois les clones de §4
  résorbés, pour empêcher toute nouvelle duplication du même style dans
  `workers*.py`.
- **radon/xenon** : une fois les 9 fonctions rang F de §5 découpées sous D,
  passer `xenon` en bloquant avec des seuils lâches
  (`-b D -m D -a B` : aucun bloc pire que D, moyenne de module pire que D,
  moyenne globale pire que B) plutôt qu'un seuil strict d'emblée — la
  moyenne globale actuelle (A, 4.89) laisse de la marge sans pénaliser les
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
