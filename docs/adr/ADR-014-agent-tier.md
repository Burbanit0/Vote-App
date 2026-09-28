# ADR-014: the agent tier — citizens the model plays in the first person

**Status**: Accepted — built for the president in Phase 1.2 of `docs/plan/polity/plan-polity-agency-roadmap.md`.
It ships off (`agents.president: false`) and is on in `run_polity_flagship.py --profile exploration`.
**Date**: 2026-09-28
**Context**: the agency roadmap's decisions D3 (a tiered population), D4 (the exploration gate),
D8 (the leader's goal stays implicit) and D9 (English agent prompts).

## Context

Every LLM decision in polity was a batch classification. The engine sent a chunk of citizens as
numeric vectors to a prompt that opens "Tu es un moteur de simulation. Pour chaque citoyen reçu…",
and it received closed codes back. No citizen had a persona, a memory or words of their own, and
none proposed anything. Two of the nine decision types collapse: `coalition_decision` is flat on
three model families, and `representative_response` only partly responds (OBS-007). The protocol
programme's thesis is that every confirmed collapse is inter-individual.

The roadmap asks for leaders who try to stay popular, then citizens who argue, organise and test
the rules. None of that fits a batch classifier. Leaders come first because they are few: one
president, a handful of nominees.

## Decision

### An agent is a citizen, played in the first person, one call per turn

- **Who.** The sitting president, and (Phase 1.4, `agents.nominees`) each presidential nominee
  for their campaign turn. The agent set is derived from office and nomination, so there is no
  promotion state yet.
- **Persona.** A template rendered from the citizen's numbers (`agents.persona`). It carries a
  name, their party, their three top-priority issues, their ambition, and their view on every
  issue. There is no LLM-written biography, and the numbers stay the kernel's truth.
- **Named issues.** Agents argue about named issues. `agents.ISSUES` names the 20 issues with a
  pole at 0 and a pole at 1. The factor loadings stay random per seed, so a persona's views can
  combine in ways no real ideology would. This is a declared confound, not a bug to fix before
  it shows.
- **Memory is a view over the journal, not a store.** `Journal.tap` feeds `AgentMemory` each event
  as it is written:
  - the last 16 institutional and bill events are the public record;
  - an agent's own last 8 turns (moves, bill and note to self, not the speech) and legitimacy
    readings are their personal record. The speech is left out because the model echoed its past
    speeches word for word (OBS-028).

  On resume the memory is rebuilt in one pass over the already-truncated `events.jsonl`, so
  nothing new is checkpointed. There is no retrieval scoring and no reflection call yet; the
  agent's own `note_to_self` carries its continuity.
- **Prompt layout.** The system prompt holds the persona and the rules in force. Nothing in it
  changes from tick to tick, so it is a stable prefix for vLLM's prefix cache. The user prompt
  holds the tick's briefing and the memory. The briefing shows approval, legitimacy, street
  pressure, the gap from the pledge, whether the agenda is theirs, and per issue: the policy, the
  stated position, the pledge, the public median and the seat-weighted assembly median.
- **The goal stays implicit (D8).** The persona "wants to govern by [its] convictions and to keep
  office; how you weigh the two is yours to decide". The prompt states the rules and the numbers,
  and never what to do (contract C4). Whether presidents chase approval is a result to observe.
- **The answer is typed moves plus words** (`llm_schemas.LeaderTurn`):
  - `rationale` comes first, since field order is generation order;
  - `positions` names the position the president now takes on an issue, as a target value;
  - `bill` names the policy they want on an issue, the same way, when the agenda is theirs.

  Targets, not signed deltas. The first live runs had Qwen3-8B promise one pole while moving
  toward the other, and its own notes named target values. The kernel takes the bounded step
  toward each target (`steps_toward`) and journals it as a `{dimension, delta}` shift.
  In the same answer:
  - `speech` and `note_to_self` are the agent's words;
  - `other_initiative` records what the agent wanted that the rules do not offer, and is never
    applied. That field is the limit-testing log the later phases build from.
- **The kernel referees.**
  - `validate_turn` checks the issue counts (`mandate.max_response_shifts`,
    `legislation.max_bill_dimensions`), duplicates and issue numbers. The step bounds
    (`mandate.max_response_delta`, `legislation.max_bill_step`) cannot be broken, because the
    kernel takes the step. A bill offered while the agenda is closed is ignored rather than
    refused.
  - Validation runs inside the replay loop (#679), so a rejected answer is replayed with varied
    sampling.
  - When every attempt fails, the president stays silent and the formula drafts the bill: the
    world before agents.
  - Free text is cut to its limits, never refused.
- **Where the turn sits.** A `_phase_leaders` phase runs just before legislation.
  - It replaces `representative_response`, which the accountability phase now skips for an agent
    president. It reads the same one-tick-lagged street pressure (§7bis.7).
  - It replaces `_draft_bill` whenever the agenda is the president's. Under cohabitation the
    government still drafts by formula.
  - Mandate metrics survive: the indexer falls back to `mandate_deviation_recorded` when there
    are no response events, and the explorer's frames replay `agent_turn` shifts like responses.
- **Thinking.** The turn runs with thinking on, under the `llm.thinking_token_budget` cap from its
  first run (`THINKING_BUDGET_TYPES`), so it cannot run away the way positioning does (OBS-022).
- **Batching (§3.5) is reversed for agents.** One agent means one call. The server batches the
  concurrent calls, as vLLM does for every request.

### Records

- An `agent_turn` event carries the applied moves, the words and the usual LLM provenance. It
  holds a `codebook_version`, so `progress.json` counts it as a decision.
- `bill_proposed` gains `drafted_by: "agent"` when the agent chose the bill.
- A clamp at a position bound is journaled as for every other shift (`clamped_at_bound`).

## What this ADR does not settle

- Turn temperature, settled after this ADR (2026-09-28): `agents.turn_temperature`, 0 by default,
  0.6 in the exploration profile (Qwen3's thinking-mode value), because non-determinism is wanted.
  It did not stop the repetition that prompted it; OBS-028 traces that to the situation. The first attempt sends it with the seed base, so a
  single-worker run still regenerates; retries keep their own temperature and seeds.
- Nominee and party-leader turns and their promotion rules (roadmap 1.4, Phase 3 and Phase 4).
- LLM-written personas, scored memory retrieval, and reflection calls. Each has an "add when" line
  in the roadmap's §5.

## Consequences

- A president agent's run is not comparable with a formula-president run on anything the
  president decides. The exploration profile is where agents run; the flagship stays formula.
- Prompt versions become experimental variables (OBS-019). The prompts live in `agents.py`, and a
  change to them is a change to what runs measure.
- The deterministic twin cannot play an agent, so `--profile exploration --engine deterministic`
  keeps the formula president (`agents.president` requires `llm.enabled`).
