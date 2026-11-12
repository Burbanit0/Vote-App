# ADR-009: ordinary legislation — a policy status quo, bills, and the chamber's suspensive veto

**Status**: Accepted — built in S4.2 (`plan-polity-build-order.md`). Ships off, until the
calibration below.
**Date**: 2026-09-13
**Context**: Decisions D3 and D7, both dated 2026-09-13:

- **D3:** ordinary legislation comes before ADR-008's constitutional amendments.
- **D7:** the sortition chamber reviews bills, with its suspensive veto.

## Context

The polity elects a president and an assembly, and forms a coalition, but nothing it does
changes anything: there is no policy. Offices are held; nothing is decided. As a result:

- **The chamber has no agenda.** The sortition chamber deliberates with nothing in front of it,
  and its prompt tells it to hold still (`observations.md` OBS-004).
- **The veto is never used.** `sortition_chamber.veto_power` and `veto_delay_ticks` have been
  parsed since v6b and consumed by nothing.
- **Voters have nothing to judge.** A government's record has no content for voters to judge.

ADR-008 designed constitutional amendments, which change the rules. Ordinary legislation changes
policy under fixed rules, so ADR-008's comparability machinery (`law_version` segmentation) is not
needed here: every run keeps one ruleset.

The build order asks for:

- a policy vector in the issue space;
- a proposer who moves it on at most two dimensions within a step bound;
- assembly ratification with a coalition majority;
- a cohabitation block;
- the chamber's suspensive veto;
- targets named before code: policy congruence, the cost of ruling, and gridlock under
  cohabitation.

## Decision

### The status quo (`legislation.py`, `legislation:`)

Policy is a point in the same issue space as citizens' positions, one value per issue in [0, 1].
It starts at the population's per-issue median, a neutral origin that no party chose. Only an
enacted bill moves it.

`Legislature` (on `TickState`, checkpointed) holds:

- the policy;
- the seats and coalition from the last legislative election;
- the policy at the start of the current presidential term and of the current assembly;
- a suspended bill, if any.

There are no bills before the first legislative election, since there is no assembly to pass
them, and none while the presidency is vacant.

### A bill

Every `bill_interval_ticks` ticks, with no bill suspended, the agenda setter drafts one:

- **Who sets the agenda.**
  - *Unified government, or no coalition formed:* the president, aiming at their revealed position
    and weighting issues by their own priorities.
  - *Cohabitation* (the president's party outside the governing coalition, `metrics.is_cohabitation`):
    the government sets the agenda. It aims at the platform of the coalition's first party (its
    initiator), weighting every issue equally.
- **What the bill contains.** It moves policy on the (at most) `max_bill_dimensions` issues where
  the priority-weighted gap between aim and policy is largest (ties to the lower issue), each by at
  most `max_bill_step` toward the aim. With no gap left, no bill is drafted.

### Its path

1. **Assembly reading.** Every seated party votes for the bill if it brings policy strictly closer
   to its platform (the same Euclidean distance coalition formation uses), and against otherwise.
   The bill passes when the seats in favour exceed `assembly_majority_ratio` of all seats: the
   majority a coalition needs.
2. **Cohabitation block** (`cohabitation_block`). Under cohabitation, the president blocks a passed
   bill that moves policy away from their revealed position, measured with their priorities. A
   president's own bill never moves away from them, so the block binds only the government's
   bills.
3. **Chamber review** (first reading only, when the chamber sits). Each member votes for the bill if
   it brings policy strictly closer to their `chamber_position`, measured with their priorities.
   - **Suspensive veto.** A majority against is a veto when `veto_power: suspensive_limited`: the bill
     is suspended for `veto_delay_ticks` and blocks the agenda meanwhile. It then returns for a second
     assembly reading and the cohabitation check against that day's seats and president, and is
     enacted if it survives. The chamber cannot veto it twice.
   - **Consultative only.** Under `consultative_only` the review is journaled and changes nothing.
4. **Enactment.** Policy takes the bill's values.

Events: `bill_proposed`, `bill_voted` (with its reading), `bill_blocked`, `bill_reviewed`,
`bill_enacted`, and a yearly `policy_status` with the policy and its congruence (below).

