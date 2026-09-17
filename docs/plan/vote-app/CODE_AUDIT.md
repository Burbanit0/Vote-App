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

*Mise à jour du 2026-09-08 : `flake8` remplacé par `ruff` (Lot 1 du
[plan de solidité technique](PLAN_SOLIDITE_TECHNIQUE.md)) — même périmètre
exact (pyflakes uniquement, pas de règle de style/complexité), configuré
dans `fast_api_voter/pyproject.toml`. Les mentions de `flake8` ci-dessous
restent comme trace historique de l'audit d'origine ; le lint réel tourne
désormais sous `ruff check fast_api_voter`.*

*Mise à jour du 2026-09-09 : `deptry` ajouté au cliquet (Lot 2 du plan de
solidité technique — équivalent Python de `knip`, dépendances déclarées-
mais-inutilisées / utilisées-mais-non-déclarées). Scope volontairement
limité à `fast_api_voter/api/` (`scripts/` — la harness LLM polity — en est
exclu, comme `api/tests/` par design de l'outil). Baseline : 0 trouvaille.
Effet de bord : a révélé `ruff`/`pytest`/`pytest-asyncio`/`pytest-cov`
dupliqués dans `requirements.txt` (production) alors qu'ils n'appartiennent
qu'à `requirements-dev.txt` — retirés, et `fast_api_voter/Dockerfile` (image
dev, utilisée par `scripts/bootstrap.sh` pour lancer `pytest` en conteneur)
installe désormais aussi `requirements-dev.txt` en conséquence.*

*`madge` ajouté le même jour (imports circulaires côté frontend +
visualisation du graphe) — informationnel uniquement, pas dans le cliquet
(`npm run madge:circular` dans `voter-app`, ou `scripts/audit.sh --quality`).
Une trouvaille : un cycle `import type` entre `hooks/useSimulationWorker.ts`
et `components/Simulation/IdeologyHeatmap.tsx` — bénin (les imports
`type`-only sont éliminés à la compilation, aucun risque d'exécution), pas
corrigé.*

*`import-linter` ajouté le même jour (Lot 2) — contrat `layers`
`routes → domain → engine` du skill `voter-api`, désormais bloquant en CI.
0 violation trouvée (déjà propre).*

*Règles Semgrep custom ajoutées le même jour (Lot 2,
`.semgrep/vote-app-rules.yml`, bloquantes) : `v2-router-missing-rate-limit`
a trouvé 3 routers `/api/v2` (`tech`, `theory`, `export`) sans aucune limite
de débit — corrigé en leur ajoutant la dépendance `check_v2_rate_limit` déjà
utilisée par `election`/`simulations`. `except-exception-without-log` a
trouvé 18 `except Exception` muets sur 9 fichiers — corrigés en ajoutant un
appel `log.*(..., exc_info=True)` à chacun, sur le modèle déjà établi
ailleurs dans le code. Les deux corrections sont vérifiées par les 1789
tests backend + mypy + ruff + un run e2e complet (218 tests, 0 flake).*

*`dependency-cruiser` ajouté le même jour (Lot 2) — équivalent frontend
d'`import-linter` : `src/lib` (libs pures, voir CLAUDE.md — section
Playground) ne doit jamais importer depuis `src/components`/`src/pages`,
règle `lib-is-pure` désormais bloquante en CI (`.dependency-cruiser.json`,
imports type-only exemptés). Baseline : 0 violation (287 modules, 1558
dépendances). Épinglé en `17.4.3` : la `18.x` exige Node `^22||^24||>=26`, ce
repo (CI et dev local) tourne encore en Node 20.*

