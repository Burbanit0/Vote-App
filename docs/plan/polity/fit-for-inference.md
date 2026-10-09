# Fit for inference: which LLM decisions a claim may rest on

> **status:** living table. Update a row when its evidence changes, and cite the source.
> Started 2026-10-08 for `docs/plan/PLAN_BEYOND_CI.md` W2.3.

**The rule.** A result may rest only on decision types marked **validated** here, or on a
type whose role in that claim has been checked directly. For the threshold experiment,
that check is W2.1's gate probe on forum `found`.

Every row comes from an existing measurement; this table adds no new evidence. The terms
follow `plan-decision-quality-validation.md`:

- **Validated**: at least 90% agreement with a deterministic rule on unambiguous cases
  (Group A).
- **Collapse**: the answer stays fixed whatever the input.
- **Sensitivity**: the answer moves with the state it should depend on, more than with the
  wording. Measured by `check_agent_prompt_neutrality.py`.

**Where this differs from the plan's provisional list (W2.3).** That list was written
before these sources were reread.
- `candidacy_considered` keeps "unverified", but with its measured agreement shown.
- `vote_cast` is validated **at the bar**, not above it.
- Forum `party_move` is unverified for accuracy, but its sensitivity has been checked.

## Crowd decisions (batched, closed codes)

| Decision type | Verdict | Evidence | Open |
|---|---|---|---|
| `vote_cast` | **Validated, at the bar** (audit only in production) | Agreement with the first-choice rule: 36/40 = 90.0% [76.9, 96.0] (`fast_api_voter/scripts/bakeoff_request_arms_results.md`). Logprob instrument: 16/16 aligned on 2026-09-10 (synthesis §1). Qwen's own gate has read 13/16 since the 2026-09-15 control on vLLM 0.28, and the 0.30/0.31 bumps left it there (`fast_api_voter/scripts/check_vllm_031_bump_results.md`). | Production ballots are `utility_ballot` in both engines. The LLM answers a 10% sample, which is not counted. OBS-023 and OBS-024 are open. |
| `candidacy_considered` | **Unverified** | No collapse: 5/5 on the signature test (`plan-adversarial-framing-collapse.md`). The Group A protocol on unambiguous cases was not run. Agreement with the ambition threshold over *all* cases is 318/500 = 63.6% (S2.4 bank, `plan-polity-build-order.md`) and 69% on the p100 runs (OBS-011). | About 40% of citizens declare at every election (OBS-011), and the outcome and the motif disagree. |
| `party_nomination_choice` | **Unverified** | Pilot with ground truth: 4/5 = 80%, no collapse (`plan-decision-quality-validation.md`, `plan-adversarial-framing-collapse.md`). | OBS-006 (out-of-range answers), OBS-013 (choices lean toward the last-listed candidate). |
| `pressure_action` | **Collapsed under the shipped menu** | Under `electoral_only`, the shipped menu, P(act=4) ≥ 0.976 for every citizen, with separation +0.004 (synthesis §2). Group A pilot: 25.0% then 41.7% disagreement (`plan-decision-quality-validation.md`). With the menu opened it does act: 29/70 acting codes (correction of 2026-08-31 in `docs/claude-memory/project_polity_pressure_action_collapse_investigation.md`). | Not in `_UNVERIFIED_DECISION_TYPES`, so digests do not flag metrics derived from it. |
| `representative_response` | **Collapsed** | P(stance=1) = 1.000000 ± 0.000001 over 9 points (synthesis §2). After the partial fix of 2026-09-11 (OBS-007, Track B1), real runs still answer CONCESSION: 299 of 304 non-fallback answers on p100, 33 of 33 in p500 seed 1, 25 of 32 in seed 2 (the other 7 are SILENCE) (OBS-007). The probe is flat on Granite and Gemma too (`fast_api_voter/scripts/bakeoff_s24_first_wave_results.md`). It is listed in `_UNVERIFIED_DECISION_TYPES`. | OBS-007 is open. |
| `coalition_decision` | **Collapsed** | P(action=1) = 0.965–0.999 everywhere, at real batch size too (synthesis §2). Flat on Granite 4.2 8B and Gemma 4 12B (`fast_api_voter/scripts/bakeoff_s24_first_wave_results.md`). It is listed in `_UNVERIFIED_DECISION_TYPES`. | In the exploration profile, party-leader agents negotiate coalitions instead (ADR-019). |
| `reaction_to_event` | **Unverified** | SCANDAL: the collapse was already resolved on vLLM (synthesis §6), with no accuracy measure since. ECONOMIC_SHOCK: P(motif=402) = 1.0 at every magnitude, "measured, not classified as a collapse" (synthesis §2). | The ECONOMIC_SHOCK reading. OBS-025: batches of 25 fall back whole when the model overshoots the reaction cap. |
| `campaign_positioning` | **Unresolved** | No collapse; its content varies between nominees and poles (`plan-adversarial-framing-collapse.md`). | A separate defect is open (`plan-decision-quality-validation.md`). OBS-022: positioning prompts hit the token limit. |
| `chamber_deliberation` | **Unresolved** | The prescribed pole is correct (3/3). On the derived pole, an "active adjustment" motif came with no adjustment; that label is corrected in production (`plan-adversarial-framing-collapse.md`). | OBS-021: 5–12% fallback from shift caps. |

