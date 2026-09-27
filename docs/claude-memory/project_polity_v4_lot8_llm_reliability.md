---
name: project-polity-v4-lot8-llm-reliability
description: "v4 palier of the polity simulator is complete (merged develop via PR #138); two LLM decision-quality bugs were found only at real production scale and are documented as a pattern to watch for in future lots"
metadata: 
  node_type: memory
  type: project
  originSessionId: 9988b0af-d35f-4d22-b8d0-3ab9d9b157f8
  modified: 2026-08-14T23:14:26.685Z
---

The polity v4 roadmap (8 lots, `merry-hugging-hamming.md`) is complete as of 2026-08-14 — PR #138 merged Lot 8 (acceptance) into `develop`. There is no Lot 9; the design doc's own §13 names v5 (exogenous events) as the next palier, with the vLLM switch and §16.6 storage named as worthwhile pre-v5 items.

**Why this matters going forward:** Lot 8's actual acceptance sweep (100 citizens, 20 issue dimensions, real candidate diversity, 8-year runs) surfaced two LLM reliability bugs that had been invisible through every prior lot's own pre-flight reliability spikes, because those spikes only checked schema validity/alignment (does the batch decode, do the cids match), never output *content quality* (are the decisions plausible/diverse).

1. `decide_campaign_positioning` (`think=False`) produced a 100%-reproducible degenerate batch (one nominee duplicated, rest dropped) for a real recurring nominee combination. Fixed with `think=True` + a larger measured token budget.
2. `cast_votes` produced 100% blank presidential ballots — every voter, every election, every arm — reproduced at the raw model-response level. Root cause: the model was asked to judge candidate acceptability from raw 20-dim vectors with no worked definition, the same weighted-distance-vs-threshold arithmetic the deterministic path computes exactly. Fixed by precomputing the distance and handing it to the model, plus adding `VoteMotif.ACCEPTABLE_MATCH` (105) since no existing motif described a sincere vote for an imperfect-but-tolerable candidate.

**How to apply:** Before trusting any future lot's LLM decision type at full population scale, consider whether its pre-flight spike ever checked output *diversity*, not just schema validity — a spike that only confirms "the batch decodes and cids align" can still hide a decision type that always answers the same degenerate thing. If a future lot (v5+) adds a new LLM decision type, budget time for a live smoke check at real population scale before treating the reliability spike as sufficient. See [[feedback_llm_reliability_investigation]] for how the user wants this kind of issue handled when found.

Also recurring in this environment: Docker Desktop and the `ollama-polity` container stop across session/context boundaries. Recovery: `Start-Process 'C:\Program Files\Docker\Docker\Docker Desktop.exe'`, wait for `docker ps` to succeed, then `docker start ollama-polity` (the `qwen3:8b` model persists in the container, no re-pull needed).
