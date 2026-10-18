"""scripts/rented/telemetry.py's reading of vLLM's Prometheus page (plan-rented-gpu-runs.md §10)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "rented" / "telemetry.py"
_spec = importlib.util.spec_from_file_location("rented_telemetry", SCRIPT)
assert _spec is not None and _spec.loader is not None
telemetry = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(telemetry)

PAGE = """# HELP vllm:num_requests_running Number of requests in model execution batches.
# TYPE vllm:num_requests_running gauge
vllm:num_requests_running{engine="0",model_name="qwen3.8:27b"} 12.0
vllm:num_requests_running{engine="1",model_name="qwen3.8:27b"} 3.0
vllm:kv_cache_usage_perc{engine="0",model_name="qwen3.8:27b"} 0.114
vllm:generation_tokens_total{engine="0",model_name="qwen3.8:27b"} 1.18e6
vllm:iteration_tokens_total_bucket{le="1.0"} 4.0
process_cpu_seconds_total 42.0
"""


def test_the_wanted_counters_are_summed_over_their_labels() -> None:
    assert telemetry.vllm_metrics(PAGE) == {
        "vllm:num_requests_running": 15.0, "vllm:kv_cache_usage_perc": 0.114, "vllm:generation_tokens_total": 1.18e6,
    }
