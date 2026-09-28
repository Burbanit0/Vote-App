# ADR-015: a typed constitution — amendable articles, laid over the founding config

**Status**: Accepted — the kernel is built in Phase 2.1 of `docs/plan/polity/plan-polity-agency-roadmap.md`.
Scripted amendments (2.1) and the amendment procedure, an agent's proposal and the chamber's vote
(2.2 and 2.3), are built. This ADR supersedes ADR-008 §2 (the `AmendableParameter` registry and the `ActiveLaws` overlay).
**Date**: 2026-09-28
**Context**: the agency roadmap's decision D2 (a typed constitution) and the user's goal of seeing
the voting system itself change.

## Context

A run's rules were one frozen `PolityConfig`, fixed for the whole run. ADR-008 designed an
amendment seam: a registry of amendable parameters, and an `ActiveLaws` overlay that every call
site would read, falling back to the config. That design needs every reader of an amendable value
to learn about laws.

It does not have to. Every tick phase reads its rules from one place, `TickContext.config`, and
`TickContext` is rebuilt every tick.

## Decision

- **Articles are config paths with a domain.** `config.ARTICLES` names each amendable rule and the
  values it may take: a list (the voting method among the 13 ranked methods, a term limit of 1–3
  or none, a seat-allocation rule) or a numeric range (the electoral threshold, the assembly's
  seats, the petition threshold, the recall floor).
  - The registry lives in `config.py` because it describes the config, and so that `config.py` and
    `constitution.py` need no cycle.
  - Only rules read at an election, a rotation or a tick's accountability are articles. An
    amendment then takes effect the next time the rule is read, and no calendar moves. A term
    length would need the institutional clock re-anchored and waits for a use.
- **The rules in force are the founding config with each amendment laid over it.**
  - `constitution.in_force(founding, constitution)` rebuilds them with `dataclasses.replace`.
  - The tick loop builds each tick's `TickContext.config` from it. Every phase therefore reads the
    rules in force, and no reader changes.
  - The founding config, its checkpoint hash and `config.json` never move.
- **State is small; history is the journal.**
  - `TickState.constitution` holds a version and the amended values. It is `None` until the first
    amendment, so a run that never amends checkpoints exactly as before.
  - Each amendment is a `constitution_amended` event carrying the article, old value, new value,
    version and source. It is institutional, so it shows on the explorer's timeline.
- **Amendments come first in the tick** (`_phase_constitution`), so the whole tick runs under
  them. Several on one tick apply in the order given.
- **Scripted amendments** (`constitution.scripted: [{tick, article, value}]`) are a run's own
  experiment: "two-round for ten years, then Borda".
  - When the config loads, each one is checked against its article's domain.
  - `validate_config` checks the cross-setting rules again after each amendment in turn, so a run
    cannot amend itself into a config the rules refuse.
  - They are also the kernel's smoke test.

## The amendment procedure (roadmap 2.2 and 2.3)

Switched on by `agents.amendments`, which needs the president agent and the sortition chamber.

- **The president proposes.** Their turn may carry one `amendment` (article, value, reason).
  - Two things are checked with the turn, so a bad one is retried like any invalid turn: the
    article exists and allows the value (`validate_amendment`), and the rules still hold with it.
  - One proposal is pending at a time. One made while another is pending, or before any chamber has
    been drawn, is dropped: the briefing says so. The briefing also shows the constitution in force
    and the threshold each article needs.
- **The chamber votes the next tick,** at the start of it (`_resolve_amendment`, after the scripted
  amendments). Each member takes a turn of their own (`decide_ballot`, decision type
  `amendment_vote`), in parallel, and none sees another's vote. It carries a statement and a
  `note_to_self` like any agent turn, so members remember how they voted.
- **Ratified when strictly more than the threshold of all members voted yes.** A member whose every
  attempt failed votes `none` and counts against. The rules are checked once more before it applies.
  Ratification is a `constitution_amended` event with source `vote`, after an `amendment_resolved`
  event with the tally. A rejected proposal is dropped, and the president may propose again.
- **The threshold is an article.** `constitution.amendment_threshold` (0.5 to 0.9) is amendable like
  the rest, and `constitution.entrenched` names articles that need more (the amendment threshold
  itself, and the voting method, by default). The threshold of a proposal is fixed when it is
  proposed and stored with it, so a proposal to lower the threshold is voted under the old one.
- **The pending proposal is state.** It lives in `Constitution.pending`, is checkpointed with it,
  and is cleared by `amend` and by `close_proposal`. A resume across it is byte-identical.
- **The values an agent writes are JSON** (`"two_round"`, `null`, `0.5`), as the prompts show them.

## What this ADR does not settle

- Chamber members proposing amendments: left out until the president-only proposals show that the
  chamber never initiates.
- Averaging across versions: the digest's yearly rows say which constitution each year ended under
  (roadmap 2.4), but the statistics still average over a run that amended itself. The "refuse to
  average" rule waits for the first ensemble that spans amendments.
- Score and approval ballots, which would let the cardinal methods be articles, and the term
  length.

## Consequences

- A run's `config.json` shows the founding rules. What was in force at a tick is the founding
  config plus the `constitution_amended` events up to it.
- Tested:
  - article domains;
  - the refusal of every malformed scripted amendment;
  - the rules re-checked after each amendment;
  - a run that amends its voting method and term limit, then resumes byte-identical across both
    amendments;
  - a Hypothesis property: any legal constitution, applied at tick 0, passes `validate_config`
    and runs.
