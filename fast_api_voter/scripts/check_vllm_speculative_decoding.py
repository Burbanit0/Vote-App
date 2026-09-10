"""
scripts/check_vllm_speculative_decoding.py

plan-llm-protocol-and-theory-program.md §3.B.6: n-gram speculative decoding
has zero mentions anywhere in this project's history -- untested, not
rejected. Lossless by construction (every speculated token is verified
against the real model's own distribution before being accepted, so at
temperature=0 output must be byte-identical with or without it) -- this
script proves that property directly rather than assuming it, the same
discipline this project already applies to every other server-level change
(vllm_determinism_results.md's own B2 protocol).

Run this TWICE: once against the server WITHOUT --speculative-config (the
baseline), once WITH it, using the exact same prompt/seed both times, and
diff the two runs' saved output. Usage:

    docker compose -f fast_api_voter/docker-compose.llm.yml up -d
    python fast_api_voter/scripts/check_vllm_speculative_decoding.py --out /tmp/before.json
    # edit docker-compose.llm.yml, restart, then:
    python fast_api_voter/scripts/check_vllm_speculative_decoding.py --out /tmp/after.json
    python -c "import json,sys; a=json.load(open('/tmp/before.json')); b=json.load(open('/tmp/after.json')); \
        print('IDENTICAL' if a['content']==b['content'] else 'DIFFERENT'); \
        print(f\"before: {a['elapsed']:.1f}s  after: {b['elapsed']:.1f}s\")"
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.citizen import Citizen  # noqa: E402
from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import (  # noqa: E402
    ChamberContext,
    build_chamber_system_prompt,
    build_chamber_user_prompt,
    compute_max_tokens,
)
from api.domain.polity.llm_client import VllmJsonClient  # noqa: E402
from api.domain.polity.llm_schemas import CHAMBER_JSON_SCHEMA  # noqa: E402


def _vllm_config():
    shipped = load_config()
    return dataclasses.replace(shipped, llm=dataclasses.replace(shipped.llm, provider="vllm", base_url="http://localhost:8000/v1"))


def _chamber_member(cid: int) -> Citizen:
    c = Citizen(
        citizen_id=cid,
        issue_positions=tuple((cid * 0.017 + d * 0.013) % 1.0 for d in range(20)),
        issue_priorities=tuple(1.0 / 20 for _ in range(20)),
        blank_threshold=0.5,
        ambition_score=0.5,
        sortition_seat_until_tick=16,
        sortition_terms_served=1,
    )
    c.chamber_position = c.issue_positions
    return c


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--reps", type=int, default=3)
    args = parser.parse_args(argv)

    config = _vllm_config()
    members = [_chamber_member(3000 + i) for i in range(5)]
    contexts = {m.citizen_id: ChamberContext(cid=m.citizen_id, ticks_left=12) for m in members}
    sp = build_chamber_system_prompt(members, config)
    up = build_chamber_user_prompt(members, contexts)
    max_tokens = compute_max_tokens(5) + 8000

    results = []
    with VllmJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        for rep in range(args.reps):
            start = time.perf_counter()
            raw = client.complete_json(
                system_prompt=sp, user_prompt=up, json_schema=CHAMBER_JSON_SCHEMA,
                max_tokens=max_tokens, think=True,
            )
            elapsed = time.perf_counter() - start
            print(f"rep {rep}: elapsed={elapsed:.1f}s len={len(raw)}")
            results.append({"elapsed": elapsed, "content": raw})

    args.out.write_text(json.dumps({"reps": results, "content": results[0]["content"]}), encoding="utf-8")
    print(f"wrote {args.out}")
    all_identical = all(r["content"] == results[0]["content"] for r in results)
    print(f"all {args.reps} reps byte-identical to each other: {all_identical}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
