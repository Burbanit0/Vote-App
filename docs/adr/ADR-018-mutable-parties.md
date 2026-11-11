# ADR-018: mutable parties — an agent joins, leaves or founds, and a party too small is dissolved

**Status**: Accepted — built in Phase 4.1 of `docs/plan/polity/plan-polity-agency-roadmap.md`.
**Date**: 2026-09-28
**Context**: the roadmap's goal of parties that form. The five k-means parties of `parties.py`
never changed. ADR-016's forum turn is the one place a citizen already acts, so membership
moves ride on it.

## Decision

- **The forum turn carries the move.** `ForumTurn` gains `party_move` (`none`, `join`, `leave`,
  `found`) and `party_id` (the party to join, -1 otherwise). No new model call: an agent who
  posts may also change party. It is switched on by `agents.party_moves` (needs `agents.forum`);
  the prompt then shows each party's share of the citizens and its three firmest planks.
- **The kernel refers.** `simple_rules.apply_party_move` applies the move and says what it did
  (`join 2`, `leave`, `found 5`, or nothing when refused). A refused move is not retried.
  - `join` needs an existing party other than one's own.
  - `leave` makes the citizen an independent (`party_affiliation` is `None`). An independent
    can be a rupture candidate, measured against the nearest platform.
  - `found` needs `parties.birth_enabled`. The new party's platform is the founder's own
    positions. Its co-founders are the founder and every citizen who would sign for those
    positions (the ballot-access signature rule) and stands nearer to them than to their own
    party's platform; they change party with the founder. It holds only if they are at least
    `parties.founding_ratio` of the citizens. That ratio is an article, so the polity can make
    parties easier or harder to found.
- **A party too small is dissolved.** With `parties.death_enabled`, after any move, a party
  under half the founding ratio of the citizens is dissolved. Its members go to the nearest
  party left; independents stay independent. The last party and any party with seats in the
  assembly are kept, because the assembly is a snapshot of the last election.
  The gap between the founding ratio and half of it stops a party being founded and dissolved
  in turn.
- **State is the citizens and the party list.** Membership is `Citizen.party_affiliation` and
  the list is `TickState.parties`; both were already checkpointed, so a run that never moves
  checkpoints as before and a resume across a founding is byte-identical. A new party's id is
  the highest id plus one.
- **Journal.** The turn's `forum_post` carries `party_move`. `party_founded` and
  `party_dissolved` are institutional events, so they show on the explorer's timeline.

## Amendment 2026-10-08: founders are told the seat threshold

`docs/plan/PLAN_BEYOND_CI.md`, decision D2. The forum's party-move rules (`_party_move_rules`)
now state the electoral threshold, read from the live constitution: "At a legislative election,
a party with less than X% of the votes cast for parties wins no seat."

- **Why.** Until now no agent saw the threshold, so the LLM could respond to it only through
  rule-driven dissolution, never in its own founding decisions. The plan's first experiment
  (W2.1) asks whether the threshold changes how often parties are founded. Without this line
  it could only find "no effect", by construction.
- **Neutrality.** It is a consequence, stated like the others, with no advice (C4). The forum
  probe of `check_agent_prompt_neutrality.py` (n=30, qwen3:8b, seed-2 phase-4 citizens) gave
  the same verdicts before and after the change: sensitivity to the co-founder count 97%
  both times; the paraphrase moves 6%; `leave` is never taken in either run (a dead option
  that predates this change). One cell moved: citizens who could not found answered `join`
  12% of the time after, 0% before. That is just above the probe's ±7% noise band at n=30, and
  the paraphrase stayed at 6%.
- **The gate.** `check_agent_prompt_neutrality.py --probe threshold` asks the same able
  founders (the citizens who could found) once told 3% and once told 7%. It counts `found`
  only, and tests the paired answers with an exact McNemar test. If founding does not move
  (p >= 0.05), the experiment stops there (W2.1). A move in the wrong direction is reported as
  such. **Result, 2026-10-09: STOP.** 59/60 founded at both thresholds (p = 1), and at least 13 of
  the 14 founders told fewer than 7 backers founded at 7% (OBS-045).
- **A 0% threshold** (legal, and amendable to) drops the sentence rather than saying "less
  than 0%".
- **Not changed.** The kernel: seats, founding and dissolution rules are as before.

## Amendment 2026-10-21: a party is locked for a year after its founding

OBS-052: on the 8B, founders re-founded their own party tick after tick (47 parties founded and 30
dissolved in 8 years for 100 citizens; 11 of the 29 founded parties dissolved went within 2 ticks). The gap between the founding ratio and
half of it did not stop a party being founded and dissolved in turn, as this ADR expected: a founding takes
every co-founder at once, so a party loses its members in one move.

- **The lock.** For `parties.founding_lock_years` after a party is founded (1 by default, so 4 ticks: the
  founding tick and the 3 after it; 0 turns it off), its members can neither found a party nor be brought
  into another's founding (`simple_rules.locked_parties`, passed to `cofounders` and `apply_party_move`). It is
  not an article. A party whose founding tick lies after the tick asked about is not locked.
- **What stays free.** Joining and leaving: a member of a locked party may still join another or become an
  independent. Dissolution is unchanged, so a locked party that its members leave can still be dissolved.
- **The lock follows the party, not the citizen.** A founder who leaves their party is free to found again,
  and so are the members of a locked party that is dissolved. What the lock stops is OBS-052's damage: a
  founding cannot take a young party's members. Locking the citizen would need state on every citizen; it
  waits for a run to show founders leaving to found again.
- **Same tick.** The lock is computed before every move, so a party founded earlier in a tick is locked for
  the rest of it.
- **The citizen is told.** The forum turn's stand line counts co-founders the same way and tells a member of
  a locked party: "Your party P was founded at tick T: until tick U, its members can neither found a party
  nor be brought into one." Without it the model would propose a move the kernel refuses (C3/C5). The forum's
  prompts are all written before the tick's first move, so a citizen swept into a party founded earlier in the
  same tick is refused without having been told; their next tick's stand line says it.
- **State.** `Party.founded_tick` (None for the parties a run starts with). The checkpoint writes it only for
  a founded party, so the party list of a run that never founds is written as before, and a party list from
  before the amendment loads as established. The new setting changes the config hash, though, so a checkpoint
  taken before this amendment does not resume under it, as with any config change.
- **Deterministic engine.** Unchanged: party moves come only from the forum turn, which needs the model.
- **Not changed.** The founding ratio, the dissolution rule, the platform of a new party.

## What this ADR does not settle

- The party leader's `party_leader_turn`, which would move a platform. A platform is fixed at
  founding for now; it waits for a run to show parties whose platform members outgrow.
- A crowd citizen's own moves. The crowd changes party only when a founder brings them along
  or their party is dissolved.
- A cap on the number of parties. The founding ratio bounds it (at most 1/ratio parties, 20 at
  the default 0.05).
- The explorer's diary line for a move: the event has it, the panel does not show it yet.
