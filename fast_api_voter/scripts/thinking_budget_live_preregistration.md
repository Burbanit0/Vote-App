# Thinking budget on live prompts: pre-registration (2026-10-21, before any call)

Proposition #2 of the 2026-10-21 polity-engine investigation. Question: does the single `llm.thinking_token_budget`
(2048) cause the 8B's wrong votes (OBS-054), and if so what is the smallest budget that removes the error?

**Material.** The logged first-attempt `vote_cast` and `chamber_deliberation` calls of the 8B baseline (`rtxpro6000-8b-baseline`)
and of the three 30-year p500 runs (`full/`), with their prompts (`llm_prompts.jsonl`). Sample, seeded (20261021), by
`thinking_budget_live.py sample`: all 20 baseline vote calls; per p500 run 67 vote calls that ended at the budget and 13
that ended under it (the under-budget ones are the internal check: a larger budget must not change them); chamber calls
that ended at the budget, 25 per run over the four runs.

**Arms.** `thinking_token_budget` 2048 (today), 4096, 8192, none. Same bytes otherwise (system, user, schema,
`max_tokens`, `temperature`, `seed` as logged), the local 8B on the current stack, alone on the server. Votes: 2 repeats
per arm and call; chamber: 3. Arms run one after the other, calls within an arm concurrently (8 workers).

**Outcomes** (units are the voters of a vote call; the rule is `decision_audit.vote_rule`: a candidate within the voter's
`blank_threshold` is acceptable, blank only when none is). Over units where the rule says a candidate is acceptable:
- **E1**: the model votes blank.
- **E2**: the model's first choice is not the nearest acceptable candidate (a blank counts as wrong).
Chamber (no rule-truth): units with a non-empty `shifts`, and shifts per unit; descriptive only.

**Tests.** Each of 4096, 8192, none against 2048, on E1 and on E2: an exact McNemar test on the discordant (call, repeat,
voter) unit pairs, Holm across the six. Units are clustered in calls (about 3 per call); the test treats them as
independent, so p-values are optimistic and are read together with the call-level discordant counts.

**Noise floor.** For each arm the share of unit pairs whose E2 differs between its two repeats. If it exceeds 5% in
the 2048 arm, the comparison is reported as unresolved.

**Decision rule.** Let E2(b) be the arm's E2 rate. Walk b over 2048, 4096, 8192 in that order and take the first with
E2(b) - E2(none) <= 0.02 and median reasoning tokens(b) < median reasoning tokens(none):
- if it is 2048: the budget is not the cause; keep it, and the error is the model's;
- if it is 4096 or 8192: that budget is the candidate (a prompt-like change: runs before and after are not comparable);
- if none qualifies: no tested budget removes the error; the error is the model's, or needs more thinking than "none" allows.
In every case also report truncation (`finish_reason == "length"`), the share of calls at the budget and the latency p50 per arm.

**Check on the cases that ended under the budget originally**: their E2 may differ between arms by no more than the
noise floor; if it does, the arms differ by something other than the budget and the experiment is void.

**Not done here**: any simulation, any claim about elections (the counted ballots are the kernel's), the 27B.
