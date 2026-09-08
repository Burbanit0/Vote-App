# ADR-004: Two independent voting-rule engines (client + backend), locked identical by a golden-fixture parity test

**Status**: Adopté, en vigueur
**Date de la décision** : 2026-06-27 (introduction du harnais de parité, commit `897d675`)
**Date de rédaction de cet ADR** : 2026-09-08 — reconstruction rétroactive (Lot 0.6 du plan), voir la note en fin de document

## Contexte

Le Playground doit recalculer le résultat d'une élection **instantanément** —
faire glisser un candidat sur la carte idéologique et voir les zones de
victoire se redessiner en direct, sans aller-retour réseau. En parallèle,
l'application affirme que ses 29 méthodes de vote sont correctement
implémentées, ce qui exige un moteur testé rigoureusement (mypy strict,
Hypothesis, suite de non-régression).

Un aller-retour HTTP à chaque frame de glisser-déposer casse l'interaction ;
un moteur purement client, non vérifié avec la même rigueur qu'un moteur
serveur testé, risque de rendre un résultat scientifiquement faux sans que
personne ne le remarque.

## Décision

Maintenir **deux implémentations indépendantes** des règles de vote :

- **Client** (rapide, spatial) : `voter-app/src/lib/playgroundVoting.ts` —
  `ruleWinnerFromRanks(ranks, m, rule, scores?)`.
- **Backend** (autoritaire, testé) :
  `fast_api_voter/api/engine/utils/simulation_ranked_utils.py` +
  `simulation_score_utils.py`.

... et les **verrouiller identiques** par un harnais de parité :
`fast_api_voter/scripts/gen_engine_parity.py` génère des gagnants de
référence sur des profils de vote seedés →
`voter-app/src/lib/__fixtures__/engineParity.json`, vérifié par
`playgroundVoting.parity.test.ts`. 26 méthodes sont verrouillées identiques
(21 ordinales + 5 cardinales) ; `KNOWN_DIVERGENT` est vide.

## Alternatives considérées

- **Un seul moteur côté serveur, le client interroge l'API à chaque
  recalcul.** Rejeté : l'instrument central du Playground (glisser un
  candidat, voir les zones de victoire bouger en direct) dépend d'un calcul
  synchrone côté client ; un aller-retour réseau par frame de glisser-déposer
  rend l'interaction inutilisable.
- **Deux implémentations sans garantie de parité vérifiée** (statu quo avant
  le harnais). Rejeté après coup par les faits, pas par principe : le commit
  d'introduction du harnais (`897d675`, 2026-06-27) verrouille 8 règles et
  fait immédiatement remonter 4 divergences, corrigées le même jour par
  `b3ed2fb` (Bucklin non cumulatif), `d590469` (élimination IRV/Coombs
  incorrecte), `520f6bf` (chemin de Schulze erroné côté backend) et `3f222ad`
  (égalité de départage STAR, en étendant au passage la parité aux méthodes
  cardinales). Deux moteurs sans verrou de parité avaient donc déjà dérivé en
  pratique, pas seulement en théorie.
- **Compiler le moteur Python pour un usage client (WASM/Pyodide)**, ce qui
  aurait évité une double implémentation. Non retenue — aucune trace dans
  l'historique git d'un essai ou d'un rejet argumenté ; à traiter comme une
  alternative non explorée plutôt que délibérément écartée.

## Conséquences

- **Toute modification d'une règle doit toucher les deux côtés** et
  régénérer la fixture (`gen_engine_parity.py`), sous peine de faire échouer
  le test de parité — documenté comme règle bloquante dans `CLAUDE.md` et le
  skill `voter-api`.
- `engineParity.json` est un artefact **généré** : jamais édité à la main,
  y compris pour faire taire un test de parité en échec.
- Le harnais de parité est un **détecteur de bugs réel**, pas seulement une
  garantie sur le papier — il a trouvé 4 divergences dès sa mise en place
  (dont une, IRV/Coombs, avec un vrai bug de chaque côté : tie-break non
  neutre côté client, gaps côté backend, corrigés dans le même commit
  `d590469`). Une divergence de parité doit être traitée comme un bug
  jusqu'à preuve du contraire, jamais comme une fixture à mettre à jour
  pour faire passer le test.
- Le coût accepté est la **double maintenance** : chaque règle de vote existe
  et doit être comprise dans deux langages, deux bases de code. Ce coût est
  jugé inférieur à celui de perdre l'interactivité instantanée du Playground,
  ou à celui d'un moteur client non vérifié.

## Note de reconstitution

Cet ADR documente une décision déjà en vigueur dans le code ; il n'a pas été
rédigé au moment où la décision a été prise. Sources : les 5 commits du
2026-06-27 cités ci-dessus (`897d675`, `b3ed2fb`, `d590469`, `520f6bf`,
`3f222ad`), le harnais lui-même
(`fast_api_voter/scripts/gen_engine_parity.py`, `playgroundVoting.parity.test.ts`),
`CLAUDE.md` (« The dual voting engine — keep it in sync ») et le skill
`voter-api`. Aucune justification contemporaine autre que les messages de
commit eux-mêmes n'a été retrouvée — le raisonnement du « pourquoi deux
moteurs plutôt qu'un » ci-dessus est reconstruit à partir de la contrainte
technique qu'encode le code (interaction instantanée du Playground), pas
d'une note d'architecture écrite au moment de la décision.
