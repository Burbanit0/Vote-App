"""
scripts/check_pressure_action_chunk_generality.py

Third follow-up to the chunk-collapse finding (reasoning_budget_and_decision_quality_findings.md).
The size-sensitivity test (check_pressure_action_chunk_size_sensitivity.py) found that shrinking
one specific 21-citizen chunk (originally uniform act=0/NOTHING at size 21) to sub-batches of 3
broke the uniform-collapse pattern, but replaced it with a DIFFERENT degenerate pattern: not one
of the 21 decisions picked an acting code (SIGN/LAUNCH/MOBILIZE) -- every output was NOTHING or
WAIT_FOR_ELECTION. That chunk happens to be atypical: 3 of its 4 unambiguous citizens (per the
pilot's own gap/blank_threshold proxy) call for ACT.

Open question, per direct instruction, sequenced BEFORE testing intermediate sizes (testing a
full size curve on an unconfirmed single-chunk artifact would risk describing nothing real):
does "avoids acting codes at size=3" generalize to OTHER chunks with a different action/no-action
mix, or is it specific to that one chunk's atypical composition?

Tests two other real chunks from the SAME tick=1/target=5 batch, both ORIGINALLY uniform
act=3/MOBILIZE at their production size (21-24, "chunk 1" cid 6..84 and "chunk 3" cid 172..279 --
the two chunks that bookended the collapsed-to-NOTHING chunk already tested), each with a
different action/no-action proxy mix than the first chunk tested:
  - chunk1 (cid 6..84): 4 expect ACT, 4 expect NOTHING, 13 ambiguous -- BALANCED, unlike the
    first chunk's 3-ACT/1-NOTHING skew.
  - chunk3 (cid 172..279): 6 expect ACT, 3 expect NOTHING, 12 ambiguous -- ACT-leaning, but a
    different ratio (2:1) than the first chunk's (3:1), and originally collapsed the OPPOSITE
    direction (uniform MOBILIZE, not uniform NOTHING).

If BOTH still avoid acting codes at size=3 despite starting from a uniform-MOBILIZE baseline at
size 21+, that argues for a general "small pressure_action batches avoid acting codes" effect,
independent of chunk composition or which direction the larger batch collapsed. If either shows
real acting-code decisions, the first chunk's result was chunk-specific, not general.

Same real ctx discipline as the prior two follow-ups: target=5, mandate_dev=0.0,
ticks_to_election=15, petition_open=already_signed=False/petition_expires_at_tick=None (verified
zero petition lifecycle events through tick=1 in this run), available=(0,1,2,3,4),
neighbors_acting=None, think=False (the real production path). Same ascending-citizen_id order
(chunk boundaries in the ORIGINAL journal are already this order; only size changes here, order
was already tested separately in check_pressure_action_chunk_reorder.py).

Usage:
    python fast_api_voter/scripts/check_pressure_action_chunk_generality.py
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

_TARGET = 5
_MANDATE_DEV = 0.0
_TICKS_TO_ELECTION = 15
_ACTING_CODES = {1, 2, 3}
_ACT_NAMES = {0: "NOTHING", 1: "SIGN_PETITION", 2: "LAUNCH_PETITION", 3: "MOBILIZE", 4: "WAIT_FOR_ELECTION"}
_SUB_BATCH_SIZE = 3

# Both chunks originally uniform act=3 (MOBILIZE) in production at size 21-24 (tick=1, target=5) --
# the opposite polarity from the chunk already tested (which was uniform act=0/NOTHING).
_CHUNKS: dict[str, dict[int, float]] = {
    "chunk1 (cid 6..84, originally uniform MOBILIZE, balanced 4-ACT/4-NOTHING proxy mix)": {
        6: 0.2802, 7: 0.2578, 10: 0.3683, 29: 0.2767, 32: 0.2966, 36: 0.3914, 40: 0.1883,
        47: 0.3524, 50: 0.2742, 52: 0.3332, 53: 0.2756, 55: 0.3627, 59: 0.3644, 60: 0.38,
        66: 0.3269, 67: 0.3116, 69: 0.1447, 70: 0.1569, 71: 0.17, 82: 0.4308, 84: 0.3721,
    },
    "chunk3 (cid 172..279, originally uniform MOBILIZE, 6-ACT/3-NOTHING proxy mix)": {
        172: 0.4452, 175: 0.3253, 176: 0.2168, 191: 0.3511, 203: 0.1907, 206: 0.2627,
        212: 0.3498, 214: 0.2624, 218: 0.2829, 228: 0.3224, 235: 0.3919, 238: 0.2347,
        240: 0.3677, 247: 0.2899, 249: 0.4164, 257: 0.1802, 261: 0.2494, 265: 0.3544,
        270: 0.4825, 276: 0.3098, 279: 0.3986,
    },
}
_BLANK_THRESHOLD: dict[int, float] = {
    6: 0.0663, 7: 0.6127, 10: 0.4701, 29: 0.4168, 32: 0.2783, 36: 0.4705, 40: 0.5822,
    47: 0.4214, 50: 0.3955, 52: 0.2083, 53: 0.5815, 55: 0.4065, 59: 0.4278, 60: 0.5372,
    66: 0.3807, 67: 0.428, 69: 0.3555, 70: 0.2064, 71: 0.1, 82: 0.2666, 84: 0.3401,
    172: 0.2778, 175: 0.1386, 176: 0.5028, 191: 0.3591, 203: 0.2493, 206: 0.4629,
    212: 0.3623, 214: 0.4494, 218: 0.7352, 228: 0.4388, 235: 0.2571, 238: 0.3542,
    240: 0.3817, 247: 0.4186, 249: 0.352, 257: 0.6098, 261: 0.2493, 265: 0.1712,
    270: 0.1871, 276: 0.1712, 279: 0.4347,
}


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


def main() -> int:
    config = load_config()
    citizens_by_id = {c.citizen_id: c for c in generate_population(config.citizens, 280, config.run.seed)}

    overall_acting_seen = False
    with OllamaJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        for chunk_label, self_gaps in _CHUNKS.items():
            cids = list(self_gaps.keys())
            print(f"\n########## {chunk_label} ##########")
            sub_batches = [cids[i:i + _SUB_BATCH_SIZE] for i in range(0, len(cids), _SUB_BATCH_SIZE)]
            all_results: dict[int, tuple[int, int]] = {}
            for batch_cids in sub_batches:
                ordered_citizens = [citizens_by_id[cid] for cid in batch_cids]
                contexts = {cid: _make_context(cid, self_gaps[cid]) for cid in batch_cids}
                raw = client.complete_json(
                    system_prompt=build_pressure_system_prompt(ordered_citizens, config),
                    user_prompt=build_pressure_user_prompt(ordered_citizens, contexts),
                    json_schema=PRESSURE_JSON_SCHEMA,
                    max_tokens=compute_max_tokens(len(ordered_citizens)),
                    think=False,
                )
                decisions = decode_pressure_batch(raw, batch_cids)
                by_cid: dict[int, tuple[int, int]] = {d.cid: (d.act, d.motif) for d in decisions}
                all_results.update(by_cid)
                for cid in batch_cids:
                    act, motif = by_cid[cid]
                    ratio = self_gaps[cid] / _BLANK_THRESHOLD[cid]
                    print(f"  cid={cid:>4} self_gap={self_gaps[cid]:.4f} ratio={ratio:.3f} -> act={act} ({_ACT_NAMES[act]}) motif={motif}")

            acting = [cid for cid in cids if all_results[cid][0] in _ACTING_CODES]
            overall_acting_seen = overall_acting_seen or bool(acting)
            correct, checked = 0, 0
            for cid in cids:
                expected = _expected_act(cid, self_gaps[cid])
                if expected is None:
                    continue
                checked += 1
                actual = all_results[cid][0] in _ACTING_CODES
                correct += actual == expected
            print(f"\n  acting-code decisions (1/2/3) chosen: {len(acting)}/{len(cids)} {acting}")
            if checked:
                print(f"  unambiguous accuracy: {correct}/{checked} ({correct/checked:.1%})")

    print("\n--- verdict ---")
    if overall_acting_seen:
        print(
            "At least one acting code (SIGN/LAUNCH/MOBILIZE) appeared in at least one of these "
            "two chunks at size=3 -> the total avoidance seen on the first chunk tested does NOT "
            "generalize cleanly; it looks chunk-composition-dependent, not a fixed property of "
            "small pressure_action batches."
        )
    else:
        print(
            "ZERO acting codes across both chunks at size=3, despite both chunks originally "
            "collapsing to uniform MOBILIZE at size 21+ in production -> the acting-code "
            "avoidance generalizes beyond the first chunk tested, independent of chunk "
            "composition or which direction the larger batch collapsed. This looks like a "
            "general property of small pressure_action batches under think=False, not an "
            "artifact of one atypical chunk."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
