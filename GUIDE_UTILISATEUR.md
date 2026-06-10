# Vote Lab — Guide complet d'utilisation

> **Pour qui ?** Ce guide est destiné à toute personne curieuse de comprendre comment les systèmes électoraux fonctionnent — aucune connaissance préalable requise.
>
> **Accès** : ouvrir `http://localhost:3000` dans votre navigateur (Chrome ou Firefox recommandé).

---

## Qu'est-ce que Vote Lab ?

Vote Lab est un laboratoire interactif qui répond à une question fondamentale et souvent ignorée : **la façon dont on compte les votes change-t-elle qui gagne une élection ?**

La réponse est oui — et c'est fascinant. Avec le même groupe d'électeurs ayant exactement les mêmes préférences, des systèmes de vote différents peuvent élire des candidats complètement différents. Vote Lab vous permet d'explorer cela en temps réel, en déplaçant des candidats sur une carte, en simulant des campagnes, en redessinant des frontières électorales, et bien plus.

**Ce que vous pouvez faire :**
- Comparer 17 méthodes de vote sur la même élection
- Rejouer des élections historiques réelles (France 2002, USA 1992, Allemagne 2021)
- Dessiner des circonscriptions et observer le gerrymandering
- Simuler comment la campagne électorale influence le résultat
- Explorer pourquoi certains électeurs s'abstiennent
- Et une dizaine d'autres expériences

---

## Page d'accueil — Le test rapide (30 secondes)

**Accès** : `http://localhost:3000`

La page d'accueil propose un widget interactif en 3 étapes.

### Étape 1 : Choisir un scénario

Quatre boutons représentent des situations électorales types :

| Scénario | Ce qu'il illustre |
|---|---|
| 🇫🇷 **France 2002** | Comment la gauche fragmentée a envoyé Le Pen au 2nd tour |
| 🇺🇸 **USA 1992** | Comment Perot tiers-candidat a aidé Clinton à gagner avec 43 % |
| ✅ **Consensus** | Cas idéal : tout le monde s'accorde |
| 📐 **Cycle Condorcet** | Cas où aucun vainqueur « juste » n'existe |

**→ Cliquez sur "France 2002"**

### Étape 2 : Choisir deux méthodes de vote

Deux menus déroulants vous permettent de choisir les systèmes à comparer. Essayez :
- **Méthode A** : `plurality` (scrutin uninominal — la méthode française)
- **Méthode B** : `schulze` (méthode par duels directs)

### Étape 3 : Observer le résultat

Après 1-2 secondes de calcul, deux cases s'affichent avec le vainqueur de chaque méthode.

**Résultat attendu avec France 2002** :
- `plurality` élit souvent **Chirac** ou **Le Pen** (selon la simulation)
- `schulze` élit souvent **Jospin** — le candidat que la majorité préférait en duel direct

👉 **Conclusion** : le même électorat, mais deux gagnants différents selon comment on compte. C'est l'essence du problème.

---

## L'Election Lab — Le cœur de Vote Lab

**Accès** : bouton `🔬 Election Lab` dans la barre de navigation, ou `http://localhost:3000/election-lab`

C'est l'outil principal. Il simule une élection complète et vous laisse explorer le résultat sous 20 angles différents.

### Configuration (panneau gauche)

Avant de simuler, vous configurez l'élection :

**Candidats** : chaque candidat a une position sur deux axes idéologiques :
- **X (horizontal)** : économie — de -1 (gauche économique) à +1 (droite économique)
- **Y (vertical)** : société — de -1 (conservateur) à +1 (progressiste/libéral)

**Exemple de configuration intéressante** :
- Alice : x = -0.5, y = 0.3 (gauche progressiste)
- Bob : x = 0.5, y = -0.2 (droite conservatrice)
- Carol : x = 0.0, y = 0.0 (centre)

**Électorat** : vous choisissez combien d'électeurs (50 à 1000) et leur distribution idéologique (`random`, `centrist`, `polarized`...).

**→ Cliquez sur le bouton "🗳️ Simuler"** et attendez 2-3 secondes.

