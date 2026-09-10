"""
scripts/check_toon_candidacy_ab.py

plan-llm-protocol-and-theory-program.md §5.E, step 1bis's own mandated
starting point: "run it on candidacy_considered first, which has real
ground truth (simple_rules.decide_candidacy) AND no known collapse
defect, so a quality regression is attributable to the format rather
than confounded with an existing failure." pressure_action (the other
§5.E target) comes only after this, and only with §5.C's P(act) baseline
already captured -- see check_logprob_pressure_action_gap_tracking.py.

Two gates, not one, per §5.E's own Verification section:
(a) token count before/after via count_prompt_tokens (no estimation);
(b) a decision-quality A/B against real ground truth -- decide_candidacy
    is a pure ambition_score >= threshold comparison, so this is a real
    accuracy figure, not a collapse-signature-only reading.

Same 25 citizens, same production system-prompt/user-prompt SEMANTICS
(build_candidacy_system_prompt_toon differs from build_candidacy_system_
prompt ONLY in the added format-explanation paragraph, offline-tested),
same real CANDIDACY_JSON_SCHEMA output, same think=False (this decision
type's own production value) -- run once through each format, so any
difference in either metric is attributable to the format change alone.

Usage:
    docker compose -f fast_api_voter/docker-compose.llm.yml up -d
    python fast_api_voter/scripts/check_toon_candidacy_ab.py
"""
from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.citizen import Citizen  # noqa: E402
from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import (  # noqa: E402
    build_candidacy_system_prompt,
    build_candidacy_system_prompt_toon,
    build_candidacy_user_prompt,
    build_candidacy_user_prompt_toon,
    compute_max_tokens,
)
from api.domain.polity.llm_client import VllmJsonClient, decode_candidacy_batch  # noqa: E402
from api.domain.polity.llm_schemas import CANDIDACY_JSON_SCHEMA  # noqa: E402
from api.domain.polity.simple_rules import decide_candidacy  # noqa: E402

_POPULATION_SIZE = 25  # the shipped llm.max_batch_size -- one real, full-size chunk


def _make_citizen(cid: int, ambition_score: float) -> Citizen:
    return Citizen(
        citizen_id=cid,
        issue_positions=tuple((cid * 0.017 + d * 0.013) % 1.0 for d in range(20)),
        issue_priorities=tuple(1.0 / 20 for _ in range(20)),
        blank_threshold=0.5,
        ambition_score=ambition_score,
    )


def _vllm_config():
    shipped = load_config()
    return dataclasses.replace(shipped, llm=dataclasses.replace(shipped.llm, provider="vllm", base_url="http://localhost:8000/v1"))


def main() -> int:
    config = _vllm_config()
    threshold = config.candidacy.ambition_threshold

    # Ambition scores evenly span both sides of the real shipped threshold
    # (0.30) -- perceived_support varies too (irrelevant to the ground
    # truth, but part of the real prompt payload either format sends).
    citizens = [
        _make_citizen(i, ambition_score=round(0.05 + i * 0.9 / (_POPULATION_SIZE - 1), 4))
        for i in range(_POPULATION_SIZE)
    ]
    support = {c.citizen_id: round((c.citizen_id * 37 % 100) / 100, 4) for c in citizens}
    truth = {c.citizen_id: decide_candidacy(c, config.candidacy) for c in citizens}
    expected_cids = [c.citizen_id for c in citizens]

    print(f"candidacy TOON A/B: {len(citizens)} citizens, threshold={threshold}, "
          f"{sum(truth.values())} ground-truth declare / {len(citizens) - sum(truth.values())} decline")

    with VllmJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        results = {}
        for label, sys_prompt, user_prompt in [
            ("JSON", build_candidacy_system_prompt(citizens), build_candidacy_user_prompt(citizens, support)),
            ("TOON", build_candidacy_system_prompt_toon(citizens), build_candidacy_user_prompt_toon(citizens, support)),
        ]:
            prompt_tokens = client.count_prompt_tokens(system_prompt=sys_prompt, user_prompt=user_prompt, think=False)
            content = client.complete_json(
                system_prompt=sys_prompt, user_prompt=user_prompt,
                json_schema=CANDIDACY_JSON_SCHEMA, max_tokens=compute_max_tokens(len(citizens)), think=False,
            )
            try:
                decisions = decode_candidacy_batch(content, expected_cids)
                decode_ok = True
            except Exception as exc:  # noqa: BLE001 -- reporting, not re-raising
                decisions = []
                decode_ok = False
                print(f"  {label}: DECODE FAILED: {exc}")
            correct = sum(1 for d in decisions if bool(d.outcome) == truth[d.cid])
            results[label] = {
                "prompt_tokens": prompt_tokens,
                "decode_ok": decode_ok,
                "n_decisions": len(decisions),
                "correct": correct,
            }
            print(f"  {label}: prompt_tokens={prompt_tokens} decode_ok={decode_ok} "
                  f"decisions={len(decisions)}/{len(citizens)} correct={correct}/{len(citizens)}")

    if results["JSON"]["decode_ok"] and results["TOON"]["decode_ok"]:
        token_savings = results["JSON"]["prompt_tokens"] - results["TOON"]["prompt_tokens"]
        pct = 100 * token_savings / results["JSON"]["prompt_tokens"]
        print(f"\ntoken savings (JSON - TOON): {token_savings} ({pct:.1f}%)")
        print(f"accuracy: JSON {results['JSON']['correct']}/{len(citizens)} vs "
              f"TOON {results['TOON']['correct']}/{len(citizens)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
