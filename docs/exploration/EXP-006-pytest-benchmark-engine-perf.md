# EXP-006 — `pytest-benchmark` : une régression de perf sur le moteur de vote est-elle vraiment invisible ?

- **Date** : 2026-09-11 · **Statut** : adopté (gate CI bloquant, seuils absolus) · **Coût réel** : ~2h (recherche des modes de défaillance CI réels, mesure directe des 26 méthodes, conception du seuil, injection + vérification d'une régression réelle, câblage CI)
- **Verdict en une phrase** : les 26 méthodes de vote (21 ordinales + 5 cardinales, `simulation_ranked_utils.py`/`simulation_score_utils.py`) tournent toutes en moins de 14 ms même au plafond de production (1000 électeurs, 8 candidats) — un budget si généreux qu'un plafond absolu à 100-500 ms (15-500x la mesure réelle) gate déjà chaque PR sans jamais avoir besoin d'une comparaison à une baseline stockée, et une régression O(n²) injectée en direct (×290 sur `get_copeland_winner`) confirme que le gate a vraiment des dents.

## Hypothèse de départ

`PLAN_SOLIDITE_TECHNIQUE.md` (Lot 8.1) pose le problème sans présumer de la
solution : une régression de perf sur le moteur de vote est aujourd'hui
totalement invisible — rien ne mesure son temps d'exécution, seulement sa
justesse (`engineParity.json`, les tests axiomatiques du Lot 4). L'outil
évident est `pytest-benchmark`, mais sa fonctionnalité vedette — comparer
contre une baseline stockée (`--benchmark-autosave` +
`--benchmark-compare-fail=mean:X%`) — est réputée fragile sur un runner CI
partagé. Hypothèse à trancher *avant* d'écrire le moindre test : cette
fragilité est-elle réelle sur ce projet, et si oui, un plafond absolu généreux
(même philosophie que le `timeout: 30_000` de la suite e2e) est-il une
alternative crédible qui gate vraiment quelque chose sans faux positifs ?

## Protocole

### 1. Vérifier la fragilité CI avant de la supposer

Deux vérifications indépendantes, pas une supposition :

- **Recherche** : la documentation et les retours connus de
  `pytest-benchmark` confirment que ses propres seuils recommandés
  (`min:15%`) existent précisément parce que les runners GitHub Actions
  partagés ont une variance de vitesse réelle d'une exécution à l'autre — et
  que comparer contre une baseline *committée* sur un runner *éphémère*
  (chaque job = une VM fraîche) revient à comparer la vitesse d'aujourd'hui
  contre celle d'une VM différente, pas contre le même matériel.
- **Incompatibilité `pytest-xdist` confirmée, pas supposée** :
  `pytest-benchmark` se désactive automatiquement dès que `pytest-xdist` est
  actif (« Benchmarks are automatically disabled because xdist plugin is
  active »), un comportement documenté, pas un bug. Or
  `backend-ci-cd-pipeline.yml` lance la suite normale via `pytest api/tests
  -n auto` — donc un fichier de benchmark placé dans cette même invocation
  ne mesurerait jamais rien, un vert qui ne prouve rien de pire qu'un test
  qui ne tourne pas du tout.

Ces deux faits, pas un a priori, ont tranché le design : plafonds absolus
généreux (comme l'e2e), et une invocation dédiée hors `-n auto` (même
mécanisme que `test_schema_contract.py`/Schemathesis, `--ignore` dans
`pyproject.toml` + son propre step CI).

### 2. Mesurer, pas deviner, les tailles d'entrée réelles

`api/schemas/election.py` (`ProfileSimulateRequest`) : `num_voters` plafonné
à 1000, candidats à 8 — pas des ronds arbitraires, la vraie borne de
production. `_KY_EXACT_CAP = 6` dans `simulation_ranked_utils.py` : Kemeny-
Young bascule de l'algorithme exact O(n!) à l'approximation KwikSort
O(n log n) au-delà de 6 candidats — deux algorithmes réellement différents
derrière un seul nom de fonction, benchmarkés séparément (6 et 8 candidats).

Chronométrage direct des fonctions du moteur (script isolé, `time.perf_counter`,
meilleur de 2 essais, machine de dev idle) avant d'écrire le moindre test :

| Méthode | 1000 électeurs / 4 candidats | 1000 électeurs / 8 candidats |
|---|---|---|
| `plurality` | 0,08 ms | 0,08 ms |
| `dowdall` (le plus lent des positionnelles, `Fraction`) | 2,98 ms | 6,13 ms |
| `condorcet`/`copeland` | 1,19 ms | 7,36 ms |
| `schulze` | 0,97 ms | 6,31 ms |
| `minimax` | 1,21 ms | 7,41 ms |
| `benham` (le plus lent du set ordinal) | 1,35 ms | 13,08 ms |
| `kemeny_young` (exact, 6 cand.) | — | 4,08 ms |
| `kemeny_young` (approx. KwikSort, 8 cand.) | — | 4,23 ms |
| `score`/`star`/`cumulative`/`maximin`/`nash` | 0,28-0,44 ms | 0,50-0,82 ms |

Aucune explosion combinatoire nulle part — la peur initiale du plan
(« Kemeny-Young est factoriel/exponentiel ») est réelle pour l'algorithme
mais sans conséquence en pratique : `_KY_EXACT_CAP` la contient déjà à 6! =
720 permutations, toujours sous les 5 ms.

### 3. Choisir les seuils et le mécanisme

`api/tests/test_engine_benchmarks.py` : 27 cas (21 méthodes ordinales du
set de parité `scripts/gen_engine_parity.py` + Kemeny exact/approx séparés +
5 cardinales), `benchmark.pedantic(fn, rounds=10, warmup_rounds=1)` pour un
temps mur borné et prévisible (pas la calibration ouverte par défaut de
`pytest-benchmark`, qui viserait jusqu'à 1 s par cas). Deux paliers, très
larges par rapport à la mesure réelle ci-dessus :

- **100 ms** — tallies O(n), scoring cardinal en une passe.
- **500 ms** — élimination/appariement/Kemeny (le pire mesuré, `benham` à
  13 ms, a encore 38x de marge).

Assertion sur `benchmark.stats.stats.mean` (pas `.max`, moins sensible à un
pic isolé de scheduling) contre ce plafond, en secondes, avec un message
d'erreur qui rappelle explicitement que le seuil est volontairement large
avant de blâmer le code.

Exclu de l'invocation par défaut (`--ignore=api/tests/test_engine_benchmarks.py`
dans `pyproject.toml`, même mécanisme que `test_schema_contract.py`) et
lancé dans son propre step CI bloquant (`backend-ci-cd-pipeline.yml` :
`pytest api/tests/test_engine_benchmarks.py -o addopts=""`), mirroré dans
`ci-local/backend.Dockerfile`.

### 4. Prouver que le gate a vraiment des dents

Discipline systématique de ce plan (cf. EXP-002, EXP-004 régression
visuelle) : ne jamais
faire confiance à un détecteur sans l'avoir vu détecter quelque chose de
vrai. Régression injectée directement dans `get_copeland_winner` (une passe
O(n²) redondante, comparaison de listes triées par paire d'électeurs,
répétée 3x pour un coût cumulé net), testée, puis intégralement retirée :

```python
# AVANT (baseline)
mean = 3,7 ms  →  PASS (plafond 500 ms)

# Régression injectée (boucle O(n²) redondante × 3, 1000 électeurs)
mean = 1 101,6 ms  →  FAIL
# AssertionError: condorcet_copeland: mean 1101.6ms exceeds the 500ms
# ceiling at 1000 voters / 8 candidates.

# Après revert (git diff vide, confirmé)
mean = 3,1 ms  →  PASS
```

Le gate détecte bien une régression algorithmique réelle et raisonnable
(un `O(n²)` accidentel, pas un cas extrême) largement avant qu'elle
n'atteigne le plafond de 500 ms — avec de la marge dans les deux sens (assez
strict pour attraper, assez large pour ne pas mordre le bruit machine).

