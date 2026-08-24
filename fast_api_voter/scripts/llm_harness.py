"""
fast_api_voter/scripts/llm_harness.py

Thin CLI entry point for the llm_test_harness package (register/report).

Usage:
    python fast_api_voter/scripts/llm_harness.py register \\
        --hypothesis "..." --decision-criterion "..." --planned-n 10 --budget "..."
    python fast_api_voter/scripts/llm_harness.py report <experiment_id> [--out FILE]

See fast_api_voter/scripts/llm_test_harness/README.md for the full
register -> run -> report workflow, including why `run` is a Python
script using trial.record_trial rather than a CLI subcommand.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from llm_test_harness.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
