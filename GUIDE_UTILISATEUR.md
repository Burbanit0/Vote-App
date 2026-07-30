# Vote Lab — Guide complet d'utilisation

> **Pour qui ?** Ce guide est destiné à toute personne curieuse de comprendre comment les systèmes électoraux fonctionnent — aucune connaissance préalable requise.
>
> **Accès** : ouvrir `http://localhost:3000` dans votre navigateur (Chrome ou Firefox recommandé).

---

## Qu'est-ce que Vote Lab ?

Vote Lab est un laboratoire interactif qui répond à une question fondamentale et souvent ignorée : **la façon dont on compte les votes change-t-elle qui gagne une élection ?**

La réponse est oui — et c'est fascinant. Avec le même groupe d'électeurs ayant exactement les mêmes préférences, des systèmes de vote différents peuvent élire des candidats complètement différents. Vote Lab vous permet d'explorer cela en temps réel, en déplaçant des candidats sur une carte, en simulant des campagnes, en rejouant le vote blanc sous quatre régimes constitutionnels réels, et bien plus.

**Ce que vous pouvez faire :**
- Comparer 29 méthodes de vote sur la même élection, groupées en 5 familles
- Vivre 14 « histoires » guidées qui font surgir un paradoxe précis sous vos yeux
- Voter vous-même dans une vraie élection à 41 électeurs, sous 5 langages de bulletin différents
- Explorer 62 fiches en profondeur dans le Laboratoire (mécanismes, dynamiques temporelles, théorie, vote blanc…)
- Comparer un même phénomène sur deux électorats différents côte à côte

