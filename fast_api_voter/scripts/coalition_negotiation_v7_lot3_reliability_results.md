# coalition negotiation (v7 Lot 2, §3.4 Cas 2) — v7 Lot 3 live reliability spike

`decide_coalition`'s multi-round negotiation loop (v7 Lot 2, PR #223) had never been run against a
real model -- everything up to this point was verified with fakes. This is the "spike before you
trust it" pass this project runs for every LLM decision type before treating it as reliable.

## Why this spike is structurally different from chamber_deliberation's/vote_cast's

Every prior truncation floor this project chased (`chamber_deliberation`, `vote_cast`) came from
`think=True` -- a chain-of-thought budget the model can get stuck looping inside (Mode A) or
exhaust on genuinely long reasoning (Mode B). `decide_coalition` calls the client with
`think=False` (a pre-v7 choice, unchanged by Lot 2) -- there is no reasoning trace to allocate a
budget for or get stuck in. That risk class is structurally absent here. What genuinely is new and
untested is the round ≥ 2 prompt shape (`prior_decision` + `provisional_coalition_seats`,
`build_coalition_user_prompt`) -- never sent to a real model before this spike -- and the
negotiation loop's own control flow (fixed-point / hard-cap stop) end to end.

## Method

`scripts/check_coalition_negotiation_reliability.py`. Four scenarios varying party composition
(tight majority, two-bloc-plus-kingmaker, fragmented, near-parity) at 5 reps each, plus one
scenario (`genuine_shortfall_forces_reconsideration`) purpose-built to pressure-test round 2's
actual value proposition, at 10 reps. Real `OllamaJsonClient`, shipped model (`qwen3:8b`), GPU,
`max_batch_replays=0` (strict first-attempt measurement, not the replay-absorbed rate).

**The engineered scenario, and why**: two responders close to the initiator's platform are given
tiny seat counts (5 each) so that initiator + both together fall short of the 50% threshold
(26+5+5=36 < 43); two responders far from the initiator's platform are given large seat counts (25
each, still under the initiator's 26 so neither becomes initiator itself) so that exactly one of
them is individually decisive. The intent: round 1 plausibly declines both far parties on proximity
grounds, and round 2 shows them a real, large (7-seat) shortfall -- the clearest incentive this
project's own motif table offers for a revision (502 OFFICE_SEEKING: real leverage as the deciding
vote, not just 501 IDEOLOGICAL_PROXIMITY). A first attempt at this scenario (seats
`[(0,20),(1,8),(2,8),(3,40)]`) failed for an unrelated reason before ever testing anything: party 3
(40 seats) exceeded the intended initiator's own seats and became initiator itself
(`coalition_initiator: largest_seats`), clearing majority alone with zero network calls. A second
attempt (4 similarly-sized responders) was defeated by a general algebraic fact, verified directly:
if P0 is the largest party (hence initiator) and Pi is any single responder with Pi < P0, then
P0+Pi exceeds a 50%-of-total threshold whenever the combined seats of every OTHER, unused responder
don't outweigh P0+Pi -- true generically with few, similarly-sized responders. The final version
(above) breaks this by making the "close" responders tiny and the "far" ones individually large.

## Result

**30/30 formations completed without a single `LlmResponseError`.** Every round shape (round 1,
identical to the pre-v7 prompt; round ≥ 2, carrying `prior_decision`/`provisional_coalition_seats`)
produced schema-valid, motif/action-coherent output on the first attempt, every time, across all
five scenarios. Zero truncations, zero decode failures, zero validator rejections. This is the
reliability question this spike set out to answer, and it is unambiguously answered: **the
mechanism is reliable.**

**But every one of the 30 formations converged in exactly 2 rounds with IDENTICAL decisions in
round 1 and round 2 -- including the engineered shortfall scenario.** In
`genuine_shortfall_forces_reconsideration`, all four responders answered JOIN in round 1, every
single time (10/10 reps), despite two of them being ideologically far from the initiator
(`math.dist` 1.11 and 1.48 on a 20-dimension space where the closest responder sits at 0.37) --
the model did not decline them on proximity grounds the way the scenario's design assumed it
would, so round 2 never actually got the chance to show a real shortfall (there wasn't one: the
"far" responders joined immediately, so the coalition already cleared majority in round 1). No
scenario, across 30 independent live trials, produced a case where a responder's round-2 answer
differed from its round-1 answer.

| | value |
|---|---|
| formations run | 30 |
| `LlmResponseError`s | 0 |
| rounds_used distribution | `{2: 30}` |
| formations showing a round-1→final revision | 0 |

## What this does and does not mean

**Does mean**: v7 Lot 2 is reliable and safe to ship as-is. Nothing about the round ≥ 2 prompt
shape confuses the model, breaks the schema, or produces incoherent motif/action pairings. The
fixed-point stop condition works correctly (every formation here reached it at round 2, the
earliest round it can possibly fire, since round 1 alone can never be a fixed point by
construction -- see `decide_coalition`'s own docstring).

**Does not mean**: that conditional reasoning ("I join iff party X joins") has been observed to
work. It hasn't -- not once, in 30 trials, including one specifically engineered to create pressure
for it. Three explanations are plausible and none was distinguished by this spike: (a) `qwen3:8b`
at this prompt shape may have a strong prior toward JOIN that proximity/seat signals don't
override, (b) round 2's prompt may not differ enough from round 1's to perturb a
temperature=0-deterministic model already committed to an answer, or (c) the scenario, despite the
seat-count engineering, may still not have produced genuine ambiguity from the model's own
perspective. This is a real, open, separate question from reliability -- whether the mechanism ever
needs to be observed producing a revision to be considered "working" is itself not settled (a
negotiation that converges immediately because there was nothing to negotiate about is not a bug),
and resolving it needs either a differently-engineered scenario, a different `think`/temperature
setting, or population-scale observation across a real acceptance run -- none of which are Lot 3's
job. Left open, not closed, for a future lot.

## Conclusion

**v7 Lot 2 ships as reliable.** The open question above is scientific, not a reliability gate --
noted here for whoever picks up v7's next lot (an acceptance run, §11) or reconsiders the prompt's
incentive framing, not blocking anything already merged.
