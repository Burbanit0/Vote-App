# ADR-008: the law system — seam, bounded amendment, and comparability (design only, not built)

**Status**: Proposed — design settled, implementation deliberately deferred (see
"When to build" below)
**Date**: 2026-09-11
**Context**: `lets-build-a-solid-spicy-otter.md` ("The law system — design now,
build after Track B"), written while closing out Tracks A/B/C/E of that plan

## Context

Today a `PolityConfig` is fixed for the whole run: every institutional parameter
(`recall_floor`, `petition.signature_threshold`, the pressure menu, the electoral
method, all of it) is read from one frozen dataclass tree, generated once at
`load_config()` and never touched again. A polity that can amend its own rules
mid-run — a real constitution, not a fixed ruleset — is a categorically more
interesting object to simulate than one that cannot, and the design doc's own
scope table names it as the natural next increment (v8) without ever specifying
it.

**There is no law concept in the domain today, and this is new construction, not
a wiring job.** `legislative_result` (the assembly election's own outcome) carries
only `{seats, votes, blank_count}` — it is an election result, not legislation.
No decision type proposes a rule change, no schema represents one, and nothing
anywhere reads a config value conditionally on "which version of the rules is in
force right now." Every existing mechanism that varies over time (recalls,
coalitions, mandates, positions) varies *citizen or institutional state* within a
ruleset that itself never moves.

This ADR settles three things the plan's own text asked to be settled on paper
before any code: the seam, the bound on what a law can touch, and how a run whose
rules changed mid-flight stays honestly comparable to one that didn't. It
deliberately does not produce an implementation — see "When to build."

## Decision

### 1. The seam: a new decision type on the sortition chamber, not a repurposed `chamber_deliberation`

The sortition chamber is the right *organ* — it already deliberates on a live
cadence (`is_sortition_rotation`, §6bis.3) with a stable membership and its own
journaled decision type. But `chamber_deliberation` (dt=11) itself is the wrong
*mechanism* to extend: today it is a per-member `PositionShift` on that member's
own `chamber_position` — a personal stance, sincere-or-shifted, with no notion of
a proposal, a quorum, or a resolution. Repurposing its existing schema would
conflate "where I personally stand" with "what the chamber collectively decides,"
which is a different question needing its own vehicle.

**Proposed instead**: a new decision type, `law_proposal` (working name), fired
on the same rotation cadence as `chamber_deliberation`, structured as two phases
already familiar from mechanisms this project has built before:

- **Propose**: at most one active proposal at a time (mirrors `PendingRerun`'s own
  "never a second mechanism for the same concern" discipline) — a bounded-menu
  choice of *which* amendable parameter to move and by how much, drawn from the
  registry in §2 below. Framed the same non-prescriptive way `pressure_action`'s
  menu is: the model chooses from real, legal options, never told which one is
  "correct."
- **Ratify**: the SAME batched-vote shape `cast_votes`/`decide_coalition` already
  use (a `{decisions: [...]}` envelope, one decision per chamber member,
  majority-or-configured-threshold to pass) — not a new voting primitive, the
  existing one applied to a new question.

This keeps the chamber's own dt=11 completely unchanged (its own personal-stance
question is orthogonal and stays exactly as calibrated) and adds a new,
independently-testable decision type rather than overloading an existing one —
the same "one new fact, one new call site" discipline this session's own
calibration tracks (B1/B2/B3) followed throughout.

### 2. Bounded, never arbitrary: a small, explicit, named registry

A law may move a **named subset** of parameters, each within a **declared range**,
never an arbitrary config write. Concretely, a new module-level registry —
structurally identical to `PressureCalibrationSignal`'s own "one declared,
documented, boring dataclass per legal option" shape:

```python
@dataclass(frozen=True)
class AmendableParameter:
    path: str        # e.g. "legitimacy.recall_floor" -- dotted, matches config's own shape
    min_value: float
    max_value: float
    step: float       # the largest single amendment can move it, one ratification at a time
```

