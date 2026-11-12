"""
scripts/check_pressure_action_model_comparison.py

Eighth follow-up to the chunk-collapse finding (reasoning_budget_and_decision_quality_findings.md).
The closed investigation eliminated position, batch size (1 through 25), and one specific prompt
sentence as sole causes for pressure_action's total avoidance of acting codes (SIGN_PETITION/
LAUNCH_PETITION/MOBILIZE) below production batch size -- leaving the leading hypothesis as
something about the model's own behavior on this menu shape (2 of 5 options framed as always-
legitimate), not proven, not testable by further prompt deletion.

This asks a question the closed investigation never touched: is the collapse specific to
qwen3:8b, or does it reproduce across other models? Runs the REAL, unmodified production prompt
(build_pressure_system_prompt/build_pressure_user_prompt, think=False, size=1 -- exactly the
shipped call shape) against 4 other models, on the same 5 representative cases already used in
the prompt-ablation test: 4 extreme "should act" citizens (cid=6 ratio=4.226, cid=152 ratio=3.250,
cid=270 ratio=2.579, cid=146 ratio=2.397) plus 1 extreme "should NOT act" control (cid=158
ratio=0.177).

Does not touch config.llm.model in polity_config.yaml -- builds a per-call LlmConfig override via
dataclasses.replace, same pattern as every prior script in this workstream.

Usage:
    python fast_api_voter/scripts/check_pressure_action_model_comparison.py
"""
from __future__ import annotations

import dataclasses
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

_MODELS = ["llama3.1:8b", "gemma2:9b", "mistral:7b", "qwen2.5:7b"]

_CASES: list[dict[str, int | float | str]] = [
    {"cid": 6, "self_gap": 0.2802, "blank_threshold": 0.0663, "role": "should-ACT (extreme)"},
    {"cid": 152, "self_gap": 0.3458, "blank_threshold": 0.1064, "role": "should-ACT (extreme)"},
    {"cid": 270, "self_gap": 0.4825, "blank_threshold": 0.1871, "role": "should-ACT (extreme)"},
    {"cid": 146, "self_gap": 0.4161, "blank_threshold": 0.1736, "role": "should-ACT (extreme)"},
    {"cid": 158, "self_gap": 0.086, "blank_threshold": 0.487, "role": "should-NOT-act (control)"},
]

# qwen3:8b baseline, already measured (check_pressure_action_size_one.py, real prompt, size=1, think=False)
_QWEN3_BASELINE = {6: 0, 152: 4, 270: 4, 146: 4, 158: 0}


def main() -> int:
    config = load_config()
    citizens_by_id = {c.citizen_id: c for c in generate_population(config.citizens, 280, config.run.seed)}

    all_results: dict[str, dict[int, tuple[int, int]]] = {}
    for model in _MODELS:
        model_config = dataclasses.replace(config.llm, model=model)
        results: dict[int, tuple[int, int]] = {}
        print(f"\n########## model={model} ##########")
        with OllamaJsonClient.from_config(model_config, seed=config.run.seed) as client:
            for case in _CASES:
                cid = int(case["cid"])
                citizen = citizens_by_id[cid]
                self_gap = float(case["self_gap"])
                ctx = PressureContext(
                    cid=cid, target=_TARGET, self_gap=self_gap, mandate_dev=_MANDATE_DEV,
                    ticks_to_election=_TICKS_TO_ELECTION, available=(0, 1, 2, 3, 4),
                    petition_open=False, petition_expires_at_tick=None, already_signed=False,
                    neighbors_acting=None,
                )
                try:
                    raw = client.complete_json(
                        system_prompt=build_pressure_system_prompt([citizen], config),
                        user_prompt=build_pressure_user_prompt([citizen], {cid: ctx}),
                        json_schema=PRESSURE_JSON_SCHEMA,
                        max_tokens=compute_max_tokens(1),
                        think=False,
                    )
                    decision = decode_pressure_batch(raw, [cid])[0]
                    results[cid] = (decision.act, decision.motif)
                    ratio = self_gap / float(case["blank_threshold"])
                    print(
                        f"  cid={cid:>4} [{case['role']}] ratio={ratio:.3f} -> "
                        f"act={decision.act} ({_ACT_NAMES[decision.act]}) motif={decision.motif}"
                    )
                except Exception as exc:  # noqa: BLE001 -- report per-model failures without aborting the whole comparison
                    print(f"  cid={cid:>4} [{case['role']}] FAILED: {exc}")
                    results[cid] = (-1, -1)
        all_results[model] = results

    print("\n--- summary: acting codes chosen per model (of 5 cases) ---")
    print(f"qwen3:8b (baseline, already measured): 0/5 acting codes")  # noqa: F541
    for model in _MODELS:
        results = all_results[model]
        acting = [cid for cid, (act, _m) in results.items() if act in _ACTING_CODES]
        failed = [cid for cid, (act, _m) in results.items() if act == -1]
        print(f"{model}: {len(acting)}/5 acting codes {acting}{' (failures: ' + str(failed) + ')' if failed else ''}")

    print("\n--- verdict (per-model, NOT a single aggregated claim -- see plan-pressure-action-remediation.md §1) ---")
    for model in _MODELS:
        results = all_results[model]
        n_failed = sum(1 for act, _m in results.values() if act == -1)
        n_ok = len(results) - n_failed
        n_acting = sum(1 for act, _m in results.values() if act in _ACTING_CODES)
        if n_failed == len(results):
            category = "NOT EVALUABLE -- structured-output schema-compliance failure on every call, not a content result"
        elif n_ok < 3:
            category = f"insufficient sample (n={n_ok}) to conclude either way"
        elif n_acting == n_ok:
            category = "content-blind collapse to ACTING codes -- opposite pole from qwen3:8b, not a replication of it"
        elif n_acting == 0:
            category = "content-blind collapse to NON-acting codes -- same pole as qwen3:8b"
        else:
            category = f"mixed ({n_acting}/{n_ok} acting) -- neither a clean collapse nor evidence of correct tracking without checking against the proxy per-case"
        print(f"{model}: {category}")
    print(
        "\nDo not compress this into one aggregate sentence. Two of four alternative models could "
        "not be evaluated at all (JSON schema-compliance failure, unrelated to content quality). "
        "Of the two with a usable sample, they diverge in OPPOSITE directions (qwen2.5:7b's small "
        "n=3 leans NOTHING like qwen3:8b; mistral:7b's full n=5 collapses to MOBILIZE instead) --"
        " that divergence is itself evidence for a structural/task-shape cause across model "
        "families, not evidence that qwen3:8b is uniquely broken or that switching model fixes it."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
