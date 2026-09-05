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

## Workstream update, 2026-08-30 — a new failure mode found opening this workstream: single-citizen-batch `think=True` collapses to a fixed default for `pressure_action`

The workstream this document scoped above was finally opened
(`plan-decision-quality-validation.md`) after 6 days untouched. Its `pressure_action` pilot
(`check_pressure_action_quality_pilot.py`, Group A method — compare the LLM decision against
`deterministic_pressure_action` on the same real inputs) found a 25.0% disagreement rate on
unambiguous cases (10/40), concentrated in 4 of 25 distinct consulted citizens, each disagreeing
*stably* across multiple ticks (not flickering). Chasing why led to a follow-up probe
(`check_pressure_action_forced_reasoning.py`): re-ask the same 4 citizens' real captured context
(confirmed via the journal — no `petition_launched`/`signed`/`expired` event exists anywhere in
the pilot run, so `petition_open=already_signed=False` is a verified fact, not an assumption) with
`think=True` forced, one citizen per call (chunk_size=1) — a call shape `decide_pressure_actions`
has **never used in production** (it always runs `think=False`, batched up to
`config.llm.max_batch_size`).

**Result, itself a new finding, not an answer to the original question**: zero `<think>` content
in any of the 4 responses (unlike `vote_cast`, also `think=True` on this same OpenAI-compat
endpoint, whose reasoning shows up inline and needs `_THINK_TAG_RE` stripping before every decode
— so this isn't a script blind spot, the model produced none here), and all 4 calls converged to
the **identical** `act=4 (WAIT_FOR_ELECTION), motif=305`, despite `self_gap` ranging from 0.145 to
0.328 and the original (`think=False`) decisions splitting between NOTHING and MOBILIZE. Same
"identical output regardless of input" signature this document's own `cast_votes` `think=False`
spike found (§ above, 24/25 voters returning the literal position order) — but for a completely
different call configuration.

**Explicit caveat, so this isn't mistaken for an active risk**: single-citizen-batch `think=True`
is not a configuration this project runs anywhere in production for `pressure_action` — the
collapse found here says nothing about the real, shipped `think=False`/batched behavior this
decision type actually uses. It is a new, real, catalogued failure mode (same register as Mode
A/B) for a hypothetical configuration, not a bug affecting any current run. Recorded here so it
isn't rediscovered from scratch if `pressure_action` is ever considered for `think=True`, or if
single-citizen batching is ever proposed for it.

**Update, 2026-08-30 (`check_candidacy_forced_reasoning_comparison.py`)**: the single-citizen-
batch `think=True` collapse documented above is **not specific to `pressure_action`**. The same
mechanism forced onto `candidacy_considered` (a decision type that does NOT collapse under its
own real `think=False` production path -- `check_candidacy_considered_isolation_disposition.py`,
5/5 correct) produced the identical signature: zero visible `<think>` content across all 8 test
citizens (5 extreme low-ambition + 3 extreme high-ambition, both poles, correcting a first draft
of this script that tested only the low-ambition citizens and could not have distinguished a real
collapse from "correct because every test citizen shares the same true answer" -- caught and
fixed before drawing a conclusion), and all 8 collapsed to the identical `outcome=0`
(decline)/`motif=204` -- including the 3 high-ambition citizens who should have declared. **This
weakens, not strengthens, any link between the think=True reasoning-suppression finding and the
act/response framing theory characterized in `plan-adversarial-framing-collapse.md`.** If a
decision type that is otherwise immune to the relational-framing collapse shows the identical
total reasoning suppression under this specific, never-used-in-production call shape
(single-citizen batch, `think=True`), the suppression looks like a general property of that call
configuration itself -- plausibly something about how this backend's reasoning trigger behaves on
an extremely small, simple single-item prompt -- not a symptom of, or evidence for, the
relational/act-response mechanism. Kept as its own catalogued finding (same register as the
original), explicitly cross-referenced now rather than left implicitly connected.

**Neither finding (the 25% rate, nor the collapse) settles the original question** of whether the
4 citizens' `think=False` divergence reflects genuine information the coarse proxy lacks, or a
real content-quality gap. Both investigative avenues (richer context-field inspection; forced
reasoning) are now spent without resolving it. Next: extend the pilot's sample (population_size
scaled ~2.5-3x, same duration) to see whether the concentration pattern (a small, stable subset of
citizens diverging) recurs with *different* individuals of a similar profile at a larger scale —
which would support "stable disposition the proxy misses" over "random noise" — without re-opening
either exhausted qualitative avenue.

## Workstream update, 2026-08-30 (cont.) — extended pilot: pre-registered criterion triggers "method has a problem" — `pressure_action` has a real, directional bias

The extended pilot (`population_size=280`, ~2.8x the original 100, same 4-year duration,
`--max-batch-replays 2`) ran to completion: 313 total LLM `pressure_action` decisions across 66
distinct consulted citizens, 108 unambiguous cases across 24 distinct citizens.

```
agreement rate on unambiguous cases: 58.3% (63/108)
disagreement rate: 41.7% (45/108)
concentration: 45 disagreements among 14/24 distinct unambiguous citizens (58.3%)
```

