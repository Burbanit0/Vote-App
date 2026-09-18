# EXP-015 — `mutmut` : périmètre, sélection de tests et score de mutation du moteur de vote

- **Date** : 2026-08-23 → 2026-09-13 · **Statut** : adopté (gate CI, plancher à 70 %) · **Coût réel** : étalé sur trois semaines, par passes successives
- **Verdict en une phrase** : le score de mutation a mesuré la **liste de tests sélectionnée** avant de mesurer la suite elle-même — trois élargissements successifs ont déplacé le score de 58,9 % à 73,3 % *sans écrire une seule ligne de test*, et la seule panne réellement bloquante (17 jours de rouge) venait de l'incompatibilité entre le modèle in-process de mutmut 3.7.0 et le garde-fou de réinitialisation de numpy 2.4+.

> Ce carnet rassemble l'historique qui vivait en commentaires dans
> `fast_api_voter/pyproject.toml` (177 lignes de commentaire pour 52 lignes de
> config). La config n'y garde que ce qui explique une clé à son point d'usage ;
> le raisonnement, les dates et les verdicts sont ici.

## Hypothèse de départ

La couverture de ligne dit qu'une ligne a été *exécutée*, pas qu'un test
*assert* dessus. Le moteur de vote (`simulation_ranked_utils.py`,
`simulation_score_utils.py`) est verrouillé côté client par le harnais de parité
(`playgroundVoting.parity.test.ts`), donc une assertion manquante s'y paie
doublement. L'hypothèse : un score de mutation révélerait des déficits
d'assertion que 90 % de couverture masquent.

## Protocole

`mutmut` sur deux fichiers moteur au départ, avec `mutate_only_covered_lines`
(les lignes non couvertes produisent des survivants garantis et inintéressants),
une sélection de tests explicite, et un plancher vérifié en CI par
`scripts/check_mutation_score.sh`.

## Ce que ça a trouvé

### 1. Le score mesurait la sélection, pas la suite

La sélection de tests était **manuelle**. Première version : 12 + 2 fichiers sur
les 80 de `api/tests/`, avec une mise en garde interne listant neuf fonctions
(condorcet, two_round, plurality, approval, minimax, copeland, nanson, baldwin,
kemeny) comme « sans fichier de test dédié ». Elles en avaient toutes un — il
n'était simplement pas sélectionné.

| Action | Score | Survivants |
|---|---|---|
| Liste initiale (14 fichiers) | 58,9 % | 714 |
| Élargie à 25 fichiers, **zéro test écrit** | 64,2 % | 621 |

La leçon tient en une phrase : une liste de sélection maintenue à la main
devient elle-même la chose mesurée. Elle est désormais **dérivée** — la recette
`grep` qui la régénère vit dans `pyproject.toml`, à côté de la liste.

Le même piège s'est reproduit : après l'ajout de `test_anonymity.py` et
`test_cardinal_orphans.py` (correctif des départages de 13 règles), le score a
*baissé* (64,2 % → 63,2 %) malgré 13 bugs réels corrigés et 96 tests ajoutés —
parce que ni l'un ni l'autre n'avait été ajouté à la liste. Les tests écrits
pour attraper ces bugs n'ont jamais tourné sous mutmut.

### 2. Le module cardinal avait un vrai déficit d'assertion

L'élargissement a levé une ambiguïté que l'ancienne mise en garde laissait
ouverte :

```
simulation_ranked_utils   440 → 337 survivants (71,3 %)
simulation_score_utils    284 → 284 survivants (51,7 %)  ← pas un seul mutant
```

Tous les fichiers ajoutés testaient une règle **ordinale**, donc le module
cardinal n'a pas bougé d'un mutant. 51,7 % était un déficit d'assertion réel, pas
un artefact de sélection.

