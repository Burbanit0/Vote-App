---
name: feedback-llm-reliability-investigation
description: "User wants thorough root-cause investigation of LLM decision-quality bugs (not just retries), and treats abstention/blank as a last resort a citizen falls back to, not a default choice"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 9988b0af-d35f-4d22-b8d0-3ab9d9b157f8
  modified: 2026-08-14T23:14:12.703Z
---

When a polity LLM decision type produces suspicious, too-uniform output (e.g. 100% blank votes across an entire electorate), the user wants a full root-cause investigation rather than a quick mitigation (bumping replay counts, shortening timeouts) — even if it costs significant additional time. Confirmed explicitly during the v4 Lot 8 acceptance run: `cast_votes` was producing 100% blank presidential ballots at full production scale, and the user chose "full investigation" over "accept as a genuine finding" or "stop chasing LLM issues."

**Why:** The user's own framing: "voted blank should be more a last option than a real opinion... currently it represents a few part of the population opinion, a citizen admits that the candidate is not perfect for him but close enough to his idea so he will vote for him." This is a substantive modeling opinion, not just a bug-tolerance preference — blank/abstention in this simulation should be reserved for when literally no candidate is tolerable, never a default fallback when the model is uncertain or the arithmetic is hard.

**How to apply:** When an LLM decision type in this codebase produces implausibly uniform or extreme output at real scale, investigate whether the model is being asked to do arithmetic/judgment it can't reliably perform (e.g. weighted-euclidean distance across 20 raw dimensions) rather than being handed a precomputed value. The fix pattern that worked and was well-received: precompute the same quantity the deterministic baseline already uses (e.g. `simple_rules.weighted_distance`), hand it to the model as a plain number, and give it an explicit, mechanical rule for what to do with it — mirroring the project's own existing precedent of precomputing `self_gap`/`mandate_dev` for dt=10 rather than asking the model to derive them from raw vectors. Also: the user explicitly wants `think=True` kept once it fixes a different reliability issue (it resolved a separate degenerate-output bug in `decide_campaign_positioning`) — don't revert to `think=False` as a shortcut even if `think=True` has its own quirks (occasional slow calls); solve those with token budget or prompt clarity, not by reverting.

See [[project_polity_v4_lot8_llm_reliability]] for the concrete bugs and fixes this produced.
