---
name: project-polity-portable-workspace-ubuntu
description: "Le contexte de travail (doc de conception, .claude/, mémoire) est versionné depuis 2026-09-04 pour reprendre polity sous Ubuntu; docs/claude-memory/ doit être resynchronisé"
metadata: 
  node_type: memory
  type: project
  originSessionId: 3a861f4b-2769-4ed4-8e06-4c320033190a
  modified: 2026-09-05T01:18:00.807Z
---

Depuis le 2026-09-04, le projet se poursuit aussi depuis Ubuntu. La branche
`chore/portable-workspace-ubuntu` (commits 7e71619 + d25d277, basée sur
`fix/polity-pressure-action-quality-investigation`) a fait entrer dans git ce
qui n'existait que sur la machine Windows : `polity-simulation-design-v2.md` et
ses quatre voisins, `.claude/agents/` + `.claude/commands/`, et
`docs/claude-memory/` — une copie de ce répertoire de mémoire.

**Why:** le doc de conception est cité par numéro de section (§3.4, §5, §8,
§6bis.3) partout dans le code, les ADR et le journal ; hors du dépôt, toutes
ces références pointaient vers un fichier introuvable sur toute machine sauf
une. Même raisonnement que celui qui avait déjà fait versionner `docs/adr/` et
`docs/journal/`.

**How to apply:** `docs/claude-memory/` est un **instantané**, pas la source.
Après une session qui écrit ou corrige un souvenir ici, resynchroniser avant de
committer :
`cp ~/.claude/projects/<slug>/memory/*.md docs/claude-memory/` (sans écraser son
`README.md`, qui explique la restauration et n'appartient pas à `memory/`).
Restent volontairement ignorés : `acceptance_*_runs/` et
`llm_test_harness/data/` (45 Mo de runs bruts, les `*_results.md` narrés sont
commités à leur place), `settings.local.json`, les caches.

Piège Linux rencontré au passage : un `pip freeze >` sous PowerShell avait
réécrit `fast_api_voter/requirements.txt` en UTF-16 LE + CRLF, illisible pour
`pip install -r` et vu comme un binaire par git (donc aucun diff pour le
signaler). Restauré, et `requirements*.txt text eol=lf` ajouté à
`.gitattributes`. Sous PowerShell, écrire avec `Out-File -Encoding utf8`, jamais
la redirection `>` nue.

Voir [[project-polity-branch-workflow]] pour la base de PR (`polity`) et
[[project-polity-pressure-action-collapse-investigation]] pour le travail en
cours embarqué dans le commit `wip`.
