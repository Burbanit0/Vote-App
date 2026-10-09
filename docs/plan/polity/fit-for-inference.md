# Fit for inference: which LLM decisions a claim may rest on

> **status:** living table. Update a row when its evidence changes, citing the source.
> Started 2026-10-08 for `docs/plan/PLAN_BEYOND_CI.md` W2.3.

**The rule.** A result may rest only on decision types marked **validated** here, or on a
type whose role in the claim has been checked directly. That check is W2.1's gate probe for
the threshold experiment's channel (forum `found`/`leave`).

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
| `vote_cast` | **Validated** (where it is used) | Logprob instrument: 16/16 alignments, 16/16 correct, separation 0.997 vs 0.049 (`synthese-programme-llm-2026-09-10.md` §1). 23/24 against the rule (ADR-011). | In production it is **audit only**: ballots are `utility_ballot` in both engines and the LLM answers a 10% sample that is not counted. OBS-023 (thinking budget binds at p500) and OBS-024 (a batch of three answering for one voter) are open. |
| `candidacy_considered` | **Unverified** | Collapse ruled out by signature only (4–6 extreme cases); the Group A protocol was not run (`plan-decision-quality-validation.md`, table "Statut mis à jour"). | About 40% of citizens declare at every election (OBS-011), and the outcome and the motif disagree. |
| `party_nomination_choice` | **Unverified** | Pilot with ground truth: 4/5 = 80%, below the 90% bar (same table). | OBS-006 (out-of-range answers), OBS-013 (choices lean toward the last-listed candidate and do not match the stated reason). |
| `pressure_action` | **Collapsed** (marked unreliable) | Group A pilot: 25.0% then 41.7% disagreement (`plan-decision-quality-validation.md`). P(act=4) ≥ 0.976 for every citizen, separation +0.004 (synthesis §2). | Remediation attempts all negative (`docs/claude-memory/project_polity_pressure_action_collapse_investigation.md`). |
| `representative_response` | **Collapsed** | P(stance=1) = 1.000000 ± 0.000001 over 9 points (synthesis §2). Listed in `_UNVERIFIED_DECISION_TYPES` (`viz_export.py`), so every LLM digest flags it. | — |
| `coalition_decision` | **Collapsed** | P(action=1) = 0.965–0.999 everywhere, at real batch size too (synthesis §2). The collapse persists on Granite 4.2 8B and Gemma 4 12B (`scripts/bakeoff_s24_first_wave_results.md`). Also in `_UNVERIFIED_DECISION_TYPES`. | In the exploration profile, coalitions are negotiated by party-leader agents instead (ADR-019). |
| `reaction_to_event` | **Partly** | SCANDAL: the collapse was already resolved on vLLM (synthesis §6). ECONOMIC_SHOCK: P(motif=402) = 1.0 at every magnitude, measured but not classified as a collapse (synthesis §2). | The ECONOMIC_SHOCK branch. |
| `campaign_positioning` | **Unresolved** | Neither flat collapse nor clean behaviour (`plan-validation` table, `plan-adversarial-framing-collapse.md`). | OBS-022 (positioning prompts hit the token limit). |
| `chamber_deliberation` | **Unresolved** | Answers the state the prompt prescribes, but pairs an "active adjustment" motif with an empty shift list on one pole (same sources). | OBS-021 (5–12% fallback from shift caps). |

## Agent turns (free text plus a schema, one citizen at a time)

These are gated by sanity checks and OBS entries (`plan-polity-agency-roadmap.md` D4). Except
for the two prompts below, none has been validated for inference.

| Turn | Verdict | Evidence | Open |
|---|---|---|---|
| Forum `party_move` | **Sensitive to its state; one dead option** | Neutrality probe, n=30: `found` moves 97% with the co-founder count, the paraphrase moves 6%, `leave` is never chosen (`scripts/check_agent_prompt_neutrality_d2_results.md`, PR #861). | **W2.1 gate.** Does `found` move with the stated seat threshold? It needs a GPU run after the D2 change. |
| Amendment ballot (chamber) | Sensitivity checked (OBS-030, OBS-038) | The neutrality harness `ballot` probe. | Reasons echo the proposer's (OBS-038). |
| President, nominee, coalition leader, extra-legal act | Sanity checks only | OBS-028, OBS-029, OBS-035, OBS-041, OBS-043. The neutrality harness `president` and `campaign` probes. | No accuracy measure. |

## What this means for W2.1

- **The threshold experiment's primary outcome is the forum's `found`/`leave` rate.** That is
  an agent turn, not a crowd decision. It is fit only once the gate shows `found` responding to
  the stated threshold. Until then the experiment does not run.
- **`leave` is a dead option** in the probe. A "leave rate" outcome would measure nothing, so
  the pre-registration should rest on `found` and on ENP by votes, and report `leave` without
  testing it.
- **ENP by votes depends on the legislative vote.** That vote is `choose_party` (nearest
  platform), a deterministic rule, not an LLM decision. So the secondary outcome inherits no
  LLM validity question beyond who founds which party.
