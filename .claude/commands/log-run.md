---
description: Rédige le récit d'un run de simulation (TIMELINE.md, à côté de events.jsonl) à partir de son digest.json
---

Utilise le sub-agent `run-narrator` pour :

1. Repérer le run à raconter : soit celui nommé par l'utilisateur, soit ceux
   signalés au démarrage de session (un `digest.json` sans `TIMELINE.md`, ou
   plus récent que lui) sous `fast_api_voter/scripts/flagship_runs/*/run/*/`.
2. Lire son `digest.json` en entier, et `digest.jsonl` si le run a été
   interrompu puis repris — chaque tentative fait partie de l'histoire.
3. Établir l'arc (mandats, chronologie institutionnelle, impact population)
   avant de rédiger, puis écrire le récit selon le gabarit du sub-agent.
4. Ne rien appliquer directement : présenter le `TIMELINE.md` proposé pour
   validation.
5. Une fois validé, l'écrire à côté du `events.jsonl` du run et confirmer le
   commit à faire.
