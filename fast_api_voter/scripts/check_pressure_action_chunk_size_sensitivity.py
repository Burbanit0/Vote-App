"""
scripts/check_pressure_action_chunk_size_sensitivity.py

Second follow-up to the chunk-collapse finding (reasoning_budget_and_decision_quality_findings.md).
The order-permutation test (check_pressure_action_chunk_reorder.py) ruled out a simple position/
boundary artifact: reordering the same 21-citizen collapsed chunk still collapsed, twice.

This asks the other half of the question the pre-registered framing set up: is the collapse
SIZE-dependent -- the same family as cast_votes's own already-fixed collapse
(reasoning_budget_and_decision_quality_findings.md's own earlier section: near-uniform
permutation collapse at LARGER batch sizes, resolved by reducing _VOTE_CAST_MAX_CHUNK_SIZE 3->1)
-- or does it persist even at sizes this project has already measured clean for this exact
schema shape (lot6_batch_reliability_results.md: 1/3/5/10 clean through the native think=False
path)?

Takes the SAME 21 citizens, SAME real ctx, SAME ascending-citizen_id order (so this test isolates
size alone -- order was already tested separately) as the collapsed chunk (tick=1, target=5,
cid 87..171, extended quality pilot), and re-issues them as 7 sub-batches of 3 (a size this
project has direct clean-batch evidence for). If per-citizen content-sensitivity returns at this
size, the collapse is a batch-size artifact -- reparable the same way cast_votes was. If
sub-batches still collapse internally (all 3 citizens in a sub-batch get the same act despite
differing self_gap), size reduction alone does not fix it.

Ground-truth check: 4 of these 21 citizens are UNAMBIGUOUS per the pilot's own pre-registered
criterion (gap/blank_threshold ratio outside [0.5, 1.5]) -- cid=87 (ratio=2.28, expect ACT),
cid=146 (ratio=2.40, expect ACT), cid=152 (ratio=3.25, expect ACT), cid=158 (ratio=0.18, expect
NOTHING). Small N, but a real accuracy signal alongside the within-subbatch variation check.

Usage:
    python fast_api_voter/scripts/check_pressure_action_chunk_size_sensitivity.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.citizen import generate_population  # noqa: E402
from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import (  # noqa: E402
    PressureContext,
    build_pressure_system_prompt,
    build_pressure_user_prompt,
    compute_max_tokens,
)
from api.domain.polity.llm_client import OllamaJsonClient, decode_pressure_batch  # noqa: E402
from api.domain.polity.llm_schemas import PRESSURE_JSON_SCHEMA  # noqa: E402

# Same 21 citizens, same order as the journal (ascending citizen_id -- the ORIGINAL production
# order, unlike the reorder test), split into 7 consecutive sub-batches of 3.
_ORIGINAL_ORDER_CIDS = [87, 98, 103, 111, 118, 126, 129, 132, 135, 144, 146, 147, 148, 150, 152, 157, 158, 166, 168, 169, 171]
_SELF_GAP = {
    87: 0.1777, 98: 0.377, 103: 0.2108, 111: 0.2293, 118: 0.4112, 126: 0.4277, 129: 0.418,
    132: 0.3024, 135: 0.1941, 144: 0.3515, 146: 0.4161, 147: 0.3171, 148: 0.2386, 150: 0.4175,
    152: 0.3458, 157: 0.155, 158: 0.086, 166: 0.2, 168: 0.4194, 169: 0.231, 171: 0.5115,
}
_BLANK_THRESHOLD = {
    87: 0.0778, 98: 0.5864, 103: 0.2283, 111: 0.2285, 118: 0.5114, 126: 0.2921, 129: 0.2924,
    132: 0.2374, 135: 0.2769, 144: 0.4897, 146: 0.1736, 147: 0.3594, 148: 0.1763, 150: 0.7213,
    152: 0.1064, 157: 0.1899, 158: 0.487, 166: 0.3514, 168: 0.3837, 169: 0.2972, 171: 0.4036,
}
_TARGET = 5
_MANDATE_DEV = 0.0
_TICKS_TO_ELECTION = 15
_ACTING_CODES = {1, 2, 3}
_ACT_NAMES = {0: "NOTHING", 1: "SIGN_PETITION", 2: "LAUNCH_PETITION", 3: "MOBILIZE", 4: "WAIT_FOR_ELECTION"}
_SUB_BATCH_SIZE = 3


def _expected_act(cid: int) -> bool | None:
    ratio = _SELF_GAP[cid] / _BLANK_THRESHOLD[cid]
    if ratio < 0.5:
        return False
    if ratio > 1.5:
        return True
    return None  # ambiguous, excluded


def _make_context(cid: int) -> PressureContext:
    return PressureContext(
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


def main() -> int:
    config = load_config()
    citizens_by_id = {
        c.citizen_id: c
        for c in generate_population(config.citizens, 280, config.run.seed)
    }

    sub_batches = [
        _ORIGINAL_ORDER_CIDS[i:i + _SUB_BATCH_SIZE]
        for i in range(0, len(_ORIGINAL_ORDER_CIDS), _SUB_BATCH_SIZE)
    ]
    print("Original (size=21, single call): all -> act=0 (NOTHING) uniformly, per the journal.")
    print(f"Re-running as {len(sub_batches)} sub-batches of size {_SUB_BATCH_SIZE}, same order, same ctx.\n")

    all_results: dict[int, tuple[int, int]] = {}
    with OllamaJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        for batch_cids in sub_batches:
            ordered_citizens = [citizens_by_id[cid] for cid in batch_cids]
            contexts = {cid: _make_context(cid) for cid in batch_cids}
            raw = client.complete_json(
                system_prompt=build_pressure_system_prompt(ordered_citizens, config),
                user_prompt=build_pressure_user_prompt(ordered_citizens, contexts),
                json_schema=PRESSURE_JSON_SCHEMA,
                max_tokens=compute_max_tokens(len(ordered_citizens)),
                think=False,
            )
            decisions = decode_pressure_batch(raw, batch_cids)
            by_cid = {d.cid: (d.act, d.motif) for d in decisions}
            all_results.update(by_cid)
            acts_in_batch = {act for act, _m in by_cid.values()}
            uniform_flag = " <-- still uniform" if len(acts_in_batch) == 1 else ""
            print(f"sub-batch {batch_cids}:{uniform_flag}")
            for cid in batch_cids:
                act, motif = by_cid[cid]
                ratio = _SELF_GAP[cid] / _BLANK_THRESHOLD[cid]
                print(
                    f"  cid={cid:>4} self_gap={_SELF_GAP[cid]:.4f} blank_threshold={_BLANK_THRESHOLD[cid]:.4f} "
                    f"ratio={ratio:.3f} -> act={act} ({_ACT_NAMES[act]}) motif={motif}"
                )

    print("\n--- verdict ---")
    uniform_sub_batches = sum(
        1 for batch_cids in sub_batches
        if len({all_results[cid][0] for cid in batch_cids}) == 1
    )
    print(f"{uniform_sub_batches}/{len(sub_batches)} sub-batches are STILL internally uniform (all 3 citizens, same act).")

    correct, checked = 0, 0
    for cid in _ORIGINAL_ORDER_CIDS:
        expected = _expected_act(cid)
        if expected is None:
            continue
        checked += 1
        actual = all_results[cid][0] in _ACTING_CODES
        agree = actual == expected
        correct += agree
        print(
            f"unambiguous check: cid={cid} expected_act={expected} actual_act={actual} "
            f"({'AGREE' if agree else 'DISAGREE'})"
        )
    if checked:
        print(f"\nunambiguous accuracy at size={_SUB_BATCH_SIZE}: {correct}/{checked} ({correct/checked:.1%})")

    if uniform_sub_batches == 0:
        print(
            "\nNo sub-batch is internally uniform -> content-sensitivity RESTORED at "
            f"size={_SUB_BATCH_SIZE}. Supports a size-dependent, reparable collapse -- same "
            "family as cast_votes's own fix (reduce max_batch_size for this decision type)."
        )
    elif uniform_sub_batches == len(sub_batches):
        print(
            "\nEVERY sub-batch is still internally uniform, even at this small size -> the "
            "collapse persists below the size this project already validated clean for this "
            "schema shape. Does not fit the simple 'reduce chunk size' story -- something else "
            "is driving it."
        )
    else:
        print(
            f"\nMixed: {uniform_sub_batches}/{len(sub_batches)} sub-batches still collapsed "
            "internally, the rest show real variation -> partial size sensitivity, worth "
            "characterizing further before concluding either way."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
