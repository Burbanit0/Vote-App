# reaction_to_event/ECONOMIC_SHOCK: closing a genuinely untested gap, and a real instrumentation bug found along the way — plan-llm-protocol-and-theory-program.md §5.C

## Why this branch, not a SCANDAL re-measurement

`decide_reaction_to_event`'s own RELIABILITY WARNING already marks the SCANDAL branch's
original collapse RESOLVED on vLLM/AWQ (2026-09-06): salience_delta varied directionally
sensibly (0.20 vs 0.15) across the original two poles, no collapse. Re-measuring an
already-resolved branch continuously would have been the lowest-value use of the §5.C
instrument among the four originally-flagged decision types. The same docstring names a real,
still-open gap instead: *"ECONOMIC_SHOCK's target is always null ... neither the original
warning nor this resolution should be assumed to transfer to that branch without its own check
-- still untested, either backend."* This probes that branch specifically, via its own
distinguishing signal: `magnitude` (unique to ECONOMIC_SHOCK; SCANDAL has no analogue).

## A real instrumentation bug found live, and the general fix

First attempt located the `motif` field's token at its default (first-character) offset and
got a suspiciously uniform `P(motif=402)=0.500000` at every single point. Investigation: this
project's whole motif codebook groups codes by a shared leading digit
(`401`/`402`/`403` for `ReactionMotif`, `501`/`502`/`504`/`505` for `CoalitionMotif`, etc.) —
`locate_decision_field_logprobs`'s existing offset-0 default locates a token covering only the
value's first character, which for `401` vs `402` vs `403` is the SAME "4" every time, telling
you nothing. `binary_probability`'s own documented "neither candidate captured" fallback
(0.5) correctly reported "unmeasured" rather than fabricating a wrong number — but a caller
still has to recognize a suspiciously flat reading as that symptom rather than a real finding.

Fixed generally, not just worked around in this one script: `locate_decision_field_logprobs`
gained a `value_char_offset` parameter (default 0, fully backward compatible — every existing
call site and its tests are unaffected) letting a caller target the actual discriminating
character position for a multi-digit field. 4 new offline tests cover it, including the exact
failure mode (offset=0 lands on the shared "4") and the fix (offset=2 lands on the
discriminating digit, correctly, whether that digit is tokenized alone or grouped with
preceding digits into one token). Re-run with `value_char_offset=2`: the located token's own
text turned out to be a bare single digit ("2" or "3"), confirming empirically (not assumed)
that this specific completion tokenized the motif value digit-by-digit rather than as one
3-character token.

## Result: P(motif=402, reacts) = 1.000000 at every magnitude tested

15 real citizens across 5 magnitude points (0.05, 0.40, 0.75, 1.10, 1.50 — crossing
`events.economy_shock_threshold=0.5` partway through), 3 per call, `event_salience=0.0` fixed
for every citizen (isolates magnitude's own effect; SCANDAL's own resolution already
established prior salience's effect separately). Real `build_reaction_system_prompt`/
`build_reaction_user_prompt`, real `REACTION_JSON_SCHEMA`, `think=False` (this decision type's
own production value). 15/15 aligned.

| magnitude | mean P(motif=402) |
|---|---|
| 0.05 | 1.000000 |
| 0.40 | 1.000000 |
| 0.75 (major) | 1.000000 |
| 1.10 (major) | 1.000000 |
| 1.50 (major) | 1.000000 |

Zero spread. Every citizen, at every magnitude including the smallest tested (0.05 — an order
of magnitude below the "major" threshold), was judged to have a personally relevant reaction
with certainty. `motif=403` (EVENT_PERSONALLY_IRRELEVANT) was never chosen even once.

## Reading this carefully — what this does and does not establish

This closes the CATEGORICAL half of the previously-untested gap: does the model ever treat an
economic shock as personally irrelevant, and does that categorical choice track severity? Not
tested at any of the 5 magnitudes tried. It does NOT test the other, arguably more informative
half: `salience_delta`'s own graded INTENSITY (how much the citizen reacts, not whether they
react at all) — a float field, out of `locate_decision_field_logprobs`'s current scope for the
same reason a coarse `value_char_offset` cannot cleanly target a multi-digit decimal's most
informative digit the way it can a 3-digit motif code. Whether reaction intensity scales with
shock severity remains genuinely open.

Worth stating plainly rather than over-reading: unlike the four types this session's other
§5.C applications measured (which showed the SAME action regardless of ctx, the collapse
signature this project has been chasing), "always personally relevant" for an economy-wide
shock is not obviously wrong the way "always concede" or "always join" is — a systemic
economic event plausibly does touch everyone to some degree, unlike a scandal a disengaged
citizen might reasonably shrug off. This measurement establishes the categorical choice is
flat, not that the flatness is necessarily a defect; whether it should track magnitude at all
is a modeling question this measurement surfaces but does not answer.

## Disposition

`locate_decision_field_logprobs`'s `value_char_offset` parameter is a general, reusable fix
available to any future motif-field instrumentation, not specific to this branch.
`decide_reaction_to_event`'s docstring updated with a dated note narrowing, not fully closing,
the "ECONOMIC_SHOCK ... still untested" gap: the categorical branch is now measured, the
`salience_delta` intensity question is not.
