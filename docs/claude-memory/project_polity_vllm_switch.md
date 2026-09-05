---
name: project-polity-vllm-switch
description: "vLLM switch attempted live 2026-08-30 (PR #231) and blocked on a WSL2/Docker Desktop platform bug (UVA unavailable), not a config issue — provider stays 'ollama', dated reopening conditions in plan-vllm-switch-readiness.md"
metadata: 
  node_type: memory
  type: project
  originSessionId: 22458a2f-ddf0-45bc-bb54-2e029e1a45ce
  modified: 2026-08-30T12:50:25.063Z
---

**Update 2026-08-30 (PR #231, `plan-vllm-switch-readiness.md`)**: a GPU host became available and the vLLM switch was actually attempted live for the first time in this project — and blocked, before reaching any of the calibration questions below. `docker-compose.llm.yml` was pinned with real, API-verified values (`vllm/vllm-openai:v0.28.0`, `Qwen/Qwen3-8B-AWQ` at a specific HF commit SHA — AWQ chosen because bf16 `Qwen/Qwen3-8B` needs ~16GB for weights alone on this project's 16.3GB RTX 5070 Ti, leaving ~0 headroom for KV cache). The container fails at engine init with `RuntimeError: UVA is not available` (`vllm/v1/worker/gpu/buffer_utils.py`) — a confirmed **upstream vLLM bug specific to WSL2/Docker Desktop** (`vllm-project/vllm#43381`, `#47387`), not anything about this project's config. The fix (`#47579`) is unmerged as of 2026-08-30 (rebase-conflicted since 2026-08-08), so no released vLLM version has it. The one documented workaround (`VLLM_USE_V1=0`, forcing the legacy engine) had no effect — that version has likely already dropped the V0 fallback entirely.

**Decision**: `provider` stays `ollama`. Not a permanent renunciation — explicit, dated reopening conditions (same treatment as the sortition-chamber veto deferral): retest once `#47579` is merged **and published in a release** (not just merged to main), or if this project's execution environment ever moves to native Linux for an unrelated reason. Explicitly rejected: hunting an older pre-V2-default vLLM version (no signal on which one would work — refused as blind guessing), waiting on the unmerged fix (unmaintained external timeline), native Linux just for this (reopens an already-parked "don't change OS mid-investigation" question for unguaranteed gain).

**Also resolved this update**: the AWQ-vs-bf16 confound is real and separate from the platform blocker — switching to AWQ changes the model's own weights, not just the serving layer, so every reliability calibration this project has done (`_POSITIONING_THINK_TOKEN_ALLOWANCE`, `_VOTE_CAST_MAX_CHUNK_SIZE`, `_CHAMBER_MAX_CHUNK_SIZE`, the ranking-ambiguity and `chamber_position==sincere_position` prompt fixes) was measured against the un-quantized Ollama model and would need separate re-verification (axis b) even once the platform blocker (axis a) clears. Never reached axis (b) testing.

---

**Original context (PR #139, 2026-08-15)**: The v4 vLLM switch (design doc §15bis.6) was implemented and merged to `develop`. `llm_client.py` has `VllmJsonClient` alongside `OllamaJsonClient`, dispatched via `build_json_client(llm_config, ...)` in `run_polity_simulation._llm_client_scope`. `test_polity_vllm_live.py` (`POLITY_VLLM_LIVE=1`-gated, 8 tests) and `check_vllm_batching_determinism.py` were written then, never run until the 2026-08-30 attempt above — both still exist, complete, and remain the reference for whenever a vLLM backend actually starts.

Also see [[feedback_gh_pr_targets_develop]] for a repo-workflow gotcha hit while landing PR #139, and [[project_polity_branch_workflow]] for the current `polity → develop` merge trigger (settled 2026-08-30: after the full v0-v8 roadmap, not before).
