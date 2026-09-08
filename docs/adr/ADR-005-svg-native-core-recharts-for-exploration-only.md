# ADR-005: SVG natif pour les visualisations centrales toujours montées, Recharts confiné aux panneaux d'exploration à la demande

**Status**: Adopté, en vigueur
**Date de la décision** : non datée précisément dans l'historique disponible — en place au moins depuis la consolidation Playground/Laboratoire (~2026-07, d'après le journal)
**Date de rédaction de cet ADR** : 2026-09-08 — reconstruction rétroactive (Lot 0.6 du plan), voir la note en fin de document

## Contexte

Le Playground est un **instrument**, pas un tableau de bord statique : la
carte idéologique, l'hémicycle, la frise de campagne et le scorecard sont
montés en permanence et doivent réagir instantanément au glisser-déposer
d'un candidat (cf. ADR-004). Recharts est une bibliothèque de graphiques
généraliste, complète mais lourde, pensée pour des visualisations qui se
montent une fois et changent peu, pas pour un rendu ré-exécuté à chaque
frame de drag.

La suite de tests impose une invariant de performance explicite (le
« form-lock ») : au premier rendu du Playground, seuls les interrupteurs
`*-toggle` sont dans le DOM — aucun panneau lourd n'est monté
(`PlaygroundPage.test.tsx`).

## Décision

Deux paliers visuels distincts, documentés dans le skill `voter-ui` :

- **Les canevas centraux sont du SVG natif, écrit à la main** :
  `LeaderCanvas`, `ParliamentCanvas`, `CampaignTimeline`, le scorecard, les
  cartes de zones de victoire. Toute nouvelle visualisation intégrée au
  cœur de l'instrument (sparkline, bande, overlay) suit ce patron plutôt que
  d'introduire Recharts.
- **Recharts est réservé aux panneaux d'exploration derrière un
  `Collapsible`**, jamais dans les canevas centraux toujours montés. Il est
  isolé en **chunk Vite dédié** (`manualChunks` dans `vite.config.ts` :
  `if (id.includes('recharts')) return 'recharts';`) et préchargé une fois,
  paresseusement, via `requestIdleCallback` depuis
  `PlaygroundController.tsx` (commenté dans le code : « Phase 0 perf: warm
  the heavy Recharts vendor chunk after first paint »), plutôt que chargé au
  premier rendu.

## Alternatives considérées

- **Utiliser Recharts partout**, pour un seul système de rendu de graphiques
  à maintenir. Rejeté : monter Recharts dans un canevas toujours actif
  violerait directement l'invariant form-lock testé (rien de lourd au
  premier rendu), et son coût de rendu par frame est incompatible avec le
  glisser-déposer en direct sur la carte idéologique.
- **Écrire tout en SVG natif, y compris les panneaux d'exploration.**
  Non retenue en pratique : les panneaux d'exploration affichent des
  graphiques classiques (courbes, barres, radars) où Recharts apporte de la
  vitesse de développement sans le risque de performance, puisqu'ils ne sont
  jamais montés par défaut.

## Conséquences

- **Deux systèmes de rendu à connaître** selon l'endroit du code — documenté
  explicitement dans le skill `voter-ui` (« Two visual tiers — pick the
  right one ») précisément pour qu'un contributeur ne réintroduise pas
  Recharts dans un canevas central par réflexe.
- Le bundle Recharts reste un chunk séparé, mis en cache long terme par le
  navigateur, jamais téléchargé par une page qui ne l'utilise pas.
- Le coût est un canevas central **écrit et maintenu à la main** : pas
  d'API déclarative de haut niveau, chaque nouvelle visualisation native
  demande plus de code SVG qu'un composant Recharts équivalent — accepté
  pour garder l'instrument central léger et instantané.

## Note de reconstitution

Cet ADR documente une décision déjà en vigueur dans le code ; il n'a pas été
rédigé au moment où la décision a été prise. Sources : le skill `voter-ui`
(section « Two visual tiers » et « The form-lock invariant »),
`voter-app/vite.config.ts` (commentaire sur les `manualChunks`), et
`PlaygroundController.tsx` (commentaire « Phase 0 perf »). Aucun message de
commit explicite justifiant le choix initial n'a été retrouvé dans
l'historique git disponible (qui ne remonte qu'au 2026-08-29) ; la
justification ci-dessus est reconstruite à partir du code et des contraintes
qu'il encode, pas d'une note contemporaine de la décision.