This is not a tightening of the first pilot's 25.0% estimate around a stable center — it is a
**shift past the pre-registered "problem" boundary**
(`plan-decision-quality-validation.md`'s own criterion: `>~20-25%` disagreement, or a collapse
signature, means "method has a problem, stop, investigate before building anything else"; `10-
20-25%` is the grey zone the first pilot's 25.0% sat at the edge of). Doubling-plus the sample did
not confirm the first pilot's rate as a stable estimate — it revealed the first pilot's 25.0% was
itself a small-sample underestimate. Per the criterion written before either pilot ran, this
result is read as **confirmed problem, not sample-size noise and not a second grey-zone
reading** — the same discipline this week's ~50% stationarity test and the first pilot's own
25.0% were both given, applied here to its actual conclusion rather than softened because the
number is inconvenient.

The concentration signal named as the thing to watch for at scale reproduced and sharpened: 58.3%
of distinct unambiguous citizens disagree at least once (up from 4/25=16% in the first pilot), and
within this run each disagreeing citizen is stable across ticks (near-identical `gap`/
`blank_threshold`, same disagreement, recurring at ticks 0/1/2/3/16) — not tick-to-tick flicker.

**The directional signal is the more important finding of the two.** 42 of 45 disagreements
(93%) share the identical shape: the deterministic proxy says NOTHING (`gap` comfortably under
the citizen's own `blank_threshold`, ratio<0.5), and the LLM picks MOBILIZE anyway. Only 3
disagreements (all at tick=1: cid=87, 146, 152) run the other direction. A near-total one-way
skew on a stable subgroup is not the signature "the model uses richer information than the
proxy" would produce — that would predict disagreements scattered in both directions depending on
each citizen's specific context, not a 93%-one-way asymmetry. It instead reads as a structural
propensity toward MOBILIZE over NOTHING for this citizen class, independent of the actual content
of their situation — a shape-level bias, not evidence of the LLM seeing something the proxy
misses.

**Consequence, per the pre-registered criterion**: the six remaining Group A/B/C probes
(`candidacy_considered`, `party_nomination_choice`, `coalition_decision`,
`campaign_positioning`, `representative_response`, `reaction_to_event`, `chamber_deliberation` —
`plan-decision-quality-validation.md` §1) stay paused. Building them on top of an unresolved,
confirmed directional bias in the one decision type already checked would risk the same mistake
this whole workstream exists to avoid repeating: trusting "structurally valid" output as a proxy
for "sound" output. Understanding this `pressure_action` bias is now the workstream's own
priority, not a checkbox on the way to the other six.

## Workstream update, 2026-08-30 (cont. 2) — root mechanism identified: chunk-level output collapse, not a per-citizen disposition, and an ACTIVE production risk (not hypothetical like the `think=True` collapse above)

Before treating the 93%-directional reading above as the conclusion, checked what the 14
disagreeing citizens' actual journaled *batches* looked like — not their own `self_gap`/
`blank_threshold` (already ruled out as explanatory) but their position within the real HTTP call
that produced their decision. `chunk_voters` (`llm_behavior_engine.py:587-627`) is a pure,
deterministic function: near-equal chunks by ascending `citizen_id`,
`num_chunks=ceil(n/max_batch_size)`, sizes differing by at most 1 — and
`config.llm.max_batch_size=25` (`polity_config.yaml:424`, unchanged shipped default) is what
`decide_pressure_actions` passes it (`llm_behavior_engine.py:1903`). Reconstructing the chunk
boundaries this predicts against the extended pilot's own journal and checking every citizen in
each chunk, not just the 14 flagged ones:

At tick=1 (target=5, 63 consulted → chunks of exactly 21/21/21, cid ranges [6..84]/[87..171]/
[172..279], matching `chunk_voters`'s predicted boundaries exactly): **every one of the 21
citizens in the first chunk got `act=3` (MOBILIZE); every one of the 21 in the second chunk got
`act=0` (NOTHING); every one of the 21 in the third chunk got `act=3` again** — regardless of each
citizen's own `self_gap`, which spans 0.086 to 0.512 within the second chunk alone, comfortably
crossing both sides of every one of those citizens' own `blank_threshold`. At tick=0 (65
consulted → chunks of 22/22/21) and ticks 2/3 (60 consulted → chunks of 20/20/20), all chunks
independently landed on unanimous MOBILIZE — consistent with the same mechanism, just invisible as
a "split" because every chunk in those calls happened to collapse the same way.

**This reframes the directional-bias finding above, it doesn't just add to it.** The "14 distinct
citizens, 93% one direction" result is not a stable per-citizen disposition the coarse proxy
misses, and not a general model-wide preference for MOBILIZE — it is the visible remainder of
whole chunks collapsing to one uniform act, with the flagged citizens being simply whichever
chunk members' own gap/threshold ratio happened to disagree with whatever their chunk landed on.
The 93% skew reflects that in this run's four sampled ticks, 3 of them collapsed every chunk
toward MOBILIZE and 1 produced a mixed outcome (2 MOBILIZE-chunks, 1 NOTHING-chunk) — a small,
essentially arbitrary sample of chunk-level outcomes, not a property of the citizens themselves.

**Why this is materially more serious than the single-citizen-batch `think=True` collapse
documented in the update above**: that one was explicitly not a production risk. This one runs on
the exact shipped path — `decide_pressure_actions`'s real production call, `think=False`,
`max_batch_size=25` unchanged from default — and triggers automatically the moment a consulted
cohort exceeds 25 citizens in a single tick, which any population past pilot scale reaches
routinely. In practice: for most citizens in a normal-sized run, their journaled `pressure_action`
decision is not really "this citizen's own choice given their own `gap`" — it is their chunk's
collapsed answer, individual variation discarded.

**Not yet directly proven, flagged for whoever picks this up next**: whether this is the same
failure shape `cast_votes`'s own docstring already names ("identity/near-uniform permutation
collapse … at larger batch sizes") recurring on a different schema, or a distinct mechanism
specific to `PressureDecision`'s prompt/schema shape. Also untested: whether re-running the same
chunk with citizens reordered changes which act it collapses to (would confirm a position/order
artifact over any content-driven convergence) — the cheapest next confirmatory step, not yet run.

**Consequence**: supersedes the "structural propensity toward MOBILIZE … independent of content"
reading two sections above — that description undersold the mechanism once chunk boundaries were
checked against the real journal. The six remaining probes stay paused (unchanged). The priority
for `pressure_action` itself shifts from "characterize a per-citizen bias" to "this decision
type's batched `think=False` path silently collapses per-citizen judgment to a chunk-uniform
default at the exact batch size shipped to production" — a finding about the simulation's
production behavior today, not a hypothetical configuration.

## Workstream update, 2026-08-30 (cont. 3) — order-permutation test: collapse is NOT a position artifact; checked candidacy_considered/party_nomination_choice for the same pattern (not found)

Two follow-ups, run before writing anything further, per direct instruction — these are the
questions that decide whether this is a reparable position bug or something deeper.

**1. Order-permutation test** (`check_pressure_action_chunk_reorder.py`, new, committed). Took the
real 21-citizen chunk documented above (tick=1, target=5, cid 87..171, `self_gap` 0.086-0.512,
collapsed to uniform `act=0`/NOTHING/motif=305 in production) and re-issued the identical call —
same `think=False`, same ctx per citizen, same verified petition state — with the 21 citizens
serialized in two independently shuffled orders (fixed seeds, reproducible). If the collapse were
a position/boundary artifact of `chunk_voters`'s ascending-`citizen_id` ordering (the same family
as the already-fixed chunk-size bugs), reordering should produce a *different* uniform answer, or
a split following the *new* position boundaries.

It did not. **Both shuffles collapsed again to the identical `act=0`/NOTHING for the near-totality
of the chunk** (21/21 in shuffle #2; 20/21 in shuffle #1), regardless of `self_gap` still spanning
the full 0.086-0.512 range and regardless of each citizen's new position in the list. This rules
out a simple positional-boundary story: two different serializations of the same 21 citizens
still land on the same answer for (essentially) everyone.

One citizen (cid=171, the single highest `self_gap` in the chunk, 0.5115) escaped the collapse in
shuffle #1 (`act=4`/WAIT_FOR_ELECTION, at position 16/20) but **did not** escape in shuffle #2
(same citizen, same `self_gap`, position 7/20, got `act=0` like everyone else). The script's own
first-draft verdict logic wrongly reported this as "escaped in both shuffles" (a set-union bug,
not an intersection) — caught and fixed before reporting, not left as the record. The corrected,
honest read: this single escape is **not reproducible** across the two trials, so it does not
support either "content-sensitivity at the tail" or "a position rule" — the more likely
explanation is ordinary batch-call stochastic variance, already documented elsewhere in this
project as present even at temperature=0 under batching (design doc point #20's own live
measurement). The escape is noise; the robust, reproduced-twice result is the near-total collapse
itself.

**Verdict on the pre-registered question**: closer to "content-driven collapse" than "position
artifact" — but not in the sense of the model correctly reading the batch's aggregate content.
Two different orderings of the identical 21 citizens both produced (essentially) one answer for
the whole batch, ignoring individual `self_gap` variance that spans both sides of every citizen's
own threshold. This looks like a batch-scale degenerate-output pattern at the `pressure_action`
schema/prompt shape — a new, distinct instance of the same *family* `cast_votes`'s own docstring
already names ("identity/near-uniform … collapse … at larger batch sizes"), not a proven
instance of the *same* mechanism, and not (on this evidence) the prompt-cache-reuse mechanism
specifically — that comparison is plausible but untested here, not established.

**2. Existing-journal check for `candidacy_considered`/`party_nomination_choice`** (Group A, ground
truth already available, read-only — no new live calls). `party_nomination_choice` structurally
cannot show this pattern: `decide_party_nominations`'s own docstring confirms it never chunks
(batches by *contested party*, "a handful at most," never by citizen) — the mechanism has nothing
to apply to. `candidacy_considered` *does* chunk the same way (`chunk_voters(citizens,
config.llm.max_batch_size)`, same `llm_behavior_engine.py:1056`) and the extended pilot's own
journal already has 280-citizen runs of it (tick=0 and tick=16, `llm.enabled=True` throughout the
pilot). Checked all 12 predicted chunks (sizes 23-24) at tick=0 against each citizen's
`ambition_score` (regenerated via `generate_population`, same seed): **every chunk contains both
outcomes** (declare/don't-declare), and the split tracks content cleanly — mean `ambition_score`
0.273 for declared vs. 0.149 for non-declared. No collapse found here.

**Consequence**: the chunk-collapse finding does **not** generalize to "every batched
`think=False` decision type" on the evidence gathered so far — it is reproduced twice for
`pressure_action`, absent (checked, not just unchecked) for `candidacy_considered`, and
structurally inapplicable to `party_nomination_choice`. Scope stays `pressure_action`-specific
until/unless another chunking decision type (none currently exist besides these three plus
`cast_votes`, which already has its own separate, already-mitigated collapse finding) shows the
same pattern. The other 6 probes remain paused; nothing in production has been touched.

## Workstream update, 2026-08-30 (cont. 4) — chunk-size reduction does NOT cleanly fix this the way it fixed `cast_votes`: a different, stranger degenerate pattern appears instead

Following the same precedent that resolved `cast_votes`'s own collapse (chunk size reduced,
tested empirically, 8/8 clean at size 1 — see the earlier section above), tested whether
shrinking batch size restores per-citizen content-sensitivity for `pressure_action`
(`check_pressure_action_chunk_size_sensitivity.py`, new, committed). Took the same 21 citizens,
same real ctx, same ascending-`citizen_id` order as the collapsed chunk documented above, and
re-issued them as 7 sub-batches of 3 — a size `lot6_batch_reliability_results.md` already
measured clean for this exact schema shape.

**Within-subbatch uniformity mostly broke**: only 1 of 7 sub-batches was still internally uniform
(all 3 citizens identical), versus near-total uniformity at size 21/25. On that axis alone, this
looks like support for a size-dependent, reparable collapse.

**But the actual outputs reveal a different, more specific problem.** Across all 21 citizens and
7 calls, **not a single decision chose an acting code** (`SIGN_PETITION`/`LAUNCH_PETITION`/
`MOBILIZE`, codes 1/2/3) — every output was either `NOTHING` (0) or `WAIT_FOR_ELECTION` (4). The
apparent "variation" is the model oscillating between two *non-acting* answers per citizen, not
tracking whether each citizen's own `gap`/`blank_threshold` calls for action. All 3 of this
group's unambiguous "should-act" citizens (cid=87 ratio=2.28, cid=146 ratio=2.40, cid=152
ratio=3.25 — each comfortably over the 1.5 threshold) got a non-acting output anyway.
Unambiguous accuracy on this batch at size=3: **1/4 (25.0%)** (cid=158, the one "should-NOT-act"
case, agreed) — worse than the extended pilot's own 58.3% baseline, though this is a single N=4
draw and should not be read as a rate estimate.

**This does not fit the `cast_votes` precedent cleanly.** `cast_votes`'s chunk-size fix restored
*correct*, ground-truth-verified behavior (8/8 clean, individually checked). Here, shrinking the
batch changed *which* degenerate pattern appears — uniform-collapse-across-the-whole-chunk became
oscillation-between-two-non-acting-codes-across-the-whole-chunk — without restoring the thing
that actually matters: ever choosing to act when a citizen's own signal calls for it. Whether
this specific chunk (a genuinely unusual composition — of 21 citizens, only 4 are unambiguous and
3 of those 4 call for ACT, an atypically action-heavy mix) or `_SUB_BATCH_SIZE=3` specifically
drove this is not yet disentangled — single trial, one chunk, one size.

**Truncation ruled out, not just judged unlikely.** `_extract_native_content`
(`llm_client.py:678-699` — the `think=False` native-endpoint path `pressure_action` actually
uses) raises `LlmResponseError` immediately whenever Ollama's `done_reason != "stop"`; it cannot
return content otherwise. `check_pressure_action_chunk_size_sensitivity.py` completed all 7
sub-batch calls with zero errors and zero replays — structurally impossible if any call had
truncated. Corroborated against `docker logs ollama-polity` for the run's time window: no
truncation/context-limit signal present. The `NOTHING`/`WAIT_FOR_ELECTION`-only pattern is a real
decision the model made, not a budget artifact in disguise.

**Still open**: whether a different chunk (not this one, which happens to be unusually
action-favoring per the proxy — 3 of its 4 unambiguous citizens call for ACT) shows the same
acting-code avoidance at size=3, or whether this is an artifact of this one chunk's atypical
composition; whether an intermediate size (5, 10) sits between "uniform collapse" and "avoids
acting codes entirely" or jumps straight from one degenerate pattern to the other — deliberately
sequenced after the chunk-generality question, since a full size curve (3/5/10/21) built on an
unconfirmed single-chunk artifact would risk producing a curve that describes nothing real.

## Workstream update, 2026-08-30 (cont. 5) — truncation ruled out structurally; acting-code avoidance at size=3 confirmed to generalize across 3 chunks, both collapse polarities

**Truncation check (log-reading only, no new live calls needed)**: see the ruled-out note folded
into the section above — `_extract_native_content` hard-fails on any non-`"stop"` `done_reason`,
and the size-3 script completed all 7 calls with zero errors/replays, which is only possible if
every call finished cleanly. Confirmed, not inferred.

**Generality check** (`check_pressure_action_chunk_generality.py`, new, committed): tested two
more real chunks from the same tick=1/target=5 batch, both chosen for a *different* proxy mix
than the first chunk tested, and — critically — both **originally uniform `act=3`/MOBILIZE** at
production size (21-24), the opposite collapse polarity from the first chunk's uniform NOTHING:

```
chunk1 (cid 6..84, balanced 4-ACT/4-NOTHING proxy mix):  0/21 acting codes at size=3, accuracy 4/8 (50.0%)
chunk3 (cid 172..279, 6-ACT/3-NOTHING proxy mix):        0/21 acting codes at size=3, accuracy 3/9 (33.3%)
```

**Zero acting codes (`SIGN_PETITION`/`LAUNCH_PETITION`/`MOBILIZE`) across all 3 chunks tested at
size=3 — 63 citizens, 21 live calls total** — regardless of each chunk's proxy composition and
regardless of which direction it originally collapsed at production size. This rules out "the
first chunk's result was an artifact of its atypical action-heavy composition": two chunks whose
*production-size* behavior was uniform MOBILIZE still produce zero acting-code decisions once
split into batches of 3. **The acting-code avoidance at `_SUB_BATCH_SIZE=3` is now a
3-for-3-reproduced pattern, not a single-chunk artifact.** Accuracy on the small unambiguous
subsets stayed in the same weak range as the first chunk (50.0%, 33.3%, vs. the first chunk's
25.0%) — all well under the pre-registered ≥90% validation bar, all pulled down specifically by
never choosing to act when the proxy calls for it.

**Reframes the "reparable the same way `cast_votes` was" question further**: `cast_votes`'s own
chunk-size fix (25→1) restored genuinely correct, ground-truth-verified behavior. Here, chunk
size seems to control *which* degenerate mode `pressure_action` falls into — large batches
collapse to one uniform answer (act or no-act, seemingly whichever the batch "decides" as a
whole); small batches (size 3) avoid the acting half of the menu entirely, independent of
individual content, while still varying between the two non-acting codes. Neither size regime
observed so far tracks each citizen's own `gap`/`blank_threshold` signal correctly.

**Next, per the pre-agreed order**: now that generality is confirmed (not just the first chunk),
proceed to intermediate sizes (5, 10) to see whether they sit between the two degenerate modes,
transition sharply at some threshold, or show a third pattern.

## Workstream update, 2026-08-30 (cont. 6) — the size curve is a sharp two-state pattern, not a gradient: acting codes appear ONLY at production chunk size, nowhere below it

`check_pressure_action_chunk_size_curve.py` (new, committed) ran all 3 chunks at both remaining
sizes (5, 10), using `chunk_voters` itself — the real production chunking function — so
boundaries match what an actual reduced `max_batch_size` would produce, not an ad hoc split.

```
                size=3   size=5   size=10   size=21-24 (production)
chunk2 (87..171)  0/21     0/21     0/21     uniform NOTHING (all 21)
chunk1 (6..84)    0/21     0/21     0/21     uniform MOBILIZE (all 21)
chunk3 (172..279) 0/21     0/21     0/21     uniform MOBILIZE (all 21)
```

**Zero acting codes (`SIGN`/`LAUNCH`/`MOBILIZE`) at every size tested below production scale** —
3, 5, and 10 alike, 3 chunks each, 189 individual decisions total, none of them an acting code.
Unambiguous accuracy stayed essentially flat across 3/5/10 within each chunk (chunk2: 25.0% at
all three sizes; chunk1: 50.0% at all three; chunk3: 33.3% at all three) — changing the sub-size
within this range changes almost nothing. Acting codes appear **only** at the full production
size (21-25, `config.llm.max_batch_size`), and there only as a chunk-uniform collapse, not
tracking individual citizens.

**This is a sharp two-state pattern, not a gradient**, and it settles the "reparable the way
`cast_votes` was" question for the range actually tested: `cast_votes`'s fix worked because
*some* smaller size existed where behavior became genuinely correct (8/8 verified against ground
truth). Here, no size from 3 to 10 shows correct behavior — they all share the same failure
(never act), just for different reasons than the size-21+ failure (always the same act for
everyone). There is no demonstrated safe chunk size for `pressure_action` in the range checked;
reducing `max_batch_size` alone is not a fix on this evidence, only a swap between two different
wrong behaviors. The untested gap is 11-20 (and the exact boundary where acting codes start
appearing, likely somewhere near 15-25) — not yet probed, and not obviously worth probing further
without first deciding whether characterizing the exact transition point matters more than
treating "no chunk size in [3,24] reproduces correct behavior" as sufficient to act on.

## Verdict: `pressure_action` has no working chunk-size configuration tested in [3, 25] — a separate open workstream, characterization stopped, remediation direction not yet chosen (2026-08-30)

**Closing the characterization phase here, per direct instruction.** The result is qualitatively
complete, not merely "still being refined": the entire tested space ([3, 5, 10, 21-25]) is now
covered by exactly two failure modes and zero working configurations — not a continuous gradient
where an intermediate point might still turn out to be "the right one," but a sharp switch
between two equally wrong behaviors. Chasing the exact 10-21 transition would answer a mechanical
curiosity question (where is the boundary), not the question that matters for remediation (how to
get a correct decision) — nothing in the evidence gathered suggests any point on that boundary
would behave better than the two extremes already characterized.

**Evidence assembled** (all committed, all reproducible):
- Truncation ruled out structurally (`_extract_native_content` hard-fails on any non-`"stop"`
  `done_reason`; every script run completed without error).
- Not a position artifact (two independent reorderings of the same collapsed chunk reproduce the
  same near-total collapse; the one non-reproducible single-citizen exception is noise).
- Not a single-chunk artifact (3 real chunks, both collapse polarities, same acting-code avoidance
  at every sub-production size).
- Flat, weak accuracy (25.0% / 50.0% / 33.3% per chunk) unaffected by size within [3, 10].
- Not a batch-size problem the way `cast_votes`/`chamber_deliberation` were (both had a smaller
  size that was *actually correct*; no size in [3, 25] shown correct here).

**What this means going forward**: the problem most likely sits in how this decision type is
posed to the model — the prompt, the output schema, or the response space itself — not in batch
dimensioning. Closer in nature to `cast_votes`'s own Mode A ("reasoning cannot rescue this prompt
shape") than to a budget problem, except here it shows up as two *opposite*, *symmetric* failure
directions at the two tested size regimes rather than one convergence failure, which points at
something more structural in `pressure_action`'s own framing specifically.

**Status**: `pressure_action` marked unreliable in production, not just in this research
document — see the `RELIABILITY WARNING` added to `decide_pressure_actions`'s own docstring
(`llm_behavior_engine.py`) and the 🔴 marker added to §3.6.6 of the design doc. This is a real,
currently-running decision type (dt=10, fires every tick for every consulted citizen), and this
finding says it can produce systematically — not occasionally — incorrect decisions whenever
`llm.enabled=True`. `mobilization_rate` and other pressure-derived metrics from any such run
should be treated as unverified until this is resolved.

**Paused, not abandoned**: the other 6 quality probes (`candidacy_considered` and
`party_nomination_choice` — Group A; `coalition_decision` — Group B; the four Group C
self-consistency checks) stay on hold until `pressure_action` has at least an identified
remediation path — this pilot has already demonstrated its own value (catching a real problem
before building six more probes on top of the same unverified assumption), so there is no reason
to keep stacking probes while a confirmed problem sits unanswered.

**Next**: remediation direction is an open question for discussion, not something to pick
unilaterally — candidates include reworking `pressure_action`'s prompt framing, changing its
output schema, or another approach not yet considered.

## Workstream update, 2026-08-30 (cont. 7) — size=1 tested: batching is eliminated as a cause entirely, the problem is in the prompt/schema itself

Before choosing between the prompt-framing and schema-redesign remediation candidates, tested the
one size not covered by the size curve above: `_SUB_BATCH_SIZE=1`, fully isolated single-citizen
calls — the exact configuration that fixed `cast_votes`'s own collapse
(`_VOTE_CAST_MAX_CHUNK_SIZE` 3→1). Unlike 3/5/10, size=1 makes cross-citizen interaction
structurally impossible: each call contains exactly one citizen, one `ctx`, nothing else in the
batch to converge with. This is the one test able to separate "batching itself is the cause" from
"the prompt/schema fails regardless of batching."

`check_pressure_action_size_one.py` (new, committed) ran all 63 citizens from the 3 already-
characterized chunks as 63 independent single-citizen calls, same real ctx, same `think=False`
production path.

```
acting codes chosen: 0/63 (0.0%)
unambiguous act-vs-no-act accuracy: 8/21 (38.1%)
```

**Zero acting codes even fully isolated — batching is eliminated as a cause entirely.** Every one
of the 63 calls, with no other citizen present to converge with, still returned only `NOTHING` or
`WAIT_FOR_ELECTION`. This settles the question the whole size curve was building toward: the
avoidance of `SIGN_PETITION`/`LAUNCH_PETITION`/`MOBILIZE` lives in `pressure_action`'s prompt or
schema itself, independent of batch size — not a batching/cross-citizen-interaction problem the
way `cast_votes`'s was. 8 citizens with `ratio>1.5` (unambiguously should act) were tested in full
isolation and every one still got a non-acting output, including cid=6 at `ratio=4.226`, the most
extreme "should act" case in the entire dataset.

**Consequence for remediation direction**: rules out chunk-size adjustment as a fix at any size
(1 through 25 now all checked). Makes the prompt-framing hypothesis raised in discussion — the
system prompt's explicit reassurance that "0 (NOTHING) et 4 (WAIT_FOR_ELECTION) sont des résultats
légitimes... jamais des échecs" (`llm_behavior_engine.py:1807-1810`) may dominate at the expense of
ever choosing an acting code — considerably more targeted and testable now that cross-citizen
interaction is out of the picture. Still open, not yet run: a `think=True`-forced probe on one or
two of these size=1 cases (mirroring the earlier forced-reasoning follow-up, with the same
methodological caveat that `think=True` is not the production configuration) to see whether the
model's own stated reasoning, if any surfaces, points at that line or something else entirely.

## Workstream update, 2026-08-30 (cont. 8) — think=True-forced probe on size=1 reproduces the zero-reasoning collapse a third time; the prompt-framing hypothesis remains untested by this method

`check_pressure_action_size_one_forced_reasoning.py` (new, committed) forced `think=True` on two
size=1 cases chosen deliberately for an extreme, unambiguous "should act" ratio — cid=6
(ratio=4.226, the most extreme case in the whole 63-citizen dataset) and cid=270 (ratio=2.579,
different chunk). Per direct instruction, checked `<think>` content presence explicitly as a
first-class result **before** attempting to interpret anything else.

**Both calls returned zero `<think>` content**, reproducing the single-citizen-batch `think=True`
collapse already catalogued earlier in this document (there: 4 citizens from the first pilot, all
converging to identical `act=4`/`motif=305`). Both new cases here collapsed to the exact same
`act=4`/`motif=305` default. This is now confirmed across 6 citizens, two different pilot
populations, two different sampling rounds — a robust, highly reproducible pattern in its own
right, but **per the pre-registered checkpoint, it means this probe learned nothing about the
prompt-framing hypothesis**: there is no surfaced reasoning to check for a reference to the "0/4
are legitimate outcomes" line, or anything else. `think=True` at size=1 cannot be used to read the
model's rationale for this decision type — the reasoning channel itself is unavailable in this
configuration, not merely uninformative.

**Consequence**: testing the prompt-framing hypothesis (or any other candidate mechanism) will
need a different method than reading forced reasoning — most directly, a controlled ablation
(re-run the same size=1, `think=False`, production-path calls with the "0/4 are legitimate,
jamais des échecs" line removed or reworded from the system prompt, holding everything else fixed,
and check whether extreme "should act" cases like cid=6 flip to an acting code). This is also
methodologically cleaner than reading self-reported reasoning even when available, since an LLM's
stated rationale is not guaranteed to reflect its actual causal mechanism — an intervention (change
the prompt, observe the effect) tests causality directly rather than inferring it from
introspection. Not yet run — a real prompt change, even an experimental one, warrants discussion
before proceeding.

## Workstream update, 2026-08-30 (cont. 9) — pre-registration for the prompt-ablation causal test, written before any call

Testing whether the system prompt's "0 (NOTHING) et 4 (WAIT_FOR_ELECTION) sont des resultats
legitimes... jamais des echecs" line (`build_pressure_system_prompt`, `llm_behavior_engine.py`
~line 1807-1810) causally contributes to the total avoidance of acting codes. Four points fixed
in writing before any live call, per direct instruction:

