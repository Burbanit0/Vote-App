# ADR-015: a typed constitution — amendable articles, laid over the founding config

**Status**: Accepted — the kernel is built in Phase 2.1 of `docs/plan/polity/plan-polity-agency-roadmap.md`.
Only scripted amendments exist so far; proposals and ratification come in 2.2 and 2.3. This ADR
supersedes ADR-008 §2 (the `AmendableParameter` registry and the `ActiveLaws` overlay).
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

## What this ADR does not settle

- Who proposes, who ratifies, and at what threshold: roadmap 2.2 and 2.3, where the amendment
  procedure itself becomes articles (entrenchment, the procedure in force at proposal time).
- Segmenting the digest and the statistics by constitution version (roadmap 2.4 and the
  "refuse to average" rule). Until then, a metric over a run that amended itself straddles two
  sets of rules; the journal says where.
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