`test_cardinal_orphans.py` a couvert les six règles jamais testées en assertant
sur **les nombres**, pas seulement sur le vainqueur : `median_voting`,
`mean_median_hybrid`, `variance_based`, `score_distribution_analysis` (depuis
supprimée — seuls ses tests l'appelaient), `majority_judgment`, `evaluative`.
Score combiné : **73,3 %** (1397/1906) au run suivant.

Deux trous supplémentaires ont été trouvés **en lisant**, pas en mesurant
(l'artefact `.mutmut-cache` de CI était vide) : la branche de départage itératif
de `get_majority_judgment_winner` (ne se déclenche que si deux candidats sont à
égalité sur la médiane **et** la jauge) n'était atteinte par aucun test, et sa
sortie `scores` n'était assertée nulle part.

### 3. La panne bloquante : numpy 2.4+ contre le modèle in-process de mutmut

Du **2026-08-29 au 2026-09-13** (≈17 runs, tous les push et tous les
déclenchements planifiés), le job entier échouait de façon déterministe avant de
produire le moindre score :

```
ImportError: cannot load module more than once per process
```

…en collectant l'`import numpy` de `test_anti_plurality.py`, pendant la passe de
collecte de stats de mutmut. **Pas flaky : 17 jours de suite.**

Cause racine confirmée, pas seulement circonstancielle : numpy 2.4+ a ajouté un
garde-fou refusant de réinitialiser son extension C dans le même processus
([numpy/numpy#29030](https://github.com/numpy/numpy/issues/29030), même famille
de panne que [DataDog/dd-trace-py#18276](https://github.com/DataDog/dd-trace-py/issues/18276)).
Le modèle de re-exec in-process de mutmut 3.7.0 fait exactement cela.

mutmut 3.8.0 corrige ce cas précis (« gather coverage in a separate process »,
#528/#566). Vérifié localement en reproduisant le crash sur 3.7.0 puis en
confirmant que 3.8.0 passe la collecte de stats et entre dans le test de mutants
réel — même config, même numpy 2.5.2, même Python 3.14.7 qu'en CI.

### 4. Le correctif a triplé le nombre de mutants — et ce n'était pas une régression

Premier score post-correctif : **64,4 % (4063/6322)**, sous le plancher de 70 %.
Ce n'était pas « 17 jours de décomposition » : le nombre total de mutants a plus
que **triplé** (1906 → 6322) par rapport à la baseline de 73,3 %.

Le codebase n'a pas triplé. C'est le correctif de couverture de 3.8.0
(collecte en processus séparé) qui reconnaît désormais bien plus de lignes
couvertes que le modèle in-process de 3.7.0 ne pouvait le faire — la même
famille de sous-comptage silencieux que le crash, simplement pas assez sévère
partout pour planter. La plupart des ~2245 survivants sont des mutants qui
n'étaient **jamais générés** avant, pas des mutants sur lesquels la suite a
régressé.

Confirmé réel et corrigeable sur un cas concret : `is_dict = _is_dict_format(votes)`
→ `is_dict = None` survivait sur **toutes** les règles qui le lisent (19+
fonctions partageant `_ballots_and_candidates`/`_build_pairwise`), parce que rien
dans la suite n'exerçait le format de bulletin enveloppé dans un dict
(`{"ranking": [...]}`) sur lequel ces fonctions branchent explicitement.
`test_ballot_dict_format.py` a fermé ce trou : **58 mutants passés de survivant à
tué** (64,4 % → 65,2 %), exactement là où c'était prédit.

### 5. Deuxième passe : `get_star_voting_winner`

La fonction la moins bien couverte des deux fichiers moteur (**57 survivants**,
plus que toute autre). Toutes les fixtures STAR existantes utilisaient exactement
deux candidats, notés de façon assez semblable pour que l'accumulateur du premier
tour, les compteurs du second et les valeurs par défaut `.get(candidate, 0)`
puissent **tous** être faux sans jamais changer lequel des deux gagnait.

`test_star_runoff_tie.py` a ajouté les cas où chacun compte pour de vrai : une
victoire d'outsider au second tour, un bulletin qui omet un finaliste, deux
bulletins à égalité et non un, un candidat noté par exactement un bulletin.
**53 des 57 fermés** (65,2 % → 66,1 %).

Les 4 restants sont des **mutants équivalents confirmés** (la branche
`data["count"] > 0` est inatteignable par construction : tout candidat présent
dans `candidate_scores` y a été ajouté par au moins un bulletin), documentés dans
la docstring de ce fichier plutôt que laissés sans explication.

## Décisions de périmètre

**`api/domain/theory/workers.py`** a d'abord été exclu — non par choix, mais par
incompatibilité outillage : sa seule couverture passait par le `TestClient` de
FastAPI (`test_theory_batch1-4.py`), et toute tentative d'inclure un test basé sur
`TestClient` cassait reproductiblement (3×) avec « NumPy module reloaded » +
erreurs asyncio « cancelled via cancel scope » / « invalid state ». La même
invocation pytest, mêmes flags, tourne proprement **hors** mutmut — ce qui isole
le problème au modèle de re-exec de mutmut, pas à la suite de tests.

L'incompatibilité vit dans les **fichiers de test** (couplage `TestClient`), pas
dans `workers.py` : le module n'a aucun couplage FastAPI/Pydantic propre.
`test_theory_pure.py` appelle 11 de ses 15 fonctions `_xxx_worker(data: dict) ->
(body, status)` directement avec un dict simple, sans `TestClient`/`fastapi`/`numpy`
— donc mutmut peut le sélectionner, et le fichier a été ajouté.

Les 4 workers restants (`_plott_chaos_worker`, `_agenda_manipulation_worker`,
`_manipulation_analysis_worker`, `_democratic_backsliding_worker`) touchent numpy
directement et **restent exclus** : savoir si la panne de rechargement in-process
est spécifiquement un problème `TestClient` ou un problème numpy n'est toujours
pas tranché.

## Pourquoi le plancher reste à 70 %

Le plancher est resté à 70 % et le snooze dans `.github/ci-health-snoozes.json`
en place pendant que les trous se ferment un par un. Relever le plancher à un
chiffre que personne n'a encore gagné serait exactement le raccourci
« faire passer un run rouge au vert » contre lequel `check_mutation_score.sh`
met lui-même en garde.

## Prochain chantier

`get_simple_score_winner` est la seule fonction du module cardinal sans fixtures
adverses choisies à la main — à reprendre dès qu'une liste de survivants fraîche
est disponible.

## Ce qui reste dans `pyproject.toml`

Seulement ce qui explique une clé à son point d'usage, et qui se lirait mal
ailleurs :

- pourquoi `also_copy = ["api/"]` (les tests vivent en `api/tests/`, pas au
  `tests/` racine que mutmut suppose) ;
- pourquoi `mutate_only_covered_lines` ;
- pourquoi `pytest_add_cli_args = ["-o", "addopts="]` — un vrai piège : sans
  cette neutralisation, le `--cov-fail-under` du projet ferait sortir chaque run
  de mutant en non-zéro quel que soit le sort du mutant, **corrompant le signal
  tué/survivant** ;
- la recette `grep` qui régénère la sélection de tests.
