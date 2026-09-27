"""
fast_api_voter/scripts/llm_test_harness

Reusable harness for GPU/LLM reliability experiments -- pre-registration,
automatic environment capture, structured SQLite storage, and generated
(never hand-written) markdown reports. Built to replace the ad hoc
scripts and narrative *_results.md files from this project's own
2026-08-17/19 GPU investigation, whose own noise source (an antivirus
scan, coinciding with one of three observed failures) was discovered only
by reconstructing Windows event logs after the fact -- exactly what
environment.py exists to capture live instead.

See README.md for the register -> run -> report workflow and why `run`
is a library call (trial.record_trial), not a CLI subcommand.
"""
from __future__ import annotations

from .environment import EnvironmentSnapshot, capture
from .registration import Experiment, register
from .report import generate_report
from .sample_size import exhaustion_probability, required_sample_size, z_score
from .trial import TrialResult, record_trial

__all__ = [
    "EnvironmentSnapshot",
    "capture",
    "Experiment",
    "register",
    "generate_report",
    "exhaustion_probability",
    "required_sample_size",
    "z_score",
    "TrialResult",
    "record_trial",
]