---

### Onglet 📊 Résultats

**Ce que vous voyez** : un tableau montrant qui gagne selon chacune des 17 méthodes de vote.

**Ce qu'il faut regarder** :
- Le badge en haut indique le **taux d'accord inter-méthodes** : si c'est 100%, toutes les méthodes s'accordent — cas rare. Si c'est 50%, les méthodes sont profondément en désaccord.
- La colonne **Condorcet** ✓ indique si la méthode respecte le critère fondamental : "élire le candidat qui battrait tous les autres en duels directs"
- La colonne **Régret bayésien** mesure à quel point le résultat satisfait l'électorat dans son ensemble

**Résultat typique avec 3 candidats polarisés** :
- `plurality` (scrutin uninominal) élit souvent le candidat d'un camp extrême
- `schulze`, `borda`, `irv` élisent souvent le candidat du centre
- Le taux d'accord tombe à 30-60 % : les méthodes ne s'accordent pas

**→ Activez le "Mode Duel" (bouton ⚔)** pour comparer deux méthodes côte à côte. Sélectionnez `plurality` à gauche et `schulze` à droite. Si les vainqueurs sont différents, un bandeau rouge apparaît avec l'explication automatique.

---

### Onglet 🗺 Carte idéologique

**Ce que vous voyez** : une carte 2D où chaque point est un électeur. Les ★ sont les candidats.

**Interactions** :
- **Glissez un candidat** : le résultat de l'élection change en temps réel (après le drop, recalcul automatique en 150 ms)
- **Toggle "Heatmap"** (bouton vue) : la carte se transforme en carte de chaleur colorée — les zones rouges sont acquises à la droite, les zones bleues à la gauche
- **Toggle "Électeur médian"** : une croix ✛ orange apparaît au centre géométrique de l'électorat. Une ligne pointe vers le candidat que le Théorème de Black (1948) prédit comme vainqueur : le plus proche du médian.

**Expérience à faire** :
1. Activez "Électeur médian"
2. Glissez le candidat Carol vers le centre (x=0, y=0)
3. Observez la ligne verte ✓ : Carol est maintenant "conforme au théorème de Black"
4. Les autres méthodes élisent-elles Carol ? (Réponse : souvent oui pour Condorcet, parfois non pour Plurality)

**Expérience avec la heatmap** :
1. Passez en vue "Carte de chaleur"
2. Glissez un candidat : les couleurs se réorganisent — chaque zone passe à la couleur du candidat qui "possède" ce territoire idéologique
3. Les lignes blanches sont les frontières entre les zones d'influence

---

### Onglet 🎬 Pipeline

**Ce que vous voyez** : une animation montrant comment chaque modèle transforme l'électorat étape par étape.

**Ce que ça illustre** : une élection réelle ne commence pas par un vote sincère. Les électeurs sont d'abord influencés par la campagne, puis par la contagion sociale, puis par les médias. Le pipeline montre ces transformations l'une après l'autre.

**Pour l'activer** : cliquez "▶ Animer le pipeline". Les points changent de couleur progressivement à chaque étape.

**Étapes affichées** (si les modèles correspondants sont activés dans le panneau gauche) :
1. **Base** : préférences sincères initiales
2. **Campagne** : effets de la dynamique de campagne (sondages, Brownian motion)
3. **Contagion** : propagation du vote blanc dans le réseau social
4. **Information** : distorsion par les biais médias
5. **Résultats** : vainqueur final par méthode

---

### Onglet ▶ Animation du décompte

**Ce que vous voyez** : le décompte bulletin par bulletin, animé visuellement.

**Sélectionnez la méthode** `irv` (vote alternatif) et cliquez ▶ Jouer.

**Ce qui se passe** :
- Tour 1 : chaque électeur vote pour son 1er choix → si personne n'a la majorité absolue, le dernier est éliminé
- Tour 2 : les électeurs du candidat éliminé reportent leur voix sur leur 2e choix
- Et ainsi de suite jusqu'à ce qu'un candidat dépasse 50 %

