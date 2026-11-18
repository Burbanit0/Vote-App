# EXP-030 — The model's party founding follows what its prompt says is allowed

- **Date**: 2026-11-18 UTC · **Status**: measured, CPU only, on the ten model-led runs of EXP-028 · **Real cost**: CPU, seconds; no GPU, no rented compute
- **Verdict in one sentence**: in 3,300 forum turns the model answered `found` on 80% of the turns where its prompt said founding was allowed (770 of 960), on 10% where it showed too few citizens (55 of 578) and on 0.4% where it said the citizen's party was too young to found (7 of 1,762), so the 45 to 54 parties founded per run follow the prompt's stated conditions and a kernel that accepts 492 of the 832 `found` answers; this is instruction-following of a stated rule, not evidence that the model's judgement adds a party system, and it says what a rule "found whenever allowed" would give without testing it.

## Starting hypothesis

EXP-028 found that the model arm's difference from the rule twin sits in party founding (45 to 54 parties a run through the forum; none in the twin) and could not say whether that is the model playing a role or the prompt telling it when to found: gate G2 (`polity-state-2026-11.md`) waits on it. The owner chose (2026-11-17) to read the logged prompts first, before any new GPU run. `fit-for-inference.md` already records that the forum `found` answer moves with the co-founder count (97% in the neutrality probe) and that OBS-045's gate found no response to the stated *threshold*; this note asks whether, on the live runs, the decision does more than read the condition the prompt states.

## Protocol

`fast_api_voter/scripts/archive/read_founding_against_the_gate.py <model-runs-dir>` on the ten runs of EXP-028 (`1456fef5`, vLLM 0.31.0, Qwen3-8B-AWQ, budget 2,048; prompts kept). Two things the first reading of this note got wrong are the protocol now:

- **The model's answer is read from the call log** (`llm_calls.jsonl`, `content`), **not from the journal**: `forum_post.party_move` journals only what the kernel accepted, and a refused `found` is logged as an empty move.
- **The founding lock is separated.** A member of a party founded in the last year gets the line "Your party P was founded at tick T: until tick U, its members can neither found a party nor be brought into one" in the prompt (and the kernel refuses them).

Each forum turn's prompt also carries "N of the 100 citizens stand nearer to your positions than to their own party's platform, you included; founding a party needs 5", and the system prompt says a `found` makes a party "only if at least 5% of the citizens stand nearer ... your briefing says how many do". The script reads those lines from the 3,300 turns' prompts.

## What it found

| turns | count | model said `found` | kernel accepted |
|---|---:|---:|---:|
| unlocked, N below 5 | 578 | 55 (10%) | 3 |
| **unlocked, N at 5 or more** | **960** | **770 (80%)** | **489** |
| locked, N below 5 | 1,042 | 3 (0.3%) | 0 |
| locked, N at 5 or more | 720 | 4 (0.6%) | 0 |

- **Overall**: the model answered `found` on 832 of 3,300 turns (`join` 167, `leave` 26, `none` 2,275); the kernel accepted 492 foundings, 103 joins and 26 leaves. The journal's 2,679 empty moves include 340 refused `found` and 64 refused `join`.
- **A step, not a slope**: among unlocked turns the rate is 6 to 13% for N from 1 to 4 and 75 to 86% for every N from 5 to 19 (79, 81, 78, 78, 78 at 5 to 9; 86% at 10 to 14), with 4 of 8 at 20 and over. Nothing grows with how many citizens stand closer; the response is to the line "N reaches the need", and to the lock line.
- **The lock is obeyed**: 7 `found` answers in 1,762 locked turns. (The lock itself was also checked on the kernel side in EXP-028: none of the 302 dissolved founded parties dissolved in its first year.)
- **Why the kernel accepts only 489 of the 770**: each turn's briefing is built before any of the tick's turns is applied, and the kernel recounts at apply time. An earlier turn in the same tick that founds or re-affiliates changes who is locked and who counts, so 281 of the 770 `found` answers on turns that looked allowed were refused. The three accepted foundings with N shown as 4 (seeds 2, 3 and 6) are the same effect the other way: in seeds 2 and 3 a citizen who left their party earlier in the tick became partyless and counted as a co-founder. This was read from two examples and from the counts; the 281 were not each traced.
- **Why every seed lands at 45 to 54**: per seed, 84 to 105 unlocked turns reach the bar, the model answers `found` on 69 to 84 of them and the kernel accepts 45 to 54. Both factors are stable across seeds.

## What it cost

CPU only, one script over the ten runs' logged prompts, call logs and journals; no GPU, no rented compute.

## Verdict and why

The model founds a party almost every time its prompt says it may, and almost never when the prompt says it may not: 80%, 10% and 0.4% on the three kinds of turn. That is a model reading and following a stated condition, which is what the system prompt and the briefing ask of it, and the logged rationales restate the condition ("meeting the 5% threshold"). It does not separate "the model plays a role" from "the prompt tells it exactly when to found", the question G2 turns on; the data lean to the second.

For G2 this changes the reading of EXP-028. The model arm's party system comes from the founding mechanism being on in that arm only, a bar of 5 citizens at a population of 100 (so 960 of the 3,300 turns are eligible), and a model that founds on four turns in five when allowed. A rule "found with probability about 0.8 when allowed", with the kernel's own recount, would give nearly the same foundings; this was **not built or run**. So EXP-028's extra archetypes and its plausibility failure on effective parties say little about what the model's leaders add: they are largely a property of the mechanism and the prompt, and the model's own contribution there is following them.

What this note does **not** show: that a rule would reproduce the party system (not run); anything at another population, where 5% is more citizens and fewer turns qualify; a second model, budget or prompt (a prompt that does not state the bar might give another pattern); why the model founds on 80% and not on all of the eligible turns; or what the 10% of founding answers below the bar are (55 of 578: the model reading N as larger, or ignoring it; not read).

## What I take from it (portable)

- Read the model's answer from the call log, not from the journal, whenever the kernel can refuse it: a journal that records only accepted moves makes a refused answer look like a choice not to act. A first version of this note did exactly that and reported a "gate respected" that held by construction.
- Split a decision by the conditions the prompt states before reading a rate: a 29% overall rate was a mix of 80% where allowed and 0.4% where barred, and a "rise with N" was the changing share of locked turns.
- A decision that follows the prompt's stated rule is a check that the prompt is read, not evidence of judgement; whether the model adds anything is a question about a case the prompt does not settle.
