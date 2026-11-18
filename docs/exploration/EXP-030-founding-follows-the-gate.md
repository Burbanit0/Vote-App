# EXP-030 — The model's party founding follows the number its prompt shows

- **Date**: 2026-11-18 UTC · **Status**: measured, CPU only, on the ten model-led runs of EXP-028; it says what the founding decision follows, not whether its rate is right · **Real cost**: CPU, seconds; no GPU, no rented compute
- **Verdict in one sentence**: in 3,300 forum turns the model chose `found` on 489 of the 1,680 turns whose prompt showed enough citizens standing nearer to its positions than to their own party's platform (29%) and on 3 of the 1,620 turns where it did not (0.2%), and its rate climbs with that number from 20% at the bar to 42 to 50% well above it; so the 45 to 54 foundings per run follow the briefing and the kernel's low bar (5 citizens at 100), they do not look like an artefact of the prompt, and they say nothing yet about whether a 29% rate is right.

## Starting hypothesis

EXP-028 found that the model arm's difference from the rule twin sits in party founding (45 to 54 parties a run through the forum, none in the twin), and could not say whether that is the model playing a role or a prompt artefact. Gate G2 (`polity-state-2026-11.md`) waits on it. The owner chose (2026-11-17) to read the logged prompts first, before any new GPU run. OBS-045 had found, on a probe, that able founders founded 59 of 60 times whether told 3% or 7%: a response to the stated threshold was not detected. This note asks the other half: does the decision follow the number the briefing gives the citizen?

## Protocol

`fast_api_voter/scripts/archive/read_founding_against_the_gate.py <model-runs-dir>` on the ten runs of EXP-028 (`1456fef5`, vLLM 0.31.0, Qwen3-8B-AWQ, thinking budget 2,048; the runs kept their prompts). Every forum turn's user prompt carries one line: "N of the 100 citizens stand nearer to your positions than to their own party's platform, you included; founding a party needs 5". The system prompt says a `found` makes a party "only if at least 5% of the citizens stand nearer to your positions ... your briefing says how many do". The script reads N and the need from each of the 3,300 turns' prompts (all had the line, and all 100 and 5) and the turn's `party_move` from `forum_post` in the journal, and tallies `found` by whether N reaches the need and by N.

## What it found

| N shown (of 100; need 5) | forum turns | chose `found` |
|---|---:|---:|
| 1 to 3 | 1,110 | 0 |
| 4 | 510 | 3 (1%) |
| 5 | 414 | 81 (20%) |
| 6 | 344 | 101 (29%) |
| 7 | 254 | 62 (24%) |
| 8 | 201 | 57 (28%) |
| 9 | 136 | 48 (35%) |
| 10 to 14 | 275 | 115 (42%) |
| 15 to 19 | 48 | 21 (44%) |
| 20 and over | 8 | 4 (50%) |
| **N below 5 / 5 and over** | **1,620 / 1,680** | **3 (0.2%) / 489 (29.1%)** |

- **The gate is respected**: of 492 `found` turns, 489 were shown N of 5 or more; the 3 others were shown 4 (seeds 2, 3 and 6) and each still founded a party (492 `party_founded` events, one per `found` turn, EXP-028), so the kernel's own count reached 5 at that moment; whether the briefing's count is a tick older was not checked.
- **The rate follows the margin too**: 20% at the bar, 24 to 35% at 6 to 9, 42 to 50% at 10 and over (one dip, at 7). The model is not choosing at one fixed rate: it founds more where more citizens stand closer to it.
- **Why every seed lands at 45 to 54**: half of all forum turns are eligible (44 to 56% by seed) and the model founds on 26 to 34% of those (per seed), a product that varies little across seeds. The count is nearly constant because both factors are.
- **The bar is low here**: 5% of 100 is 5 citizens, and half the forum turns see at least 5 citizens closer to their own positions than to their party's. In the rule twin `agents.party_moves` is off, so the twin has no such option at all; the 45 to 54 foundings are what this mechanism gives with this population and this model, not a variety the model adds to a mechanism both arms have.
- **Other party moves**: 103 `join` and 26 `leave` over the 3,300 turns; 2,679 turns chose none.

## What it cost

CPU only, one script over the ten runs' logged prompts and journals; no GPU, no rented compute.

## Verdict and why

The founding decision follows the briefing: nothing before N reaches the bar, a fifth of the turns at it, and more as N grows. That is a response to a number the prompt shows, so the 45 to 54 foundings are not noise from the prompt, and OBS-045's "no response to the threshold" does not generalise to "no response to the briefing". It does not make the rate right: 29% of eligible turns is the model's choice with no ground truth behind it (Stage 3a's case family would be the place for one), and the system prompt itself says "most turns change nothing" while the model founds on a third of the turns that allow it.

For gate G2 this moves the reading of EXP-028. The model arm's extra party system is a consequence of the founding mechanism being on, a bar of 5 citizens at a population of 100, and a model that founds at about 29% where it can. It is not evidence that the model's leaders add variety through their own decisions (EXP-029: they are centre-seekers), nor that the founding is an artefact. Whether it holds at a larger population, where 5% is 25 citizens and fewer turns are eligible, was not run.

What this note does **not** show: that 29% is a right or a plausible rate; that the response is the model's reasoning and not a surface reading of the number; the same measure at another population, model or budget; or what a rule-based founder would do (none exists; the twin has the option off).

## What I take from it (portable)

- Test a decision against the number its prompt gives it before concluding it ignores its inputs: OBS-045's probe varied the stated threshold and found no response, and the live prompts show a clear one to the count of citizens.
- A count that is nearly constant across seeds can come from two stable factors multiplied, not from one fixed decision: here the share of eligible turns and the rate once eligible.
