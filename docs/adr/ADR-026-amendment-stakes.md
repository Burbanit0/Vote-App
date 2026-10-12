# ADR-026: the president knows what a rule change would do, and always answers whether to amend

**Status**: Accepted — built in the exploration profile (owner's decision, 2026-10-11).
**Date**: 2026-10-11
**Context**: Once presidents lasted (ADR-025), three of phase12's five seeds ratified a third term,
each proposed by the sitting president. The owner wants to keep that, and wants presidents to try
other rules too: the voting method, the institutions. Two things stood in the way:

- **Nothing to weigh a voting method by.** A president could propose one, but could not tell whether it
  would help them. Across every run so far there were 4 such proposals, against 22 for the electoral
  threshold and 15 for the term limit.
- **The amendment was an optional field of the president's turn.** On Qwen3-8B, an optional act field
  is weighed only when the model already means to use it (OBS-031): campaigning was filled 1 time in
  160 while optional, and `extra_legal` 0 of 98.

## Decision

- **The stakes** (`agents.amendment_stakes`, off by default, on in the exploration profile). The
  president's briefing adds, under the constitution in force:
  - **The voting method:** the last presidential election's ballots counted under each of the 13
    methods, and whom each elects: "you" or a citizen. These are the ballots ADR-020 already keeps for
    referendums.
  - **The seats:** the last legislative election's party votes re-seated under each seat allocation and
    at thresholds of 0, 3, 5, 8 and 15% (the article's ends and the usual bars between), giving the seats
    the president's party wins.
    - Ties are drawn from the election's own seeded lot (`seat_lot`, which the election now uses too), so
      "under the rules in force" is the seats the party holds.
    - The legislature keeps those votes and their tick; they are checkpointed, and older checkpoints load.
  - **Only when an amendment can be proposed:** with one pending, or no chamber drawn, the stakes are left
    out.
  - **The contract:** these are facts the kernel computes, which give the state a scale (C3). Nothing
    says which change to propose (C4).
- **The amendment is required and nullable**, like `campaign` and `extra_legal`: every turn says
  whether it proposes. A proposal made while none can be is dropped, as before, so no turn fails for
  being filled in.

## Measured

`scripts/check_amendment_stakes.py` was run on the 34 sitting presidents of the finished exploration
runs (phases 8–12 and the 2-year constitutions sweep), each in their final state, 2 turns each, at
temperature 0.6. The optional-field column ran on ca39ec09, the required-field column on the branch.

| | amendment optional | required |
|---|---:|---:|
| without the stakes | 5 proposals in 68 turns, 2 articles | 33 in 68, 7 articles |
| with the stakes | 10 in 68, 2 articles | 27 in 68, 5 articles |

- **The required field is the lever.** Presidents propose in about half their turns, across the
  constitution:
  - voting method 5
  - seat allocation 5
  - electoral threshold 7
  - petition threshold 8
  - term limit 5
  - referendum 2
  - founding ratio 1

  The reasons are often openly self-serving: "plurality to simplify elections and secure
  re-election"; "lowering the threshold reduces the risk of confidence votes".
- **The stakes change what is proposed, not how often.** 16 of 27 proposals become electoral-threshold
  changes, argued from the numbers shown: "Lowering the threshold will help my party gain seats", "to
  increase my party's seat chances".
  - Voting-method proposals fall from 5 to 2, and seat allocation from 5 to 0.
  - Neither of the two method proposals would have elected the president.
- **The unit is the president, not the sample.** A president's turn barely varies at temperature 0.6:
  on phase12's five presidents, 40 samples came out 40 alike in one run and 0 of 40 in a rerun of the
  same turns. The counts above are therefore over 34 presidents, and the stakes' effect on what is
  proposed is a tendency from small numbers.
- **The cost.** More proposals means more invalid ones: abolishing the term limit while
  `refuse_to_leave` exists, or a fourth term. They cost retries, and 1 turn in 136 used up all its
  retries.

## Not settled

- **Final states only.** Every probe state is a president at a run's last tick, with an empty memory.
  How often presidents amend over a whole run, and what the chamber ratifies, needs an ensemble.
- **Thresholds only.** The seats are shown at five thresholds and the three seat allocations, not at
  other assembly sizes or with other articles changed.
- **Votes as cast.** The seats re-seat the votes as cast: the mechanical effect of each rule. Under
  ADR-024, voters cast them against the threshold in force, so a lower bar would also have kept some
  deserters at home. That is not shown, and the stakes understate what a lower bar gives a small
  party.
- **The probe builds its own briefing.** It does not reuse the kernel's, so a later change to the
  president's briefing has to be mirrored in it. It also checks that each probed run was founded on the
  exploration profile's rules, and skips any run that was not; the 34 probed runs all were.
- **Only the president sees them.** Chamber members vote on a proposal
  without the stakes.
