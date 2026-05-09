# Vote Lab — Méthodologie de recherche

> Document de référence pour les simulations de théorie du vote.  
> Version 1.0 · Mai 2026

---

## 1. Modèle spatial de vote

### 1.1 Architecture générale

Vote Lab implémente un **modèle spatial de vote** dans lequel chaque électeur et chaque candidat sont positionnés dans un espace idéologique à 20 dimensions (les *enjeux politiques*). La préférence d'un électeur pour un candidat est calculée comme une **utilité** — une valeur continue reflétant l'alignement politique, la loyauté partisane, et des facteurs socio-démographiques.

### 1.2 Les 20 enjeux politiques

```
economy          environment      healthcare       education
taxes            social_welfare   agriculture      public_transport
defense          gender_equality  pensions         climate_change
housing          immigration      crime_safety     technology_innovation
minimum_wage     business_regulation jobs           infrastructure
```

Chaque enjeu est représenté sur une échelle **[0, 1]** :
- `0` → position progressiste / interventionniste
- `1` → position libérale / conservatrice

### 1.3 Positions des acteurs

**Candidats** — chaque candidat possède :
- `ideology_position ∈ [0, 1]` : position idéologique globale
- `policies[enjeu] ∈ [0, 1]` : position sur chaque enjeu (dérivée de `ideology_position` avec bruit ±`position_variance`)
- `party_lean ∈ [-1, 1]` : orientation partisane (affecte le bonus de loyauté)
- `charisma ∈ [0.5, 1.0]`, `scandals ∈ {0, 1, 2}`, `campaign_funds`, `experience`, `popularity`

**Électeurs** — chaque électeur possède :
- `political_lean_normalized ∈ [0, 1]` : position idéologique
- `issue_positions[enjeu] ∈ [0, 1]` : position sur chaque enjeu (proche de `political_lean_normalized` avec bruit ±0.15)
- `issue_priorities[enjeu] ∈ [0, 1]` : importance relative de chaque enjeu (dérivée des caractéristiques démographiques)
- `blank_threshold ∈ [0, 1]` : seuil minimal d'utilité pour qu'un candidat soit préféré au vote blanc (voir §4)

---

## 2. Fonction d'utilité

### 2.1 Formule

```
utility(voter, candidate) =
    0.60 × issue_score
  + 0.20 × loyalty_bonus
  + 0.15 × charisma_effect
  +        scandal_penalty
  +        mood_effect
```

### 2.2 Composantes

**`issue_score`** — alignement pondéré sur les enjeux :

```
issue_score = Σ_k  issue_priorities[k] × (1 - |voter.issue_positions[k] - candidate.policies[k]|)
```

où `k` parcourt les enjeux prioritaires du votant. Les enjeux hors de `issue_priorities` sont ignorés. Un bonus de genre est ajouté pour les électrices si `candidate.policies[gender_equality]` est élevé (+10% × policies[gender_equality]).

**`loyalty_bonus`** — fidélité partisane :

```
candidate_lean_normalized = (candidate.party_lean + 1) / 2
party_match = 1 - |voter.political_lean_normalized - candidate_lean_normalized|
loyalty_bonus = voter.party_loyalty × party_match
```

**`charisma_effect`** = `candidate.charisma`

**`scandal_penalty`** = −0.3 × `candidate.scandals` (×1.5 si `charisma < 0.5`)

**`mood_effect`** = `voter.mood × 0.1 × (1 − candidate.scandals)`

### 2.3 Intervalle de l'utilité

L'utilité n'est pas bornée à [0, 1] en théorie, mais reste généralement dans [−0.2, 1.2] pour les combinaisons réalistes de paramètres. La condition `will_vote` requiert `utility > 0.3`.

---

## 3. Régret bayésien

### 3.1 Définition

Le **régret bayésien** (Bayesian Social Regret) d'une méthode de vote mesure l'écart moyen entre l'utilité maximale atteignable et l'utilité produite par l'élu :

```
BR(méthode) = (1/N) × Σ_i  [ max_c utility(voter_i, c)  −  utility(voter_i, winner) ]
```

où `N` est le nombre d'électeurs, `c` parcourt tous les candidats, et `winner` est le candidat élu par la méthode.

### 3.2 Interprétation

- `BR = 0` : la méthode élit le candidat qui maximise l'utilité collective → résultat optimal
- `BR > 0` : des électeurs auraient pu obtenir un meilleur résultat
- Plus le régret est **bas**, plus la méthode est **efficace socialement**

