---
name: feedback-llm-mode-a-truncation-diagnosis
description: "Methodology for diagnosing LLM truncation bugs — read full raw reasoning traces before writing a fix, check the pivot point, verify suspected data mismatches against the actual request body"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 22458a2f-ddf0-45bc-bb54-2e029e1a45ce
  modified: 2026-09-01T01:21:20.555Z
---

When an LLM call truncates (`finish_reason='length'`) despite a generous token budget, don't
assume more budget will fix it — check whether it's "Mode A" (unbounded, non-convergent reasoning
loop, no budget fixes it) vs "Mode B" (genuine long content, budget alone fixes it) before touching
anything. A token count alone cannot distinguish the two.

**Why**: confirmed twice on the Polity project — `chamber_deliberation` and `campaign_positioning`
both had "budget already raised, still truncating at a real rate" bugs that turned out to be Mode A,
fixed by a targeted prompt disambiguation, not a budget change. In both cases `complete_json`'s own
extractors raise an exception the instant `finish_reason != "stop"`, discarding
`message.content`/`message.reasoning` before the caller ever sees them — a raw HTTP call bypassing
the wrapper is required to see the actual reasoning trace at all.

**How to apply**:
1. Bypass the client wrapper with a raw call that captures the full response regardless of
   `finish_reason` (mirror the production request body exactly — same endpoint, same shape).
2. Don't stop at a "top N repeated fragments" summary — read the actual trace text. A repeated
   fragment alone tells you THAT it loops, not WHERE the reasoning goes wrong or WHY.
3. Check the **pivot point**: does the model reach a substantively correct/complete answer before
   the loop starts, or is the loop present from the very beginning? If the answer was already
   settled and the loop is about output *format*, the fix is a disambiguation sentence, not a
   decision aid. If the model never gets anywhere near a real answer, that's a different, harder
   problem (see below — not every truncation shares one cause, even on the same decision type).
4. When a trace's rumination claims a **data mismatch** (e.g. "the array should have N entries but
   I see M"), verify against the actual request body sent — don't assume the model is right, and
   don't assume it's a prompt bug without checking. On `campaign_positioning`, one truncation cause
   turned out to be the model silently truncating its own transcription of a 20-element array to
   10 while reasoning, then "discovering" a phantom conflict with a correctly-sized second array —
   an internal artifact, not a data or prompt bug, and not fixable by rewording anything.
5. Don't assume all truncations on the same decision type share one root cause. Read each reproduced
   trace individually — they may split into genuinely distinct mechanisms (3/4 shared one fixable
   cause, 1/4 was unrelated on this project).
6. After a fix, validate live on the exact cases that were failing, with enough repetitions to
   account for non-determinism (a case that failed once or twice pre-fix needs multiple post-fix
   reps before calling it resolved — n=2 or n=3 is not enough either direction).
7. Never claim a second, adjacent bug is fixed just because it happened to come back clean in the
   same validation run — a coincidental small-n result is not evidence, especially when the applied
   fix has no plausible mechanism to affect that second bug.

**Before the first call of any LLM quality test: verify the expected answer is ALLOWED by the
configuration under test.** On Polity this went unchecked for weeks and destroyed an entire
investigation: 18 of 20 `pressure_action` diagnostic scripts asked the model to emit act codes
1/2/3 while the shipped `pressure_menu` (`electoral_only: true`) made `menu_acts()` return `(0, 4)`
and the prompt itself said "CONTRAINTE ABSOLUE ... [0, 4]". The model refused, correctly, every
time — and that refusal was recorded as a "content-blind collapse", spawning a whole theory. Two
tells that should have caught it far earlier: (a) a metric pinned at *exactly* zero across every
variant tried, which is more often a constraint than a behavior, and (b) two independent
remediations "failing identically" — identical numbers usually mean both measured the same
constant, not that both failed. Read the model's own reasoning trace early: this one stated the
constraint in its first sentence.
