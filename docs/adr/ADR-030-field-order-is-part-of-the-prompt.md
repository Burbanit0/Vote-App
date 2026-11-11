# ADR-030: the order of a schema's fields is part of the prompt, chosen by measurement

**Status**: Accepted (owner, 2026-10-19); first table set by the owner, 2026-10-20 (below).
**Date**: 2026-10-19
**Context**: Under constrained decoding the model writes an object's fields in the order the schema sends
them. The vLLM client sorted the request body's keys for a future cache key, so every object reached the
model alphabetically, never in the order `llm_schemas.py` declares (OBS-050). That order is not neutral:
it caused the 2026-09-06 whitespace loop, vLLM 0.32's empty `shifts` (EXP-025), and on the frozen bank it
moves `pressure_act` from 62.5% (alphabetical) to 79.2% (the declared order) or 45.8% (the reason code
first, which made the model act for 23 of 24 citizens). The literature agrees that the order matters and
that no general rule holds ("Let Me Speak Freely?", EMNLP 2024; Castillo on Gemini's key sorting; "Capacity,
Not Format", 2026). The owner: "I already had the reflection and don't want to have it every month."

## Decision

- **One table decides the order.** `llm_client.WIRE_ORDER` maps a decision class's name to the order its
  fields are sent in. A class it does not list, and every nested object and agent turn, goes out
  alphabetically, byte for byte as before. The table started empty; its first entries are the owner's
  (below). Each session records the order it sent, so a verdict is always against what its controls sent.
- **The table is filled by a test, not by reasoning.** `scripts/check_schema_order.py`:
  - `isolation` (no GPU): every candidate changes key order and nothing else;
  - `run`: two control sessions (production's table, the same bytes twice, on either side of a server restart:
    `--restart-between-controls`) and one session per candidate on
    the order bank (`case_bank_order.jsonl`: 144 pressure and 160 vote units of ground truth, 500 candidacy);
  - `decide`: the rule below, written before any run, and `check_schema_order_results.md`.
- **The candidates** are the id first, then the six orders of the decision, what depends on it, and the
  `motif` code (`schema_order.RULES`), plus alphabetical.
- **The rule.** A candidate replaces a class's current order only if, on that class's primary measure (its
  largest ground-truth family, else its validity), it:
  - beats the first control (paired McNemar, Holm across that class's distinct candidate orders, p < 0.05:
    arms that send it the same order are one candidate);
  - also beats the second control;
  - does not lower validity significantly;
  - does not put 95% of units on one answer where the control gives no answer to 80%.
  The noise floor comes from the two controls only; a candidate is assumed to be as noisy as they are (the
  plan's second session per candidate was not built).
  A measure whose two controls disagree on more than 10% of units cannot decide: the class keeps its order
  (on the first run every measure had 0% noise; `positioning_poles`, 9 of 10 answers changing on identical
  bytes, is left out of the order bank). Without a winner, nothing changes.
- **Then live.** `scripts/schema_order_live_ab.sh` runs the candidate table against a control that differs
  only in `WIRE_ORDER` (exploration profile, p100, 10 seeds by default, both arms at once on one server) and
  `schema_order_live_report.py` applies the second gate (below, "The 8-year A/B and the second gate"): an
  exact sign-flip test by seed, Holm across the measures it can test (elections, recalls, occupancy,
  pressure inaction, forum mind-shift, fallbacks, retries). It replaced the first gate, "every measure within
  the two controls' range", which a candidate with no effect passes only one time in three per measure. The first gate rejected the motif-first order (pressure inaction
  0%, forum mind-shift 0.6%), passed the first table at 4 years once fallbacks and retries were made
  one-sided after a failed first report (a change made after seeing a result), and failed it at 8 years.
- **When to re-run, and only then:** a vLLM or xgrammar version, a model or quantisation, a decision class
  gaining, losing or renaming a field, a rewrite of a decision's system prompt. A test pins `WIRE_ORDER`
  and names each class's fields; `llm_client.py` is in `PROMPT_SOURCE_FILES`, so a run records it.

## Consequences

- Request hashes, goldens and replay logs are unchanged: the order is applied on the wire, after the hash.
- A change of `WIRE_ORDER` changes behaviour like a prompt change: runs before and after are not comparable
  decision by decision, and its PR carries the results doc and the live report.
- Not covered yet: `reaction_to_event`, `chamber_deliberation`, `coalition_decision` and
  `party_nomination_choice` are measured on validity over 4 to 10 cases, which cannot show a 10-point change;
  the agents' turns and nested objects (`PositionShift`) have no ground truth, and their
  declared order was where last night's forum and chamber regressions came from; they stay alphabetical until
  a bank family can measure them. `campaign_positioning` is not in the order bank (too noisy to measure).

## The first table (owner, 2026-10-20)

The first sweep (`check_schema_order_results.md`, vLLM 0.31.0) found no order that passes the rule alone:
the reason code before the act is significantly worse on pressure (70-72/144 against 97), and the best orders
lead without reaching significance. The owner set `WIRE_ORDER` to those best orders anyway ("the best looking
order is not always the alphabetic one ... modify it to the optimum for each kind of decision"):

| decision | order | first sweep | alphabetical |
| --- | --- | --- | --- |
| pressure_action | cid, target, act, motif | 107/144 (19 better / 9 worse) | 97 |
| candidacy_considered | cid, outcome, motif | 332/500 (31 / 17, p 0.06) | 318 |
| vote_cast | cid, blank, motif, ranking | 152/160 (3 / 0), logprob gate 16/16 | 149, gate 13/16 |
| representative_response | cid, stance, shifts, motif | 18/18 valid | 17/18 |

Ties were broken on validity and the logprob gate, then on the two findings above: the decision before the
reason code, and `stance` before `shifts` (what decided vLLM 0.32). The five other decisions showed no
difference and stay alphabetical, as do the agents' turns and nested objects. The table ships only after the
live check passes; the next sweep compares candidates against it, with alphabetical as one of them.

## The 8-year A/B and the second gate (2026-10-20)

The table shipped with #967 after the 4-year live check. An 8-year A/B followed (`schema_order_live_ab.sh`,
control 54b7c6da = alphabetical, candidate 21599708 = the table, seeds 1-3, vLLM 0.31.0, 6 h 51 min; EXP-025).
The first gate said **FAIL** on three measures: pressure inaction 43.5% (controls 48.1%, 50.3%), forum
mind-shift 5.3% (4.7%, 4.8%), fallbacks 30 (5, 11). Elections, recalls and occupancy were identical; the retry
rate passed (1.35% against 1.35% and 1.40%).

**The gate, not the table, was the weak point.** "Inside the range of two pooled controls" holds for a
candidate with no effect only one time in three per measure (simulated: 33%), so with seven measures it fails
almost every candidate. By seed, most of the gap is seed-to-seed noise: pressure inaction runs from 31% to 70%
across the control runs, and the table is within 1.5 points of its seed's controls on seeds 1 and 3 (below
both on seed 1, above both on seed 3); only seed 2 is clearly lower (45% against 68% and 70%). The fallbacks
are failed chamber sessions (the model answers for 1 of 5 members): 6 sessions against 1 and 2, 5 of them in
one run, on a decision whose bytes the table does not change.

