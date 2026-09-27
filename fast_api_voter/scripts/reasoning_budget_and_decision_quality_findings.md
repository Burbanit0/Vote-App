# Reasoning-budget exhaustion and unvalidated decision quality — a cross-cutting finding

Discovered 2026-08-20/21, GPU, during the v6b Lot 4 acceptance run's 8 relaunch attempts. Raised
by direct user challenge to stop reactively raising a token constant and instead ask two harder
questions: was the last time this exact failure category was "fixed" ever actually validated for
quality, not just crash-avoidance — and does this affect more than the one function currently on
fire? Both answers turned out to matter more than the acceptance run itself.

## What happened, in order

`cast_votes` (dt=1, `think=True`) failed live 3 times in a row, each after raising
`_VOTE_THINK_TOKEN_ALLOWANCE` in response to the previous failure: 4000 → 8000 → 12000. Every
failure was confirmed via `docker logs ollama-polity` to be genuine, deterministic budget
exhaustion — `n_ctx_slot=16384` throughout (not the already-fixed context-window bug), no
context-shift event, `truncated=0`, `n_decoded` landing within a few hundred tokens of whatever
`max_tokens` had just been set to. Three different chunks of content (different ticks), three
different ceilings, three exhaustions. No convergence.

At 12000, the request (`compute_max_tokens(3)+12000=13716`) was already within ~500 tokens of the
16384-token context ceiling given the observed ~2100-token prompt — raising it further risks
walking straight back into the *other*, already-fixed bug
(`ollama_context_window_results.md`'s context-shift corruption), trading one resolved problem for
a resurrected one.

## The two pre-existing failure-mode buckets, and why cast_votes doesn't fit either cleanly

This codebase already distinguishes two failure modes for `think=True` on subjective/comparative
prompts, documented in `decide_campaign_positioning`'s own docstring:

- **Mode A — "reasoning cannot rescue"** (`decide_party_nominations`, `ollama_structured_output_results.md`
  Finding E): `finish_reason='length'` regardless of batch size or token budget. The model's
  `<think>` block never converges on this prompt *shape* ("which of these candidates is the
  better choice?"), no matter how much room it's given. Fixed by switching to `think=False`.
- **Mode B — "budget was simply too tight"** (`decide_campaign_positioning` itself): a *different*
  bug under `think=False` (duplicate/drop degenerate batches, not truncation), and `think=True`
  with a **single, stable** widened budget (+8000) resolved it cleanly — 5/5, with real margin,
  no further escalation needed.

`cast_votes`'s new failures pattern-match Mode A's *symptom* (repeated exhaustion, no
convergence across three widening attempts) rather than Mode B's (one widen, clean resolution).
But Mode A's own fix — switch to `think=False` — was tested directly against `cast_votes` and
**failed decisively**: see below. `cast_votes` is a genuinely new, third case that doesn't fit
either bucket's established fix.

`decide_candidacies`'s own history adds a further wrinkle: its failing prompt ("should this
citizen run?") isn't a multi-item comparison at all, just a single citizen's own subjective
judgment — yet it triggered the identical unbounded-reasoning symptom under `think=True`. So the
trigger isn't cleanly "comparing multiple options" either; "comparative-judgment shape" is this
codebase's working label, not a confirmed mechanism.

## The `think=False` spike for `cast_votes` — a direct, conclusive test

Rather than assume Mode A's fix would transfer (the codebase's own `decide_campaign_positioning`
docstring already warns against doing exactly that: *"do not assume this result transfers back to
decide_party_nominations without its own live check"*), ran a bounded live spike: real production
config, real seed-42 population/parties, 5 realistic nominees (one per party, `declare_candidacy`'d
so `build_system_prompt`/`build_user_prompt` see valid platforms), 15 real voters across 5 chunks of
3, `think=False`, real `build_system_prompt`/`build_user_prompt`/`decode_vote_batch` — exactly the
production call, minus the `think` flag.

Every decoded ballot was checked against the **actual precomputed `weighted_distance`** from that
voter to every candidate (not just "did it decode cleanly"):

```
RESULT: 1/15 correct under think=False
```

Near-total collapse — mostly a fixed-looking non-distance-based ordering (`[2,1,3]`-shaped
patterns repeating across unrelated voters), the same "identity/near-uniform permutation
collapse" failure mode `cast_votes`'s own docstring already documents for `think=False` at larger
batch sizes (24/25 voters returning the literal position order `[1,2,3,4,5]`). `think=False` is
**not** a viable fix for `cast_votes` at any tested chunk size — switching would silently corrupt
every ballot cast under it, which is a materially worse outcome than the run currently aborting
loudly.

## The real finding: nothing else has ever been checked this way

Auditing every `think=False`-fixed decision type's own live test (`test_polity_llm_live.py`):

| Decision type | dt | `think` | Prompt shape | Live test checks |
|---|---|---|---|---|
| `vote_cast` | 1 | `True` | rank candidates by precomputed distance | **Quality-checked**: 5/5, 9/9 batches verified against real `weighted_distance` (historical); **just disproved under `think=False`**, 1/15 (this finding) |
| `candidacy_considered` | 2 | `False` | "should I run?" (self, subjective) | Structural only: cid alignment, valid motif |
| `party_nomination_choice` | 4 | `False` | "which of these should this party pick?" (comparative) | Structural only: cid alignment, in-range `winner_position`, valid motif |
| `campaign_positioning` | 5 | `True` | self-directed platform shift | Bound-respect only (`max_positioning_shifts`/`max_positioning_delta`), not strategic soundness |
| `representative_response` | 6 | `False` | self-directed reaction to pressure | Structural + bound-respect via `validate_response_decision`, not content quality |
| `pressure_action` | 10 | `False` | self-directed act choice from a menu | Structural + menu-legality only |
| `reaction_to_event` | 8 | `False` | self-directed reaction to a shock | Structural only |
| `chamber_deliberation` | 11 | `True` | self-directed deliberation | Structural only |
| `coalition_decision` | — | `False` | "do you join THIS coalition?" (comparative), **own docstring**: *"flagged for live verification rather than assumed"* | Structural only: `action in {1,2}`, valid motif |

**Every decision type except `vote_cast` has *no* checkable ground truth at all** — "should this
citizen run," "which nominee is best," "do you join this coalition" are not quantities with a
computable correct answer the way `weighted_distance` gives `vote_cast`. That isn't a gap anyone
overlooked; there is genuinely nothing to check most of these against. But it also means: **we
have zero evidence that `think=False` produces sound decisions for any of them** — only that it
produces *structurally valid* ones. `vote_cast` is the one case where a ground truth existed, and
the moment it was checked, `think=False` failed catastrophically. Whether the same silent
corruption is happening under `think=False` for `party_nomination_choice`, `pressure_action`,
`reaction_to_event`, `coalition_decision`, etc. is now a genuinely open question this project has
never had the means to answer — not a reassured "probably fine."

## Is there a middle ground between `think=True`/`False`?

Checked directly: no. Ollama's OpenAI-compat and native endpoints both expose exactly one
`max_tokens` ceiling covering the whole completion (`<think>` block plus the visible answer) —
there is no separate "thinking budget" parameter the way Anthropic's extended thinking exposes
`budget_tokens`. A "budget-forcing" technique exists in the research literature (inject a closing
`</think>` after N reasoning tokens to force the model to commit to an answer even mid-thought) but
is not implemented anywhere in this codebase (`llm_client.py` sends one request, gets one
response) and would be new, unvalidated engineering — a real option for a future palier, not
something available today.

## Consequence for `cast_votes` specifically — RESOLVED: `_VOTE_CAST_MAX_CHUNK_SIZE` reduced 3 → 1

Neither established fix worked: `think=True` didn't converge on some (unpredictable) fraction of
real chunks regardless of budget, up to nearly the full context ceiling; `think=False` corrupted
every ballot (see the spike above, 1/15 correct). Per explicit instruction, chunk-size reduction was
tested empirically before assuming it wouldn't help (it was expected to be insufficient, since the
dominant cost was thought to be the flat `_VOTE_THINK_TOKEN_ALLOWANCE`, not the per-voter addend in
`compute_max_tokens`).

Live spike (2026-08-21, GPU, `think=True`, the same 12000-token allowance, real production
population/prompts, 8 chunks per size, checked for a clean decode only — not re-validated against
`weighted_distance` ground truth, since `think=True` was already quality-proven at small batch sizes
by the historical 5/5, 9/9 findings this doc's own inventory cites):

```
chunk_size=1: 8/8 clean
chunk_size=2: 7/8 clean (1 failure, finish_reason='length', 143.3s to fail — a real, expensive
              budget exhaustion, not a fluke)
```

Reducing chunk size *does* reduce the reasoning-token appetite, just not primarily through the flat
60-token/voter addend `compute_max_tokens` adds on top of the allowance — fewer voters per call
measurably reduces how much the model has to reason about per call. This directly contradicts the
pre-test expectation, which is exactly why the user asked for the empirical test rather than
accepting the calculation-based assumption.

**Shipped**: `_VOTE_CAST_MAX_CHUNK_SIZE = 1` (`llm_behavior_engine.py`), with the full escalation
history and this finding documented inline. Cost: roughly 3× the number of `cast_votes` calls per
election (95 voters/election at 1-per-call vs. `ceil(95/3)=32` at 3-per-call), forecast at ~+29 min
added to a 3-election, 8-year acceptance run (~4h baseline) — not the dominant cost driver
(`chamber_deliberation`/`pressure_action`'s own per-tick call volume is), and likely an overestimate
since it assumes chunk_size=3 would have completed cleanly instead of repeatedly failing and burning
replay attempts. Tests, mypy, flake8 all green (see commit).

## Next priority: think=False decision-quality validation workstream (separate branch, not yet started)

This is the single most important finding of this investigation, independent of the `cast_votes`
blocker above: **decision quality under `think=False` has never been validated against any ground
truth for 6 of 7 non-`vote_cast` LLM decision types** (`candidacy_considered`,
`party_nomination_choice`, `representative_response`, `pressure_action`, `reaction_to_event`,
`coalition_decision` — see the inventory table above; `campaign_positioning`/`chamber_deliberation`
run `think=True` and are likewise unvalidated for quality beyond bound-respect). Every one of them
has only ever been checked for *structural* validity (cid alignment, in-range values, valid motif) —
never for whether the decision itself is sound. The only decision type ever checked against ground
truth is `vote_cast`, and the moment it was checked under `think=False` here, it failed
catastrophically (1/15 correct) — a materially worse outcome than the loud failure it would have
replaced. Whether the same silent corruption is happening under `think=False` for the other six
decision types is a genuinely open question this project has never had the means to answer.

This is a real methodological gap touching the simulation's fundamental validity, not a side note,
and should be opened as its own workstream — **new branch, not mixed with the `cast_votes` fix** —
once the current acceptance run (all of today's fixes: bug 1-4, `chamber_deliberation`'s think
budget, `cast_votes`'s chunk size, `cast_votes`'s temperature-varied-retry mitigation) completes
successfully. Scope: for each of the six decision types, build a quality probe analogous to this
session's `vote_cast` spike wherever a ground-truth or near-ground-truth signal can be constructed —
e.g. `party_nomination_choice` against `sympathizer_ratio`; `pressure_action` against menu-legal,
gap-consistent choices; `coalition_decision` against basic seat-majority rational-actor consistency —
run it once, live, per decision type, rather than rediscovering this gap piecemeal over the coming
weeks the way it was found here only by accident of `vote_cast` having a ground truth available.

**Added to scope (2026-08-22)**: the `cast_votes` schema-incoherence bug investigated in
`cache_recycle_chunk_size_tension_findings.md` (a deterministic, per-voter `blank=1`+non-empty-
`ranking` incoherence under `think=True`, mitigated with a local temperature-varied retry rather than
root-caused) is a concrete, well-documented instance of this same broader gap — a decision-quality
failure that happened to be *caught* only because `VoteCastDecision` has a cross-field coherence rule
Pydantic can enforce post-hoc, exactly the "which other decisions lack a hard rule able to catch this
type of corruption" question this workstream already names below. This case is not investigated
separately; whoever opens this workstream should start from it as a worked example (the exact error
text, the ground-truth reconstruction methodology used to confirm it wasn't a defensible edge case,
and the mitigation's own honest limits — it treats the symptom via retry, not the cause) rather than
re-deriving the same investigation from scratch.

Also flag for this workstream's own scope: **"which other decisions lack a hard rule able to catch
this type of corruption"** — `VoteCastDecision`'s blank/ranking rule caught this case only by
validation luck (a coherence rule happened to already exist for unrelated reasons), not by
generalized design. Auditing every schema for missing cross-field coherence rules that *could* exist
but don't (the same audit style as the inventory table above, but for structural incoherence rather
than semantic soundness) belongs in this workstream's own scope, not as a separate effort.

A `/log-session` entry covering this whole investigation (budget-exhaustion bugs + the
quality-validation gap discovery + the cast_votes schema-incoherence bug and its mitigation) is due
once the current acceptance run's own outcome is known, not before.