## Agent turns (free text plus a schema, one citizen at a time)

These are gated by sanity checks and OBS entries (`plan-polity-agency-roadmap.md` D4).
None is validated for accuracy. The two rows below have had their sensitivity checked,
which is weaker.

| Turn | Verdict | Evidence | Open |
|---|---|---|---|
| Forum `party_move` | **Unverified; sensitive to its state; one dead option** | Neutrality probe, n=30: `found` moves 97% with the co-founder count, the paraphrase moves 6%, and `leave` is never chosen (PR #861, `fast_api_voter/scripts/check_agent_prompt_neutrality_d2_results.md`). Wording alone once kept `found` at 0 (OBS-029, fixed by rewording). | **The W2.1 gate:** does `found` move with the stated seat threshold? It needs a GPU run after the D2 change. |
| Amendment ballot (chamber) | **Unverified; sensitivity checked** | OBS-030 and OBS-038; the neutrality harness `ballot` probe. | Ballot reasons echo the proposer's (OBS-038). |
| President, nominee, coalition leader, extra-legal act | **Unverified; sanity checks only** | OBS-028, OBS-035, OBS-041, OBS-043; the neutrality harness `president` and `campaign` probes. | No accuracy measure. |

## What this means for W2.1

- **The primary outcome is the forum's `found` rate.** It is an agent turn, not a crowd
  decision. It becomes fit only once the gate shows `found` responding to the stated
  threshold; until then the experiment does not run.
- **`leave` is a dead option in the probe.** W2.1 names "the `found` and `leave` rate". A
  leave rate would measure nothing, so the pre-registration should report it and not test
  it. That is a change to W2.1's wording, to be made in the pre-registration.
- **The gate compares 3% with 7%; the main run compares 3% with 5%.** A gate PASS shows the
  channel exists, but does not promise a response at 3 vs 5. The pilot should size n on the
  3-vs-5 difference.
- **ENP by votes is not LLM-free in the exploration profile.** The legislative vote itself
  is a rule (`choose_party`). But with `policy_retrospection` at 2.0 it weighs the governing
  parties' record, and several of its inputs come from agent turns that are not validated:
  - party-leader agents negotiate the governing coalition (ADR-019);
  - citizens' positions drift through forum opinion change (ADR-016/017);
  - issue weights move with campaign salience (ADR-023).

  A vote-ENP result is a result about this whole society and should be stated that way. The
  re-seating script (W2.2 item 4) separates the threshold's purely mechanical part.
