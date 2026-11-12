# candidacy_considered's excess declared-rate survives calibration — Track B3, 2026-09-11 (NEGATIVE)

## What was already known

Stage 3 (`scaleprobe-8y-p500-v2-postfix`) measured **202/500 (40.4%) declaring**, against this
project's own pre-registered bar of **< 5%** (5 parties x 2-5 serious contenders ~= 2-5% of a p500
population). Unlike B1/B2's targets, this is not a content-blind collapse -- the model differentiates
for real (64% accuracy against `simple_rules.decide_candidacy`'s ground truth) -- it is simply far
too permissive.

`ambition_score` (`citizens.ambition_dist`, shipped `beta(2,8)`) is sent as a bare float in [0,1]
with no reference at all. `polity-decision-contracts.md`'s own §3 names the gap and the intended
fix: "préférer une référence de population, dans la forme qu'a déjà `perceived_support`." ADR-002
already established `config.ambition_threshold` is not valid ground truth for the LLM path --
`decide_candidacies` never reads it at all (confirmed twice in that ADR's own text, and again via
`grep -n "ambition_threshold" llm_behavior_engine.py`, whose only hit is a comment inside
`_deterministic_candidacy_fallback`'s docstring).

## What was added

`build_candidacy_system_prompt_toon_calibrated` (`llm_behavior_engine.py`) -- one new sentence
stating the population's own MEAN `ambition_score`, computed once by the caller over the same
`population` `support` is computed over (never per-chunk, matching `decide_candidacies`'s own
"never recomputed per-chunk" discipline for `support`). `perceived_support` is already self-scaling
(a `sympathizer_ratio` population fraction), so it was not this fix's target.

## Method

`check_candidacy_calibration.py` -- a REAL population (`generate_population` against the shipped
config, `citizens.ambition_dist=beta(2,8)`), full p500, unfiltered (matching
`_declare_nominees_llm`'s own call site: every citizen in this model already has a party, so there
is no party-affiliation subset to filter to in practice). Same chunking
(`llm.max_batch_size=25`, 20 chunks), same think=False, same `CANDIDACY_JSON_SCHEMA` output -- only
the system prompt builder changed between the two arms.

## Result: worse, not better

| | declared | accuracy |
|---|---|---|
| baseline (`build_candidacy_system_prompt_toon`) | 202/500 (40.4%) | 318/500 (63.6%) |
| calibrated (`build_candidacy_system_prompt_toon_calibrated`, mean_ambition=0.1975) | 238/500 (47.6%) | 292/500 (58.4%) |

The baseline figure (202/500, 40.4%) reproduces Stage 3's real production number exactly -- the
same seed, same config, same real batch shape -- confirming this probe is a faithful
reproduction, not a synthetic approximation. The calibrated arm declared **more**, not fewer, and
got **less** accurate against ground truth. Neither number moves meaningfully toward the <5% bar;
both land an order of magnitude above it.

## What this means, and what it does not

**Not shipped.** `decide_candidacies` still calls the uncalibrated `build_candidacy_system_prompt_toon`.

This is the **second** confirmed case (after B2's `coalition_decision`) where C3 (missing scale)
does not explain the defect. One plausible reading: stating the population MEAN gives the model a
comparison point that argues in the wrong direction -- "your ambition is above the population
average" reads as a reason *to* run, when real candidacy requires a far rarer combination of traits
than merely above-average ambition. A mean is the wrong reference shape here, unlike
`representative_response`'s exact geometric ceiling (B1) or even `coalition_decision`'s dispersion
measure (B2, which at least didn't make things worse) -- this is not a case of "no reference" but
"the natural reference argues for more, not less".

**This also settles part of B3's own open modelling question in the negative, not just the prompt
question.** The plan reasoned that the model has no consequence to reason from because losing a
nomination costs nothing (`nomination_lost` journals and nothing else) -- but that mechanism, if
built, could only suppress REPEAT candidacy at a citizen's second or third election, never the
FIRST. This probe's 500 citizens have no election history at all (a fresh `generate_population`
call, not a mid-run snapshot) and still declare at 40-48% -- so whatever is driving the excess rate
is present before any citizen could possibly have lost a prior nomination. **An ambition-decay-on-
defeat or cooldown-after-loss mechanism would not have moved this measurement at all, because
the population it was measured on has no defeats to decay from.** Decision, recorded here per the
plan's own requirement to decide explicitly rather than let it go undiscovered: **do not build the
ambition-feedback mechanism as a fix for this bar.** It may still be worth building on its own
merits as a `static_population: true` design question (repeat candidates with unchanged ambition
forever is a real, separately-noted oddity -- `check_toon_candidacy_ab.py`'s own sibling finding
that `campaign_positioning` returns byte-identical shifts across every election), but it is not an
answer to the rate defect this track was scoped to close, and building it under that pretense would
be solving the wrong problem on purpose.

**What remains untested**: whether a *stricter* population reference (a high percentile rather than
the mean, or the two raw signals compared against each other rather than each alone) would push the
right direction. Revisit only with a probe that isolates that specific hypothesis -- this result
rules out "population mean" specifically, not every possible population-reference shape.
