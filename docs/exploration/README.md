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
| [008](./EXP-008-hook-taskcompleted-recit-run-polity.md) | Hook `TaskCompleted` (vs `SessionStart`) | Automatisation de session — récit automatique d'un run polity | Rejeté (`TaskCompleted`) ; `SessionStart` adopté comme confort | Ne se déclenche pas pour une tâche Bash en arrière-plan (`run_in_background: true`) — vrai négatif confirmé par un témoin `PostToolUse` déclenché dans la même session, pas un artefact de config périmée ; jambe Python validée en réel le 11/09 par un SIGTERM opérateur non planifié (digest correct), cas qu'un `TaskCompleted` ne couvre pas | ~30-45 min (sonde, imprécis) dans un chantier de ~4h |

> **Numérotation partagée entre branches.** Cet index est le livrable commun ;
> les numéros EXP sont globaux, pas par branche. `develop` porte EXP-002 à
> EXP-007 (z3, couverture runtime e2e, régression visuelle, form-lock/bundle,
> pytest-benchmark, Locust) qui ne sont pas encore visibles depuis le worktree
> polity. EXP-008 a été numéroté en conséquence — il a d'abord été écrit
> « EXP-002 » le 2026-09-11, ce qui entrait en collision avec le z3 de
> `develop` ; corrigé le jour même. **Avant d'ouvrir un EXP depuis polity,
> vérifier le dernier numéro sur `develop` :**
> `git ls-tree --name-only origin/develop docs/exploration/`