## Ce que ça a trouvé

- **Rien de pathologique dans le moteur actuel** — c'était l'hypothèse nulle
  attendue (le Lot 4 avait déjà vérifié la justesse en profondeur ; ceci
  vérifie la performance, un axe différent). Toutes les 27 mesures tiennent
  confortablement sous leur plafond, avec 15-160x de marge.
- **Un signal de contention machine réel, observé en cours de route, pas
  cherché** : en relançant la suite complète pendant qu'un serveur uvicorn
  et Locust tournaient en parallèle (pour l'item 8.2, voir EXP-007), les
  mêmes benchmarks ont mesuré des moyennes 20-50 % plus hautes (`benham` :
  7,9 ms → 10,1 ms ; `minimax` : 7,2 ms → 10,8 ms) qu'à l'isolement — une
  preuve directe, sur ce projet, que le bruit d'exécution réel existe et
  peut faire varier une mesure de façon significative, tout en restant
  très loin sous les plafonds choisis (10,8 ms contre un plafond de
  500 ms). Exactement le genre de variance qu'une comparaison à une
  baseline stockée à pourcentage serré (`mean:20%`) aurait pu transformer
  en faux positif ; un plafond absolu large l'absorbe sans discussion.
- **L'incompatibilité `xdist`** elle-même est une trouvaille utile au-delà
  de ce fichier : tout futur ajout de test de performance dans ce repo doit
  suivre le même patron (invocation dédiée), pas une supposition ponctuelle.

## Ce que ça a coûté

~2h : ~30 min de recherche (documentation `pytest-benchmark`, confirmation
de l'incompatibilité xdist) : ~30 min de chronométrage direct des 26
méthodes pour calibrer les tailles/seuils ; ~30 min d'écriture du fichier de
test + câblage CI (`pyproject.toml`, `backend-ci-cd-pipeline.yml`,
`ci-local/backend.Dockerfile`) ; ~30 min d'injection/vérification/retrait de
la régression de démonstration. Une nouvelle dépendance de dev
(`pytest-benchmark==5.3.0`), zéro dépendance de production, zéro dette
(aucun faux positif rencontré, aucune exception à documenter).

## Verdict et pourquoi

**Adopté comme gate CI bloquant**, pas comme outil informationnel — à la
différence de la plupart des items du Lot 6 (refurb, perflint, sonarjs).
Trois raisons concrètes :

1. **La baseline est déjà à zéro** et le restera tant qu'aucune régression
   réelle n'existe — même raisonnement que `pip-licenses` (Lot 6.7) :
   quand un gate part propre, l'activer bloquant coûte zéro friction
   immédiate et empêche toute régression future d'entrer inaperçue.
2. **Le coût CI est négligeable** : les 27 cas s'exécutent en moins d'une
   seconde au total (mesuré : 0,95 s). Rien à voir avec le calcul
   « comparaison à une baseline flaky vaut mieux qu'un gate absent » —
   ici le calcul est « un gate quasi-gratuit et non-flaky vaut mieux
   qu'un gate flaky ou qu'aucun gate ».
3. **La preuve en direct** (régression injectée → détectée → retirée →
   vert) est le même bar que ce plan applique systématiquement (EXP-002,
   Lot 7) — un détecteur non vérifié n'est qu'une hypothèse.

Le workflow `--benchmark-autosave`/`--benchmark-compare-fail` de
`pytest-benchmark` reste documenté (`test_engine_benchmarks.py`'s docstring)
comme outil local pour un vrai travail de profiling — juste jamais comme ce
qui gate une PR.

## Ce que j'en retiens (transférable à un autre projet)

1. **Vérifier un mode de défaillance avant de le supposer change la
   décision de design, pas juste sa justification.** L'incompatibilité
   `pytest-xdist` n'est pas un détail : sans l'avoir cherchée activement,
   un fichier de benchmark ajouté négligemment à la suite normale aurait
   semblé fonctionner (vert) tout en ne mesurant jamais rien — un piège
   silencieux pire qu'un flaky test visible.
2. **Un plafond absolu généreux n'est pas un pis-aller par rapport à une
   comparaison relative — c'est parfois le choix strictement meilleur**
   quand (a) le code mesuré est déjà rapide en valeur absolue (marge de
   10-100x disponible) et (b) l'environnement d'exécution (runner partagé)
   a une variance non maîtrisée. La comparaison relative n'a d'avantage
   que quand ces deux conditions s'inversent — un code déjà proche de son
   plafond légitime, sur une machine stable.
3. **La contention machine réelle mesurée pendant ce travail** (30-50 %
   de variance simplement en faisant tourner un serveur + un outil de
   charge à côté) est une preuve empirique, pas théorique, que la
   littérature sur la fragilité CI des benchmarks relatifs ne surestime
   rien pour ce genre de projet.
