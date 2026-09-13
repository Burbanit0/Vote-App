"""Golden references: prompts sent and journals written must match the committed
manifest. See api/tests/polity_golden.py for why these exist."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from api.tests.polity_golden import GOLDEN_MANIFEST, LLM_DECISION_TYPES, compute_manifest, describe_drift


@pytest.fixture(scope="module")
def actual_manifest(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    return compute_manifest(Path(tmp_path_factory.mktemp("polity_golden")))


def test_prompts_and_journals_match_the_golden_references(actual_manifest: dict[str, Any]) -> None:
    expected = json.loads(GOLDEN_MANIFEST.read_text(encoding="utf-8"))
    if actual_manifest != expected:
        pytest.fail(
            "Polity golden references changed:\n"
            f"{describe_drift(expected, actual_manifest)}\n\n"
            "If this change is intentional, regenerate with `python scripts/gen_polity_golden.py` "
            "(from fast_api_voter/) and explain in the commit message what changed and why.",
            pytrace=False,
        )


def test_the_golden_scenario_exercises_every_llm_decision_type(actual_manifest: dict[str, Any]) -> None:
    # A reference that silently stops covering a decision type guards nothing for it.
    requested = set(actual_manifest["fake_llm"]["requests"]["by_decision_type"])
    journaled = set(actual_manifest["fake_llm"]["by_event_type"])
    assert "unknown_schema" not in requested
    assert set(LLM_DECISION_TYPES) <= requested
    assert set(LLM_DECISION_TYPES) <= journaled
