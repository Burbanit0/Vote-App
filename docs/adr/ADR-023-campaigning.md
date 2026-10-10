# ADR-023: campaigning

**Status**: Accepted — Phase 5.2 of `docs/plan/polity/plan-polity-agency-roadmap.md`.
**Date**: 2026-10-02
**Context**: The limit-testing log asked for this and nothing else. Across three 8-year runs
(OBS-035) the agents' `other_initiative` field held 101 entries, and 56 of them wanted a way to
reach part of the electorate — "targeted outreach to swing voters on healthcare and education",
"run ads emphasising strong worker protections", "engage in public debates" — in every seed. A
nominee could move its platform (`positions`) and make one public statement (`speech`), and had no
way to address anyone in particular. Nothing extra-legal was ever asked for, so on the roadmap's own
rule ("build first the acts agents actually attempted") this comes before Phase 5's remaining acts.

## Decision

- **A nominee may campaign on one issue**, through `campaign` on `CampaigningNomineeTurn`: an object
  of `{issue, audience}`, or null. The field is **required and nullable**, which is the only shape
  that survived measurement -- the other two were each tried live first:

  | shape | act used | retries |
  |---|---:|---:|
  | two required sibling fields, a validator refusing half a campaign | 85-95% | **35%** (the model set one field and left the other) |
  | one optional nested object | **1 of 160** | 0% |
  | one required, nullable nested object | 22-60% | 2% |

  Required so the act is always weighed (OBS-031: a field the model may omit, it omits), nullable so
  declining is expressible, nested so half a campaign cannot be said at all.
- **Salience, not persuasion.** The citizens reached come to weigh that issue more when they compare
  candidates; their opinions do not move. `weighted_distance` already weights each issue by the
  voter's own `issue_priorities`, so the effect flows through the vote rule that exists. Nothing is
  added to that rule and no second copy of it appears.
- **That makes it a choice rather than a gain.** Raising an issue a rival owns helps the rival, and
  `_campaign_rules` says so in the prompt — a fact the nominee needs in order to choose an issue at
  all, and not advice about what to choose (contract clause C4).
- **The move keeps the simplex.** `salience.raise_salience` gives the issue `step` of the weight it
  does not already hold and scales the others by `1 - step`, so the priorities still sum to exactly
  1. That sum is load-bearing: `weighted_distance`'s range, and so every `blank_threshold`
  comparison in the engine, depends on it, and two tests in `test_polity_citizen.py` assert it.
- **Two audiences, both computed by the kernel.** `base` is the nominee's own party, so an
  independent nominee reaches nobody. `undecided` is the citizens no candidate currently speaks for,
  read off `utility_ballot` rather than a second copy of the blank rule.
- **`campaign.salience_step`** is the one knob (0 = no campaigning, every run before this). It needs
  `agents.nominees`, since the act is a field of the nominee's turn. The exploration profile sets 0.15.
- `campaign_run` (institutional, so it reaches agent memory as public record) journals the issue, the
  audience, how many citizens heard it and the step. A campaign that reached nobody is journaled too:
  that an independent nominee has no base is a fact about the run.

## Measured

`scripts/check_agent_prompt_neutrality.py --probe campaign` (40 nominees per cell per wording),
against the nominee's standing in the poll:

| | no campaign | base | undecided |
|---|---:|---:|---:|
| behind in the poll | 32% | 8% | 60% |
| ahead in the poll | 57% | 20% | 22% |

All three checks pass: sensitivity 38% against a 20% noise band, no dead option, and rewording moves
the answer 12% where the state moves it 38%. A nominee behind chases the citizens no candidate speaks
for and one ahead mostly sits still -- strategy the mechanism allows rather than the prompt instructs.

*Re-measured 2026-10-07 (OBS-043), n=80:* behind in the poll 51% / 14% / 35%, ahead 74% / 14% / 12%. The
table above is one n=40 run, and the probe's run-to-run variance exceeds its binomial band: the shares are
that run's; the ordering holds. It was also measured with a prompt sentence claiming own-party candidates count
for more, false in every profile; removing it moves nothing beyond the noise.

## Not settled

- **Whether 0.15 is the right step** is a guess, as ADR-021's thresholds were. Too small and
  campaigning is decorative; too large and one campaign decides an election.
- ~~Reach is unbounded within an audience.~~ **Measured and fixed (OBS-036).** The run that showed
  it mattered came immediately: uncapped, each campaign reached ~60 citizens of 100 and 91% of the
  electorate ended near single-issue. `campaign.max_reached` now draws who hears a campaign by lot
  from the audience, on a seeded `campaign_rng` checkpointed like the other streams; the exploration
  profile sets 12. Whether 12 is right is unverified.
- **The effect never decays -- accepted for now (OBS-037).** Capped at 12, campaigning leaves a 0.34
  median attention on a citizen's biggest issue against 0.17 with it off, and nominees converge on one
  issue. The owner validated that on 2026-10-03 as plausible behaviour rather than a defect. Decay stays
  unbuilt until a run shows concentration climbing with run length, which a 30-year run might.
- **Only nominees campaign.** A sitting president cannot, though `other_initiative` from presidents
  did not ask for it.
- **The word "campaign" was already taken.** `nominee_system_prompt` has always said "You may
  campaign on a platform" for what is only a platform move, which OBS-035 suspects of priming the
  asks. The two now sit side by side; whether the older wording should change is unmeasured.
