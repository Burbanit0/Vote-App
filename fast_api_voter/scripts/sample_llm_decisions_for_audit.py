"""
scripts/sample_llm_decisions_for_audit.py

Design doc §11, point 3 ("audit d'echantillon des decisions LLM") --
Points ouverts #1... #3: "frequence et taille de l'audit d'echantillon."
Full scoping in plan-rupture-candidacy-threshold.md's sibling document,
plan-llm-decision-audit-sampling.md.

**What this is not**: an automated plausibility checker. Nothing else in
this codebase has the LLM (or any heuristic) judge the LLM's own output --
every existing check (ACCEPTABLE_MATCH in codebook.py,
ResponseDecision._check_stance_coherence in llm_schemas.py) is mechanical,
comparing already-computed values. Building an automated judge here would
itself be exactly the kind of prescriptive theoretical criterion design
doc §3.3 rules out for the citizens/parties themselves. This script only
samples and renders; the plausibility judgment stays human.

**What "LLM decision" means here**: an event whose `motif` field is set.
Several event_types (pressure_action, in particular) are written by BOTH
the deterministic baseline and the LLM path depending on config -- only
the LLM path ever sets `motif` (see run_polity_simulation.py's own
`motif: str | None = None` default, only overwritten in the LLM branch).
Filtering on event_type alone would wrongly include deterministic-sourced
events in a mixed or LLM-disabled run; filtering on a truthy `motif` is
what's actually being asked for regardless of which event_types happen to
carry it in a given run.

**Sample size**: 30 per event_type present (or all of them, if fewer than
30 exist for that type) -- see plan-llm-decision-audit-sampling.md §5 for
the reasoning (this project's own established live-spike scale, not a
statistical power calculation; this is a qualitative spot-check, not a
hypothesis test). Stratified by event_type so a high-volume type
(vote_cast) cannot crowd a rare one (coalition_decision) out of the
sample.

**No raw reasoning to sample**: only the final structured decision (motif
+ payload) is ever journaled for a successful call -- see the plan doc's
§2 for why (llm.rationale_mode's free_text/hybrid modes are shipped but
unimplemented, NotImplementedError in llm_behavior_engine.py). This
audits coherence (motif + decision fields), not the model's reasoning
text, which does not exist in durable form to audit.

Usage:
    python fast_api_voter/scripts/sample_llm_decisions_for_audit.py \\
        path/to/run/events.jsonl --seed 0 --output audit_sample.md
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.codebook import motif_labels  # noqa: E402
from api.domain.polity.indexer import read_journal  # noqa: E402

DEFAULT_SAMPLE_SIZE = 30


def sample_for_audit(
    journal_path: Path, seed: int, sample_size: int = DEFAULT_SAMPLE_SIZE
) -> dict[str, list[dict]]:
    """Reads `journal_path`, groups every event with a truthy `motif` by
    `event_type`, and draws a stratified sample of up to `sample_size` per
    type. Reproducible: the same (journal_path, seed, sample_size) always
    returns the same sample, since read_journal's own iteration order and
    dict insertion order are both stable."""
    by_type: dict[str, list[dict]] = defaultdict(list)
    for event in read_journal(journal_path):
        if event.get("motif"):
            by_type[event["event_type"]].append(event)

    rng = np.random.default_rng(seed)
    sample: dict[str, list[dict]] = {}
    for event_type in sorted(by_type):
        pool = by_type[event_type]
        n = min(sample_size, len(pool))
        # sorted(): keep sampled events in journal order within a type,
        # rather than in the RNG's own draw order -- easier to cross-
        # reference against the raw journal during review.
        chosen_indices = sorted(rng.choice(len(pool), size=n, replace=False).tolist())
        sample[event_type] = [pool[i] for i in chosen_indices]
    return sample


def render_markdown(sample: dict[str, list[dict]], run_label: str) -> str:
    labels = motif_labels()
    total = sum(len(events) for events in sample.values())
    lines = [f"# LLM decision audit sample — {run_label}", "", f"{total} decisions sampled.", ""]
    for event_type, events in sample.items():
        lines.append(f"## {event_type} ({len(events)} sampled)")
        lines.append("")
        for event in events:
            motif_code = int(event["motif"])
            # Soft fallback, not a raise: this is a best-effort read tool for
            # human review, not a validator -- check_codebook_version already
            # gates a real run's own codebook mismatch at start-up, and each
            # event carries its own codebook_version for a reviewer to check.
            motif_name = labels.get(motif_code, "UNKNOWN")
            lines.append(
                f"- tick={event['tick']} citizen_id={event.get('citizen_id')} "
                f"motif={motif_code} ({motif_name}) codebook_version={event.get('codebook_version') or '?'}"
            )
            lines.append(f"  payload: {json.dumps(event['payload'], sort_keys=True)}")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("journal", type=Path, help="path to a run's events.jsonl")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--sample-size", type=int, default=DEFAULT_SAMPLE_SIZE)
    parser.add_argument("--output", type=Path, default=None, help="write markdown here instead of stdout")
    args = parser.parse_args()

    sample = sample_for_audit(args.journal, args.seed, args.sample_size)
    markdown = render_markdown(sample, run_label=args.journal.parent.name)
    if args.output is not None:
        args.output.write_text(markdown, encoding="utf-8")
        total = sum(len(events) for events in sample.values())
        print(f"wrote {total} sampled decisions across {len(sample)} decision types to {args.output}")
    else:
        print(markdown)
    return 0


if __name__ == "__main__":
    sys.exit(main())