### 3.3 Limites

Le régret bayésien suppose que l'utilité est **cardinale et agrégeable**, hypothèse contestable en théorie du choix social (Arrow). Les utilités ici sont comparables au sein d'une population simulée mais ne le seraient pas nécessairement dans une vraie élection. Le calcul est sensible à la taille de la population et au nombre de candidats.

---

## 4. Vote blanc

### 4.1 Modélisation

Le vote blanc est intégré comme un **candidat implicite** inséré dans le classement de chaque électeur. Sa position dans ce classement dépend du `blank_threshold` du votant :

```
Rang du blanc = Nombre de candidats dont utility(voter, c) > voter.blank_threshold
```

Exemple : threshold = 0.5, utilités = {Alice: 0.7, Bob: 0.4, Carol: 0.2}
→ Classement : [Alice, **Blanc**, Bob, Carol]

### 4.2 Distribution de `blank_threshold`

```
blank_threshold ~ Beta(3, 5)   →   moyenne ≈ 0.375
```

La distribution Beta(3, 5) place la plupart des valeurs entre 0.15 et 0.65, reflétant que la majorité des électeurs votent blanc uniquement en cas d'insatisfaction marquée. Le taux d'insatisfaction générale (`dissatisfaction_rate`) décale ce seuil vers le haut (β·Beta(2,2) est ajouté pour chaque électeur).

### 4.3 Règles constitutionnelles

| Règle | Description |
|---|---|
| `SYMBOLIC` | Droit français actuel : compté mais non électif |
| `COMPETITIVE` | Le blanc peut gagner : s'il obtient le plus de premiers choix |
| `THRESHOLD_30` | Si blanc ≥ 30% → élection invalidée |
| `MAJORITY_REQUIRED` | Le vainqueur doit battre le blanc en duel pairwise |

---

## 5. Vote stratégique

### 5.1 Types de comportement

**Vote sincère** : l'électeur classe les candidats par utilité décroissante.

**Vote stratégique** : l'électeur modifie son bulletin pour améliorer le résultat selon la méthode utilisée.

| Méthode | Stratégie modélisée |
|---|---|
| Pluralité | Duverger : reporter sur le meilleur viable (top-2 des sondages) |
| Borda | Enterrement : placer le principal rival en dernière position |
| IRV | Compromis : promouvoir le meilleur viable si le candidat sincère n'est pas dans le top-2 |
| Approbation | Vote groupé : approuver uniquement le candidat de tête |
| Score | Exagération : donner 5 au préféré, 0 au principal rival |

### 5.2 `strategic_propensity`

Chaque électeur a une `strategic_propensity ∈ [0, 0.8]` calculée à partir de l'âge, du niveau d'éducation et de la loyauté partisane. Le `voting_style` ("sincere" ou "strategic") est tiré selon cette propension.

### 5.3 Vulnérabilité stratégique

Mesure de la proportion d'électeurs pouvant améliorer le résultat par une manipulation :

```
strategic_vulnerability = (nombre d'électeurs pouvant manipuler) / min(N, 100)
```

Pour les méthodes classées, on teste chaque permutation du bulletin sincère de chaque électeur.

---

## 6. Distributions idéologiques

| Distribution | Description | Paramétrage |
|---|---|---|
| `random` | Démographie française réelle (INSEE) | Beta(2,3) sur lean |
| `centrist` | Pic centré | Normal(0.5, 0.1) tronquée [0,1] |
| `polarized` | Bimodale | 50% Normal(0.2, 0.08) + 50% Normal(0.8, 0.08) |
| `left_skewed` | Majorité gauche | Beta(2, 5) |
| `right_skewed` | Majorité droite | Beta(5, 2) |

---

## 7. Données démographiques

### 7.1 Source des données d'âge

La distribution d'âge des électeurs est dérivée du **Recensement général de la population INSEE 2019** (RP2019), fichier « Individus localisés au canton-ou-ville ». Les colonnes `IND_SNHM** ` correspondant aux tranches 18-85 ans (par année) sont sommées sur les quatre groupes (communes rurales, urbaines de différentes tailles).

