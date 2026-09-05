"""
scripts/check_pressure_action_chunk_size_curve.py

Fourth follow-up to the chunk-collapse finding (reasoning_budget_and_decision_quality_findings.md).
Two degenerate modes are now confirmed for pressure_action's batched think=False path on the same
3 real 21-citizen chunks (tick=1, target=5, extended quality pilot journal):
  - size=21-24 (production): uniform collapse -- every citizen in the chunk gets the identical
    act, ignoring individual self_gap.
  - size=3: avoids acting codes entirely (SIGN/LAUNCH/MOBILIZE never chosen) across all 3 chunks,
    63 citizens, regardless of chunk composition or original collapse polarity -- confirmed
    general, not a single-chunk artifact (check_pressure_action_chunk_generality.py).

This tests intermediate sizes (5, 10) on the SAME 3 chunks, using chunk_voters -- the actual
production chunking function -- so the sub-batch boundaries at each size match what a real run
with a smaller config.llm.max_batch_size would produce, not an ad hoc split. Question: do
intermediate sizes sit between the two failure modes (a gradual transition), flip sharply at some
threshold, or show a third, distinct pattern neither size 3 nor size 21+ produced?

Same real ctx per citizen (target=5, mandate_dev=0.0, ticks_to_election=15, petition_open=
already_signed=False/petition_expires_at_tick=None -- verified zero petition lifecycle events
through tick=1 in this run, available=(0,1,2,3,4), neighbors_acting=None), same ascending-
citizen_id order per chunk (order was already tested separately), think=False (production path).

Usage:
    python fast_api_voter/scripts/check_pressure_action_chunk_size_curve.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.citizen import Citizen, generate_population  # noqa: E402
from api.domain.polity.config import PolityConfig, load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import (  # noqa: E402
    PressureContext,
    build_pressure_system_prompt,
    build_pressure_user_prompt,
    chunk_voters,
    compute_max_tokens,
)
from api.domain.polity.llm_client import OllamaJsonClient, decode_pressure_batch  # noqa: E402
from api.domain.polity.llm_schemas import PRESSURE_JSON_SCHEMA  # noqa: E402

_TARGET = 5
_MANDATE_DEV = 0.0
_TICKS_TO_ELECTION = 15
_ACTING_CODES = {1, 2, 3}
_ACT_NAMES = {0: "NOTHING", 1: "SIGN_PETITION", 2: "LAUNCH_PETITION", 3: "MOBILIZE", 4: "WAIT_FOR_ELECTION"}

_CHUNKS: dict[str, dict[int, float]] = {
    "chunk2 (cid 87..171, originally uniform NOTHING)": {
        87: 0.1777, 98: 0.377, 103: 0.2108, 111: 0.2293, 118: 0.4112, 126: 0.4277, 129: 0.418,
        132: 0.3024, 135: 0.1941, 144: 0.3515, 146: 0.4161, 147: 0.3171, 148: 0.2386, 150: 0.4175,
        152: 0.3458, 157: 0.155, 158: 0.086, 166: 0.2, 168: 0.4194, 169: 0.231, 171: 0.5115,
    },
    "chunk1 (cid 6..84, originally uniform MOBILIZE)": {
        6: 0.2802, 7: 0.2578, 10: 0.3683, 29: 0.2767, 32: 0.2966, 36: 0.3914, 40: 0.1883,
        47: 0.3524, 50: 0.2742, 52: 0.3332, 53: 0.2756, 55: 0.3627, 59: 0.3644, 60: 0.38,
        66: 0.3269, 67: 0.3116, 69: 0.1447, 70: 0.1569, 71: 0.17, 82: 0.4308, 84: 0.3721,
    },
    "chunk3 (cid 172..279, originally uniform MOBILIZE)": {
        172: 0.4452, 175: 0.3253, 176: 0.2168, 191: 0.3511, 203: 0.1907, 206: 0.2627,
        212: 0.3498, 214: 0.2624, 218: 0.2829, 228: 0.3224, 235: 0.3919, 238: 0.2347,
        240: 0.3677, 247: 0.2899, 249: 0.4164, 257: 0.1802, 261: 0.2494, 265: 0.3544,
        270: 0.4825, 276: 0.3098, 279: 0.3986,
    },
}
_BLANK_THRESHOLD: dict[int, float] = {
    87: 0.0778, 98: 0.5864, 103: 0.2283, 111: 0.2285, 118: 0.5114, 126: 0.2921, 129: 0.2924,
    132: 0.2374, 135: 0.2769, 144: 0.4897, 146: 0.1736, 147: 0.3594, 148: 0.1763, 150: 0.7213,
    152: 0.1064, 157: 0.1899, 158: 0.487, 166: 0.3514, 168: 0.3837, 169: 0.2972, 171: 0.4036,
    6: 0.0663, 7: 0.6127, 10: 0.4701, 29: 0.4168, 32: 0.2783, 36: 0.4705, 40: 0.5822,
    47: 0.4214, 50: 0.3955, 52: 0.2083, 53: 0.5815, 55: 0.4065, 59: 0.4278, 60: 0.5372,
    66: 0.3807, 67: 0.428, 69: 0.3555, 70: 0.2064, 71: 0.1, 82: 0.2666, 84: 0.3401,
    172: 0.2778, 175: 0.1386, 176: 0.5028, 191: 0.3591, 203: 0.2493, 206: 0.4629,
    212: 0.3623, 214: 0.4494, 218: 0.7352, 228: 0.4388, 235: 0.2571, 238: 0.3542,
    240: 0.3817, 247: 0.4186, 249: 0.352, 257: 0.6098, 261: 0.2493, 265: 0.1712,
    270: 0.1871, 276: 0.1712, 279: 0.4347,
}

_SIZES = (5, 10)


def _expected_act(cid: int, self_gap: float) -> bool | None:
    ratio = self_gap / _BLANK_THRESHOLD[cid]
    if ratio < 0.5:
        return False
    if ratio > 1.5:
        return True
    return None


def _make_context(cid: int, self_gap: float) -> PressureContext:
    return PressureContext(
        cid=cid, target=_TARGET, self_gap=self_gap, mandate_dev=_MANDATE_DEV,
        ticks_to_election=_TICKS_TO_ELECTION, available=(0, 1, 2, 3, 4),
        petition_open=False, petition_expires_at_tick=None, already_signed=False,
        neighbors_acting=None,
    )


def _run_size(
    client: OllamaJsonClient,
    config: PolityConfig,
    citizens_by_id: dict[int, Citizen],
    self_gaps: dict[int, float],
    max_batch_size: int,
) -> dict[int, tuple[int, int]]:
    cids = list(self_gaps.keys())
    ordered_citizens = [citizens_by_id[cid] for cid in cids]
    all_results: dict[int, tuple[int, int]] = {}
    for chunk in chunk_voters(ordered_citizens, max_batch_size, min_batch_size=1):
        chunk_cids = [c.citizen_id for c in chunk]
        contexts = {cid: _make_context(cid, self_gaps[cid]) for cid in chunk_cids}
        raw = client.complete_json(
            system_prompt=build_pressure_system_prompt(chunk, config),
            user_prompt=build_pressure_user_prompt(chunk, contexts),
            json_schema=PRESSURE_JSON_SCHEMA,
            max_tokens=compute_max_tokens(len(chunk)),
            think=False,
        )
        decisions = decode_pressure_batch(raw, chunk_cids)
        all_results.update({d.cid: (d.act, d.motif) for d in decisions})
    return all_results


def main() -> int:
    config = load_config()
    citizens_by_id = {c.citizen_id: c for c in generate_population(config.citizens, 280, config.run.seed)}

    summary = []
    with OllamaJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        for chunk_label, self_gaps in _CHUNKS.items():
            for size in _SIZES:
                print(f"\n########## {chunk_label} @ max_batch_size={size} ##########")
                results = _run_size(client, config, citizens_by_id, self_gaps, size)
                acting = [cid for cid in self_gaps if results[cid][0] in _ACTING_CODES]
                correct, checked = 0, 0
                for cid, gap in self_gaps.items():
                    expected = _expected_act(cid, gap)
                    if expected is None:
                        continue
                    checked += 1
                    actual = results[cid][0] in _ACTING_CODES
                    correct += actual == expected
                    ratio = gap / _BLANK_THRESHOLD[cid]
                    act, motif = results[cid]
                    print(
                        f"  cid={cid:>4} ratio={ratio:.3f} expected_act={expected} -> "
                        f"act={act} ({_ACT_NAMES[act]}) motif={motif} "
                        f"{'AGREE' if actual == expected else 'DISAGREE'}"
                    )
                acc = f"{correct}/{checked} ({correct/checked:.1%})" if checked else "n/a"
                print(f"  acting codes chosen: {len(acting)}/21 | unambiguous accuracy: {acc}")
                summary.append((chunk_label, size, len(acting), correct, checked))

    print("\n--- summary across the whole size curve (3, 5, 10, 21+) ---")
    print("size=3 (prior test):  0/21 acting codes on all 3 chunks (63/63 citizens)")
    for chunk_label, size, acting_n, correct, checked in summary:
        acc = f"{correct}/{checked}" if checked else "n/a"
        print(f"{chunk_label} @ size={size}: acting_codes={acting_n}/21, unambiguous_accuracy={acc}")
    print("size=21-24 (production, prior finding): uniform collapse, one act for the whole chunk")
    return 0


if __name__ == "__main__":
    sys.exit(main())
