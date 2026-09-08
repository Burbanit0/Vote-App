# ADR-004: Two independent voting-rule engines (client + backend), locked identical by a golden-fixture parity test

**Status**: Adopté, en vigueur
**Date de la décision** : ~2026-06/07 (introduction du harnais de parité, d'après le journal — la plage exacte de commits n'est plus dans l'historique conservé par ce dépôt)
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
  le harnais). Rejeté après coup par les faits, pas par principe : le journal
  de bord documente que la mise en place du harnais de parité **a mis au jour
  4 bugs réels côté backend** (Bucklin non cumulatif, élimination IRV/Coombs
  incorrecte, chemin de Schulze erroné, égalité de départage STAR) **et 1
  défaut côté client**, tous corrigés à l'introduction du harnais. Deux
  moteurs sans verrou de parité avaient donc déjà dérivé en pratique, pas
  seulement en théorie.
- **Compiler le moteur Python pour un usage client (WASM/Pyodide)**, ce qui
  aurait évité une double implémentation. Non retenue — aucune trace dans
  l'historique disponible d'un essai ou d'un rejet argumenté ; à traiter
  comme une alternative non explorée plutôt que délibérément écartée.

## Conséquences

- **Toute modification d'une règle doit toucher les deux côtés** et
  régénérer la fixture (`gen_engine_parity.py`), sous peine de faire échouer
  le test de parité — documenté comme règle bloquante dans `CLAUDE.md` et le
  skill `voter-api`.
- `engineParity.json` est un artefact **généré** : jamais édité à la main,
  y compris pour faire taire un test de parité en échec.
- Le harnais de parité est un **détecteur de bugs réel**, pas seulement une
  garantie sur le papier — il a déjà trouvé 5 bugs à sa mise en place. Une
  divergence de parité doit être traitée comme un bug jusqu'à preuve du
  contraire, jamais comme une fixture à mettre à jour pour faire passer le
  test.
- Le coût accepté est la **double maintenance** : chaque règle de vote existe
  et doit être comprise dans deux langages, deux bases de code. Ce coût est
  jugé inférieur à celui de perdre l'interactivité instantanée du Playground,
  ou à celui d'un moteur client non vérifié.

## Note de reconstitution

Cet ADR documente une décision déjà en vigueur dans le code ; il n'a pas été
rédigé au moment où la décision a été prise. Sources : le harnais lui-même
(`fast_api_voter/scripts/gen_engine_parity.py`, `playgroundVoting.parity.test.ts`),
`CLAUDE.md` (« The dual voting engine — keep it in sync »), le skill
`voter-api`, et `docs/journal/JOURNAL_DE_BORD.md` (entrée reconstruite
« 2026-06-10 → 2026-07-30 », qui cite les 5 bugs trouvés par le harnais).
L'historique git conservé par ce dépôt ne remonte qu'au 2026-08-29 ; les
commits d'origine de cette décision (antérieurs) ne sont plus consultables
directement, seule leur trace narrative dans le journal l'est.