**Résultat typique** : avec 3 candidats dont un centriste, le centriste gagne souvent en IRV même s'il était 3e au 1er tour — ses partisans étaient des 2es choix de tout le monde.

---

### Onglet 🎲 Monte Carlo

**Ce que vous voyez** : 100 à 500 élections simulées d'affilée, avec des tirages aléatoires légèrement différents à chaque fois.

**Pourquoi c'est utile** : une seule simulation peut être "chancieuse". Le Monte Carlo montre le comportement moyen et la stabilité de chaque méthode.

**Ce qu'il faut observer** :
- Le **graphe de convergence** : les courbes se stabilisent-elles rapidement ? Si oui, la méthode est robuste.
- Le **classement des méthodes** : le Race Bar en bas montre en temps réel quelle méthode a le meilleur taux de stabilité. Les barres se réordenent pendant que les simulations tournent.
- La **matrice de similarité** : après la simulation, un graphe D3 apparaît montrant quelles méthodes s'accordent souvent entre elles (nœuds proches = méthodes similaires).

**Expérience à faire** :
1. Passez l'électorat en `polarized`
2. Lancez 200 simulations
3. Observez : le taux d'accord inter-méthodes chute (souvent sous 50 %)
4. Le graphe de similarité montre deux clusters séparés : méthodes de score vs méthodes de classement

---

### Onglet ⚡ Manipulabilité

**Ce que vous voyez** : pour chaque méthode, la probabilité qu'un électeur puisse changer le résultat en votant "stratégiquement" (en ne votant pas pour son vrai préféré).

**Ce que ça signifie** : un indice de 0 = la méthode est imperméable au vote tactique. Un indice de 1 = presque tous les électeurs peuvent manipuler le résultat.

**Résultat typique** :
- `plurality` : indice élevé (0.4-0.6) — très manipulable, c'est l'effet "vote utile"
- `schulze`, `minimax` : indices plus bas — plus résistants à la manipulation
- `majority_judgment` : l'un des plus résistants théoriquement

---

### Onglet 📊 Vote blanc

**Ce que vous voyez** : comment le vote blanc modifie les résultats selon trois règles constitutionnelles.

**Les trois règles** :
- **Symbolique** : le vote blanc est compté mais n'affecte pas le résultat
- **Compétitif** : le vote blanc est un candidat à part entière — il peut "gagner" et invalider l'élection
- **Seuil 30 %** : si plus de 30 % votent blanc, l'élection est annulée

**Ce qu'il faut regarder** : le graphe "Divergence avant/après vote blanc". Si la barre de divergence est rouge et haute, le vote blanc change radicalement qui gagne selon la méthode utilisée.

**Expérience** : activez le vote blanc (panneau gauche → "Vote blanc" → ON) puis relancez. Comparez avec et sans vote blanc dans cet onglet.

---

### Onglet 📈 Campagne

**Ce que vous voyez** : un graphe "swimlane" montrant qui serait élu par chaque méthode à chaque moment de la campagne.

**Ce que ça signifie** : une élection ne se joue pas en un jour. Cet onglet simule 30 jours de campagne (mouvements aléatoires des intentions de vote) et montre comment le vainqueur potentiel change selon la méthode.

**Ce qu'il faut chercher** :
- Les méthodes **stables** : le même vainqueur tout au long de la campagne (barre uniforme)
- Les méthodes **volatiles** : le vainqueur change plusieurs fois (barre multicolore)
- Souvent, `plurality` est plus volatile que `schulze` ou `borda`

---

### Onglet 🔬 Effets combinés

**Ce que vous voyez** : une matrice 2×2×2 (8 combinaisons) montrant comment les trois modèles (campagne, vote blanc, information) interagissent.

**Comment lire la matrice** : chaque case est une combinaison ON/OFF des trois modèles. Les cases rouges indiquent que cette combinaison réduit fortement l'accord entre méthodes.

**Conclusion typique** : la combinaison "campagne + vote blanc" est souvent la plus déstabilisante — plus déstabilisante que chaque modèle seul.

---