**1. Isolation.** `check_pressure_action_prompt_ablation.py` (new) defines its own
`_build_ablated_system_prompt`, a local copy of `build_pressure_system_prompt` with only that one
sentence removed — everything else (the constraint line, the filtered act table, the motif table,
the cid-list self-check) built from the SAME imported constants (`PRESSURE_ACT_PROMPT_TABLE`,
`PRESSURE_MOTIF_PROMPT_TABLE`, `menu_acts`) the production function uses, so the two prompts are
byte-identical except for the one removed sentence. `llm_behavior_engine.py` itself is not
touched. This is a standalone test script calling the real client with a parallel, in-memory
prompt string — no file used by any production or in-progress run is modified.

**2. Predictions, both directions, written before running.**
- If removing the line flips the extreme "should act" cases to an acting code: the line is
  confirmed as (at least) a causal factor in the avoidance.
- If removing the line does **not** change the outcome: this does **not** exonerate the line. It
  could still be one contributing factor interacting with something else in the prompt (the
  `CONTRAINTE ABSOLUE` framing, the act table's own phrasing, or the prompt's overall structure)
  rather than acting alone — "no effect from removing it in isolation" is not the same claim as
  "the line is not part of the mechanism."

**3. Multiple extreme cases, not just cid=6.** Four citizens with an extreme, unambiguous
"should act" ratio (already tested at size=1/`think=False` in the prior section, all currently
non-acting): cid=6 (ratio=4.226, baseline: NOTHING), cid=152 (ratio=3.250, baseline:
WAIT_FOR_ELECTION), cid=270 (ratio=2.579, baseline: WAIT_FOR_ELECTION), cid=146 (ratio=2.397,
baseline: WAIT_FOR_ELECTION). A flip on only one of these would be weaker evidence than a flip
across all four.

