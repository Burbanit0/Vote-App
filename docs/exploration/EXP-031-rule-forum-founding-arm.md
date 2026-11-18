# EXP-031 — The model arm's party system, reproduced with a rule instead of the model

- **Date**: 2026-11-17 · **Status**: measured, CPU only, ten seeds per arm; it separates the party system from the model, not the leaders from the amendments · **Real cost**: 20 to 50 s of CPU per ten runs (the model arm took 5 h 14 min of GPU); no GPU, no rented compute
- **Verdict in one sentence**: a rule that answers the forum with `found` on 80% of the turns where the prompt's own condition allows it, and nothing otherwise, gave on ten seeds the model arm's party system (45 to 56 parties founded a run against 45 to 54, effective parties median 7.7 against 8.1, 0 of 10 runs inside the plausibility band against 1 of 10), and the same arm at rate 0 gave a twin-like result (no party founded, effective parties 4.4, 10 of 10 inside the band; the twin itself has 7 of 10, and differs in turnout cost); so the extra parties and the plausibility failure come from the founding mechanism being on, not from the model, and not from the president or mechanisms this arm switches off; the model arm's wider spread of labels is **not** shown to differ from this arm's (ten seeds each cannot tell them apart).

## Starting hypothesis

EXP-030 found that the model founds a party on 80% of the turns its prompt says founding is allowed and almost never otherwise, consistent with the prompt telling it when to found; it did not test that a rule would do the same. The owner chose (2026-11-17) "a rule run, no GPU". If a rule that follows the prompt's condition gives the model arm's party system, that system does not depend on the model; if not, the model's founding does something the condition does not explain.

## Protocol

**How this differs from what the owner chose.** The option read "add a rule ... in the rule twin with party_moves on ... a rule path for party moves in the deterministic engine", an engine change. This run makes none: it injects a rule client into the llm path, so the arm is the model arm's configuration with the founding (and the president's turn) answered by a rule, not the twin plus party moves. It keeps every setting except the answering agent the same as the model arm's, which is why it was used; it costs the property that the arm is a twin. The engine path stays unbuilt and is the owner's call.

`fast_api_voter/scripts/archive/run_rule_forum_founding.py` (8 years, 100 citizens, 15 seats, the `polity` tree at `56cb898b`; ten seeds 1 to 10 per arm) and `compare_rule_forum_arm.py` against EXP-028's model arm and rule twin. No engine change: the scenario profile is built as the model arm ran it, with a **rule client** injected in place of vLLM:

- the forum turn is answered `found` with probability RATE when the prompt shows N at or above the need and no founding lock, else `none`; no post, no stance shift, no join or leave; the draw is a hash of the seed and the prompt. RATE 0.8 is EXP-030's rate where allowed; 0, 0.2, 0.4 and 1.0 were also run. The stand-line pattern is the one of EXP-030, and the client raises if a prompt lacks it.
- the president must stay an agent (`llm.crowd` is false and the mandate needs one: `validate_config`), so its turn is answered by one that does nothing.

**Differences between this arm and the model arm** (a diff of the runs' `config.json`): `agents.nominees`, `coalition`, `amendments` and `amendment_stakes` are off (the engine's rules decide them); `campaign.salience_step` and `max_reached` are 0 and `regime.enabled` is off (`validate_config` ties them to those agents); `llm.reproducibility` is strict instead of relaxed, `max_batch_replays` 0 instead of 2 and `intra_run_workers` 1 instead of 24 (harness settings; no model is called). Everything else is the same, including party births and deaths, the forum and the stance step. **This is not a swap of the founding decision alone.** The twin also differs from both in `vote.turnout_cost` (0.02, against 0.04), so the twin's turnout failures are not like for like.

The comparison with the model arm is of two samples of ten: the model's leaders consume engine draws the rule arm does not, so a seed is not a pair.

## What it found

| | model arm (EXP-028) | rule-forum arm, rate 0.8 | rule twin |
|---|---|---|---|
| parties founded per run | 45 to 54 | 45 to 56 | 0 |
| parties dissolved per run | 24 to 40 | 28 to 40 | 0 |
| effective parties, mean over elections: median (range) | 8.1 (6.6 to 10.5) | 7.7 (5.6 to 8.7) | 4.4 (4.2 to 5.0) |
| runs inside the plausibility band | 1 of 10 | 0 of 10 | 7 of 10 |
| band checks failed, over ten runs | volatility 9, enp 5, turnout 4 | volatility 9, enp 3 | turnout 2, volatility 1 |
| archetypes | fragmentation 3, alternation 2, churn 2, stasis 2, collapse 1 | churn 6, fragmentation 3, alternation 1 | alternation 5, stasis 5 |
| entropy; largest share | 2.25 bits; 30% | 1.30 bits; 60% | 1.00 bit; 50% |

