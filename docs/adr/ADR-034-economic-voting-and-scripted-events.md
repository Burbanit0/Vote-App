# ADR-034: voters judge the economy, and a scenario names its crises

**Status**: Accepted — economic voting is built in the scenario profile only (plan-scenarios-v1, step 3b); scripted events are available to every profile and ship empty. Both settings are neutral by default.
**Date**: 2026-10-22
**Update 2026-10-24**: the archetype labels in this ADR's tables are version 2 (the realignment rule was a fixed 0.1); [ADR-037](ADR-037-realignment-against-the-populations-spread.md) replaced it (version 3), so the current code does not reproduce them. The runs themselves are unchanged.
**Context**: Two gaps stood between the engine and a lifecycle with turning points.

- **The economy never reached the ballot.** `shock.py`'s AR(1) climate moved a citizen's anxiety and, through
  an event, their salience, but no election and no approval ever judged it. A recession could not cost an
  incumbent their office, which is the most familiar turning point in electoral history (retrospective
  voting, Fiorina 1981; economic voting, Lewis-Beck and Stegmaier 2000). ADR-009's `policy_retrospection`
  already judged policy per citizen (the distance policy moved toward them over a term); nothing judged
  the economy.
- **A scenario could not name its crises.** Scandals and shocks were draws from a seeded stream: a run had
  whatever its seed gave it, so "a recession in year 3" could not be asked for, and a catalogue of scenarios
  (plan-scenarios-v1, step 6) had no crisis dimension to vary.

## Decision

**`vote.economic_voting`** (0 by default). The economy's x(t) at the election is part of what a voter judges
about the incumbent: the judged president gains `economic_voting x x(t)` utility, the president's party a
share of it (`approval_party_carryover`, as for the record and the policy), and in a legislative election the
governing parties gain it. Positive x is good times: they reward the incumbent, bad times punish them. It is
**sociotropic** (the national economy, the same for every voter) and read **at the election** (voters judge
the recent economy, not the whole term; the AR(1) is persistent enough, phi 0.8, that this is a few quarters).
It rides on the policy record already threaded to every vote and every approval (`PolicyRecord.economy`;
empty `then` and `now` when no legislation runs, and `policy_gain` is then 0), so approval, and through it
legitimacy and the confidence vote, move with the economy as well. It needs
`events.economic_shock_enabled` (without it x stays 0) and `vote.mode: utility` (the model's own ballots, mode `llm`, do not
read it; a config rule refuses the pair rather than leave the weight inert).

**`events.scripted`**: a list of `{tick, kind}` (a `scandal` against the sitting president) or
`{tick, kind, magnitude}` (an `economic_shock` adding `magnitude` to x(t): negative a recession, positive a
boom). Each tick must lie in the run (a crisis after the last tick would silently never happen); a scandal
takes no magnitude; a scripted scandal needs `scandal_enabled` and a scripted shock `economic_shock_enabled`
(a disabled mechanism stays disabled); the schedule is held to the same rules whether parsed from YAML or built in
code, and a magnitude must be finite. The draws are still made, so **a schedule does not move the events stream**: with the
same seed a scripted shock changes the economy by exactly the impulse decayed (a test holds it). It is not the same run
plus an impulse, though: the changed economy changes approval, votes and recalls, so everything downstream that
draws from another stream can differ from that tick on. A scripted scandal on a tick where a random one also falls
is one scandal, not two, and the journal does not mark which events were scripted (the run's `config.json` holds the
schedule).

The scenario profile sets `economic_voting` 1.0. Its schedule is empty: a schedule is a scenario's input, which
the catalogue varies.

## Measured

Ten seeds, 8 years, 100 citizens, `--engine deterministic --profile scenario`, the rule-only twin, each arm
setting `economic_voting` and, where named, one economic shock at tick 12 (the presidential election is at
tick 16). Not pre-registered: a reading, reproduced by `python scripts/probe_welfare.py --output-dir <dir>`
(`--arm voting,tick,magnitude` re-runs one row); the shipped row is also what `run_polity_seed_sweep.py
--engine deterministic --profile scenario` reports.