**Decision (owner, 2026-10-20): keep the table.** This overrides a pre-registered gate a second time, and is
stated as such. The 8-year runs are not re-judged under the second gate: a rule chosen after seeing the data
it judges is not a test.

**The second gate**, fixed before any run that uses it (`schema_order_live_report.py`):
- **One control, not two.** Two runs of the same code with the same seed send the same bytes and replay the
  same events until batching noise parts them: in the 8-year runs ctl-a and ctl-b shared their first 146,
  151 and 115 events (seeds 1-3), the table parted from both after 14, 1 and 7. Two controls are therefore
  closer to each other than to any candidate, and a test treating the three runs of a seed as exchangeable
  raises false alarms: with no effect, one measure comes out below 0.05 in 10% to 15% of simulated runs
  (controls correlated 0.5 to 0.8, 6 seeds), not 5%. One control run and one candidate run per seed, started
  together on one server, are exchangeable if the order changes nothing.
- **The test**: per seed, the difference new - ctl; the statistic is its mean; the exact p-value is the share
  of the 2^k sign flips that reach it (two-sided for behaviour, one-sided for fallbacks and retries). A seed
  where the two runs agree, or where either has no such decision, cannot vote. Holm at 0.05 across the
  measures that can be tested: a measure equal in every run is "same"; the family is the largest set of the
  measures with the smallest reachable p-values (2^-k over the seeds that differ, twice that two-sided) that
  Holm could reject in full, and the rest are "cannot tell". Both depend only on which seeds differ, never on
  the signs, so the test stays exact. Simulated with no effect (1,500 trials each, ±1 point): family-wise
  false alarms 1.6% to 4.9% for 6 to 10 seeds.
- **FAIL**: a share (pressure inaction, forum mind-shift) at 0 or 1, or gone (no such decision at all),
  where the control shows a mix, whatever the number of seeds (the motif-first collapse needs no test); or
  fallbacks or retries significantly higher. **CHANGED**: a behaviour measure significantly different either
  way; not a rejection (the order is chosen to change decisions), the owner reads it before shipping. **No
  verdict**: a behaviour measure that varies could not be tested. **PASS**: none of these; the report names
  the failure measures it could not tell.
- **Seeds**: how many are needed depends on how many measures vary. With the four that varied at 8 years
  (pressure inaction, forum mind-shift, fallbacks, retries), the behaviour measures become testable at 7 seeds
  but with almost no power; a shift of 1 standard deviation of the per-seed difference is caught 24% of the
  time at 8 seeds and 51% at 10, a shift of 1.5 56% and 91%. The default is 10 (20 sweeps). Fallbacks are
  sparse (0 in 4 of the 9 runs at 8 years), so they will often be "cannot tell"; the report says so rather
  than passing them.
- **Start order** alternates by seed (odd seeds start ctl first, even seeds new first), so it cannot push
  every seed's difference the same way.
- The next live check re-tests the table this way, alphabetical (`WIRE_ORDER = {}`) as the control.
