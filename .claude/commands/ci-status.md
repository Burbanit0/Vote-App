---
description: État CI du tip de polity (chaque workflow), puis diagnostic des échecs
---

1. Lance `python3 .claude/hooks/session_ci_status.py --verbose` et montre le résultat tel quel.
2. Si un workflow est en échec, applique le skill `voter-ci` (section « Diagnosing a real CI failure ») : lis le vrai log du job en échec, jamais le seul nom du job, et dis si l'échec vient du code, d'un test instable, d'une advisory (base de données qui bouge sans changement de code) ou de l'infrastructure.
3. Termine par la correction proposée. Ne relance jamais un job « pour voir » sans avoir établi la cause.
4. Pour un diagnostic complet d'un échec, `/ci-doctor <run|PR|branche>`. Historique, groupes d'échecs et tests instables : le tableau de bord CI (https://burbanit0.github.io/Vote-App/, données sur la branche `ci-data`).
