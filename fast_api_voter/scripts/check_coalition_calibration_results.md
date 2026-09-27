# coalition_decision's collapse survives calibration — Track B2, 2026-09-11 (NEGATIVE)

## What was already known

`check_logprob_coalition_action_tracking_results.md` measured `P(action=1, JOIN)` staying within
**0.965–0.999** across five points spanning a join-obvious (identical platform, initiator needs
this party) to decline-obvious (maximally distant platform, initiator already has a majority
alone) spectrum, at real production batch size (5 responders together). Pole-to-pole difference
**-0.0026** (negligible), full spread **0.0345**, non-monotonic (the low point sits at the t=0.5
midpoint, not either extreme).

`distance_to_initiator` (`build_coalition_user_prompt`) is sent with no reference at all.
`polity-decision-contracts.md`'s own §3 names the gap and the intended fix: "une échelle non
prescriptive existe et est déjà calculée ailleurs : la distance moyenne entre partis de
l'assemblée."

## What was added

`build_coalition_system_prompt_calibrated` (`llm_behavior_engine.py`) — one new sentence stating
the mean pairwise distance among every **seated** party in the assembly (initiator included),
computed from `party_platforms` already available at the call site. Deliberately not the
geometric maximum (`sqrt(issue_count)`, ≈4.47 at the shipped 20 dimensions): two real
citizen-generated platforms essentially never land at that theoretical extreme, so it would be
true but uninformative — the same reasoning that made pressure_action's own calibration choose an
empirical reference (`blank_threshold`) over an abstract one.

## Method

`check_coalition_calibration.py` — the exact same script as the uncalibrated baseline
(`check_logprob_coalition_action_tracking.py`), one line changed: the system prompt builder. Same
5 fixed responder platforms, same institutional-shortfall sweep, same diagonal reading, same real
5-party batch, same model.

## Result: no meaningful change

| t | distance | shortfall | P(action=1), baseline | P(action=1), calibrated |
|---|---|---|---|---|
| 0.00 (join-obvious) | 0.000 | 25.0 | 0.999374 | 0.999888 |
| 0.25 | 1.118 | 16.0 | 0.992539 | 0.998012 |
| 0.50 | 2.236 | 8.0 | 0.964855 | 0.953275 |
| 0.75 | 3.354 | 0.0 | 0.999015 | 0.995318 |
| 1.00 (decline-obvious) | 4.472 | 0.0 | 0.996777 | 0.999497 |

Pole-to-pole difference: **-0.000391** (baseline: -0.0026 — *smaller* in magnitude, not larger).
Full spread: **0.046613** (baseline: 0.0345 — marginally wider, still negligible in absolute
terms). The dip sits at the **same** t=0.5 midpoint in both the baseline and the calibrated run,
with a comparable magnitude (0.965→0.953) — the shape did not change, only moved by noise-scale
amounts.

**Verdict: no restored sensitivity.** Unlike B1 (`representative_response`), where the calibrated
prompt broke the collapse cleanly at one identifiable point, this signal gave the model nothing to
differentiate on. Every point, at every distance from identical to maximally opposed, still reads
"join" with ≥95% confidence.

## What this means, and what it does not

**Not shipped.** `decide_coalition` still calls the uncalibrated `build_coalition_system_prompt`.
`coalition_decision` stays in `viz_export.py`'s `_UNVERIFIED_DECISION_TYPES` unchanged —
`cohabitation_rate`/`coalition_lifespans` remain unverified.

This is a genuine negative result, not a wasted attempt: it narrows what "C3 missing scale" can
explain. The hypothesis cleared cleanly for `pressure_action` (Phase C/D/E, 100% on the
unambiguous subset at batch 1) and partially for `representative_response` (B1, a real
zero/nonzero distinction). It does **not** clear here. Two readings, neither established by this
probe alone:

1. **The reference chosen is not the right one.** Mean pairwise distance describes the assembly's
   overall dispersion, not necessarily what a party actually weighs when deciding to join — a
   party might reason instead about its distance relative to the *initiator specifically*
   (already given, unscaled) or about the *coalition's* resulting median position, neither of
   which this fix supplies.
2. **The collapse is not primarily a missing-scale problem for this type.** "Join a governing
   coalition when invited" may be a policy the model converges to for institutional reasons largely
   independent of ideological distance — joining is nearly always personally advantageous
   (access to power, patronage, avoiding being left in opposition) regardless of platform
   agreement, which is a `real-world-plausible` policy, not obviously a defect, even though it
   fails this project's own "distance should matter" behavioural contract (`polity-decision-
   contracts.md` §3's own dt=9 entry: "à situation institutionnelle égale, un parti proche
   rejoint plus souvent qu'un parti éloigné").

Neither reading is settled here. Revisit only with a new, specifically-targeted probe — most
likely one that isolates whether the model is weighing `distance_to_initiator` **at all** (e.g. a
probe holding institutional shortfall fixed at a genuinely marginal value, where joining or not
should be a closer call, and sweeping distance alone) before attempting a second calibration
signal.
