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
| [001](./EXP-001-audit-commentaires-heuristique-git-blame.md) | Heuristique `git blame` (staleness) | Audit de commentaires (Lot 6.1) | Adopté (comme filtre) | 329/~5 200 blocs présélectionnés (écarts jusqu'à 379j) ; 5 vérifiés à la main, 5/5 vrai décalage temporel mais 0/5 péremption réelle — bon proxy pour « à relire », mauvais pour « c'est faux » | ~1h30 |
| [002](./EXP-002-hook-taskcompleted-recit-run-polity.md) | Hook `TaskCompleted` (vs `SessionStart`) | Automatisation de session — récit automatique d'un run polity | Rejeté (`TaskCompleted`) ; `SessionStart` adopté comme confort | Ne se déclenche pas pour une tâche Bash en arrière-plan (`run_in_background: true`) — vrai négatif confirmé par un témoin `PostToolUse` déclenché dans la même session, pas un artefact de config périmée ; confirmé a posteriori le 11/09 par un run réellement bloqué (0 exception, 0 crash) que seule la jambe Python a su capter | ~30-45 min (sonde, imprécis) dans un chantier de ~4h |
