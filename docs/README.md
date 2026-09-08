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
| `docs/adr/` | Décisions d'architecture engageantes, avec alternatives écartées. | Rare | ✅ (polity seulement pour l'instant — Lot 0.6 l'ouvre à l'app) |
| `docs/journal/commits.jsonl` | Trace machine exhaustive, générée — archéologie et alimentation des autres surfaces. | Par commit (auto, worktree polity) | ❌ (Lot 0.5, dépend d'infrastructure spécifique au worktree `Vote-App-polity`, non disponible dans ce dépôt) |
| Mémoire Claude polity | Écueils rechargés d'office à chaque session — le seul support qui empêche *réellement* la répétition. | Par écueil rencontré | ✅ côté polity uniquement — hors périmètre de ce dépôt |
| `CODE_AUDIT.md` (racine) | État de santé daté du code, rejouable. | Par passe de nettoyage | ✅ |

## Comment choisir la bonne surface

- **Je viens de finir une session de travail, je veux qu'on se souvienne de ce
  qui s'est passé** → `/log-session` → `docs/journal/JOURNAL_DE_BORD.md`.
- **J'ai essayé un outil / une méthode et je veux garder trace du verdict**
  → `/log-experiment` → `docs/exploration/EXP-*.md`, indexé dans
  `docs/exploration/README.md`.
- **Une décision structurante a été prise, avec des alternatives écartées, et
  elle doit rester compréhensible dans un an** → un ADR dans `docs/adr/`.
- **Je veux savoir où en est la qualité du code, dans l'ensemble** →
  `CODE_AUDIT.md`.

## Ce que ce document n'est pas

Ce n'est pas un journal de plus : il ne raconte rien lui-même, il pointe vers
la bonne surface. S'il faut le mettre à jour à chaque session, c'est le signe
qu'une nouvelle surface a été ajoutée et doit être documentée ici — pas qu'il
doit devenir narratif.
