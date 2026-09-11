# Audit de pertinence des commentaires — Lot 6.1

Phase 1 de l'item [6.1 du plan](../../PLAN_SOLIDITE_TECHNIQUE.md#61--audit-de-pertinence-des-commentaires--l--%E2%AD%90%E2%AD%90-%F0%9F%93%9D%F0%9F%93%9D%F0%9F%93%9D) :
construire et faire tourner l'approche (a) proposée par le plan (heuristique
`git log`), pour voir ce qu'elle trouve avant d'investir dans l'approche (b)
(passe LLM).

## Outil

`scripts/audit_stale_comments.py` — pour chaque bloc de commentaire/docstring
(`#`, `//`, `/* */`, docstrings Python autonomes) sous `fast_api_voter/api` et
`voter-app/src`, compare sa date `git blame` à celle de la ligne de code qui le
suit immédiatement. Un écart significatif suggère que le code a bougé sans que
le commentaire ne suive.

```bash
python scripts/audit_stale_comments.py                       # écrit candidates.md
python scripts/audit_stale_comments.py --threshold-days 90    # seuil plus large
```

Sortie : [`candidates.md`](./candidates.md), régénéré à chaque exécution — ne
pas l'éditer à la main.

## Constat de la passe #1 (2026-09-08, corrigée)

Une première exécution de ce script avait donné un résultat trompeur : « 5 257
paires scrutées, seulement 4 au-dessus du seuil ». Ce chiffre venait d'un
clone git avec un historique tronqué (fetch peu profond) — pas d'une propriété
réelle du dépôt. Avec l'historique complet (1 553 commits sur `develop`,
remontant à 2025-03-01), le même script sur le même commit donne un résultat
très différent :

**329 candidats au-dessus du seuil d'un jour**, avec des écarts réels allant
jusqu'à **379 jours** (`fast_api_voter/api/engine/population_simulation.py`,
comment de 2025-06-03 vs. code touché en 2026-06-17). Le signal temporel
existe bel et bien sur ce dépôt — la conclusion « dépôt trop jeune » de la
passe précédente était un artefact d'environnement, pas un constat.

**5 candidats vérifiés à la main**, en couvrant le haut du classement (plus
gros écarts) et un échantillon au milieu :

| Fichier | Écart | Commentaire | Ce qui a réellement changé |
|---|---|---|---|
| `fast_api_voter/api/engine/population_simulation.py:9` | 379 j | Bannière décrivant le fichier (« simulation d'une population sur une grille ») | Reformatage/ligne vide voisine — le commentaire reste exact |
| `fast_api_voter/api/engine/utils/simulation_score_utils.py:346` | 219 j | `# Calculate utilities (normalized scores)` | La ligne suivante a gagné une annotation de type stricte (`defaultdict[Any, list[Any]]`, passe mypy de 2026-06-17) — le commentaire reste exact |
| `voter-app/src/types.ts:1` | 253 j | `// src/types.ts` | Rien de sémantique — commentaire auto-référentiel, jamais faux, candidat plutôt à la catégorie « redondant » du Lot 6.1 qu'à « périmé » |
| `fast_api_voter/api/engine/utils/simulation_ranked_utils.py:540` | 174 j | Docstring de `get_minimax_winner` | Fonction inchangée depuis ; écart dû à une passe de typage voisine plus tardive dans le fichier — le commentaire reste exact |
| `fast_api_voter/api/domain/election/__init__.py:164` | 23 j | `# ── Perturber endpoints (Phase 3 batch 4) ──` | Marqueur de section toujours exact, code du bloc suivant retouché pour une raison indépendante |

**5/5 vérifiés sont de vrais négatifs sur la péremption** : dans chaque cas,
c'est le **code** qui a bougé pour une raison sans rapport (annotation de
type, reformatage, passe de linting) pendant que le commentaire au-dessus
restait sémantiquement exact — jamais l'inverse. Un seul (`types.ts:1`) est
un candidat valable, mais pour la catégorie « redondant », pas « périmé ».

## Verdict de la phase 1

**L'heuristique (a) fonctionne** — corrigée du problème d'historique, elle
détecte un vrai décalage temporel, à une échelle exploitable (329 candidats
sur ~5 200 blocs scrutés, soit ~6 %). Mais sur cet échantillon vérifié, elle a
une **précision faible pour la péremption réelle** (0/5) : le décalage
temporel capture surtout du **code qui bouge sans rapport avec le commentaire
voisin** (durcissement de types, reformatage), pas des commentaires qui
mentent sur ce que fait le code.

**Enseignement transférable** : l'écart temporel `git blame` est un bon proxy
pour « ce commentaire mérite d'être relu », un mauvais proxy pour « ce
commentaire est faux ». Il présélectionne efficacement (329 candidats à
examiner plutôt que ~5 200 blocs), mais le tri final entre périmé / redondant
/ archéologique / toujours-valide (les quatre catégories du Lot 6.1) exige de
lire le contenu du commentaire et du code, pas seulement leurs dates —
l'approche (a) et l'approche (b) sont donc **complémentaires**, pas
concurrentes : (a) réduit l'espace de recherche, (b) tranche.

**Conséquence pour la suite** : la phase 2 applique l'approche (b) — une
passe sémantique (LLM ou revue manuelle) — sur les 329 candidats déjà
présélectionnés par (a), plutôt que sur l'ensemble des blocs de commentaire du
dépôt.

## Phase 2 (2026-09-10) — passe sémantique, verdict final

Exécutée par 6 agents en parallèle (un par tranche de ~55 candidats), chacun
lisant le commentaire **et** le code environnant — jamais la seule date —
avant de trancher, et vérifiant activement toute affirmation factuelle
(compter un nombre annoncé, grep une fonction citée, relire une formule
décrite) plutôt que de juger sur plausibilité.

| Catégorie | Nombre | Traitement |
|---|---|---|
| **Périmé** | 15 | Corrigé |
| **Redondant** | 59 | Supprimé |
| **Archéologique** | 0 | — |
| **Pourquoi** (non négociable) | 45 | Gardé |
| **Toujours-valide** (vrai négatif) | 210 | Aucune action |

**Verdict** : sur les 329 candidats présélectionnés par la phase 1, 4,6 %
(15) étaient effectivement faux — confirmant le diagnostic de la phase 1 que
l'écart temporel `git blame` est surtout du bruit (code qui bouge sans
rapport avec le commentaire voisin). Le motif dominant des 15 Périmé n'est
pas l'usure isolée mais la **migration non nettoyée** : un tiers d'entre eux
évoquaient encore Flask (retiré, cf. `CLAUDE.md`) ou Jest (jamais utilisé,
le projet tourne sous Vitest) comme des contraintes actuelles. Le reste
étaient des erreurs factuelles ponctuelles indépendantes (formule mal
décrite, décompte périmé, référence à un composant supprimé). Zéro
« archéologique » — ce dépôt ne laisse pas de récit de session dans son code
source, cohérent avec le carnet d'expérience séparé (Lot 0.2).

74 commentaires corrigés ou supprimés, sur 44 fichiers (11 backend,
33 frontend) ; `ruff`/`mypy`/pytest et `tsc`/`vitest`/`eslint` verts après
coup. Détail complet dans [PLAN_SOLIDITE_TECHNIQUE.md §6.1](
../../PLAN_SOLIDITE_TECHNIQUE.md#61--audit-de-pertinence-des-commentaires--l--%E2%AD%90%E2%AD%90-%F0%9F%93%9D%F0%9F%93%9D%F0%9F%93%9D)
et dans l'historique de la PR qui a appliqué ces changements.