**4. A control case that should legitimately stay non-acting.** cid=158 (ratio=0.177, the most
extreme "should NOT act" case in the dataset, baseline: NOTHING, correct per the proxy). If
removing the line makes THIS citizen start receiving an acting code too, that would show the line
was serving a real, useful function (suppressing over-eager action) that any fix would need to
replace, not just delete.

**Baselines reused, not re-measured**: all 5 citizens' `think=False`/size=1 baseline decisions
were already established in the prior size=1 test (same run, same population, same seed) — not
re-run here, since a single isolated `think=False` call has no batching/cross-thread reduction
step to introduce the non-determinism this project's own §20 finding documents specifically for
*batched* inference. Only the ablated-prompt calls are new.

## Workstream update, 2026-08-30 (cont. 10) — ablation result: removing the "0/4 are legitimate" line, alone, does not flip behavior — the line is not a sole, sufficient cause

`check_pressure_action_prompt_ablation.py` (new, committed) ran the 4 extreme "should act" cases
plus the 1 "should NOT act" control through `_build_ablated_system_prompt` — the real system
prompt with only the "0 (ne rien faire) et 4 (attendre la prochaine election) sont des resultats
legitimes... jamais des echecs" sentence removed, everything else byte-identical.

```
cid=6   (ratio=4.226): NOTHING -> WAIT_FOR_ELECTION        [unchanged, still non-acting]
cid=152 (ratio=3.250): WAIT_FOR_ELECTION -> NOTHING        [unchanged, still non-acting]
cid=270 (ratio=2.579): WAIT_FOR_ELECTION -> WAIT_FOR_ELECTION [unchanged]
cid=146 (ratio=2.397): WAIT_FOR_ELECTION -> WAIT_FOR_ELECTION [unchanged]
cid=158 (ratio=0.177, control): NOTHING -> WAIT_FOR_ELECTION [unchanged, still non-acting]
```

