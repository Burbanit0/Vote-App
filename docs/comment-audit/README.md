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

## Constat de la passe #1 (2026-09-08)

**5 257 paires (commentaire, ligne de code suivante) scrutées ; 4 dépassent un
écart d'un jour ; les 4 sont des faux positifs.** Dans chaque cas, la ligne de
code juste après le commentaire a été retouchée deux jours plus tard pour une
raison sans rapport avec ce que dit le commentaire (le plus souvent : un ajout
d'import qui reformate la ligne d'`import`/de déclaration juste en dessous),
et le commentaire reste exact. Vérifié à la main pour les 4 :

| Fichier | Commentaire | Ce qui a réellement changé 2 jours après |
|---|---|---|
| `fast_api_voter/api/domain/simulations/advanced.py:76` | docstring de `_monte_carlo_worker` | ligne suivante retouchée sans lien avec le docstring |
| `fast_api_voter/api/tests/test_kemeny_young.py:1` | docstring décrivant l'algorithme Kemeny-Young | l'import a gagné `kemeny_used_approximation` (commit `f2ae5ce`, correctif de race condition) — Kemeny-Young lui-même n'a pas bougé, le docstring reste juste |
| `voter-app/src/components/Simulation/simulationConstants.ts:26` | commentaire sur `METHOD_LABELS` | la déclaration `const` juste en dessous a été retouchée, le commentaire reste juste |
| `voter-app/src/hooks/useDragTouch.ts:1` | docstring JSDoc du hook | la ligne d'import a gagné `KeyboardEvent`, le docstring reste juste |

**Pourquoi le rendement est quasi nul** : `fast_api_voter/api` et
`voter-app/src` sont jeunes de quelques jours (la migration strangler-fig
s'est terminée le 2026-09-04) et la plupart des fichiers n'ont qu'un seul
commit qui touche l'essentiel de leurs lignes. Un commentaire n'a
structurellement pas encore eu le temps de dater par rapport au code qu'il
surplombe — l'écart temporel entre les deux est le mauvais signal *à ce
stade* du projet, indépendamment de la qualité de l'implémentation.

## Verdict de la phase 1

**L'heuristique (a) n'est pas rejetée, mais elle est prématurée** sur ce
dépôt : à réévaluer une fois que `git log` aura plus de mois derrière lui (cf.
le seuil par défaut du script, documenté dans son en-tête). Pour l'instant,
elle ne peut pas servir de méthode de détection primaire.

**Conséquence pour la suite** : la phase 2 de cet item doit s'appuyer sur
l'approche (b) — une passe sémantique (LLM ou revue manuelle) sur les blocs
`(commentaire, code)`, qui ne dépend pas de l'âge du dépôt et peut détecter
un commentaire redondant, archéologique ou déjà faux dès sa première version.
Le contraste entre les deux approches, tel que mesuré ici, est lui-même le
contenu prévu par le plan pour le futur carnet d'expérience (`docs/exploration/`,
Lot 0.2 — pas encore créé au moment de cette passe).
