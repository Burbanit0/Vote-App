# Vote Lab — Référence théorique complète

> **Pour qui ?** Enseignants, chercheurs, étudiants en science politique,
> mathématiques ou économie souhaitant comprendre les fondements formels
> de chaque simulation proposée par Vote Lab.
>
> **Comment citer :** voir `METHODOLOGY.md` pour la bibliographie complète.

---

## Table des matières

1. [Fondements : la théorie du choix social](#1-fondements--la-théorie-du-choix-social)
2. [Les 17 méthodes de vote](#2-les-17-méthodes-de-vote)
3. [Les théorèmes d'impossibilité](#3-les-théorèmes-dimpossibilité)
4. [Les paradoxes démocratiques](#4-les-paradoxes-démocratiques)
5. [Modèles de comportement électoral](#5-modèles-de-comportement-électoral)
6. [Phénomènes de participation](#6-phénomènes-de-participation)
7. [Systèmes alternatifs de gouvernance](#7-systèmes-alternatifs-de-gouvernance)
8. [Solutions technologiques](#8-solutions-technologiques)
9. [Limites des modèles](#9-limites-des-modèles)
10. [Références](#10-références)

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

---

## 2. Les 17 méthodes de vote

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

---

## 10. Références

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
