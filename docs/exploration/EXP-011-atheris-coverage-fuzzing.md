# EXP-011 — `atheris` : est-ce vraiment plus profond qu'Hypothesis seul sur le moteur et les parseurs ?

- **Date** : 2026-09-11 · **Statut** : adopté (workflow CI planifié, non-bloquant) · **Coût réel** : ~3h (recherche `atheris` vs `hypofuzz`, lecture du moteur + grep des parseurs, écriture des deux harnais, 3 cycles trouvaille→correction→test, campagnes réelles, câblage CI)
- **Verdict en une phrase** : oui, mais modestement et vite — deux harnais (26 fonctions du moteur de vote, 9 parseurs de réponses LLM) ont trouvé 3 crashes réels dans les toutes premières secondes de fuzzing (tous corrigés avec un test de régression), zéro nouveau crash sur 5 minutes supplémentaires par harnais une fois corrigés, et un 4ème bug trouvé en lisant le code avant même d'écrire le harnais — la profondeur promise par l'item est réelle sur les formes d'entrée qu'Hypothesis ne peut structurellement pas générer, mais la surface de ce code sature vite pour un fuzzer à couverture.

## Hypothèse de départ

`PLAN_SOLIDITE_TECHNIQUE.md` (Lot 9) pose la prémisse sans la prouver :
« bien plus profond qu'Hypothesis seul sur le moteur et les parseurs ». Ce
backend a déjà une suite Hypothesis substantielle
(`test_hypothesis_condorcet.py`, `test_hypothesis_monotonicity.py`,
`test_hypothesis_legitimacy.py`, plus le fuzzing de contrat Schemathesis du
Lot 3) — avant d'écrire le moindre harnais, deux questions à trancher avec
des faits, pas des suppositions : (1) `atheris` ou `hypofuzz` — deux outils
réellement différents, pas des synonymes ; (2) est-ce que ça trouve
vraiment quelque chose que la suite existante ne trouve pas, ou est-ce que
la prémisse de l'item ne tient pas (encore) à la taille actuelle de ce
code ?

## Protocole

### 1. `atheris` vs `hypofuzz` — vérifié en direct, pas supposé

| | `atheris` | `hypofuzz` |
|---|---|---|
| Licence | Apache-2.0 (OSI) | `LicenseRef-HypoFuzz` (licence custom, pas OSI) — gratuit pour usage « non commercialement supporté » uniquement, modification/redistribution interdites sans permission écrite |
| Mainteneur | Google, toujours actif (`gh api repos/google/atheris` : `isArchived: false`, dernier push 2026-06-17) | Zac Hatfield-Dodds (mainteneur de Hypothesis lui-même), dépôt non archivé mais dernier commit 2026-05-15 |
| Dernière release PyPI | 3.1.0 | 25.11.1 (novembre 2025 — ~6 mois derrière le dernier commit du dépôt) |
| Python 3.14 (pin de ce repo) | Wheel `cp314` **téléchargée et installée avec succès** (`pip download atheris --python-version 314 --only-binary=:all:` → `atheris-3.1.0-cp314-cp314-manylinux2014_x86_64.whl`, 36,8 Mo) | Classifier PyPI annonce 3.14, non vérifié par une install réelle (jugé inutile une fois `atheris` retenu) |
| Intégration avec Hypothesis | Bridge non officiel/fragile (API interne `ConjectureData.for_buffer`) ou harnais `FuzzedDataProvider` indépendant — **choisi ici** | Réutilise directement les stratégies `@given` déjà écrites dans ce repo — le fit technique le plus naturel sur le papier |

