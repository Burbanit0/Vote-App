# EXP-002 — Z3 : prouver plutôt qu'échantillonner sur le moteur de vote

- **Date** : 2026-09-10 · **Statut** : adopté (partiel) · **Coût réel** : ~3h (exploration, un faux résultat corrigé, écriture des tests permanents)
- **Verdict en une phrase** : Z3 prouve en quelques secondes que minimax et Schulze respectent le critère de Condorcet pour **tous** les électorats possibles (pas un échantillon) jusqu'à 7 candidats — mais une première tentative sur IRV a produit une preuve *silencieusement fausse* faute d'avoir codé fidèlement la règle de départage à égalité de ce projet, corrigée seulement en la confrontant à un contre-exemple déjà connu.

## Hypothèse de départ

Le [Lot 4.6 du plan](../../PLAN_SOLIDITE_TECHNIQUE.md#46--z3--model-checking--%E2%9A%9F-%F0%9F%93%9D%F0%9F%93%9D%F0%9F%93%9D-l-expérience-à-risque-assumé)
proposait un pari explicitement risqué : les Lots 4.1 à 4.4 avaient tous
établi la conformité aux axiomes par échantillonnage (fuzzing, oracle
tiers, énumération exhaustive bornée, tests à propriétés) — toujours un
nombre *fini* de profils concrets, aussi grand soit-il. L'hypothèse testée
ici : un solveur SMT peut-il prouver une propriété pour **tous** les
électorats possibles à la fois (un domaine infini), sans jamais énumérer
un seul profil concret ? Et si oui, à quel coût d'encodage ?

## Protocole

`z3-solver` (5.1.0.0) installé sans conflit dans le même environnement
Python 3.14 que le reste du backend (contrairement à `pref_voting` au
Lot 4.2, qui exigeait un venv séparé) — un point positif dès le départ.

Encodage : pour n candidats fixé, les n! types de bulletins possibles
deviennent des variables entières symboliques `c_0..c_{n!-1} ≥ 0` (combien
de électeurs ont exactement ce classement) — un électorat de taille et de
composition arbitraires, pas une valeur concrète. Les marges pairwise
`margin(i,j)` sont des combinaisons linéaires fixes de ces variables (le
coefficient ±1 de chaque type de bulletin est un fait statique, pas une
variable). Demander à Z3 s'il existe une affectation des `c_k` où *« un
vainqueur de Condorcet existe mais la méthode élit quelqu'un d'autre »* est
vrai ; `unsat` = preuve qu'aucune n'existe, pour absolument tous les
électorats possibles à ce nombre de candidats.

Trois cibles tentées, volontairement de difficulté croissante :
1. **Minimax** — arithmétique pure (min/max de marges), aucune structure
   itérative.
2. **Schulze** — nécessite un calcul de plus fort chemin (beat-path),
   encodé par un Floyd-Warshall déroulé (`O(n³)` expressions imbriquées
   pour n fixé, pas de récursion ni de quantificateur).
3. **IRV** — élimination itérative avec redistribution, la cible choisie
   *exprès* pour être la plus susceptible de mal se passer (case-split sur
   qui est éliminé à chaque tour).

## Ce que ça a trouvé

**Minimax et Schulze : succès net, et plus fort que tout ce que les Lots
4.1-4.4 avaient produit.** `unsat` confirmé jusqu'à n=7 candidats :

| n (candidats) | types de bulletins | Minimax | Schulze |
|---|---|---|---|
| 3 | 6 | 0.01 s | 0.01 s |
| 4 | 24 | 0.02 s | 0.18 s |
| 5 | 120 | 0.11 s | 0.45 s |
| 6 | 720 | 1.23 s | 2.07 s |
| 7 | 5 040 | 39.94 s | 18.80 s |

C'est une preuve, pas un sondage : contrairement au Lot 4.3 (exhaustif mais
borné à m≤5 électeurs) ou au Lot 4.1 (échantillonné), ce résultat couvre
**tout électorat, de toute taille**, à n candidats fixé. Le mur est prévisible
et documenté par le plan lui-même (« explosion combinatoire ») : le nombre
de variables croît en `n!`, donc n=7 (5 040 variables) prend déjà 20-40 s
là où n=6 (720 variables) prenait 1-2 s — un mur d'encodage, pas de
solveur : Z3 lui-même n'a jamais peiné à raisonner, c'est la taille du
problème qui explose.

**IRV : un résultat faux, silencieux, découvert seulement en croisant avec
un fait déjà connu — l'enseignement le plus important de cette expérience.**
Premier encodage : `unsat` pour « IRV peut-il élire un perdant de Condorcet ? »
— une négation totale, en 0.001 s. Sauf que le Lot 4.4 avait déjà trouvé et
vérifié à la main un contre-exemple réel
(`test_condorcet_loser_irv_can_be_violated`, `test_voting_criteria_matrix.py`) :
IRV élit *bel et bien* parfois le perdant de Condorcet. Un `unsat` ne peut
pas être vrai s'il contredit un fait déjà établi par vérification directe —
donc l'encodage, pas le fait, était en cause.

