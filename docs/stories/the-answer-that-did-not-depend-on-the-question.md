# The answer that did not depend on the question

Polity is a simulated democracy whose citizens, party leaders and presidents are played
by a language model (Qwen3-8B, served locally). Many of their decisions are closed
codes. Does a party join the coalition it is offered? Does the president concede to the
street? Does a discontented citizen act, or wait for the next election? The model writes
a short JSON answer, and the simulation reads one number out of it.

The runs looked plausible. Coalitions formed, presidents responded, elections came and
went. Small spot checks had hinted at a problem: on four to six hand-built test cases,
the same answer every time. This piece is about how we measured that three of those
decisions barely depended on their inputs, and about the instrument that showed it. It is also about
the part that surprised us most: one of the three was entirely the prompt's fault, and
another partly.

## Reading the decision, not the answer

A sampled answer tells you what the model said once. It does not tell you how close it
came to saying something else. For a closed-code decision there is a better reading: the
probability the model gives each code at the moment it writes it. vLLM returns the top
token log-probabilities for every generated token, so if the answer is
`{"act": 4}`, you can read P(4) against P(0) at the token where the `4` was written.

Doing this on the production prompts was the hard part. The answers are JSON constrained
by a grammar, often preceded by a `<think>` block that the server strips from the text
but not from the token stream. The instrument rebuilds the raw text from the tokens,
finds the answer inside it, locates each decision field's token, and refuses to return a
partial reading. It raises an error instead. For a two-code field it normalises over
the two, so P(act=4) means P(4) / (P(4) + P(0)).

An instrument like that needs a decision whose right answer is known before it is
trusted anywhere else. Polity has one: whether a voter casts a blank ballot follows a
rule the simulation can compute. On 16 voters (8 who should vote blank, 8 who should not)
the mean P(blank) was **0.9969** for the first group and **0.0494** for the second, a
separation of **+0.948**. The instrument could see a decision that tracks its input. Then
it was pointed at the others.

## Three flat lines

Each probe used the production prompt builders unchanged, varied one input from one
extreme to the other, and read the probability at each point.

**The president's response.** Nine situations, from legitimacy 0.95 with nobody in the
street to legitimacy 0.05 with a large crowd in the street. The probability of
conceding was between **0.999999 and 1.000000 at every point**. The full spread across
the nine was 0.000001.

**A party offered a coalition.** Five parties along a diagonal, from one identical to
the initiator, with the coalition 25 seats short, to one maximally distant on all 20
issues, with no seats missing. P(join) was **0.999374** for the first and **0.996777** for the last.

**A citizen deciding whether to act.** Seventeen citizens, from one who nearly agrees
with the officeholder (a gap of 0.02) to one far from them (2.20), against a threshold
of 0.5. The probability of "wait for the election" was **0.976** for the most satisfied
citizen. Asked alone instead of in the batch, that citizen got 0.999992, and the angriest
got 1.000000.

These are not weak preferences that a different sampling seed would flip. Sampling each
citizen at their own probability instead of taking the top answer would be expected to
change 0.03 of the 17 decisions: not even one. The model was confidently constant.

## Why the aggregates could not say so

For the citizen's action, the shipped menu offered only two codes: do nothing, or wait
for the election. Neither counts as mobilising, so a mobilisation rate of zero is exactly
what that menu predicts whether the decision works or not. A flat answer and a working
one produce the same aggregate. Only a per-citizen reading can tell them apart.

The other two do show in the totals, but a total cannot say whether the decision followed
its inputs. In ten full runs, coalition offers were accepted 152 times in 160. After a
partial fix of the president's prompt, two larger runs still had presidents conceding in
33 of 33 answers and in 25 of 32. That could describe a cooperative society. Only varying
the inputs shows whether the decision is listening to them.

## The constant that was the prompt's

The citizen's action had a simpler explanation than the model. The rule the simulation
uses to score it compares the citizen's gap with their personal threshold. The prompt
sent the gap and **never sent the threshold**. The model was asked whether a citizen was
discontented enough to act, given a number with no scale.

A control prompt that stated the threshold and the rule outright, one citizen per call,
got it right: P(act) was **0.007** for the satisfied citizen and **1.000** for the angry
one, a separation of +0.993. In batches the same prompt became unstable: 17 citizens in
one call read flat (+0.0001), and with the batch order randomized, accuracy swung between
0 and 100% from one trial to the next at the same size.

Stating the rule was never going to be the fix. A model that executes a rule written into
its prompt is a slow copy of the rule, and the project forbids it. The shipped fix
(2026-09-10) sends the threshold as data, with no rule, one citizen per call. In a
calibration grid, prompts of that kind agreed with the rule at batch size 1 (on one side
of the threshold only, a later correction found) and failed at batches of 5 and 25,
mostly near the 50% a constant answer gets. Live, end to end, the shipped version agreed
with the rule on 12 of 12 citizens, on both sides of the threshold, where a constant answer
would get 6. On a frozen bank of 24 cases it agreed on 15, where a constant would get 12.
The decision is no longer constant, and it is not validated either.

