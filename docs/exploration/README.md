# Index des verdicts

Le livrable partageable de l'exploration outillage/pratiques du
[plan de solidité technique](../../PLAN_SOLIDITE_TECHNIQUE.md) (Lot 0.3) :
« j'ai essayé ~25 outils de qualité sur un vrai projet, voilà lesquels ont
trouvé quelque chose ». Un rejet argumenté vaut autant qu'une adoption —
souvent plus, parce que personne ne publie ses rejets.

Une entrée par expérience close, gabarit dans [`TEMPLATE.md`](./TEMPLATE.md),
rédigée via `/log-experiment`.

| EXP | Outil | Domaine | Verdict | Trouvailles réelles | Coût |
|---|---|---|---|---|---|
| [001](./EXP-001-audit-commentaires-heuristique-git-blame.md) | Heuristique `git blame` (staleness) | Audit de commentaires (Lot 6.1) | Suspendu | 4/5 257 candidats flagués, les 4 des faux positifs (dépôt trop jeune pour que le signal existe) | ~1h |