Diagnostic (confronter l'encodage à ce contre-exemple connu plutôt que lui
faire confiance) : l'encodage ne traitait que le cas « un candidat unique
a strictement le moins de premiers choix ». Sur le profil connu (A et B à
égalité à 2 premiers choix, C à 3, sur 7 bulletins), aucun candidat n'est
un minimum *strict* — la vraie règle de ce moteur élimine A et B
**simultanément** (la convention documentée dans `get_irv_winner` et déjà
découverte comme distinctive lors des Lots 4.2/4.4 pour d'autres méthodes),
laissant C gagner par défaut. Ce cas n'existait tout simplement pas dans
l'encodage — ni une erreur de syntaxe, ni un timeout, juste une règle
métier omise. Le `unsat` obtenu décrivait fidèlement une méthode
*différente* de la vraie `get_irv_winner`.

Encodage corrigé (ajout du cas « deux candidats à égalité au minimum,
élimination simultanée, le troisième gagne par défaut ») et **revérifié sur
le profil connu avant de refaire confiance à quoi que ce soit** : l'encodage
corrigé retrouve bien C comme vainqueur sur ce profil précis. Relancer la
recherche donne alors `sat`, avec en prime un vainqueur inattendu de
l'optimisation Z3 : le **plus petit contre-exemple possible, prouvé
minimal** (pas juste « plus petit que ceux trouvés par hasard ») — 7
bulletins (2× A-C-B, 3× B-C-A, 2× C-A-B), vérifié directement contre
`get_irv_winner` :

```
>>> get_irv_winner([['A','C','B']]*2 + ['B','C','A']*3 + ['C','A','B']*2)
'B'   # et B est bien le perdant de Condorcet sur ce profil
```

Cet encodage IRV corrigé n'est **pas committé** : plus fragile (plus de
branches de cas, donc plus de façons de mal représenter une règle réelle)
que les méthodes purement arithmétiques ci-dessus, pour un gain déjà
obtenu autrement par les Lots 4.1-4.4.

## Ce que ça a coûté

~3h au total : ~45 min pour installer Z3 et faire marcher le premier
encodage (minimax, n=3) ; ~30 min pour étendre à Schulze (Floyd-Warshall
déroulé) et mesurer la montée en charge jusqu'à n=7 ; ~1h pour l'épisode
IRV (encoder, obtenir le faux `unsat`, le confronter au contre-exemple
connu, diagnostiquer l'omission, corriger, revérifier) ; ~45 min pour
écrire les tests permanents (`test_z3_formal_proofs.py`, ~5s en CI) et ce
carnet.

Aucun faux positif côté minimax/Schulze — les deux se sont comportés
exactement comme attendu dès le premier encodage correct, contrairement à
IRV. Aucune charge de maintenance a priori : les preuves sont des faits
mathématiques sur des algorithmes déjà figés (minimax, Schulze ne
changeront pas), donc un nouvel échec de ces deux tests signifierait un
vrai changement de comportement du moteur, pas un test qui se dégrade avec
le temps.

## Verdict et pourquoi

**Adopté, mais partiellement — exactement la nuance que ce genre
d'expérience est censé produire.** Deux tests permanents ajoutés
(`fast_api_voter/api/tests/test_z3_formal_proofs.py`, `z3-solver` en
dépendance de dev) pour minimax et Schulze : rapides, généraux, et prouvent
une propriété plus forte que tout ce qui existait avant sur ce point précis
(critère de Condorcet, tous électorats plutôt qu'un échantillon). Rien
d'autre committé : ni l'encodage IRV (trop fragile pour son gain marginal
ici), ni une extension à d'autres critères ou méthodes (ranked pairs, black,
kemeny) — un vrai suivi possible, pas fait faute de budget et sachant
maintenant que l'effort d'encodage fidèle peut dépasser largement l'effort
de preuve elle-même.

## Ce que j'en retiens (transférable à un autre projet)

1. **Un solveur SMT ne peut prouver que ce que vous lui avez fidèlement
   décrit — et une preuve issue d'un encodage infidèle est un mensonge
   silencieux, pas une erreur bruyante.** Z3 n'a jamais planté ni signalé
   d'ambiguïté sur l'encodage IRV incomplet : il a répondu `unsat` avec la
   même confiance apparente que pour un encodage correct. La seule
   parade trouvée ici a été de **toujours posséder au moins un fait
   indépendant déjà vérifié** (ici, un contre-exemple trouvé par fuzzing
   dans un lot précédent) pour croiser tout résultat SMT avant de lui faire
   confiance — un solveur formel ne remplace pas une vérification
   indépendante, il s'y ajoute.
2. **La difficulté d'encodage, pas la performance du solveur, est le vrai
   risque pour les algorithmes itératifs/à branchements** (élimination,
   tri, cas de figure à départager) — contrairement aux algorithmes
   purement arithmétiques (comparaisons de scores, chemins de graphe à
   taille fixe), qui se sont encodés et ont raisonné sans accroc jusqu'à
   des tailles pratiques. Choisir la cible en fonction de la FORME de
   l'algorithme (arithmétique vs. itératif) prédit mieux la difficulté que
   l'intuition sur « quelle méthode est complexe ».
3. **Une preuve formelle et un test échantillonné répondent à des
   questions différentes, pas à la même question en mieux.** Le test
   échantillonné (Lot 4.1) avait déjà la bonne réponse sur IRV/Condorcet
   loser ; la preuve formelle n'a rien appris de nouveau sur CE fait — elle
   a par contre livré une info qu'aucun échantillonnage ne peut donner par
   construction : la taille minimale *prouvée* d'un contre-exemple. Les
   deux approches se complètent, aucune ne rend l'autre obsolète.
