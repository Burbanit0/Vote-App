# Vote Lab — Référence théorique complète

> **Pour qui ?** Enseignants, chercheurs, étudiants en science politique,
> mathématiques ou économie souhaitant comprendre les fondements formels
> de chaque simulation proposée par Vote Lab.
>
> **Comment citer :** voir la bibliographie complète en [§11](#11-références).

---

## Table des matières

1. [Fondements : la théorie du choix social](#1-fondements--la-théorie-du-choix-social)
2. [Les méthodes de vote (29)](#2-les-méthodes-de-vote-17-playground--12-laboratoire--29)
3. [Les théorèmes d'impossibilité](#3-les-théorèmes-dimpossibilité)
4. [Les paradoxes démocratiques](#4-les-paradoxes-démocratiques)
5. [Modèles de comportement électoral](#5-modèles-de-comportement-électoral)
6. [Phénomènes de participation](#6-phénomènes-de-participation)
7. [Systèmes alternatifs de gouvernance](#7-systèmes-alternatifs-de-gouvernance)
8. [Solutions technologiques](#8-solutions-technologiques)
9. [Limites des modèles](#9-limites-des-modèles)
10. [Le simulateur Polity](#10-le-simulateur-polity)
11. [Références](#11-références)

---

## 1. Fondements : la théorie du choix social

### 1.1 Définitions de base

**Profil de préférences** : un vecteur de relations de préférence individuelles
`(≻₁, ≻₂, ..., ≻ₙ)` où `≻ᵢ` est une relation d'ordre totale sur l'ensemble
des alternatives `A` pour l'individu `i`.

**Règle de choix social** : une fonction `f : P → R` qui associe à chaque profil
de préférences admissibles une relation de préférence collective `R` sur `A`.

**Vainqueur de Condorcet** : l'alternative `a*` telle que pour toute autre
alternative `b`, une majorité stricte préfère `a*` à `b` en comparaison directe.
Il n'existe pas toujours (paradoxe de Condorcet).

**Régret bayésien** : mesure de l'écart entre l'utilité du vainqueur élu et
l'utilité maximale atteignable. Formellement :
```
BR(méthode) = E[max_a U(a) - U(gagnant_méthode)]
```
Un régret bayésien de 0 signifie que la méthode élit toujours le candidat
qui maximise le bien-être collectif espéré.

### 1.2 Le modèle spatial

Vote Lab utilise un modèle spatial bidimensionnel où :
- L'axe X représente la position économique (−1 = gauche, +1 = droite)
- L'axe Y représente la position sociétale (−1 = conservateur, +1 = progressiste)

L'utilité d'un électeur `v` pour un candidat `c` est une fonction décroissante
de leur distance euclidienne dans cet espace :

```
U(v, c) = 1 − 0.5 × dist(v, c) / √2
```

**Hypothèse clé (single-peakedness)** : les préférences sont supposées
unimodales — l'utilité décroît de façon monotone en s'éloignant du
point idéal de chaque électeur. Cette hypothèse est suffisante pour
garantir l'existence d'un vainqueur de Condorcet en dimension 1
(Black, 1948) mais PAS en dimension ≥ 2 (Plott, 1967).

### 1.3 Deux modèles d'électorat

Vote Lab utilise **deux** générateurs d'électorat qui partagent le même moteur de
*règles* (parité verrouillée, §9.1) mais pas la même génération d'*utilités* :

**Modèle playground (client, 2D, temps réel)** — celui de §1.2 : chaque électeur
et candidat est un point dans un plan idéologique, l'utilité est `−distance + valence`
(valence optionnelle, 0 par défaut). Rapide, spatial, manipulable à la souris.

**Modèle backend (recherche, 20 enjeux)** — chaque électeur et candidat est
positionné sur **20 enjeux politiques** (économie, environnement, santé, fiscalité,
immigration, etc.), chacun sur `[0, 1]`. L'utilité est une combinaison pondérée :

```
utility(v, c) = 0.60·issue_score + 0.20·loyalty_bonus + 0.15·charisma
              + scandal_penalty + mood_effect

issue_score = Σ_k  priorité_v[k] · (1 − |position_v[k] − policy_c[k]|)
```

où `k` parcourt les enjeux prioritaires de l'électeur, `loyalty_bonus` récompense
l'alignement partisan, et `scandal_penalty = −0.3·scandales` (×1.5 si charisme < 0.5).
La condition `will_vote` requiert `utility > 0.3`.

**Vote blanc comme candidat implicite** — dans le modèle backend, le blanc est
inséré dans le classement de chaque électeur à la position égale au nombre de
candidats dont l'utilité dépasse son `blank_threshold ~ Beta(3, 5)` (moyenne ≈ 0.375).
Quatre règles constitutionnelles du blanc sont modélisées :

| Règle | Description |
|---|---|
| `symbolic` | Droit français actuel : compté mais non électif |
| `competitive` | Le blanc peut gagner s'il obtient le plus de premiers choix |
| `threshold_30` | Blanc ≥ 30 % → élection invalidée |
| `majority_required` | Le vainqueur doit battre le blanc en duel pairwise |

**Distributions idéologiques** disponibles : `random` (démographie française INSEE,
Beta(2,3)), `centrist` (Normal(0.5, 0.1)), `polarized` (bimodale 50/50),
`left_skewed` (Beta(2,5)), `right_skewed` (Beta(5,2)).

---

## 2. Les méthodes de vote (17 playground + 12 laboratoire = 29)

### 2.1 Méthodes de classement (Ranked)

#### Plurality (Scrutin uninominal)
**Principe** : chaque électeur vote pour un seul candidat ; le plus voté gagne.

**Propriétés** :
- Satisfait : Pareto, Non-dictature
- Viole : IIA (systématiquement), Condorcet (fréquemment)
- Manipulabilité : très élevée (vote utile structurel)

**Usage réel** : Royaume-Uni, USA, Canada, France (1er tour).

**Paradoxe caractéristique** : effet spoiler — un candidat proche d'un autre
lui vole des voix et élimine tous les deux (France 2002 : fragmentation de la
gauche → Le Pen qualifié).

---

#### Two-Round (Scrutin uninominal à deux tours)
**Principe** : si aucun candidat n'atteint 50%+1 au premier tour,
les deux premiers s'affrontent au second.

**Propriétés** :
- Réduit (mais n'élimine pas) l'effet spoiler
- Viole IIA et Monotonie (un candidat peut perdre en gagnant des voix)
- Manipulabilité : modérée (le vote utile au 1er tour reste rationnel)

**Usage réel** : France (présidentielle, législatives), nombreux pays.

**Paradoxe caractéristique** : non-monotonie — un candidat peut être éliminé
précisément parce que trop d'électeurs l'ont soutenu au premier tour
(modifiant l'adversaire du second tour).

---

#### Borda Count
**Principe** : avec `n` candidats, chaque électeur attribue `n−1` points à son
premier choix, `n−2` au second, ..., `0` au dernier. Le candidat avec le
plus de points gagne.

**Formalisation** : score Borda de `a` dans le profil `(≻₁,...,≻ₙ)` :
```
B(a) = Σᵢ |{b ∈ A : a ≻ᵢ b}|
```

**Propriétés** :
- Satisfait : Pareto, Non-dictature, Positivement répondant
- Viole : IIA (structurellement — l'ajout d'un candidat faible peut changer le résultat)
- Résistance à la manipulation : moyenne

**Inventeur** : Jean-Charles de Borda (1781), académicien et marin français.

**Paradoxe de Borda** : la méthode peut élire un candidat que personne ne
préfère en duel direct à un autre — en particulier quand les préférences
sont "divided in the middle".

---

#### Approval Voting (Vote par approbation)
**Principe** : chaque électeur approuve un sous-ensemble quelconque de candidats ;
le plus approuvé gagne.

**Formalisation** : chaque électeur `i` choisit `Aᵢ ⊆ A`.
Score d'approbation : `S(a) = |{i : a ∈ Aᵢ}|`.

**Propriétés** :
- Satisfait : Pareto, Non-dictature, IIA (dans sa formulation standard)
- Stratégie sincère complexe : voter pour son meilleur ensemble est rationnel
  mais dépend des croyances sur les autres
- Résistance à l'effet spoiler : élevée

**Inventeur** : Formulé par Robert Weber (1977), popularisé par Brams & Fishburn (1978).

**Limite** : "Bullet voting" — beaucoup d'électeurs n'approuvent qu'un seul
candidat, ce qui réduit l'approval à la pluralité.

---

#### IRV — Instant Runoff Voting (Vote alternatif)
**Principe** : chaque électeur classe tous les candidats. On élimine le
dernier (en first-choice votes) à chaque tour, en redistribuant ses bulletins
au prochain candidat non-éliminé, jusqu'à majorité absolue.

**Propriétés** :
- Satisfait : Majorité (si un candidat a >50% au 1er tour, il gagne)
- Viole : Monotonie (peut perdre en gagnant des voix), IIA
- Résistance à l'effet spoiler : meilleure que la pluralité

**Usage réel** : Australie (Chambre des représentants), Irlande (présidentielle),
Maine et Alaska (USA), Écosse (certaines élections), Londres (mairie).

**Paradoxe de non-monotonie** : un candidat peut être éliminé parce qu'il a
reçu trop de premières préférences, modifiant les duels au tour suivant.

---

#### Coombs
**Principe** : similaire à IRV mais on élimine le candidat avec le plus de
DERNIÈRES positions (plutôt que le moins de premières).

**Propriétés** :
- Élit le vainqueur de Condorcet plus fréquemment que IRV
- Viole Monotonie
- Moins utilisé mais théoriquement intéressant

---

#### Bucklin
**Principe** : en plusieurs rounds, on compte d'abord les premiers choix,
puis si pas de majorité on ajoute les seconds choix, etc.

**Historique** : utilisé dans plusieurs villes américaines au début du XXe siècle,
abandonné car produisait des paradoxes fréquents.

---

#### Minimax (Simpson-Kramer)
**Principe** : pour chaque candidat, calculer la défaite maximale en duels
directs. Le vainqueur est celui dont la défaite maximale est la plus faible.

**Formalisation** : `score_minimax(a) = max_{b≠a} |{i : b ≻ᵢ a}|`.
Le vainqueur est `argmin_a score_minimax(a)`.

**Propriétés** :
- Élit toujours le vainqueur de Condorcet s'il existe
- Variante de la méthode de Condorcet
- Sensible aux "fausse défaites" marginales

---

#### Schulze
**Principe** : algorithme de plus long chemin (Widest Path) dans le graphe
des préférences pairwise. L'alternative avec le chemin le plus large vers
toutes les autres gagne.

**Formalisation** : `P[a,b]` = nombre d'électeurs préférant `a` à `b`.
`strength(a,b)` = force du plus fort chemin de `a` à `b` (algorithme Floyd-Warshall).
`a` bat `b` si `strength(a,b) > strength(b,a)`.

**Propriétés** :
- Élit toujours le vainqueur de Condorcet s'il existe
- Satisfait : Clone-proof, Reversal symmetry
- Résistance à la manipulation : élevée

**Usage réel** : Parti Pirate Allemand, Wikimedia Foundation, Debian (choix de
paquets par défaut), Ubuntu.

---

#### Kemeny-Young
**Principe** : trouver l'ordre total des candidats qui minimise la somme des
désaccords avec les préférences individuelles (distance de Kendall-tau).

**Formalisation** :
```
Kemeny(σ) = Σᵢ |{(a,b) : a ≻σ b mais b ≻ᵢ a}|
```
Le vainqueur est le premier élément de `argmin_σ Kemeny(σ)`.

**Complexité** : NP-difficile en général. Exact pour ≤6 candidats (6!=720
permutations). Vote Lab utilise KwikSort pour approximer avec >6 candidats.

**Propriétés** :
- Maximise l'accord avec les préférences collectives
- Élit le vainqueur de Condorcet s'il existe
- Axiomatiquement caractérisé par Young & Levenglick (1978)

---

#### Copeland
**Principe** : score = victoires en duels directs − défaites.

**Formalisation** : `copeland(a) = |{b : a bat b}| − |{b : b bat a}|`.

**Propriétés** :
- Élit le vainqueur de Condorcet s'il existe
- Produit souvent des ex-æquo (départage nécessaire)
- Simple à comprendre et à calculer

---

#### Nanson
**Principe** : élimination itérative. À chaque round, calculer les scores Borda
de tous les candidats actifs et éliminer ceux sous la moyenne. Répéter.

**Propriété fondamentale** : **si un vainqueur de Condorcet existe, Nanson
l'élit toujours** (Nanson, 1882). Garantie que Borda n'offre pas.

---

#### Baldwin
**Variante de Nanson** : au lieu d'éliminer tous les candidats sous la moyenne,
on n'élimine que le candidat avec le plus faible score Borda à chaque round.

**Propriété** : élit aussi toujours le vainqueur de Condorcet s'il existe,
mais avec une procédure d'élimination différente de Nanson.

---

### 2.2 Méthodes de score

#### Simple Score
**Principe** : chaque électeur attribue un score entre 0 et 5 à chaque candidat.
Le candidat avec la moyenne la plus haute gagne.

**Propriétés** :
- Satisfait IIA (les scores sont absolus, pas relatifs)
- Résistance à la manipulation : variable (les électeurs peuvent "bomber" leurs préférences)

---

#### STAR Voting (Score Then Automatic Runoff)
**Principe** : phase 1 → score 0-5 ; phase 2 → runoff entre les deux candidats
avec la meilleure moyenne, gagné par celui que plus d'électeurs ont scoré plus haut.

**Propriétés** :
- Combine les avantages du score (expression continue) et du runoff (majorité finale)
- Développé par Equal Vote Coalition (2014)

---

#### Median Voting (Vote médian)
**Principe** : chaque électeur attribue un score ; le vainqueur est le candidat
avec la médiane la plus haute. En cas d'égalité : procédure de départage par
majorité absolue étendue.

**Propriétés** :
- Plus robuste à la manipulation que la moyenne (changer son score ne change
  la médiane que si on était de l'autre côté)
- Proposé par Balinski & Laraki dans une formulation proche de MJ

---

#### Majority Judgment (Jugement Majoritaire)
**Principe** (Balinski & Laraki, 2010) : chaque électeur note chaque candidat
sur une échelle ordinale (Excellent → À Rejeter). Le vainqueur est celui dont
la **note médiane** est la plus haute. Départage : retirer une note médiane
et comparer.

**Formalisation** : soit `Gₖ(a)` la distribution de notes de `a`.
La note médiane `μ(a)` est telle que ≥50% notent `a` au moins `μ(a)`.

**Département** : si `μ(a) = μ(b)`, on compare `p` (fraction strictement
au-dessus de `μ`) et `q` (fraction strictement en dessous). Si `p > q`,
le candidat a une "majorité supérieure" et gagne.

**Propriétés** :
- Satisfait : Pareto, Non-dictature, Clone-proof
- Viole : IIA (légèrement), Monotonie de groupe
- Résistance à la manipulation : **la plus élevée parmi toutes les méthodes score**
  (Balinski & Laraki, 2010)
- Expérimentée réellement : LaPrimaire.org (France 2017, 33 000 participants)

---

#### Evaluative Voting (Vote évaluatif)
**Principe** : chaque électeur attribue +1, 0, ou −1 à chaque candidat.
Le score net détermine le vainqueur.

**Formulation** : simplifié par Balinski & Laraki comme extension naturelle
de MJ avec 3 niveaux. Permet l'expression du rejet (−1) contrairement à
l'approbation simple.

---

#### Mean-Median Hybrid
**Principe** : combine la moyenne et la médiane dans une pondération configurable.

---

#### Variance-Based
**Principe** : favorise les candidats avec une faible variance de scores
(consensus plutôt que polarisation).

---

### 2.3 Méthodes spéciales

#### Quadratic Voting (Vote quadratique)
**Principe** (Lalley & Weyl, 2018) : chaque électeur dispose d'un budget de
voix. Voter pour `k` propositions coûte `k²` jetons.

**Propriété fondamentale** : l'équilibre de Nash du QV est approximativement
efficace au sens de Pareto — les préférences d'intensité sont révélées
fidèlement.

**Formalisation** : si un électeur a une valeur `vᵢ` pour une proposition,
le nombre optimal de voix `kᵢ = vᵢ / (2λ)` où `λ` est le prix marginal.

**Usage réel** : Expérimenté par le Colorado Legislature (2019), utilisé par
RadicalxChange pour des votes internes.

---

#### Quadratic Funding (Financement quadratique)
**Principe** (Buterin, Hitzig & Weyl, 2019) : allocation de biens communs.
Le financement public d'un projet P est proportionnel au carré de la somme
des racines des contributions individuelles :

```
Financement(P) ∝ (Σᵢ √cᵢₚ)²
```

**Propriété** : maximise le bien-être collectif sous contrainte budgétaire,
en amplifiant les projets avec beaucoup de petits donateurs vs peu de gros.

---

#### Sequential Proportional Approval Voting (SPAV)
**Principe** : variante proportionnelle de l'approbation pour les scrutins
multi-gagnants. À chaque round, le poids de vote des électeurs dont un élu
est déjà sélectionné est divisé par (1 + nb_élus_approuvés).

**Propriété** : satisfait "Proportional Justified Representation" (Aziz et al., 2017).

---

#### Méthode de Phragmén (1894)
**Principe** : méthode proportionnelle par approbation minimisant la charge
maximale parmi les électeurs soutenant les élus.

**Propriété** : équité maximin — maximise le minimum d'utilité par groupes
d'électeurs. Redécouverte par la littérature contemporaine (Brill et al., 2017).

---

### 2.4 Méthodes supplémentaires du laboratoire

Le playground expose les 17 méthodes ci-dessus. Le **laboratoire** (`/laboratoire`)
ajoute 12 méthodes plus spécialisées, essentiellement des variantes Condorcet et
des règles à propriété particulière. Elles partagent le même moteur de règles que
le playground (parité client⇄backend, voir §9.1).

- **Ranked Pairs (Tideman, 1987)** — verrouille les duels pairwise du plus fort au
  plus faible en sautant ceux qui créeraient un cycle ; élit la source du graphe
  obtenu. Méthode de Condorcet, monotone, indépendante des clones.
- **River (Heitzig, 2004)** — variante de Ranked Pairs n'autorisant qu'une arête
  entrante par candidat ; plus rapide, mêmes garanties Condorcet.
- **Split Cycle (Holliday & Pacuit, 2020)** — élimine, dans chaque cycle, l'arête
  de défaite la plus faible ; élit les candidats sans défaite restante. Résiste au
  spoiler (independence of clones + immunité aux « pertes » de section).
- **Smith/IRV (Smith-then-IRV)** — restreint d'abord à l'ensemble de Smith (plus
  petit ensemble battant tout le reste), puis applique IRV. Rend IRV cohérent avec
  Condorcet.
- **Benham** — IRV où, à chaque round, on élit immédiatement un éventuel vainqueur
  de Condorcet des candidats restants. Méthode de Condorcet.
- **Black (1958)** — élit le vainqueur de Condorcet s'il existe, sinon le vainqueur
  Borda. Combine cohérence Condorcet et robustesse Borda.
- **Raynaud** — élimine répétitivement le candidat qui subit la défaite pairwise la
  plus forte. Méthode de Condorcet.
- **Anti-plurality (veto)** — chaque électeur vote *contre* un candidat ; le moins
  rejeté gagne. Utile pour illustrer l'opposé structurel de la pluralité.
- **Dowdall (Nauru)** — Borda pondéré harmonique : le rang `k` rapporte `1/k`.
  Favorise fortement les premiers choix par rapport au Borda linéaire.
- **Cumulative voting** — chaque électeur répartit un budget de points sur les
  candidats (concentration possible). Classique pour la représentation des
  minorités.
- **Nash (produit d'utilités)** — élit le candidat maximisant le *produit* des
  utilités (bien-être nashien) plutôt que la somme ; pénalise les résultats très
  inégalitaires.
- **Random ballot (dictature aléatoire)** — tire un bulletin au hasard et élit son
  premier choix. Seule règle **non manipulable** (strategyproof) et proportionnelle
  en espérance ; sert de témoin théorique (Gibbard, 1977).

---

## 3. Les théorèmes d'impossibilité

### 3.1 Théorème d'Arrow (1951)

**Énoncé** : Aucune règle de choix social ne peut simultanément satisfaire :
1. **Domaine universel** : toutes les préférences individuelles sont admissibles
2. **Pareto (unanimité)** : si tout le monde préfère `a` à `b`, alors `a > b` collectivement
3. **Indépendance des alternatives non pertinentes (IIA)** : le classement entre
   `a` et `b` ne dépend pas des préférences sur les autres alternatives
4. **Transitivité** : la relation collective est un ordre total
5. **Non-dictature** : il n'existe pas d'individu dont la préférence prime toujours

**Preuve (esquisse)** : par l'existence d'un "pivotal voter" — dans tout profil,
il existe un électeur dont le changement de préférence entre deux alternatives
détermine le résultat collectif, ce qui constitue une forme de dictature
sur cette paire (Arrow, 1951 ; Wilson, 1972).

**Interprétation** : toute méthode de vote doit sacrifier au moins un de ces
5 axiomes. Le choix de l'axiome sacrifié définit le "profil éthique" de
la méthode.

---

### 3.2 Théorème de Gibbard-Satterthwaite (1973-1975)

**Énoncé** : Toute règle de choix social déterministe, non-dictatoriale, et
applicable à ≥3 alternatives est **manipulable** — il existe des profils
de préférences où un électeur peut améliorer son résultat en déclarant
des préférences différentes de ses vraies préférences.

**Implication** : le "vote sincère" n'est jamais une stratégie dominante
pour toutes les méthodes non-triviales.

**Nuance** : certaines méthodes (Majority Judgment, STAR) minimisent les
situations où la manipulation est utile, sans l'éliminer entièrement.

---

### 3.3 Théorème du chaos de Plott (1967)

**Énoncé** : Dans un espace de politiques à ≥2 dimensions avec ≥3 électeurs,
un vainqueur de Condorcet n'existe (presque) jamais. De plus, l'ensemble
des alternatives non-dominées (le "top cycle") peut couvrir l'espace entier.

**Implication directe** : l'agenda-setter peut produire n'importe quel résultat
avec le même électorat en choisissant l'ordre des votes.

**Condition nécessaire pour un Condorcet winner en 2D** (Plott's condition) :
les droites de médiane des électeurs doivent se croiser en un point unique —
condition de "mesure nulle" (probabilité 0 pour des préférences génériques).

---

### 3.4 Paradoxe d'agrégation des jugements (List-Pettit, 2002)

**Énoncé** : Quand des agents votent sur des propositions logiquement liées,
la règle majoritaire peut produire un résultat collectivement incohérent
même si chaque individu est parfaitement cohérent.

**Exemple canonique** (le "discursive dilemma") :

| Juge | P1 (contrat valide) | P2 (obligations non remplies) | C (= P1∧P2 → responsabilité) |
|------|---------------------|-------------------------------|-------------------------------|
| A    | Oui                 | Oui                           | Oui                           |
| B    | Oui                 | Non                           | Non                           |
| C    | Non                 | Oui                           | Non                           |
| **Majorité** | **Oui**     | **Oui**                       | **Non**                       |

La majorité accepte les prémisses et rejette leur conclusion logique.

**Solution** : voter sur les prémisses et déduire la conclusion (premise-based),
ou voter directement la conclusion (conclusion-based). Les deux donnent des
résultats différents.

---

### 3.5 Paradoxe libéral de Sen (1970)

**Énoncé** : Même avec seulement 2 individus ayant des préférences cohérentes,
il est impossible de satisfaire simultanément :
- **Pareto** : si tout le monde préfère `a` à `b`, choisir `a`
- **Libéralisme minimal** : chaque individu a le droit de décider pour au moins
  une paire d'alternatives dans sa "sphère privée"

**Interprétation** : les droits individuels et l'efficacité collective sont
logiquement incompatibles. Toute démocratie libérale est fondée sur un
compromis non-résolu entre ces deux valeurs.

---

### 3.6 Impossibilité d'apportionment (Balinski-Young, 1982)

**Énoncé** : Il est impossible de répartir des sièges entiers entre des
partis de façon à satisfaire simultanément :
- **Quotient** : chaque parti reçoit entre ⌊quota⌋ et ⌈quota⌉ sièges
- **Monotonie de la population** : un parti ne perd pas de sièges en gagnant des voix
- **Monotonie de la chambre** : personne ne perd de sièges quand on en ajoute

**Paradoxes découverts** :
- **Paradoxe d'Alabama (1880)** : l'Alabama perd un siège quand la chambre est agrandie
- **Paradoxe de la population** : un État peut perdre un siège en gagnant des habitants
- **Paradoxe du nouvel État** : l'arrivée d'un nouvel État peut faire perdre des sièges aux anciens

---

## 4. Les paradoxes démocratiques

### 4.1 Paradoxe de Condorcet (1785)

Les préférences collectives peuvent être cycliques même si chaque préférence
individuelle est transitive :
- Électeur 1 : A > B > C
- Électeur 2 : B > C > A
- Électeur 3 : C > A > B

Résultat : A > B (majorité), B > C (majorité), C > A (majorité) — cycle.

**Fréquence** : augmente avec le nombre de candidats et la polarisation de l'électorat.
Pour 3 candidats et 3 électeurs avec préférences uniformes : probabilité ≈ 8.8%.

---

### 4.2 Paradoxe d'Ostrogorski (1902)

**Énoncé** : Un parti peut gagner sur chaque question votée séparément
et pourtant perdre l'élection globale.

**Exemple** : avec 3 questions (A, B, C) et 5 électeurs, le Parti X peut
avoir une majorité sur chaque question individuellement mais perdre
l'élection si les majorités sont différentes à chaque fois.

---

### 4.3 Effet spoiler

Un candidat sans chance de gagner modifie le résultat en "volant" des voix
à un candidat proche idéologiquement.

**Exemple historique** : USA 2000, Ralph Nader (Verts) → 97 000 voix en Floride.
Bush bat Gore de 537 voix. Nader était mathématiquement le spoiler.

**Solution** : méthodes de Condorcet, IRV, Approval — toutes réduisent l'effet
spoiler mais ne l'éliminent pas entièrement.

---

### 4.4 Paradoxe de non-monotonie

Certaines méthodes (IRV, Two-Round) peuvent produire des situations où
un candidat perd PARCE QU'il a reçu plus de voix.

**Mécanisme en IRV** : recevoir plus de voix au 1er tour peut modifier
l'ordre d'élimination et créer un adversaire plus fort au duel final.

---

## 5. Modèles de comportement électoral

### 5.1 Vote sincère vs vote stratégique (tactique)

**Vote sincère** : l'électeur vote pour son candidat préféré selon ses vraies
préférences.

**Vote stratégique** : l'électeur vote pour un candidat qui n'est pas son premier
choix afin d'éviter un résultat pire.

**Condition de rationalité** : le vote stratégique est rationnel si et seulement
si `U(résultat_stratégique) > U(résultat_sincère)`.

**Stratégies connues** :
- **Compromising** : remonter un candidat acceptable pour bloquer le pire
- **Burying** : descendre un rival pour favoriser son candidat
- **Push-over** : soutenir un candidat faible pour créer un duel favorable
- **Truncating** : ne pas classer tous les candidats (IRV)

---

### 5.2 Modèle de campagne (Brownian Motion)

Vote Lab modélise les intentions de vote comme un processus de Wiener
(mouvement brownien) perturbé par des effets de sondage :

```
dVᵢ(t) = σ dWᵢ(t) + λ [Sᵢ(t) − Vᵢ(t)] dt
```

Où `Vᵢ(t)` est l'intention de vote pour le candidat `i` au jour `t`,
`σ` est la volatilité, `Sᵢ(t)` est le sondage du jour `t`, et `λ`
est la force du polling effect (bandwagon).

---

### 5.3 Modèle de contagion sociale du vote blanc (SIS)

Les comportements de vote blanc se propagent dans un réseau social
selon un modèle SIS (Susceptible-Infected-Susceptible) :

```
dS/dt = −βSI + γI
dI/dt = βSI − γI
```

Où S = proportion d'électeurs "sains" (votants), I = proportion d'électeurs
"contaminés" (vote blanc), β = taux de contagion, γ = taux de "guérison".

**Équilibre endémique** : `I* = 1 − γ/β` si `β > γ` (nombre de reproduction R₀ = β/γ > 1).

---

### 5.4 Modèle d'information asymétrique

Chaque électeur appartient à un segment d'information
{bas, moyen, élevé} avec des probabilités `{π_l, π_m, π_h}`.
Les utilités perçues sont déformées par un biais médias `bᵢ` par candidat :

```
U_perçue(v, c) = U_sincère(v, c) × (1 + bᵢ × ρ_v)
```

Où `ρ_v ∈ [−1, 1]` mesure la réceptivité de l'électeur au biais médias
selon son niveau d'information (les électeurs très informés sont moins réceptifs).

---

### 5.5 Modèle d'abstention différentielle

La probabilité d'abstention d'un électeur dépend de l'écart entre son
candidat préféré et les sondages :

```
P(abstention | v, round) = max(0, min(1,
    demob_factor × sigmoid(poll_gap × 3 + utility_gap × 1.5 − 1.0) × poll_influence
))
```

Où `poll_gap = 1 − vote_shares[préféré_de_v]` mesure le décalage entre
le candidat favori et son score dans les sondages.

**Propriété** : `demob_factor = 0 ⟹ P(abstention) = 0` (aucune abstention).

---

### 5.6 Vote rétrospectif (Fiorina, 1981)

L'utilité effective du candidat sortant est modifiée par la performance économique :

```
U_rétro(v, sortant) = U_sincère(v, sortant) + perf_éco × retention × voter_memory
```

Où `perf_éco ∈ [−1, 1]`, `retention ∈ [0, 1]` mesure l'intensité rétrospective,
et `voter_memory ∈ [0, 1]` modèle l'horizon temporel des électeurs.

**Donnée empirique** : chaque point de PIB supplémentaire au moment de l'élection
ajoute en moyenne 0.5% au score du parti sortant (Hibbs, 2000).

---

### 5.7 Polarisation affective (Iyengar et al., 2019)

L'utilité affective modifie l'utilité idéologique par un terme de rejet :

```
U_affect(v, c) =
    U_sincère(v, c)                            si c est dans le camp de v
    U_sincère(v, c) × (1 − hostility_factor)   si c est dans le camp opposé
```

**Mesure empirique** : aux USA, le "feeling thermometer" moyen des partisans
pour le parti adverse est passé de 45/100 en 1994 à 20/100 en 2022
(Pew Research Center, 2022).

---

### 5.8 Biais de désirabilité sociale (Bradley effect)

Un électeur peut déclarer une intention de vote différente de son vote réel
par pression sociale :

```
Déclaration(v) = {
    vote_sincère,               avec proba (1 − social_desirability_factor)
    vote_"acceptable",          avec proba social_desirability_factor  | si vote_sincère = candidat_sensible
}
```

**Exemples documentés** :
- Tom Bradley (1982) : -9 points en réalité vs sondages
- Brexit (2016) : Leave sous-estimé de ~4%
- Trump (2016, 2020) : sous-estimé de 3-5 points dans les swing states

---

### 5.9 Cascades d'information (Bikhchandani, Hirshleifer, Welch, 1992)

Dans un vote séquentiel, un électeur ignore son signal privé avec probabilité
`cascade_strength` et suit le signal public (votes précédents) :

```
vote_final(v, t) = {
    signal_privé(v),                   avec proba (1 − cascade_strength)
    argmax_a {votes[a] : t' < t},      avec proba cascade_strength
}
```

**Résultat** : avec `cascade_strength > 0`, un candidat aléatoire prenant
l'avantage parmi les premiers votants peut déclencher une cascade irréversible.

---

### 5.10 Vague électorale (Coattail Effect)

La popularité d'un candidat en tête de liste influence les candidats du même
camp pour les élections simultanées :

```
U_effectif(v, local_cand) = (1 − coattail_factor) × U_sincère(v, local_cand)
                           + coattail_factor × U_sincère(v, tête_de_liste_du_camp)
```

---

## 6. Phénomènes de participation

### 6.1 Fatigue électorale

Le taux de participation décline de façon quasi-linéaire avec la fréquence
des élections :

```
turnout(k) = max(engaged_pct, 1 − k × fatigue_rate)
```

**Données empiriques** :
- Suisse (4 scrutins/an) : participation moyenne ~43%
- France : législatives 3 semaines après présidentielle → −12 points
- Référendums répétés : 2ème vote toujours moins participatif

---

### 6.2 Distorsion démographique

L'électorat effectif est systématiquement biaisé par rapport à la population :
- France 2022 : 18-24 ans = 55% de participation vs 65+ ans = 85%
- Écart éducation : sans diplôme 50% vs Bac+4 80%

**Mesure d'équité** : indice de Gini de représentation :
```
Gini_rep = (1 - Σᵢ |pop_pct_i - voter_pct_i|) / pop_homogeneity
```

---

### 6.3 Vote obligatoire

Les "reluctant voters" (forcés à voter) ont un comportement mesuré différent :
- +3-5% de bulletins nuls/blancs
- +X% de votes protestataires
- Participation augmente de ~20-30 points

**Trade-off** : représentativité accrue vs signal collectif "bruité" par
les votes aléatoires ou non-informés.

---

### 6.4 NOTA (None Of The Above)

Si la part de votes NOTA dépasse un seuil constitutionnel, l'élection
est invalidée. Vote Lab simule trois règles :

- **Invalidation** : si NOTA > 50%, nouvelle élection requise
- **Runoff** : NOTA qualifié = nouvelle élection sans les mêmes candidats
- **Winner-take-all** : NOTA élu → siège vacant (Nevada, USA)

---

## 7. Systèmes alternatifs de gouvernance

### 7.1 Sortition (Tirage au sort)

**Principe** : sélection aléatoire (pure ou stratifiée) d'une assemblée
représentative de la population.

**Propriété statistique** : une assemblée de taille `n` tirée au sort est
représentative avec erreur standard `σ = √(p(1-p)/n)`.
Pour n=150 et p=0.5 : σ ≈ 4%.

**Exemples** : Boulé athénienne (500 citoyens), Convention Citoyenne irlandaise
2016 (99 membres), Convention Citoyenne pour le Climat France 2019 (150 membres).

---

### 7.2 Liquid Democracy

**Principe** : chaque électeur peut voter directement ou déléguer son vote
à un mandataire (délégation transitive).

**Graphe de délégation** : un DAG orienté G = (V, E) où (v, w) ∈ E signifie
que v délègue à w. Le poids de vote de w est :
```
weight(w) = 1 + Σ_{v: délègue à w, directement ou transitivement} 1
```

**Problème des cycles** : si A→B→C→A, aucun ne peut voter.
Vote Lab détecte les cycles (algorithme DFS) et les résout en forçant
le vote sincère pour les membres du cycle.

**Indice de Gini du poids** : mesure la concentration du pouvoir de vote.
Augmente avec la probabilité de délégation.

---

### 7.3 Conviction Voting (Polkadot, 2019)

**Principe** : le poids d'un vote croît avec la durée d'engagement des tokens.

| Durée de lock | Multiplicateur |
|---------------|---------------|
| 0 jours | ×0.1 |
| 7 jours | ×1 |
| 14 jours | ×2 |
| 28 jours | ×3 |
| 56 jours | ×4 |
| 112 jours | ×5 |
| 224 jours | ×6 |

**Propriété** : décourage les "whale attacks" (acheter des tokens, voter,
vendre immédiatement). Un petit holder avec 224 jours de lock pèse
60× plus qu'un grand holder sans lock.

---

### 7.4 Quadratic Funding (Gitcoin, Optimism)

Voir section 2.3. Déployé avec >$50M distribués à Gitcoin,
$70M via Optimism RPGF (Retroactive Public Goods Funding).

---

### 7.5 Deliberative Polling (Fishkin, 1988)

**Protocole** :
1. Sondage initial des préférences (avant délibération)
2. Week-end de délibération structurée avec experts et pairs
3. Sondage final

**Résultats empiriques** : dans 90% des expériences, les opinions changent
significativement. Les changements sont stables et informés (Fishkin, 2018).

---

### 7.6 Futarchie (Hanson, 2000)

**Principe** : "Vote sur les valeurs, parie sur les croyances."
La société définit un objectif à maximiser. Des marchés de prédiction
déterminent quelle politique l'atteindra le mieux. La politique
dont le marché prédit le meilleur résultat est automatiquement adoptée.

**Limite** : qui définit l'objectif ? Les marchés peuvent être manipulés.
Non déployé à grande échelle.

---

## 8. Solutions technologiques

### 8.1 Vote E2E-V (End-to-End Verifiable)

**Garanties** :
1. **Vote-and-verify** : chaque électeur peut vérifier que son bulletin est dans l'urne
2. **Anonymat** : personne ne peut lier un bulletin à un électeur
3. **Tallying** : le comptage est vérifiable sans déchiffrement individuel

**Primitives cryptographiques** :
- Chiffrement El-Gamal homomorphe : `E(a) × E(b) = E(a+b)` — somme sans déchiffrement
- Mix-nets : mélange cryptographique prouvé des bulletins
- Zero-Knowledge Proofs : prouver la validité d'un bulletin sans révéler son contenu

**Déploiements** :
- **ElectionGuard** (Microsoft, open source, 2019) : utilisé en Finlande, USA
- **Helios** (Adida, 2008) : Princeton, Université catholique de Louvain
- **Belenios** (INRIA, France) : Université de Lorraine

---

### 8.2 Vote par internet (e-voting)

**Estonie** (depuis 2005) :
- 51% des votes par internet en 2023
- Basé sur la carte d'identité électronique (PKI nationale)
- Vote re-votable jusqu'à la fermeture des bureaux (protection contre la coercition)
- Zéro incident de sécurité documenté en 20 ans

**Obstacles principaux** :
- Terminal compromis (solution partielle : carte ID physique comme 2nd facteur)
- Coercition (solution partielle : re-vote)
- Fracture numérique (solution : vote physique toujours disponible)

---

### 8.3 Gouvernance blockchain

**Vote pondéré par tokens (1T1V)** : Compound, Uniswap, Aave.
Avantage : coordination sans intermédiaire.
Limite : concentration du pouvoir par les "whales".

**Auto-amendment** : Tezos (depuis 2018).
Le protocole peut voter pour modifier sa propre façon de voter.
Procédure : Exploration → Testing → Promotion (4 phases, ~3 mois).

**DAO Governance** : MakerDAO, Nouns, Gitcoin.
Chaque NFT = 1 vote. Délégation liquide optionnelle.

---

### 8.4 Pol.is (algorithme)

**Pipeline** :
1. Participants votent Oui/Non/Abstention sur des propositions
2. Construction de la matrice votes × participants
3. PCA (analyse en composantes principales) → projection 2D
4. K-means clustering → groupes d'opinion
5. Identification des "consensus items" : `approval_rate > threshold` dans TOUS les clusters

**Déploiement Taiwan (vTaiwan, 2015-2016)** :
- 450 000 participants sur la régulation Uber/Airbnb
- 20 propositions consensuelles identifiées
- Loi adoptée sans opposition significative
- Encore en vigueur en 2024

---

## 9. Limites des modèles

### 9.1 Hypothèses implicites de Vote Lab

| Hypothèse | Statut empirique | Implication si violée |
|---|---|---|
| Préférences stables | ❌ Faux (Slovic 1995) | Variance du résultat |
| Espace 2D euclidien | ⚠️ Simplification | Résultats différents en n-D |
| Single-peaked | ⚠️ Souvent violé | Condorcet moins fréquent |
| Électeurs rationnels | ❌ Faux (Kahneman 2002) | Biais systématiques |
| Utilités comparables | ⚠️ Non-prouvable | QV/MJ basés sur cette hypothèse |
| Électorat fixe | ❌ Faux | Démocratie endogène |
| Sincère vs stratégique = dichotomie | ⚠️ Continuum réel | Manipulation partielle |

### 9.2 La question philosophique fondamentale

Le résultat de toute simulation dans Vote Lab dépend de choix effectués
**avant** la simulation : quelle méthode, quel agenda, quelles hypothèses.

Les théorèmes d'impossibilité (Arrow, Sen, Plott, Gibbard-Satterthwaite)
convergent vers une conclusion commune : **la volonté collective n'est pas
une entité préexistante que les méthodes de vote "révèlent" — c'est une
construction procédurale**.

Rousseau avait tort sur la "volonté générale" comme entité objective.
Arrow l'a démontré mathématiquement.

Mais cela ne signifie pas que la démocratie est inutile — cela signifie que
la légitimité démocratique vient de la **procédure acceptée collectivement**,
pas d'un résultat "vrai" indépendant.

### 9.3 Parité du moteur (client ⇄ backend)

Les règles de vote existent en **deux implémentations** — un moteur client rapide
(`voter-app/src/lib/playgroundVoting.ts`) et un moteur backend faisant autorité
(`fast_api_voter/api/engine/utils/`). Un harnais de fixtures « golden » génère les
vainqueurs de référence côté backend et un test de parité vérifie que le client
produit exactement les mêmes vainqueurs. Toute divergence est un bug jusqu'à preuve
du contraire — le harnais a effectivement débusqué des bugs des deux côtés.

### 9.4 Sources de données

- **Démographie** — distribution d'âge dérivée du Recensement INSEE 2019 (RP2019).
- **Élections réelles** convertibles en bulletins classés synthétiques (par
  proximité idéologique) : France 2002 & 2022 (1er tour, Conseil constitutionnel /
  Ministère de l'Intérieur), USA 1992 (FEC), UK 2015 (Electoral Commission).
- **Limite de la conversion** — les scores de premier tour → bulletins classés
  supposent des préférences purement idéologiques ; les électeurs réels ont des
  motivations non-idéologiques que ce modèle ignore.

---

## 10. Le simulateur Polity

> **Ce chantier n'est pas Vote Lab.** Cette section documente un second
> projet de recherche — un simulateur multi-agents de dynamique politique
> ("La Fourmilière", `fast_api_voter/api/domain/polity/`) qui partage le
> backend de Vote Lab mais aucun code, aucune configuration et aucun
> journal avec lui. Contrairement aux sections 1 à 9, qui documentent des
> résultats établis de la théorie du choix social, chaque formule ci-dessous
> est un **choix de modélisation propre à ce projet** — pas un résultat
> citable de la littérature. La spécification complète et versionnée vit
> dans `polity-simulation-design-v2.md` (document de conception local, non
> publié) ; cette section en est le résumé public.

### 10.1 Légitimité — `L(t)`

Le cœur du modèle est une légitimité `L(t) ∈ [0, 1]` par élu, mise à jour à
chaque pas de temps :

```
L(t) = decay · L(t-1) + support(t) − écart(t)
L(0) = support(0)
```

`decay` est un paramètre de configuration (`legitimacy.decay`, 0.9 par
défaut). `support(t)` était un **point ouvert du plan de conception**
(§7.1 : "reste à définir opérationnellement") — sa résolution, apportée par
ce projet et non par la littérature, est :

```
support(t) = (1 − decay) · m
```

où `m` (force du mandat) est la fraction des bulletins **exprimés** classant
le vainqueur au-dessus du blanc, calculée de façon **agnostique à la méthode
électorale** — la même définition s'applique aux 13 méthodes de classement
implémentées (§2.1), ce qui permet de comparer leur effet sur `L(t)` sans
changer la métrique elle-même.

Cette définition est **le seul choix** sous lequel `L(t)` converge vers un
point fixe stable en l'absence de toute pression citoyenne : si `écart(t) ≡
0`, alors `L(t) ≡ m` pour tout `t` — la légitimité reste plate à la force du
mandat initial tant que rien ne s'y oppose. C'est la condition de contrôle
attendue : *un élu qui trahit intégralement son mandat face à une population
passive ne perd aucune légitimité* (§10.2) — et c'est ce point fixe qui a
permis de clore le bloquant historique de l'audit de précision sur la
formule de `L(t)` (référencé A6 dans `polity-simulation-design-v2.md`),
ouvert depuis le début de l'audit.

### 10.2 `écart(t)` — un modèle purement actionnel

`écart(t)` agrège trois signaux, chacun borné par sa propre pondération
(`w_pet + w_mob = 1`) :

```
écart(t) = w_pet · signed_ratio(t) + w_mob · street_pressure(t)
           + passive_erosion_weight · mandate_deviation(t)
```

`signed_ratio(t)` et `street_pressure(t)` existent seulement quand les
citoyens **agissent** (signature de pétition, mobilisation) — par défaut,
`passive_erosion_weight = 0.0`, ce qui rend le modèle strictement
*actionnel* : une dérive de mandat qui ne provoque aucune réaction
citoyenne ne coûte rien à l'élu. C'est un choix de modélisation assumé, pas
un oubli — il isole l'effet des leviers de pression (§10.5) de l'effet de
la dérive elle-même, et rend observable la question centrale du projet :
une population dotée de leviers de pression s'en saisit-elle réellement ?

### 10.3 Le plancher dur et le rappel

`L(t)` est comparé à chaque pas à un plancher fixe (`legitimacy.recall_floor`,
0.2 par défaut) : si `L(t)` passe strictement en-dessous, l'élu est
destitué. Le plancher est **volontairement fixe**, jamais indexé sur `L(0)`
— un plancher mobile détruirait la lisibilité externe du seuil (un
observateur ne pourrait plus dire, en lisant `L(t)` seul, si un rappel est
imminent).

Deux mécanismes distincts peuvent déclencher une destitution — le
franchissement du plancher, ou un vote de confiance perdu après qu'une
pétition a atteint son seuil de signatures — mais les deux sont journalisés
sous le même type d'événement (`recalled`), distingué par un champ
`trigger`. Un même tick peut voir les deux se produire simultanément
(un plancher franchi le tick même de l'élection, par exemple) ; dans ce
cas, le plancher a toujours priorité dans l'attribution — mais les deux
mécanismes restent journalisés intégralement, jamais court-circuités.

### 10.4 La déviation de mandat — une mesure, jamais un levier

`mandate_deviation(t)` est la distance pondérée entre la plateforme promise
à l'élection (`pledged_platform`, figée) et la position réellement défendue
(`revealed_position`, qui peut dériver). C'est une **mesure**, jamais une
décision — rien dans le modèle ne peut faire dériver `revealed_position` en
l'absence d'un agent LLM actif (`llm.enabled: false`) : c'est le cas de
contrôle du projet, vérifié par test, sous lequel la déviation de mandat
est nulle par construction pour toute la durée d'une simulation. Toute
déviation observée à partir de l'activation de l'agent est donc, par
construction, entièrement attribuable à ce dernier — l'argument de
comparaison le plus propre dont dispose le projet entre une base
déterministe et un comportement généré.

### 10.5 Le menu de pression — une variable expérimentale à quatre modalités

Le concepteur fixe le **menu constitutionnel** des leviers disponibles
(signer/lancer une pétition, participer à une mobilisation, ou attendre la
prochaine élection) — les citoyens choisissent librement à l'intérieur de
ce menu, jamais au-delà. Le menu n'est pas traité comme deux booléens
indépendants mais comme **une seule variable à quatre modalités**
(`electoral_only` / pétition seule / mobilisation seule / les deux), pour
que le plan d'analyse reste un plan de sensibilité à un paramètre à la
fois plutôt qu'un croisement combinatoire. `electoral_only` — aucun levier
entre deux scrutins — sert de **groupe de contrôle** : sous cette
modalité, `L(t)` doit rester plate à `m` pour toute la durée d'un mandat
(§10.1), et c'est effectivement le cas testé.

### 10.6 Le seuil d'éveil — une porte d'échantillonnage, jamais une décision

Tous les citoyens ne sont pas consultés à chaque tick : un citoyen n'est
sollicité que si son propre écart avec la position actuelle de l'élu
dépasse un seuil individuel (`base_threshold`, tiré une fois par citoyen à
la génération de la population), lui-même modulé par le contexte (la
dérive de mandat observée, la proximité de la prochaine élection). Ce
mécanisme est une **porte d'échantillonnage** — il détermine *qui* est
interrogé, jamais *ce qu'il répond* — et n'impose aucun plafond sur le
nombre de citoyens consultables à un tick donné.

### 10.7 Les événements exogènes — l'étincelle

Le palier v5 ajoute deux générateurs indépendants, chacun activable séparément
sous un même interrupteur maître (`events.enabled`) : un **scandale**
(arrivée Bernoulli par tick — la discrétisation standard d'un processus de
Poisson à résolution temporelle unitaire — ciblant l'élu en poste s'il en
existe un) et un **choc économique** (un climat AR(1) léger,
`x(t) = phi·x(t-1) + sigma·ε(t)`, à l'échelle de la population entière et
volontairement non borné — le même choix que pour `street_pressure`, dont la
borne utile vit chez le consommateur, pas chez le générateur).

**Aucun quatrième terme dans `écart(t)`.** Dans le droit fil de §10.2 : un
événement ne touche jamais `L(t)` directement — §8 rejette explicitement
« une formule d'impact directe sur `legitimacy_perceived` ». Il relève à la
place `event_salience`, un état décroissant propre à chaque citoyen, qui
abaisse le seuil d'éveil (§10.6) — un citoyen légèrement plus susceptible
d'être consulté, jamais un citoyen dont l'avis est présumé. Tout effet
ultérieur sur `L(t)` passe entièrement par le même canal citoyen que §10.5
documente déjà (`pressure_action`) : jamais une écriture directe.

`reaction_to_event` (dt=8) diffère aussi de §10.6 par sa forme : c'est une
consultation **de masse**, posée à chaque citoyen dès qu'un événement se
produit, et non filtrée par le seuil d'éveil — la porte d'échantillonnage
gouverne la *pression*, pas la *perception* d'un événement.

**L'étincelle, pas encore la cascade.** Un run dédié (`scripts/acceptance_v5_results.md`)
vérifie qu'un tick de choc produit un pic ponctuel et visible du taux de
consultation, distinct de l'érosion graduelle de la déviation de mandat déjà
documentée en §10.4 — dans le même run. Ce n'est **pas** une cascade : ce run
tourne sans graphe social (`neighbors_acting` y reste `null`, régime
atomisé), et §7bis.9e du plan de conception est explicite — un basculement de
type Gilets jaunes « n'est pas atteignable avant v6 », qui requiert
simultanément le graphe social, les chocs exogènes et les leviers de
pression. Le graphe social lui-même existe depuis le palier v6a (§10.8) ; la
combinaison des trois ingrédients simultanément n'a, elle, jamais été
exécutée (§10.8 sa propre limite).

Ce palier apporte enfin une réponse partielle au point ouvert n°5
(régénération des personas) : `economy_shock_threshold` définit désormais
concrètement ce qu'est « un choc économique majeur » — sans pour autant
clore le point, la bibliothèque de personas elle-même (§9) restant à
construire.

**Avertissement daté sur ce run (ajouté 2026-08-22, non intégré au texte
ci-dessus).** Le run cité (`electoral_only-llm-8y-events-r0.15-s0.25`,
2026-08-15) est **antérieur** à l'ensemble des correctifs de fiabilité
LLM produits par l'investigation « bug 4 » de cette même session
(2026-08-17 → 2026-08-22) : la correction du non-déterminisme au
démarrage GPU (2026-08-18), la mitigation cache-recycling (2026-08-20), et
la découverte d'un taux d'incohérence `blank`/`ranking` déterministe sur
`vote_cast` mesuré à **~6,7 %** des appels (`cache_recycle_chunk_size_tension_findings.md`,
2026-08-22) — un mode d'échec où une relance identique à température=0 ne
fait que reproduire la même décision fautive plutôt que de s'en écarter.
Un audit a posteriori de ce run précis (relecture des 300 événements
`vote_cast` journalisés, ticks 0/16/32, contre la règle §3.6.1 exacte)
n'y a trouvé **aucune** incohérence `blank`/`ranking` — cohérent avec le
`replays.log` vide du run lui-même. Ce n'est pas une preuve que rien
d'autre n'a pu y être affecté (l'audit ne couvre que cette règle précise,
pas les autres modes de défaillance identifiés la même semaine), mais
rien dans les données journalisées de ce run ne contredit sa propre
conclusion. **Le résultat n'est donc pas invalidé — il reste non
re-vérifié sous le code corrigé**, et cette distinction est délibérée.

### 10.8 Le graphe social et la contagion

Le palier v6a (§5) construit un graphe social déterministe, propre au
projet (`SocialGraph`, jamais un `networkx.Graph` brut hors de
`social_graph.py`) — trois topologies possibles (`watts_strogatz`,
`erdos_renyi`, `barabasi_albert`), statique pour l'instant : le point ouvert
du plan de conception sur un graphe évolutif (homophilie) reste
volontairement non résolu (`evolving: true` est analysé puis rejeté au
chargement de la configuration, le même garde-fou TRANCHÉ que
`recall_floor_indexed_on_l0`).

**`neighbors_acting(citoyen, cible)` — la définition retenue.** Le plan de
conception emploie deux fois le même verbe, « déjà **mobilisée** », jamais
« déjà agi » : la fraction est donc calculée **uniquement** sur les voisins
dont la dernière décision `pressure_action` **appliquée** était `MOBILIZE`
(§7bis.4b) — jamais une signature ou un lancement de pétition (§7bis.4a,
un levier institutionnel distinct, aux conséquences propres). La fraction
est aussi bornée à la **même cible** : un voisin ayant mobilisé contre un
élu depuis remplacé ne compte pas. Un citoyen isolé (aucun voisin dans le
graphe) obtient `0.0`, jamais une division par zéro — un état réel et
documenté, pas une approximation.

Comme `street_pressure` pour dt=6 (§10.4), ce terme porte **un tick de
retard structurel** : `decide_pressure_actions` regroupe toute une cohorte
en un seul appel gelé avant qu'aucune décision n'aboutisse, donc la
décision d'un voisin au *même* tick est par construction invisible.

**Le canal, jamais une règle imposée.** `neighbors_acting` alimente deux
choses, séparément :
- un quatrième terme dans `f(contexte)` du seuil d'éveil (§10.6),
  symétrique à `mandate_deviation`/`event_salience` — abaisse le seuil,
  ne décide jamais : la porte reste une porte (§7bis.9d).
- le champ `ctx.neighbors_acting` de `pressure_action` (dt=10), une
  fraction réelle dès que `social_graph.enabled` est vrai, **indépendamment**
  de la modulation du seuil elle-même — un choix délibéré du palier v6a
  Lot 1 : le graphe peut informer le LLM sans mécaniquement filtrer qui
  est consulté, un bras expérimental à part entière.

**Le tableau du §7bis.9f, tel quel :**

| Régime | Palier | `f(contexte)` inclut le voisinage ? | Cascade possible ? |
|---|---|---|---|
| Pression atomisée | v4/v5 | Non | Non, par construction |
| Pression avec contagion | v6a | Oui | Oui, jamais imposée |

**Le run d'acceptation** (`scripts/run_v6a_acceptance.py`, résultats dans
`scripts/acceptance_v6a_results.md`) compare les deux régimes sur une
configuration par ailleurs strictement identique (`mobilization_only`, seed
42, `population_size=100`, 8 ans) — la seule variable qui change est
`social_graph.enabled`/`awakening.context_modulation.neighbors_acting`, à
l'image exact du tableau ci-dessus. Le bras atomisé est cité verbatim
depuis `scripts/acceptance_v4_results.md` (palier v4 Lot 8), jamais
ré-exécuté.

**Ce que le run mesure, honnêtement (n=1, une seule graine).** Sur
l'agrégat cumulé du terme, la contagion n'amplifie pas mécaniquement la
mobilisation : la part `MOBILIZE` du `lever mix` est légèrement **plus
basse** sous contagion (0,629 contre 0,699 en régime atomisé) et la
légitimité moyenne en fin de run est plus **haute** (0,475 contre 0,370) —
même nombre de rappels dans les deux bras (2, tous par plancher de
légitimité). Le canal n'agit donc pas comme un simple multiplicateur
d'ampleur. Ce qu'il produit, en revanche, c'est un **pic de synchronisation
au tick** que rien dans le régime atomisé ne peut produire par
construction : jusqu'à 85 citoyens sur ~100 consultés mobilisent au même
tick sous contagion+LLM, contre un maximum de 39 sur le bras déterministe
équivalent (`neighbors_acting` réalisé : moyenne 0,184, maximum 1,000 —
le canal est réellement actif, pas seulement câblé). C'est la signature
d'un moment de bandwagon ponctuel, pas d'une dérive cumulative — cohérent
avec « l'étincelle, pas encore la cascade » : la contagion change la
*forme* temporelle de la mobilisation (des pics synchrones) sans changer
son volume agrégé sur ce seed précis. Chiffres complets dans
`scripts/acceptance_v6a_results.md`.

**Limite assumée, énoncée sans détour : ce n'est toujours pas la cascade
complète.** §7bis.9e du plan de conception est explicite — un basculement
de type Gilets jaunes exige **simultanément** le graphe social (v6a), les
chocs exogènes (v5) et les leviers de pression (v4). Ce run isole
délibérément l'effet marginal du seul canal de contagion, sur une
population déjà capable de se mobiliser (`events.enabled` reste `false`
partout) — v5 Lot 5 a déjà, séparément et honnêtement, démontré la moitié
« étincelle » de cette même conclusion à trois ingrédients (§10.7). Les
deux n'ont jamais été exécutés ensemble.

**Avertissement daté sur ce run (ajouté 2026-08-22, non intégré au texte
ci-dessus).** Le run cité (`contagion-llm-8y`, 2026-08-16) est, comme
celui de §10.7, **antérieur** à l'ensemble des correctifs de fiabilité
LLM de l'investigation « bug 4 » (2026-08-17 → 2026-08-22) — même
chronologie, mêmes correctifs concernés (non-déterminisme au démarrage
GPU, mitigation cache-recycling, taux d'incohérence `blank`/`ranking`
sur `vote_cast` mesuré à ~6,7 % des appels). Un audit a posteriori des
300 événements `vote_cast` journalisés de ce run précis (ticks 0/16/32,
règle §3.6.1 exacte) n'y a trouvé **aucune** incohérence — cohérent avec
son propre `replays.log` vide. Comme pour §10.7 : ceci ne couvre que
cette règle précise, pas les autres modes de défaillance identifiés la
même semaine, mais rien dans les données journalisées de ce run ne
contredit sa propre conclusion. **Le résultat n'est donc pas invalidé —
il reste non re-vérifié sous le code corrigé.**

### 10.9 La chambre de sortition — sincère ou erratique ?

**n=1, une seule graine (seed=42) : ce qui suit est un point de mesure, pas
une moyenne statistique — et il a fallu trois runs, un bug de métrique
corrigé et un second confond de calendrier résolu pour l'obtenir.**

Le palier v6b (§6bis.3) construit un second corps délibératif, tiré au sort
plutôt qu'élu — explicitement conçu comme **groupe de contrôle** : « aucun
mandat électoral à trahir », insensible par construction aux trois canaux de
pression du §7bis (pas de pétition, pas de mobilisation, pas de plancher de
légitimité — rien de tout cela ne peut atteindre un citoyen tiré au sort).
Le plan de conception pose l'hypothèse directement : « l'absence de pression
électorale produit-elle des décisions plus **sincères** (alignées sur ses
propres `issue_positions`) ou plus **erratiques** (aucun garde-fou de
responsabilité) ? »

**Sélection et rotation.** 30 sièges (configuration livrée), mandat d'un an,
non renouvelable — au sens strict : un citoyen déjà tiré une fois est exclu
du bassin tant qu'il reste des citoyens jamais tirés. À l'échelle livrée
(`population_size=100`, `seats=30`), ce bassin strict s'épuise mesurablement
tôt dans un run (autour du tick 12-16, `scripts/sortition_calibration_results.md`) —
assoupli ensuite en « jamais deux mandats qui se chevauchent », sans quoi la
chambre se viderait pour le reste du run.

**`chamber_deliberation` (dt=11) — la décision LLM.** Chaque membre siégeant
révise, chaque tick, sa `chamber_position` par rapport à sa propre
`issue_positions` sincère (jamais de `pledged_platform` — un tiré au sort n'a
rien promis). Le contexte transmis au modèle ne porte qu'un seul champ,
`ticks_left` : aucune légitimité, aucune déviation de mandat, aucune pression
de rue, aucun voisin — l'isolement du plan de conception est une propriété
structurelle du schéma, pas une consigne de prompt. `chamber_deviation`
(`weighted_euclidean(issue_positions, chamber_position, issue_priorities)`)
est l'analogue direct de `mandate_deviation` (§10.4), appliqué à un citoyen
qui n'a rien promis.

**Deux runs, un bug de métrique découvert entre les deux.** Un premier run
d'acceptation (`recall_floor` par défaut, menu `both`) a révélé un confond
de calendrier : sous le menu complet, la légitimité du président élu
s'effondre en un tick après quasi chaque élection (`L` 0,43→0,12, puis
0,44→0,11), déclenchant un rappel par plancher dans les deux cas — le poste
reste vacant l'essentiel des 33 ticks, et `mandate_deviation` lu à zéro tout
du long ne reflétait donc rien : le président n'avait presque jamais
l'occasion de dériver. Un second run, identique à l'exception de
`legitimacy.recall_floor=0.0`, élimine ce confond par construction
(`office_occupancy=1.0`, zéro rappel sur tout le run) — mais y révèle un
second problème, de nature différente : `mandate_deviation` restait
*encore* à zéro, alors même que le président siégeait sans interruption.
Investigation : `pledge_scope: top_k_priorities` (le mode livré) ne
pondère que les 5 dimensions de priorité les plus élevées du titulaire,
remises à zéro puis renormalisées — un bug de conception de métrique, pas
un artefact de ce run précis (documenté dans les docstrings de
`accountability.py` et dans `traceability.md`). Sur ce run, les trois
dimensions sur lesquelles le président dérivait réellement (poids 0,0745 /
0,0395 / 0,0205) ne faisaient simplement pas partie de son propre top-5 —
la métrique était structurellement aveugle à la dérive, pas simplement
sous-pondérée.

**La mesure corrigée — deux chiffres, deux significations.** Recalculée
avec la même méthode déjà utilisée par `chamber_deviation`
(`weighted_euclidean` sur le vecteur de priorités complet, sans troncature),
la déviation *officielle* du président élu — celle que le modèle mesure et
sur laquelle repose toute décision en aval, puisque `écart(t)`, le vote de
confiance et le seuil d'éveil lisent tous `revealed_position`, donc sa
version clampée — s'établit à une moyenne de 0,1496 sur les 33 ticks
(maximum 0,2312), contre une chambre tirée au sort quasi inerte (moyenne
0,000036, maximum 0,0353 — 99,70 % des décisions étiquetées
`SINCERE_POSITION` par le modèle lui-même). C'est déjà, sur cette seule
base, la première mesure qui distingue réellement les deux trajectoires.

**Mais la série côté président n'est pas monotone continue : elle plafonne,
et ce plafonnement n'est pas un arrêt de la pression.** Elle s'immobilise
exactement à deux reprises (0,194070 du tick 10 au tick 15 ; 0,231248 du
tick 27 au tick 31), à chaque fois en seconde moitié de mandat. Vérifié
directement contre le journal : à chacun de ces ticks,
`representative_response` continue d'émettre, sans exception, un `shifts`
non vide (motif `302 STREET_PRESSURE_RESPONSE`, `stance=1` concession) sur
les mêmes trois dimensions, avec un delta positif — la pression ne s'arrête
jamais. Ce qui plafonne, c'est `apply_shifts` : les trois dimensions ont
déjà atteint 1,0, et chaque delta suivant vise une cible non bornée
supérieure à 1,0 (1,15 / 1,10 / 1,05 typiquement), silencieusement absorbée
par le clamp. Lu seul, un tel plateau se prête à une lecture ambiguë — un
ralentissement réel de la pression de rue, ou une saturation de l'espace
des positions — d'où la reconstruction qui suit.

Une seconde reconstruction, purement diagnostique, tranche cette ambiguïté.
Méthode : rejouer les mêmes `shifts` que le journal officiel, tick par
tick, à partir de la même `pledged_platform` de départ — mais sans jamais
appliquer le clamp `[0,1]` d'`apply_shifts` ; chaque delta s'accumule tel
quel, dimension par dimension. Sous cette reconstruction, la déviation
« fantôme » non bornée du président grimpe à 0,701 en fin de premier
mandat (contre 0,194 côté clampé — facteur **×3,6**) et 0,642 en fin de
second mandat (contre 0,231 — facteur **×2,8**) : elle continue de croître
linéairement pendant tout le plateau, confirmant que la pression ne s'est
jamais arrêtée. Cette seconde valeur ne remplace pas la première : les
deux répondent à des questions différentes. La déviation clampée est ce
que le système *mesure et sur quoi il agit* — la seule quantité qui existe
dans une structure de données du modèle. La reconstruction non clampée
n'existe nulle part dans le modèle ; elle répond à « quelle est l'ampleur
réelle de la pression que le président a encaissée », indépendamment de ce
que sa position peut encore exprimer une fois les bornes atteintes.

**Troisième run — résoudre le confond de vacance autrement que par un
plancher nul.** Le deuxième run élimine le confond de calendrier avec
`legitimacy.recall_floor=0.0`, mais au prix d'un choix scientifiquement peu
satisfaisant : un plancher nul ne teste pas la responsabilité, il l'éteint.
Une alternative plus fidèle existe dans les mécanismes déjà livrés : sous
`pressure_menu.electoral_only=True`, `petition_pressure` et `street_pressure`
sont structurellement nuls (la configuration interdit la pétition et la
mobilisation sous ce menu), et `passive_erosion_weight` livré vaut déjà 0,0
— donc `écart(t) ≡ 0` quel que soit `mandate.enabled`, `L(t)` converge vers
son point fixe `m`, et `crosses_floor` ne peut jamais se déclencher tant que
`m > recall_floor` — corroboré empiriquement par les trois lignes
`electoral_only` déjà commitées de `acceptance_v4_results.md` (zéro rappel
sur les trois). `representative_response` (dt=6), lui, n'est jamais gaté sur
`pressure_menu` — seulement sur `llm.enabled and mandate.enabled` — donc le
président reste exposé exactement comme sous `both`, à un détail près :
`ctx.street` devient `None` plutôt qu'une vraie valeur (« un représentant
aveugle à la rue »).

Un troisième run (`--menu electoral_only`, plancher de rappel inchangé à
0,2, mêmes 8 ans / 33 ticks) a été pré-enregistré avant lancement :
falsifiables déclarés à l'avance (`recalls_by_trigger == {}`,
`office_occupancy == 1.0`, série `mandate_dev` sourcée `"ctx"`), et trois
branches nommées pour la seule question réellement ouverte — la moyenne de
déviation unifiée pourrait rester comparable au second run (la dérive n'est
pas pilotée par la rue), matériellement plus basse mais non nulle (la rue
est un contributeur, pas la seule cause), ou quasi nulle (sans aucun canal
de pression, rien ne pousse le président à bouger). Aucune valeur n'a été
pariée à l'avance ; le critère de succès était de rapporter le chiffre réel,
quelle que soit la branche.

Résultat : tous les falsifiables structurels tiennent (`recalls_by_trigger={}`,
`office_occupancy=1,0`, 990 `chamber_deliberation` et 9 `sortition_rotation`
— identiques au second run événement pour événement, confirmant que la
chambre reste insulée du menu de pression). Les élections elles-mêmes sont
byte-identiques entre le deuxième et le troisième run (même titulaire,
mêmes `pledged_platform`, aux trois tours) : ni la génération de population
ni les décisions de candidature/nomination/vote ne lisent quoi que ce soit
dépendant de `pressure_menu` — les deux runs comparent donc réellement le
même président sous deux régimes de pression, pas deux présidents
différents. La déviation unifiée s'établit à une moyenne de 0,1017
(maximum 0,2312) sur ce run, contre 0,1496 (maximum 0,2312) sur le second —
**branche intermédiaire** : retirer la rue du contexte du président fait
baisser la dérive moyenne d'environ un tiers, mais ne l'annule pas. Le
maximum, lui, est identique au bit près entre les deux runs — pas une
coïncidence suspecte : reconstruction faite depuis les deux journaux bruts,
les deux trajectoires convergent indépendamment vers la saturation des
**trois mêmes dimensions** au clamp `[0,1]` (le reste du vecteur reste
exactement égal à `pledged_platform` dans les deux cas), atteinte au tick
27 sous pression complète et seulement au tick 30 sous `electoral_only` —
même plafond, franchi plus tard sans la rue, ce qui est précisément ce qui
tire la moyenne du troisième run vers le bas sans toucher son maximum.
Côté chambre, rien ne bouge : déviation moyenne 0,0000357 (maximum 0,0353),
99,70 % des décisions étiquetées `SINCERE_POSITION` — quasi identique au
second run.

**Ce que cela signifie pour l'hypothèse** : sur les trois runs menés, la
réponse penche nettement vers « sincère pour la chambre, erratique pour le
président élu » — y compris quand on retire délibérément la rue de son
contexte. Le second run isole la dérive sous pression complète (moyenne
0,1496, elle-même plafonnée par le clamp à un facteur ×2,8-×3,6 en dessous
de la pression réellement encaissée) ; le troisième montre que retirer la
pétition et la mobilisation ne fait baisser cette dérive que d'un tiers
environ (0,1017), jamais à zéro — la chambre, elle, reste inerte dans les
trois configurations testées. Ce qui reste ouvert : *pourquoi* un président
continue de dériver même sans aucun canal de pression citoyenne actif — le
simple fait d'avoir un mandat, une promesse à laquelle on peut être
comparé, et une échéance électorale à venir semble suffire à produire une
dérive substantielle, mais rien dans ces trois runs n'isole laquelle de ces
composantes en est la cause. Ce n'est toujours pas une conclusion générale :
n=1, une seule graine sur les trois runs, aucune bande de Monte-Carlo, et le
premier run (confondu par le calendrier de rappel) reste une donnée
distincte et informative sur la dynamique du menu `both`, pas une mesure à
écarter.

**Limite assumée, énoncée sans détour : ce n'est ni un test institutionnel,
ni une comparaison statistiquement établie.** Le point ouvert n°11 du plan
de conception (droit de veto de la chambre) reste entièrement hors
périmètre — `veto_power`/`veto_delay_ticks` sont analysés et conservés en
configuration depuis v6 Lot 1 mais ne sont consommés par aucun code : ce
MVP est une comparaison de trajectoires, sans aucune conséquence
institutionnelle propre à la chambre.

### 10.10 Limites connues du modèle v4, v5, v6a et v6b

- **`seed=42` — la seule graine jamais utilisée par un run d'acceptation de
  ce projet — n'a jamais été validée comme représentative, et le mécanisme
  complet qui la rend fragile est maintenant identifié, pas seulement
  corrélé.** Un premier sweep de 11 graines alternatives
  (`scripts/acceptance_cascade_results.md`, run cascade v4+v5+v6a) montrait
  déjà que 9 sur 11 ne produisent aucun président élu (`election_no_winner`
  au second tour du `two_round`, le Blanc l'emportant). Une investigation
  dédiée, élargie à 40-60 graines et menée directement contre le pipeline
  de production (`generate_population` → `initialize_parties` →
  `select_party_nominee` → `build_ranking` → `get_two_round_winner`),
  ferme la chaîne causale complète :
  - À l'échelle du projet, le Blanc l'emporte sur **41/60 graines (68 %)**
    à la configuration livrée — un taux d'échec bien plus élevé que le
    premier sweep ne le laissait supposer.
  - **Le mécanisme du second tour contre le Blanc est une condition
    déterministe, pas probabiliste** : une fois le Blanc qualifié pour le
    second tour, `build_ranking` classe systématiquement tout candidat
    dans la tolérance (`blank_threshold`) d'un électeur au-dessus du Blanc,
    et tout candidat hors tolérance en dessous — donc le second tour se
    réduit, pour chaque électeur, à une seule question binaire : *ce
    finaliste précis m'est-il personnellement acceptable ?*, indépendamment
    des trois autres candidats et de leur score au premier tour. Vérifié
    empiriquement : le Blanc gagne si et seulement si l'acceptabilité du
    finaliste dans l'ensemble de la population est `≤ 50 %` — frontière
    exacte, mesurée sur 40 graines (`max` quand le Blanc gagne = 50,0 %,
    `min` quand un candidat réel gagne = 51,0 %, aucun chevauchement).
  - **Pourquoi cette majorité est difficile à atteindre** : `citizens.
    position_dist: uniform` disperse 100 citoyens de façon maximale sur un
    espace à 20 dimensions, sans centre de gravité naturel ; combiné à une
    pondération de priorités individualisée par électeur
    (`priority_dist: dirichlet`), aucun point unique n'est proche, sous la
    métrique propre à chacun, de plus de la moitié d'une population aussi
    dispersée.
  - La méthode de sélection du candidat de chaque parti a un effet réel
    mais secondaire : remplacer le critère livré (le membre du parti au
    score d'ambition le plus élevé — un trait indépendant de la position
    politique, artefact du `ambition_threshold=0.0` que tout script
    d'acceptance impose) par le membre le plus proche du centroïde
    k-means du parti fait passer le taux de victoire du Blanc de **70 % à
    27,5 %** (5 partis, 40 graines) — sans toucher au reste du pipeline.
    Augmenter le nombre de partis/nominee n'aide pas de façon monotone
    (55 % à 10 partis, mais remonte à 67,5 % à 15-20) : la couverture
    s'améliore mais la fragmentation du vote "acceptable" s'aggrave en
    proportion.
  - **Le levier qui referme la chaîne** : `citizens.position_dist` accepte
    déjà `gaussian_mixture` dans le schéma de configuration, mais
    `generate_population` le rejette avec `NotImplementedError` — jamais
    implémenté. Remplacer uniquement le tirage des positions (tout le
    reste du pipeline inchangé) par une simple gaussienne centrée
    (`std=0.30`, toujours large) fait chuter le taux d'échec de 27,5 % à
    2,5 % (1/40) ; `std≤0.20`, ou un mélange à 2-3 modes, l'annule
    entièrement sur les 40 graines testées.

  Investigation menée intégralement en lecture/mesure contre le pipeline
  réel, aucun changement de code de production. Touche rétroactivement
  **tout** run d'acceptation du projet, de v4 Lot 8 jusqu'aux runs v6b et
  cascade les plus récents : chacun a utilisé `seed=42` sans que sa
  représentativité n'ait jamais été vérifiée.
  **Décision de correction, prise le 2026-08-25**
  (`plan-distribution-positions-seeds.md`) : `citizens.position_dist:
  factor_structure` — pas `gaussian_mixture` (jamais implémenté, et un
  mélange présupposerait la question de convergence/polarisation que la
  vue méso existe pour *observer*, §14.2 du plan de conception), pas non
  plus une révision de `select_party_nominee`. Positions générées via un
  modèle factoriel à bas rang (`position = sigmoid(facteurs · loadings +
  bruit)`, 2 facteurs — l'axe économique et l'axe sociétal déjà nommés en
  §14.2), qui corrèle les 20 dimensions de façon réaliste sans imposer de
  pic artificiel : facteurs tirés d'une distribution unimodale, donc
  neutre sur la question convergence/polarisation. Choisie après un
  cadrage théorique écrit avant tout sweep (littérature déjà citée par le
  projet : Downs 1957 justifie une gaussienne simple mais sur un espace à
  une seule dimension ; Iyengar et al. 2019, §5, documente une
  polarisation qui argumenterait pour un mélange ; la structure
  factorielle répond aux deux en restant agnostique). Un sweep comparatif
  à 40 graines contre le vrai pipeline confirme : 0/40 victoires du Blanc
  (contre 11/40 sous `uniform`), corrélation inter-dimensions réaliste
  (0,54, contre 0,08 pour une gaussienne simple appliquée indépendamment
  par dimension — qui ne corrèle rien), variance seed-à-seed préservée
  (pas de consensus artificiel). Adoptée comme **nouveau défaut livré**
  pour tous les runs futurs — les runs déjà publiés (v4 Lot 8 à la
  cascade v4+v5+v6a) ne sont **pas** rejoués ni réétiquetés
  rétroactivement ; ils restent documentés comme ayant tourné sous
  `uniform`/`seed=42`, non validée comme représentative au moment de leur
  publication. Un re-baseline sélectif d'un ou plusieurs résultats déjà
  publiés reste une décision distincte, non prise à ce stade.
- **`stance = 4` (contre-mobilisation) est observable mais mécaniquement
  inerte** : aucun levier citoyen pro-sortant n'existe encore pour lui
  répondre — un représentant peut choisir cette posture, mais rien dans le
  modèle n'en tire de conséquence institutionnelle.
- **Le vote de confiance reste déterministe même quand l'agent LLM pilote
  les autres décisions** — son résultat n'est donc pas directement
  comparable à celui de l'élection présidentielle *du même run*, qui, elle,
  passe par l'agent.
- **Régime de pression atomisée par défaut** : la configuration livrée garde
  `social_graph.enabled: false` — un citoyen ne voit ni le niveau de
  mobilisation agrégé (`street_pressure`) ni le taux de signature d'une
  pétition en cours (`signed_ratio`), seulement le fait qu'une pétition
  existe. Le canal de contagion (§10.8) existe depuis v6a mais reste un
  bras expérimental, jamais le régime par défaut.
- **`m` porte un biais empirique à la baisse sur le chemin LLM** au-delà de
  six candidats : le classement produit par l'agent est tronqué au top-5,
  si bien qu'un vainqueur absent d'un bulletin tronqué compte comme
  "non classé au-dessus du blanc" plutôt que d'être exclu du dénominateur.
- **`lame_duck_deviation_delta` n'est pas mesurable à la configuration
  livrée** (`president_term_limit: null` — aucune limitation de mandat) :
  la métrique existe et est testée, mais elle n'a rien à comparer tant
  qu'aucun mandat limité n'est configuré.
- **Le basculement complet à trois ingrédients n'est toujours pas
  démontré** : v5 fournit l'étincelle (§10.7) et v6a le graphe social
  (§10.8), chacun mesuré séparément — jamais ensemble dans un même run.
- **`social_graph.evolving` (homophilie) reste non implémenté** : le point
  ouvert du plan de conception (§5, « graphe social statique ou évolutif ? »)
  reste ouvert ; seul un graphe statique existe.
- **La chambre de sortition (§10.9) reste un dispositif de comparaison
  sans conséquence institutionnelle** : aucun droit de veto (point ouvert
  n°11 du plan de conception, `veto_power`/`veto_delay_ticks` analysés et
  conservés en configuration mais consommés par aucun code). Le chiffre qui
  distingue les deux trajectoires (`mandate_deviation` unifiée du président
  vs `chamber_deviation` de la chambre) est un plancher, pas une mesure
  exacte : le clamp `[0,1]` d'`apply_shifts` sature sur les dimensions sous
  pression continue et absorbe silencieusement toute dérive au-delà —
  mesuré une première fois sous pression complète (facteur ×2,8 à ×3,6),
  corroboré une seconde fois de façon indépendante sous `electoral_only`
  (mêmes trois dimensions saturées, même plafond, atteint plus tard). n=3
  runs, une seule graine, aucune bande de Monte-Carlo.
- **La configuration livrée des événements exogènes ne se déclenche presque
  jamais sur un run court** : à `(phi=0.8, sigma=0.1, seuil=0.5)`, le choc
  économique est un événement à ~3 écarts-types, jamais observé sur un run
  de 121 ticks dans le sweep de calibration (`scripts/events_calibration_results.md`).
  Le run d'acceptation de §10.7 utilise donc une configuration délibérément
  recalibrée, documentée dans `scripts/acceptance_v5_results.md`, jamais la
  configuration livrée par défaut.

### 10.11 Références

Ce chantier n'introduit pas de nouvelle bibliographie académique propre —
`support(t)` (§10.1) est une résolution de modélisation, pas un résultat
publié, et c'est précisément ce que fermer le bloquant A6 signifie : aucune
référence unique ne fait autorité sur cette formule. Deux publications déjà
citées dans le plan de conception restent pertinentes pour situer le
modèle dans la littérature :

- **Shugart, M.S. & Carey, J.M.** (1992). *Presidents and Assemblies:
  Constitutional Design and Electoral Dynamics*. Cambridge University
  Press. — calendriers électoraux et interaction présidentielle/législative,
  qui informe le séquencement des scrutins de Polity (§13 du plan de
  conception).
- **Superti, C.** (2020). Travaux sur le vote blanc/nul comme signal de
  protestation — cité par le plan de conception pour le régime d'inaction
  des mécontents (§10.4) ; référence bibliographique complète non encore
  vérifiée dans ce document (à confirmer).

Pour la spécification complète (formules, séquencement par tick, schémas
de sortie de l'agent, journal d'événements), voir
`polity-simulation-design-v2.md` — document de conception local à ce
chantier, non publié dans ce dépôt.

---

## 11. Références

### Ouvrages fondamentaux

- **Arrow, K.J.** (1951). *Social Choice and Individual Values*. Yale University Press.
- **Balinski, M. & Young, H.P.** (1982). *Fair Representation*. Yale University Press.
- **Balinski, M. & Laraki, R.** (2010). *Majority Judgment: Measuring, Ranking, and Electing*. MIT Press.
- **Black, D.** (1948). "On the Rationale of Group Decision-Making". *Journal of Political Economy*, 56(1), 23–34.
- **Brennan, J.** (2016). *Against Democracy*. Princeton University Press.
- **Caplan, B.** (2007). *The Myth of the Rational Voter*. Princeton University Press.
- **Condorcet, M.J.A.N.** (1785). *Essai sur l'application de l'analyse à la probabilité des décisions rendues à la pluralité des voix*. Paris.
- **Downs, A.** (1957). *An Economic Theory of Democracy*. Harper & Row.
- **Fishkin, J.** (2018). *Democracy When the People Are Thinking*. Oxford University Press.
- **Gibbard, A.** (1973). "Manipulation of Voting Schemes". *Econometrica*, 41(4), 587–601.
- **Hotelling, H.** (1929). "Stability in Competition". *The Economic Journal*, 39(153), 41–57.
- **Kemeny, J.G.** (1959). "Mathematics Without Numbers". *Daedalus*, 88(4), 571–591.
- **List, C. & Pettit, P.** (2002). "Aggregating Sets of Judgments". *Economics and Philosophy*, 18(1), 89–110.
- **Lijphart, A.** (1999). *Patterns of Democracy*. Yale University Press.
- **Mouffe, C.** (1993). *The Return of the Political*. Verso.
- **Pettit, P.** (1997). *Republicanism*. Oxford University Press.
- **Plott, C.R.** (1967). "A Notion of Equilibrium and Its Possibility Under Majority Rule". *American Economic Review*, 57(4), 787–806.
- **Rawls, J.** (1971). *A Theory of Justice*. Harvard University Press.
- **Rousseau, J.J.** (1762). *Du Contrat Social*. Amsterdam.
- **Satterthwaite, M.A.** (1975). "Strategy-Proofness and Arrow's Conditions". *Journal of Economic Theory*, 10(2), 187–217.
- **Schumpeter, J.A.** (1942). *Capitalism, Socialism and Democracy*. Harper & Brothers.
- **Sen, A.K.** (1970). *Collective Choice and Social Welfare*. Holden-Day.
- **Sen, A.K.** (1999). *Development as Freedom*. Oxford University Press.
- **Shapley, L.S. & Shubik, M.** (1954). "A Method for Evaluating the Distribution of Power in a Committee System". *American Political Science Review*, 48(3), 787–792.
- **Tocqueville, A. de** (1835). *De la Démocratie en Amérique*. Paris.
- **Van Reybrouck, D.** (2013). *Contre les élections*. Actes Sud.

### Articles clés

- **Bikhchandani, S., Hirshleifer, D. & Welch, I.** (1992). "A Theory of Fads, Fashion, Custom, and Cultural Change as Informational Cascades". *Journal of Political Economy*, 100(5), 992–1026.
- **Brams, S.J. & Fishburn, P.C.** (1978). "Approval Voting". *American Political Science Review*, 72(3), 831–847.
- **Buterin, V., Hitzig, Z. & Weyl, E.G.** (2019). "A Flexible Design for Funding Public Goods". *Management Science*, 65(11), 5171–5187.
- **Fiorina, M.** (1981). *Retrospective Voting in American National Elections*. Yale University Press.
- **Fishkin, J.** (1988). "The Case for a National Caucus". *The Atlantic*, August 1988.
- **Iyengar, S. et al.** (2019). "The Origins and Consequences of Affective Polarization in the United States". *Annual Review of Political Science*, 22, 129–146.
- **Lalley, S. & Weyl, E.G.** (2018). "Quadratic Voting: How Mechanism Design Can Radicalize Democracy". *American Economic Association Papers & Proceedings*, 108, 33–37.
- **Nanson, E.J.** (1882). "Methods of Election". *Transactions and Proceedings of the Royal Society of Victoria*, 19, 197–240.
- **Young, H.P.** (1988). "Condorcet's Theory of Voting". *American Political Science Review*, 82(4), 1231–1244.

### Ressources en ligne

- **Equal Vote Coalition** (STAR Voting) : www.equal.vote
- **The Center for Election Science** (Approval Voting) : www.electionscience.org
- **ElectionGuard** (E2E-V, Microsoft) : github.com/microsoft/electionguard
- **Pol.is** (Consensus clustering) : pol.is
- **vTaiwan** (Taiwan digital democracy) : info.vtaiwan.tw
- **RadicalxChange** (QV, QF) : www.radicalxchange.org
- **MGGG** (Algorithmic redistricting) : mggg.org

---

*Vote Lab est un projet personnel de recherche civique indépendant.
Ce document décrit les fondements théoriques des simulations implémentées
et est fourni à des fins éducatives et de recherche.*

*Dernière mise à jour : 2025*
