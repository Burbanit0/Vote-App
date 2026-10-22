# ADR-035: generations turn over, in place

**Status**: Accepted — built in the scenario profile only (plan-scenarios-v1, step 3c, part 1); `citizens.replacement_per_year` is 0 by default, which is the static population.
**Date**: 2026-10-22
**Context**: The electorate was immortal. `birth_enabled` and `death_enabled` were parsed and never implemented, so a 30-year run was one generation frozen in place: nobody entered, nobody left, and the views of the people who were 40 in year 0 were still 40-year-old views in year 30. Cohort replacement (Mannheim, Inglehart) is one of the standard sources of long-run realignment: a society changes partly because new people, formed in a different period, replace old ones.

## Decision

**`citizens.replacement_per_year`** (0 by default): each tick, every ordinary citizen leaves with probability `rate / ticks_per_year` and a newcomer takes the slot. It needs `citizens.static_population: false` and `dynamics.enabled` (a config rule). **`citizens.newcomer_spread`** (0.5 by default, 0.35 in the scenario profile) is the standard deviation of the noise a newcomer's views add to the circle they grew up in.

**Replace in place.** The newcomer keeps the citizen id, so ids stay `range(n)` (opinion dynamics index by it), the social ties of the slot, and the slot's issue residuals (the part of a person's views no factor explains, regenerated from the seed on every resume). Everything else is new:

- **Views**: the mean of the latent factors of the neighbours who are not leaving this tick (political socialisation: a cohort inherits what its elders came to think, hardened or not, ADR-033 included), plus `N(0, newcomer_spread^2)` on each factor. A slot with no tie left takes the population's mean.
- **Anchor**: the newcomer's own (`Citizen.anchor_factors`), so opinion dynamics draw them back to where they started, not to the slot's founding views. This is also the groundwork ADR-032 option D needs (an anchor that is a per-person value).
- **Traits**: priorities, tolerance, ambition and awakening threshold, drawn from the distributions the founding population used. **Party**: the nearest platform. **Emotions** start at zero, and the engagement state starts active, where the run tracks them.

**Exempt**: anyone holding an office or standing as a candidate, and the sitting sortition chamber (seated for a year). A former president, who is an elector with a record, can be replaced, and the newcomer has no record.

**Its own random stream** (`demography_rng`, seeded `[seed, 35]`, in the checkpoint), drawn once per slot per tick whoever is eligible, so its position never depends on who held office and no other stream moves. With the rate at 0 nothing is drawn and a run is byte-identical to one without the feature. Each replacement is journaled as `citizen_replaced` (`party_id`, `circle`).

**Panel stability ignores replaced slots.** The four-year factor correlation (ADR-012 D1) is computed over the people who were there for the whole window: a slot replaced inside it is excluded, and a window with fewer than three left yields no value.

## Measured

Ten seeds, 30 years, 100 citizens, the rule-only twin (`--engine deterministic --profile scenario`), the scenario profile at each setting of the two knobs. Not pre-registered: a reading, reproduced by `python scripts/probe_cohorts.py --output-dir <dir>` (`--arm rate,spread` re-runs one row). D1 is the four-year panel stability; D2 is the ratio of the final spread of positions to the initial one (ADR-012 wants it near 1).

| rate | spread | newcomers at the end | D1 | D2 | archetypes (entropy) | in band |
|---:|---:|---:|---:|---:|---|---:|
| 0 | - | 0% | 0.920 | 2.30 | realignment 10 (0.00 bits) | 1/10 |
| 0.03 | 0.2 | 54% | 0.898 | 1.75 | realignment 9, alternation 1 (0.47) | 4/10 |
| **0.03** | **0.35** | **52%** | **0.900** | **1.75** | **realignment 10 (0.00)** | **4/10** |
| 0.03 | 0.5 | 52% | 0.899 | 1.84 | realignment 10 (0.00) | 3/10 |
| 0.03 | 0.8 | 55% | 0.907 | 1.96 | realignment 10 (0.00) | 3/10 |
| 0.06 | 0.5 | 79% | 0.892 | 1.43 | realignment 10 (0.00) | 1/10 |

- **Replacement does what it was added for, on spread and on the band.** Without it the spread of positions more than doubles over 30 years (2.30): drift and radicalisation accumulate with nobody to dilute them. At 3% a year it grows by 75%, and four seeds of ten stay inside the plausibility band against one.
- **It does not add variety.** Every arm but one reads as realignment in all ten seeds (0.00 bits), as the rate-0 arm does. Over 30 years the realignment rule (mean shift of at least 0.1) saturates, so the 30-year archetype cannot tell these arms apart; the one arm with an alternation (spread 0.2) is one seed out of ten and is not a trend. Cohorts alone do not make runs differ from one another.
- **The shipped value** is rate 0.03, spread 0.35: a third of a generation in ten years (52% of the people are newcomers after thirty), with the best band reading at the larger spread of the two that tie. Between spreads 0.2 and 0.35 the readings differ by one seed. A rate of 0.06 replaces 79% of the population and leaves one seed of ten in the band (the spread falls to 1.43, but turnout does not).

## Not settled

- **The economy and the forum do not form a cohort.** The plan had newcomers drawn from a distribution that drifts with the forum's mean shift and the economy. They inherit the circle's mean, which carries whatever shifts and hardening the circle has had, but a recession does not mark a generation as such (formative years are not modelled).
- **A newcomer reuses the slot's residuals and ties.** The idiosyncratic part of their views is the departed person's, and they are born into the same circle: no new tie is drawn, and rewiring (step 3c, part 2) is a separate change. A petition's signer sets still hold the old ids: a petition signed by a leaver counts the newcomer as a signer.
- **No death or birth as such.** The population size is constant. A slot is a person leaving and another arriving; there is no growth, ageing or age-specific rate.
- **Officeholders and the chamber are exempt**, so the replacement rate they see is 0 while seated. A long-lived president ages not at all.
- **The 30-year archetype is saturated** by realignment under every arm (see above): a finer label (a threshold that scales with the run's length) is a change to `trajectory.py` that this ADR does not make.
- **A checkpoint written before these fields cannot resume after them**: they change `config_hash` for every configuration (loud, at resume time), and the YAML parser requires both keys, as it does for every other field.
