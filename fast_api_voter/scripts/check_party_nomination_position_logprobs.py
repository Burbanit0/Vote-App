"""
scripts/check_party_nomination_position_logprobs.py

Track C1 step E (lets-build-a-solid-spicy-otter.md, ~1 min GPU, ~80 throwaway lines):
Stage 3 (`scaleprobe-8y-p500-v2-postfix`) fell back on `party_nomination_choice` 10/15
times (67%). Party 3, tick 16, returned `winner_position=26` against only 19 declared
candidates -- six such answers total, all FIRST attempts at temperature 0 (the
validator sits outside `_complete_and_decode_with_replay`'s own replay loop, so the
already-shipped retry budget never got a chance to act on this failure class).

Two readings, and this probe is the one cheap test that tells them apart:
- If "2" is confident and the second digit lands near p=0.5 -- a decoding accident:
  the model picked the right first digit and the (unbounded, ungrammared) second digit
  is close to a coin flip. Only a grammar bound (D1: per-party enum) truly fixes it.
- If "26" itself is confident (both digits strongly preferred) -- a comprehension
  failure: the model is not confused about HOW to write the number, it computed the
  wrong one. Only restating the bound (C) or containing the damage (B, per-party
  fallback) help; a grammar bound alone would just force a different wrong answer.

EXACT reproduction, not an approximation: `ambition_score` (never mutated post-
generation) and `platform_distance` (computed from `issue_positions`, also never
mutated -- only `revealed_position`/`pledged_platform` are) together with `Party.
platform` (never mutated anywhere in this codebase) make every field this prompt
sends time-invariant across the whole run. Loading the run's own FINAL checkpoint
(`checkpoint.json`) therefore reconstructs the EXACT tick-16 prompt byte for byte --
not a fresh, drifted `generate_population` call. All 5 real contested parties are
replayed together (not just party 3 in isolation), matching the real batched call
`decide_party_nominations` actually made -- so `compute_max_tokens`, prompt shape and
schema are all identical to what actually ran.

Usage:
    docker compose -f fast_api_voter/docker-compose.llm.yml up -d
    python fast_api_voter/scripts/check_party_nomination_position_logprobs.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.checkpoint import load_checkpoint  # noqa: E402
from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import (  # noqa: E402
    build_party_nomination_system_prompt,
    build_party_nomination_user_prompt,
    compute_max_tokens,
    sorted_candidates,
)
from api.domain.polity.llm_client import VllmJsonClient, decode_party_nomination_batch  # noqa: E402
from api.domain.polity.llm_logprob_instrumentation import (  # noqa: E402
    LogprobAlignmentError,
    _find_field_value_spans,
    _locate_content_in_raw_text,
    _token_covering_offset,
    locate_decision_field_logprobs,
)
from api.domain.polity.llm_schemas import PARTY_NOMINATION_JSON_SCHEMA  # noqa: E402
from api.domain.polity.simple_rules import sympathizer_ratio  # noqa: E402


def _top_alternatives(alternatives: dict[str, float], n: int = 8) -> list[tuple[str, float]]:
    return sorted(alternatives.items(), key=lambda item: item[1], reverse=True)[:n]


def _second_digit_token(content: str, tokens, target_party_id: int):
    """locate_decision_field_logprobs applies ONE value_char_offset across
    the WHOLE batch and raises if ANY decision's own value is too short for
    it -- correct for its own documented use (every field this project has
    used it on so far has a uniform value length across a batch), but this
    batch does not: party 0 answered a single digit ("3") while party 3
    answered two ("26"). Reimplemented here, scoped to one party's own span,
    rather than widening the shared module for a one-off diagnostic need."""
    raw_text = "".join(token.token for token in tokens)
    base_offset = _locate_content_in_raw_text(raw_text, content)
    decisions = json.loads(content)["decisions"]
    spans = _find_field_value_spans(content, "winner_position")
    for decision, (start, end) in zip(decisions, spans):
        if decision["party_id"] != target_party_id:
            continue
        if start + 1 >= end:
            return None  # this decision's own value is single-digit
        return _token_covering_offset(tokens, base_offset + start + 1)
    raise LogprobAlignmentError(f"party_id {target_party_id} not found among decisions")

_CHECKPOINT_PATH = Path(__file__).resolve().parents[1] / (
    "scripts/flagship_runs/scaleprobe-8y-p500-v2-postfix/run/"
    "scaleprobe-8y-p500-v2-postfix/checkpoint.json"
)

# The exact 5 contested parties' declared-candidate cid lists, tick 16, read
# directly from this run's own events.jsonl (party_nomination_choice.payload.
# contenders) -- reproduced literally here rather than re-derived, since re-
# deriving "who declared" would depend on candidacy_considered's own LLM
# call, which is a separate, non-reproducible source of drift this probe does
# not need to touch.
_CONTENDERS_BY_PARTY = {
    0: [23, 40, 67, 84, 94, 99, 105, 115, 122, 143, 144, 148, 156, 176, 186, 194, 195, 199, 223, 228, 234, 235, 246, 278, 282, 285, 290, 308, 311, 368, 374, 384, 387, 392, 396, 404, 413, 414, 422, 426, 455, 461, 496],
    1: [11, 17, 24, 71, 76, 81, 87, 96, 112, 133, 134, 151, 164, 173, 183, 189, 226, 254, 255, 269, 299, 352, 359, 361, 376, 378, 382, 390, 398, 402, 408, 420, 447, 457, 458, 459, 466, 471, 472, 479],
    2: [3, 35, 121, 130, 131, 136, 137, 140, 178, 181, 197, 203, 217, 237, 264, 276, 283, 288, 307, 309, 315, 317, 379, 406, 416, 423, 460, 464, 468, 478, 483],
    3: [97, 132, 138, 146, 147, 198, 245, 253, 258, 271, 354, 380, 383, 389, 415, 440, 456, 462, 463],
    4: [13, 18, 19, 20, 37, 69, 78, 79, 86, 89, 90, 92, 108, 110, 111, 113, 123, 124, 127, 158, 160, 179, 180, 182, 187, 190, 205, 207, 209, 215, 222, 236, 238, 251, 252, 257, 260, 261, 263, 266, 280, 291, 297, 302, 304, 319, 322, 324, 345, 347, 355, 363, 367, 370, 372, 373, 385, 386, 388, 393, 405, 407, 411, 418, 419, 441, 444, 445, 452, 465, 474, 477, 488],
}

_TARGET_PARTY_ID = 3  # the one where the answer (26) was small enough to be detectably out of range


def main() -> int:
    config = load_config()
    checkpoint = load_checkpoint(_CHECKPOINT_PATH)
    citizens_by_id = {c.citizen_id: c for c in checkpoint.citizens}
    parties_by_id = {p.party_id: p for p in checkpoint.parties}

    contested = {
        party_id: [citizens_by_id[cid] for cid in cids]
        for party_id, cids in _CONTENDERS_BY_PARTY.items()
    }
    all_contenders = [c for members in contested.values() for c in members]
    support = {c.citizen_id: sympathizer_ratio(c, checkpoint.citizens) for c in all_contenders}

    system_prompt = build_party_nomination_system_prompt(contested)
    user_prompt = build_party_nomination_user_prompt(contested, parties_by_id, support)

    vllm_config = config.llm
    with VllmJsonClient.from_config(vllm_config, seed=config.run.seed) as client:
        content, tokens = client.complete_json_with_logprobs(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_schema=PARTY_NOMINATION_JSON_SCHEMA,
            max_tokens=compute_max_tokens(len(contested)),
            think=False,
            temperature=0.0,
            seed=config.run.seed,
        )

    expected_party_ids = list(contested.keys())
    decisions = decode_party_nomination_batch(content, expected_party_ids)
    by_party = {d.party_id: d for d in decisions}

    print(f"decoded winner_position per party: {[(p, d.winner_position) for p, d in sorted(by_party.items())]}")

    target = by_party[_TARGET_PARTY_ID]
    n_candidates = len(contested[_TARGET_PARTY_ID])
    print(
        f"\nparty {_TARGET_PARTY_ID}: winner_position={target.winner_position} against "
        f"{n_candidates} declared candidates ({'OUT OF RANGE' if not 1 <= target.winner_position <= n_candidates else 'in range'})"
    )

    value_str = str(target.winner_position)
    try:
        probes_first = locate_decision_field_logprobs(
            content, tokens, field="winner_position", cid_field="party_id", value_char_offset=0,
        )
        first_token = next(p.token for p in probes_first if p.cid == _TARGET_PARTY_ID)
        print(f"\nfirst digit token: {first_token.token!r} logprob={first_token.logprob:.4f}")
        print("  top alternatives:", _top_alternatives(first_token.alternatives))
    except LogprobAlignmentError as exc:
        print(f"\nfirst-digit probe failed: {exc}")

    if len(value_str) >= 2:
        try:
            second_token = _second_digit_token(content, tokens, _TARGET_PARTY_ID)
            if second_token is None:
                print("\nparty 3's own value turned out single-digit this call (non-determinism across runs).")
            else:
                print(f"\nsecond digit token: {second_token.token!r} logprob={second_token.logprob:.4f}")
                print("  top alternatives:", _top_alternatives(second_token.alternatives))
        except LogprobAlignmentError as exc:
            print(f"\nsecond-digit probe failed: {exc}")
    else:
        print(f"\nwinner_position={value_str} is single-digit this run -- no second digit to probe "
              f"(temperature=0/seed={config.run.seed} may not reproduce the exact original completion; "
              f"see the results doc for how this is read either way).")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