**Référence** : INSEE, Recensement de la population 2019, exploitation principale, tableaux détaillés disponibles sur [insee.fr](https://www.insee.fr/fr/statistiques/7704821).

### 7.2 Données électorales réelles

| Élection | Source officielle |
|---|---|
| France 2002 (1er tour) | Conseil constitutionnel — résultats officiels du 21 avril 2002 |
| France 2022 (1er tour) | Ministère de l'Intérieur — résultats officiels du 10 avril 2022 |
| USA 1992 | Federal Election Commission — Official 1992 Presidential Results |
| UK 2015 | Electoral Commission — 2015 UK Parliamentary general election results |

### 7.3 Modèle de conversion des données réelles en bulletins

Pour les élections historiques, les scores de premier tour sont convertis en bulletins classés synthétiques via un **modèle de proximité idéologique** :
1. Chaque candidat est positionné sur [0, 1] selon son affiliation politique connue
2. Un électeur qui a voté pour le candidat X classe tous les autres candidats par distance idéologique croissante à X
3. Le nombre de bulletins synthétiques pour chaque candidat est proportionnel à son score réel

Ce modèle simplifie les préférences réelles : les électeurs réels peuvent avoir des raisons non-idéologiques de voter.

---

## 8. Limites du modèle

### 8.1 Limites fondamentales

**Pas de vote expressif multi-dimensionnel** — le modèle réduit les préférences à une utilité scalaire. Des préférences cycliques (A > B > C > A au niveau individuel) sont impossibles par construction, alors qu'elles peuvent exister dans la réalité.

**Pas de dynamique de campagne** — les positions des candidats sont fixes. En réalité, les candidats adaptent leurs positions en fonction des sondages et de la pression de leurs bases. Le modèle « bandwagon » approxime cet effet au niveau de l'électorat mais pas des candidats.

**Pas d'information imparfaite** — chaque électeur connaît les positions exactes de tous les candidats et calcule son utilité avec précision. En réalité, les électeurs agissent sur des perceptions incomplètes ou biaisées.

**Pas de coalition** — le modèle ne simule pas les négociations de coalition post-électorales, essentielles pour les scrutins proportionnels.

### 8.2 Limites du modèle de vote stratégique

Les stratégies implémentées sont des heuristiques simples. Les stratégies réelles sont plus complexes, conditionnelles aux sondages, et dépendent de l'information disponible. Le paramètre `strategic_propensity` est tiré d'une distribution arbitraire, non calibrée sur des données empiriques de comportement électoral.

### 8.3 Limites du vote blanc

Le modèle du vote blanc suppose que `blank_threshold` capture entièrement la décision de voter blanc. En réalité, le vote blanc est influencé par des facteurs symboliques, protestataires et contextuels non modélisés.

### 8.4 Scalabilité

La méthode de Kemeny-Young est exponentielle en O(n!) avec n le nombre de candidats. Elle est automatiquement désactivée pour les élections avec plus de 5 candidats. Le calcul de vulnérabilité stratégique est limité à un échantillon de 100 électeurs.

---

## 9. Méthodes de vote implémentées

| Famille | Méthodes |
|---|---|
| **Pluralité** | Scrutin uninominal (Plurality), Scrutin à deux tours (Two-Round) |
| **Classé** | Borda, IRV, Coombs, Bucklin, Kemeny-Young, Condorcet, Minimax, Schulze, Positional Score |
| **Approbation** | Approval (avec seuil utilitaire sincère) |
| **Score** | Simple Score, STAR Voting, Median Voting, Mean-Median Hybrid, Variance-Based |
| **Proportionnel** | D'Hondt, Sainte-Laguë, Largest Remainder (Hare/Droop), STV (Droop quota) |

---

## 10. Critères d'Arrow vérifiés empiriquement

| Critère | Description |
|---|---|
| Critère de Condorcet | Si un vainqueur de Condorcet existe, la méthode l'élit |
| Critère du perdant de Condorcet | La méthode n'élit jamais le perdant de Condorcet |
| Monotonie | Promouvoir un candidat dans certains bulletins ne peut pas le faire perdre |
| Indépendance des alternatives non pertinentes (IIA) | Supprimer un non-vainqueur ne change pas le vainqueur |
| Critère de majorité | Un candidat préféré en tête par plus de 50% gagne |
| Symétrie de renversement | L'inverse du classement collectif n'élit pas le vainqueur original |

Le théorème d'impossibilité d'Arrow (1951) garantit qu'aucune méthode de vote classé ne peut satisfaire simultanément tous ces critères avec 3+ candidats.

---

*Vote Lab · Code source disponible sur GitHub · Contributions bienvenues*