| economic voting | crisis | mean approval | alternations | re-elections | archetypes (entropy) | in band |
|---:|---|---:|---:|---:|---|---:|
| 0 | none | 0.676 | 1.3 | 0.7 | realignment 6, stasis 3, alternation 1 (1.30) | 4/10 |
| **1** | **none** | **0.614** | **1.5** | **0.5** | **realignment 5, alternation 3, stasis 2 (1.49)** | **4/10** |
| 2 | none | 0.552 | 1.5 | 0.5 | realignment 5, alternation 3, stasis 1, churn 1 (1.69) | 3/10 |
| 0 | recession -0.8 | 0.667 | 1.2 | 0.8 | realignment 9, stasis 1 (0.47) | 6/10 |
| 1 | recession -0.8 | 0.470 | 1.9 | 0.1 | realignment 10 (0.00) | 5/10 |
| 2 | recession -0.8 | 0.399 | 2.0 | 0.0 | realignment 10 (0.00) | 3/10 |
| 2 | boom +0.8 | 0.706 | 1.1 | 0.9 | realignment 7, stasis 3 (0.88) | 3/10 |

- **The channel does what it is for.** Voters who weigh the economy at 2 turn a recession into a lost
  election: re-elections per run go from 0.8 to 0.0, alternations from 1.2 to 2.0, the incumbent's mean
  approval from 0.67 to 0.40. A boom does the opposite (0.71, 0.9 re-elections).
- **Without a crisis, weighting the economy still lowers mean approval** (0.676, 0.614, 0.552 at weights 0, 1,
  2) and raises variety. That is not a bias in the economy (x has mean 0): approval is the share of citizens
  above their tolerance, 0.68 here, and symmetric noise around a share above one half lowers it. A toy model
  (margin normal around +0.15, x normal with the AR(1)'s 0.167 standard deviation) gives 0.726, 0.691, 0.640.
- **A crisis at the same tick in every seed makes the runs alike.** Nine or ten of ten seeds read as
  realignment (entropy 0.47 and 0.00 bits): everyone gets the same shock, the same salience, the same push
  (ADR-033). The divergence test asks for variety across seeds of one scenario, so a catalogue's variety has
  to come from *varying the schedule across runs* (the tick, the size, the kind), which is what the schedule
  as data is for; one fixed crisis is a different experiment from the test.
- **The shipped value** (1.0, no crisis) moves the ten-seed divergence test from varied 1.30 bits, no dominant
  story no, to varied 1.49 bits, no dominant story yes (realignment holds 5 of 10, not more than half): three
  of its four criteria; the plausibility band still holds for 4 of 10 seeds (turnout below 0.5).
- **Random economic shocks do not happen**: the AR(1) climate (sigma 0.1, phi 0.8) has a standard
  deviation of 0.167 and `economy_shock_threshold` is 0.5, three of them. In the ten seeds with no crisis,
  one `economic_shock_tick` event in 80 seed-years (and 16 scandals, the expected 1.6 a run). Economic shocks
  are, in practice, scripted; the continuous wobble is what economic voting reads.

## Not settled

- **Sociotropic only.** Every voter reads the same x. No pocketbook voting (an economy that hurts some citizens
  and not others), no partisan perception (supporters of the incumbent seeing a better economy than opponents:
  Bartels 2002), and so still no per-citizen reach of a shock on the rule path (ADR-033's open point): the
  salience a scripted shock leaves is the same for everyone.
- **A short memory, by two channels the table mixes.** The vote reads the economy at the election only, and the AR(1)
  mean-reverts, so a recession two years before is gone from the ballot. But approval reads it every tick and
  `legitimacy.approval_weight` (0.5 in the scenario profile) blends approval into legitimacy's moving average
  (decay 0.9, about ten ticks), which feeds the incumbent's record term, the confidence vote and the recall
  floor: the economy persists for a few years there, and the effective weight on it is larger than
  `economic_voting` alone. The measured table is the sum of the direct term and that channel.
- **Legislative elections judge the economy only through a governing record,** which needs legislation on;
  without it the legislative vote ignores the economy (the scenario profile has legislation on). The model's own
  ballots (`vote.mode: llm`) ignore it: refused by a rule.
- **The convention is new, and emotions do not share it.** x was symmetric before (anxiety reads |x|, and so does
  the shock threshold that triggers a reaction); positive is now good for the vote, and nothing else read its
  sign. A scripted boom therefore frightens citizens exactly as much as a recession, and sets off the same
  salience reaction: a recession-only anxiety is a one-line change when it matters.
- **The weights are a reading.** 1.0 is a value between "does nothing visible" and "dominates the ballot"
  (utilities are distances in [0, 1] and x runs ±0.17 typically, ±0.8 in a crisis), from one seed set and the
  rule-only twin.
- **Scripted events are not marked as scripted in the journal**; the run's `config.json` holds the schedule.
- **A checkpoint written before these two fields cannot resume after them**: they change `config_hash` for every
  configuration (loud, at resume time), and the YAML parser requires both keys (`vote.economic_voting`,
  `events.scripted`), as it does for every other field.
