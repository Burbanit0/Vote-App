"""
Ensures `llm_test_harness` is importable when this test directory is run
directly (pytest fast_api_voter/scripts/llm_test_harness/tests/
-o addopts=""). Explicit sys.path insertion, matching every other script
in this project's own convention, rather than relying on pytest's
implicit rootdir-walk import behavior.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