`hypofuzz` aurait été le choix le plus "naturel" vu que ce repo écrit déjà
des stratégies Hypothesis abondamment. Écarté quand même : sa licence
autorise cet usage précis (projet personnel/pédagogique, non commercial)
mais reste une ambiguïté que ce dépôt évite systématiquement pour ses
dépendances de PRODUCTION (`scripts/check_license_compliance.sh` n'accepte
qu'une liste explicite de licences permissives) — pas de raison de
l'accepter côté dev quand une alternative Apache-2.0, tout aussi
fonctionnelle et vérifiablement mieux maintenue en ce moment, existe.
`atheris` retenu.

### 2. La cible réelle — grep avant d'écrire un harnais

Lecture de `simulation_ranked_utils.py` (1153 lignes, 21 règles ordinales +
Kemeny-Young) et `simulation_score_utils.py` (579 lignes, 12 fonctions
cardinales). Puis grep systématique de tout ce qui ressemble à un parseur
d'entrée non fiable dans `api/` : la quasi-totalité des hits (`json.loads`,
`csv`, `UploadFile`) sont soit de la validation Pydantic sur le corps de
requête HTTP (déjà couverte par `test_schema_contract.py`/Schemathesis, Lot
3), soit du chargement de config/logs **de confiance** (repo-controlled,
jamais untrusted). Un seul point du backend décode du texte qui n'est ni
l'un ni l'autre : la réponse brute d'un LLM
(`api/domain/polity/llm_client.py`) — 9 fonctions quasi-identiques
`decode_*_batch` (`decode_vote_batch`, `decode_candidacy_batch`,
`decode_party_nomination_batch`, `decode_positioning_batch`,
`decode_response_batch`, `decode_pressure_batch`, `decode_reaction_batch`,
`decode_chamber_batch`, `decode_coalition_batch`), chacune : strip regex
`<think>...</think>` → `json.loads` → `pydantic.model_validate` →
vérification d'alignement cid/party_id contre ce qui a été demandé. C'est
le seul « parseur » réel de ce backend, et la cible exacte de l'item.

### 3. Deux harnais, deux stratégies de génération

`fast_api_voter/scripts/fuzz_engine.py` — pas de mutation d'octets bruts
(`Any` en entrée ne se prête pas à ça) : un `FuzzedDataProvider` construit
des profils de vote structurés mais délibérément malformés — bulletins
vides/dupliqués, candidats unicode/vides tirés d'un pool volontairement
**petit et fixe** (pour ne pas faire exploser le chemin exact O(n!) de
`get_kemeny_young_winner` au-delà de `_KY_EXACT_CAP=6`), enveloppes dict
sans le format attendu, scores cardinaux NaN/inf. Exactement les formes que
`st.permutations(["A","B","C","D"])` (les strategies Hypothesis existantes)
ne peuvent structurellement jamais produire, puisqu'une permutation est par
construction complète et sans doublon.

`fast_api_voter/scripts/fuzz_llm_parsers.py` — mutation directe des octets
bruts en texte (`ConsumeUnicodeNoSurrogates`), pas de construction
programmatique : les bugs intéressants ici sont dans le PARSING lui-même
(encodage, comportement d'une regex, récursion, logique d'alignement), pas
dans une structure Python qu'on construirait à la main. Corpus de départ
committé (`fuzz_corpus/llm_parsers/seed_*`, 6 fichiers) : un batch valide,
un batch encadré de balises `<think>`, un batch schema-invalide, du texte
non-JSON, un batch avec des champs `extra`.

### 4. Trois cycles trouvaille → correction → test, en direct

Discipline systématique de ce plan (EXP-002, EXP-004, EXP-006) : ne jamais
fabriquer une trouvaille, mais aussi ne pas laisser un vrai crash sans
correction + test de régression avant de continuer. Trois crashes réels
distincts, tous trouvés dans les toutes premières exécutions d'une campagne
courte (quelques secondes à quelques dizaines de secondes), avant même le
premier run de 5 minutes :

