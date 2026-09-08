# ADR-006: Un seul instrument Playground à 5 moments, pas une galerie de pages par sujet

**Status**: Adopté, en vigueur
**Date de la décision** : ~2026-06/07, consolidation documentée dans le journal (« 2026-06-10 → 2026-07-30 »)
**Date de rédaction de cet ADR** : 2026-09-08 — reconstruction rétroactive (Lot 0.6 du plan), voir la note en fin de document

## Contexte

L'application est partie d'une collection de dizaines de pages/onglets de
recherche indépendants (jusqu'à un « Election Lab » de 35 onglets fusionnés,
puis absorbant 40 phénomènes en 6 familles). Chaque page montrait sa propre
tranche d'un même sujet — l'électorat, la méthode de vote, la stratégie —
souvent avec son propre état, dupliqué d'une page à l'autre.

## Décision

Consolider en **un seul instrument**, le Playground, structuré en **rail à 5
moments** — Électorat → Méthode → Stratégie → Campagne → Bilan
(`components/playground/moments/*Moment.tsx`) — avec un
**Dirigeant ↔ Assemblée** en bascule plutôt qu'en pages séparées. Tout l'état
et les dérivations vivent dans un contrôleur unique
(`PlaygroundController.tsx`) et circulent par un seul contexte
(`usePlaygroundCtx`) ; les panneaux de moment et l'instrument en sont de
simples consommateurs.

Le contenu avancé/exotique (paradoxes, théorèmes d'impossibilité, réalisme
comportemental, méthodes supplémentaires) n'a pas disparu : il a été
déplacé vers une page séparée, `/laboratoire`, qui **lit le même état
d'électorat** que le Playground via `usePlaygroundCtx` plutôt que de forker
son propre state — configurer dans le Playground, explorer dans le
Laboratoire.

## Alternatives considérées

- **Garder l'Election Lab comme surface parallèle** au nouvel instrument
  Playground, une fois celui-ci construit. Explicitement rejeté — le
  journal cite la raison donnée dans le message du commit de retrait :
  « éviter la duplication de state et les drill-downs circulaires entre deux
  surfaces qui montrent la même donnée ».
- **Un panneau extensible par sujet** (accordéons empilés) plutôt qu'un rail
  séquentiel à moments. Non retenue en pratique : le rail impose un ordre de
  lecture narratif (électorat avant méthode avant stratégie), cohérent avec
  la thèse pédagogique de l'app (« le choix de la méthode change le
  vainqueur ») — un empilement d'accordéons sans ordre imposé ne porte pas
  cette narration.

## Conséquences

- **Règle du « don't denature the playground »** (documentée dans le skill
  `voter-ui`) : une nouvelle méthode de vote s'ajoute comme `Rule` dans
  `lib/playgroundVoting.ts` (elle apparaît alors automatiquement dans la
  carte de zones de victoire, le Scorecard, Pareto) ; un nouvel effet devient
  une **lens** sur la carte centrale, jamais un nouveau tiroir déroulant.
  Le contenu lourd ou exotique va au Laboratoire, pas dans le rail.
- Le Laboratoire et le Playground **partagent un seul état d'électorat** —
  pas de double configuration à maintenir en synchronisation manuelle, au
  prix d'un couplage : une modification de forme de l'état du Playground se
  répercute potentiellement sur toutes les fiches du Laboratoire qui le
  lisent.
- Le rail à 5 moments devient la charpente que toute nouvelle fonctionnalité
  de théorie du vote doit respecter, plutôt qu'un choix révisable
  fonctionnalité par fonctionnalité.

## Note de reconstitution

Cet ADR documente une décision déjà en vigueur dans le code ; il n'a pas été
rédigé au moment où la décision a été prise. Sources : le skill `voter-ui`
(« Don't denature the playground »), `PlaygroundController.tsx`, et
`docs/journal/JOURNAL_DE_BORD.md` (entrée reconstruite « 2026-06-10 →
2026-07-30 », qui cite directement la justification du message de commit de
retrait de l'Election Lab). L'historique git conservé par ce dépôt ne remonte
qu'au 2026-08-29 ; les commits d'origine de cette décision ne sont plus
consultables directement, seule leur trace narrative dans le journal l'est.
