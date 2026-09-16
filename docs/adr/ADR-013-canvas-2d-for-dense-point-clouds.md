# ADR-013: Canvas 2D pour les nuages de points denses, une exception bornée à ADR-005

**Status**: Adopté, en vigueur — accepté par le propriétaire le 2026-09-15, avant la fusion de
`polity-ui` dans `polity` (étape F0 de l'explorateur de runs)
**Date**: 2026-09-15
**Contexte de décision** : la page Polity de la Vote App, qui rejoue un run de simulation tick par
tick. Son plan (backend B1–B4, pages F0–F6, branches `feat/polity-ui-*` vers `polity-ui`) a été
arrêté avec le propriétaire le 2026-09-14.

## Contexte

ADR-005 réserve les visualisations centrales toujours montées au **SVG natif écrit à la main**, et
Recharts aux panneaux d'exploration ouverts à la demande. Ce choix tient pour le Playground : une
carte idéologique porte quelques candidats et, au plus, quelques centaines d'électeurs échantillonnés.

La carte de population de la page Polity n'a pas cette taille :

- **Un point par citoyen.** Les runs du lot p500 comptent 500 citoyens ; le run phare de 30 ans en
  prévoit davantage.
- **Redessinée à chaque tick.** Le lecteur de ticks rejoue un run à plusieurs ticks par seconde, et
  chaque changement de lentille (activité, acte de pression, vote, candidature, parti) recolore tous
  les points.
- **Le document de conception le demande déjà.** `polity-simulation-design-v2.md` §14.6 : « au-delà
  de quelques centaines de points animés, éviter le SVG par nœud — passer par Canvas 2D ou WebGL ».

Un nœud SVG par citoyen, soit 500 éléments `<circle>` recalculés et réattribués à chaque tick, fait
porter au DOM un travail que le navigateur fait mieux dans un seul bitmap. Il alourdit aussi chaque
réconciliation React de la page.

## Décision

**La carte de population de la page Polity dessine ses citoyens dans un `<canvas>` 2D.** C'est la
seule exception à ADR-005, et elle est bornée :

- **Seuls les nuages de points denses passent en Canvas.** Tout ce qui est rare et porteur de sens
  reste en **SVG superposé** au canvas, dans le même repère : les partis, le président, sa promesse
  et sa dérive (un segment), la sélection, les axes et leurs libellés (« Axe latent 1/2 » et les
  enjeux qui y pèsent le plus). Les autres vues de la page (frise institutionnelle, lecteur) restent en
  SVG natif, et les courbes macro en Recharts dans un panneau à la demande, comme ADR-005 le prévoit.
- **Le dessin est une fonction pure.** `lib/polity/mapScene.ts` calcule la scène : positions en
  pixels, couleur et forme de chaque point selon la lentille. `lib/polity/drawScene.ts` la dessine sur
  un contexte 2D reçu en argument. Le composant ne fait que brancher un `ResizeObserver`, le
  `devicePixelRatio` et le redessin quand la scène change, jamais à chaque rendu.
- **Le survol et le clic passent par `d3-delaunay`**, déjà dépendance de la Vote App : le point le
  plus proche du pointeur, sans nœud DOM par citoyen.
- **L'accessibilité ne dépend pas du canvas.**
  - Le canvas porte `role="img"` et un résumé textuel du tick (président, comptes par statut et par
    acte).
  - Une **vue tableau** donne la même information, ligne par citoyen.
  - La sélection se fait **au clavier** : les flèches vont au citoyen le plus proche dans la direction.
  - Chaque code se lit à la **forme en plus de la couleur**, pour les lecteurs daltoniens et
    l'impression.
- **Les tests ne lisent pas les pixels du canvas en unitaire.** Le dessin est testé contre un
  **contexte d'enregistrement** : un faux `CanvasRenderingContext2D` qui consigne les appels, sur
  lequel on vérifie les points dessinés, leurs couleurs et leurs formes pour chaque lentille. Le
  rendu réel est couvert par les **captures de régression visuelle** dans l'image Docker Playwright
  épinglée (EXP-004), où la rastérisation est stable d'un run à l'autre.

## Alternatives considérées

- **SVG natif, un nœud par citoyen**, pour rester entièrement dans ADR-005. Rejeté pour la carte :
  §14.6 l'exclut au-delà de quelques centaines de points animés, et chaque tick joué réécrirait
  plusieurs centaines d'attributs dans le DOM. Retenu pour tout le reste de la page.
- **WebGL (PixiJS, regl ou deck.gl).** Rejeté pour la v1 : une dépendance de plusieurs centaines de
  ko contre un budget de bundle de 1 Mo brotli dont il restait environ 190 ko au moment du plan
  (2026-09-14), et un rendu GPU plus difficile à rendre identique dans l'image Docker des captures.
  Canvas 2D dessine 500 à quelques milliers de disques sans difficulté. À reconsidérer si un run
  dépasse ce que Canvas 2D anime fluidement.
- **Recharts (`ScatterChart`).** Rejeté : Recharts dessine en SVG, un nœud par point. Le problème
  reste entier et on y ajoute le coût de la bibliothèque dans une vue toujours montée, ce qu'ADR-005
  interdit.
- **Tout le dessin dans le composant React**, sans séparer scène et dessin. Rejeté : le dessin
  deviendrait intestable autrement qu'en pixels, et le seuil de couverture sur les lignes modifiées
  (100 %) ne pourrait être tenu que par des captures, lentes et réservées à l'image Docker.

## Conséquences

- **Trois paliers visuels au lieu de deux** : SVG natif pour les vues centrales, Canvas 2D pour les
  nuages de points denses, Recharts pour l'exploration à la demande. Le skill `voter-ui` le documente,
  pour qu'un contributeur ne passe pas une vue ordinaire en Canvas par commodité, ni la carte en SVG
  par réflexe.
- **Pas de nœud DOM par citoyen** : les tests end-to-end ne peuvent pas cibler un citoyen par
  `data-testid` sur la carte. Ils passent par la vue tableau (`data-testid` par ligne) ou par la
  sélection au clavier, et vérifient le résultat dans le panneau de biographie.
- **Un double repère à tenir cohérent** entre le canvas et le SVG superposé. Une seule fonction de
  projection en pixels, dans `mapScene.ts`, sert aux deux ; un test vérifie qu'un point du canvas et
  le marqueur SVG du même citoyen tombent au même endroit.
- **Le coût d'entrée d'une première vue Canvas** dans le code : `ResizeObserver`,
  `devicePixelRatio`, redessin conditionnel, contexte d'enregistrement pour les tests. Il est payé
  une fois, dans la carte de population, et n'est pas reproduit ailleurs sans un nouvel ADR.
