"""
api.domain.polity.viz_export — post-run UI-ready artifacts (Phase 6,
plan-flagship-30y-run.md, design doc §14).

Strictly post-run (§16.1's "cold regime"), unlike `snapshots.py` (in-run) --
this module never runs during the simulation, only after `run_simulation`
has closed the journal. Reuses `index_run`/`RunMetrics` rather than
recomputing metrics (this project's own standing rule, §16.2: "les métriques
du §10 deviennent des vues dérivées, pas une seconde source de vérité à
maintenir" -- the same reasoning `compaction.py` already applies to
`citizen_events`), and reads `events.jsonl` once, directly, for the
institutional timeline -- no new metric formula lives here, only reshaping.

Three of §14's four data families are covered here; the fourth already
exists elsewhere and is deliberately NOT duplicated:

- **Macro** (§14.3): `export_macro`, a faithful passthrough of every
  `RunMetrics` field -- the plan's own worked list ("legitimacy, effective
  parties, blank-vote rate, mandate deviation, stance distribution, chamber
  deviation") is illustrative, not exhaustive; `RunMetrics` itself is the
  authoritative "what this run measured", so nothing here re-derives a
  narrower view of it.
- **Institutional** (§14.4): `export_institutional`, a flat tick-ordered
  timeline filtered from the raw journal (elections, coalitions, petitions,
  recalls, scandals/economic shocks) -- a projection of existing fields,
  not a new computation.
- **Micro/méso** (§14.1/2): the yearly snapshots already exist as their own
  artifact (`snapshots.py`, Phase 6's in-run half, `snapshots.jsonl` beside
  `events.jsonl`) -- not re-exported here. The one piece that has never been
  persisted anywhere is the social graph itself; `export_social_graph`
  regenerates it (never reads it from a checkpoint -- `checkpoint.py`'s own
  module docstring: the graph is a pure function of `(config,
  population_size, seed)` with zero mid-run mutation, so regenerating it
  post-run is exact, not an approximation) and reshapes it into a plain
  node/edge list a UI can render directly.
- **Biography** (§16.7): per-citizen event stream -- already queryable from
  `compaction.py`'s own `citizen_events_decoded` DuckDB view
  (`compact_run`'s own worked example: "tous les événements du citoyen
  #4172"). Nothing to add here; a UI queries the `.duckdb` file directly.

**Carrying Phase 1's `unverified` labels through**: `representative_response`
and `coalition_decision` still show the content-blind collapse signature
under vLLM/AWQ (`scripts/check_vllm_collapse_signatures_results.md`) --
`reaction_to_event`'s SCANDAL branch was re-tested and cleared, and is
deliberately NOT included below. Every exported `RunMetrics` field this
project's own indexer.py docstring traces back to one of those two decision
types is named in `export_metadata`'s own `unverified_fields`, so a UI (or a
person reading the export directly) has an explicit, documented basis for
which numbers to present as findings and which to flag -- not a silent
inference, and not applied when `llm.enabled` is False (a deterministic run
has no such concern at all: `deterministic_pressure_action`/`simple_rules.py`
never collapses, having no learned distribution to collapse in the first
place)."""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from api.domain.polity.config import PolityConfig
from api.domain.polity.indexer import RunMetrics, index_run, read_journal
from api.domain.polity.social_graph import generate_social_graph

DEFAULT_EXPORT_FILENAME = "viz_export.json"

_INSTITUTIONAL_EVENT_TYPES = frozenset({
    "elected",
    "election_no_winner",
    "election_invalidated",
    "snap_election_triggered",
    "legislative_result",
    "coalition_formed",
    "coalition_failed",
    "petition_launched",
    "petition_expired",
    "confidence_vote_triggered",
    "confidence_vote_result",
    "recalled",
    "scandal_occurred",
    "economic_shock_tick",
})
"""Every election/coalition/petition/recall/scandal event_type this project's
codebase actually journals (grepped from run_polity_simulation.py's own
journal.write call sites -- not assumed from the design doc's prose list).
`economic_shock_tick` is included alongside `scandal_occurred`: both are v5's
exogenous-events family, journaled by the same phase, and the plan's own
"scandals" wording does not imply excluding the other half of that family.
`snap_election_triggered` (Track A3, 2026-09-11) joins the election family
alongside `election_invalidated` -- both are "the calendar just got
suspended" events, journaled from the exact same tick-loop position."""

