# Candidats à commentaires périmés (généré)

Généré par `scripts/audit_stale_comments.py` — heuristique (a) du Lot 6.1 : `git blame` sur chaque bloc de commentaire vs. la ligne de code qui le suit, seuil de 1 jours d'écart.

**Ceci est une liste de candidats, pas un verdict.** Chaque ligne est à trier manuellement (ou via l'approche (b), passe LLM) dans une des quatre catégories du Lot 6.1 avant toute correction.

4 candidats au-dessus du seuil.

| Fichier | Lignes | Écart (j) | Commentaire touché | Code touché | Aperçu |
|---|---|---|---|---|---|
| `fast_api_voter/api/domain/simulations/advanced.py` | 76-82 | 1 | 2026-09-04 | 2026-09-06 | """ |
| `fast_api_voter/api/tests/test_kemeny_young.py` | 1-5 | 1 | 2026-09-04 | 2026-09-06 | """Unit tests for Kemeny-Young: the exact algorithm (<= 6 candidates) |
| `voter-app/src/components/Simulation/simulationConstants.ts` | 26-26 | 1 | 2026-09-04 | 2026-09-06 | // Fallback labels used in non-React contexts (report HTML, CSV, buildConclusion) |
| `voter-app/src/hooks/useDragTouch.ts` | 1-10 | 1 | 2026-09-04 | 2026-09-06 | /** |