### Onglet 🏛 Coalition

**Ce que vous voyez** : comment les sièges seraient alloués selon D'Hondt (proportionnel), et quelle coalition gouvernementale serait nécessaire.

**L'hémicycle** : la visualisation semi-circulaire classique du parlement. Chaque secteur = un candidat/parti.

**Ce qu'il faut observer** :
- La colonne "Coalition" montre quels candidats deviendraient des alliés naturels (idéologiquement proches)
- L'"Écart idéologique" mesure à quel point la coalition est cohérente — une coalition dispersée est plus fragile
- Changez les méthodes dans le tableau → observez comment la coalition change

**Expérience** : comparez la coalition formée par plurality vs schulze. Avec plurality, un parti peut avoir la majorité seul. Avec proportionnel, la coalition est souvent nécessaire.

---

### Onglet 🗺 Circonscriptions

**Ce que vous voyez** : votre électorat divisé en N circonscriptions géographiques.

**Ce que ça illustre** : au Royaume-Uni, au Canada et aux USA, chaque zone géographique élit son représentant local (FPTP). Résultat : un parti peut obtenir 60 % des sièges avec 40 % des voix nationales.

**Les deux hémicycles côte à côte** :
- **Gauche (FPTP)** : résultat avec circonscriptions
- **Droite (Proportionnel)** : ce que serait le parlement si on comptait les voix nationales

**Badge "Distorsion"** : si +14pts, cela signifie que le vainqueur FPTP obtient 14 points de pourcentage de sièges de plus que sa part de votes.

**Expérience** : augmentez le nombre de circonscriptions à 30, passez l'idéologie en `polarized`. La distorsion explose souvent — c'est l'effet "winner-take-all" amplifié.

---

### Onglet 🗳 Primaires

**Ce que vous voyez** : une simulation en deux tours — d'abord les primaires internes à chaque parti, puis l'élection générale.

**Le phénomène simulé** : les militants qui votent aux primaires sont plus extrémistes que l'électorat général. Résultat : les primaires sélectionnent souvent des candidats plus radicaux que ne le souhaite l'ensemble de l'électorat.

**Ce qu'il faut regarder** :
- **"Distorsion"** sous chaque parti : distance entre le centre idéologique du parti et le candidat sélectionné. Plus la barre est rouge et grande, plus la primaire a produit un candidat extrême.
- **"Sans primaires vs Avec primaires"** : les deux vainqueurs sont-ils différents ? Si oui, le badge rouge "Histoire réécrite" s'allume.

**Expérience** : augmentez le "Facteur de participation primaire" à 0.5 (50 % des électeurs participent à la primaire). Les candidats sélectionnés devraient être plus extrêmes.

---

### Onglet 📺 Replay historique

**Ce que vous voyez** : une reconstitution simulée d'une élection historique réelle, avec la possibilité de "réécrire l'histoire".

**Les 4 scénarios disponibles** :

| Scénario | Ce qui s'est passé | Ce qu'on peut explorer |
|---|---|---|
| 🇫🇷 **France 2002** | Jospin éliminé au 1er tour, Le Pen qualifié | Et si Jospin avait été plus centriste ? |
| 🇺🇸 **USA 1992** | Clinton élu avec 43 % grâce à Perot | Et si Perot s'était retiré ? |
| 🇩🇪 **Allemagne 2021** | Scholz élu de justesse, coalition nécessaire | Et si les Verts avaient été moins à gauche ? |
| 📐 **Cycle Condorcet** | Aucun vainqueur "juste" possible | Comment les méthodes "cassent" le cycle |

**Comment utiliser** :
1. Cliquez sur France 2002
2. Cliquez "▶ Simuler"
3. Utilisez le slider "Jour de campagne" → observez les intentions de vote évoluer
4. **Glissez Jospin** (★ bleu) vers le centre (x=0, y=0)
5. Cliquez "↺ Rejouer avec ces positions"

**Résultat attendu** : en déplaçant Jospin au centre, il devient souvent le vainqueur de la simulation au lieu de Chirac. Le bandeau rouge "⚠ Histoire réécrite" s'affiche avec le message pédagogique expliquant le changement.

