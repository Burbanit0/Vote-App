# ADR-030: the order of a schema's fields is part of the prompt, chosen by measurement

**Status**: Accepted (owner, 2026-10-19).
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
  alphabetically, byte for byte as before. The table starts empty: production's bytes do not change until a
  measurement says so.
- **The table is filled by a test, not by reasoning.** `scripts/check_schema_order.py`:
  - `isolation` (no GPU): every candidate changes key order and nothing else;
  - `run`: two control sessions (production's table, the same bytes twice) and one session per candidate on
    the order bank (`case_bank_order.jsonl`: 144 pressure and 160 vote units of ground truth, 500 candidacy);
  - `decide`: the rule below, written before any run, and `check_schema_order_results.md`.
- **The candidates** are the id first, then the six orders of the decision, what depends on it, and the
  `motif` code (`schema_order.RULES`), plus alphabetical.
- **The rule.** A candidate replaces a class's current order only if, on that class's primary measure (its
  largest ground-truth family, else its validity), it:
  - beats the first control (paired McNemar, Holm across that class's candidates, p < 0.05);
  - also beats the second control;
  - does not lower validity significantly;
  - does not put 95% of units on one answer where the control gives no answer to 80%.
  A measure whose two controls disagree on more than 10% of units cannot decide (today `positioning_poles`
  and `chamber_poles`): the class keeps its order. Without a winner, nothing changes.
- **Then live.** `scripts/schema_order_live_ab.sh` runs the candidate table against production twice
  (exploration profile, p100, 4 years, 3 seeds) and `schema_order_live_report.py` passes it only if every
  measure (elections, recalls, occupancy, pressure inaction, forum mind-shift, fallbacks, retries) stays within
  the two controls' range. On last night's runs it rejects the motif-first order for the three regressions
  found by hand.
- **When to re-run, and only then:** a vLLM or xgrammar version, a model or quantisation, a decision class
  gaining, losing or renaming a field, a rewrite of a decision's system prompt. A test pins `WIRE_ORDER`
  and names each class's fields; `llm_client.py` is in `PROMPT_SOURCE_FILES`, so a run records it.

## Consequences

- Request hashes, goldens and replay logs are unchanged: the order is applied on the wire, after the hash.
- A change of `WIRE_ORDER` changes behaviour like a prompt change: runs before and after are not comparable
  decision by decision, and its PR carries the results doc and the live report.
- Not covered yet: the agents' turns and nested objects (`PositionShift`) have no ground truth, and their
  declared order was where last night's forum and chamber regressions came from; they stay alphabetical until
  a bank family can measure them. `campaign_positioning` is not in the order bank (too noisy to measure).
