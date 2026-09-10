# Candidats à commentaires périmés (généré)

Généré par `scripts/audit_stale_comments.py` — heuristique (a) du Lot 6.1 : `git blame` sur chaque bloc de commentaire vs. la ligne de code qui le suit, seuil de 1 jours d'écart.

**Ceci est une liste de candidats, pas un verdict.** Chaque ligne est à trier manuellement (ou via l'approche (b), passe LLM) dans une des quatre catégories du Lot 6.1 avant toute correction.

329 candidats au-dessus du seuil.

| Fichier | Lignes | Écart (j) | Commentaire touché | Code touché | Aperçu |
|---|---|---|---|---|---|
| `fast_api_voter/api/engine/population_simulation.py` | 5-9 | 379 | 2025-06-03 | 2026-06-17 | ###################################################################### |
| `fast_api_voter/api/engine/utils/simulation_score_utils.py` | 288-291 | 286 | 2025-11-10 | 2026-08-24 | """ |
| `voter-app/src/types.ts` | 1-1 | 253 | 2025-03-01 | 2025-11-10 | // src/types.ts |
| `fast_api_voter/api/engine/utils/simul.py` | 97-97 | 219 | 2025-11-10 | 2026-06-18 | # Tally votes |
| `fast_api_voter/api/engine/utils/simul.py` | 193-193 | 219 | 2025-11-10 | 2026-06-18 | # Calculate average score per candidate |
| `fast_api_voter/api/engine/utils/simulation_score_utils.py` | 8-10 | 219 | 2025-11-10 | 2026-06-18 | """ |
| `fast_api_voter/api/engine/utils/simulation_score_utils.py` | 37-40 | 219 | 2025-11-10 | 2026-06-18 | """ |
| `fast_api_voter/api/engine/utils/simulation_score_utils.py` | 174-176 | 219 | 2025-11-10 | 2026-06-18 | """ |
| `fast_api_voter/api/engine/utils/simulation_score_utils.py` | 199-201 | 219 | 2025-11-10 | 2026-06-18 | """ |
| `fast_api_voter/api/engine/utils/simulation_score_utils.py` | 240-242 | 219 | 2025-11-10 | 2026-06-18 | """ |
| `fast_api_voter/api/engine/utils/simulation_score_utils.py` | 338-340 | 219 | 2025-11-10 | 2026-06-18 | """ |
| `fast_api_voter/api/engine/utils/simulation_score_utils.py` | 346-346 | 219 | 2025-11-10 | 2026-06-18 | # Calculate utilities (normalized scores) |
| `fast_api_voter/api/engine/utils/simulation_voting_utils.py` | 411-411 | 185 | 2025-11-10 | 2026-05-15 | # --- 2. Utility Calculation --- |
| `fast_api_voter/api/engine/utils/simulation_ranked_utils.py` | 23-31 | 174 | 2025-11-10 | 2026-05-03 | """ |
| `fast_api_voter/api/engine/utils/simulation_ranked_utils.py` | 61-65 | 174 | 2025-11-10 | 2026-05-03 | """ |
| `fast_api_voter/api/engine/utils/simulation_ranked_utils.py` | 101-105 | 174 | 2025-11-10 | 2026-05-03 | """ |
| `fast_api_voter/api/engine/utils/simulation_ranked_utils.py` | 200-204 | 174 | 2025-11-10 | 2026-05-03 | """ |
| `fast_api_voter/api/engine/utils/simulation_ranked_utils.py` | 306-310 | 174 | 2025-11-10 | 2026-05-03 | """ |
| `fast_api_voter/api/engine/utils/simulation_ranked_utils.py` | 348-352 | 174 | 2025-11-10 | 2026-05-03 | """ |
| `fast_api_voter/api/engine/utils/simulation_ranked_utils.py` | 540-544 | 174 | 2025-11-10 | 2026-05-03 | """ |
| `fast_api_voter/api/engine/utils/simulation_ranked_utils.py` | 576-580 | 174 | 2025-11-10 | 2026-05-03 | """ |
| `fast_api_voter/api/engine/utils/simulation_voting_utils.py` | 209-209 | 174 | 2025-11-10 | 2026-05-03 | # --- 1. Generate Voters and Candidates --- |
| `voter-app/src/components/Chart/BarChart.tsx` | 13-13 | 172 | 2025-05-31 | 2025-11-20 | // Clear previous rendering |
| `voter-app/src/components/Chart/Heatmap.tsx` | 36-36 | 172 | 2025-05-31 | 2025-11-20 | // Color scale |
| `voter-app/src/components/Simulation/simulationConstants.ts` | 26-26 | 117 | 2026-05-11 | 2026-09-06 | // Fallback labels used in non-React contexts (report HTML, CSV, buildConclusion) |
| `voter-app/src/types.ts` | 101-101 | 112 | 2026-05-03 | 2026-08-24 | // --- Sensitivity analysis --- |
| `voter-app/src/types.ts` | 117-117 | 112 | 2026-05-03 | 2026-08-24 | // --- Condorcet matrix --- |
| `voter-app/src/types.ts` | 292-292 | 112 | 2026-05-03 | 2026-08-24 | // --- Simulation comparison --- |
| `voter-app/src/hooks/useDragTouch.ts` | 1-10 | 111 | 2026-05-17 | 2026-09-06 | /** |
| `voter-app/src/types.ts` | 132-132 | 111 | 2026-05-04 | 2026-08-24 | // --- Monte Carlo --- |
| `voter-app/src/types.ts` | 215-215 | 111 | 2026-05-04 | 2026-08-24 | // --- Multi-winner proportional methods --- |
| `voter-app/src/types.ts` | 244-244 | 111 | 2026-05-04 | 2026-08-24 | // --- Bandwagon simulation --- |
| `voter-app/src/components/Simulation/simulationConstants.ts` | 4-4 | 104 | 2026-05-11 | 2026-08-24 | // Static keys — used as fallback IDs and in non-React contexts (report generation, CSV export) |
| `fast_api_voter/api/sockets/__init__.py` | 76-76 | 102 | 2026-05-25 | 2026-09-04 | # ── Handlers ─────────────────────────────────────────────────────────────── |
| `fast_api_voter/api/domain/simulations/advanced.py` | 76-82 | 98 | 2026-05-30 | 2026-09-06 | """ |
| `voter-app/src/workers/simulationWorker.ts` | 1-12 | 97 | 2026-05-17 | 2026-08-23 | /** |
| `voter-app/src/services/profileApi.ts` | 34-34 | 74 | 2026-06-11 | 2026-08-24 | /** Build the `extra="forbid"` request body from shared electorate + playground knobs. */ |
| `voter-app/src/services/assemblyApi.ts` | 78-78 | 73 | 2026-06-11 | 2026-08-24 | /** Build the `extra="forbid"` request body from shared electorate + assembly knobs. */ |
| `voter-app/src/services/assemblyApi.ts` | 116-116 | 73 | 2026-06-12 | 2026-08-24 | /** All three structures are scored at once, so `structure` is not sent. */ |
| `fast_api_voter/api/domain/election/workers_advanced.py` | 779-779 | 70 | 2026-06-14 | 2026-08-24 | # ── Party Dynamics ──────────────────────────────────────────────────────────── |
| `fast_api_voter/api/domain/election/workers_advanced.py` | 1260-1260 | 70 | 2026-06-14 | 2026-08-24 | # ── /api/election/power-indices ─────────────────────────────────────────────── |
| `fast_api_voter/api/domain/election/workers_behavioral.py` | 335-335 | 70 | 2026-06-14 | 2026-08-24 | # ── Liquid Democracy ────────────────────────────────────────────────────────── |
| `fast_api_voter/api/domain/election/workers_behavioral.py` | 1505-1505 | 70 | 2026-06-14 | 2026-08-24 | # ── Choice Overload ─────────────────────────────────────────────────────────── |
| `fast_api_voter/api/domain/election/workers_behavioral.py` | 1790-1790 | 70 | 2026-06-14 | 2026-08-24 | """Pure worker for /choice-overload — extracted for FastAPI v2 reuse.""" |
| `voter-app/src/types.ts` | 90-90 | 70 | 2026-06-14 | 2026-08-24 | /** Compact, display-ready summary of a saved scenario's results. */ |
| `voter-app/src/lib/methodInfo.ts` | 40-40 | 66 | 2026-06-18 | 2026-08-24 | // Result-table / backend ids → canonical registry key. |
| `voter-app/src/lib/scenarioInfo.ts` | 124-126 | 66 | 2026-06-18 | 2026-08-24 | // Electorate-mixture presets (the "Modèles" in the Electorate Composer). Keyed |
| `fast_api_voter/api/engine/utils/simulation_score_utils.py` | 359-359 | 64 | 2025-11-10 | 2026-01-13 | # Find the utility of the voter's most preferred candidate |
| `voter-app/src/lib/playgroundMeta.ts` | 1-3 | 59 | 2026-06-25 | 2026-08-24 | // Playground metadata — labels + stated scorecard conventions, shared by the |
| `voter-app/src/App.test.tsx` | 23-23 | 58 | 2026-05-09 | 2026-07-07 | // ── Tests ────────────────────────────────────────────────────────────────── |
| `fast_api_voter/api/engine/utils/arrow_criteria.py` | 30-30 | 45 | 2026-05-03 | 2026-06-18 | # ── Method registry ──────────────────────────────────────────────────────── |
| `fast_api_voter/api/routes/health.py` | 22-22 | 45 | 2026-05-24 | 2026-07-09 | """Lazy import so the route doesn't pay redis cost when uncalled.""" |
| `fast_api_voter/api/engine/utils/simulation_multiwinner_utils.py` | 22-22 | 44 | 2026-05-04 | 2026-06-18 | # ── Single Transferable Vote ─────────────────────────────────────────────── |
| `fast_api_voter/api/engine/utils/simulation_multiwinner_utils.py` | 47-47 | 44 | 2026-05-04 | 2026-06-18 | # Pool: list of (weight, remaining_ranking) |
| `fast_api_voter/api/engine/utils/simulation_multiwinner_utils.py` | 388-388 | 44 | 2026-05-04 | 2026-06-18 | # Party-list methods |
| `fast_api_voter/api/engine/utils/simulation_multiwinner_utils.py` | 153-153 | 31 | 2026-05-17 | 2026-06-18 | # Pool: each entry is (weight: float, ranking: List[str]) |
| `fast_api_voter/api/engine/utils/simulation_ranked_utils.py` | 634-634 | 30 | 2026-05-19 | 2026-06-18 | # ── New methods ──────────────────────────────────────────────────────────────── |
| `voter-app/src/components/shared/GerrymanderMap.tsx` | 1-7 | 27 | 2026-05-17 | 2026-06-14 | /** |
| `voter-app/src/hooks/useChartTheme.ts` | 10-10 | 26 | 2026-05-09 | 2026-06-05 | /** CartesianGrid stroke */ |
| `voter-app/src/hooks/useChartTheme.ts` | 12-12 | 26 | 2026-05-09 | 2026-06-05 | /** Axis tick text fill */ |
| `voter-app/src/hooks/useChartTheme.ts` | 20-20 | 26 | 2026-05-09 | 2026-06-05 | /** Reference line stroke */ |
| `voter-app/src/lib/scorecard.ts` | 119-120 | 26 | 2026-07-03 | 2026-07-30 | /** Tier B: "explained, not compared" — surfaced only in the method gallery and |
| `fast_api_voter/api/engine/utils/simulation_ranked_utils.py` | 242-242 | 25 | 2026-07-29 | 2026-08-24 | # A candidate never ranked last has 0 vetoes — Counter.get defaults it in. |
| `voter-app/src/components/shared/ConvictionVotingPanel.tsx` | 1-5 | 25 | 2026-05-20 | 2026-06-14 | /** |
| `voter-app/src/components/shared/EmptyChart.tsx` | 9-12 | 25 | 2026-05-10 | 2026-06-05 | /** |
| `voter-app/src/hooks/useMetaTags.ts` | 45-45 | 25 | 2026-05-10 | 2026-06-05 | // Open Graph |
| `voter-app/src/hooks/useMetaTags.ts` | 51-51 | 25 | 2026-05-10 | 2026-06-05 | // Twitter / X |
| `fast_api_voter/api/domain/polity/citizen.py` | 171-173 | 24 | 2026-07-31 | 2026-08-25 | """Deterministic population generation: the same (config, population_size, |
| `fast_api_voter/api/domain/election/__init__.py` | 142-142 | 23 | 2026-05-24 | 2026-06-17 | # ── Perturber endpoints (Phase 3 batch 3) ────────────────────────────────── |
| `fast_api_voter/api/domain/election/__init__.py` | 164-164 | 23 | 2026-05-24 | 2026-06-17 | # ── Perturber endpoints (Phase 3 batch 4) ────────────────────────────────── |
| `fast_api_voter/api/domain/election/__init__.py` | 186-186 | 23 | 2026-05-24 | 2026-06-17 | # ── Perturber endpoints (Phase 3 batch 5) ────────────────────────────────── |
| `fast_api_voter/api/domain/election/__init__.py` | 208-208 | 23 | 2026-05-25 | 2026-06-17 | # ── Perturber endpoints (Phase 3 batch 6) ────────────────────────────────── |
| `fast_api_voter/api/domain/election/__init__.py` | 230-230 | 23 | 2026-05-25 | 2026-06-17 | # ── Phase 3 batch 7 ───────────────────────────────────────────────────────── |
| `fast_api_voter/api/domain/election/__init__.py` | 252-252 | 23 | 2026-05-25 | 2026-06-17 | # ── Phase 3 batch 8 ───────────────────────────────────────────────────────── |
| `fast_api_voter/api/domain/election/__init__.py` | 274-274 | 23 | 2026-05-25 | 2026-06-17 | # ── Phase 3 batch 9 (final) ──────────────────────────────────────────────── |
| `fast_api_voter/api/domain/theory/__init__.py` | 52-52 | 23 | 2026-05-25 | 2026-06-17 | # ── Phase 4 batch 2 ───────────────────────────────────────────────────────── |
| `fast_api_voter/api/domain/theory/__init__.py` | 74-74 | 23 | 2026-05-25 | 2026-06-17 | # ── Phase 4 batch 3 ───────────────────────────────────────────────────────── |
| `fast_api_voter/api/domain/theory/__init__.py` | 96-96 | 23 | 2026-05-25 | 2026-06-17 | # ── Phase 4 batch 4 (final) ───────────────────────────────────────────────── |
| `voter-app/src/App.test.tsx` | 5-5 | 23 | 2026-05-09 | 2026-06-02 | // ── Component mocks ──────────────────────────────────────────────────────── |
| `fast_api_voter/api/domain/polity/llm_client.py` | 310-314 | 22 | 2026-08-01 | 2026-08-24 | """600s default: a live consolidation run measured a real full-size |
| `fast_api_voter/api/domain/tech.py` | 121-121 | 22 | 2026-05-30 | 2026-06-22 | # ── Audit proof ─────────────────────────────────────────────────────── |
| `voter-app/src/components/playground/PlaygroundController.tsx` | 55-56 | 22 | 2026-06-25 | 2026-07-17 | // The active "moment" — the station on the instrument's journey. Drives the |
| `voter-app/src/components/pedagogy/AnimatedVoteCount.test.tsx` | 54-54 | 21 | 2026-05-15 | 2026-06-05 | // Plurality: no majority required — most votes wins |
| `voter-app/src/components/pedagogy/AnimatedVoteCount.tsx` | 11-11 | 21 | 2026-05-15 | 2026-06-05 | // ── Types ─────────────────────────────────────────────────────────────────── |
| `voter-app/src/components/pedagogy/AnimatedVoteCount.tsx` | 309-309 | 21 | 2026-05-15 | 2026-06-05 | // Derive 0–5 score from rank position |
| `voter-app/src/components/pedagogy/AnimatedVoteCount.tsx` | 421-421 | 21 | 2026-05-15 | 2026-06-05 | // Spread remaining votes among other candidates |
| `voter-app/src/pages/__tests__/PlaygroundPage.test.tsx` | 252-252 | 21 | 2026-06-12 | 2026-07-03 | // ── P5: scorecard + values lens ────────────────────────────────────────── |
| `voter-app/src/components/Simulation/__tests__/MonteCarloResults.test.tsx` | 88-88 | 20 | 2026-05-16 | 2026-06-05 | // Disable streaming to use the HTTP path |
| `voter-app/src/components/research/BlankVoteTimeSeries.tsx` | 73-73 | 20 | 2026-05-15 | 2026-06-05 | // Find blank_pct from any country key |
| `voter-app/src/components/research/BlankVoteTimeSeries.tsx` | 230-230 | 20 | 2026-05-15 | 2026-06-05 | // Visible events for selected countries |
| `voter-app/src/components/research/BlankVoteTimeSeries.tsx` | 233-233 | 20 | 2026-05-15 | 2026-06-05 | // Trend analyses |
| `voter-app/src/components/Simulation/VoteStepAnimator.tsx` | 507-507 | 19 | 2026-05-16 | 2026-06-05 | // ── Fetch data |
| `voter-app/src/components/shared/__tests__/CombinedEffectsMatrix.test.tsx` | 27-27 | 19 | 2026-05-16 | 2026-06-05 | // 8 combinations: blank × campaign × info |
| `voter-app/src/hooks/useDebouncedSimulation.test.ts` | 69-69 | 19 | 2026-05-16 | 2026-06-05 | // Advance past debounce window |
| `voter-app/src/hooks/useDebouncedSimulation.test.ts` | 100-100 | 19 | 2026-05-16 | 2026-06-05 | // One more advance to trigger final debounce |
| `voter-app/src/hooks/useDebouncedSimulation.test.ts` | 134-134 | 19 | 2026-05-16 | 2026-06-05 | // runNow should bypass the debounce |
| `voter-app/src/hooks/useDebouncedSimulation.test.ts` | 173-173 | 19 | 2026-05-16 | 2026-06-05 | // Resolve second run first |
| `voter-app/src/hooks/useDebouncedSimulation.test.ts` | 179-179 | 19 | 2026-05-16 | 2026-06-05 | // Resolve first run — should be discarded (stale) |
| `voter-app/src/hooks/useDebouncedSimulation.ts` | 41-42 | 19 | 2026-05-16 | 2026-06-05 | // Use refs to always read latest values inside the async callback |
| `voter-app/src/hooks/useDebouncedSimulation.ts` | 104-104 | 19 | 2026-05-16 | 2026-06-05 | // Candidate added or removed → clear results immediately |
| `voter-app/src/hooks/useMonteCarloStream.ts` | 114-114 | 19 | 2026-05-16 | 2026-06-05 | // Convergence: backend sends full accumulated history each time |
| `fast_api_voter/api/domain/tech.py` | 435-435 | 18 | 2026-05-30 | 2026-06-18 | # ── Classical election (plurality by ideology proximity) ────────────── |
| `fast_api_voter/api/domain/theory/workers.py` | 521-521 | 18 | 2026-05-30 | 2026-06-18 | # ── Constraint check helper ─────────────────────────────────────────── |
| `fast_api_voter/api/domain/theory/workers.py` | 906-906 | 18 | 2026-05-30 | 2026-06-18 | # ── Liberal order from private spheres ──────────────────────────────── |
| `fast_api_voter/api/domain/theory/workers.py` | 927-927 | 18 | 2026-05-30 | 2026-06-18 | # ── Pareto order ────────────────────────────────────────────────────── |
| `fast_api_voter/api/domain/theory/workers.py` | 1168-1168 | 18 | 2026-05-30 | 2026-06-18 | # ── Strategy generators ─────────────────────────────────────────────── |
| `fast_api_voter/api/domain/theory/workers.py` | 1182-1182 | 18 | 2026-05-30 | 2026-06-18 | # Elevate the weakest (last) candidate to second place to create spoiler |
| `voter-app/src/components/Simulation/IdeologyHeatmap.tsx` | 24-24 | 18 | 2026-05-17 | 2026-06-05 | // ── Constants ───────────────────────────────────────────────────────────────── |
| `voter-app/src/components/Simulation/IdeologyHeatmap.tsx` | 83-83 | 18 | 2026-05-17 | 2026-06-05 | // ── Async grid computation via Web Worker ───────────────────────────── |
| `voter-app/src/components/Simulation/MethodRaceBar.tsx` | 18-18 | 18 | 2026-05-17 | 2026-06-05 | // ── Constants ───────────────────────────────────────────────────────────────── |
| `voter-app/src/components/Simulation/MethodRaceBar.tsx` | 82-82 | 18 | 2026-05-17 | 2026-06-05 | // Methods that crossed the badge threshold |
| `voter-app/src/components/Simulation/MethodSimilarityGraph.tsx` | 1-8 | 18 | 2026-05-17 | 2026-06-05 | /** |
| `voter-app/src/components/Simulation/MethodSimilarityGraph.tsx` | 71-71 | 18 | 2026-05-17 | 2026-06-05 | // ── Helpers ─────────────────────────────────────────────────────────────────── |
| `voter-app/src/components/Simulation/MethodSimilarityGraph.tsx` | 73-73 | 18 | 2026-05-17 | 2026-06-05 | /** Convert flat "A\|B" → value map to a symmetric nested matrix. */ |
| `voter-app/src/components/Simulation/MonteCarloRaceChart.tsx` | 92-94 | 18 | 2026-05-17 | 2026-06-05 | // ── Accumulate history snapshots ────────────────────────────────────────── |
| `voter-app/src/components/shared/AbstentionPanel.tsx` | 75-75 | 18 | 2026-05-17 | 2026-06-05 | // ── SVG ideology map with abstention overlay ────────────────────────────────── |
| `voter-app/src/components/shared/AbstentionPanel.tsx` | 274-274 | 18 | 2026-05-17 | 2026-06-05 | // Turnout line chart data |
| `voter-app/src/components/shared/CampaignSwimlane.tsx` | 6-6 | 18 | 2026-05-17 | 2026-06-05 | // ── SVG layout constants ────────────────────────────────────────────────────── |
| `voter-app/src/components/shared/CampaignSwimlane.tsx` | 60-60 | 18 | 2026-05-17 | 2026-06-05 | // Reset on new data |
| `voter-app/src/components/shared/CampaignSwimlane.tsx` | 82-82 | 18 | 2026-05-17 | 2026-06-05 | // X-axis mapping: day → SVG X coordinate |
| `voter-app/src/components/shared/CoalitionPanel.tsx` | 17-17 | 18 | 2026-05-17 | 2026-06-05 | // ── Palette ─────────────────────────────────────────────────────────────────── |
| `voter-app/src/components/shared/DistrictMap.tsx` | 19-19 | 18 | 2026-05-17 | 2026-06-05 | // ── Palette ─────────────────────────────────────────────────────────────────── |
| `voter-app/src/components/shared/DistrictMap.tsx` | 159-159 | 18 | 2026-05-17 | 2026-06-05 | // ideology gradient tint: left-leaning = slight blue, right = slight red |
| `voter-app/src/components/shared/ElectionPipelineAnimator.tsx` | 14-14 | 18 | 2026-05-17 | 2026-06-05 | // ── SVG constants (same coord system as IdeologyMapChart) ───────────────────── |
| `voter-app/src/components/shared/ElectionPipelineAnimator.tsx` | 27-27 | 18 | 2026-05-17 | 2026-06-05 | // ── Colours ─────────────────────────────────────────────────────────────────── |
| `voter-app/src/components/shared/GerrymanderMap.tsx` | 20-20 | 18 | 2026-05-17 | 2026-06-05 | // ── Grid constants ──────────────────────────────────────────────────────────── |
| `voter-app/src/components/shared/GerrymanderMap.tsx` | 28-28 | 18 | 2026-05-17 | 2026-06-05 | // ── Types ───────────────────────────────────────────────────────────────────── |
| `voter-app/src/components/shared/GerrymanderMap.tsx` | 136-136 | 18 | 2026-05-17 | 2026-06-05 | // ── SVG coordinate helpers ───────────────────────────────────────────────── |
| `voter-app/src/components/shared/HistoricalReplay.tsx` | 263-263 | 18 | 2026-05-17 | 2026-06-05 | // Candidates with drag-updated positions |
| `voter-app/src/components/shared/HotellingPanel.tsx` | 67-67 | 18 | 2026-05-18 | 2026-06-05 | // Multi-method comparison |
| `voter-app/src/components/shared/STVPanel.tsx` | 46-46 | 18 | 2026-05-17 | 2026-06-05 | // ── Palette ─────────────────────────────────────────────────────────────────── |
| `voter-app/src/components/shared/__tests__/GerrymanderMap.test.tsx` | 94-94 | 18 | 2026-05-17 | 2026-06-05 | // After one click, district should be (initialDistrict + 1) % numDist |
| `voter-app/src/components/shared/__tests__/JuryTheoremPanel.test.tsx` | 187-187 | 18 | 2026-05-17 | 2026-06-05 | // Advance fake timers past debounce |
| `voter-app/src/components/shared/__tests__/MethodGroupDonut.test.tsx` | 59-59 | 18 | 2026-05-17 | 2026-06-05 | // donutSingle key or its translation |
| `voter-app/src/hooks/useDragTouch.ts` | 18-18 | 18 | 2026-05-17 | 2026-06-05 | /** Called on each move while dragging. */ |
| `voter-app/src/hooks/useDragTouch.ts` | 20-20 | 18 | 2026-05-17 | 2026-06-05 | /** Called when the drag ends. */ |
| `voter-app/src/hooks/useDragTouch.ts` | 116-116 | 18 | 2026-05-17 | 2026-06-05 | // ── Mouse events (window-level to capture fast pointer movement) ─────────── |
| `voter-app/src/utils/voronoiRegions.test.ts` | 3-3 | 18 | 2026-05-17 | 2026-06-05 | // Simple domainToSvg for tests: maps [-1,1] → [40, 440] on a 480px canvas |
| `fast_api_voter/api/domain/election/__init__.py` | 1-16 | 17 | 2026-05-30 | 2026-06-17 | """ |
| `fast_api_voter/api/domain/theory/__init__.py` | 1-10 | 17 | 2026-05-30 | 2026-06-17 | """ |
| `voter-app/src/components/shared/AffectivePolarizationPanel.tsx` | 72-72 | 17 | 2026-05-19 | 2026-06-05 | // ── SVG ideology overlay ────────────────────────────────────────────────────── |
| `voter-app/src/components/shared/CascadePanel.tsx` | 104-104 | 17 | 2026-05-19 | 2026-06-05 | // cascade line x position |
| `voter-app/src/components/shared/MultiwinnerCompare.tsx` | 53-53 | 17 | 2026-05-19 | 2026-06-05 | // ── Palette ─────────────────────────────────────────────────────────────────── |
| `voter-app/src/components/shared/MultiwinnerCompare.tsx` | 204-204 | 17 | 2026-05-19 | 2026-06-05 | // Pedagogical message |
| `voter-app/src/components/shared/PolarizationPanel.tsx` | 240-240 | 17 | 2026-05-18 | 2026-06-05 | // Threshold where condorcet rate < 70% |
| `voter-app/src/components/shared/__tests__/DistrictMap.test.tsx` | 130-130 | 17 | 2026-05-17 | 2026-06-03 | // Warning alert appears when winners differ |
| `voter-app/src/components/shared/__tests__/HistoricalReferencePanel.test.tsx` | 152-152 | 17 | 2026-05-17 | 2026-06-03 | // The scenario-specific pedagogical note should appear |
| `voter-app/src/components/shared/BallotComplexityPanel.tsx` | 158-158 | 16 | 2026-05-20 | 2026-06-05 | // ── Bar chart data ────────────────────────────────────────────────────── |
| `voter-app/src/components/shared/BallotComplexityPanel.tsx` | 166-166 | 16 | 2026-05-20 | 2026-06-05 | // ── Curve data ────────────────────────────────────────────────────────── |
| `voter-app/src/components/shared/ChoiceOverloadPanel.tsx` | 96-96 | 16 | 2026-05-20 | 2026-06-05 | // ── Line chart data ───────────────────────────────────────────────────── |
| `voter-app/src/components/shared/ConvictionVotingPanel.tsx` | 74-74 | 16 | 2026-05-20 | 2026-06-05 | // ── Palette ─────────────────────────────────────────────────────────────────── |
| `voter-app/src/components/shared/ConvictionVotingPanel.tsx` | 90-90 | 16 | 2026-05-20 | 2026-06-05 | // ── Scatter SVG ─────────────────────────────────────────────────────────────── |
| `voter-app/src/components/shared/ConvictionVotingPanel.tsx` | 122-122 | 16 | 2026-05-20 | 2026-06-05 | // Sample to max 200 dots for performance |
| `voter-app/src/components/shared/DemographicTurnoutPanel.tsx` | 32-32 | 16 | 2026-05-20 | 2026-06-05 | // ── Types ───────────────────────────────────────────────────────────────────── |
| `voter-app/src/components/shared/DemographicTurnoutPanel.tsx` | 66-66 | 16 | 2026-05-20 | 2026-06-05 | // ── Preset profiles ─────────────────────────────────────────────────────────── |
| `voter-app/src/components/shared/DemographicTurnoutPanel.tsx` | 117-117 | 16 | 2026-05-20 | 2026-06-05 | // ── Ideology drift SVG ──────────────────────────────────────────────────────── |
| `voter-app/src/components/shared/DemographicTurnoutPanel.tsx` | 238-238 | 16 | 2026-05-20 | 2026-06-05 | // ── Chart data ────────────────────────────────────────────────────────── |
| `voter-app/src/components/shared/ElectoralFatiguePanel.tsx` | 201-201 | 16 | 2026-05-20 | 2026-06-05 | // ── Chart data ────────────────────────────────────────────────────────── |
| `voter-app/src/components/shared/LiquidDemocracyPanel.tsx` | 99-99 | 16 | 2026-05-19 | 2026-06-05 | // Build node set (cap at 150 for performance) |
| `voter-app/src/components/shared/LiquidDemocracyPanel.tsx` | 124-124 | 16 | 2026-05-19 | 2026-06-05 | // Arrow marker |
| `voter-app/src/components/shared/LiquidDemocracyPanel.tsx` | 163-163 | 16 | 2026-05-19 | 2026-06-05 | // Super-voter crown ring |
| `voter-app/src/components/shared/LiquidDemocracyPanel.tsx` | 173-173 | 16 | 2026-05-19 | 2026-06-05 | // Cycle voter ring |
| `voter-app/src/components/shared/LiquidDemocracyPanel.tsx` | 183-183 | 16 | 2026-05-19 | 2026-06-05 | // Main dot |
| `voter-app/src/components/shared/__tests__/BallotComplexityPanel.test.tsx` | 34-34 | 16 | 2026-05-20 | 2026-06-05 | // ── Fixture ─────────────────────────────────────────────────────────────────── |
| `voter-app/src/i18n/locales/fr.ts` | 2696-2696 | 16 | 2026-05-20 | 2026-06-05 | // Section 1 |
| `voter-app/src/i18n/locales/fr.ts` | 2706-2706 | 16 | 2026-05-20 | 2026-06-05 | // Section 2 — E2E-V |
| `voter-app/src/i18n/locales/fr.ts` | 2734-2734 | 16 | 2026-05-20 | 2026-06-05 | // Section 4 — Pol.is |
| `fast_api_voter/api/domain/polity/codebook.py` | 46-47 | 15 | 2026-08-01 | 2026-08-16 | """Raised when a run's configured codebook_version doesn't match the |
| `fast_api_voter/api/domain/theory/workers.py` | 1921-1921 | 15 | 2026-05-30 | 2026-06-14 | # ── Pedagogical note ────────────────────────────────────────────────────── |
| `fast_api_voter/api/engine/utils/campaign_dynamics.py` | 75-79 | 15 | 2026-05-15 | 2026-05-30 | """ |
| `fast_api_voter/api/engine/utils/gibbard_satterthwaite.py` | 30-30 | 15 | 2026-05-15 | 2026-05-30 | """Return the winner function for a ranked-ballot method key, or None.""" |
| `fast_api_voter/api/tests/test_kemeny_young.py` | 1-5 | 15 | 2026-08-21 | 2026-09-06 | """Unit tests for Kemeny-Young: the exact algorithm (<= 6 candidates) |
| `voter-app/src/components/shared/CompulsoryVotingPanel.tsx` | 24-24 | 15 | 2026-05-21 | 2026-06-05 | // ── Types ───────────────────────────────────────────────────────────────────── |
| `voter-app/src/components/shared/__tests__/HistoricalReferencePanel.test.tsx` | 6-6 | 15 | 2026-05-17 | 2026-06-02 | // Mock the ElectionContext so we control scenarioMeta directly |
| `voter-app/src/components/shared/__tests__/MethodGroupDonut.test.tsx` | 6-6 | 15 | 2026-05-17 | 2026-06-02 | // Mock Recharts — expose Cell dataKey for assertions |
| `voter-app/src/components/shared/__tests__/PrimarySimulator.test.tsx` | 15-15 | 15 | 2026-05-17 | 2026-06-02 | // Mock Recharts to avoid SVG measurement issues in jsdom |
| `voter-app/src/hooks/__tests__/useSimulationWorker.test.ts` | 110-110 | 15 | 2026-05-17 | 2026-06-02 | // ── 3. Mock-based hook interface test ───────────────────────────────────────── |
| `voter-app/src/hooks/__tests__/useSimulationWorker.test.ts` | 112-113 | 15 | 2026-05-17 | 2026-06-02 | // The hook can't be imported directly in Jest due to import.meta.url. |
| `fast_api_voter/api/domain/polity/simple_rules.py` | 58-58 | 14 | 2026-07-31 | 2026-08-14 | # ── 1. Vote rule ────────────────────────────────────────────────────────── |
| `fast_api_voter/api/engine/utils/simulation_metrics.py` | 47-48 | 14 | 2026-05-03 | 2026-05-17 | # Maximum number of voters sampled when computing strategic_vulnerability. |
| `fast_api_voter/api/tests/test_polity_metrics.py` | 1-5 | 14 | 2026-07-31 | 2026-08-14 | """Lot 9 — metrics.py: the v0 subset of output metrics. |
| `voter-app/src/components/playground/LeaderCanvas.tsx` | 44-44 | 14 | 2026-06-19 | 2026-07-03 | // Manipulation lens — each voter as a conviction bloc; colour by temptation. |
| `voter-app/src/components/shared/AgendaManipulationPanel.tsx` | 45-45 | 14 | 2026-05-21 | 2026-06-05 | // ── Pairwise matrix SVG ─────────────────────────────────────────────────────── |
| `voter-app/src/components/shared/DemocraticBackslidingPanel.tsx` | 173-173 | 14 | 2026-05-22 | 2026-06-05 | // ── Chart data ───────────────────────────────────────────────────────────── |
| `voter-app/src/components/shared/JudgmentAggregationPanel.tsx` | 49-49 | 14 | 2026-05-21 | 2026-06-05 | // ── Logic Tree SVG ──────────────────────────────────────────────────────────── |
| `voter-app/src/components/shared/ManipulationAnalysisPanel.tsx` | 134-134 | 14 | 2026-05-21 | 2026-06-05 | // ── Voter detail panel ──────────────────────────────────────────────────────── |
| `voter-app/src/components/shared/ManipulationAnalysisPanel.tsx` | 210-210 | 14 | 2026-05-21 | 2026-06-05 | // All voter positions (for the map background) |
| `voter-app/src/components/shared/PartyDynamicsPanel.tsx` | 34-34 | 14 | 2026-05-21 | 2026-06-05 | // ── Presets ─────────────────────────────────────────────────────────────────── |
| `voter-app/src/components/shared/PartyDynamicsPanel.tsx` | 88-88 | 14 | 2026-05-21 | 2026-06-05 | // ── Ideology map SVG ────────────────────────────────────────────────────────── |
| `voter-app/src/components/shared/PolisPanel.tsx` | 65-65 | 14 | 2026-05-21 | 2026-06-05 | // ── PCA Scatter ─────────────────────────────────────────────────────────────── |
| `voter-app/src/components/shared/PowerIndicesPanel.tsx` | 183-183 | 14 | 2026-05-22 | 2026-06-05 | // ── Scatter: seats% vs Shapley% ─────────────────────────────────────────────── |
| `voter-app/src/components/shared/SenParadoxPanel.tsx` | 23-23 | 14 | 2026-05-21 | 2026-06-05 | // ── Conflict visualisation SVG ──────────────────────────────────────────────── |
| `fast_api_voter/api/routes/theory.py` | 73-73 | 13 | 2026-05-25 | 2026-06-07 | # ── Shared helper ─────────────────────────────────────────────────────────── |
| `fast_api_voter/api/tests/test_polity_codebook.py` | 1-6 | 13 | 2026-08-01 | 2026-08-14 | """codebook.py — the vote-decision slice of design doc §3.7's compression tables. |
| `fast_api_voter/api/tests/test_polity_llm_client.py` | 1-4 | 13 | 2026-08-01 | 2026-08-15 | """llm_client.py — sync Ollama transport + batch envelope decoding. |
| `voter-app/src/components/Simulation/VoteStepAnimator.tsx` | 452-454 | 13 | 2026-05-23 | 2026-06-05 | // Full candidate configs (with positions) — when provided, the animation |
| `voter-app/src/components/playground/__tests__/IssuesPanel.test.tsx` | 55-55 | 13 | 2026-06-13 | 2026-06-26 | // Aligned profile: no paradox headline, no divergence marks. |
| `voter-app/src/components/shared/CollectiveWillPanel.tsx` | 53-53 | 13 | 2026-05-22 | 2026-06-05 | // Semi-circle arc from π to 0 (left to right) |
| `voter-app/src/components/shared/ElectionPipelineAnimator.tsx` | 245-245 | 13 | 2026-05-17 | 2026-05-31 | // ── Fetch pipeline ──────────────────────────────────────────────────── |
| `voter-app/src/components/shared/EpistocracyPanel.tsx` | 56-56 | 13 | 2026-05-22 | 2026-06-05 | // ── Constants ───────────────────────────────────────────────────────────────── |
| `voter-app/src/components/shared/IdentityVotingPanel.tsx` | 261-261 | 13 | 2026-05-22 | 2026-06-05 | // Reset groups to use first lab candidate as affiliation |
| `voter-app/src/components/shared/IdentityVotingPanel.tsx` | 310-310 | 13 | 2026-05-22 | 2026-06-05 | // ── Chart data ───────────────────────────────────────────────────────────── |
| `voter-app/src/components/shared/__tests__/JuryTheoremPanel.test.tsx` | 34-34 | 13 | 2026-05-17 | 2026-05-31 | // ── Fixture ─────────────────────────────────────────────────────────────────── |
| `voter-app/src/components/shared/__tests__/JuryTheoremPanel.test.tsx` | 184-184 | 13 | 2026-05-17 | 2026-05-31 | // Before debounce fires: no extra call yet |
| `voter-app/src/components/shared/__tests__/LiquidDemocracyPanel.test.tsx` | 15-15 | 13 | 2026-05-19 | 2026-06-02 | // D3 mock — force simulation not available in JSDOM |
| `voter-app/src/pages/__tests__/PlaygroundPage.test.tsx` | 213-213 | 13 | 2026-06-11 | 2026-06-25 | // ── P4: the dynamic layer ──────────────────────────────────────────────── |
| `voter-app/src/pages/__tests__/PlaygroundPage.test.tsx` | 220-220 | 13 | 2026-06-11 | 2026-06-25 | // Replayable in the other direction. |
| `voter-app/src/pages/__tests__/PlaygroundPage.test.tsx` | 300-300 | 13 | 2026-06-13 | 2026-06-26 | // The worked example compares plurality vs IRV on this electorate. |
| `voter-app/src/components/Simulation/VoteStepAnimator.tsx` | 542-542 | 12 | 2026-05-23 | 2026-06-05 | // Clear central-view broadcast when the animator unmounts (user switches tab) |
| `voter-app/src/theme/PageContainer.tsx` | 27-27 | 12 | 2026-05-23 | 2026-06-05 | /** Extra inline style merged onto the container. */ |
| `voter-app/src/theme/PageContainer.tsx` | 30-30 | 12 | 2026-05-23 | 2026-06-05 | /** Default vertical padding class. Override with eg "py-3". */ |
| `voter-app/src/theme/tokens.ts` | 54-54 | 12 | 2026-05-23 | 2026-06-05 | // ── Common aliases (Bootstrap convention) ──────────────────────────────── |
| `fast_api_voter/api/engine/utils/simulation_metrics.py` | 300-302 | 11 | 2026-05-03 | 2026-05-15 | # ------------------------------------------------------------------ |
| `fast_api_voter/api/engine/utils/simulation_metrics.py` | 340-342 | 11 | 2026-05-03 | 2026-05-15 | # ------------------------------------------------------------------ |
| `fast_api_voter/api/engine/utils/simulation_metrics.py` | 621-623 | 11 | 2026-05-03 | 2026-05-15 | # Condorcet cycles: find triples A > B > C > A. |
| `fast_api_voter/api/engine/utils/simulation_voting_utils.py` | 493-496 | 11 | 2026-05-03 | 2026-05-15 | """ |
| `fast_api_voter/api/engine/utils/simulation_voting_utils.py` | 518-522 | 11 | 2026-05-03 | 2026-05-15 | """ |
| `fast_api_voter/api/engine/utils/simulation_voting_utils.py` | 548-552 | 11 | 2026-05-03 | 2026-05-15 | """ |
| `fast_api_voter/api/engine/utils/simulation_voting_utils.py` | 579-584 | 11 | 2026-05-03 | 2026-05-15 | """ |
| `fast_api_voter/api/engine/utils/simulation_voting_utils.py` | 606-609 | 11 | 2026-05-03 | 2026-05-15 | """ |
| `fast_api_voter/api/engine/utils/simulation_voting_utils.py` | 842-842 | 11 | 2026-05-03 | 2026-05-15 | # --- 4. Voting Methods --- |
| `fast_api_voter/api/engine/utils/simulation_voting_utils.py` | 844-844 | 11 | 2026-05-03 | 2026-05-15 | # Method groups used for strategic dispatch and sincere fallback. |
| `voter-app/src/api/index.ts` | 21-21 | 11 | 2026-05-24 | 2026-06-05 | // ── Convenience aliases for request/response bodies ──────────────────────── |
| `voter-app/src/api/index.ts` | 46-46 | 11 | 2026-05-24 | 2026-06-05 | // ── Shared primitives ────────────────────────────────────────────────────── |
| `voter-app/src/components/lab/labCatalog.tsx` | 190-190 | 11 | 2026-07-17 | 2026-07-28 | // ── The catalog ────────────────────────────────────────────────────────────── |
| `voter-app/src/components/shared/__tests__/ConvictionVotingPanel.test.tsx` | 236-236 | 11 | 2026-05-20 | 2026-05-31 | // gini_conviction=0.45 < gini_tokens=0.62 → green badge |
| `voter-app/src/components/shared/__tests__/NOTAPanel.test.tsx` | 144-144 | 11 | 2026-05-20 | 2026-05-31 | // Slider at 0 / low nota_pct → no invalid badge |
| `fast_api_voter/api/engine/utils/real_election_data.py` | 85-85 | 10 | 2026-05-04 | 2026-05-15 | # ── Real election data ───────────────────────────────────────────────────── |
| `fast_api_voter/api/engine/utils/real_election_data.py` | 402-402 | 10 | 2026-05-04 | 2026-05-15 | # Real plurality winner (most first-round votes) |
| `fast_api_voter/api/engine/utils/simulation_voting_utils.py` | 743-743 | 10 | 2026-05-04 | 2026-05-15 | # Utilities and sincere rankings |
| `fast_api_voter/api/engine/utils/simulation_voting_utils.py` | 764-764 | 10 | 2026-05-04 | 2026-05-15 | # Winner + Bayesian regret per method |
| `fast_api_voter/api/tests/test_polity_citizen.py` | 1-5 | 9 | 2026-07-31 | 2026-08-10 | """Lot 2 — citizen.py: the Citizen entity + deterministic population generation. |
| `fast_api_voter/api/domain/polity/simple_rules.py` | 326-326 | 8 | 2026-07-31 | 2026-08-09 | # ── 3. Coalition rule ───────────────────────────────────────────────────── |
| `voter-app/src/__mocks__/useSimulationWorker.ts` | 1-14 | 8 | 2026-05-24 | 2026-06-02 | /** |
| `voter-app/src/components/playground/InstrumentPanel.tsx` | 18-21 | 7 | 2026-06-26 | 2026-07-03 | // InstrumentPanel — the live screen. The spatial map sits inside the signature |
| `fast_api_voter/api/domain/simulations/helpers.py` | 145-150 | 6 | 2026-05-07 | 2026-05-14 | """ |
| `fast_api_voter/api/main.py` | 118-118 | 6 | 2026-05-24 | 2026-05-30 | # ── Access log middleware ─────────────────────────────────────────────────── |
| `fast_api_voter/api/routes/election.py` | 34-35 | 6 | 2026-05-24 | 2026-05-30 | # Re-uses the Pydantic models defined in Phase 1. Single source of truth |
| `fast_api_voter/api/routes/election.py` | 448-451 | 6 | 2026-05-24 | 2026-05-31 | """A voter casts NOTA when their max-utility for any candidate is below |
| `fast_api_voter/api/routes/election.py` | 467-469 | 6 | 2026-05-24 | 2026-05-31 | """P(null \| method) = error_base × candidate_factor × education_factor |
| `fast_api_voter/api/routes/election.py` | 483-486 | 6 | 2026-05-24 | 2026-05-31 | """Voters intending to vote for the 'sensitive' candidate (index |
| `fast_api_voter/api/routes/election.py` | 503-506 | 6 | 2026-05-24 | 2026-05-31 | """P(vote \| election k) = max(engaged_voter_pct, 1 - k × fatigue_rate). |
| `fast_api_voter/api/routes/election.py` | 520-522 | 6 | 2026-05-24 | 2026-05-31 | """Each voter observes the last `observation_window` votes and may follow |
| `fast_api_voter/api/routes/election.py` | 536-538 | 6 | 2026-05-24 | 2026-05-31 | """Three empirical biases stacked: expressive voting (Fiorina 1976), |
| `fast_api_voter/api/routes/election.py` | 552-555 | 6 | 2026-05-24 | 2026-05-31 | """Schwartz 2004 paradox of choice: beyond `overload_threshold` |
| `fast_api_voter/api/routes/election.py` | 567-569 | 6 | 2026-05-24 | 2026-05-31 | """Voters update their ideology toward a network-weighted mean for |
| `fast_api_voter/api/routes/election.py` | 583-586 | 6 | 2026-05-24 | 2026-05-31 | """Voters with individual competence p > 0.5 aggregate collectively |
| `fast_api_voter/api/routes/election.py` | 598-600 | 6 | 2026-05-24 | 2026-05-31 | """Each candidate iteratively moves in the direction (±x, ±y) that |
| `fast_api_voter/api/routes/election.py` | 612-615 | 6 | 2026-05-24 | 2026-05-31 | """For each voter distribution in `ideology_range`, computes the |
| `fast_api_voter/api/routes/election.py` | 627-629 | 6 | 2026-05-24 | 2026-05-31 | """Compares three assembly-selection methods on the same population: |
| `fast_api_voter/api/routes/election.py` | 645-647 | 6 | 2026-05-25 | 2026-05-31 | """Voters penalise candidates from the opposing political camp |
| `fast_api_voter/api/routes/election.py` | 661-664 | 6 | 2026-05-25 | 2026-05-31 | """Distortion between the real electorate and the effective electorate |
| `fast_api_voter/api/routes/election.py` | 678-680 | 6 | 2026-05-25 | 2026-05-31 | """Voluntary turnout is right-biased (empirical pattern); compulsory |
| `fast_api_voter/api/routes/election.py` | 694-697 | 6 | 2026-05-25 | 2026-05-31 | """Parties adapt positions (Hotelling), get eliminated below |
| `fast_api_voter/api/routes/election.py` | 714-715 | 6 | 2026-05-25 | 2026-05-31 | """Same compute as /simulate, but emits a per-step snapshot of voter |
| `fast_api_voter/api/routes/election.py` | 727-729 | 6 | 2026-05-25 | 2026-05-31 | """Each district elects its winner by FPTP from a locally biased |
| `fast_api_voter/api/routes/election.py` | 741-744 | 6 | 2026-05-25 | 2026-05-31 | """Each party holds an internal primary among its partisan voters; |
| `fast_api_voter/api/routes/election.py` | 756-757 | 6 | 2026-05-25 | 2026-05-31 | """Multi-seat STV (Droop, Hare, or Imperiali quota) compared to |
| `fast_api_voter/api/routes/election.py` | 771-773 | 6 | 2026-05-25 | 2026-05-31 | """Each round, voters whose 1st choice polls below `strategic_threshold` |
| `fast_api_voter/api/routes/election.py` | 788-790 | 6 | 2026-05-25 | 2026-05-31 | """Brownian campaign simulation for 4 historical scenarios |
| `fast_api_voter/api/routes/election.py` | 802-804 | 6 | 2026-05-25 | 2026-05-31 | """Voters assigned to the (smallest) overlapping district or the |
| `fast_api_voter/api/routes/election.py` | 818-820 | 6 | 2026-05-25 | 2026-05-31 | """Same electorate, 5 multi-winner methods. Reports per-method |
| `fast_api_voter/api/routes/election.py` | 834-835 | 6 | 2026-05-25 | 2026-05-31 | """Isolates the effect of blank-vote rules on inter-method agreement |
| `fast_api_voter/api/routes/election.py` | 848-849 | 6 | 2026-05-25 | 2026-05-31 | """Pure rule-based text interpretation of an existing /simulate |
| `fast_api_voter/api/routes/election.py` | 863-865 | 6 | 2026-05-25 | 2026-05-31 | """QF amplifies projects with many small donors over those with few |
| `fast_api_voter/api/routes/election.py` | 879-881 | 6 | 2026-05-25 | 2026-05-31 | """Each voter votes directly or delegates. Delegation chains are |
| `fast_api_voter/api/routes/election.py` | 895-897 | 6 | 2026-05-25 | 2026-05-31 | """Voters with longer locks amplify their votes (×0.1 at 0 days, |
| `fast_api_voter/api/routes/election.py` | 911-913 | 6 | 2026-05-25 | 2026-05-31 | """Shapley-Shubik (pivot-in-permutation) and Banzhaf |
| `voter-app/src/components/playground/__tests__/NoShowParadox.test.tsx` | 20-20 | 6 | 2026-06-19 | 2026-06-26 | // At rest (nobody abstains) there is no paradox highlighted. |
| `voter-app/src/components/shared/__tests__/BallotComplexityPanel.test.tsx` | 121-122 | 6 | 2026-05-24 | 2026-05-31 | // Accept either /api/election/* (Flask) or /api/v2/election/* (FastAPI v2, |
| `voter-app/src/components/shared/__tests__/CoalitionPanel.test.tsx` | 87-88 | 6 | 2026-05-24 | 2026-05-31 | // Accept either /api/election/coalition (Flask v1) or |
| `voter-app/src/components/Simulation/MonteCarloResults.tsx` | 151-151 | 5 | 2026-05-04 | 2026-05-10 | // ── Derived ──────────────────────────────────────────────────────────── |
| `voter-app/src/components/lab/labCatalog.tsx` | 6-18 | 5 | 2026-07-17 | 2026-07-22 | // labCatalog — the Laboratoire's entire content as DATA. One entry per |
| `voter-app/src/components/lab/labCatalog.tsx` | 20-20 | 5 | 2026-07-17 | 2026-07-22 | // ── Lazy panels (formerly spread across 8 anchor files) ───────────────────── |
| `voter-app/src/components/lab/labCatalog.tsx` | 22-22 | 5 | 2026-07-17 | 2026-07-22 | // Méthodes |
| `fast_api_voter/api/engine/utils/real_election_data.py` | 343-343 | 4 | 2026-05-04 | 2026-05-09 | # ── Analysis ─────────────────────────────────────────────────────────────── |
| `fast_api_voter/api/engine/utils/simul.py` | 19-19 | 4 | 2025-11-10 | 2025-11-14 | # Assign demographics |
| `fast_api_voter/api/engine/utils/simul.py` | 94-94 | 4 | 2025-11-10 | 2025-11-14 | # Collect votes (including "No Vote" for those who turned out but abstained) |
| `fast_api_voter/api/engine/utils/simul.py` | 129-129 | 4 | 2025-11-10 | 2025-11-14 | # Sort candidates by score to create ranking (highest score first) |
| `fast_api_voter/api/engine/utils/simul.py` | 132-132 | 4 | 2025-11-10 | 2025-11-14 | # Collect rankings |
| `fast_api_voter/api/engine/utils/simul.py` | 175-175 | 4 | 2025-11-10 | 2025-11-14 | # Scale to 0-5 |
| `fast_api_voter/api/engine/utils/simul.py` | 185-185 | 4 | 2025-11-10 | 2025-11-14 | # Clamp to 0-5 |
| `fast_api_voter/api/engine/utils/simul.py` | 190-190 | 4 | 2025-11-10 | 2025-11-14 | # Collect scores |
| `fast_api_voter/api/engine/utils/simulation_score_utils.py` | 229-229 | 4 | 2025-11-10 | 2025-11-14 | # Sort by combined score (descending) |
| `fast_api_voter/api/engine/utils/simulation_score_utils.py` | 277-277 | 4 | 2025-11-10 | 2025-11-14 | # Sort by weighted score (descending) |
| `fast_api_voter/api/engine/utils/simulation_score_utils.py` | 331-331 | 4 | 2025-11-10 | 2025-11-14 | # Sort by total votes (descending) |
| `fast_api_voter/api/engine/utils/simulation_score_utils.py` | 381-381 | 4 | 2025-11-10 | 2025-11-14 | # Sort by average regret (ascending - lower regret is better) |
| `fast_api_voter/api/engine/utils/simulation_voting_utils.py` | 340-340 | 4 | 2025-11-10 | 2025-11-14 | # More extreme = more likely to vote |
| `fast_api_voter/api/engine/utils/simulation_voting_utils.py` | 928-928 | 4 | 2025-11-10 | 2025-11-14 | # --- 4. Run Simulation --- |
| `fast_api_voter/api/tests/test_sockets.py` | 32-35 | 4 | 2026-05-25 | 2026-05-30 | """Run the FastAPI + Socket.IO ASGI app on a random local port. |
| `voter-app/src/components/Simulation/MonteCarloResults.tsx` | 43-43 | 4 | 2026-05-04 | 2026-05-09 | // ── Helpers ──────────────────────────────────────────────────────────────── |
| `voter-app/src/components/shared/DistrictMap.tsx` | 13-14 | 4 | 2026-06-01 | 2026-06-05 | // ── Types ───────────────────────────────────────────────────────────────────── |
| `voter-app/src/components/shared/HistoricalReplay.tsx` | 17-18 | 4 | 2026-06-01 | 2026-06-05 | // ── Types ───────────────────────────────────────────────────────────────────── |
| `voter-app/src/components/shared/PartyDynamicsPanel.tsx` | 27-28 | 4 | 2026-06-01 | 2026-06-05 | // ── Types ───────────────────────────────────────────────────────────────────── |
| `voter-app/src/components/shared/SenParadoxPanel.tsx` | 18-19 | 4 | 2026-06-01 | 2026-06-05 | // ── Types ───────────────────────────────────────────────────────────────────── |
| `voter-app/src/components/shared/SkeletonCard.tsx` | 44-47 | 4 | 2026-05-09 | 2026-05-14 | /** |
| `fast_api_voter/api/domain/election/workers_advanced.py` | 385-386 | 3 | 2026-06-14 | 2026-06-18 | # Voluntary: right-leaning voters have higher effective threshold |
| `fast_api_voter/api/domain/election/workers_advanced.py` | 424-424 | 3 | 2026-06-14 | 2026-06-18 | # ── Election runner (plurality) ─────────────────────────────────────── |
| `fast_api_voter/api/domain/election/workers_advanced.py` | 574-574 | 3 | 2026-06-14 | 2026-06-18 | # ── Metric helpers ──────────────────────────────────────────────────── |
| `fast_api_voter/api/domain/election/workers_advanced.py` | 642-642 | 3 | 2026-06-14 | 2026-06-18 | # ── Assembly constructors ───────────────────────────────────────────── |
| `fast_api_voter/api/domain/election/workers_advanced.py` | 711-711 | 3 | 2026-06-14 | 2026-06-18 | # ── Winner by assembly ──────────────────────────────────────────────── |
| `fast_api_voter/api/domain/election/workers_behavioral.py` | 256-256 | 3 | 2026-06-14 | 2026-06-18 | # ── Approval with bullet voting ─────────────────────────────────────── |
| `fast_api_voter/api/domain/election/workers_behavioral.py` | 904-904 | 3 | 2026-06-14 | 2026-06-18 | """Returns (sincere plurality winner or 'NOTA', nota_pct).""" |
| `fast_api_voter/api/domain/election/workers_behavioral.py` | 940-940 | 3 | 2026-06-14 | 2026-06-18 | # sincere approval: approve above voter mean |
| `fast_api_voter/api/domain/election/workers_playground.py` | 477-479 | 3 | 2026-06-14 | 2026-06-18 | # (b) Descriptive mirror over the MODELLED attribute space: does the |
| `voter-app/src/components/campaign/__tests__/CampaignTimeline.test.tsx` | 93-93 | 3 | 2026-06-23 | 2026-06-26 | // Confirmation appears. |
| `voter-app/src/components/playground/ParliamentCanvas.tsx` | 154-154 | 3 | 2026-06-11 | 2026-06-14 | // Party territories + instant voter re-attachment (local, live during drag). |
| `fast_api_voter/api/domain/simulations/helpers.py` | 1-6 | 2 | 2026-05-07 | 2026-05-09 | """ |
| `voter-app/src/components/playground/PlaygroundController.tsx` | 173-174 | 2 | 2026-06-25 | 2026-06-27 | // Project candidates onto the active dimension count so the math, the map and |
| `voter-app/src/components/playground/ReplayStage.tsx` | 7-10 | 2 | 2026-07-22 | 2026-07-25 | // ReplayStage — the "what is being counted right now" visual: one bar per |
| `voter-app/src/components/shared/__tests__/AbstentionPanel.test.tsx` | 8-9 | 2 | 2026-05-30 | 2026-06-02 | // Mock the typed openapi-fetch client; real react-query drives the state |
| `voter-app/src/hooks/useVoteReplay.ts` | 19-19 | 2 | 2026-07-22 | 2026-07-25 | // Base beat: counting drops one ballot per beat (fast); rounds/duels need reading. |
| `voter-app/src/lib/scorecard.test.ts` | 28-28 | 2 | 2026-06-12 | 2026-06-14 | // 3 voters, cycle: 0>1>2, 1>2>0, 2>0>1 |
| `voter-app/src/lib/scorecard.test.ts` | 39-39 | 2 | 2026-06-12 | 2026-06-14 | // Clear winner 1 (majority puts it above both others) |
| `voter-app/src/lib/scorecard.test.ts` | 53-53 | 2 | 2026-06-12 | 2026-06-14 | // Frontrunners by firsts: 0 and 2 (one first each + tie-break by order). |
| `voter-app/src/pages/__tests__/PlaygroundPage.test.tsx` | 96-96 | 2 | 2026-06-10 | 2026-06-13 | // Reset the module-singleton store to a known baseline between tests. |
| `voter-app/src/services/assemblyApi.ts` | 4-6 | 2 | 2026-06-11 | 2026-06-13 | // Lab reshape P3 — the party-level assembly endpoint. One shared electorate; |
| `fast_api_voter/api/routes/simulations.py` | 264-264 | 1 | 2026-05-30 | 2026-05-31 | # ── simulation_compare (Phase 4.5.a.7) ────────────────────────────────────── |
| `fast_api_voter/api/routes/simulations.py` | 323-323 | 1 | 2026-05-30 | 2026-05-31 | # ── simulation_advanced (Phase 4.5.a.8) ───────────────────────────────────── |
| `fast_api_voter/api/schemas/__init__.py` | 286-286 | 1 | 2026-05-30 | 2026-05-31 | # simulations whatif + campaign (Phase 4.5.a.6) |
| `voter-app/src/components/campaign/CampaignTimeline.tsx` | 129-129 | 1 | 2026-06-23 | 2026-06-24 | // Any move on the timeline invalidates the "pinned" confirmation. |
| `voter-app/src/lib/playgroundDynamics.ts` | 1-4 | 1 | 2026-06-11 | 2026-06-13 | // playgroundDynamics.ts — pure helpers for the playground's dynamic layer |
| `voter-app/src/lib/playgroundVoting.test.ts` | 246-246 | 1 | 2026-06-13 | 2026-06-14 | // A: grades [5,5,0] median 5; B: [4,4,4] median 4 but higher mean. |
| `voter-app/src/lib/playgroundVoting.ts` | 202-202 | 1 | 2026-06-11 | 2026-06-12 | /** Cardinal score in [0,1] per voter via min-max of -distance. */ |
| `voter-app/src/lib/playgroundVoting.ts` | 797-797 | 1 | 2026-06-11 | 2026-06-12 | // ── Public API ──────────────────────────────────────────────────────────────── |
| `voter-app/src/lib/playgroundVoting.ts` | 812-812 | 1 | 2026-06-13 | 2026-06-14 | // Cardinal rules — fall back to plurality if scores weren't supplied. |
| `voter-app/src/lib/playgroundVoting.ts` | 821-821 | 1 | 2026-06-13 | 2026-06-14 | // Ordinal rules. |
| `voter-app/src/lib/scorecard.ts` | 196-196 | 1 | 2026-06-12 | 2026-06-13 | /** Duverger-style compression probe: preferred frontrunner top, other bottom. */ |
| `voter-app/src/pages/__tests__/PlaygroundPage.test.tsx` | 7-7 | 1 | 2026-06-12 | 2026-06-13 | // NB: declared inside the factory — vi.mock is hoisted above file-level consts. |
