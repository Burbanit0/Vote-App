# ADR-035: generations turn over, in place

**Status**: Accepted — built in the scenario profile only (plan-scenarios-v1, step 3c, part 1); `citizens.replacement_per_year` is 0 by default, which is the static population.
**Date**: 2026-10-22
**Context**: The electorate was immortal. `birth_enabled` and `death_enabled` were parsed and never implemented, so a 30-year run was one generation frozen in place: nobody entered, nobody left, and the views of the people who were 40 in year 0 were still 40-year-old views in year 30. Cohort replacement (Mannheim, Inglehart) is one of the standard sources of long-run realignment: a society changes partly because new people, formed in a different period, replace old ones.

## Decision

**`citizens.replacement_per_year`** (0 by default): each tick, every ordinary citizen leaves with probability `rate / ticks_per_year` and a newcomer takes the slot. It needs `citizens.static_population: false`, `dynamics.enabled` and `social_graph.enabled` (a config rule: without a graph every circle is empty and each generation is drawn around the population's mean). **`citizens.newcomer_spread`** (0.5 by default, 0.35 in the scenario profile) is the standard deviation of the noise a newcomer's views add to the circle they grew up in.

**Replace in place.** The newcomer keeps the citizen id, so ids stay `range(n)` (opinion dynamics index by it), the social ties of the slot, and the slot's issue residuals (the part of a person's views no factor explains, regenerated from the seed on every resume). Everything else is new:

- **Views**: the mean of the latent factors of the neighbours who are not leaving this tick (political socialisation: a cohort inherits what its elders came to think, hardened or not, ADR-033 included), plus `N(0, newcomer_spread^2)` on each factor. A slot with no tie left takes the population's mean.
- **Anchor**: the newcomer's own (`Citizen.anchor_factors`), so opinion dynamics draw them back to where they started, not to the slot's founding views. This is also the groundwork ADR-032 option D needs (an anchor that is a per-person value).
- **Traits**: priorities, tolerance, ambition and awakening threshold, drawn from the distributions the founding population used. **Party**: the nearest platform. **Emotions** start at zero, and the engagement state starts active, where the run tracks them.

**Exempt**: anyone holding an office or standing as a candidate, anyone who has been president (the newcomer would share their id in the office history and read as the same person, with a fresh term-limit record), the sitting sortition chamber (seated for a year), and the citizens the election in progress still counts on (those who declared candidacy, those barred, the incumbent re-running).

**What the run keyed by id does not outlive the person.** A replaced citizen's signature leaves any open petition, their mobilisation of the previous tick no longer counts for their neighbours, and the agents' memory of that id (their own moves, their petitions) is cleared when `citizen_replaced` is read, so the newcomer remembers nothing of who left.

**Its own random stream** (`demography_rng`, seeded `[seed, 35]`, in the checkpoint), drawn once per slot per tick, and a newcomer's inputs for every slot the rate picks whether or not it is exempt, so its position never depends on who held office and no other stream moves. With the rate at 0 nothing is drawn and a run is byte-identical to one without the feature. Each replacement is journaled as `citizen_replaced` (`party_id`, `circle`).

**Panel stability ignores replaced slots.** The four-year factor correlation (ADR-012 D1) is computed over the people who were there for the whole window: a slot replaced inside it is excluded, and a window with fewer than three left yields no value.

## Measured

Ten seeds, 30 years, 100 citizens, the rule-only twin (`--engine deterministic --profile scenario`, which includes ADR-034's economic voting), the scenario profile at each setting of the two knobs. Not pre-registered: a reading, reproduced by `python scripts/probe_cohorts.py --output-dir <dir>` (`--arm rate,spread` re-runs one row). D1 is the four-year panel stability (ADR-012's band is 0.70 to 0.90); D2 is the ratio of the final spread of positions to the initial one (ADR-012 wants it near 1).

| rate | spread | newcomers at the end | D1 | D2 | archetypes (entropy) | in band |
|---:|---:|---:|---:|---:|---|---:|
| 0 | - | 0% | 0.917 | 2.33 | realignment 10 (0.00 bits) | 2/10 |
| 0.03 | 0.2 | 53% | 0.899 | 1.77 | realignment 10 (0.00) | 0/10 |
| **0.03** | **0.35** | **53%** | **0.901** | **1.83** | **realignment 10 (0.00)** | **0/10** |
| 0.03 | 0.5 | 53% | 0.904 | 1.83 | realignment 10 (0.00) | 1/10 |
| 0.03 | 0.8 | 53% | 0.908 | 1.98 | realignment 10 (0.00) | 2/10 |
| 0.06 | 0.5 | 75% | 0.890 | 1.52 | realignment 10 (0.00) | 1/10 |

- **Replacement does one thing here: it holds back the growth of the spread.** Without it the spread of positions more than doubles over 30 years (2.33): drift and radicalisation accumulate with nobody to dilute them. At 3% a year it grows by 77% to 98% (1.77 to 1.98), at 6% by 52%. A larger newcomer spread dilutes less, as it should. Panel stability falls from 0.917 to about 0.90, the top of ADR-012's band, because the correlation excludes replaced slots but the people who stay are pulled toward their neighbours' newcomers.
- **It does not add variety.** Every arm reads as realignment in all ten seeds (0.00 bits). Over 30 years the realignment rule (mean shift of at least 0.1) saturates, so the 30-year archetype cannot tell these arms apart. Cohorts alone do not make runs differ from one another.
- **It does not bring runs into the plausibility band.** Zero to two seeds of ten are inside it in every arm, with or without replacement, and the counts are not ordered by the rate, so they are noise. For the two arms whose failures were counted, the shipped one fails volatility in 4 seeds (as the rate-0 arm does), panel stability in 6 (8 without), and turnout in 3 (none without): the one thing replacement made worse is turnout.
- **An earlier reading of this table said otherwise** (4 seeds of ten inside the band at 3% against 1 without). It was taken before ADR-034's economic voting was merged into the branch, which moves the band on its own; the table above is re-measured on the merged code, after the review fixes (former presidents exempt, the stream drawn for every picked slot).
- **The shipped value** is rate 0.03, spread 0.35: about half the people are newcomers after thirty years, a spread that is not a copy of the circle (0.2) and not independent of it (0.8). Between 0.2 and 0.5 the readings differ by about one seed, which is noise. It is shipped in the scenario profile because a society that never changes its members is not the object of study, not because it improved the divergence test: it does not.

## Not settled

- **The economy and the forum do not form a cohort.** The plan had newcomers drawn from a distribution that drifts with the forum's mean shift and the economy. They inherit the circle's mean, which carries whatever shifts and hardening the circle has had, but a recession does not mark a generation as such (formative years are not modelled).
- **A newcomer reuses the slot's residuals and ties.** The idiosyncratic part of their views is the departed person's, and they are born into the same circle: no new tie is drawn, and rewiring (step 3c, part 2) is a separate change. Past posts in the forum feed stay attributed to the id.
- **No death or birth as such.** The population size is constant. A slot is a person leaving and another arriving; there is no growth, ageing or age-specific rate.
- **Officeholders, former presidents and the chamber are exempt**, so they never age out: the replacement rate falls a little short of the nominal one (a few percent of slots at most).
- **The 30-year archetype is saturated** by realignment under every arm (see above): a finer label (a threshold that scales with the run's length) is a change to `trajectory.py` that this ADR does not make.
- **A checkpoint written before these fields cannot resume after them**: they change `config_hash` for every configuration (loud, at resume time), and the YAML parser requires both keys, as it does for every other field.