**Zero flips across all 5 cases.** All 4 extreme should-act citizens remained non-acting with the
line removed (two even swapped between the two non-acting codes — NOTHING↔WAIT_FOR_ELECTION —
without ever reaching an acting code); the control case also stayed non-acting, so there is no
sign the line was suppressing over-eager action either. Per the pre-registered reading written
before this ran: **this rules out the line as a sole, sufficient cause, but does not exonerate
it as a contributing factor** — removing one sentence in isolation left the rest of the prompt's
structure (the `CONTRAINTE ABSOLUE` framing, the filtered act table, the overall shape of asking
for one JSON decision about a menu of legitimate-inaction options) fully intact, and any of those
could still matter, alone or in combination with the removed line.

**Where this leaves the investigation**: the single-sentence prompt-framing hypothesis, tested in
its most direct, cheapest form, did not confirm. This does not mean prompt/schema framing is
ruled out in general (`think=True`/size=1 already showed the failure isn't batching-related, so
it remains something about how this decision is posed) — it means the mechanism is not
attributable to this one sentence acting alone. Further ablation (removing more of the prompt at
once, or testing a differently-worded framing rather than deletion) would be a new, larger design
question, not a quick follow-up — a natural point to stop and reassess with input on direction
rather than continue narrowing unilaterally.

