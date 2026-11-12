---
name: project-polity-pressure-action-collapse-investigation
description: "State of the pressure_action/relational-framing LLM collapse investigation on branch fix/polity-pressure-action-quality-investigation — 4 confirmed collapses, Phase 2 remediation all negative, but campaign_positioning's separate Mode A bug fixed (first real win)"
metadata: 
  node_type: memory
  type: project
  originSessionId: 22458a2f-ddf0-45bc-bb54-2e029e1a45ce
  modified: 2026-09-01T01:21:10.178Z
---

**MAJOR CORRECTION 2026-08-31 — read this first.** `pressure_action` does NOT collapse. 18 of its
20 diagnostic scripts ran under the shipped `pressure_menu` (`electoral_only: true`), where
`menu_acts()` = `(0, 4)` and the production prompt declares acting codes 1/2/3 FORBIDDEN — while
the harness ground truth demanded exactly those codes. Every "0/70 acting codes", "0/17 on the
should-act pole", and the §3.1/§3.2 "identical 17/70 failures" measured that constitutional
constraint, not model behavior. Menu opened, same 70 citizens, same prompt: **29/70 acting codes
emitted** (`check_pressure_action_open_menu_baseline.py`). What remains real is a **quality**
problem — 60.0% agreement vs an 80% bar, independently consistent with the one always-valid
earlier measurement (`check_pressure_action_quality_pilot.py`, which opens the menu explicitly:
41.7% disagreement). See [[feedback_llm_mode_a_truncation_diagnosis]] for the method lesson.

Branch `fix/polity-pressure-action-quality-investigation` (based on `polity`) investigates a
content-quality bug: 3 LLM decision types (`representative_response`, `coalition_decision`,
`reaction_to_event` SCANDAL branch) show a "collapse" where the model ignores real per-citizen
signal and returns the same output on opposite poles. Their option sets are NOT config-gated
(`Stance` 1-4, `CoalitionAction` JOIN/LEAVE always available), so the defect that destroyed
`pressure_action`'s evidence does not mechanically apply — but each still needs that check
explicitly before being re-cited, and each rests on only a 4-6 trial signature.

**Theory**: framed as act/response vs. threshold — decisions asking the model to choose an
act/response toward an external target collapse; decisions asking for a self-assessment against a
threshold (`candidacy_considered`, `party_nomination_choice`) do not.

**Phase 2 remediation (`plan-pressure-action-resolution.md`), concluded 2026-08-31, all negative**:
temperature=0.7 (1/5, same signature as 0.3), removing Ollama's grammar-constrained decoding
entirely (0/17 on the informative subset — the apparent 75.7% "pass" was a base-rate artifact from
class imbalance), few-shot with 2 worked examples (0/16, zero acting codes ever emitted despite an
explicit in-context example). Phase 3 (combinations) does not open — no individual path showed any
signal. Phase 4 (a `sort_keys=True` scoping effort to unblock reasoning-field-first schema
reordering) is the only remaining identified path but requires its own separate scoping decision,
not opened as a shortcut.

**`campaign_positioning` was suspected as a 5th collapse case (act/response-shaped) but is NOT
one** — content genuinely varies between nominees and poles at n=32 (theory's own "4/4" headline
corrected to "4/5" in `plan-adversarial-framing-collapse.md`). It DOES have a separate, unrelated
completion-reliability bug: 25% of `size=1` calls fail (truncation dominant), traced by reading
full raw `message.reasoning` traces (not just repeated-fragment summaries) to the same Mode A
non-convergent-reasoning-loop signature already fixed once for `chamber_deliberation` — see
[[feedback_llm_mode_a_truncation_diagnosis]]. **This one WAS fixed** (disambiguation sentence in
`build_positioning_system_prompt`, validated live 0/9 vs 6/6 pre-fix) — the first real remediation
win across this whole investigation. A second, distinct truncation cause on the same decision type
(a model-internal array-transcription artifact, not a prompt ambiguity) remains unfixed and
unconfirmed either way (n=3 clean post-fix, too small to call resolved).

**How to apply**: the 4 confirmed act/response collapses still have zero working mitigations —
don't assume the `campaign_positioning` win transfers to them (different bug entirely: content
collapse vs. completion failure). If resuming this branch, check `plan-pressure-action-resolution.md`
and `plan-adversarial-framing-collapse.md` for the current state before proposing new tests — both
are kept meticulously up to date with every result, including corrected/retracted claims.