The mean pairwise distance (the 30 runs standardised together) is 3.01 within the model arm, 2.86 within the rule-forum arm and 2.78 within the twin; between model and rule-forum 2.82, model and twin 3.31, rule-forum and twin 3.13. These are means over 45 or 100 pairs without a spread or a permutation baseline, and are not read as a test.

**Rate and confound check** (same ten seeds, same arm, only the rate changes):

| rate | parties founded | effective parties, median (range) | inside the band | archetypes |
|---|---|---|---:|---|
| 0 | 0 | 4.4 (4.0 to 4.7) | 10 of 10 | alternation 6, stasis 4 |
| 0.2 | 27 to 38 | 7.6 (6.1 to 8.9) | 1 of 10 | churn 4, stasis 3, alternation 2, fragmentation 1 |
| 0.4 | 37 to 45 | 7.1 (5.4 to 8.1) | 0 of 10 | churn 6, stasis 3, fragmentation 1 |
| 0.8 | 45 to 56 | 7.7 (5.6 to 8.7) | 0 of 10 | churn 6, fragmentation 3, alternation 1 |
| 1.0 | 48 to 58 | 7.4 (6.3 to 8.6) | 0 of 10 | churn 5, fragmentation 2, alternation 2, stasis 1 |

- **Founding is what makes the party system**: at rate 0, with the same no-op president and the same switched-off mechanisms, the arm has no party founded, the twin's effective parties and 10 of 10 runs inside the band. The president that does nothing and the missing nominees, coalitions, amendments, campaign and regime do not create the party system. Any positive rate gives effective parties near 7 to 8 and almost no run inside the band; the count of parties founded rises with the rate (27 to 38, 37 to 45, 45 to 56, 48 to 58).
- **Matching 45 to 54 founded is partly calibration**: 0.8 is the model's rate where allowed, so the founding counts agree by construction. The effective parties and the plausibility failure agree at rates from 0.2 to 1.0, which is why they, and not the counts, are the evidence that the mechanism and not the rate is the cause.
- **The model arm's highest effective parties (10.5, 10.3, 9.5) lie above the rule arm's maximum (8.7)**; EXP-028 links those three runs to a threshold lowered by amendment, which the rule arm lacks. The medians (8.1 and 7.7) and the band failures agree; the tails do not.
- **Labels**: at 0.8 the rule arm reads churn on 6 of 10 runs against 2 of 10 in the model arm (Fisher exact p 0.17) and fails the divergence test's dominant-story condition by one run; at 0.2 it has four labels and no dominant story, at 1.0 churn 5. The label spread of the two arms is **not shown to differ** with ten seeds each.
- **Acceptance**: 754 `found` answers over the ten runs, 503 accepted (67%); the model's 832 and 492 (59%, EXP-030). The rule never answers `found` below the bar or under a lock, which the model did on 62 turns, so its refusals have a different mix. Why a third of even the rule's answers are refused was not traced (a recount after the same tick's other foundings would fit, as in EXP-030).
- **Pairing**: at rate 0 the effective parties equal the twin's seed for seed on several seeds (the engine draws agree until a founding changes the stream), so a paired reading against the twin was available and was not made.

## What it cost

20 to 50 s of CPU for each ten seeds (2 to 5 s a run, measured at two times of day), five times (the rates); the model arm took 5 h 14 min of the local GPU. No rented compute.

## Verdict and why

The party system of EXP-028's model arm does not need the model: a rule that founds when the prompt's stated bar is met reproduces its size (founded, dissolved), its effective parties and its failure of the plausibility band, and the same arm with founding off reproduces the twin. The mechanism being on, a bar of 5 citizens at a population of 100, and a founder that acts at all give the system. So the extra effective parties and the plausibility failure of EXP-028 are no evidence that the model's leaders add anything.

What is left for G2 (the owner's call) is narrower: the model arm's wider label spread and its highest effective parties. The first is not shown to differ at ten seeds; the second comes with the model's amendments, which this arm does not have. Whether the model's leaders or amendments add variety a rule does not is not answered here.

What this note does **not** show: that the model's founding is a rule turn by turn (the rate and condition come from EXP-030, and the arm ignores the model's below-bar founding answers, joins and leaves); which of the model arm's leader decisions give its higher tails; the same at another population or bar; that ten seeds are enough for labels (they are not); or a test of equivalence for any of the numbers (they overlap, no test was run).

## What I take from it (portable)

- Run the null before the claim: the rate-0 arm costs one command and shows that the president that does nothing is not what makes the party system. Without it a reader cannot tell the switched-off mechanisms from the founding.
- A rule fitted to the model's rate matches its counts by construction; read the quantities the rate does not set (effective parties, the plausibility checks), and sweep the rate.
- A label count from ten seeds moves with the rate and the seed; do not put "6 of 10 against 2 of 10" in a verdict.
- A model replaced by a rule needs no engine change: the client protocol is small (`complete_json`, `count_prompt_tokens`, an `extra_body` argument), and the config validator names the agents each mechanism depends on.