## CLOSURE, 2026-08-30 — `pressure_action` quality investigation: three causes eliminated by direct test, real mechanism not identified, deferred to a future design session with a named candidate (not a blank page)

**Full chain of evidence, each link a pre-registered, directly-tested elimination — not
inference or assumption:**

1. **Not a position artifact.** Two independent reorderings of the same collapsed 21-citizen
   chunk reproduced the same near-total collapse regardless of serialization order (one
   non-reproducible single-citizen exception, read as noise, not signal).
2. **Not a batch-size problem.** The full curve — sizes 1, 3, 5, 10, and production (21-25) — was
   tested across 3 real chunks, both collapse polarities. Every size below production scale
   (1/3/5/10) avoids acting codes (`SIGN`/`LAUNCH`/`MOBILIZE`) entirely, including size=1 fully
   isolated single-citizen calls (0/63 acting codes, including the most extreme "should act" case
   in the dataset, ratio=4.226). Production size collapses the whole chunk to one uniform answer
   instead. No size in [1, 25] produces correct, content-tracking behavior. Unlike `cast_votes`/
   `chamber_deliberation`, chunk-size reduction is not a fix here — this rules out batching/
   cross-citizen interaction as the cause entirely, not merely as unlikely.
3. **Not the "0/4 are legitimate outcomes" sentence acting alone.** A pre-registered causal
   ablation (isolated test prompt, `llm_behavior_engine.py` never touched) removed exactly that
   one sentence and re-ran 4 extreme should-act cases plus 1 should-NOT-act control. Zero flips —
   every should-act case stayed non-acting, the control stayed non-acting too (no
   over-correction). This rules the sentence out as a *sole, sufficient* cause; it does not
   exonerate it as one contributing factor among others.