So one of the three flat lines was a question nobody could have answered, asked of many
citizens at once. That is worth checking first, every time a decision looks dead.

## The constants that stayed

The other two did not go away so easily. Calibrating the president's prompt, by stating
two facts that were always true (the bounds of two of its inputs), moved the calm pole:
P(concede) fell to 0.12 at legitimacy 0.95. Every other point stayed at about 1.0. A
one-sentence calibration of the coalition prompt restored nothing.

Two questions then mattered: is this one model, and is it instruction tuning?

- **Other model families.** The coalition probe was pre-registered for at least two
  non-Qwen families. It stayed flat on both: IBM's Granite 4.2 8B and Google's Gemma 4
  12B (Gemma's reading needed a thinking budget to be parsed). The constant was not the
  same everywhere: Granite almost always joined (with one dip, to 0.65), and Gemma never
  did (P(join) 0.000 at every level). The flatness persisted; the value it settled on did
  not. The president's response was flat on both as well.
- **Base versus instruct.** Qwen3-4B and Qwen3-4B-Base, both bf16, differ only in
  instruction tuning. The coalition decision was flat in both. For the citizen's action
  (with the old prompt), the base model's probabilities moved a little more with the gap
  than the instruct model's, but on the main statistic neither cleared the pre-registered
  bar (the base model's single-citizen control did, at +0.124), and the emitted decision
  was flat in all four cells (two models, two probe geometries).
- **One exception.** The president's response did not collapse on the 4B instruct model:
  at the calm pole it chose silence, and the two poles were fully apart. Instruction
  tuning alone does not produce that flatness, then; between the 8B and 4B models, size,
  quantisation and precision all differ. All of this is at 4B, so it narrows the question
  rather than closing it.

## What changed

The project now keeps a table of which decision types a scientific claim may rest on:
only those marked validated, or one whose role in that claim has been checked directly.
Casting a ballot is validated, at the bar; the coalition and the president's response are
marked collapsed; most others are unverified. In the simulation's exploration setup,
coalitions are negotiated by party-leader agents instead of a batched yes/no.

The same habit stopped an experiment this month. Before spending GPU days on the effect
of a seat threshold on party founding, a probe told 60 would-be founders the threshold
was 3%, then 7% (sampled at temperature 0.6 this time, not read from logprobs). 59 of the
60 founded at each threshold, including at least 13 of the 14 whose backing was below 7%.
The experiment did not run.

## What this does not show

- The logprob probes are small: at most 17 points each, at temperature 0, mostly on one
  model. The point is not the precise numbers. It is that the numbers do not move.
- Not every decision collapsed. The blank vote tracks its rule, candidacy and nomination
  decisions show no collapse, and a flat reading of an economic-shock reaction was not
  classified as one.
- "Flat" here means the two ends of the axis agree. Granite's coalition curve dips at one
  point, and the probe's extreme points include situations production never creates.
- The citizen's action works only one citizen per call. Batched, the calibrated prompts
  fall to about a constant's score, and even alone the shipped one agrees on 15 of 24
  bank cases.

---

*Sourced from `fast_api_voter/scripts/`:
`check_logprob_blank_calibration_results.md`,
`check_logprob_response_stance_tracking_results.md`,
`check_logprob_coalition_action_tracking_results.md`,
`check_logprob_pressure_action_gap_tracking_results.md`,
`check_per_citizen_sampling_premise_results.md`,
`check_pressure_missing_threshold_results.md`,
`check_pressure_calibration_matrix_results.md`,
`check_pressure_shipped_wiring_results.md`,
`check_response_calibration_results.md`,
`check_coalition_calibration_results.md`,
`check_base_vs_instruct_results.md`,
`check_vllm_collapse_signatures_results.md`,
`check_base_vs_instruct_gate_results.md`,
`check_pressure_gap_tracking_geometry_b_results.md` and
`bakeoff_s24_first_wave_results.md`. The instrument is
`fast_api_voter/api/domain/polity/llm_logprob_instrumentation.py`. The aggregate counts
are in [`observations.md`](../plan/polity/observations.md) (OBS-007), the table of fit decision types is
[`fit-for-inference.md`](../plan/polity/fit-for-inference.md), and the threshold probe is
[OBS-045](../plan/polity/observations.md#obs-045). The French synthesis of the whole programme is
[`synthese-programme-llm-2026-09-10.md`](../plan/polity/synthese-programme-llm-2026-09-10.md).*
