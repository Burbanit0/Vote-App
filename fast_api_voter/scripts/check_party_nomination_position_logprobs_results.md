# party_nomination_choice's winner_position=26 is a comprehension failure, not a decoding accident — Track C1 step E, 2026-09-11

## What was already known

Stage 3 (`scaleprobe-8y-p500-v2-postfix`) fell back on `party_nomination_choice` 10/15 times
(67%). Party 3, tick 16, returned `winner_position=26` against only 19 declared candidates — six
such answers total, all first attempts at temperature 0 (`validate_party_nomination_decision` sits
outside `_complete_and_decode_with_replay`'s own replay loop, so the shipped retry budget never got
a chance to act on this class of failure). Nothing in the prompt equals 26 (total contenders across
all 5 parties = 206, winner cid = 132, winner's true position = 2).

Two readings, pre-registered before this probe ran: if "2" is confident and the second digit lands
near p=0.5, it is a decoding accident (an unbounded, ungrammared second digit is close to a coin
flip) — only a grammar bound (D1) truly fixes it. If "26" itself is confident (both digits strongly
preferred), it is a comprehension failure — only restating the bound (C) or containing the damage
(B, per-party fallback) help; a grammar bound alone would just force a different wrong answer.

## Method

`check_party_nomination_position_logprobs.py` — an EXACT reproduction, not an approximation.
`ambition_score` (never mutated post-generation) and `platform_distance` (from `issue_positions`,
also never mutated — only `revealed_position`/`pledged_platform` are) together with `Party.platform`
(never mutated anywhere in this codebase) make every field this prompt sends time-invariant across
the whole run. Loaded the run's own final `checkpoint.json` (500 citizens, 5 parties) and replayed
the exact tick-16 batch (all 5 real contested parties together, real declared-candidate cid lists
read from `events.jsonl`'s own `party_nomination_choice.payload.contenders`), same schema, same
`think=False`, temperature=0, same seed — via `complete_json_with_logprobs`, then
`llm_logprob_instrumentation.locate_decision_field_logprobs` for the first digit and a small
one-off extension (`_second_digit_token`, this script only) for the second, since the shared helper
applies one `value_char_offset` across a whole batch and this batch has heterogeneous value lengths
(party 0 answered a single digit, party 3 answered two).

## Result: reproduced exactly, and both digits are confident

The replay reproduced the original failure byte-for-byte: `winner_position=26` for party 3 against
19 candidates, out of range, same as Stage 3.

| digit | token | logprob | P (exp) | next-best alternatives |
|---|---|---|---|---|
| first ("2") | `'2'` | -0.0059 | 0.9941 | `3` (-5.568, P=0.0038), `1` (-6.256, P=0.0019) |
| second ("6") | `'6'` | -0.1142 | 0.8920 | `8` (-2.833, P=0.0589), `7` (-3.052, P=0.0472), `5`/`9`/`1` all below 0.001 |

Neither digit is anywhere near a coin flip. The second digit's own top alternatives are other
digits (8, 7, 5, 9, 1) — the batch-terminator token (`"},"`) sits far down the list at logprob
-9.08 (P≈0.0001), so this is not "the model finished at 2 and then something forced a spurious
continuation" either. The model committed to a two-digit answer in the 25-29 range with high
confidence, on both characters.

## Verdict: comprehension failure

**This settles the pre-registered question in favor of comprehension failure, not decoding
accident.** The model is not confused about HOW to write a number — it computed a specific, wrong
one, confidently. A grammar bound (D1, `enum: [1..19]`) would still make every future answer
mechanically legal (xgrammar renormalizes over only valid continuations, so an enum bound cannot be
violated by construction), but per the plan's own reasoning this does not address WHY the model
reasoned to 26 in the first place — it would force the sampling into *some* value in [1,19], not
necessarily a value that reflects any coherent preference the model actually had. Restating the
bound in the prompt (C: state each party's own `candidate_count` and legal range) is the fix this
verdict actually argues for; per-party fallback (B) contains the blast radius regardless of which
content fix is chosen.

## What's next, per the plan's own fixed order

E is done. Next: A (validate inside `_complete_and_decode_with_replay`'s own `decode=` lambda, so
the already-shipped retry budget actually gets a chance at this failure class) and B (per-party
fallback, so one bad party's confidently-wrong answer no longer sinks the other four parties' good
ones). Then C (state the per-party bound explicitly) as the content-level response this verdict
argues for — D1 is not ruled out as a later defense-in-depth backstop, but is not the fix this
specific verdict calls for on its own.

## Step C verified live, 2026-09-11

Re-ran this exact script (unchanged) after shipping `candidate_count` per party block plus the
system-prompt sentence pointing to it. Party 3's answer moved from `26` (out of range) to `19` —
the maximum LEGAL position for its own 19 candidates, now in range, and just as confidently chosen
(P("1")=0.99994, P("9"|"1")=0.9985 — if anything more confident than the original wrong answer).

**Read carefully: this fix's scope is legality (C2), not judgment quality, and this run cannot
distinguish "genuinely selected the last candidate for a real reason" from "learned to echo
`candidate_count` back as a habit."** The five parties' answers this run were `(0:19, 1:36, 2:1,
3:19, 4:73)` against candidate counts `(43, 40, 31, 19, 73)` — only 2 of 5 (parties 3 and 4)
happened to equal their own party's candidate_count exactly, and party 2's answer (`1`, the
MINIMUM) rules out a simple "always pick the max" reflex outright. This is real variation, not a
constant, but it is not proof of genuine per-candidate judgment either — nobody has checked whether
`winner_position` tracks `ambition_score`/`perceived_support`/`platform_distance` content the way
`polity-decision-contracts.md`'s own dt=4 behavioural clause requires. That question was already
open before this fix (the type was never confirmed collapse-free by content-sensitivity, only by
its 4/5-tick accuracy against ground truth) and stays open after it — worth a dedicated probe
before trusting this type's judgment quality the way `pressure_action`'s content-sensitivity was
explicitly verified.