Candidates named in the plan (`recall_floor`, `petition.signature_threshold`, the
pressure menu's own thresholds) are a starting set, not a final one — the
registry's own existence is the decision here, not its exact membership, which is
an implementation-time question against whichever parameters are actually stable
and load-bearing by the time this is built.

**Why bounded and why a step limit, specifically**: arbitrary config mutation
would make every invariant in the engine conditional on "which law is active,"
which this project's own review discipline (`Citizen`/`PolityConfig` frozen
dataclasses, `PolityConfigError` at parse time, `validate_*_decision` at every
decision boundary) has consistently refused to accept elsewhere. A `step` bound
additionally prevents a single ratified law from jumping a parameter outside the
range every *other* calibration in this codebase (B1's `mandate_dev` ceiling, B2's
distance reference, A1's `recall_floor` interaction with a won confidence vote)
was measured and tuned against — an amendment should evolve the ruleset, not
invalidate every prior finding about it in one vote.

**Structurally, this is an overlay, not a mutation of `PolityConfig` itself.**
Every config dataclass in this domain is `@dataclass(frozen=True)` on purpose (a
run's ruleset is not supposed to move under a reader's feet); making the amendable
fields mutable would be a far larger, more invasive change than the law system
itself and would weaken that guarantee for every OTHER caller of those same
fields, amendable or not. Instead: a small `ActiveLaws` object — `dict[str, float]`
from `AmendableParameter.path` to its current (possibly amended) value, defaulting
to empty — travels alongside `PolityConfig` (a sibling in the tick loop's own
state, same register as `pending_rerun`/`economy_x`/`staggered_declared_cids`,
checkpointed the same way) and is what any dt=10/dt=6/etc. call site actually
reads for an amendable value, falling back to the frozen config's own value when
no law has touched that path yet. The frozen config stays the true constitutional
floor; `ActiveLaws` is the ratified deltas on top of it, and the two are never
conflated in a checkpoint or a journal event.

### 3. Comparability is the hard part, and it is solved on paper, not deferred to code

If the rules change at tick N, a metric computed over the whole run silently
straddles two different measurements — exactly the trap `office_occupancy`'s own
Track A work took care to name rather than paper over (a boundary imprecision,
documented rather than silently rounded). Three commitments, all needed together:

1. **The journal records the rule version in force at every ratification, not
   just the fact that one happened.** A new event type, `law_ratified`, carries
   `{parameter, old_value, new_value, law_version}` — `law_version` a simple
   monotonic counter (0 = the constitutional baseline, incremented once per
   ratified amendment), analogous to `PendingRerun.attempt`'s own "the journal
   should be able to answer 'which attempt was this' without re-deriving it from
   context."
2. **`digest.json` segments every relevant series by `law_version`, not just by
   tick.** `event_counts_by_year`/`population_impact_by_year`/`legitimacy_
   trajectory` (`run_digest.py`) all currently assume the ruleset is constant
   across the whole run; each needs a `law_version` column (or an equivalent
   segmentation) so a reader can tell "this dip in legitimacy started right after
   amendment 3" from "this is what the whole run's baseline dynamics look like."
   This is additive to `run_digest.py`'s existing shape, not a rewrite of it —
   the same "derived view, one source of truth" rule this module's own docstring
   already states for `viz_export.py`'s reuse of `segment_terms`.
3. **Every cross-run comparison must refuse to average across an amendment.**
   Concretely: any script or harness that aggregates a metric across ticks or
   across seeds (`scripts/llm_test_harness/`, the eventual Track D sweep) must
   either (a) restrict its own comparison window to a single `law_version`, or
   (b) explicitly flag when it does not, the same way `viz_export.export_
   metadata`'s `unverified_decision_types` flags a metric this project does not
   yet trust — a silently-blended average across a rule change is a strictly
   worse failure mode than an unverified decision type, because nothing about the
   number itself looks wrong.

**What this ADR does NOT settle, on purpose**: the exact ratification threshold
(simple majority of the chamber? a supermajority, mirroring `coalition_majority_
ratio`?), whether a law can be repealed or only amended forward, and whether
`law_version` resets or persists across a `snap_election_on_recall`/blank-vote
rerun cycle. These are real modelling judgments that deserve their own
pre-registered reasoning at implementation time, the same discipline B3's
ambition-feedback question got this session — not decided here as a byproduct of
settling the seam.

## When to build

**The plan's own precondition for building this — "Track B is the prerequisite,
not a detour" — is only partially satisfied, and that matters for timing, not
just for the record.** The three symptoms the plan named as making a law system
"noise wearing the costume of emergence" have not all resolved the way the plan's
own text anticipated when it deferred this work:

| symptom named as the blocker | status as of this ADR |
|---|---|
| the presidency is empty half the run | **Fixed** (Track A: `support(t)`, same-tick veto, snap election — verified live) |
| `representative_response` concedes 19/19 | **Partially fixed** (Track B1: a real zero/nonzero distinction at the zero-pressure pole, not a validated gradient above it) |
| `coalition_decision` is an unverified collapse | **Still unresolved** (Track B2's calibration attempt failed cleanly; the collapse itself is unchanged) |

`chamber_deliberation` itself — the actual seam this ADR proposes to extend —
was never established as broken either way (Track B4 deferred it for a cost
re-measurement reason, `think=True`'s own budget, not because a collapse was
found), so the seam's own foundation is not itself in question. But
`coalition_decision` staying broken is directly relevant: coalition formation is
the OTHER assembly-level collective decision this engine has, and if the chamber
can ratify laws while the assembly's own coalition behavior is still an
unverified collapse, a reader comparing "how do collective bodies in this
simulator actually deliberate" would be comparing one real mechanism against one
that still is not.

**Recommendation, not a rule**: build this after a second, more targeted attempt
at `coalition_decision` (per that track's own "what remains untested" note — a
stricter population reference, or a probe that isolates whether
`distance_to_initiator` is weighed at all) either succeeds or is retired as
genuinely unfixable, whichever comes first — not blocked indefinitely on it, but
not started while it is merely unexamined since the last attempt.

## Consequences

- No code changes ship with this ADR. `AmendableParameter`, `ActiveLaws`,
  `law_proposal`, and `law_ratified` are all named here for the first time and do
  not exist in the domain package yet.
- The next concrete step, when this is picked up, is a pre-registered
  Group-C-style criterion for `law_proposal` itself (this project's own B6 note:
  "Group C types have no deterministic proxy, so the pre-registered criterion
  must be invented per type") — before any prompt is written, not after.
- `run_digest.py`'s `law_version` segmentation and the harness's refuse-to-average
  rule are both a real, if modest, amount of work on their own, independent of
  the decision type itself — they should be scoped and estimated at
  implementation time rather than assumed free because "it's just a groupby."
