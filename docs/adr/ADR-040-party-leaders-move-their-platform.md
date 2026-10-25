# ADR-040: party leaders move their platform (Laver and Sergenti's rules)

**Status**: Accepted — built, **off by default** (plan-scenarios-v1, step 7, its rule-based half); `parties.leader_rule` is `sticker` in every profile, the behaviour of every run before this ADR. The catalogue of scenarios varies it.
**Date**: 2026-10-25
**Context**: A party's platform was where k-means put it at the start of a run (or, for a party a citizen founds, the founder's views), and it never moved again: parties were positions, not actors. Laver and Sergenti (2012, *Party Competition: An Agent-Based Model*) model party leaders who follow simple, typed rules for moving their platform between elections, and show that the mix of rules shapes the party system. Step 7 of plan-scenarios-v1 asks for those rules as the cheap leader arm, and later for the LLM president to be classified against them.

## Decision

**`parties.leader_rule`** (`sticker` by default; `aggregator`, `hunter`, `explorer`) and **`parties.leader_step`** (0 by default: how far a leader moves in a year, Euclidean over the issues, which run from 0 to 1). A config rule refuses a moving rule without a step. Every party in a run follows the same rule.

**Once a year**, on the last tick of the year (`_phase_party_positions`, last in the tick, so the next year's ballots read the new platforms), every party's leader follows its rule from the same snapshot of platforms:

- **sticker** never moves;
- **aggregator** steps toward the centroid of its supporters (all the way when they are nearer than a step);
- **hunter** keeps its heading while its poll share is higher than at its last move; otherwise it turns to a random heading in the half of the space it came from (its first move is a random heading);
- **explorer** polls five positions a step away in random directions, every other platform where it stands, and moves to the best one if it polls better than where it is.

**A supporter** is the citizen a party is nearest to by the legislative ballot's own distance (`simple_rules.weighted_distance`, priority-weighted), and **a poll share** is the share of citizens it is nearest to: sincere first preferences, before strategic voting and the incumbents' record. A platform is clipped to [0, 1] on every issue. Party membership does not follow a moving platform (a citizen keeps the party they joined); only the ballot, the coalition's distances, legislation and newcomers read the new platforms.

**State and determinism**: a hunter's heading and last share live on its `Party` and are checkpointed with it (written only for a party that has them); hunters and explorers draw from their own stream (`leaders_rng`, seeded `[seed, 40]`, checkpointed, `None` for stickers), so no other stream moves. A run that crashes and resumes matches an uninterrupted one byte for byte, for hunters and explorers both. Each move is journaled as `party_repositioned` (`party_id`, `rule`, `share`, `shift`).

## Measured

The catalogue of scenarios with two new dimensions, `leader_rule` (the four rules) and `leader_step` (0.02 to 0.10), on top of the ten it had: 1,000 runs of the rule-only twin, 15 years, 100 citizens (`python scripts/run_polity_catalogue.py run --out <dir> --runs 1000 --seed 1`; the hypercube is now twelve-dimensional, so its points are not the fourth sweep's). The four-archetype gate still holds (alternation 59%, churn 16%, stasis 13%, realignment 12%), and 308 runs are inside the whole band (342 in the fourth sweep, on other points).

| leader rule (250 runs each) | alternation | churn | stasis | realignment | entropy | runs inside the band | mean largest volatility |
|---|---:|---:|---:|---:|---:|---:|---:|
| sticker | 149 | 36 | 35 | 30 | 1.61 bits | 33% | 0.269 |
| aggregator | 143 | 34 | 43 | 30 | 1.66 | 31% | 0.269 |
| hunter | 149 | 51 | 20 | 30 | 1.57 | 27% | 0.288 |
| explorer | 149 | 39 | 34 | 28 | 1.61 | 33% | 0.277 |

- **Hunters make churn**: leaders chasing votes move their parties more, legislative swings grow (largest volatility 0.288 against 0.269), churn rises from 36 to 51 runs and stasis falls from 35 to 20. PRIM finds it unprompted: the churn box names `leader_rule` hunter (49% against a base of 16%).
- **Aggregators lean toward stasis** (43 runs against 35): parties that follow their own supporters stay where those supporters are.
- **Explorers are barely distinguishable from stickers** at these step sizes: five probes a year a step away rarely find a better position in a twenty-issue space.
- **The effects are modest**: the archetype mix and its entropy move little (1.57 to 1.66 bits), and with 250 runs a rule the differences are readings, not settled effects.

## Not settled

- **One rule for every party.** Laver and Sergenti's central result is about mixes (stickers among hunters, aggregators among predators); a per-party assignment was not built.
- **No predator** (a party that moves toward the largest one), and no satisficing or speed variants.
- **Membership is sticky**: citizens keep the party they joined when its platform moves, so a party can drift away from its members; re-affiliation was not built.
- **The poll is sincere first preferences**, not the vote: strategic voting (ADR-024) and the record of the incumbents (ADR-011, ADR-034) are not in it.
- **The second half of step 7**, classifying the LLM president against these rules, needs the model and has not run.
- **A checkpoint written before these fields cannot resume after them**: the two keys change `config_hash` for every configuration (loud, at resume time).
