# ADR-007: Pas de comptes ni d'authentification — l'application est anonyme et sans état

**Status**: Adopté, en vigueur
**Date de la décision** : ~2026-06/07, retrait documenté dans le journal (« 2026-06-10 → 2026-07-30 »)
**Date de rédaction de cet ADR** : 2026-09-08 — reconstruction rétroactive (Lot 0.6 du plan), voir la note en fin de document

## Contexte

Lors de la refonte Flask → FastAPI (~2026-05/06), l'application avait
construit une authentification réelle — `fastapi-users` + OAuth Google/GitHub
— et une couche « communauté » avec des comptes, migrées endpoint par
endpoint comme le reste du backend (journal, entrée « 2026-05-23 →
2026-06-09 »). Dans la phase suivante, cette couche a été **entièrement
retirée**, en même temps qu'un pivot plus large vers un positionnement
d'outil de recherche public plutôt que de plateforme communautaire
(ajout de `/decouvrir`, « À vous de jouer », analytics anonymes).

## Décision

**Aucun compte, aucune authentification, aucune persistance par
utilisateur.** Le backend est stateless (pas de base SQL) ; tous les
endpoints de l'API sont ouverts, protégés uniquement par du rate-limiting
par route (5-120 req/min selon l'endpoint), jamais par une vérification
d'identité.

## Alternatives considérées

- **Conserver la couche OAuth/comptes déjà construite**, pour des
  fonctionnalités comme des scénarios sauvegardés ou une communauté
  d'utilisateurs. Rejetée par retrait effectif. Le journal est honnête sur
  une limite réelle de cette reconstruction : *« pourquoi : non détaillé
  dans les messages de commit au-delà de "backend stateless" ; cohérent
  avec l'orientation outil de recherche public plutôt que plateforme
  communautaire »* — la décision est documentée dans son résultat et sa
  cohérence avec le pivot produit, pas dans un raisonnement contemporain
  explicite.

## Conséquences

- **La documentation doit rester synchronisée avec cette décision** — elle
  ne l'a pas toujours été : la passe de correction de documentation (PR
  #313, 2026-09-06) a dû corriger `SECURITY.md`, qui décrivait encore une
  authentification JWT et des identifiants Postgres n'existant plus dans
  l'app. C'est le type exact de dérive documentaire que le Lot 6.1 du plan
  (audit de pertinence des commentaires) cherche à détecter à l'échelle du
  code, pas seulement des fichiers `.md`.
- Toute fonctionnalité future nécessitant une persistance par utilisateur
  (élections sauvegardées, historique personnel) doit soit rester compatible
  avec l'anonymat (lien partageable, export local plutôt que compte), soit
  **rouvrir explicitement cette décision** — jamais réintroduire une
  authentification partielle en silence.
- Le README documente ce choix comme une caractéristique du produit
  (« The app is anonymous (no accounts) ») et non comme une simple omission
  technique — le distinguo importe pour tout futur contributeur qui se
  demanderait pourquoi ajouter un compte.

## Note de reconstitution

Cet ADR documente une décision déjà en vigueur dans le code ; il n'a pas été
rédigé au moment où la décision a été prise, et le raisonnement original
n'a jamais été pleinement enregistré (le journal le signale lui-même — voir
citation ci-dessus). Sources : `README.md` (§ Stack, § Routes, § Public API),
`docs/journal/JOURNAL_DE_BORD.md` (entrées reconstruites « 2026-05-23 →
2026-06-09 » et « 2026-06-10 → 2026-07-30 »), et PR #313 (correction de
`SECURITY.md`). L'historique git conservé par ce dépôt ne remonte qu'au
2026-08-29 ; les commits d'origine de cette décision ne sont plus
consultables directement, seule leur trace narrative dans le journal l'est.
C'est, des quatre ADR de ce lot, celui dont la reconstitution est la plus
incertaine : le journal lui-même admet ne pas avoir retrouvé le raisonnement
complet derrière le retrait.
