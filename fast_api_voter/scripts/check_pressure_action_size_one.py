"""
scripts/check_pressure_action_size_one.py

Fifth follow-up to the chunk-collapse finding (reasoning_budget_and_decision_quality_findings.md).
The size curve tested so far (3, 5, 10, 21-25) never included size=1 -- the one size that
actually fixed cast_votes's own collapse (_VOTE_CAST_MAX_CHUNK_SIZE reduced 3->1). Size=1 is
qualitatively different from 3/5/10, not another point on the same curve: zero cross-citizen
interaction is possible in a single-citizen call, so it is the one test that can separate two
otherwise indistinguishable hypotheses:

- If size=1 STILL avoids acting codes (never SIGN/LAUNCH/MOBILIZE, even for an isolated citizen
  with no other citizen in the call) -> batching/cross-citizen interaction is eliminated as a
  cause entirely; the problem lives in the prompt/schema itself, independent of batch size.
- If size=1 RESTORES real acting-code decisions -> the problem is specifically about batching
  (same family as cast_votes), and the think=True-forced mechanism probe becomes the priority to
  understand the interaction, not prompt/schema redesign.

Runs all 63 citizens from the 3 chunks already characterized (tick=1, target=5, extended quality
pilot journal) as 63 independent single-citizen calls -- same real ctx per citizen, same
petition/target/menu facts, think=False (the real production path). Per direct instruction, if
this restores acting codes, the bar for "success" stays the SAME as every other probe in this
project: does the isolated citizen's decision track the deterministic proxy's act-vs-no-act
prediction (not which specific lever -- that stays the palier's own free-choice question, per
plan-decision-quality-validation.md's own pre-registered criterion) -- not merely "produced
something other than NOTHING/WAIT_FOR_ELECTION". Also watches for a NEW degenerate pattern this
size hasn't been checked for yet: acting-code decisions collapsing to always the SAME specific
code (e.g. always SIGN_PETITION) regardless of citizen, which would just be a different-flavored
collapse rather than real content-tracking.

Usage:
    python fast_api_voter/scripts/check_pressure_action_size_one.py
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

_SELF_GAP: dict[int, float] = {
    # chunk2 (cid 87..171, originally uniform NOTHING at size 21+)
    87: 0.1777, 98: 0.377, 103: 0.2108, 111: 0.2293, 118: 0.4112, 126: 0.4277, 129: 0.418,
    132: 0.3024, 135: 0.1941, 144: 0.3515, 146: 0.4161, 147: 0.3171, 148: 0.2386, 150: 0.4175,
    152: 0.3458, 157: 0.155, 158: 0.086, 166: 0.2, 168: 0.4194, 169: 0.231, 171: 0.5115,
    # chunk1 (cid 6..84, originally uniform MOBILIZE at size 21+)
    6: 0.2802, 7: 0.2578, 10: 0.3683, 29: 0.2767, 32: 0.2966, 36: 0.3914, 40: 0.1883,
    47: 0.3524, 50: 0.2742, 52: 0.3332, 53: 0.2756, 55: 0.3627, 59: 0.3644, 60: 0.38,
    66: 0.3269, 67: 0.3116, 69: 0.1447, 70: 0.1569, 71: 0.17, 82: 0.4308, 84: 0.3721,
    # chunk3 (cid 172..279, originally uniform MOBILIZE at size 21+)
    172: 0.4452, 175: 0.3253, 176: 0.2168, 191: 0.3511, 203: 0.1907, 206: 0.2627,
    212: 0.3498, 214: 0.2624, 218: 0.2829, 228: 0.3224, 235: 0.3919, 238: 0.2347,
    240: 0.3677, 247: 0.2899, 249: 0.4164, 257: 0.1802, 261: 0.2494, 265: 0.3544,
    270: 0.4825, 276: 0.3098, 279: 0.3986,
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


def _expected_act(cid: int) -> bool | None:
    ratio = _SELF_GAP[cid] / _BLANK_THRESHOLD[cid]
    if ratio < 0.5:
        return False
    if ratio > 1.5:
        return True
    return None


def main() -> int:
    config = load_config()
    citizens_by_id = {c.citizen_id: c for c in generate_population(config.citizens, 280, config.run.seed)}
    cids = sorted(_SELF_GAP.keys())

    results: dict[int, tuple[int, int]] = {}
    with OllamaJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        for cid in cids:
            citizen = citizens_by_id[cid]
            ctx = PressureContext(
                cid=cid, target=_TARGET, self_gap=_SELF_GAP[cid], mandate_dev=_MANDATE_DEV,
                ticks_to_election=_TICKS_TO_ELECTION, available=(0, 1, 2, 3, 4),
                petition_open=False, petition_expires_at_tick=None, already_signed=False,
                neighbors_acting=None,
            )
            raw = client.complete_json(
                system_prompt=build_pressure_system_prompt([citizen], config),
                user_prompt=build_pressure_user_prompt([citizen], {cid: ctx}),
                json_schema=PRESSURE_JSON_SCHEMA,
                max_tokens=compute_max_tokens(1),
                think=False,
            )
            decision = decode_pressure_batch(raw, [cid])[0]
            results[cid] = (decision.act, decision.motif)
            ratio = _SELF_GAP[cid] / _BLANK_THRESHOLD[cid]
            expected = _expected_act(cid)
            actual = decision.act in _ACTING_CODES
            tag = "" if expected is None else (" AGREE" if actual == expected else " DISAGREE")
            print(
                f"cid={cid:>4} ratio={ratio:.3f} expected_act={expected} -> "
                f"act={decision.act} ({_ACT_NAMES[decision.act]}) motif={decision.motif}{tag}"
            )

    acting = [cid for cid in cids if results[cid][0] in _ACTING_CODES]
    acting_code_counts: dict[int, int] = {}
    for cid in acting:
        acting_code_counts[results[cid][0]] = acting_code_counts.get(results[cid][0], 0) + 1

    correct, checked = 0, 0
    for cid in cids:
        expected = _expected_act(cid)
        if expected is None:
            continue
        checked += 1
        correct += (results[cid][0] in _ACTING_CODES) == expected

    print(f"\n--- summary (n={len(cids)}, single-citizen calls, size=1) ---")
    print(f"acting codes chosen: {len(acting)}/{len(cids)} ({len(acting)/len(cids):.1%})")
    print(f"acting-code breakdown: { {_ACT_NAMES[k]: v for k, v in acting_code_counts.items()} }")
    if checked:
        print(f"unambiguous act-vs-no-act accuracy: {correct}/{checked} ({correct/checked:.1%})")

    print("\n--- verdict ---")
    if not acting:
        print(
            "ZERO acting codes even at size=1, fully isolated citizens -> batching/cross-citizen "
            "interaction is eliminated as a cause. The avoidance of SIGN/LAUNCH/MOBILIZE lives in "
            "the prompt/schema itself, independent of batch size entirely."
        )
    elif checked and correct / checked >= 0.9:
        print(
            f"Acting codes restored AND unambiguous accuracy ({correct}/{checked}) meets the "
            "pre-registered >=90% bar -> size=1 looks like a genuine fix, same family as "
            "cast_votes. Same success bar as every other probe in this project, not just "
            "'left the degenerate mode'."
        )
    else:
        print(
            f"Acting codes appeared ({len(acting)}/{len(cids)}) but unambiguous accuracy "
            f"({correct}/{checked if checked else 0}) does not meet the >=90% bar -> size=1 "
            "breaks the total-avoidance pattern but does not, on this evidence, restore correct "
            "content-tracking. Batching is not the sole cause; check the acting-code breakdown "
            "above for a new default-code collapse."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
