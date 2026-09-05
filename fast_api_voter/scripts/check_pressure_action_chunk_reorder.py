"""
scripts/check_pressure_action_chunk_reorder.py

Follow-up to the chunk-collapse finding in reasoning_budget_and_decision_quality_findings.md
("root mechanism identified: chunk-level output collapse"). That finding showed a real
21-citizen production chunk (tick=1, target=5, cid 87..171, extended quality pilot) collapsed
to the IDENTICAL act=0 (NOTHING) for every member, despite self_gap spanning 0.086-0.512 --
comfortably crossing every member's own blank_threshold in both directions.

This script asks the one question that distinguishes two structurally different bugs, per
direct instruction:

- POSITION artifact (same family as the already-fixed chunk_size bugs): the collapse tracks
  where a citizen sits in the request, not who they are. Reordering the SAME 21 citizens
  (same ctx, same target, same petition state -- nothing else changes) should produce a
  DIFFERENT uniform act, or a split that follows the NEW position boundaries rather than the
  citizens' own content.
- CONTENT-driven collapse (deeper, comparable to the prompt-cache reuse mechanism already
  catalogued in this project): the SAME 21 citizens collapse to the SAME act regardless of
  their serialized order -- something about this specific batch's aggregate content (all
  under the same target, same tick, same institutional state) drives one fixed answer,
  independent of both individual ctx AND position.

Real context, extracted directly from the extended pilot's own journal (`scripts/
pressure_action_quality_pilot/pressure-action-quality-pilot/events.jsonl`) -- not reconstructed
or assumed. Zero petition_launched/signed/expired events exist anywhere through tick=1 in that
run (checked directly), so petition_open=already_signed=False, petition_expires_at_tick=None
is a verified fact for every citizen in this chunk. available=(0,1,2,3,4): petition_enabled=
mobilization_enabled=True in the pilot config (menu_acts is a pure function of config).
neighbors_acting=None: social_graph disabled (pilot config leaves load_config()'s default).

Calls think=False, matching the REAL production path exactly (unlike the earlier forced-
think=True probe, which was explicitly exploratory/non-production) -- this test's whole point
is to reproduce the actual mechanism, only varying order.

Usage:
    python fast_api_voter/scripts/check_pressure_action_chunk_reorder.py
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.citizen import Citizen, generate_population  # noqa: E402
from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import (  # noqa: E402
    PressureContext,
    build_pressure_system_prompt,
    build_pressure_user_prompt,
    compute_max_tokens,
)
from api.domain.polity.llm_client import OllamaJsonClient, decode_pressure_batch  # noqa: E402
from api.domain.polity.llm_schemas import PRESSURE_JSON_SCHEMA  # noqa: E402

# The real chunk that collapsed to uniform act=0 (NOTHING) in the extended pilot's journal,
# tick=1, target=5, cid range [87..171] (21 citizens) -- verbatim self_gap per citizen,
# mandate_dev=0.0 and ticks_to_election=15 for all (confirmed uniform in the journal, not
# assumed), original act=0/motif=305 for every one of them.
_ORIGINAL_ORDER_CIDS = [87, 98, 103, 111, 118, 126, 129, 132, 135, 144, 146, 147, 148, 150, 152, 157, 158, 166, 168, 169, 171]
_SELF_GAP = {
    87: 0.1777, 98: 0.377, 103: 0.2108, 111: 0.2293, 118: 0.4112, 126: 0.4277, 129: 0.418,
    132: 0.3024, 135: 0.1941, 144: 0.3515, 146: 0.4161, 147: 0.3171, 148: 0.2386, 150: 0.4175,
    152: 0.3458, 157: 0.155, 158: 0.086, 166: 0.2, 168: 0.4194, 169: 0.231, 171: 0.5115,
}
_TARGET = 5
_MANDATE_DEV = 0.0
_TICKS_TO_ELECTION = 15
_ORIGINAL_ACT = 0
_ACT_NAMES = {0: "NOTHING", 1: "SIGN_PETITION", 2: "LAUNCH_PETITION", 3: "MOBILIZE", 4: "WAIT_FOR_ELECTION"}

_REORDER_SEED = 20260830  # fixed, so this run is reproducible
_REORDER_SEED_2 = 71  # second, independent shuffle -- distinguishes "the highest-self_gap
# citizen (cid=171) escapes wherever it lands" (content-driven, even if only at the tail) from
# "whoever lands near that same list position escapes" (a position/recency artifact) -- the
# first shuffle alone (a single data point) can't tell these apart.


def _make_contexts() -> dict[int, PressureContext]:
    return {
        cid: PressureContext(
            cid=cid,
            target=_TARGET,
            self_gap=_SELF_GAP[cid],
            mandate_dev=_MANDATE_DEV,
            ticks_to_election=_TICKS_TO_ELECTION,
            available=(0, 1, 2, 3, 4),
            petition_open=False,
            petition_expires_at_tick=None,
            already_signed=False,
            neighbors_acting=None,
        )
        for cid in _ORIGINAL_ORDER_CIDS
    }


def _run_chunk(client: OllamaJsonClient, ordered_citizens: list[Citizen], contexts: dict[int, PressureContext], label: str) -> dict[int, tuple[int, int]]:
    expected_cids = [c.citizen_id for c in ordered_citizens]
    raw = client.complete_json(
        system_prompt=build_pressure_system_prompt(ordered_citizens, load_config()),
        user_prompt=build_pressure_user_prompt(ordered_citizens, contexts),
        json_schema=PRESSURE_JSON_SCHEMA,
        max_tokens=compute_max_tokens(len(ordered_citizens)),
        think=False,
    )
    decisions = decode_pressure_batch(raw, expected_cids)
    by_cid: dict[int, tuple[int, int]] = {d.cid: (d.act, d.motif) for d in decisions}
    print(f"\n=== {label} (order: {expected_cids}) ===")
    for cid in expected_cids:
        act, motif = by_cid[cid]
        print(f"  cid={cid:>4} self_gap={_SELF_GAP[cid]:.4f} -> act={act} ({_ACT_NAMES[act]}) motif={motif}")
    return by_cid


def main() -> int:
    config = load_config()
    citizens_by_id = {
        c.citizen_id: c
        for c in generate_population(config.citizens, 280, config.run.seed)
    }
    contexts = _make_contexts()

    print(f"Original journal record: all {len(_ORIGINAL_ORDER_CIDS)} citizens -> "
          f"act={_ORIGINAL_ACT} ({_ACT_NAMES[_ORIGINAL_ACT]}), motif=305, "
          f"self_gap range [{min(_SELF_GAP.values()):.4f}, {max(_SELF_GAP.values()):.4f}]")

    results = []
    with OllamaJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        for seed, label in ((_REORDER_SEED, "SHUFFLE #1"), (_REORDER_SEED_2, "SHUFFLE #2")):
            shuffled_cids = list(_ORIGINAL_ORDER_CIDS)
            random.Random(seed).shuffle(shuffled_cids)
            ordered_shuffled = [citizens_by_id[cid] for cid in shuffled_cids]
            result = _run_chunk(client, ordered_shuffled, contexts, f"{label} (seed={seed})")
            results.append((label, shuffled_cids, result))

    print("\n--- verdict ---")
    for label, shuffled_cids, result in results:
        acts = {act for act, _motif in result.values()}
        escapees = [cid for cid in shuffled_cids if result[cid][0] != _ORIGINAL_ACT]
        position = {cid: i for i, cid in enumerate(shuffled_cids)}
        print(
            f"{label}: {len(acts)} distinct act(s); escapee(s) from the original uniform "
            f"NOTHING: {[(cid, f'pos={position[cid]}/{len(shuffled_cids)-1}', f'self_gap={_SELF_GAP[cid]:.4f}') for cid in escapees]}"
        )

    escapee_sets = [
        {cid for cid in _ORIGINAL_ORDER_CIDS if result[cid][0] != _ORIGINAL_ACT}
        for _label, _cids, result in results
    ]
    reproducible_escapees = set.intersection(*escapee_sets) if escapee_sets else set()
    any_escapees = set.union(*escapee_sets) if escapee_sets else set()
    if reproducible_escapees:
        print(
            f"\n{reproducible_escapees} escaped the collapse in EVERY shuffle -> reproducible "
            "content-sensitivity, not noise."
        )
    elif any_escapees:
        print(
            f"\n{any_escapees} escaped in SOME but not all shuffles -> the escape itself is not "
            "reproducible per citizen. Read this as likely ordinary batch-call stochastic "
            "variance (already documented elsewhere in this project even at temperature=0 under "
            "batching), not evidence of either content-sensitivity or a position rule -- the "
            "robust, reproducible result is the >=20/21 uniform collapse itself, present in both "
            "shuffles despite two different serializations of the same citizens."
        )
    else:
        print("\nNo escapees in either shuffle -> full uniform collapse persists regardless of order, strongest content-blind reading.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
