"""Run one model through the bake-off case bank (S2.2), or replay a recorded call log.

Every model answers the same frozen cases (scripts/bakeoff/case_bank.jsonl); token budgets
follow the model's own profile (api/domain/polity/model_profiles.py). A session writes
scripts/bakeoff_runs/<label>/ and resumes if interrupted. Score sessions with
scripts/bakeoff_report.py.

Usage (from fast_api_voter/):
    # live, against the vLLM server (docker-compose.llm.yml)
    python scripts/run_bakeoff.py --label qwen3-8b-awq
    python scripts/run_bakeoff.py --label granite --model granite-4.2-8b --base-url http://localhost:8001/v1

    # no GPU: answer the cases from a recorded llm_calls.jsonl (a bake-off session, or a run
    # whose requests the cases match -- the p500 batch's seed-42 run answers candidacy_p500)
    python scripts/run_bakeoff.py --label replay-seed42 --families candidacy_p500 \\
        --replay-calls-from ../../Vote-App-p500/fast_api_voter/scripts/seed_sweep_runs/sweep-8y-p500-seed42/run/sweep-8y-p500-seed42

A replay has no logprobs (probabilities stay unmeasured), no warm-up, and holds each
request once, so it re-runs nothing.
"""
from __future__ import annotations

import argparse
import dataclasses
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.bakeoff_cases import read_bank  # noqa: E402
from api.domain.polity.bakeoff_runner import DEFAULT_RERUN_FRACTION, run_session  # noqa: E402
from api.domain.polity.config import PolityConfig  # noqa: E402
from api.domain.polity.llm_call_log import CALL_LOG_FILENAME, read_calls  # noqa: E402
from api.domain.polity.llm_client import build_json_client  # noqa: E402
from api.domain.polity.llm_replay import ReplayClient  # noqa: E402
from api.domain.polity.model_profiles import model_profile  # noqa: E402
from api.domain.polity.run_provenance import git_provenance, vllm_server_provenance  # noqa: E402
from bakeoff_cases import DEFAULT_BANK, reference_config  # noqa: E402

DEFAULT_RUNS = Path(__file__).resolve().parent / "bakeoff_runs"


def session_config(provider: str, model: str | None, base_url: str | None) -> PolityConfig:
    config = reference_config(provider=provider, model=model)
    if base_url is not None:
        config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, base_url=base_url))
    return config


def _call_log(path: Path) -> Path:
    return path / CALL_LOG_FILENAME if path.is_dir() else path


def session_metadata(args: argparse.Namespace, config: PolityConfig) -> dict[str, Any]:
    profile = model_profile(config.llm.provider, config.llm.model)
    live = args.replay_calls_from is None
    return {
        "label": args.label,
        "provider": config.llm.provider,
        "model": config.llm.model,
        "weights": profile.weights,
        "family": profile.family,
        "base_url": config.llm.base_url if live else None,
        "replayed_from": None if live else str(_call_log(args.replay_calls_from)),
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "git": git_provenance(),
        "server": vllm_server_provenance(config.llm.base_url) if live and config.llm.provider == "vllm" else None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--label", required=True, help="the session's name, and its directory under --out")
    parser.add_argument("--provider", default="vllm", choices=("vllm", "ollama"))
    parser.add_argument("--model", default=None, help="llm.model as served (default: the shipped config's); needs a model profile")
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--bank", type=Path, default=DEFAULT_BANK)
    parser.add_argument("--out", type=Path, default=DEFAULT_RUNS)
    parser.add_argument("--families", nargs="+", default=None, help="only these families (the logprob gate always runs)")
    parser.add_argument("--replay-calls-from", type=Path, default=None, help="a run or session directory, or its llm_calls.jsonl")
    parser.add_argument("--rerun-fraction", type=float, default=DEFAULT_RERUN_FRACTION)
    args = parser.parse_args(argv)

    bank = read_bank(args.bank)
    config = session_config(args.provider, args.model, args.base_url)
    metadata = session_metadata(args, config)
    replaying = args.replay_calls_from is not None
    client: Any = ReplayClient(read_calls(_call_log(args.replay_calls_from))) if replaying else build_json_client(config.llm, seed=config.run.seed)
    try:
        session_dir = run_session(
            bank, client, config, args.out / args.label, metadata=metadata, families=args.families,
            warm_up=not replaying, rerun_fraction=0.0 if replaying else args.rerun_fraction,
        )
    finally:
        close = getattr(client, "close", None)
        if callable(close):
            close()
    print(f"session written to {session_dir}; score it with: python scripts/bakeoff_report.py {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
