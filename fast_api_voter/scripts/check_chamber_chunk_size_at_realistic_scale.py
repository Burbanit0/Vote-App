"""
scripts/check_chamber_chunk_size_at_realistic_scale.py

Phase 7's smoke run came back 1.88x SLOWER than the pre-chunk-size baseline
(4257.6s vs 2266.8s). check_dynamic_budget_latency_regression.py already
ruled out the budget STRATEGY itself as the cause at chunk_size=1 (flat vs
dynamic showed no meaningful difference there). This isolates chunk SIZE
directly, at REALISTIC scale (75 members -- one real tick's worth of
sortition_chamber.seats, not the 1-8 member samples check_vllm_chunk_size_
throughput_results.md used), calling the real decide_chamber_deliberation
end to end (retry/fallback wiring included), same 75 members both times.

Usage:
    docker compose -f fast_api_voter/docker-compose.llm.yml up -d
    python fast_api_voter/scripts/check_chamber_chunk_size_at_realistic_scale.py
"""
from __future__ import annotations

import dataclasses
import sys
import time
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.citizen import Citizen  # noqa: E402
from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity import llm_behavior_engine as lbe  # noqa: E402
from api.domain.polity.llm_client import VllmJsonClient  # noqa: E402


def _vllm_config():
    shipped = load_config()
    return dataclasses.replace(shipped, llm=dataclasses.replace(shipped.llm, provider="vllm", base_url="http://localhost:8000/v1"))


def _chamber_member(cid: int) -> Citizen:
    c = Citizen(
        citizen_id=cid,
        issue_positions=tuple((cid * 0.019 + d * 0.013) % 1.0 for d in range(20)),
        issue_priorities=tuple(1.0 / 20 for _ in range(20)),
        blank_threshold=0.5,
        ambition_score=0.5,
        sortition_seat_until_tick=16,
        sortition_terms_served=1,
    )
    c.chamber_position = c.issue_positions
    return c


def main() -> int:
    config = _vllm_config()
    members = [_chamber_member(1000 + i) for i in range(75)]
    contexts = {m.citizen_id: lbe.ChamberContext(cid=m.citizen_id, ticks_left=12) for m in members}

    with VllmJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        print("== chunk_size=1 (forced, matching the pre-2026-09-08 shipped ceiling) ==")
        with mock.patch.object(lbe, "_chamber_chunk_size", return_value=1):
            start = time.perf_counter()
            outcome1 = lbe.decide_chamber_deliberation(members, contexts, config, client)
            elapsed1 = time.perf_counter() - start
        n_fallback1 = sum(outcome1.llm_fallback.values())
        n_retried1 = sum(outcome1.retry_sampling_varied.values())
        print(f"elapsed={elapsed1:.1f}s decisions={len(outcome1.decisions)} "
              f"fallback={n_fallback1} retried={n_retried1} s/member={elapsed1 / 75:.2f}")

        print("\n== chunk_size=5 (shipped default on vllm) ==")
        assert lbe._chamber_chunk_size(config) == 5
        start = time.perf_counter()
        outcome5 = lbe.decide_chamber_deliberation(members, contexts, config, client)
        elapsed5 = time.perf_counter() - start
        n_fallback5 = sum(outcome5.llm_fallback.values())
        n_retried5 = sum(outcome5.retry_sampling_varied.values())
        print(f"elapsed={elapsed5:.1f}s decisions={len(outcome5.decisions)} "
              f"fallback={n_fallback5} retried={n_retried5} s/member={elapsed5 / 75:.2f}")

    print(f"\nchunk=1: {elapsed1:.1f}s total, {elapsed1 / 75:.2f}s/member")
    print(f"chunk=5: {elapsed5:.1f}s total, {elapsed5 / 75:.2f}s/member")
    print(f"speedup factor: {elapsed1 / elapsed5:.2f}x")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
