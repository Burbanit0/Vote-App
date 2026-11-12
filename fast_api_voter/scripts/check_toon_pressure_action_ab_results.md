# TOON input encoding, pressure_action — plan-llm-protocol-and-theory-program.md §5.E

## The paired requirement this satisfies

§5.E's own blocking reservation on `pressure_action`: *"Changing its prompt format invalidates
every prior collapse measurement on it ... So the TOON test there must be paired with §5.C's
logprob instrumentation (measure P(act) before and after), or it produces a new prompt with no
comparable baseline."* This re-runs `check_logprob_pressure_action_gap_tracking.py`'s own probe
verbatim (same 17 self_gap points, same target/mandate_dev/ticks_to_election, same shipped
closed menu) through both the JSON prompt (`build_pressure_system_prompt`/`build_pressure_user_
prompt`) and a TOON one (`build_pressure_system_prompt_toon`/`build_pressure_user_prompt_toon`
— which additionally hoists `target`/`mandate_dev`/`ticks_to_election`/`available`/petition/
`neighbors_acting` out of the per-citizen rows into a single one-row `call` section, since all of
them are call-level constants under this project's actual shipped architecture: one consulted
officeholder per tick, config-derived legal menu, no social graph, no open petitions under
`electoral_only` — see that function's own docstring), reading P(act=4) via the same instrument
validated earlier this session.

## Gate (a): token savings — real, and larger than candidacy_considered's

| | JSON | TOON |
|---|---|---|
| prompt_tokens | 1743 | 976 |

**44.0% reduction** (767 tokens) — well beyond `candidacy_considered`'s 6.9%, consistent with
the plan's own prediction that `pressure_action` ("~8-12 clés, quasi que des scalaires, jusqu'à
25 citoyens par chunk") would benefit most from TOON, and in fact somewhat larger than the
plan's own rough estimate (~30-40%). Both formats decoded cleanly (17/17 structurally valid
decisions each) — the format change does not break output validity.

## Gate (b): quality — does NOT clear, and the reason matters

The JSON baseline (previously measured, reproduced here) shows P(act=4) pinned near 1.0
regardless of self_gap — the confirmed collapse. Under TOON, P(act=4) drops sharply and
non-monotonically across most of the same range (values from 0.003 to 0.30, no clean trend)
instead of staying pinned near 1.0. At first glance this could look like "the collapse
loosened" — it is worth being precise about why it is not that.

Applying the same weak `>0.5` threshold-call reading used in the original baseline, against the
same weak proxy (`self_gap < blank_threshold` ⟹ NOTHING correct, else WAIT_FOR_ELECTION
correct — itself not validated ground truth, per `decide_pressure_actions`'s own docstring):

| | threshold-calls correct | vs. a trivial "always predict the majority class" baseline (9/17 = 52.9%) |
|---|---|---|
| JSON | 9/17 (52.9%) | matches exactly — JSON's collapse constant (always WAIT) happens to equal the majority class in this sample |
| TOON | 8/17 (47.1%) | **worse** — TOON's own collapse constant (always NOTHING, every single point falls below 0.5) is the *minority* class here |

**TOON did not restore self_gap-tracking. It flipped which constant the model collapses to** —
from "always WAIT_FOR_ELECTION" (JSON) to "always NOTHING" (TOON, with a few noisy mid-range
bumps that never cross the 0.5 threshold-call line). Both are still content-blind with respect
to self_gap; TOON's own constant simply happens to score worse against this particular
(unvalidated) proxy in this particular 8-vs-9 sample, which is not itself the point — the point
is that neither format shows a real gradient.

## Reading this against §5.E's own stated risk

§5.E's own reservation #2, written before any live test: *"Token count ≠ comprehension ... these
models have seen overwhelmingly more JSON in training ... not about numeric reasoning over
positions and thresholds, which is what this project actually asks for."* This is a direct,
concrete instance of exactly that risk — not hypothetical. `candidacy_considered` (a simpler,
single-threshold judgment) showed zero measured quality cost from the same kind of format
change; `pressure_action` (part of the project's own confirmed-collapse set, already known to
be format/framing-sensitive per §2's own hypothesis) shows a large, real behavioral shift whose
practical quality is, if anything, slightly worse by the only proxy available. This is
consistent with — not contradicting — the project's broader pattern: the reliable decision
types tolerate a format change cleanly, the already-fragile ones are exactly where a format
change has the most room to move something, in either direction, unpredictably.

**Caveat, stated plainly:** this is one live run per format, not replicated with a second
seed. The shift is large enough (near-1.0 to near-0, inverted at that) that it is very unlikely
to be pure sampling noise, but a second run would strengthen this before treating the specific
47.1% number as precise — the qualitative conclusion (TOON changes which pole pressure_action
collapses to, without restoring real sensitivity) is the load-bearing claim here, not the exact
percentage.

## Disposition

**Not shipped, and not recommended for `pressure_action` on this evidence.** Real, substantial
token savings do not offset a quality picture that is unclear at best and slightly worse at
worst, on the project's own only available (weak) proxy, for a decision type that already has
zero validated reliability. Diagnostic-only functions (`build_pressure_system_prompt_toon`/
`build_pressure_user_prompt_toon`) are kept in the codebase as instrumentation for any future
investigation (e.g., pairing this with §2's base-vs-instruct comparison, to see whether the
format-flip is itself an alignment-prior artifact), not as a candidate for production use.