**Trois destinations, une seule appli** : Vote Lab n'a pas de compte, pas de connexion — juste trois pages accessibles depuis la barre de navigation : **Playground** (l'instrument principal), **Laboratoire** (l'exploration approfondie) et **À vous de jouer** (vous votez vous-même).

---

## Page d'accueil — la thèse en un coup d'œil

**Accès** : `http://localhost:3000`

La page d'accueil tient sur un seul écran. Elle pose la thèse centrale de l'appli — « la règle décide, pas seulement les électeurs » — puis vous laisse choisir votre porte d'entrée.

**Ce que vous y trouvez :**
- Un bandeau tout en haut, pour qui ne connaît qu'un seul mode de scrutin (le sien), qui renvoie vers *Découvrir en 2 minutes* (voir plus bas).
- Un titre + un mini-instrument **live** juste à côté : un aperçu réduit, mais réellement interactif, de ce que fait le Playground.
- Deux boutons : **« Découvrir »** (→ la page d'apprentissage en douceur) et **« Ouvrir l'instrument »** (→ le Playground, avec un scénario France 2002 déjà chargé).
- Une bande des **5 moments** de l'instrument (Électorat → Méthode → Stratégie → Campagne → Bilan), cliquable, qui mène directement au Playground.
- La grille des **14 histoires guidées** — chacune avec son titre et sa phrase d'accroche, qui ouvre le Playground directement sur cette histoire.
- Un pied de page avec les liens vers Découvrir, le Playground, le Laboratoire et son lexique.

---

## Découvrir en 2 minutes (`/decouvrir`)

**Pour qui** : vous ne connaissez qu'un seul mode de scrutin — probablement celui de votre pays — et vous voulez comprendre en douceur pourquoi il y en a d'autres.

**Le fil** : douze amis doivent choisir un seul restaurant parmi Pizza 🍕, Sushi 🍣 et Thaï 🍜 — un exemple minuscule, mais avec de vraies préférences qui divergent.

1. **Point de départ** : vous connaissez déjà une façon de voter (le scrutin uninominal — un nom, un tour).
2. **La rupture** : sur ces mêmes bulletins, changez la règle — passez au deux tours, à l'approbation, à Condorcet — et regardez le gagnant changer sous vos yeux. Le décompte est réellement recalculé par le même moteur que le Playground, ce n'est pas une simple illustration.
3. **La carte** : trois familles de bulletins expliquées en mots simples — classer (`rank`), noter (`score`), cocher (`approve`) — chacune avec son icône.
4. **Passer à l'action** : un bouton vous envoie vers une vraie élection, soit dans le Playground, soit dans « À vous de jouer ».

---

## Le Playground — l'instrument principal

**Accès** : bouton `🎛 Playground` dans la barre de navigation, ou `http://localhost:3000/playground`

C'est un seul instrument, du simple au complexe : vous choisissez la question, puis vous avancez **moment par moment** et lisez les effets en direct sur la carte centrale. Rien ne se cache dans des onglets séparés — tout reste sur le même écran, qui se met à jour en 100-200 ms à chaque réglage.

### Dirigeant ou Assemblée ?

Un bouton en haut à droite bascule entre deux questions : **👑 Dirigeant** (qui gagne, un seul poste — président, maire…) et **🏛 Assemblée** (comment se répartissent les sièges d'un parlement). Les 5 moments et l'électorat restent les mêmes ; seule la question posée à la carte change.

### Les 5 moments

Le rail en haut du Playground avance de gauche à droite :

1. **Électorat** — qui vote, comment il se distribue et se comporte. Choisissez un point de départ (préréglage abstrait ou élection réelle), ajustez le nombre de candidats/électeurs, ou composez un électorat sur mesure à partir de plusieurs « communautés » (blocs) idéologiques. Réglages avancés : 1, 2 ou 3 dimensions idéologiques, la façon dont les préférences sont tirées (spatiale, ou selon des cultures statistiques comme Mallows, l'urne de Pólya ou Plackett-Luce), et la « valence » — une qualité non-idéologique par candidat (compétence, charisme…).
2. **Méthode** — la règle de décompte et la forme du bulletin. Cochez les méthodes à comparer parmi **29 règles**, groupées en 5 familles : **Majoritaires** (scrutin uninominal, deux tours, vote alternatif/IRV, Coombs, anti-pluralité), **Positionnelles** (Borda, Bucklin, Nanson, Baldwin, Dowdall), **Condorcet** (11 méthodes fondées sur les duels par paires — Condorcet, Minimax, Schulze, Ranked Pairs, Kemeny, Black, Raynaud, Benham, River, Smith-IRV, Split Cycle), **Cardinales** (approbation, note/score, STAR, jugement majoritaire, cumulatif, maximin, Nash) et **Autres** (bulletin aléatoire).
3. **Stratégie** — vote utile, vote blanc, manipulation. Choisissez si les électeurs votent sincèrement ou stratégiquement (avec un curseur de compromis/enterrement), réglez un modèle d'abstention, activez le **vote blanc en direct** (intensité + choix du régime constitutionnel, avec verdict affiché immédiatement), et lisez un indice de manipulabilité qui compare la règle active à la pluralité et à l'IRV.
4. **Campagne** — la réaction du vote dans le temps. Une frise temporelle montre comment le vainqueur évoluerait sur 30 jours de campagne à partir de l'électorat courant ; vous pouvez « épingler » un instant précis comme nouveau point de départ partagé par le reste de l'instrument.
5. **Bilan** — le verdict, ce que ça vaut selon vos valeurs. En mode Dirigeant : la méthode change-t-elle le vainqueur ? qui gagne sous quelles règles ? y a-t-il un vainqueur de Condorcet ? — plus un tableau de robustesse dépliable (stabilité, résistance stratégique, efficacité Condorcet) pour les 29 méthodes. En mode Assemblée : la fiche de score de la structure parlementaire choisie.

### Les lentilles de la carte

Au centre, la carte idéologique change de lecture selon la **lentille** active : **Vainqueur** (qui gagne où, par défaut), **Manipulation** (qui a intérêt à mentir sur son vote), **Probabilité** (chances de victoire sous un tirage aléatoire de bulletin) et **Critères** (quels critères théoriques — Condorcet, majorité, monotonie, Pareto… — la règle active respecte ou viole sur cet électorat). Chaque moment propose une lentille par défaut adaptée, mais vous pouvez toujours en choisir une autre.

### Les Histoires — 14 paradoxes racontés en direct

Le bouton **« Histoires »** ouvre un choix de récits guidés : chacun rejoue, scène par scène, un phénomène précis de théorie du vote sur le vrai instrument — jamais une simple image, toujours le moteur réel qui recalcule sous vos yeux.

**En mode Dirigeant (11 histoires) :**

| Histoire | Ce qu'elle montre |
|---|---|
| **L'effet spoiler** | Un troisième candidat qui ne peut pas gagner peut quand même décider du vainqueur. |
| **L'étau du centre** | Le candidat que tout le monde accepte peut être éliminé le premier. |
| **Ça dépend qui compte** | Un même électorat, trois méthodes, trois vainqueurs — lequel est le « vrai » ? |
| **La course au vote utile** | Quand la règle vous pousse à trahir votre favori. |
| **Majorité contre bien-être** | Le mieux placé n'est pas toujours celui qui rendrait le plus service. |
| **Un électorat, plusieurs présidents** | France 2002 : les mêmes bulletins, un vainqueur différent selon la méthode. |
| **La stratégie du clone** | Un candidat peut se faire élire en alignant un allié presque identique — mais pas avec n'importe quelle méthode. |
| **Le vote blanc, quatre destins** | Les mêmes électeurs, le même bulletin — la règle qui compte le blanc décide de tout. |
| **Gagner des voix, perdre l'élection** | Sous le vote alternatif, convaincre de nouveaux électeurs peut, dans certains cas, vous faire perdre. |
| **Le vote à l'envers** | Inversez tous les bulletins : le scrutin majoritaire peut réélire le même vainqueur. |
| **Le soutien de trop** | Au vote par approbation, dire sincèrement du bien d'un second choix peut faire perdre votre favorite. |

**En mode Assemblée (3 histoires) :**

| Histoire | Ce qu'elle montre |
|---|---|
| **Le seuil qui efface** | Une barre à 5 % ne retire pas que des sièges : elle déplace les voix. |
| **Un vote, trois parlements** | Mêmes bulletins, mêmes partis : proportionnelle, uninominal ou mixte ? |
| **Le diviseur décide** | Deux façons d'arrondir la proportionnelle — deux assemblées. |

---

## Le Laboratoire — l'exploration approfondie

**Accès** : bouton `🔬 Laboratoire` dans la barre de navigation, ou `http://localhost:3000/laboratoire`

Le Laboratoire lit le **même électorat** que celui configuré dans le Playground — configurez-le là-bas, explorez-le ici, sans double saisie. Il se présente comme un rail de familles à gauche et un « établi » à droite qui affiche la fiche choisie.

**Les 6 familles, avec le nombre de fiches dans chacune :**

| Famille | Fiches | Ce qu'on y trouve |
|---|---|---|
| **Méthodes** | 3 | Duel de méthodes côte à côte, matrice complète des méthodes, galerie avec analogie « au quotidien » pour chacune |
| **Règles & stratégie** | 6 | Forme du bulletin, sincérité, vulnérabilité stratégique, équilibre, VSE (efficacité du vote), valeurs |
| **Systèmes & mécanismes** | 15 | Jury de Condorcet, démocratie liquide, tirage au sort, délibération, vote de conviction, épistocratie, vote identitaire, coalitions, multi-gagnants, circonscriptions, gerrymandering, STV (vote transférable), complexité du bulletin, animation du décompte, atlas mondial des régimes électoraux |
| **Dynamiques** | 15 | Trajectoires de campagne, mécanismes temporels (primaires, abstention différentielle, contagion du vote blanc…), réalisme comportemental (biais, fatigue électorale, polarisation affective…) |
| **Théorie & analyse** | 19 | Paradoxes, théorèmes d'impossibilité, lexique interactif, analyses approfondies, résultats détaillés |
| **Vote blanc & abstention** | 4 | La fiche vote blanc (voir plus bas), la divergence qu'il crée selon la méthode, le NOTA (« aucun des candidats »), l'abstention différentielle |

Soit **62 fiches** au total.

**Le mode Comparer** : le bouton « Comparer un électorat » ouvre une seconde colonne à côté de la première, affichant **la même fiche** mais lue sur un **second électorat** au choix (les candidats restent fixes, seule la distribution des électeurs change). C'est un vrai « même phénomène, deux électorats » côte à côte, pas deux panneaux sans lien — et ça reste synchronisé si vous changez de fiche en cours de route.

---

## À vous de jouer — vous votez vous-même

**Accès** : bouton `✍️ À vous de jouer` dans la barre de navigation, ou `http://localhost:3000/a-vous-de-jouer`

Ici, vous n'observez plus une simulation : vous **votez réellement**, dans une élection fictive à 4 candidats (Alice, Bruno, Carla, Diane) et 41 autres électeurs.

**Avant de voter** : un écran d'invitation, sans aucune analyse encore visible — un bouton ouvre l'isoloir.

**Dans l'isoloir**, deux volets :
1. **Votre opinion** — un curseur d'affinité (0 à 100) par candidat, qui dérive votre classement sincère en direct.
2. **Le bulletin** — vous choisissez l'un des **5 langages de bulletin** : *Un seul nom* (uninominal), *Un ordre* (classement complet), *Plusieurs noms* (approbation), *Une note* (note de 1 à 5), *Des points* (10 points à répartir). Un aperçu du bulletin papier montre exactement les marques que ce langage laisse. Une posture — sincère, stratégique ou abstention — détermine comment le bulletin se remplit ; le mode stratégique révèle des curseurs tactiques propres à chaque langage.

**Le vote est scellé** une fois déposé : impossible de le modifier sur place, il faut « revoter » pour rouvrir l'isoloir — un choix délibéré pour éviter de tricher avec le résultat.

**Après le vote**, plusieurs sections lisent votre bulletin scellé :
- **Votre poids** — un curseur de 1 à 15 électeurs « comme vous » montre combien de voix suffiraient pour faire basculer le résultat sous la règle active.
- **Où vous situez-vous dans la foule** — un dépouillement à main levée des premiers choix.
- **Comment chaque méthode compterait votre bulletin** — une méthode par langage compatible, chacune avec son propre vainqueur.
- **Le dépouillement, étape par étape** — rien n'est caché, plus une explication du vainqueur et le registre complet des bulletins.
- **Le poids d'une seule voix** — un curseur d'écart (100 à 1 000 000 de voix), mis en regard de la Floride 2000 (537 voix d'écart sur 5 963 110 bulletins) : le pouvoir réel d'une voix dépend de l'écart final, pas de la taille de l'électorat.

---

## Le vote blanc — quatre régimes réels

Le vote blanc n'est pas un « non-choix » unique : la fiche dédiée du Laboratoire (`Vote blanc & abstention` → « Vote blanc — et après ? ») et le contrôle en direct du moment Stratégie du Playground rejouent le **même résultat** sous quatre régimes constitutionnels réels :

- **🇫🇷 Aujourd'hui en France (hors exprimés)** — le blanc est compté et publié depuis 2014, mais retiré des suffrages exprimés : il ne pèse sur aucun seuil, un candidat est toujours élu.
- **⚖️ Si le blanc comptait (réforme)** — hypothèse de réforme : le blanc entre au dénominateur, et la barre de majorité à 50 % devient plus dure à franchir.
- **🇺🇾 Compétitif (Uruguay)** — le blanc est traité comme un candidat à part entière : s'il devance le premier, la candidature est rouverte.
- **🇨🇴 Seuil 50 % (Colombie)** — si le blanc dépasse la moitié des voix, l'élection est annulée et rejouée avec de nouveaux candidats.

Le Laboratoire ajoute aussi un toggle **« Sur mon électorat »** sur cette fiche : au lieu de curseurs abstraits A/B/C, il calcule les parts réelles à partir de l'électorat actuellement configuré dans le Playground.

---

## Guide de lecture des visualisations

### La carte idéologique

- **Axe horizontal** : un pôle idéologique ← · → l'autre (souvent gauche/droite économique)
- **Axe vertical** (en 2D/3D) : un second axe (souvent société/valeurs)
- **Points colorés** : électeurs (couleur = leur candidat préféré selon la règle active)
- **Points/étoiles** : candidats, déplaçables à la souris — le résultat se recalcule après chaque déplacement

### Les hémicycles (demi-cercles parlementaires)

En mode Assemblée, chaque secteur coloré représente un parti. La ligne de majorité absolue permet de voir d'un coup d'œil si un parti la franchit seul.

### Le vainqueur de Condorcet

C'est le candidat qui battrait chacun des autres en duel direct (1 contre 1). Souvent proche du centre de l'électorat. Quand il n'existe pas (les préférences collectives forment un cycle — A bat B, B bat C, C bat A), c'est le paradoxe de Condorcet : aucune méthode ne peut alors produire un résultat que personne ne pourrait contester.

### La lentille Critères

Sur la carte du Playground, la lentille « Critères » teste, pour la règle active et cet électorat précis, si des critères théoriques classiques (Condorcet, majorité, monotonie, symétrie de réversion, Pareto, indépendance aux alternatives non pertinentes…) sont respectés ou violés — testé empiriquement sur l'électorat courant, pas seulement énoncé en théorie.

---

## Parcours suggérés selon votre curiosité

### 🟢 « Je découvre, je veux comprendre l'essentiel en 10 minutes »
1. Page d'accueil → « Découvrir » → la rupture des 12 amis et du restaurant
2. Playground → histoire « Ça dépend qui compte » (Condorcet paradoxe)
3. Playground → moment Bilan → activer 3-4 méthodes → observer si le vainqueur change

### 🟡 « Je veux comprendre pourquoi on parle de réforme électorale »
1. Playground → histoire « Le vote blanc, quatre destins »
2. Laboratoire → famille « Systèmes & mécanismes » → fiche Circonscriptions/Gerrymandering
3. Laboratoire → famille « Systèmes & mécanismes » → fiche STV (vote transférable)
4. Laboratoire → famille « Vote blanc & abstention » → toggle « Sur mon électorat »

### 🔴 « Je veux aller au fond du sujet »
1. Playground → moment Méthode → activer les 29 règles → moment Bilan → tableau de robustesse
2. Playground → histoires « Gagner des voix, perdre l'élection » et « Le vote à l'envers » (paradoxes internes à une seule règle)
3. Laboratoire → famille « Théorie & analyse » → paradoxes et théorèmes d'impossibilité
4. À vous de jouer → votez sous 2-3 langages de bulletin différents, comparez qui gagne à chaque fois

---

## Les grandes conclusions que Vote Lab permet de tirer

1. **La méthode de vote change réellement le vainqueur** — ce n'est pas théorique. Sur un même électorat (France 2002 par exemple), les méthodes ordinales et cardinales peuvent élire des candidats différents de la pluralité.

2. **Plus l'électorat est polarisé, plus les méthodes divergent** — le consensus est fragile quand les camps sont extrêmes.

3. **Le scrutin uninominal (pluralité) est particulièrement vulnérable** au vote utile, à la fragmentation du champ, et au découpage des circonscriptions.

4. **Le vainqueur de Condorcet n'existe pas toujours** — parfois les préférences collectives sont cycliques. Aucune méthode ne peut produire un résultat « parfait » dans ce cas (théorème d'Arrow, 1951).

5. **Presque aucune règle n'est parfaite sur tous les critères à la fois** — gagner des voix peut faire perdre (monotonie), approuver un choix de plus peut coûter son favori (later-no-harm), inverser tous les bulletins peut ne rien changer (symétrie de réversion). Ce ne sont pas des bugs de Vote Lab : ce sont des propriétés mathématiques documentées de chaque règle.

6. **Le vote blanc n'a pas un seul sens** — le même résultat peut être lu comme un mandat clair, une absence de majorité, ou une invalidation totale, selon le régime constitutionnel choisi.

---

*Vote Lab est un projet personnel de recherche civique. Les simulations sont basées sur des modèles mathématiques académiques (Balinski & Laraki pour le jugement majoritaire, Black pour l'électeur médian, Condorcet pour le jury et les duels, Droop pour le STV...). Les résultats sont reproductibles avec la même graine aléatoire (seed).*
