# Prompt — Reconstruction rétroactive du journal de bord

> À utiliser une seule fois, avec Claude Code, à la racine du repo
> Vote-App, après avoir installé `journal-writer.md` (agent) et
> `log-session.md` (commande /log-session). Sert à peupler `docs/journal/JOURNAL_DE_BORD.md` avec
> l'historique du projet avant de passer en mode "au fil de l'eau".

---

Utilise le sub-agent `journal-writer` en **mode reconstruction
rétroactive** pour peupler `docs/journal/JOURNAL_DE_BORD.md` depuis le début du
projet.

Sources à utiliser, dans cet ordre de priorité :

1. **La conversation fournie ci-dessous (ou en pièce jointe)** — elle
   couvre en détail la session du 17-18/08/2026 : bascule GPU d'Ollama,
   quatre bugs distincts découverts et diagnostiqués (context-shift,
   budget de tokens positioning, budget de tokens/dépendance de pipeline
   vote_cast, cache-reuse cross-requête), la découverte puis
   l'explication partielle de la non-reproductibilité (cold-start GPU),
   un spike `llama-server` mené à son terme, et une décision
   d'architecture actée en ADR. Utilise-la comme source principale pour
   cette période — elle contient le raisonnement et les hypothèses
   testées puis écartées, pas seulement l'état final visible dans le
   code.
2. `git log --all --date=short` sur tout l'historique du repo, pour
   dater et regrouper les grandes étapes antérieures (mise en place du
   moteur de vote, ajout des méthodes, début du chantier polity, etc.).
3. Les documents datés déjà présents dans le repo
   (`polity-simulation-design.md`, `audit-precision-plan.md` du
   30/07/2026, les fichiers `*_results.md` sous `scripts/`,
   `docs/adr/ADR-001-serving-layer-ollama-vs-llama-server.md`,
   `THEORY.md`, `traceability.md`) pour situer et détailler les étapes
   correspondantes.

Regroupe par étape logique plutôt que par date stricte quand plusieurs
jours se rapportent au même chantier (ex. une entrée pour "rédaction du
plan de conception + audit de précision", une entrée pour "démarrage du
worktree v0", une entrée pour "bascule GPU, ses quatre bugs et la
décision d'architecture qui en découle").

Pour la période du 17-18/08/2026 (bascule GPU), l'entrée déjà rédigée
dans `docs/journal/JOURNAL_DE_BORD.md` couvre l'ensemble de la séquence connue à
ce jour (bugs 1 à 4, ADR inclus) — sert de référence de niveau de détail
attendu. Complète-la uniquement si la conversation fournie ou l'état du
repo contiennent des développements postérieurs à cette entrée (ex. le
bug 4 finalement résolu, un nouvel acceptance run relancé) ; ne la
duplique pas.

Marque chaque entrée reconstruite avec la mention de traçabilité prévue
dans le sub-agent (`> Entrée reconstruite a posteriori...`).

Présente l'ensemble des entrées proposées, dans l'ordre chronologique,
avant toute application au fichier — je valide avant que quoi que ce
soit soit écrit dans `docs/journal/JOURNAL_DE_BORD.md`.
