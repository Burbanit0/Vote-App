# Fit for inference: which LLM decisions a claim may rest on

> **status:** living table. Update a row when its evidence changes, citing the source.
> Started 2026-10-08 for `docs/plan/PLAN_BEYOND_CI.md` W2.3.

**The rule.** A result may rest only on decision types marked **validated** here, or on a
type whose role in the claim has been checked directly for that claim. For the threshold
experiment, that check is W2.1's gate probe on forum `found`. As of this writing, no type is
validated.

Every row comes from an existing measurement; nothing here is new evidence. The
dimensions follow `plan-decision-quality-validation.md`:
- **Group A**: agreement with a deterministic rule on unambiguous cases. "Validated" means at
  least 90% agreement there.
- **Collapse signature**: does the answer stay fixed whatever the input?
- **Sensitivity**: does the answer move with the state it should depend on, beyond the
  wording's own effect? This is `check_agent_prompt_neutrality.py`.

## Crowd decisions (batched, closed codes)

| Decision type | Verdict | Evidence | Open |
|---|---|---|---|
| `vote_cast` | **At the bar** (audit only in production) | Agreement with the first-choice rule is 36/40 = 90.0% [76.9, 96.0] (`fast_api_voter/scripts/bakeoff_request_arms_results.md`), exactly the bar. The logprob instrument read 16/16 on 2026-09-10 (synthesis §1), but reads 13/16 aligned on the shipped model since vLLM 0.30/0.31 (`fast_api_voter/scripts/check_vllm_031_bump_results.md`). | In production, ballots are `utility_ballot` in both engines; the LLM answers a 10% sample that is not counted. OBS-023 and OBS-024 are open. |
| `candidacy_considered` | **Fails the bar** | Agreement with the ambition threshold: 318/500 = 63.6% (`plan-polity-build-order.md`, S2.4 bank) and 69% on the p100 runs (OBS-011); the bar is 90%. No flat collapse (signature test). | About 40% of citizens declare at every election (OBS-011), and the outcome and the motif disagree. |
| `party_nomination_choice` | **Unverified** | Pilot with ground truth: 4/5 = 80%, below the 90% bar (same table). | OBS-006 (out-of-range answers), OBS-013 (choices lean toward the last-listed candidate and do not match the stated reason). |
| `pressure_action` | **Collapsed under the shipped menu** | Under `electoral_only` (the shipped menu), P(act=4) ≥ 0.976 for every citizen, separation +0.004 (synthesis §2); the Group A pilot disagreed 25.0% then 41.7% (`plan-decision-quality-validation.md`). With the menu opened, it does act (29/70 acting codes: `docs/claude-memory/project_polity_pressure_action_collapse_investigation.md`, correction of 2026-08-31). | Not in `_UNVERIFIED_DECISION_TYPES`, so digests do not flag metrics derived from it. |
| `representative_response` | **Unverified** (was collapsed) | P(stance=1) = 1.000000 ± 0.000001 over 9 points on 2026-09-10 (synthesis §2); partly fixed on 2026-09-11, when the prompt started stating the scales (OBS-007, Track B1). Listed in `_UNVERIFIED_DECISION_TYPES` (`viz_export.py`), so every LLM digest flags it. | OBS-007 is open; no measurement since the fix qualifies it. |
| `coalition_decision` | **Collapsed** | P(action=1) = 0.965–0.999 everywhere, at real batch size too (synthesis §2). The collapse persists on Granite 4.2 8B and Gemma 4 12B (`fast_api_voter/scripts/bakeoff_s24_first_wave_results.md`). Also in `_UNVERIFIED_DECISION_TYPES`. | In the exploration profile, coalitions are negotiated by party-leader agents instead (ADR-019). |
| `reaction_to_event` | **Collapsed** (ECONOMIC_SHOCK); **unverified** (SCANDAL) | ECONOMIC_SHOCK: P(motif=402) = 1.0 at every magnitude (synthesis §2): the answer does not depend on the input. SCANDAL: the collapse was already resolved on vLLM (synthesis §6), with no accuracy measure since. | OBS-025: batches of 25 fall back whole when the model overshoots the reaction cap. |
| `campaign_positioning` | **Unresolved** | Neither flat collapse nor clean behaviour (`plan-decision-quality-validation.md`, `plan-adversarial-framing-collapse.md`). | OBS-022 (positioning prompts hit the token limit). |
| `chamber_deliberation` | **Unresolved** | Answers the state the prompt prescribes, but pairs an "active adjustment" motif with an empty shift list on one pole (same sources). | OBS-021 (5–12% fallback from shift caps). |

## Agent turns (free text plus a schema, one citizen at a time)

These are gated by sanity checks and OBS entries (`plan-polity-agency-roadmap.md` D4). None
is validated for inference; the two below have had their sensitivity checked, which is weaker.

| Turn | Verdict | Evidence | Open |
|---|---|---|---|
| Forum `party_move` | **Sensitive to its state; one dead option** | Neutrality probe, n=30: `found` moves 97% with the co-founder count, the paraphrase moves 6%, `leave` is never chosen (PR #861, `fast_api_voter/scripts/check_agent_prompt_neutrality_d2_results.md`). | **W2.1 gate.** Does `found` move with the stated seat threshold? It needs a GPU run after the D2 change. |
| Amendment ballot (chamber) | Sensitivity checked (OBS-030, OBS-038) | The neutrality harness `ballot` probe. | Reasons echo the proposer's (OBS-038). |
| President, nominee, coalition leader, extra-legal act | Sanity checks only | OBS-028, OBS-029, OBS-035, OBS-041, OBS-043. The neutrality harness `president` and `campaign` probes. | No accuracy measure. |

## What this means for W2.1

- **The primary outcome is the forum's `found` rate.** That is an agent turn, not a crowd
  decision, and it is fit only once the gate shows `found` responding to the stated
  threshold. Until then the experiment does not run.
- **The gate compares 3% with 7%; the main run compares 3% with 5%.** A gate PASS shows the
  channel exists. It does not promise a response at 3 vs 5, so the pilot should size n on the
  3-vs-5 difference.
- **`leave` is a dead option** in the probe. A "leave rate" would measure nothing: report it,
  do not test it.
- **ENP by votes is not LLM-free in the exploration profile.** The legislative vote itself is
  a rule (`choose_party`: nearest platform). But in this profile several things it uses are
  shaped by agent turns, none of them validated:
  - the governing parties' record weighs on it (`policy_retrospection` 2.0), and the governing
    coalition is negotiated by party-leader agents (ADR-019);
  - citizens' positions drift through forum opinion change (ADR-016/017);
  - issue weights move with campaign salience (ADR-023).

  A vote-ENP result is a result about this whole society, and should be stated that way. The
  re-seating script (W2.2 item 4) separates the threshold's purely mechanical part.
