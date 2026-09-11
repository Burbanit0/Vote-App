# EXP-003 — Couverture *runtime* : que reste-t-il inatteignable quand la dette morte a disparu ?

- **Date** : 2026-09-11 · **Statut** : adopté (partiel — script manuel, pas de gate CI) · **Coût réel** : ~5h (recherche outillage front, deux impasses de mécanisme diagnostiquées et corrigées, trois passes réelles de la suite e2e, vérification manuelle des trouvailles)
- **Verdict en une phrase** : sous la vraie suite Playwright, le backend n'exécute que **34 %** de ses lignes (contre 91,56 % en tests unitaires) et le frontend **63 %** (contre 87,05 %) — l'écart le plus spectaculaire (2 813 lignes, ~19 % du backend, 0 % e2e malgré ~99 % unitaire) est un sous-système entier (`api/domain/polity/`) qui n'a **aucune route** enregistrée dans `api/main.py`, et le cas le plus intéressant est une page retirée du routage (`/simulation/compare`) dont l'endpoint backend et le hook frontend restent unitairement testés à 100 % tout en étant invisibles à `knip` — un vrai angle mort des deux signaux existants, trouvé seulement en croisant les trois.

## Hypothèse de départ

Le [Lot 6 du plan](../../PLAN_SOLIDITE_TECHNIQUE.md#lot-6--ce-que-lanalyse-statique-ne-voit-pas)
pose la question après la suppression de 16 500 lignes mortes (chantier
antérieur) : qu'est-ce qui reste inatteignable **même en usage réel** ? Deux
signaux existent déjà et ont chacun un angle mort structurel :

- **Détection statique** (vulture, knip, dependency-cruiser) : voit ce qui
  n'est *référencé par rien*. Ne peut pas voir qu'une fonction référencée
  et unitairement testée n'est en réalité jamais déclenchée par un vrai
  parcours utilisateur.
- **Couverture unitaire** (pytest-cov 90 % backend, Vitest frontend) : mesure
  ce qu'un test atteint en appelant une fonction directement avec des
  données synthétiques — souvent plus profond qu'aucun vrai clic ne va
  jamais, et parfois complètement déconnecté de toute route réellement
  montée dans l'app.

Hypothèse testée : une passe de couverture sous la **vraie suite Playwright**
(navigateur réel, frontend ET backend réellement démarrés) donnerait un
troisième signal — et le DELTA entre lui et la couverture unitaire
identifierait du code bien testé en isolation mais jamais câblé à un usage
réel, éventuellement du code que les outils statiques auraient dû
détecter et n'ont pas détecté.

## Protocole

### Backend : `coverage.py` autour du vrai serveur

`coverage.py` est déjà une dépendance transitive (`pytest-cov`, configurée
dans `fast_api_voter/pyproject.toml`'s `[tool.coverage.run]`/`[report]`) —
aucune nouvelle dépendance nécessaire. Le principe : wrapper le process
`uvicorn` que Playwright frappe réellement (`:4434` par défaut, cf.
`CLAUDE.md`) avec `coverage run`, laisser tourner la vraie suite e2e contre
lui, puis générer le rapport avec la même config que la couverture unitaire
(même `source`/`omit`, donc même dénominateur de lignes).

**Piège trouvé et corrigé — `coverage run -m uvicorn` ne sauvegarde jamais
rien.** Premier essai : `coverage run -m uvicorn api.main:app --port 4434`,
puis `kill -TERM <pid>` pour arrêter proprement en fin de suite. Le serveur
loggue un arrêt parfaitement propre (« Shutting down… Application shutdown
complete… Finished server process ») — et pourtant **aucun fichier
`.coverage` n'apparaît sur disque**, vérifié à trois reprises avec des ports
différents avant d'y croire. Cause, trouvée en lisant `uvicorn/server.py` :
`Server.capture_signals()` restaure le handler de signal ORIGINAL puis
**se re-déclenche lui-même le signal reçu** (`signal.raise_signal`) une fois
le nettoyage asynchrone terminé — un idiome délibéré pour qu'un superviseur
de process voie le vrai signal de fin dans le code de sortie. Ce second
signal tue le process via l'action par défaut du noyau, **après** que le
code Python a fini de nettoyer, ce qui contourne entièrement `atexit`
(qui ne se déclenche qu'à une sortie normale de l'interpréteur, jamais à une
mort par signal) — et la sauvegarde de `coverage.py` est justement basée sur
`atexit`.

Correctif : `fast_api_voter/scripts/run_e2e_coverage_server.py` installe
*son propre* handler SIGTERM/SIGINT **avant** qu'uvicorn installe le sien.
`capture_signals()` capture ce handler comme « l'original » et le restaure
avant de se re-signaler à la fin — donc notre handler reçoit exactement ce
second signal, au moment exact où le nettoyage async est déjà terminé, et
peut appeler `coverage.Coverage.current().save()` avant de rendre la main
au comportement par défaut. Revérifié directement (santé de l'endpoint +
présence du fichier `.coverage.e2e` après un `kill -TERM`) avant de faire
confiance au mécanisme.

**Deuxième piège trouvé — contamination par un process tiers sur le port
par défaut.** La première passe « complète » du script utilisait le port
`:4434` documenté par `CLAUDE.md`. Un process externe (UID différent du
mien, `/usr/local/bin/python3.11`, tournant depuis avant cette session)
occupait déjà ce port dans cet environnement — mon serveur instrumenté
échouait donc à démarrer (« address already in use »), mais le script ne
le remarquait pas : le sondage de disponibilité (`curl .../health`)
réussissait quand même, en tapant sur le process tiers au lieu du mien. La
suite e2e passait, produisait un rapport de couverture backend avec des
chiffres plausibles (imports de modules exécutés au chargement) — **et
pourtant ce rapport ne mesurait rien de ce que la suite avait réellement
déclenché**. Trouvé en relisant le log ligne par ligne (`grep "address
already in use"` dans la sortie du script, jamais vérifié auparavant parce
que le sondage HTTP semblait suffire) plutôt qu'en faisant confiance au
"suite verte + rapport produit" comme preuve de validité. Corrigé : le
script tourne maintenant sur un port dédié (`4444`, overridable), et
`vite.config.ts`'s proxy dev + `src/api/client.ts`'s `API_BASE` sont déjà
tous deux pilotables par `VITE_API_URL` (pattern déjà existant, juste
étendu au proxy) — le frontend est donc pointé explicitement dessus. Les
deux passes « vérifiées » citées plus bas ont été relancées intégralement
après ce correctif ; les chiffres qu'elles donnent sont reproductibles
(deux runs indépendants, mêmes totaux backend à l'unité près).

### Frontend : recherche d'outillage, puis Istanbul

Le plan suggérait Istanbul, avec un avertissement explicite : cet
écosystème a historiquement du retard sur les nouvelles majors de Vite.
Ce dépôt tourne sur **Vite 8.2.2** (`voter-app/package.json`) — vérifié
avant tout engagement plutôt que supposé :

- `vite-plugin-istanbul@9.0.1` (dernière version, `npm view`) déclare
  `peerDependencies: { vite: '>=7' }` — compatible sans réserve.
- Installé sans aucun conflit de peer dependency (`npm install -D
  vite-plugin-istanbul`, `npm install -D nyc` pour la fusion/le rapport).
- Testé en vrai avant d'y engager le reste du travail : serveur de dev
  lancé avec `E2E_COVERAGE=true`, module servi inspecté directement
  (`curl .../src/index.tsx`) — les compteurs Istanbul (`cov_xxx()`) sont
  bien injectés, `window.__coverage__` bien exposé.

**Aucune impasse Istanbul/Vite 8 rencontrée** — contrairement à
l'avertissement du plan, qui datait d'avant que l'écosystème ait rattrapé
Vite 8 (9.0.1 est sorti après le support explicite de Vite 7+). Le
fallback prévu par le plan (Playwright `page.coverage` V8, Chromium
seulement) n'a donc pas été nécessaire — et Istanbul a un avantage réel sur
lui pour ce dépôt précis : la suite tourne sur **chromium + firefox**
(`playwright.config.ts`), et `page.coverage.startJSCoverage()` n'existe que
sur Chromium. Istanbul instrumente le code source directement
(indépendant du moteur JS), donc les deux projets contribuent au même
rapport.

**Piège de câblage, plus subtil** : chaque test importe `test`/`expect`
directement depuis `'@playwright/test'`, et Playwright n'a pas de
mécanisme de hook global appliqué à tous les fichiers — un
`test.afterEach` ne s'applique qu'aux tests créés depuis la même instance
`test` étendue. `window.__coverage__` est réinitialisé à chaque nouvelle
page/contexte (donc à peu près à chaque test), et disparaîtrait donc
silencieusement sans un point d'extraction par test. Solution : un seul
fichier `voter-app/tests/e2e/coverageFixtures.ts` ré-exportant `test`
(étendu avec une fixture `auto: true` qui vide `window.__coverage__` sur
disque après chaque test) et `expect` ; les 11 fichiers de spec importent
désormais depuis lui plutôt que directement depuis `'@playwright/test'` —
un changement d'import d'une ligne par fichier, comportement identique
quand `E2E_COVERAGE` n'est pas positionné (le cas de tout run de PR normal).

### Orchestration

`scripts/e2e_coverage.sh` : démarre le backend instrumenté, attend qu'il
réponde, lance `E2E_COVERAGE=true VITE_API_URL=http://localhost:4444 npx
playwright test`, arrête le backend (SIGTERM → sauvegarde), génère les deux
rapports (`coverage.py` HTML + texte côté backend, `nyc report` HTML +
texte + json-summary côté frontend, fusionnant les blobs par test dans
`.nyc_output/`).

## Ce que ça a trouvé

**Chiffres globaux, deux passes indépendantes et reproductibles (mêmes
totaux backend à l'unité près) :**

| | Unitaire | Runtime e2e | Delta |
|---|---|---|---|
| Backend — lignes | 91,56 % (13 687/14 949) | **34,4 %** (5 149/14 949) | -57 pts |
| Frontend — instructions | 87,05 % (9 125/10 482) | **63,15 %** (6 211/9 835)* | -24 pts |
| Frontend — lignes | 88,69 % (7 889/8 895) | 64,22 % (5 328/8 296)* | -24 pts |

\* *Dénominateurs légèrement différents (9 835 vs 10 482) : Vitest mesure
via le provider `coverage-v8` (natif V8), l'e2e via l'instrumentation
Babel d'Istanbul — deux façons de compter une « instruction » qui ne
tombent pas exactement pareil. La comparaison est valide dans sa direction
et son ordre de grandeur, pas au chiffre près.*

L'écart backend (-57 points) est bien plus marqué que le frontend
(-24 points) — attendu : le frontend partage un arbre de composants commun
entre les 5 routes réelles, donc visiter même une poignée de pages exécute
une bonne partie du code partagé (UI, hooks, stores) ; le backend expose
des dizaines de fonctions `_xxx_worker` indépendantes, chacune sa propre
route, et l'e2e n'en frappe qu'une poignée.

### Trouvaille n°1 — `api/domain/polity/*` : un sous-système entier, 0 % e2e, ~99 % unitaire

2 813 lignes (~19 % du backend) sur 20 fichiers
(`api/domain/polity/accountability.py`, `codebook.py`, `config.py`,
`indexer.py`, `llm_behavior_engine.py`, `llm_client.py`, `llm_schemas.py`,
`parties.py`, `run_polity_simulation.py`, `simple_rules.py` et dix autres)
sont à **0 % d'exécution e2e** alors que la plupart sont à 97-100 %
unitaire (dix d'entre eux apparaissent même dans les « 39 fichiers
ignorés pour couverture complète » du rapport unitaire — 100 % pile).

Vérifié à la main, pas pris pour argent comptant : `grep -n "polity"
fast_api_voter/api/routes/*.py` — zéro résultat ; `api/main.py:162-168`
n'enregistre (`include_router`) que `health`, `election`, `export`,
`public`, `simulations`, `tech`, `theory` — **aucune route `polity`
n'existe dans l'app FastAPI qui tourne**. Côté frontend, `grep -rln
"polity" voter-app/src/` — zéro résultat également. Ce n'est pas un bug :
`fast_api_voter/scripts/` contient tout un harnais (`llm_harness.py`,
`run_v5_acceptance.py`, `calibrate_*.py`…) qui importe et exécute ce code
directement comme bibliothèque de recherche, hors de l'app HTTP. Mais
c'est exactement la question que Lot 6 pose : ce sous-système, unitairement
irréprochable, ne fait **structurellement pas partie** du produit que
l'utilisateur réel touche — une frontière architecturale à documenter
explicitement plutôt qu'à laisser implicite.

### Trouvaille n°2 — une page retirée du routage dont le backend et un hook restent testés à 100 %, invisibles à `knip`

`voter-app/src/routes.ts:34` : `/simulation/compare` est dans
`LEGACY_REDIRECTS`, redirigé vers `/playground` — `App.tsx:46-59` ne monte
plus jamais `SimulationComparePage` (confirmé : zéro référence dans
`App.tsx`, la seule autre référence au composant est son propre test
unitaire). Or :

- Le backend garde la route **vivante** : `api/routes/simulations.py:277-279`
  enregistre toujours `POST /compare` → `_compare_methods_worker`
  (`api/domain/simulations/compare.py`). Ce fichier (457 lignes) a la
  couverture unitaire **la plus basse de tout le backend** (65 % — déjà un
  point faible connu, indépendant de cette expérience) et tombe à **7 %**
  en e2e (30/457 lignes).
- Côté frontend, `voter-app/src/hooks/useDebouncedSimulation.ts` (qui
  appelle `runComparisonSimulation` de `simulationCompareApi.ts`, le
  client de cette même route) a **8/8 fonctions couvertes (100 %)** par
  son propre test unitaire (`useDebouncedSimulation.test.ts`) — et
  **zéro** autre référence dans tout `voter-app/src/` (`grep -rn
  "useDebouncedSimulation" src/` ne retourne que le hook et son test).
  `npx knip` ne le signale **pas** comme fichier mort : son import depuis
  son propre fichier de test constitue, pour l'analyse de reachabilité de
  knip, une arête d'usage valide — c'est le comportement voulu de l'outil
  (un test est une raison légitime d'importer quelque chose), mais ça crée
  exactement l'angle mort que cette expérience cherchait : « importé »
  (knip content) et « unitairement couvert à 100 % » (pytest-cov/Vitest
  contents) sans qu'aucun des deux signaux ne puisse dire « mais jamais
  monté par un vrai routeur ».

C'est la trouvaille la plus utile du lot : ni la détection statique ni la
couverture unitaire, seules ou combinées, n'auraient signalé ce cas — il a
fallu croiser « y a-t-il une route qui monte réellement ce composant » (une
question que seule une vraie suite e2e, ou une lecture manuelle du graphe
de routage, peut poser).

### Trouvaille n°3 — les fiches du Laboratoire : 62 au total, ~2 déclenchent le backend en e2e

`voter-app/src/components/lab/labCatalog.tsx:6-8` (commentaire du fichier,
vérifié en comptant les entrées du catalogue) : « 53 former anchor leaves +
the strategy panel split into its four modules + ballot + values + the
methods duel, matrix and gallery = **62 fiches** ». `CLAUDE.md` documente
déjà que seules deux fiches du Laboratoire (plus le mode Assemblée)
frappent réellement le backend en e2e — cette expérience quantifie l'effet
côté backend : `api/domain/election/workers.py` (617 lignes, 85 %
unitaire) tombe à **6 %** e2e ; `workers_advanced.py` (688 lignes, 92 %
unitaire) à **9 %** ; `workers_behavioral.py`, `workers_dynamics.py`,
`workers_mechanisms.py`, `workers_playground.py` suivent le même profil
(85-95 % unitaire, 4-9 % e2e). Contrairement aux deux trouvailles
précédentes, **ce n'est pas une anomalie** : c'est la version chiffrée,
attendue, du phénomène général que Lot 6 pose en question — la plupart des
fiches sont volontairement des calculs client (Web Worker, simulation
spatiale) ou ne sont visitées par aucun test e2e nommé, seulement montées
en masse par le test de balayage (« every fiche mounts ») qui vérifie
qu'elles s'affichent sans planter, pas qu'elles calculent quoi que ce soit
côté serveur.

### Coût observé de l'instrumentation — pourquoi ça reste un script manuel

Isolé (un seul test, un seul run), l'instrumentation Istanbul coûte
**~60 %** de temps en plus (2,7 s → 4,3 s sur le test le plus lourd du
frontend, « the strategic-vulnerability module runs and lists methods » —
une simulation client CPU-intensive, cf. le commentaire `fullyParallel:
false` de `playwright.config.ts`). Sous la suite complète (8 workers en
parallèle, la config par défaut), ce même test a **échoué par timeout
(30 s) sur firefox, de façon reproductible sur 2 runs indépendants sur
2** — la surcharge par-test reste modeste isolément, mais la contention
CPU entre plusieurs simulations lourdes instrumentées tournant en même
temps sur des workers concurrents suffit à faire déborder un budget qui
tient normalement (3,8 s sans instrumentation, mesuré sur la suite
complète non instrumentée, 218/218 passés, 0 échec, 55,9 s). Le temps
mur total du script (démarrage backend + suite + génération des deux
rapports) reste comparable à la normale (~99 s vs ~90 s documentés par
`CLAUDE.md` pour la suite seule) — ce n'est donc pas un problème de coût
CPU/temps total, mais un problème de **stabilité** localisé à un test
précis sous forte parallélisation.

## Ce que ça a coûté

~5h au total : ~1h de recherche/vérification d'outillage frontend (Vite 8,
compatibilité Istanbul, alternative V8) ; ~1h30 à diagnostiquer et corriger
le piège `coverage run -m uvicorn` (lecture du code source d'uvicorn,
plusieurs itérations de test manuel avant de faire confiance au
correctif) ; ~1h à découvrir et corriger la contamination par le process
tiers sur le port 4434 (trois passes complètes de la suite avant que le
chiffre bizarrement plat n'attire l'attention, puis diagnostic et
correctif) ; ~1h30 de vérification manuelle des trouvailles (routes,
imports, `knip`, lecture directe du code) et de rédaction. Aucune nouvelle
dépendance de production ; deux dépendances de dev frontend
(`vite-plugin-istanbul`, `nyc`), zéro nouvelle dépendance backend
(`coverage.py` déjà présent).

## Verdict et pourquoi

**Adopté comme outil diagnostique, pas comme gate.** `scripts/
e2e_coverage.sh` produit deux rapports réels et reproductibles
(`fast_api_voter/htmlcov-e2e/`, `voter-app/coverage-e2e/`) à lancer à la
demande — pas de job CI, même non-bloquant. Deux raisons concrètes,
distinctes du choix « manuel » pour, par exemple, `schemathesis.yml` ou
`flaky-check-backend.yml` (qui tournent nightly sans souci) :

1. **Instabilité reproduite, pas seulement suspectée** — le même test
   échoue de la même façon sur 2/2 runs complets sous instrumentation,
   jamais sous les mêmes conditions sans elle. Committer ça en CI nightly
   produirait un signal rouge récurrent sans rapport avec une vraie
   régression, exactement le bruit que ce plan (Lot 5) a par ailleurs
   travaillé à éliminer côté backend.
2. **La valeur du signal ne se dégrade pas entre deux exécutions** — Lot 6
   demande une photo ponctuelle (« qu'est-ce qui est mort en usage réel »),
   pas une tendance à surveiller commit après commit comme la couverture
   unitaire ou le score de mutation. Un script que quelqu'un lance après
   une passe de nettoyage majeure (le contexte même de cette expérience)
   sert exactement à ça.

## Ce que j'en retiens (transférable à un autre projet)

1. **Un arrêt « propre » (logs de shutdown gracieux) ne garantit pas
   qu'un mécanisme basé sur `atexit` s'exécute.** Un serveur qui se
   re-signale lui-même en fin de cycle de vie pour préserver un code de
   sortie correct (un idiome courant, pas un bug d'uvicorn) tue le process
   par signal brut après le nettoyage Python — invisible dans les logs,
   qui montrent un arrêt normal. La seule parade fiable trouvée :
   intercepter le signal *avant* que le composant tiers n'installe le
   sien, pour agir au moment exact où il se re-signale.
2. **Un healthcheck HTTP qui répond ne prouve pas qu'il répond depuis LE
   process qu'on croit avoir démarré** — surtout sur un port par défaut
   documenté et donc probable candidat à occupation par autre chose dans
   un environnement partagé. Le service tiers a fait échouer mon serveur
   silencieusement (`address already in use` noyé dans les logs, jamais
   grep'é avant la première conclusion) pendant que le sondage de
   disponibilité réussissait quand même contre l'autre process. Un
   rapport de couverture qui « a l'air plausible » (des pourcentages
   raisonnables sur des fichiers réels) n'est pas une preuve qu'il mesure
   ce qu'on croit — vérifier la provenance réelle des données (ici : `grep
   "Started server process"` / `"address already in use"` dans le log
   du process qu'on a soi-même lancé) avant de publier un chiffre.
3. **Un import depuis un fichier de test suffit à satisfaire un graphe de
   reachabilité statique (knip et consorts), mais ne prouve rien sur
   l'usage réel.** C'est un comportement voulu de ces outils (tester
   quelque chose est un usage légitime), pas un bug — mais ça veut dire
   qu'aucune combinaison de détection statique + couverture unitaire ne
   peut, par construction, distinguer « câblé dans l'app » de « câblé
   seulement dans son propre test ». Seule une preuve d'exécution sous
   usage réel (e2e, ou lecture manuelle du graphe de montage des routes)
   ferme cet angle mort.