Everything here is deterministic on both engines. `chamber_deliberation` keeps running unchanged
on the LLM path and moves the `chamber_position` a review reads. A model-decided proposal or review
is a later step, with its own pre-registered criterion and bake-off family before any prompt is
written (ADR-008's rule for decision types with no deterministic proxy).

### Voters judge policy (`vote.policy_retrospection`, ships at 0)

A policy record is where policy stood when an office's term began, and where it stands now. A
voter's gain from it is `d(voter, policy then) − d(voter, policy now)`, measured with their
priorities: positive when policy moved their way.

- **Presidential election.** The judged incumbent's utility gains `policy_retrospection × gain`. The
  incumbent is S4.1's: the holder whose term ends, or the president a rerun carries. Another
  candidate of their party gains `approval_party_carryover` of that.
- **Legislative election.** The governing parties gain `policy_retrospection × gain` in each voter's
  party choice. They are the coalition formed at the previous legislative election, or the
  president's party when none formed. The choice is the nearest platform by utility, and blank when
  even the best falls below minus the voter's threshold.

At weight 0 both votes are exactly today's (property-tested), so shipping the weight at 0 keeps
S4.1's and the legislative vote's control arms. This is the channel through which a cost of ruling
can arise at all. Moving policy toward a government's side leaves voters on the other side worse
off, and voters are otherwise blind to what a government did.

## Control arm and first acceptance

- **Disabled.** `legislation.enabled: false` (shipped) has no policy, no bills and no new events.
  The golden references and the bake-off bank do not move, and a static run's checkpoints gain no
  keys.
- **Retrospection at 0.** With `policy_retrospection: 0`, a policy record changes no ballot and no
  party choice (property).
- **Rules by hand.** Drafting, the assembly reading, the block, the review, the suspension and the
  second reading each match a hand-worked case.
- **Resume.** A legislating run killed mid-tick resumes byte-identical, a suspended bill included.

## Pre-registered facts for the calibration

**Setup.** Measured on the p100 deterministic twin (`run_polity_flagship.py`'s full-mechanism
config, sortition chamber on), seeds 1–10, **16 years**, which gives four legislative elections per
run.

**Search.**

- `bill_interval_ticks` ∈ {1, 2, 4}
- `max_bill_step` ∈ {0.05, 0.10, 0.20}
- `vote.policy_retrospection` ∈ {0, 2, 5, 10}

**Selection.** L1–L3 are judged at `policy_retrospection: 0`. L4 then picks the smallest weight that
meets it. Among the settings where every fact holds, the lowest bill rate wins, then the smallest
step. If none qualifies, legislation stays off and the failing facts are reported.

1. **L1 — checks moderate policy (congruence).** Averaged over the ticks with a policy in force and
   a sitting president, policy's distance to the population's per-issue median is smaller than the
   president's revealed position's distance to it. Distance is RMS per issue.
2. **L2 — the institution is alive.** At least one bill is enacted per presidential term on average,
   and policy moves in at least 9 of 10 seeds.
3. **L3 — gridlock under cohabitation.** Pooled over seeds, the share of drafted bills that are
   enacted is lower under cohabitation than under unified government. It is reported as unmeasured
   if either regime drafts fewer than 20 bills.
4. **L4 — the cost of ruling.** The governing parties' combined legislative vote share falls, on
   average, from the election that made them the government to the next one. It falls by more than
   at `policy_retrospection: 0`. The fall itself is the regularity comparative studies of
   incumbent parties report (Paldam 1986; Nannestad and Paldam 2002).

### Calibration result (2026-09-13)

`fast_api_voter/scripts/calibrate_legislation_results.md`. Readings the ADR left open were fixed in
the script before the grid ran.

**Nothing qualifies, and legislation stays off.** No setting meets all four facts (0 of 9). L2 fails
in every one; the other three facts hold in every one.

- **L1 holds.** Policy stays 0.012–0.024 from the median, while the sitting president stands 0.169
  from it.
- **L3 holds.** Under cohabitation 0–4.3% of drafted bills are enacted, against 2.8–27.3% under
  unified government.
- **L4 holds from weight 2** (weight 5 at a bill every tick with step 0.2). The governing share
  falls 0.07–0.43 points. At weight 0 it does not move at all, since a static population casts the
  same legislative ballots every time.
- **L2 fails everywhere.** 0.04–0.23 bills are enacted per presidential term, and policy moves in
  3–9 of 10 runs. Two things drive this.
  - *Few bills pass.* A sincerely voting assembly passes few of them.
  - *Terms are short.* In this twin a presidency lasts a median of 2 ticks before its recall
    (`observations.md` OBS-015), so there are about 20 terms per 16-year run.

A calibration against a twin with a working presidency is a new pre-registration (D9 in
`plan-polity-build-order.md`).

## Consequences

- **New state and events.** The `legislation` config section and the `vote.policy_retrospection`
  weight enter `config_hash`. Six event types are added.
- **The chamber's own deliberation is unchanged.** It keeps its prompt and its calls. D7's "until
  then" is met by the review's existence, not by retiring those calls. Whether to retire them
  belongs to the model-decided review step.
- **Measurement.** Policy congruence is measured against the population's median. With dynamic
  citizens (S4.3) that median moves, so congruence can drift without any bill.
- **ADR-008.** It stays proposed. Amendments build on this status quo and this assembly vote, and
  bring the `law_version` segmentation ordinary legislation does not need.