# Phase 1 (plan-flagship-30y-run.md): re-tested under vLLM, still collapse.
#
# `representative_response` got a partial fix 2026-09-11 (Track B1, lets-
# build-a-solid-spicy-otter.md, scripts/check_response_calibration_
# results.md) -- build_response_system_prompt_calibrated states mandate_
# dev/street's own scales, and stance is no longer flat: P(stance=1) drops
# to 0.12 at the genuine zero-pressure point. STILL LISTED HERE, on
# purpose: that result is a real zero/nonzero distinction, not a validated
# gradient -- every interpolated point ABOVE zero pressure still reads
# P(stance=1)~=1.0, so mandate_deviation's own distribution above that one
# point remains exactly as unverified as before the fix. Remove from this
# tuple only once a probe establishes real sensitivity to the MAGNITUDE of
# pressure once pressure exists, not merely to its presence.
#
# `coalition_decision`'s own C3 calibration attempt FAILED, same day (Track
# B2, scripts/check_coalition_calibration_results.md): stating the mean
# pairwise inter-party distance produced no improvement on the same 5-point
# probe (pole-to-pole -0.0004 vs baseline -0.0026, full spread 0.047 vs
# 0.035 -- both negligible, same shape). Not shipped. Unlike representative_
# response, C3 does not explain this collapse -- see that results doc's own
# two unresolved readings before assuming why.
_UNVERIFIED_DECISION_TYPES = ("representative_response", "coalition_decision")

# Maps a RunMetrics field name to the decision type indexer.py's own
# docstring says it is actually computed from -- e.g. mandate_deviation's
# uncensored series is "representative_response.payload.ctx.mandate_dev,
# journaled every presided tick". Only fields with a traceable, documented
# source are listed; a field this project has not explicitly traced to one
# of the two unverified decision types is not guessed at here.
_METRICS_DERIVED_FROM_UNVERIFIED_DECISIONS: Mapping[str, str] = {
    "mandate_deviation": "representative_response",
    "mandate_deviation_unified": "representative_response",
    "lame_duck_deviation_delta": "representative_response",
    "cohabitation_rate": "coalition_decision",
    "coalition_lifespans": "coalition_decision",
}


def export_macro(metrics: RunMetrics) -> dict[str, Any]:
    """§14.3 -- every `RunMetrics` field, faithfully. A field that is `None`
    (its governing config flag is off) stays `None` here too -- this
    project's own "0.0 is a claim, None says this run does not track that"
    rule (indexer.py's own docstring), carried through rather than silently
    defaulted to an empty series a UI might mistake for "tracked, always
    zero". `chamber_deviation`'s length is `seats x presided_ticks`, NOT
    `ticks`, like every other series here -- indexer.py's own documented
    trap, repeated here rather than silently reshaped, since reshaping it
    would be a new computation this module deliberately does not do."""
    return dataclasses.asdict(metrics)


def export_institutional(events: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """§14.4 -- a flat, tick-ordered timeline. A thin projection of the
    journal's own fields (already tick-ordered by construction: D8's own
    "order is guaranteed by call order" rule), not a new computation --
    nothing here can drift from what the journal itself records."""
    timeline = []
    for event in events:
        if event["event_type"] in _INSTITUTIONAL_EVENT_TYPES:
            timeline.append({
                "tick": event["tick"],
                "event_type": event["event_type"],
                "citizen_id": event.get("citizen_id"),
                "motif": event.get("motif"),
                "payload": event["payload"],
            })
    return timeline


def export_social_graph(config: PolityConfig) -> dict[str, Any] | None:
    """§14.1/2's own graph component. `None` when `social_graph.enabled` is
    off, matching every other "flag off -> None" field in this export.
    Deduplicated into an undirected edge list -- `SocialGraph.neighbors` is
    symmetric by construction (every generator networkx.*_graph produces is
    undirected), so a naive per-node dump would list every edge twice."""
    if not config.social_graph.enabled:
        return None
    graph = generate_social_graph(config.social_graph, config.run.population_size, config.run.seed)
    edges = sorted({tuple(sorted((cid, neighbor))) for cid, neighbors in graph.neighbors.items() for neighbor in neighbors})
    return {
        "nodes": sorted(graph.neighbors.keys()),
        "edges": [list(edge) for edge in edges],
    }


def export_metadata(config: PolityConfig) -> dict[str, Any]:
    """The Phase-1-unverified-labels carry-through -- see this module's own
    docstring. Empty (not merely absent-keyed) when `llm.enabled` is False:
    the collapse finding is an LLM-path-specific one, so a deterministic run
    has nothing to flag."""
    if not config.llm.enabled:
        return {"unverified_decision_types": [], "unverified_fields": {}}
    return {
        "unverified_decision_types": list(_UNVERIFIED_DECISION_TYPES),
        "unverified_fields": dict(_METRICS_DERIVED_FROM_UNVERIFIED_DECISIONS),
    }


def export_run(journal_path: Path, config: PolityConfig, *, output_path: Path | None = None) -> Path:
    """Orchestrates the whole post-run export. `snapshots.jsonl` (Phase 6's
    in-run half) and the per-citizen biography (already queryable from
    `compact_run`'s own DuckDB view) are deliberately NOT duplicated into
    this file -- both already exist as their own artifacts beside
    `events.jsonl`; a UI reads those directly rather than through a second
    copy this module would have to keep in sync."""
    metrics = index_run(journal_path, config)
    events = list(read_journal(journal_path))

    payload = {
        "run_id": metrics.run_id,
        "macro": export_macro(metrics),
        "institutional": export_institutional(events),
        "social_graph": export_social_graph(config),
        "metadata": export_metadata(config),
    }
    output_path = output_path or journal_path.with_name(DEFAULT_EXPORT_FILENAME)
    output_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return output_path
