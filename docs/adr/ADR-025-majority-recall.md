# ADR-025: a recall needs the population against the president

**Status**: Accepted — built in the exploration profile (owner's decision, 2026-10-11).
**Date**: 2026-10-11
**Context**: In the phase11 ensemble, 41 of 70 presidencies ended in a recall at the legitimacy floor, and
every one of those 41 presidents was still approved by a majority (54 to 80%, median 71%; OBS-047). Two
things combined:

- **A mobilised minority:** the model mobilises on a third of its pressure acts (OBS-019).
- **A tenfold amplification:** `update_legitimacy` weighed support at a tenth (`0.9 L + 0.1 m`) and
  pressure at full weight, so legitimacy settled at `m - 10 e`. About 1.6 citizens in a hundred
  mobilising each tick was enough to recall a median president.

The owner's rule: a president should be recalled when the population is against them, not a few of them.
Of the rules OBS-047 replayed, the owner took both of the two that express it.

## Decision

- **Pressure weighs like support** (`legitimacy.pressure_like_support`):
  `L(t) = decay L(t-1) + (1 - decay)(m - ecart)`. Legitimacy keeps its memory (decay 0.9, about ten
  ticks) and settles at support minus pressure, not support minus ten times the pressure.
  - Holding the legitimacy floor now takes a sustained pressure of `m - 0.2`. Through street pressure
    (memory 0.85, weight 0.5) that is a share of about `(m - 0.2) / 3.3` of the citizens mobilising every
    tick: 17% for a median president (m = 0.76), 9% for one at m = 0.5.
- **The floor calls a vote** (`legitimacy.floor_calls_vote`). Legitimacy under the floor no longer
  recalls by itself. It calls the confidence vote a petition calls (§7bis.4a): every engaged citizen
  votes, and the president is recalled only if a majority does not keep them (a tie removes, as before).
  - **Journal:** `confidence_vote_triggered` carries `cause: legitimacy_floor` and none of a petition's
    fields. A lost vote is journaled `recalled` with `trigger: confidence_vote`, which the explorer
    already labels. `averted_recall` stays a petition vote's veto of a same-tick floor trip.
  - **Petition metrics** (the indexer's success and removal rates, the digest's `confidence_votes`)
    leave the floor's votes out.
  - **A won vote** replaces the mandate with its keep ratio, as a petition's does, so support is
    re-measured. It also restores legitimacy to that ratio, as an election sets it to the mandate: the
    majority has just been shown. Without that, legitimacy would stay under the floor and call a vote
    every tick.
  - **Three edge cases:**
    - A vote already lost the same tick recalls without a second vote.
    - With no one left to vote, there is no vote and no recall.
    - A president who stayed past their term (ADR-022) cannot be recalled, so no vote is put.
- **Both switches are false by default** (today's rule: the flagship, the golden and every past run) and
  true in the exploration profile. Petitions still call votes as before.
- The two votes share one function (`_confidence_vote`), which the petition path now calls too.

## Measured

OBS-047's replay of the 41 recalled presidencies, behaviour held fixed:

- **Pressure weighed like support:** none settles under the floor (median fixed point +0.61, against
  -0.85 today).
- **Floor calls a vote:** none would have lost it, since all 41 had a majority behind them.

Neither is a forecast: with presidencies lasting longer, citizens and agents act differently.

**On the deterministic twin, with behaviour free** (exploration profile, 8 years, population 100,
seeds 1-10, each switch alone):

| switches | presidential elections | recalls | votes the floor called |
|---|---:|---:|---:|
| neither (today) | 78 | 49 | -- |
| pressure like support | 31 | 1 | -- |
| floor calls a vote | 30 | 0 | 108 |
| both | 30 | 0 | 1 |

- **The pressure rule does the main work.**
- **The vote alone is heavy.** Even with a won vote restoring legitimacy, tenfold pressure drags it back
  under the floor within a few ticks: 108 votes.
- **Together,** the floor is reached once in 80 years of presidencies, and the vote kept the president.
  The 2 petition votes were kept in every arm.
- **The LLM path is not measured.** The twin's citizens mobilise by a rule, not the model.

## Not settled

- **The model's mobilisation rate** (OBS-019) is untouched. It decides how often the floor is reached
  and is not measured against anything real.
- **No vote is held while legitimacy merely approaches the floor.** A president sitting just above it
  is safe whatever approval says.
- **Every tick under the floor calls a new vote.** Nothing spaces them out (`recall_cooldown_ticks`
  gates repeat recalls, not votes). A won vote restores legitimacy, so with both switches that is rare
  (one floor vote in ten twin runs), but with the vote alone it was 108.
- **Two changes in one arm.** Their effects can't be told apart in an LLM run with both on; the twin
  separates them (above).
