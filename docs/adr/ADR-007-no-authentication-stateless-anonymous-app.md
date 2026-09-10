# ADR-007: Pas de comptes ni d'authentification — l'application est anonyme et sans état

**Status**: Adopté, en vigueur
**Date de la décision** : 2026-07-06, retrait en deux commits le même jour —
`5077d00` (front) puis `cabf6e8` (back)
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
  d'utilisateurs. Rejetée par retrait effectif, documenté en détail côté
  mécanique : `5077d00` liste les pages supprimées (Login, Register,
  OAuthCallback, Profile, UserProfile, ScenarioGallery, ScenarioBuilder…) et
  `cabf6e8` la pile backend entière retirée (routes auth/oauth/users/gallery/
  scenarios, `fastapi-users`, la couche SQLAlchemy async, le service Postgres
  de `docker-compose`). Aucun des deux messages n'énonce en revanche la
  raison **produit** du retrait (pourquoi basculer d'une plateforme
  communautaire vers un outil de recherche public) — seulement son exécution
  technique. C'est une vraie limite de la reconstitution, pas un historique
  indisponible : les commits ont été retrouvés et lus en entier, ils ne
  contiennent simplement pas ce raisonnement-là.

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
rédigé au moment où la décision a été prise. Sources : les commits `5077d00`
et `cabf6e8` cités ci-dessus (lus en entier, pas seulement leur titre),
`README.md` (§ Stack, § Routes, § Public API), et PR #313 (correction de
`SECURITY.md`, qui décrivait encore une authentification JWT n'existant plus
dans l'app depuis ce retrait). C'est, des quatre ADR de ce lot, celui dont la
reconstitution reste la plus incertaine — non pas faute d'avoir retrouvé les
commits, mais parce qu'ils documentent en détail *ce qui* a été retiré et
*comment* la suppression a été vérifiée (99 routes au boot, 374 tests
backend verts, `tsc` propre), sans jamais énoncer *pourquoi* le produit a
basculé d'une plateforme communautaire vers un outil de recherche public. Ce
raisonnement produit, s'il a existé, n'est pas dans l'historique git — c'est
une limite réelle, pas un historique tronqué.