*Mise à jour du 2026-09-10 : `Schemathesis` ajouté (Lot 3 du plan de solidité
technique) — fuzzing du contrat OpenAPI, `api/tests/test_schema_contract.py` +
workflow dédié `schemathesis.yml` (pas dans `backend-ci-cd-pipeline.yml` par
prudence : un run complet mesure ~220s (~3.5-4 min) en local, mais ce chiffre n'a pas été
revérifié sur un runner GitHub réel — voir le docstring du fichier de test
pour le détail des choix : mode POSITIVE uniquement, entiers lourds
plafonnés à 100, pas de phase de shrink ; génération rendue reproductible via
un `seed=` fixe sur le `Config` schemathesis — `derandomize=True` seul ne
suffisait pas d'un process à l'autre, `PYTHONHASHSEED` non fixé fausse la
dérivation de graine de Hypothesis). Écrire le test a immédiatement trouvé et
corrigé 6 bugs réels : des codes de statut atteignables mais jamais
documentés (400/404/500/503) sur les 7 routers de l'API (corrigé via
`responses=` + un schéma `ErrorDetail` partagé) ; un crash `IndexError` sur
`/theory/identity-voting` (le schéma acceptait 2 candidats, le worker en
exige 3 sans le vérifier) ; un crash `max() iterable argument is empty` sur
`/assembly`, `/assembly-scorecard`, `/temporal` et `/structural-fairness`
quand deux partis partagent le même nom (collision de clé dans un dict
agrégé par nom — corrigé par un `field_validator` Pydantic rejetant les
doublons, plus sûr que de rendre le code d'agrégation tolérant aux
collisions) ; un crash `TypeError`/`IndexError` sur `/campaign-sensitivity`
(`snapshot_days` typé `List[Any]` au lieu de `List[Union[int, Literal["final"]]]`,
et un jour négatif de grande magnitude débordait l'indexation Python faute
d'être borné des deux côtés) ; un crash `AttributeError` sur
`/choice-overload` (`heuristic_weights` explicitement `null` contournait le
défaut de `.get()` — corrigé en `or {}`) ; un crash `AttributeError` sur
`/tech/polis` (le schéma promet `List[str]`, le worker traitait chaque
élément comme un dict — corrigé pour accepter les deux formes). Le reste des
endpoints (~40 sur 95) porte de la dette pré-existante réelle mais
volontairement non corrigée dans ce lot — requêtes historiquement peu typées
(`Dict[str, Any]`, voir `api/schemas/simulations.py`) et endpoints de
simulation dont le temps de réponse dépasse le timeout de 10s même avec des
paramètres bridés — trackée nommément (pas un simple compte) dans
`KNOWN_FAILURES`, avec la classe de problème pour chacune. Le deuxième point
(timeouts) est exactement pourquoi l'item "Timeouts & backpressure" existe
plus loin dans le même lot.*

*Mise à jour du 2026-09-10 (bis) : régression `jscpd` (33→34 clones) trouvée
et corrigée pendant le Lot 4.2 (oracle tiers `pref_voting`) — corriger un bug
Raynaud (voir plus loin) a fait apparaître le même calcul de "pire défaite
pairwise" en double entre `winRaynaud` (`playgroundVoting.ts`) et sa trace de
rejeu (`voteTrace.ts`), auparavant trop différents structurellement pour que
`jscpd` les détecte. Factorisé dans `raynaudWorstLoss`, exportée et partagée
par les deux — cliquet revenu à 33 sans rien laisser en dette.*

*Mise à jour du 2026-09-12 : le lot "code mort frontend" resté ouvert depuis
le 2026-09-06 (§3/§7) est traité — les 9 fichiers inutilisés
(`components/research/BlankVoteTimeSeries.tsx`, `components/shared/EmptyChart.tsx`,
`components/ui/{accordion,bootstrap-tabs,pagination,tabs,tooltip-overlay}.tsx`,
`data/methodReferences.ts`, `services/index.ts`), la dépendance
`@radix-ui/react-tabs` et l'export inutilisé `CardTitle`
(`components/ui/card.tsx` — le composant lui-même n'était référencé nulle
part ailleurs, supprimé en entier plutôt que juste dé-exporté) sont
supprimés. Même passe : l'orphelin trouvé par le Lot 6.5 du plan de
solidité technique, le hook `hooks/useDebouncedSimulation.ts` (+ son test) —
plus aucun appelant vivant depuis que sa route `/simulation/compare` a été
retirée (voir Lot 14 du plan de solidité technique pour le détail des deux
zones mortes tranchées dans ce lot, dont celle-ci n'est qu'une moitié).
`npm run knip` passe de 104 à 93 trouvailles (uniquement des "unused exported
types" du kit UI et des fichiers de types larges, déjà notés en §3 comme
faux positifs structurels) ; `.github/quality-baseline.json` mis à jour en
conséquence (`knip: 104 → 93`) — le cliquet `check_quality_ratchet.sh` fait
échouer une baisse non enregistrée tout autant qu'une hausse, il faut donc
la committer explicitement, pas seulement laisser passer. `vulture`/`radon`/
`deptry`/`jscpd` inchangés (0/137/0/33). Gate frontend complet
(`tsc --noEmit`, `vitest run` — 168 fichiers/1707 tests, `lint`, `build` +
`size-limit`) vérifié vert après suppression.*

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

*Mise à jour du 2026-09-12 (Lot 13, [plan de solidité technique](PLAN_SOLIDITE_TECHNIQUE.md)
— rejeu après les Lots 7 à 12) : outils relancés à l'identique de l'édition
du 2026-09-06 pour comparaison directe. Verdict : **stable, malgré un volume
de changement important** entre les deux éditions (WebKit e2e, perf backend/
frontend, sécurité approfondie — fuzzing, SBOM, DAST —, observabilité complète
— GlitchTip, OpenTelemetry, Prometheus —, 5 nouveaux agents et 3 nouvelles
skills Claude Code, hygiène de contexte). Sur les 5 métriques du cliquet
(`scripts/check_quality_ratchet.sh`) : `vulture` (0), `radon` fonctions C+
(137), `jscpd` (33 clones) strictement identiques ; `deptry` et `knip`
momentanément régressés puis corrigés dans la même passe, pas laissés en
dette :
- **`deptry`** : 2 trouvailles réelles, toutes deux du Lot 10. `prometheus_client`
  importé directement dans `api/routes/metrics.py` mais jamais déclaré
  explicitement (reposait sur le pin transitif de `prometheus-fastapi-
  instrumentator`) — corrigé en l'ajoutant à `requirements.txt` avec sa
  version réellement résolue (`0.26.0`). `opentelemetry-instrumentation-
  fastapi` signalé "défini mais inutilisé" — faux positif confirmé (deptry
  ne résout pas le mapping du nom PyPI vers le module imbriqué
  `opentelemetry.instrumentation.fastapi`) — corrigé via
  `[tool.deptry.package_module_name_map]`, pas par un `per_rule_ignores`
  qui aurait juste caché le signal.
- **`knip`** : 2 "Configuration hints" (pas du code mort) — `scripts/
  gen-pseudo-locale.ts` et `jiti` n'avaient plus besoin d'être dans
  `ignore`/`ignoreDependencies` de `voter-app/knip.json` : la commande
  `npm run gen:pseudo-locale` (ajoutée au Lot 7) suffit à elle seule à ce
  que knip les reconnaisse comme utilisés. Entrées retirées, revérifié
  qu'aucun des deux ne réapparaît comme trouvaille réelle après coup.

Aucune des deux régressions n'était visible dans `scripts/audit.sh
--quality`'s propre synthèse (`audit-reports/SUMMARY.md`) : ce script
rapporte des sous-métriques différentes (ex. "Unused files" plutôt que la
somme totale que `check_quality_ratchet.sh` calcule) — seul le script de
cliquet lui-même, relancé avec les mêmes fichiers de rapport que la CI
(`fast_api_voter/{vulture,radon,deptry}.txt`, `voter-app/knip.txt`,
`jscpd.txt`), donne un nombre directement comparable à la baseline.*

*Mise à jour du 2026-09-12 (bis) — §7 "chantiers plus lourds" item 6 traité
(tests manquants pour la famille `get_*_winner`). Le chiffre "9" cité dans
cet item (et en §5) s'est révélé stale : il correspondait à une heuristique
par nom de fichier (`test_<méthode>.py` existe-t-il ?), qui compte à tort
`irv`/`coombs` (`test_irv_coombs_elimination.py`), `bucklin`
(`test_bucklin_cumulative.py`), `schulze` (`test_schulze_beatpath.py`) et
`ranked_pairs`/`random_ballot` (`test_ranked_pairs_random_ballot.py`) comme
non couverts alors que chacun a un vrai test dédié (appel direct, assertion
sur un gagnant précis), juste sous un nom de fichier différent ou partagé
entre deux méthodes apparentées. Re-dérivé fonction par fonction (grep
croisé sur `api/tests/`, plus `--cov-report=term-missing` sur
`simulation_ranked_utils.py`) : seules **3** fonctions n'avaient réellement
aucun test dédié — `get_borda_winner` (seulement exercée en comparaison
incidentelle dans `test_black.py`/`test_dowdall.py` et dans l'axiome §5),
`get_positional_score_winner` (zéro test de
toute nature, y compris dans `test_voting_criteria_matrix.py`, alors que
c'est du code de production réel — appelé, depuis la PR 8b, par le seul
`gibbard_satterthwaite.py` : `domain/simulations/base.py` et
`arrow_criteria.py` ont été supprimés en PR 2, et l'alias `get_score_winner`
en PR 8b), et
`get_approval_winner_sincere` (le mode de vote sincère par seuil
d'utilité — la branche correspondante dans `get_approval_winner`,
lignes ~276-298, n'avait elle-même aucune couverture, pas seulement le
wrapper). Tests ajoutés : `api/tests/test_borda.py` et
`api/tests/test_positional_score.py` (nouveaux), plus une classe
`TestGetApprovalWinnerSincere` dans `api/tests/test_approval.py` — majorité
claire, égalité alphabétique, ballots vides/à un candidat, et pour Borda et
positional-score un cas construit à la main qui les distingue explicitement
l'un de l'autre (et de la pluralité) plutôt que de se contenter de vérifier
"retourne une string". Couverture de `simulation_ranked_utils.py` : 94 % →
96 % (`--cov-report=term-missing`, 41 → 28 lignes manquantes). Aucun bug
trouvé dans l'implémentation existante par cette passe. Détail complet
(liste re-dérivée, gap "axiome" flagué séparément) dans le rapport de la
session correspondante ; §7 lui-même annoté "✅" ci-dessous.*

*Mise à jour du 2026-09-12 (ter) — §7 "chantiers plus lourds" item 5 traité
(centraliser les `except Exception` nus). Liste re-dérivée à la main (grep +
lecture du contexte réel, pas juste la ligne `except`) plutôt que réutiliser
le chiffre "42" tel quel : deux formes dominantes se sont dégagées, ni
identiques ni couvrant tout le lot.
- **"Compute with fallback"** (15 sites) — une valeur est calculée, et un
  défaut la remplace en cas d'échec pendant que l'appelant continue (ou
  retourne le défaut directement) : `gibbard_satterthwaite.py` (×2),
  `cache.py` (×1 sur 3), `campaign_dynamics.py`, `routes/health.py`,
  `workers_mechanisms.py`, `workers_advanced.py` (×2),
  `workers_behavioral.py` (×7). Centralisé dans une fonction utilitaire
  `safe_call(fn, fallback, *, log, event, level="warning", **log_kwargs)`
  (nouveau module `api/engine/utils/error_handling.py`) — `fn` et `fallback`
  sont deux callables sans argument (typiquement des `lambda:`) : le
  fallback n'est **jamais évalué en cas de succès**, ce que le code
  d'origine faisait déjà à plusieurs endroits (ex. `campaign_dynamics.py`,
  où le fallback est un second appel réel au moteur, pas une simple
  constante) et qu'une valeur par défaut passée telle quelle aurait cassé.
- **"Handler wrapping"** (18 sites) — le contrat `(body, status)` des
  workers (convention `voter-api`) : sur échec, la même exception log +
  réponse d'erreur. Centralisé dans `log_and_error_response(log, event,
  body, *, level="error", status=500, **log_kwargs)`, appelée **depuis
  l'intérieur** du `except Exception as exc:` déjà existant — elle ne
  remplace que le duo log-call + return, jamais le try/except lui-même.
  Un décorateur enveloppant toute la fonction (suggestion initiale de cet
  item) a été essayé puis abandonné après lecture attentive des sites
  réels : la quasi-totalité de ces workers valide/parse des paramètres
  *avant* le `try` (avec parfois son propre `except (TypeError, ValueError)`
  séparé) ou exécute du code *après* le `except` — un décorateur enveloppant
  toute la fonction aurait élargi silencieusement la portée de ce qui est
  intercepté (un `ValueError` de parsing aujourd'hui non couvert deviendrait
  couvert), un vrai changement de comportement, pas un refactor pur. D'où
  une fonction plus modeste appelée *depuis* le bloc `except` existant,
  jamais à sa place. `body` est fourni tel quel par l'appelant (pas
  reconstruit par l'utilitaire) : certains sites retournent `{"error":
  ...}`, d'autres un triplet `{"success": False, "error": ..., "message":
  ...}` (`domain/simulations/base.py`) — préserver le contenu exact prime
  sur une signature plus générique.
- **Laissés tels quels (9 sites), avec raison** — aucun des deux utilitaires
  ne leur va sans soit changer le comportement, soit ajouter plus de code
  qu'il n'en retire : `cache.py` (2 des 3 sites — l'un enchaîne un retour
  anticipé en cas de succès et un `except` partagé entre deux instructions,
  l'autre est un `try/except` de 3 lignes déjà minimal, écrire le `lambda`
  n'aurait rien réduit) ; `sockets/__init__.py` (boucle async qui notifie le
  client ET arrête la boucle — pas juste une valeur de repli) ;
  `domain/polity/llm_client.py` (×2) et `domain/polity/run_polity_simulation.py`
  (×1) — style "best-effort, log et continue" déjà documenté comme
  volontaire, mais via `logging.getLogger` %-style embarquant l'exception
  dans le message plutôt que le style structlog `event, **kwargs` du reste
  de `api/` ; **découverte incidente** : ces 3 sites logguent bien (la règle
  Semgrep `except-exception-without-log` les voit), mais **sans**
  `exc_info=True` — contrairement à ce que l'énoncé de cet item supposait
  ("tous les 42 sites logguent déjà avec exc_info=True"), ce n'est vrai que
  pour 39/42. Non corrigé ici (refactor de duplication, pas de gap
  d'observabilité — distinct, à traiter séparément) ; `domain/simulations/
  whatif.py` (1 site) et `domain/simulations/compare.py` (2 sites) —
  accumulation de résultat partiel dans une boucle (`log.warning` +
  `results.append(<repli propre au site>)` + `continue`), avec une forme de
  repli différente à chaque site : ni `safe_call` (le repli n'est pas une
  valeur réutilisée, c'est un item de liste au format bespoke) ni
  `log_and_error_response` (pas de `return`) ne réduisent quoi que ce soit
  ici sans forcer la forme.
- **Chiffres avant/après** : `grep -rn "except Exception" fast_api_voter/api/
  --include="*.py" | grep -v "/tests/" | wc -l` donne **35** après (42 avant)
  — mais ce chiffre brut compte aussi 6 mentions de prose dans le docstring
  du nouveau module (qui *documente* le motif "except Exception", donc le
  contient littéralement). Le compte réel de clauses `except Exception`
  fonctionnelles est **29** (35 − 6) : les 18 sites "handler wrapping" et les
  9 sites laissés tels quels gardent chacun leur propre clause (27), plus
  **une seule** clause partagée à l'intérieur de `safe_call` — qui remplace
  ce qui était 15 clauses dupliquées. Nouveau module + tests dédiés
  (`api/tests/test_error_handling.py`, 16 tests) ; 4 sites parmi les 18
  "handler wrapping" n'avaient aucun test exerçant leur chemin d'erreur
  (`domain/simulations/advanced.py`, `base.py`, `compare.py`, `campaign.py`)
  — un test de repli par fichier touché ajouté, pas les 18 (refactor, pas
  chantier de couverture). Suite backend complète, mypy, ruff et la règle
  Semgrep custom (mise à jour pour reconnaître les deux nouveaux appels comme
  un "log call" valide — sinon le job Semgrep gating de `audit.yml` aurait
  régressé sur les 18 sites "handler wrapping") tous verts.*

*Mise à jour du 2026-09-12 (quater) — §7 "chantiers plus lourds" item 1
traité (déduplication des clones jscpd entre `workers*.py`/
`election_service.py`, plus le doublon interne à `simulation_ranked_utils.py`).
Le chiffre du §4 avait déjà glissé depuis la dernière mesure (passes RNG et
refurb/perflint récentes ont déplacé des lignes) — re-dérivé avec
`npx jscpd --config .jscpd.json fast_api_voter/api voter-app/src` avant de
toucher quoi que ce soit : 13 clones backend sur les 32 totaux, tous dans le
cluster ciblé, les 19 autres (frontend `components/`/`lib/`) volontairement
laissés de côté (hors périmètre de cet item).

Lire le code réel derrière chaque paire a montré qu'il ne s'agissait pas de
13 problèmes indépendants mais de **5 blocs canoniques** copiés-collés
chacun dans plusieurs fichiers, plus un sixième découvert pendant
l'extraction elle-même (voir plus bas) :

1. **Le bloc de parsing `blank_vote`/`information_model`/`campaign`**
   (`election_service.py` `ElectionService.simulate` ↔ `workers.py`
   `_simulate_pipeline_worker`) → `parse_optional_election_configs()`,
   nouvelle fonction dans `_helpers.py` (déjà importé par les deux fichiers).
   La vérification candidats (`if len(cand_specs) < 2: ...`) reste dupliquée
   volontairement : elle dépend du `cand_specs` de chaque appelant, construit
   avec un défaut/plafond différent (`SINGLE_WINNER_CAP` côté service, `[:6]`
   côté pipeline) — pas une duplication réelle.
2. **Le bloc de contagion du vote blanc** (SIS + réduction du
   `blank_threshold`) → `_apply_blank_contagion()`, nouvelle fonction dans
   `_electorate.py`. jscpd n'en avait flaggé qu'une paire
   (`election_service.py` ↔ `workers.py` `_campaign_sensitivity_worker`),
   mais le même bloc, octet pour octet, existait en réalité **5 fois**
   (les 3 autres : `_divergence_worker`, `_combined_effects_worker`,
   `_simulate_pipeline_worker`, toutes dans `workers.py`) — les 4 non
   flaggées par jscpd (probablement une fenêtre de correspondance qui ne
   s'alignait pas à cause du contexte environnant) ont été vérifiées une par
   une (mêmes noms de paramètres, même calcul ; seul ce que l'appelant fait
   du taux final après coup diffère, ce que la fonction autorise en le
   retournant plutôt qu'en l'imposant).
3. **Le bloc "reseed global + construire l'électorat"** (`_random.seed`/
   `_np.random.seed`/`_build_base_electorate`, le pattern *legacy* qui a
   précédé le couple `_seeded_rng_pair`/RNG locale documenté sur
   `election_service.py`) → `_reseed_and_build_electorate()`, nouvelle
   fonction dans `_electorate.py`. C'est le plus gros cluster : jscpd en
   avait flaggé 13 physiquement distincts via 7 paires qui se recoupaient
   (ex. `workers_advanced.py:366-382` matchait à la fois avec
   `workers_behavioral.py:41-57` ET `:167-183` — un seul bloc canonique, pas
   deux problèmes). Vérification site par site (mêmes 4 lignes,
   caractère pour caractère) a trouvé **3 sites de plus** que les 13
   flaggés — `_liquid_democracy_worker` et `_ballot_complexity_worker`
   (`workers_behavioral.py`), `_gerrymander_worker`
   (`workers_mechanisms.py`) — repérés mécaniquement en appliquant le
   remplacement partout où le texte matchait exactement. **16 sites au
   total** utilisent désormais cette fonction unique : `workers_advanced.py`
   (`_compulsory_voting_worker`, `_deliberation_worker`),
   `workers_behavioral.py` (`_cascade_worker`, `_behavioral_biases_worker`,
   `_liquid_democracy_worker`, `_nota_worker`, `_ballot_complexity_worker`,
   `_shy_voter_worker`, `_electoral_fatigue_worker`), `workers_dynamics.py`
   (`_hotelling_worker`, `_affective_polarization_worker`),
   `workers_mechanisms.py` (`_adaptive_worker`, `_abstention_worker`,
   `_stv_worker`, `_gerrymander_worker`, `_multiwinner_compare_worker`).
   Le défaut de candidats et son plafond (`[:6]`/`[:8]`, Carol à 0.1 ou 0.3
   selon le fichier) restent propres à chaque site — jamais partagés, jamais
   part du bloc dupliqué.
4. **Le résidu STV/multi-gagnant** — une fois (3) extrait, jscpd a révélé un
   **cinquième** clone que ni lui ni cette liste n'avaient vu au départ : le
   défaut à 4 candidats + les deux vérifications (`len(cand_specs) < 2` et
   `num_seats >= len(cand_specs)`) partagées par `_stv_worker` et
   `_multiwinner_compare_worker` (`workers_mechanisms.py`) redevenaient un
   bloc de 16 lignes autonome une fois le bloc (3) qui les suivait retiré.
   Factorisé dans la foulée : `_validate_multiwinner_candidates()` +
   `_MULTIWINNER_DEFAULT_CANDIDATES`, fonctions/constante privées ajoutées
   directement dans `workers_mechanisms.py` (usage strictement local aux
   deux workers, pas de raison de le partager plus largement).
5. **Le doublon interne à `simulation_ranked_utils.py`** (rassembler
   `ballots`/`all_cands` à partir de `votes`) → `_ballots_and_candidates()`,
   nouvelle fonction privée dans le même fichier, utilisée par
   `get_benham_winner` et `get_smith_irv_winner`. La boucle IRV qui suit
   n'a PAS été fusionnée malgré une ressemblance de surface : `get_benham_winner`
   y insère une vérification Condorcet à chaque tour que `get_smith_irv_winner`
   n'a pas (Condorcet-IRV vs Smith-IRV sont deux méthodes différentes) — jscpd
   ne l'avait d'ailleurs pas flaggée non plus, cohérent avec le fait que ce
   n'est pas une vraie duplication.

Chaque extraction est un refactor pur — mêmes noms de paramètres, même
calcul, même ordre d'exécution — vérifié par la suite backend complète
(aucune régression), `mypy api/` (clean) et `ruff check fast_api_voter`
(0 erreur). `simulation_ranked_utils.py` étant un des deux fichiers du
moteur double documentés par CLAUDE.md : `./scripts/check_engine_parity_drift.sh`
regénère `engineParity.json` **octet pour octet identique** au fichier commité
(aucune dérive — attendu, ces deux fonctions ne changent pas de sortie) et
`playgroundVoting.parity.test.ts` reste vert (49/49). `lint-imports` (contrat
`routes → domain → engine`) reste à 0 violation.

**Résultat** : jscpd 32 → 19 clones ; le cluster backend ciblé passe de 13 à
**0** (les 19 restants sont exactement les clones frontend `components/`/
`lib/`, hors périmètre, inchangés). `.github/quality-baseline.json` mis à
jour (`jscpd_clones: 32 → 19`) via `./scripts/check_quality_ratchet.sh
--update` — `vulture`/`radon`/`deptry`/`knip` inchangés (0/135/0/93).*

*Mise à jour du 2026-09-12 (quinquies) — un `/code-review ultra` mandaté avant
merge (la PR touche `simulation_ranked_utils.py`, CLAUDE.md l'exige) a trouvé
5 instances **supplémentaires** de la même duplication que le point ci-dessus
venait de traiter, manquées par la vérification "site par site" faite alors —
la duplication réelle, pas une nouvelle catégorie :

- **3 sites de plus** pour le bloc `_reseed_and_build_electorate` (point 3
  ci-dessus) : `_sortition_worker` (`workers_advanced.py`), qui appelait encore
  `_build_base_electorate` après un `_random.seed`/`_np.random.seed` manuel ;
  `_historical_replay_worker` (`workers_mechanisms.py`), où le calcul des
  overrides de candidats s'intercalait entre le reseed et la construction
  (réordonné sans risque : ce calcul ne touche ni `random` ni `np.random`) ;
  `_polarization_worker` (`workers_dynamics.py`), où le `issues =
  DEFAULT_ISSUES` hissé au-dessus de la boucle `for ideology in
  ideology_range:` est devenu redondant et a été retiré. La boucle Monte-Carlo
  interne de `_polarization_worker` (seed différent par simulation) reste,
  elle, en appel direct à `_build_base_electorate` — vérifié que
  `_affective_polarization_worker`, déjà "converti" au point 3, a exactement
  la même boucle interne non convertie : convention existante, pas un oubli.
- **2 sites de plus** pour `_ballots_and_candidates` (point 5 ci-dessus) :
  `get_nanson_winner` et `get_baldwin_winner` faisaient encore leur propre
  scan `is_dict` + `for c in ranking: if c not in all_cands: ...` — le
  commentaire de `get_baldwin_winner` signalait déjà lui-même la ressemblance
  avec `get_nanson_winner`. Bascule vers
  `parsed = _ballots_and_candidates(votes)` dans les deux, ce qui remplace au
  passage un scan O(n²) par candidat par le set "seen" O(n) de la fonction
  partagée. `simulation_ranked_utils.py` touché : `mypy api/` a d'abord
  échoué (`Returning Any` sur les retours `min(all_cands)`/`min(active)`,
  `all_cands`/`ballots` hérités en `list[Any]` de la signature générique du
  helper) — corrigé par une pré-déclaration `all_cands: list[str]` avant le
  dépaquetage, sans toucher au flux de contrôle.
  `./scripts/check_engine_parity_drift.sh` et `playgroundVoting.parity.test.ts`
  (49/49) confirment que le gain de complexité ne change aucun résultat
  produit par ces deux méthodes.
- **Un mutable partagé dormant** : `_MULTIWINNER_DEFAULT_CANDIDATES` (point 4
  ci-dessus) était une `list` de `dict`s alors que `_LD_DEFAULT_CANDIDATES`/
  `_DT_DEFAULT_CANDIDATES` (même famille de fichiers, même usage) sont des
  `tuple`s — aucun bug vivant (rien ne mute ces dicts en place aujourd'hui),
  mais un futur appelant qui normaliserait un `cand_spec` sur place
  corromprait silencieusement le défaut partagé pour la durée du process.
  Alignée sur la convention établie (`tuple`).

`npx jscpd --config .jscpd.json fast_api_voter/api voter-app/src` redonne
**19** clones, inchangé — 0 clone Python avant comme après cette ronde : ces
5 blocs (4 lignes de reseed, ~15 lignes de scan `is_dict`) étaient déjà sous
le seuil `minLines`/`minTokens` de jscpd et invisibles à l'outil, exactement
comme au point 2 ci-dessus pour la contagion du vote blanc. `.github/quality-
baseline.json` inchangé (`jscpd_clones: 19`), pas de `--update` nécessaire.
Suite backend complète (2187 passed, 41 skipped — identique à la baseline de
cette branche), `mypy`, `ruff check fast_api_voter` et `lint-imports` (0
violation) tous verts.*

*Mise à jour du 2026-09-12 (sextius) — le gate CI "Backend: Tests + Coverage +
Security" a échoué après le push précédent : `diff-cover` (100% des lignes
changées exigé) a trouvé 19 lignes non couvertes, réparties entre le corps de
`_apply_blank_contagion` (`_electorate.py`), ses 4 sites d'appel dans
`workers.py` (`_divergence_worker`, `_campaign_sensitivity_worker`,
`_combined_effects_worker`, `_simulate_pipeline_worker`), son site dans
`ElectionService.simulate` (`election_service.py`), et la branche
`len(cand_specs) < 2` de `_validate_multiwinner_candidates`
(`workers_mechanisms.py`). Cause : les blocs dupliqués d'origine n'étaient
exercés par aucun test avec la contagion (`blank_vote.contagion.enabled`)
réellement activée — la duplication avait involontairement caché ce trou de
couverture derrière plusieurs copies identiques, dont aucune n'était testée
avec ce paramètre à `true`. Pour `_validate_multiwinner_candidates`, la
branche `< 2` est en réalité inatteignable via les deux endpoints HTTP
(`/stv`, `/multiwinner_compare` imposent déjà `min_length=2` au niveau
Pydantic) : gardée comme filet de sécurité pour un futur appelant direct de
la fonction, et testée comme telle (appel direct, pas HTTP).

Fix : 7 tests réels ajoutés (aucun gaming de couverture) — un par site
d'appel avec `contagion.enabled: true` dans le payload HTTP concerné, plus un
test direct de `_validate_multiwinner_candidates` sur les deux branches.
`diff-cover --compare-branch=origin/develop --fail-under=100` repasse à 100%
(0 ligne manquante). `mypy`, `ruff check fast_api_voter` et `lint-imports`
verts ; suite backend complète 2194 passed (2187 + 7), 41 skipped.*

*Mise à jour du 2026-09-13 — §7 "chantiers plus lourds" item 2 (complexité)
traité pour son périmètre non-polity : les 4 fonctions rang F de §5 hors
`domain/polity/*` sont décomposées, une PR par fonction (`--no-ff` sur
`develop`, comme le reste du plan) :

- **`_interpret_worker`** (`election/workers.py`, F 44) → **A**. Les 8
  sections déjà numérotées en commentaire (groupement par vainqueur,
  titre, analyse Condorcet, raison de divergence, meilleur/pire par
  regret bayésien, analyse du vote blanc, note pédagogique, faits clés)
  deviennent 8 fonctions privées `_interpret_*` appelées en séquence — même
  calcul, même ordre, `_interpret_group_methods` (le bloc le plus complexe
  de l'extraction) retombe en **C**. `diff-cover` a trouvé 8 lignes non
  couvertes une fois le code déplacé (spoiler Condorcet, consensus
  complet, taux de vote blanc élevé, forte concordance inter-méthodes) —
  5 tests réels ajoutés.
- **`_identity_voting_worker`** (`theory/workers.py`, F 44) → **C**. Même
  traitement, 6 helpers `_identity_*`. `diff-cover` 100 % du premier coup
  (les tests existants couvraient déjà chaque branche extraite).
- **`_democratic_backsliding_worker`** (`theory/workers.py`, F 45, la plus
  longue des 4 — 259 lignes) → **B**. Le corps de la boucle par élection
  (vote de base → mécanisme de recul choisi → résistance des garde-fous →
  vainqueur → indice de qualité démocratique → avantages cumulés →
  détection d'autocratie) extrait dans `_run_one_backsliding_election`
  (rang **D**, absorbe l'essentiel de la complexité d'origine — attendu,
  l'objectif est d'isoler la logique par cycle, pas d'éliminer un
  branchement inhérent à la simulation). Les 7 variables mutées à chaque
  itération (bonus de gerrymandering, biais médiatique, taux de
  suppression, qualité démocratique, victoires consécutives de l'sortant,
  autocratie atteinte/à quelle élection) regroupées dans un seul
  `state: Dict[str, Any]` muté sur place plutôt qu'un nouveau type
  (dataclass/NamedTuple) inédit dans ce fichier. `diff-cover` a trouvé deux
  vagues de lignes non couvertes : d'abord 4 branches `media_capture`/
  `voter_suppression`/leurs garde-fous (aucun test n'utilisait ces deux
  méthodes), puis — après un premier passage CI vert en local mais rouge
  en CI — les branches "l'opposition gagne" (`else` de `incumbent_won`),
  couvertes par accident en local par un test tiers non déterministe
  (probablement un test Hypothesis/Schemathesis dont le fuzzing a touché
  cette branche cette fois-là) plutôt que par un test dédié. Corrigé par un
  test déterministe (`seed=1`, intensité de recul nulle → concurrence
  spatiale pure, vérifié directement contre le worker avant d'écrire le
  test) — même catégorie de piège que la duplication qui cachait un trou
  de couverture en §4/« sextius » ci-dessus, cette fois côté fuzzing plutôt
  que copier-coller.
- **`start_monte_carlo`** (`sockets/__init__.py`, F 41) → **B**. Handler
  Socket.IO de streaming ; extrait `_monte_carlo_parse_input` (le bloc
  `try` de validation), `_monte_carlo_new_stats`/`_monte_carlo_accumulate_run`
  (agrégation par itération — le plus complexe des 5, rang **C**),
  `_monte_carlo_checkpoint_payload`/`_monte_carlo_final_payload` (les deux
  payloads `sio.emit`). `diff-cover` a trouvé la branche "liste de
  candidats explicite" non couverte (tous les tests existants passent par
  `num_candidates`, jamais `candidates`) — 3 tests unitaires directs
  ajoutés sur `_monte_carlo_parse_input` (fonction pure maintenant qu'elle
  est son propre helper, pas besoin du `live_server` complet).

Chaque extraction est un refactor pur (mêmes noms, même calcul, même ordre),
vérifiée par la suite backend complète, `mypy`, `ruff check` et
`lint-imports` à chaque PR. `./scripts/check_quality_ratchet.sh` reste
exactement à la baseline sur les 5 métriques après les 4 PR (`radon_c_plus`
135 → 135 : les blocs qui remplacent chaque fonction rang F sont pour
l'essentiel rang A/B, un seul rang C par extraction, donc le compte de blocs
« C ou pire » ne bouge pas alors même que la moyenne globale s'améliore,
voir §5). Aucune des 4 PR ne touche `simulation_ranked_utils.py`/
`simulation_score_utils.py`/`playgroundVoting.ts` ni une autre surface
mandatant `/code-review ultra` par CLAUDE.md.

**Hors périmètre, volontairement** : les 2 fonctions rang F restantes
(`api/domain/polity/indexer.py::index_events` F 81, `api/domain/polity/
run_polity_simulation.py::_run_accountability_phase` F 44) appartiennent à
`domain/polity/`, développé activement dans le worktree/branche séparé
`Vote-App-polity` — même décision que celle déjà documentée pour ce même
dossier dans PLAN_SOLIDITE_TECHNIQUE.md (Lot 14.5, "zones mortes"). Un
découpage unilatéral depuis `develop` risquerait un conflit avec ce travail
en cours plutôt que de l'aider ; à reprendre côté polity le moment venu.

**Effet sur §8** : le resserrement de `xenon` envisagé (`-b D -m D -a B`)
reste bloqué par ces 2 fonctions polity — `xenon api/ -e "api/tests/*"`
tourne sur tout `api/` sans exclusion de `domain/polity/`, donc un seuil par
bloc plus strict que F échouerait immédiatement sur ces deux-là. À reprendre
une fois qu'une décision équivalente aura été prise côté polity (soit les
décomposer aussi, soit exclure `domain/polity/` du gate par bloc).*

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

**Mise à jour 2026-09-12 — chiffres recalculés (`npm run knip`, total 93,
== `.github/quality-baseline.json`).** Le lot de 9 fichiers/1 dépendance/1
export signalé le 2026-09-06 est supprimé (voir la note de mise à jour en
tête de fichier) ; il ne reste plus que les types exportés jamais réimportés
ailleurs :

| Catégorie | Compte | Détail |
|---|---|---|
| Fichiers inutilisés | 0 | Corrigé le 2026-09-12 : les 9 fichiers (`components/research/BlankVoteTimeSeries.tsx`, `components/shared/EmptyChart.tsx`, `components/ui/{accordion,bootstrap-tabs,pagination,tabs,tooltip-overlay}.tsx`, `data/methodReferences.ts`, `services/index.ts`) sont supprimés |
| Dépendances déclarées jamais importées | 0 | Corrigé le 2026-09-12 : `@radix-ui/react-tabs` retiré de `package.json` |
| Dépendances utilisées mais absentes de `package.json` | 0 | Corrigé : `d3-delaunay` est déclaré (`package.json`), `@eslint/js`/`globals` aussi — les 3 findings de l'édition d'août sont résolus |
| Exports jamais importés ailleurs | 0 valeur + 93 types | Corrigé le 2026-09-12 : la valeur `CardTitle` (`components/ui/card.tsx`) était non seulement non exportée ailleurs mais aussi jamais utilisée en interne au fichier — composant supprimé en entier, pas seulement dé-exporté. Les 93 types viennent toujours majoritairement de `components/ui/*` (kit shadcn/ui) et de `src/api/index.ts`/`src/types.ts` (types larges générés/partagés, partiellement utilisés par construction) |
| Export dupliqué | 0 | Corrigé : `src/components/ui/instrument.tsx` n'exporte plus que `Instrument` en nommé |

**Priorité d'action suggérée :** plus aucun finding "risque réel" — la seule
catégorie non vide (93 types exportés jamais réimportés) reste à laisser
telle quelle sauf audit plus fin — faux positifs structurels d'un pattern
"bibliothèque de composants", comme en août et en septembre.

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

**Traité le 2026-09-12** (voir la mise à jour en tête de ce document,
« quater ») : le cluster `election_service.py`/`workers*.py`/
`simulation_ranked_utils.py` ci-dessus — 13 clones sur un total qui avait
entre-temps glissé à 32 (passes RNG et refurb/perflint postérieures au
2026-09-06) — est éliminé. Regroupé en 5 blocs de contenu réellement
identique (pas 13 problèmes indépendants) et factorisé dans
`_electorate.py`, `_helpers.py`, `workers_mechanisms.py` et
`simulation_ranked_utils.py` lui-même ; détail complet, y compris les 4
sites supplémentaires trouvés en lisant le code plutôt qu'en se fiant aux
seules paires jscpd, dans la mise à jour datée. `jscpd` : 32 → 19 clones,
tous frontend (`components/`/`lib/`) désormais — la mesure python de ce scan
est passée à 0.

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

`xenon` tourne une fois dans le job CI, en **gate réel** (`-b F -m F -a A`,
ajouté depuis l'édition d'août ; le passage en rapport pur `-a F`, qui ne
pouvait jamais échouer, a été retiré le 2026-09-17) qui fait
échouer le job si la moyenne globale du repo retombe sous le rang A — la
moyenne actuelle (A, 4.73, §5 ci-dessus) passe avec de la marge. `-b`/`-m`
restent à F (jamais d'échec par bloc/module) tant que les 6 fonctions rang F
et les fonctions rang E n'ont pas été décomposées — voir §8 pour la suite
envisagée.

**Mise à jour du 2026-09-13** : 4 des 6 fonctions rang F ci-dessus sont
décomposées (`_interpret_worker` → A, `_identity_voting_worker` → C,
`_democratic_backsliding_worker` → B, `start_monte_carlo` → B) — détail
complet dans la mise à jour datée en tête de ce document. Moyenne globale
désormais **A (4.54) sur 1227 blocs**. Seules les 2 fonctions
`domain/polity/*` du tableau restent rang F (hors périmètre, développement
polity séparé — voir la même mise à jour datée) ; `radon_c_plus` reste à 135
dans `.github/quality-baseline.json` (les blocs qui remplacent chaque F sont
pour l'essentiel A/B, un seul C par extraction, donc le compte de blocs
« C ou pire » ne bouge pas malgré l'amélioration de la moyenne globale).

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
  **Traité le 2026-09-12** (voir la mise à jour en tête de §7, item 3) : les
  63 fichiers restants (le chiffre a légèrement bougé depuis le 2026-09-06,
  suppressions/ajouts normaux) sont répartis en 11 sous-dossiers
  thématiques ; `components/shared/` lui-même ne contient plus de fichier à
  plat, seulement `README.md` et les sous-dossiers.
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
6. ✅ Supprimer le nouveau lot de 9 fichiers frontend inutilisés + la
   dépendance `@radix-ui/react-tabs` + l'export `CardTitle` signalés en §3
   (apparus indépendamment après le 2026-09-06) — fait le 2026-09-12, avec
   au passage l'orphelin `useDebouncedSimulation` du Lot 6.5 (voir Lot 14 du
   plan de solidité technique) ; `npm run knip` 104 → 93.

**Chantiers plus lourds (à planifier, pas à improviser en une PR) :**
1. ✅ Factoriser les blocs dupliqués identifiés en §4 entre les fichiers
   `workers*.py` et entre `election_service.py`/`workers.py`. Fait le
   2026-09-12 : voir la mise à jour datée « quater » en tête de ce document
   pour le détail (5 clusters réels, 16+ sites, `jscpd` 32 → 19 — la mesure
   backend passe à 0). Un `/code-review ultra` mandaté avant merge en a trouvé
   5 instances de plus de ces mêmes blocs (3 sites `_reseed_and_build_electorate`,
   2 sites `_ballots_and_candidates`) plus un mutable partagé dormant à
   aligner sur la convention `tuple` existante — voir la mise à jour datée
   « quinquies ».
2. ✅ (partiel) Décomposer les fonctions rang F restantes de §5 — fait le
   2026-09-13 pour les 4 fonctions hors `domain/polity/*` (voir la mise à
   jour datée en tête de ce document) : `_interpret_worker` F→A,
   `_identity_voting_worker` F→C, `_democratic_backsliding_worker` F→B,
   `start_monte_carlo` F→B. Les 2 fonctions polity restantes (`index_events`
   F 81, `_run_accountability_phase` F 44) sont laissées volontairement de
   côté — développement actif séparé, voir la même mise à jour datée. La
   **consolidation architecturale plus large** de `domain/election/
   workers*.py` (6 fichiers, ~7 850 lignes cumulées) — un découpage par
   responsabilité plutôt que par ordre chronologique d'ajout — reste, elle,
   un chantier distinct et non entamé : la décomposition ci-dessus retire la
   complexité extrême par fonction, pas la fragmentation du fichier dans son
   ensemble. À planifier séparément si jugé utile, plutôt qu'improvisé en
   continuité de ce lot.
3. ✅ Réorganiser `components/shared/` (66 fichiers au 2026-09-06, en forte
   baisse depuis les 123 d'août — voir §6) en sous-dossiers thématiques —
   fait le 2026-09-12. Les 63 fichiers actuels sont répartis en 11
   sous-dossiers : `mechanisms/` (8, mécanismes alternatifs — jury,
   liquide, tirage au sort, délibération, conviction, épistocratie,
   identité, E2E-V), `systems/` (8, systèmes électoraux et leurs
   visualisations — coalition, multi-gagnant, cartes de circonscriptions/
   gerrymander, STV, complexité du bulletin, pipeline électoral),
   `campaign/` (5, dynamiques de campagne — Hotelling, sensibilité,
   polarisation, dynamiques de partis), `temporal/` (5, mécanismes
   temporels — vote adaptatif, rejeu historique, primaires, cascade,
   fatigue électorale), `behavioral/` (6, réalisme comportemental — biais,
   vote timide, surcharge de choix, vote obligatoire, participation
   démographique, polarisation affective), `theory/` (9, théorie et
   paradoxes — Sen, agrégation de jugements, manipulation de l'agenda,
   tyrannie de la majorité, répartition des sièges, indices de pouvoir,
   recul démocratique, intergénérationnel, Polis), `analysis/` (4, analyse
   approfondie — manipulation, volonté collective, testeur d'hypothèses,
   matrice d'effets combinés), `blank/` (3, famille du vote blanc — NOTA,
   divergence, abstention), `results/` (4, aides de rendu des résultats
   utilisées par `FullResultsModule`), `ui/` (8, primitives génériques
   réutilisées dans toute l'app — toast, badge live, bannière hors-ligne,
   etc.) et `common/` (3, composants transverses non thématiques —
   questions de curiosité, export de jeu de données, visite guidée).
   Classification faite en lisant le contenu de chaque fichier et en
   croisant avec le regroupement déjà fait par `labCatalog.tsx` (la source
   de vérité testée du catalogue du Laboratoire) plutôt qu'en devinant sur
   le nom de fichier seul ; les ~150 imports (statiques et dynamiques
   `import()` pour le code-splitting) ont été mis à jour et `tsc`/`vitest`/
   `lint`/`build`/`knip` restent tous verts avec les mêmes compteurs
   qu'avant (0 erreur tsc, même nombre de tests, 0 erreur lint, budget
   size-limit respecté, même compte `knip`).
4. Reprendre `polity_v2_consolidation_handoff.md` comme point de départ pour
   la consolidation de `domain/polity/`.
5. ✅ Centraliser la gestion d'erreurs pour réduire les `except Exception` nus
   (backend, 42 au 2026-09-06 — voir §6) — probablement via un décorateur ou
   un context manager partagé plutôt qu'un correctif fichier par fichier.
   Fait le 2026-09-12 : voir la mise à jour datée ci-dessus pour le détail
   (42 → 29 clauses réelles, deux formes partagées plutôt qu'un décorateur
   unique, 9 sites laissés tels quels avec justification au cas par cas).
6. ✅ Ajouter les tests manquants pour les fonctions `get_*_winner` de
   `simulation_ranked_utils.py` sans couverture dédiée (recoupement §5 /
   PR #157) avant de refactorer ce fichier — éviter de casser une méthode de
   vote silencieusement pendant le découpage. Fait le 2026-09-12 : le chiffre
   "9" était stale (voir la mise à jour datée ci-dessus) — seules 3 fonctions
   manquaient réellement d'un test dédié (`get_borda_winner`,
   `get_positional_score_winner`, `get_approval_winner_sincere`), désormais
   couvertes. Le découpage de `simulation_ranked_utils.py` que ce filet de
   sécurité prépare n'a, lui, pas d'item dédié dans cette liste — reste à
   planifier séparément le moment venu.

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
  2026-09-06 (voir §3) et **promu en hook pre-commit bloquant le
  2026-09-12** (`.pre-commit-config.yaml`, même modèle local que `mypy`).
  Portée vérifiée en injectant du vrai code mort de chaque classe plutôt que
  supposée : à ce seuil, vulture attrape bien un paramètre inutilisé (100 %),
  du code inatteignable après `return` (100 %) et un import inutilisé
  (90 %) — exactement les deux classes de ses trouvailles d'origine. Il
  n'attrape **pas** une fonction top-level inutilisée ni une variable locale
  inutilisée (toutes deux plafonnées à 60 % de confiance, quel que soit le
  code) — celles-là restent informationnelles (`--min-confidence 60` dans
  `scripts/audit.sh`), dominées par les faux positifs Enum/décorateurs déjà
  documentés en §3, pas sûres à gater telles quelles.
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