4. **The forced-reasoning channel is unavailable for this decision type at size=1**: `think=True`
   collapses to zero visible `<think>` content and an identical `act=4`/`motif=305` default,
   confirmed across 6 citizens over two separate probes — not a path to understanding *why*, a
   separate catalogued failure mode in its own right (explicitly not a production risk, since
   `think=True` is never used for this decision type in production).

**The real mechanism remains unidentified.** What survives all four eliminations, named as the
leading remaining hypothesis rather than left vague: `pressure_action`'s menu presents 5 options
where 2 (`NOTHING`, `WAIT_FOR_ELECTION`) are structurally framed as a distinct, always-legitimate
category — not just described that way in the one removed sentence, but built into the decision's
very shape (one flat choice among five, two of which are explicitly non-committal by design). That
structural shape cannot be tested by deleting more prompt text; deleting the sentence that *named*
the category left the category itself — and the single flat choice across all five — fully intact,
which is consistent with why removal alone didn't move the result.

**Named candidate for a future design session** (concrete, not a placeholder — same discipline as
point #11's "needs a law concept" deferral): **split the decision into two stages** — first a
strict binary act/don't-act judgment, then, only if "act," a second choice among
`SIGN`/`LAUNCH`/`MOBILIZE`. This tests whether separating "should I act at all" from "which lever"
unblocks the acting-code choice, without touching anything else about the prompt's content or
`ctx` fields. Untested — this is a real schema/decision-flow change, requiring its own
pre-registration and validation cycle (new schema, new failure surface to check), not a quick
diagnostic. Explicitly not the only candidate — named because it directly follows from the leading
structural hypothesis, not because alternatives were ruled out.

## Postscript, 2026-08-30 — cross-model check: doesn't reproduce cleanly, but doesn't exonerate qwen3:8b either

Prompted by a tangent about switching serving backend/model (vLLM remains blocked, unrelated
platform issue — see `project_polity_vllm_switch` memory), tested whether the total avoidance of
acting codes is qwen3:8b-specific by running the REAL, unmodified prompt (size=1, `think=False`)
against 4 other models on the same 5-case set used in the ablation test
(`check_pressure_action_model_comparison.py`, new, committed). Not a return to full
characterization — a single, cheap check appended to an already-closed workstream, not a reopening
of it.

**Results are messier than a clean yes/no, and the script's own auto-generated verdict ("not
qwen3:8b-specific") undersells that messiness — flagging this explicitly rather than repeating it
uncorrected**:

- **`llama3.1:8b` and `gemma2:9b`: 0/5 usable results — both failed decode on every single call**,
  returning the same `cid` duplicated 2-4 times in the response array instead of one decision.
  This is a structured-output schema-compliance failure via Ollama's native endpoint, not a
  content-quality result either way — these two models could not be evaluated on the actual
  question at all.
- **`mistral:7b`: 5/5 decoded cleanly, and all 5 chose `MOBILIZE`** — including the control case
  (cid=158, ratio=0.177, should clearly NOT act). This is a real collapse, content-blind exactly
  like qwen3:8b's, just to the **opposite** pole (always acts vs. never acts). This is arguably
  stronger evidence for the "task/menu shape induces collapse" hypothesis than a clean "other
  models are fine" result would have been — a second model family collapses on this exact call
  shape, just onto a different fixed answer.
- **`qwen2.5:7b` (same lineage, prior generation): 3/5 decoded** (2 failed with a different
  error — the model emitted a motif code, 306, in the `cid` field). All 3 that decoded chose
  `NOTHING`, consistent with — not proof of — a Qwen-lineage-wide tendency rather than a
  qwen3-specific one.

**Honest reading**: this does not exonerate qwen3:8b's specific direction, and it does not cleanly
confirm the "menu structure" hypothesis either — it adds a real, different data point (a second
model collapsing the opposite way, content-blind) and two data points that aren't informative at
all (structural JSON-compliance failures unrelated to content quality). Switching model is not a
demonstrated fix on this evidence: one alternative that actually produced valid output collapsed
just as completely, in the direction that would be worse for a simulation whose mobilization
metrics already tend to look "too eventful" in this failure mode. Kept as an appendix to the
closed investigation, not a re-characterization — the named remediation candidate (binary-then-
lever split) and the closure status below are unchanged.

**Status**: `pressure_action` stays marked unreliable in production (`decide_pressure_actions`
docstring, `llm_behavior_engine.py`; §3.6.6 design-doc marker) — mechanism now well-characterized,
not resolved. The 6 remaining quality probes (`candidacy_considered`, `party_nomination_choice`,
`coalition_decision`, and the 4 Group C self-consistency checks) stay paused until this is
revisited — this pilot has already delivered its core value (catching a real, systematic
production bug before building six more probes on an unverified method), and there is no reason
to resume building on top of a confirmed, uncharacterized-no-longer-but-unresolved problem. This
workstream closes for today at this point — deferred, dated, with a named next step, not
abandoned.
