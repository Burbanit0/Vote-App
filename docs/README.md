# Les surfaces de documentation

Vote-App a plusieurs supports qui se chevauchaient mal avant ce document
(Lot 0.1 du [plan de solidité technique](../PLAN_SOLIDITE_TECHNIQUE.md)).
Chacun a un rôle et un rythme distincts — la confusion entre eux, plus qu'un
manque de discipline, est ce qui les faisait dériver.

| Surface | Rôle | Rythme | Existe ? |
|---|---|---|---|
| `docs/journal/JOURNAL_DE_BORD.md` | Chronologie narrative, par session de travail : ce qui a avancé, les blocages, les décisions, les prochaines étapes. | Par session (`/log-session`) | ✅ |
| `docs/exploration/EXP-*.md` | Par expérience/outil essayé : verdict (adopté/rejeté/suspendu) + ce que ça a réellement trouvé et coûté. | Par expérience close (`/log-experiment`) | ✅ (ce lot) |
| `docs/exploration/README.md` | Index de tous les verdicts — le livrable partageable du projet. | Mis à jour à chaque expérience close | ✅ (ce lot) |
| `docs/adr/` | Décisions d'architecture engageantes, avec alternatives écartées. | Rare | ✅ (polity + application — ADR-004 à 007, Lot 0.6) |
| `docs/journal/commits.jsonl` | Trace machine exhaustive, générée — archéologie et alimentation des autres surfaces. | Par commit (auto, worktree polity uniquement — `scripts/git_commit_capture.py` se garde sur le nom du worktree) | ✅ (Lot 0.5, tier 1 ; script générique sur `develop`, activation via `pre-commit install --hook-type post-commit`) |
| `…/flagship_runs/<run>/run/<run>/digest.json` + `digest.jsonl` | Trace machine d'un run de simulation : issue (terminé/crashé/interrompu), ticks atteints, comptage complet des 30 types d'événements par année, impact population. Générée, jamais rédigée. | À **chaque** fin de run, y compris crash et interruption (`api/domain/polity/run_digest.py`, appelé par le runner) | ✅ |
| `…/flagship_runs/<run>/run/<run>/progress.json` | État vivant d'un run en cours : tick complété **et tick en cours**, décisions par type, replis, et un **battement de cœur LLM** (`last_llm_response_at`). C'est la seule surface qui répond à « ce run est-il vivant ? » — lue par `scripts/check_run_liveness.py`, jamais à l'œil nu. | Par tick **et** à chaque réponse LLM (throttlé à 5 s) | ✅ (battement intra-tick ajouté le 2026-09-11, après qu'un run sain a été tué faute de pouvoir répondre à cette question) |
| `…/flagship_runs/<run>/run/<run>/TIMELINE.md` | Le récit lisible d'un run : ce qu'a vécu cette société simulée, et ce que la population a fait. Rédigé à partir du digest, jamais des logs bruts. | Par run terminé (`/log-run` → sub-agent `run-narrator`) ; les runs non racontés sont signalés au démarrage de session | ✅ |
| Mémoire Claude polity | Écueils rechargés d'office à chaque session — le seul support qui empêche *réellement* la répétition. | Par écueil rencontré | ✅ côté polity uniquement — hors périmètre de ce dépôt ; alimentation automatique (Lot 0.5, tier 3) pas encore branchée |
| `CODE_AUDIT.md` (racine) | État de santé daté du code, rejouable. | Par passe de nettoyage | ✅ |

## Comment choisir la bonne surface

- **Je viens de finir une session de travail, je veux qu'on se souvienne de ce
  qui s'est passé** → `/log-session` → `docs/journal/JOURNAL_DE_BORD.md`.
- **J'ai essayé un outil / une méthode et je veux garder trace du verdict**
  → `/log-experiment` → `docs/exploration/EXP-*.md`, indexé dans
  `docs/exploration/README.md`.
- **Une décision structurante a été prise, avec des alternatives écartées, et
  elle doit rester compréhensible dans un an** → un ADR dans `docs/adr/`.
- **Un run de simulation vient de se terminer (ou de mourir) et je veux savoir
  ce qui s'y est passé** → `/log-run` → `TIMELINE.md` à côté du `events.jsonl`
  du run, rédigé depuis son `digest.json`.
- **Je veux savoir où en est la qualité du code, dans l'ensemble** →
  `CODE_AUDIT.md`.

## Ce que ce document n'est pas

Ce n'est pas un journal de plus : il ne raconte rien lui-même, il pointe vers
la bonne surface. S'il faut le mettre à jour à chaque session, c'est le signe
qu'une nouvelle surface a été ajoutée et doit être documentée ici — pas qu'il
doit devenir narratif.