---

### Onglet ⚖️ Jury

**Ce que vous voyez** : une simulation du Théorème du Jury de Condorcet (1785).

**L'idée** : si chaque électeur a une probabilité P > 50 % de choisir la "bonne" réponse, alors plus il y a d'électeurs, plus la décision collective est fiable. C'est la base théorique du "sagesse des foules" en démocratie.

**Le graphe "Courbe de compétence"** : montrez comment la précision collective évolue quand P varie de 51 % (presque aléatoire) à 99 % (presque parfait).

**Ce qu'il faut observer** :
- La ligne pointillée rouge = prédiction théorique (formule mathématique)
- Les lignes colorées = résultats des simulations pour chaque méthode
- Les méthodes au-dessus de la ligne théorique "battent" la théorie — elles agrègent mieux l'information collective

**Slider "Compétence individuelle"** : faites-le glisser de 0.51 à 0.99 et observez les courbes se recalculer en temps réel. À P=0.7 avec 100 électeurs, la précision collective dépasse souvent 90 %.

---

### Onglet ⚙ Vote tactique

**Ce que vous voyez** : une simulation de comment les électeurs s'adaptent aux sondages au fil des rounds.

**Le mécanisme** : si mon candidat préféré est à 5 % dans les sondages, je peux décider de voter pour le "moins pire" candidat viable plutôt que de "gaspiller" mon vote. Cet onglet simule ce processus sur plusieurs rounds.

**Le Race Chart** : montrez l'évolution des intentions de vote à chaque round, avec en pointillé ce qu'auraient été les votes sincères.

**Ce qu'il faut chercher** :
- Le **badge "Convergence"** : la simulation se stabilise-t-elle ? Avec Schulze, la convergence est souvent atteinte au round 2-3. Avec Plurality, le résultat peut osciller.
- Le **badge "Dérive idéologique"** ⚠ : si le vainqueur final est idéologiquement plus éloigné de l'électorat médian que le vainqueur sincère, le vote tactique a "dégradé" la qualité démocratique.

**La carte idéologique** : les points plus brillants = électeurs qui ont changé leur vote stratégiquement. Les anneaux pointillés = leur vrai premier choix avant le changement.

---

### Onglet 📉 Abstention

**Ce que vous voyez** : comment l'abstention différentielle peut changer le résultat d'une élection.

**L'idée** : quand mon candidat est loin dans les sondages, je suis moins motivé à aller voter. Ce phénomène s'appelle la "démobilisation". Cet onglet le simule.

