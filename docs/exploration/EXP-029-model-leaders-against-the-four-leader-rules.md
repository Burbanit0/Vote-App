# EXP-029 — The model's leaders read against the four leader rules

- **Date**: 2026-11-17 UTC · **Status**: measured, indirect, one model at one budget; it describes how the model's presidents and nominees move, and says none of the four rules fits them · **Real cost**: CPU only, seconds, on the ten runs of EXP-028; no GPU, no rented compute
- **Verdict in one sentence**: in ten model-led scenario runs the leaders moved their stated position toward the electorate's median on 99% of the nominees' and 76% of the presidents' shifted dimensions, with no pull toward their own party (below what a random group of the same size would give), the president reverses its previous move more often than it repeats it (58%), and both move by steps several times a rule's, so none of sticker, aggregator-of-supporters, hunter or explorer describes them; the closest description is a centre-seeker, and the prompts, which show the public median beside the leader's own value, invite exactly that.

## Starting hypothesis

Stage 2c of `polity-state-2026-11.md`: step 7 of `plan-scenarios-v1.md` asks for "the LLM president classified against" Laver and Sergenti's four rules (sticker, aggregator, hunter, explorer; ADR-040). ADR-040 left it "needs the model, has not run". EXP-028 produced ten model-led runs, so the classification can be read from them without GPU. The owner chose the scoped-small reading (2026-11-17): CPU only, on the existing runs.

## Protocol

`fast_api_voter/scripts/archive/classify_model_leaders_against_rules.py <model-runs-dir>` on the ten runs of EXP-028 (`1456fef5`, vLLM 0.31.0, Qwen3-8B-AWQ, budget 2,048).

**What is read, because no rule moves anything in these runs**: `parties.leader_rule` is `sticker` in the scenario profile and the journal has no `party_repositioned` event. What the model's leaders do is the `shifts` of their `agent_turn`: the kernel's step toward the targets the model named, **at most 0.3 a dimension** (`agents.steps_toward`; the model gives targets, the kernel makes the deltas), applied to the leader's **stated** position, not the sincere one: a nominee's pledge, a president's `revealed` (`run_frames._agent_turn`). The script replays that stated position from the journal (candidacy, `campaign_positioning`, `mandate_pledge_declared`, then each turn's shifts, clamped to 0..1) and reads every shifted dimension from it, against the latest snapshot at or before the turn (every fourth tick, so up to three ticks old) for the electorate and the party:

- **sticker**: no shift in the turn (the model restated what it was shown, or the kernel dropped a step under half the shown precision).
- **aggregator**: the sign points toward the party's centroid without the leader (two other members at least), and, to see what the party adds, toward the electorate's median and centroid. A dimension where the target lies within 0.02 of the leader's value is skipped. Two baselines: the hit rate expected from the sign mix alone, and from a random group of the party's size in place of the party. ADR-040 defines a supporter by ballot distance; here a supporter is a party member at the snapshot.
- **hunter**: for a leader with two shifts on one dimension in the same campaign or term, the share whose second has the sign of the first. The rule's own condition, its poll share, is not read.
- **explorer**: probes five positions and takes the best; not identifiable from one logged move, so not classified.

## What it found

| | nominee | president |
|---|---:|---:|
| readable turns (ten runs) | 312 | 330 |
| turns with no shift | 20.2% | 33.6% |
| Euclidean step of a turn that moves, median (mean) | 0.30 (0.35) | 0.14 (0.17) |
| shifted dimensions toward the electorate's **median** | 478 / 484 = 98.8% | 300 / 395 = 75.9% |
| ... chance from the sign mix | 0.55 | 0.49 |
| shifted dimensions toward the electorate's centroid | 475 / 483 = 98.3% | 298 / 416 = 71.6% |
| shifted dimensions toward the **party's** centroid | 307 / 383 = 80.2% | 220 / 401 = 54.9% |
| ... expected from a random group of the party's size | 0.955 | 0.641 |
| repeat move on a dimension in one term, same sign | no pair in one campaign | 132 / 311 = 42.4% |

- **Centre-seeking, not party-seeking**: both roles move toward the public median far more than the sign mix gives. Toward the party they move **less** than a random group of the same size would predict (80% against 96% for nominees, 55% against 64% for presidents), probably because a party of a handful of citizens has a centroid near the electorate's, so a party-centroid test reads the centre-seeking through it (not checked separately). There is no sign of an aggregator of supporters.
- **No hunter's heading**: presidents reverse their previous move on a dimension more often than they repeat it (42.4% same sign, 58% opposite; an exact two-sided test gives p 0.009, optimistic as the moves cluster in leaders). A hunter that keeps its heading while it wins would sit above 50%. Nominees have no pair of turns in one campaign to compare. The poll-share half of the rule was not read.
- **Not stickers, and not small**: only 20% (nominee) and 34% (president) of turns restate the shown value. A turn that moves has a Euclidean step of 0.14 (president, median) to 0.30 (nominee), 22% of the 981 shifted dimensions sit exactly at the kernel's 0.3 cap, and the president acts about four times a year (4.1 turns per run-year). Over a year a president's moves add up to a path of about 0.4 to 0.5 (median 0.14 a moving turn, 66% of turns moving, 4.1 turns), against ADR-040's step of 0.02 to 0.10 a year; the two are not the same measure (a path, against a rule's net step, on a stated position against a party platform), and with the president's reversals the net movement is smaller than the path, but the model's leaders move by several times a rule's step.
- **What the prompts show**: the nominee's turn shows a table `issue | your platform | public median` and the president's `issue | policy now | you state | you pledged | public median | assembly median` (`agents.py`). Moving a stated value toward a column that is on the page is the move a prompt invites; this note cannot separate what the prompt shows from what the model decided, and does not say the model chose centre-seeking as a strategy.

## What it cost

CPU only: one script over the ten runs' journals and snapshots, a few seconds. No GPU, no rented compute.

## Verdict and why

The classification the step asked for **has no single label**. The model's leaders are not stickers (two thirds to four fifths of the turns move), not aggregators of supporters (no pull toward the party beyond what a random group would give), not hunters (presidents reverse more than they repeat), and an explorer cannot be read from one logged move. What they do is move toward the median the prompt shows them, by steps several times a rule's. A twin with `leader_rule: aggregator` at ADR-040's step is therefore not a stand-in for the model's leaders: its direction would be to the party's supporters, and its size a fraction of theirs.

What this note does **not** show: that the leaders' moves matter to the outcome (their stated position is not a party platform: parties do not follow it, since `parties.leader_rule` is `sticker`); that the hunter's and explorer's conditions are absent (poll share was not read); anything about a second model, another budget or other prompts (for instance a prompt without the median column); independence between the 981 shifted dimensions (they come in clusters from one turn and one leader, so the p-values are optimistic and the counts are what to read); or the position the turn was read against beyond the snapshot's three-tick lag for the sincere positions and parties.

## What I take from it (portable)

- A move has to be read against the position the kernel actually moves: here the stated one, not the sincere one. A first reading on the sincere position gave the president a "moderate pull toward the electorate, none toward the party" (62% and 49.5%); on the stated position it is 76% and 55%.
- A test against a group centroid needs a same-size random group as its baseline: a small party's centroid sits close to the electorate's, so the test reports the centre-seeking again.
- Say whether a "step" is a model choice or a kernel cap: 22% of these shifts sit exactly at the cap.
