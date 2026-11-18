# EXP-031 — The model arm's party system, reproduced with a rule instead of the model

- **Date**: 2026-11-17 · **Status**: measured, CPU only, ten seeds, one rate; it separates the party system from the model, not the leaders from the amendments · **Real cost**: 50 s of CPU for ten runs (the model arm took 5 h 14 min of GPU); no GPU, no rented compute
- **Verdict in one sentence**: a rule that answers the forum with `found` on 80% of the turns where the prompt's own condition allows it, and nothing otherwise, reproduced the model arm's party system on ten seeds (45 to 56 parties founded a run against 45 to 54, 28 to 40 dissolved against 24 to 40, effective parties 5.6 to 8.7 against 6.6 to 10.5, the same 9 of 10 volatility failures and no run inside the plausibility band), so that part of EXP-028's difference does not need the model; what the rule arm does not reproduce is the model arm's label spread (3 labels and 1.30 bits against 5 labels and 2.25 bits), which here cannot be told apart from the model's amendments and leaders.

## Starting hypothesis

EXP-030 found that the model founds a party on 80% of the turns its prompt says founding is allowed and almost never otherwise, and that this is consistent with the prompt telling it when to found; it did not test that a rule would do the same. The owner chose (2026-11-17) to test it with "a rule run, no GPU". If a rule following the prompt's condition gives the model arm's party system, that system does not depend on the model; if it does not, the model's founding does something the condition does not explain.

## Protocol

`fast_api_voter/scripts/archive/run_rule_forum_founding.py` (ten seeds, 8 years, 100 citizens, 15 seats, commit `56cb898b`'s tree) and `compare_rule_forum_arm.py` against EXP-028's model arm and rule twin. No engine change: the scenario profile is built as the model arm ran it (`flagship_config(engine="llm", profile="scenario")`), with a **client that is a rule** injected in place of vLLM:

- the forum turn is answered `found` with probability 0.8 when the prompt shows N at or above the need and no founding lock, else `none`; no post, no stance shift, no join or leave (the draw is a hash of the seed and the prompt); 0.8 is EXP-030's rate where allowed;
- the president must stay an agent (`llm.crowd` is false and the mandate needs one, `validate_config`), so its turn is answered by one that does nothing: no position, no bill, no speech;
- nominees, coalition leaders and amendments are switched off (the engine's own rules decide them), and campaign salience and the president's extra-legal act (regime) with them, as `validate_config` ties them to those agents; everything else follows `llm.enabled` as in the model arm (party births and deaths, the forum, the stance step).

**This is not a swap of the founding decision alone**: the rule arm also has a president who does nothing, rule nominees and coalitions, and no amendments. It is the model arm's mechanism with the model's leaders taken out and the founding done by a rule. The seeds are the same numbers (1 to 10) but the engine draws differ, so the runs are compared as two samples of ten, not as pairs.

## What it found

| | model arm (EXP-028) | rule-forum arm | rule twin |
|---|---|---|---|
| parties founded per run | 45 to 54 | 45 to 56 | 0 |
| parties dissolved per run | 24 to 40 | 28 to 40 | 0 |
| effective parties, mean over elections (median) | 6.6 to 10.5 (8.1) | 5.6 to 8.7 (7.7) | 4.2 to 5.0 (4.4) |
| band checks failed, over ten runs | volatility 9, enp 5, turnout 4 | volatility 9, enp 3 | turnout 2, volatility 1 |
| runs inside the band | 1 of 10 | 0 of 10 | 7 of 10 |
| archetypes | fragmentation 3, alternation 2, churn 2, stasis 2, collapse 1 | churn 6, fragmentation 3, alternation 1 | alternation 5, stasis 5 |
| entropy; largest share | 2.25 bits; 30% | 1.30 bits; 60% | 1.00 bit; 50% |
| divergence test | grows, varied, no dominant story; **not plausible** | grows, varied; **a dominant story (churn 60%)**, not plausible | all four pass |
| mean pairwise distance within the arm* | 3.01 | 2.86 | 2.78 |

\* the 30 runs standardised together; between arms: model / rule-forum 2.82, model / twin 3.31, rule-forum / twin 3.13. The rule-forum arm is nearer to the model arm than the model arm's own runs are to each other (3.01).

- **The party system reproduces**: the founding and dissolution counts, the effective parties (rule median 7.7, model 8.1) and the plausibility failure on volatility all land where the model arm does. Both sit far from the twin on effective parties (4.4). With the founding done by a rule and a president that does nothing, the mechanism and the prompt's stated bar give the party system.
- **The labels do not**: the rule arm reads as churn on six runs of ten (a dominant story, which fails the divergence test's third condition) and has no stasis and no collapse; the model arm has all five labels at no more than 30% each. The model arm's `collapse` (seed 10, an election that seated no party after the threshold rose to 0.15 in EXP-028) has no counterpart: the rule arm has no amendments. What makes the model arm's label spread, its leaders or its amendments or the rest, is not separated by this run.
- **Calls**: 67 to 87 `found` answers a run, as 0.8 of the eligible turns; the kernel accepts 45 to 56 of them, as with the model (EXP-030).

## What it cost

50 s of CPU for the ten seeds on one machine (3 to 5 s a run); the model arm took 5 h 14 min of the local GPU. No rented compute.

## Verdict and why

Part of EXP-028's difference needs no model: the party system, its count of parties, and the plausibility failure on effective parties and volatility come from the founding mechanism being on, a bar of 5 citizens at a population of 100, and a founder that acts on the prompt's condition, whoever it is. A model is not what puts the model arm outside the catalogue's range of effective parties; a rule does the same in 50 seconds.

The model arm's wider label spread (five labels, 2.25 bits, no dominant story) is not reproduced. The rule arm's runs are dominated by churn. Since the rule arm lacks the model's president, nominees, coalition leaders and amendments together, this run cannot say which of them makes the difference, or whether the difference is a property of the model at all and not of leaving those mechanisms off. For G2 (the owner's call) the question becomes narrower than EXP-028 made it: not "does the model add variety through party founding" (it does not need to), but "do the model's leaders and amendments add variety the rules do not".

What this note does **not** show: that a rule reproduces the model's founding turn by turn (the rate and the condition were taken from EXP-030, and it ignores the model's 10% of founding answers below the bar and its joins and leaves); which of the model arm's leader decisions give its labels; anything at another population or a different bar; or whether ten seeds each are enough for the label counts (six of ten churn against none in the model arm is a large gap, but they are two samples of ten).

## What I take from it (portable)

- When a model-driven difference might be the prompt's stated condition, a rule that reads the same condition is a cheap test: here it took one rule client and 50 s, against a 5-hour GPU run, and it could have said no.
- A client injected in place of the model needs no engine change: the protocol is small (`complete_json`, `count_prompt_tokens`, an `extra_body` argument), and the config validator names the agents each mechanism depends on.
- Say what else the rule arm changes: a president that does nothing and no amendments make it a different arm, not a one-decision swap.
