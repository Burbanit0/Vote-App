# v4 acceptance comparison — the 4-modality pressure-menu sweep (Lot 8)

n=1 per arm (one seed, no Monte Carlo band) -- the honest limit of this deliverable at this hardware's wall-clock cost; see this lot's own residual risks in merry-hugging-hamming.md.

## Two live reliability findings, fixed during this run

Running the actual sweep at real population scale (100 citizens, 20 issue dimensions, real candidate diversity) surfaced two model-reliability bugs that no prior spike or unit test caught, because both prior testing only checked schema validity/alignment, never vote or positioning *content* quality:

1. **`decide_campaign_positioning` (5-nominee batch) produced a 100% reproducible degenerate response under `think=False`** (one citizen duplicated, the rest dropped, byte-identical across 9 attempts at temperature=0, against a real recurring nominee combination). Fixed by switching this one call to `think=True` with a larger, measured token budget (`_POSITIONING_THINK_TOKEN_ALLOWANCE`) — verified 5/5 clean afterward against the same failing input. An interim attempt to also shorten this call's HTTP timeout (to fail faster into a hang) was tried, found to cut off legitimate slower-but-correct generations, and reverted — 600s (every other `think=True` caller's default) is what the evidence actually supports.
2. **`cast_votes` produced 100% blank presidential ballots** — every one of 100 citizens, every election, every arm — reproduced at the raw model-response level, not a decode bug. Root cause: the prompt asked the model to judge candidate "acceptability" from raw 20-dimensional position/priority vectors with no worked definition, the same weighted-euclidean-vs-`blank_threshold` arithmetic `build_ranking` computes exactly on the deterministic path, left for the model to approximate from scratch across 25 voters at once. Fixed by precomputing each voter's `simple_rules.weighted_distance` to every candidate and handing it to the model directly (the same "compute outside the LLM, pass a plain float" pattern dt=10's `self_gap` already established), plus a new `VoteMotif.ACCEPTABLE_MATCH` (105, codebook bump 1.2→1.3) for the previously-missing "sincere vote for an imperfect-but-tolerable candidate" case — every prior motif named either a blank-vote reason or a strategic one. Verified 6/6 clean trials afterward (~4% blank, a plausible rate, not a collapse).

Both fixes are additive (new `think`/token-budget/prompt content for existing call sites, a new enum member) and keep every prior byte-for-byte reproducibility test passing unmodified under the shipped `llm.enabled: false` default. See `llm_behavior_engine.py`'s `decide_campaign_positioning`/`build_system_prompt`(vote)/`build_user_prompt`(vote) docstrings and `codebook.py`'s `VoteMotif` docstring for the full reasoning.

| arm | engine | years | elapsed(s) | replays | mean L (last) | recalls | mandate_dev (last, src) | inaction_rate (last) | lever mix | stance mix | petition success/removal |
|---|---|---|---|---|---|---|---|---|---|---|---|
| both | deterministic | 30 | 0.1 | 0 | 0.000 | legitimacy_floor=8 | — (recorded) | 0.516 | 0=0.513, 1=0.162, 2=0.005, 3=0.320, 4=0.000 | 1=0.000, 2=0.000, 3=0.000, 4=0.000 | 1.000/0.000 |
| both | deterministic | 8 | 0.0 | 0 | 0.345 | legitimacy_floor=2 | — (recorded) | 0.507 | 0=0.512, 1=0.208, 2=0.007, 3=0.273, 4=0.000 | 1=0.000, 2=0.000, 3=0.000, 4=0.000 | 1.000/0.000 |
| both | llm | 8 | 6311.7 | 0 | 0.720 | legitimacy_floor=2 | 0.000 (ctx) | 0.000 | 0=0.117, 1=0.464, 2=0.000, 3=0.419, 4=0.000 | 1=1.000, 2=0.000, 3=0.000, 4=0.000 | 0.667/0.000 |
| electoral_only | deterministic | 30 | 0.1 | 0 | 0.510 |  | — (recorded) | 0.500 | 0=0.496, 1=0.000, 2=0.000, 3=0.000, 4=0.504 | 1=0.000, 2=0.000, 3=0.000, 4=0.000 | —/— |
| electoral_only | deterministic | 8 | 0.0 | 0 | 0.510 |  | — (recorded) | 0.507 | 0=0.496, 1=0.000, 2=0.000, 3=0.000, 4=0.504 | 1=0.000, 2=0.000, 3=0.000, 4=0.000 | —/— |
| electoral_only | llm | 8 | 11776.3 | 0 | 0.710 |  | 0.000 (ctx) | 0.343 | 0=0.112, 1=0.000, 2=0.000, 3=0.000, 4=0.888 | 1=0.061, 2=0.000, 3=0.939, 4=0.000 | —/— |
| mobilization_only | deterministic | 30 | 0.1 | 0 | 0.061 | legitimacy_floor=8 | — (recorded) | 0.515 | 0=0.511, 1=0.000, 2=0.000, 3=0.489, 4=0.000 | 1=0.000, 2=0.000, 3=0.000, 4=0.000 | —/— |
| mobilization_only | deterministic | 8 | 0.0 | 0 | 0.345 | legitimacy_floor=2 | — (recorded) | 0.507 | 0=0.511, 1=0.000, 2=0.000, 3=0.489, 4=0.000 | 1=0.000, 2=0.000, 3=0.000, 4=0.000 | —/— |
| mobilization_only | llm | 8 | 6525.0 | 0 | 0.370 | legitimacy_floor=2 | 0.000 (ctx) | 0.000 | 0=0.301, 1=0.000, 2=0.000, 3=0.699, 4=0.000 | 1=1.000, 2=0.000, 3=0.000, 4=0.000 | —/— |
| petition_only | deterministic | 30 | 0.1 | 0 | 0.222 | legitimacy_floor=7 | — (recorded) | 0.500 | 0=0.498, 1=0.141, 2=0.005, 3=0.000, 4=0.356 | 1=0.000, 2=0.000, 3=0.000, 4=0.000 | 0.774/0.000 |
| petition_only | deterministic | 8 | 0.0 | 0 | 0.345 | legitimacy_floor=2 | — (recorded) | 0.507 | 0=0.498, 1=0.153, 2=0.006, 3=0.000, 4=0.343 | 1=0.000, 2=0.000, 3=0.000, 4=0.000 | 0.778/0.000 |
| petition_only | llm | 8 | 9644.4 | 0 | 0.375 | legitimacy_floor=1 | 0.000 (ctx) | 0.000 | 0=0.178, 1=0.746, 2=0.076, 3=0.000, 4=0.000 | 1=0.654, 2=0.000, 3=0.346, 4=0.000 | 1.000/0.000 |

## Headline questions (§0's research question, stated as an experiment)

- Does `electoral_only` really never recall anyone? Compare the `recalls` column across arms.
- Does a free arbitration (llm engine) produce a different lever mix than the rigid sign>launch>mobilize>wait priority chain (deterministic engine)? Compare `lever mix` for the same arm across engines.
- What is the inaction rate of the discontented (§7bis.3: "probablement le résultat le plus intéressant du modèle")? See the `inaction_rate` column, llm engine rows.
- Does the confidence vote stop being decorative once revealed_position can drift (llm.enabled + mandate.enabled)? Compare `petition success/removal` for the llm engine against the deterministic baseline, where removal is provably 0 (keep_ratio == m identity, test_confidence_vote_keep_ratio_equals_mandate_strength_on_the_deterministic_path).