**Les deux sliders** :
- **Facteur de démobilisation** : l'intensité de l'effet (0 = personne ne s'abstient, 1 = forte démobilisation)
- **Poids des sondages** : à quel point les électeurs sont influencés par les sondages précédents

**Ce qu'il faut observer** :
- La **carte idéologique** : les points gris = électeurs abstentionnistes. Après le round 3, une zone entière peut devenir grise — le camp du candidat perdant se démobilise.
- Le **graphe "Participation par round"** : quelle ligne descend le plus vite ? Le camp du perdant a toujours une participation qui décline.
- Le **bandeau de comparaison** : si rouge, l'abstention a changé le vainqueur. Si vert, le résultat est le même.

**Résultat typique** : avec un facteur de démobilisation de 0.7 et des sondages influents, l'électorat de Bob peut tomber de 100 % à 60 % de participation, suffisant pour que Alice gagne même si elle avait moins de voix sincères.

---

### Onglet 🔄 STV

**Ce que vous voyez** : le Single Transferable Vote (vote à transfert unique) — le système utilisé en Irlande depuis 1922.

**Comment ça marche (simplifié)** : au lieu de voter pour un seul candidat, vous classez tous les candidats par ordre de préférence. Un quota minimum est calculé (ex : 84 voix sur 500). Dès qu'un candidat atteint ce quota, il est élu et ses votes en surplus sont redistribués à vos 2es choix au prorata.

**L'animation step-by-step** :
- Chaque "round" est une étape : soit un candidat est élu ✓ (vert), soit le dernier est éliminé ✗ (rouge)
- Les barres de progression montrent l'avancement de chaque candidat vers le quota
- Les "+X" verts = votes reçus par transfert ce round

**Les 3 hémicycles** :
- **STV** : résultat avec le système irlandais
- **D'Hondt** : résultat proportionnel pur (comme en Allemagne)
- **FPTP** : résultat avec le système britannique/français à 1 tour

**Ce qu'il faut observer** : les badges de distorsion. Souvent, FPTP donne une distorsion élevée (ex ±2 sièges) tandis que STV et D'Hondt sont proches.

---

### Onglet 🗺 Gerrymandering

**Ce que vous voyez** : un éditeur interactif de frontières de circonscriptions.

**Gerrymandering** (du nom du gouverneur Gerry + salamandre) : dessiner délibérément des frontières électorales pour avantager un parti, même si l'électorat national penche autrement.

**Comment utiliser** :
1. La grille 10×10 représente l'espace idéologique [-1,1]²
2. **Cliquez sur une cellule** → elle change de couleur (change de circonscription)
3. **Glissez** pour peindre plusieurs cellules d'un coup
4. Cliquez **"Simuler"** pour voir le résultat

**Les deux boutons spéciaux** :
- **"Redécoupage équitable"** → divise en bandes horizontales égales (référence neutre)
- **"Gerrymandering optimal"** → regroupe les électeurs adverses dans une seule circo (packing) et dilue les autres (cracking)

**Ce qu'il faut observer** :
- L'**indice de gerrymandering** (barre de 0 % à 100 %) : 0 % = résultat conforme aux voix nationales, 100 % = résultat totalement déconnecté
- Les **deux hémicycles** : "Découpage actuel" vs "Proportionnel" — combien de sièges de différence ?
- Le **message pédagogique** : avec un gerrymandering bien fait, un parti peut obtenir 70 % des sièges avec seulement 42 % des voix

**Expérience mémorable** :
1. Lancez d'abord avec le redécoupage équitable → distorsion ≈ 0
2. Cliquez "Gerrymandering optimal"
3. Simulez → observez la distorsion grimper à 40-60 %
4. Le même électorat, un résultat radicalement différent

---

## Les autres pages de Vote Lab

### 🔬 Comparaison de méthodes (`/simulation/compare`)

L'outil le plus complet pour comparer les méthodes. 14 sous-onglets :
- **Matrice des vainqueurs** : tableau de qui gagne quoi
- **Radar** : 5 axes de qualité (équité, satisfaction, résistance à la manipulation, Condorcet, stabilité)
- **Monte Carlo live** : simulations en streaming
- Et bien d'autres...

**Accès** : menu "Explorer" → "Comparaison"

### 🎯 Quiz (`/quiz`)

20 questions sur la théorie du vote, 3 niveaux de difficulté. Parfait pour tester vos nouvelles connaissances après avoir exploré le Lab.

**Accès** : menu "Apprendre" → "Quiz"

### 🗓 Et si… (`/what-if`)

Choisissez un paramètre (nombre d'électeurs, nombre de candidats, taux de vote blanc, polarisation) et observez comment le résultat évolue quand ce paramètre varie. Les graphes montrent les "points de bascule" — valeurs à partir desquelles le vainqueur change.

**Accès** : menu "Explorer" → "Et si…"

### 📈 Campagne jour par jour (`/campaign`)

Simulez 30 jours de campagne avec des événements (scandale, bon débat, gaffe) qui impactent les intentions de vote. Cliquez sur les événements dans le calendrier pour voir leur effet sur les courbes.

**Accès** : menu "Explorer" → "Campagne"

### 🦠 Contagion sociale (`/blank-contagion`)

Modélise la propagation du vote blanc dans un réseau social (modèle SIS épidémique). Quand un électeur voit ses amis voter blanc, il est tenté de faire pareil — comme une épidémie d'insatisfaction politique.

**Sliders disponibles** : taux de contagion β, taux de "guérison" γ, topologie du réseau (aléatoire, monde petit, clusters).

**Accès** : menu "Explorer" → "Contagion"

---

## Guide de lecture des visualisations

### Les hémicycles (demi-cercles parlementaires)

Chaque secteur coloré représente un candidat/parti. La ligne rouge au milieu = la majorité absolue. Si le secteur d'un candidat dépasse cette ligne, il a la majorité.

### La carte idéologique 2D

- **Axe horizontal** : gauche économique ← · → droite économique
- **Axe vertical** : conservateur ↓ · ↑ progressiste
- **Points colorés** : électeurs (couleur = leur candidat préféré)
- **★ Étoiles** : candidats (draggables)

### Les badges Bayesian Regret

Le régret bayésien mesure à quel point le résultat déçoit l'électorat. Un régret de 0 = le candidat parfait a été élu. Un régret de 0.08 = la méthode "rate" légèrement le meilleur candidat pour l'ensemble de l'électorat.

### Le vainqueur de Condorcet ✓

Marqué en vert quand il existe. C'est le candidat qui battrait chacun des autres en duel direct (1 contre 1). C'est souvent le candidat du centre. Quand il n'existe pas (cycle), c'est le paradoxe d'Arrow.

---

## Parcours suggérés selon votre curiosité

### 🟢 "Je veux comprendre l'essentiel en 15 minutes"
1. Page d'accueil → France 2002 → comparer `plurality` vs `schulze`
2. Election Lab → onglet Résultats → observer le taux d'accord
3. Election Lab → onglet Carte → glisser un candidat vers le centre
4. Election Lab → onglet 📺 Replay → France 2002 → déplacer Jospin au centre

### 🟡 "Je veux comprendre pourquoi on parle de réforme électorale"
1. Comparaison (`/simulation/compare`) → onglet Radar → quel système est le "meilleur" ?
2. Election Lab → onglet 🗺 Circonscriptions → observer la distorsion FPTP
3. Election Lab → onglet 🗺 Gerrymandering → redessinare des frontières
4. Election Lab → onglet 🔄 STV → comparer STV, D'Hondt, FPTP

### 🔴 "Je veux aller au fond du sujet"
1. Election Lab → onglet 🎲 Monte Carlo → 200 simulations, électorat polarisé
2. Election Lab → onglet ⚙ Vote tactique → observer la convergence selon la méthode
3. Election Lab → onglet 📉 Abstention → démobilisation avec facteur 0.8
4. Election Lab → onglet ⚖️ Jury → faire varier la compétence individuelle
5. Comparaison → onglet Manipulabilité → quel système résiste le mieux au vote utile ?

---

## Les grandes conclusions que Vote Lab permet de tirer

1. **La méthode de vote change réellement le vainqueur** — ce n'est pas théorique. Avec le même électorat France 2002, Condorcet et Schulze élisent Jospin là où Plurality élit Chirac.

2. **Plus l'électorat est polarisé, plus les méthodes divergent** — le consensus est fragile quand les camps sont extrêmes.

3. **Le scrutin uninominal (Plurality) est particulièrement vulnérable** au vote utile, à la fragmentation, et au gerrymandering.

4. **Le vainqueur de Condorcet n'existe pas toujours** — parfois les préférences collectives sont cycliques (A bat B, B bat C, C bat A). Aucune méthode ne peut produire un résultat "parfait" dans ce cas (théorème d'Arrow, 1951).

5. **Les primaires déplacent les candidats vers les extrêmes** — les militants sont plus radicaux que l'électorat général, et les primaires le reflètent.

6. **L'abstention différentielle peut renverser des élections** — quand le camp du perdant se démobilise, l'effet est auto-réalisateur.

---

*Vote Lab est un projet personnel de recherche civique. Les simulations sont basées sur des modèles mathématiques académiques (Balinski & Laraki pour le Jugement Majoritaire, Black pour l'électeur médian, Condorcet pour le jury, Droop pour le STV...). Les résultats sont reproductibles avec la même graine aléatoire (seed).*
