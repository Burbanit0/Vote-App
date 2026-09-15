"""Live runs for the run explorer's tests (run_frames, run_macro, explorer_biography,
run_catalog): short, but each drives a path the replay and the macro reading must handle."""
from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any

from api.domain.polity.config import PolityConfig
from api.domain.polity.run_polity_simulation import run_simulation
from api.tests.polity_golden import golden_config
from api.tests.test_polity_dynamic_citizens import MOVING, QUIET
from api.tests.test_polity_run_simulation import _ElectingFakeLlmClient, _FakeLlmClient

YEARS = 3


def _years(config: PolityConfig) -> PolityConfig:
    return dataclasses.replace(config, run=dataclasses.replace(config.run, duration_years=YEARS))


def _eventful(config: PolityConfig, **institutions: Any) -> PolityConfig:
    """A yearly presidency and frequent rupture candidacies, so three years hold several
    elections and candidates who stand across a census; the model casts every ballot."""
    config = _years(config)
    return dataclasses.replace(
        config,
        candidacy=dataclasses.replace(config.candidacy, rupture_path_enabled=True, rupture_base_probability=0.03),
        institutions=dataclasses.replace(config.institutions, president_term_years=1, **institutions),
        vote=dataclasses.replace(config.vote, mode="llm"),
    )


def explorer_runs(out: Path) -> dict[str, Path]:
    dynamic = dataclasses.replace(_eventful(golden_config(out / "dynamic", llm=False)), dynamics=MOVING, emotions=QUIET)
    return {
        # blank ballots: every election invalidated, reruns and forced attempts
        "invalidated": run_simulation(_eventful(golden_config(out / "invalidated", llm=True)), run_id="invalidated",
                                      llm_client=_FakeLlmClient()).parent,
        # a campaign a tick ahead of each election, recalls, representative responses
        "staggered": run_simulation(_eventful(golden_config(out / "staggered", llm=True), staggered_election=True),
                                    run_id="staggered", llm_client=_ElectingFakeLlmClient()).parent,
        # the shipped utility vote, the model voting only for the audit sample
        "audited": run_simulation(_years(golden_config(out / "audited", llm=True)), run_id="audited",
                                  llm_client=_ElectingFakeLlmClient()).parent,
        "deterministic": run_simulation(_eventful(golden_config(out / "deterministic", llm=False)), run_id="deterministic").parent,
        "dynamic": run_simulation(dynamic, run_id="dynamic").parent,
    }