1. **`calculate_bayesian_regret` — trouvé en 13 exécutions.** Un bulletin
   vide (`{}`, un votant qui n'a noté personne) : `max(vote.values())`
   plante avec un `ValueError: max() iterable argument is empty` — et pas
   seulement pour ce votant : la boucle externe est `for candidate in
   candidates`, donc UN bulletin vide fait planter le calcul de régret pour
   TOUS les candidats. Repro minimal : `calculate_bayesian_regret([{"A":
   5}, {}])`. Corrigé : les bulletins vides sont exclus (numérateur ET
   dénominateur du calcul de moyenne), même convention que
   `vote.get(candidate, 0)` traite déjà un candidat absent comme 0 ailleurs
   dans ce même fichier. Test de régression :
   `test_bayesian_regret_skips_a_ballot_that_rated_nobody`
   (`api/tests/test_cardinal_score_and_regret.py`).
2. **`get_nanson_winner` / `get_baldwin_winner` — trouvé en ~92
   exécutions.** `votes` non vide mais dont CHAQUE bulletin classe zéro
   candidat (`[[]]`, distinct de `votes == []` qui est déjà géré) :
   `all_cands` reste vide, et le fallback `return min(all_cands)` plante
   sur une liste vide. Deux fonctions sœurs du même fichier
   (`get_benham_winner`, `get_smith_irv_winner`) ont déjà la garde correcte
   juste à côté (`if not all_cands: return None`) — Nanson et Baldwin
   avaient simplement divergé de cette convention. Corrigé en ajoutant la
   même garde aux deux. Tests :
   `test_nanson_every_ballot_empty_has_no_winner`,
   `test_baldwin_every_ballot_empty_has_no_winner`.
3. **`get_majority_judgment_winner` — trouvé en ~85 exécutions.**
   L'ensemble des candidats était dérivé du PREMIER votant seulement
   (`list(utility_scores[0].keys())`) ; un votant suivant notant un
   candidat que le premier n'avait pas noté (`[{"A": 0.9}, {"B": 0.1}]`)
   fait planter `all_grades[c]` avec un `KeyError`, puisque ce dict n'était
   pré-rempli qu'avec les clés du premier votant. Corrigé en réutilisant
   `_score_candidates` — le helper « union de tous les votants, ordre de
   premier-vu » déjà utilisé par `get_cumulative_winner`/
   `get_maximin_score_winner`/`get_nash_winner` dans le même fichier — au
   lieu de dupliquer la logique de voter-0-seulement. En creusant la même
   fonction voisine, `get_evaluative_winner` avait exactement le même
   défaut de conception SANS planter (le candidat non vu par le premier
   votant disparaissait silencieusement du résultat entier, jamais une
   exception) — corrigé par cohérence, même si ce n'est techniquement pas
   un crash trouvé par le fuzzer lui-même. Tests :
   `test_majority_judgment_a_later_voters_extra_candidate_does_not_crash`,
   `test_evaluative_a_later_voters_extra_candidate_is_not_silently_dropped`.

Un **4ème bug**, trouvé en amont du harnais lui-même — en lisant le code du
parseur avant d'écrire la moindre ligne de fuzzing (l'étape « grep avant
d'écrire un harnais » ci-dessus) : les 9 fonctions `decode_*_batch` ne
rattrapent que `json.JSONDecodeError` autour de `json.loads`. Le parseur
JSON de la bibliothèque standard descend récursivement dans les tableaux
imbriqués ; à ~10⁵ crochets `[` imbriqués (confirmé reproductible et
déterministe depuis un interpréteur neuf — la valeur exacte de bascule
dépend de la pile C déjà utilisée par l'appelant, non stable, mais 10⁵ est
largement au-delà de tout seuil observé), il déborde la pile C **avant**
d'avoir la chance de lever son propre `JSONDecodeError` — un
`RecursionError` non rattrapé s'échappe alors de la fonction. Un LLM
bloqué dans une boucle de répétition dégénérée (un mode de panne réel et
documenté des modèles de langage) peut produire exactement cette forme.
Corrigé : `except RecursionError` ajouté aux 9 fonctions (la première avec
une explication complète, les 8 suivantes avec un pointeur court — même
convention de documentation que ce fichier applique déjà pour ses
fonctions dupliquées). Test :
`test_decode_vote_batch_rejects_deeply_nested_json_without_crashing`
(`api/tests/test_polity_llm_client.py`), avec 100 000 crochets imbriqués.

**Note méthodologique honnête sur ce 4ème bug** : une campagne de fuzzing
par mutation d'octets ne l'aurait probablement pas trouvé seule dans un
budget de temps raisonnable. La couverture qu'`atheris` instrumente est au
niveau du bytecode Python ; le parseur JSON de `json.loads` est implémenté
en C (l'accélérateur `_json`) et exécute EXACTEMENT le même chemin de code
à chaque niveau d'imbrication supplémentaire — rien dans le signal de
couverture ne récompense donc le mutateur pour empiler des crochets plus
profondément, puisque empiler un crochet de plus ne change aucune ligne de
bytecode Python exécutée. C'est un angle mort structurel du fuzzing
guidé-par-couverture bytecode-level sur du code dont la récursion
dangereuse vit dans une extension C, pas une preuve que le harnais était
mal conçu.

### 5. Campagne réelle post-corrections, chiffres mesurés

5 minutes par harnais (`-max_total_time=300`), machine de dev locale,
après les 4 corrections ci-dessus :

| Harnais | Exécutions | Couverture finale (`cov`/`ft`) | Corpus découvert | Nouveaux crashes |
|---|---|---|---|---|
| `fuzz_engine.py` | **242 108** (804 exec/s) | 1160 / 4831 | 563 entrées, 24 Ko | 0 |
| `fuzz_llm_parsers.py` | **44 410 242** (147 542 exec/s) | 48 / 48 | 21 entrées, 59 o | 0 |

Le contraste de débit entre les deux (804 exec/s contre ~147k exec/s, soit
~183x)
s'explique entièrement par le travail fait par exécution : le harnais
moteur appelle jusqu'à 25 fonctions de vote (dont certaines O(n²)/O(n³))
sur des profils pouvant aller jusqu'à 30 bulletins, quand le harnais
parseur passe l'essentiel de son temps dans un `json.loads` qui échoue en
microsecondes sur du texte aléatoire.

## Ce que ça a trouvé

Quatre bugs réels, tous corrigés avec un test de régression minimal — voir
le détail du protocole ci-dessus. Aucun n'était accessible en pratique par
un appelant actuel de ce backend (`api/schemas/simulations.py` borne
`NumVoters`/`NumRounds`, donc les bulletins qui atteignent le moteur
aujourd'hui sont internes et bien formés ; les payloads LLM, eux, sont par
nature non fiables et c'est exactement pour ça que ce fichier existe) —
mais c'est précisément le point de l'item : une fonction aussi centrale que
le moteur de vote ne devrait pas planter sur une forme d'entrée
malformée-mais-plausible, indépendamment de la discipline de ses appelants
actuels.

Passé ces quatre corrections, **zéro nouveau crash sur 5 minutes
supplémentaires par harnais** (242 108 exécutions moteur, 44 410 242
exécutions parseur — chiffres exacts des logs de campagne, pas des
estimations). Verdict honnête, pas gonflé : sur la taille actuelle
de ce code (26 fonctions pures pour le moteur, 9 fonctions quasi-
identiques pour les parseurs), la surface explorable par un fuzzer à
couverture sature vite — les couvertures se stabilisent en quelques
secondes de campagne (`cov: 1158` dès l'exécution #85 sur une campagne de
test antérieure, avant même la fin de la première minute), et le reste du
budget temps ne fait que re-confirmer l'absence de régression plutôt que
découvrir du nouveau territoire.

## Ce que ça a coûté

~3h : ~45 min de recherche `atheris` vs `hypofuzz` (licences, fraîcheur,
compatibilité Python 3.14, vérifiée en téléchargeant réellement les deux
wheels/paquets plutôt qu'en lisant seulement une page web) ; ~30 min de
lecture du moteur + grep des parseurs candidats avant d'écrire quoi que ce
soit ; ~1h d'écriture des deux harnais (dont la découverte au vol du
comportement front/back de `FuzzedDataProvider.Consume*`, qui a changé la
façon dont les corpus de départ sont paddés) ; ~45 min pour les 4 cycles
trouvaille→correction→test ; ~20 min de câblage CI
(`atheris-fuzzing.yml`, `.gitignore`, `requirements-dev.txt`). Une nouvelle
dépendance de dev (`atheris==3.1.0`), zéro dépendance de production, zéro
faux positif rencontré une fois les harnais stabilisés (le seul « faux
positif » — un dict LLM sans clé `ranking`, un contrat déjà documenté comme
requis — a été retiré du générateur plutôt que gardé comme trouvaille, voir
le commentaire dans `fuzz_engine.py`).

## Verdict et pourquoi

**Adopté**, mais avec un récit honnête sur ses limites plutôt qu'un
argumentaire de vente :

1. **La prémisse de l'item tient, mais modestement.** Les 4 bugs trouvés
   sont des formes d'entrée qu'aucune stratégie Hypothesis existante dans
   ce repo n'aurait pu générer (bulletin vide, tous-bulletins-vides,
   candidat asymétrique entre votants, imbrication JSON pathologique) —
   c'est bien « plus profond ». Mais le volume est modeste (4 bugs, tous
   trouvés en quelques dizaines de secondes cumulées) et la surface sature
   vite pour ce code de cette taille — ne pas prétendre que 5 minutes
   supplémentaires par harnais auraient trouvé un 5ème bug qui n'existe
   probablement pas.
2. **Jamais un gate de PR, jamais bloquant** — même arbitrage que
   `mutation-testing.yml`/`schemathesis.yml` (déjà établis dans ce repo
   pour la même raison : une vraie campagne de fuzzing à couverture a
   besoin de minutes, pas de secondes, pour valoir plus que ce
   qu'Hypothesis donne déjà gratuitement). `atheris-fuzzing.yml` :
   planifié (jeudi 04:44 UTC, hors du cluster lundi matin déjà chargé par
   3 autres jobs), `workflow_dispatch` avec un budget configurable, corpus
   persisté via `actions/cache` (même mécanisme que le cache incrémental
   de Stryker) pour que la valeur composera d'une exécution nocturne à
   l'autre plutôt que de repartir de zéro à chaque fois.
3. **Un crash trouvé en CI devient un artefact téléchargeable, jamais un
   échec silencieux qui disparaît** — même discipline de reproductibilité
   que `scripts/check_flaky_backend.py` : les octets exacts qui ont fait
   planter le harnais sont uploadés (90 jours de rétention), et se
   rejouent localement avec le même script
   (`python scripts/fuzz_engine.py <fichier>`).

## Ce que j'en retiens (transférable à un autre projet)

1. **La profondeur d'un fuzzer par rapport à des tests de propriété
   existants dépend de la LARGEUR des stratégies existantes, pas
   seulement de leur existence.** Ce repo avait déjà des tests Hypothesis
   sur ce code — mais des stratégies étroites (`st.permutations` sur un
   alphabet fixe de 4 candidats) qui ne pouvaient structurellement jamais
   produire les formes qui ont réellement cassé le code (bulletins vides,
   candidats asymétriques). Un fuzzer à couverture gagne exactement là où
   les stratégies existantes ont un angle mort de FORME, pas de volume
   d'exemples.
2. **La couverture bytecode-level a un angle mort structurel sur la
   récursion vivant dans une extension C** — le `RecursionError` de
   `json.loads` n'aurait probablement jamais été trouvé par la campagne
   elle-même, seulement par la lecture de code qui a précédé son écriture.
   Un harnais de fuzzing ne remplace pas la lecture de code ciblée ; il la
   complète sur un axe différent (formes d'entrée), pas sur tous les axes.
3. **Vérifier la licence ET la fraîcheur d'un outil « évident » avant de
   l'adopter change parfois la décision** : `hypofuzz` était le choix
   techniquement le plus naturel (réutilise directement les stratégies
   Hypothesis existantes) mais a été écarté sur des critères vérifiés en
   direct (licence non-OSI, cadence de release ralentie), pas sur une
   préférence a priori pour l'outil open-source — même réflexe que le
   rejet de Lost Pixel (EXP-004) et le remplacement `license-checker` →
   `license-checker-rseidelsohn` (Lot 6.7).
4. **Un harnais de fuzzing doit générer des DONNÉES malformées, pas
   violer le CONTRAT de son propre appelant** — la première version de
   `fuzz_engine.py` omettait parfois la clé `ranking` d'un bulletin
   dict-format ; ça « trouvait » un `KeyError` à chaque run, mais c'était
   une violation d'un contrat déjà documenté (`get_condorcet_winner`'s
   docstring exige `ranking`), pas une découverte. Retiré du générateur
   plutôt que gardé comme trouvaille artificielle — un fuzzer mal borné
   produit du bruit répétitif, pas de la profondeur.
