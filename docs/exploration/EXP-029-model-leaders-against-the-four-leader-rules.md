# EXP-029 — The model's leaders read against the four leader rules

- **Date**: 2026-11-17 UTC · **Status**: measured, indirect, one model at one budget; it describes how the model's presidents and nominees move, and does not classify them into one of the four rules · **Real cost**: CPU only, seconds, on the ten runs of EXP-028; no GPU, no rented compute
- **Verdict in one sentence**: in ten model-led scenario runs the president and the nominees moved their own positions in 66% and 80% of their turns, by a median 0.19 on a dimension (the rules move 0.02 to 0.10 once a year); nominees moved toward the electorate's centroid on 98% of shifted dimensions and toward their own party's on 77%, presidents toward the electorate's on 62% and toward their party's on 50% (chance), and a leader's second move on a dimension kept the sign of its first in 51%: so the nearest of the four rules is an aggregator of the electorate for nominees and a mix for presidents, with a frequency and a size no rule has, and the match is indirect.

## Starting hypothesis

Stage 2c of `polity-state-2026-11.md`: step 7 of `plan-scenarios-v1.md` asks for "the LLM president classified against" Laver and Sergenti's four rules (sticker, aggregator, hunter, explorer; ADR-040). ADR-040 left it "needs the model, has not run". EXP-028 produced ten model-led runs, so the classification can be read from them without GPU. The owner chose the scoped-small reading (2026-11-17): CPU only, on the existing runs.

## Protocol

`fast_api_voter/scripts/archive/classify_model_leaders_against_rules.py <model-runs-dir>` on the ten runs of EXP-028 (`1456fef5`, vLLM 0.31.0, Qwen3-8B-AWQ, budget 2,048). It reads the `agent_turn` events with role `president` or `nominee` and their `shifts` (a dimension and a delta, "restate your position on up to N issues"; `run_frames` replays them onto the leader's position; whether the engine applies them identically was not read), and each citizen's position and party in `snapshots.jsonl` (every fourth tick: a turn is read against the latest snapshot at or before it).

What is compared, because **no rule moves anything in these runs**: `parties.leader_rule` is `sticker` in the scenario profile and the journal has no `party_repositioned` event, so there is no rule-made move beside the model's. The model's leaders move their own position, not a party platform. For each shifted dimension:

- **sticker**: no move; read as the share of turns with no shift.
- **aggregator**: the sign of the delta points toward the centroid of the leader's own party (its supporters, the citizens with its `party_affiliation` at that snapshot), and, for comparison, toward the centroid of the whole electorate.
- **hunter**: for a leader with two shifts on the same dimension, the second has the sign of the first. The rule's own condition (its poll share rose) is not read.
- **explorer**: probes five positions and takes the best; not identifiable from one logged move, so not classified.

A sign test has a chance level of 0.5.

## What it found

| | nominee | president |
|---|---:|---:|
| turns (ten runs) | 312 | 330 |
| turns with no shift (sticker-like) | 20.2% | 33.6% |
| shifted dimensions toward the electorate's centroid | 480 / 488 = 98.4% | 308 / 493 = 62.5% |
| shifted dimensions toward the party's centroid | 367 / 475 = 77.3% | 237 / 479 = 49.5% (chance) |

- **Frequency and size**: 981 shifted dimensions in all, median size 0.193 and largest 0.300 on a 0-to-1 axis. ADR-040's rules move a party's platform once a year by 0.02 to 0.10 in total; these leaders restate a position in two turns out of three, by about twice the rules' largest step on each dimension they touch. So no rule's behaviour is close to theirs in how much they move.
- **Direction**: nominees head for the centre of the electorate in 480 of 488 shifted dimensions, and toward their party's centroid less often (77%); that is an aggregator of the whole electorate, not of its supporters. Presidents are weaker: 62.5% toward the electorate, and nothing beyond chance toward their party.
- **Heading**: of 410 repeat moves by one leader on one dimension, 211 (51.5%) have the sign of the leader's previous move; a hunter that keeps its heading while it wins would sit well above that, and a leader with no memory of its heading at 50%. This is the half of the hunter rule that can be read; the half that depends on its poll share is not.
- **What the prompt says**: the nominee's campaign turn names its audience ("undecided", in `campaign_run`) and the agent's own rationales read "target undecided voters" and "move closer to the median" (turn 0 of seed 1, citizens 27 and 15). The centre-seeking of nominees is what the prompt asks for as much as what the model decided; this note does not separate the two.

## What it cost

CPU only: one script over the ten runs' journals and snapshots, a few seconds. No GPU, no rented compute.

## Verdict and why

The classification the step asked for cannot be a single label. On what can be read, the model's nominees behave like Laver and Sergenti's **aggregator of the electorate**, and the model's presidents like an aggregator of nobody in particular (a moderate pull toward the electorate, none toward their party), neither with a hunter's heading nor a sticker's stillness. The decisive difference is amount: these leaders move far more, and far more often, than a rule with `leader_step` between 0.02 and 0.10 a year. A twin with `leader_rule: aggregator` and the step of ADR-040 is therefore not a stand-in for the model's leaders; it would be a much slower version of one of them.

What this note does **not** show: that the leaders' moves matter to the outcome (a move of the leader's own position does not move a party's platform here: `parties.leader_rule` is `sticker`, so the parties do not follow their leaders); that the hunter's and the explorer's rules are absent from the model's behaviour (their conditions depend on poll share, which was not read); anything about a second model, another budget or other prompts; and any independence between the 981 shifted dimensions. The binomial p-values the script prints (about 1e-12 for the two large effects) treat each shifted dimension as independent; they come in clusters from one turn and one leader, so they overstate the evidence, and the counts, not the p-values, are what to read. The position a turn is read against is the latest snapshot, up to three ticks old.

## What I take from it (portable)

- A classification against rules needs a move made by a rule in the same run; with `leader_rule: sticker` there is none, so what was read is a comparison with what a rule would have done, and it is indirect. Say which of the two a number is.
- A direction measured against the centre of the electorate shows what the prompt asked for as much as what the model chose; a prompt that names the audience cannot also be read as the model's own strategy.
