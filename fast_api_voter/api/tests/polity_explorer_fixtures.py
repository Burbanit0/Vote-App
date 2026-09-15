"""Live runs for the run explorer's tests (run_frames, run_macro, explorer_biography,
run_catalog): short, but each drives a path the replay and the macro reading must handle."""
from __future__ import annotations

import dataclasses
import hashlib
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from api.domain.polity.checkpoint import load_checkpoint
from api.domain.polity.citizen import Role
from api.domain.polity.config import PolityConfig
from api.domain.polity.run_catalog import DEFAULT_RUN_ROOT
from api.domain.polity.run_digest import read_journal_tolerant
from api.domain.polity.run_frames import read_census, replay
from api.domain.polity.run_polity_simulation import run_simulation
from api.domain.polity.run_projection import build_projection
from api.tests.polity_golden import golden_config
from api.tests.test_polity_dynamic_citizens import MOVING, QUIET
from api.tests.test_polity_run_simulation import _ElectingFakeLlmClient, _FakeLlmClient

YEARS = 3


def _years(config: PolityConfig) -> PolityConfig:
    return dataclasses.replace(config, run=dataclasses.replace(config.run, duration_years=YEARS))


def _eventful(config: PolityConfig, *, term_years: int = 1, **institutions: Any) -> PolityConfig:
    """A short presidency and frequent rupture candidacies, so three years hold several
    elections and candidates who stand across a census; the model casts every ballot."""
    config = _years(config)
    return dataclasses.replace(
        config,
        candidacy=dataclasses.replace(config.candidacy, rupture_path_enabled=True, rupture_base_probability=0.03),
        institutions=dataclasses.replace(config.institutions, president_term_years=term_years, **institutions),
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


# ── the committed fixture run (B3) ────────────────────────────────────────

FIXTURE_RUN_ID = "explorer-fixture"
FIXTURE_ROOT = DEFAULT_RUN_ROOT
"""The explorer's default run root: what the API serves when POLITY_RUN_ROOTS is unset."""
FIXTURE_MANIFEST = "MANIFEST.json"


def file_digests(run_dir: Path) -> dict[str, str]:
    """Each fixture file's sha256, the manifest aside."""
    return {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(run_dir.iterdir()) if path.name != FIXTURE_MANIFEST
    }


def fixture_config(output_dir: Path) -> PolityConfig:
    """Three-year terms: long enough for legitimacy to fall, so the fixture holds recalls and
    snap elections beside its scheduled ones."""
    return _eventful(golden_config(output_dir, llm=True), term_years=3)


class FixtureLlmClient(_ElectingFakeLlmClient):  # type: ignore[misc]
    """The run-simulation fake, made to look like a population: voters rank the candidates
    by their own distances and vote blank when none is close enough, and citizens vary
    their pressure acts from one citizen and one consultation to the next."""

    def __init__(self) -> None:
        self._consultations = 0

    def _vote_decisions(self, voters: list[dict[str, Any]]) -> list[dict[str, Any]]:
        decisions = []
        for voter in voters:
            distances = voter["distances"]
            if min(distances) > voter["blank_threshold"]:
                decisions.append({"cid": voter["cid"], "blank": 1, "ranking": [], "motif": 101})
            else:
                ranking = [position + 1 for position in sorted(range(len(distances)), key=lambda p: (distances[p], p))][:3]
                decisions.append({"cid": voter["cid"], "blank": 0, "ranking": ranking, "motif": 105})
        return decisions

    def _pressure_decisions(self, consulted: list[dict[str, Any]]) -> list[dict[str, Any]]:
        self._consultations += 1
        decisions = []
        for citizen in consulted:
            available = citizen["available"]
            act = available[(citizen["cid"] + self._consultations) % len(available)]
            motif = 304 if act == 0 else 305 if act == 4 else 306 if citizen["cid"] % 2 else 301
            decisions.append({"cid": citizen["cid"], "target": citizen["target"], "act": act, "motif": motif})
        return decisions


# ── the replay oracle ─────────────────────────────────────────────────────

def _pledge(values: Sequence[float] | None) -> tuple[float, ...] | None:
    return tuple(values) if values is not None else None


def _view(role: str, office: str, pledged: Sequence[float] | None, revealed: Sequence[float] | None,
          exact_pledges: bool) -> tuple[Any, ...]:
    """Role, office and pledges. With opinion dynamics a standing candidate's pledge is
    their view on the tick they declared, which only the census records; the president's
    comes from the journal whole, so only candidates' pledges are left out there."""
    if not exact_pledges and role == Role.CANDIDATE.value:
        return role, office
    return role, office, _pledge(pledged), _pledge(revealed)


def replay_mismatches(run_dir: Path) -> list[str]:
    """Where a whole-run replay, without the yearly reset, departs from a census or from
    the final checkpoint: empty when it reproduces every one."""
    config = json.loads((run_dir / "config.json").read_text(encoding="utf-8"))
    census = read_census(run_dir / "snapshots.jsonl", config["run"]["population_size"])
    projection = build_projection(config, census)
    exact = projection.positions == "static"
    ticks_per_year = config["run"]["ticks_per_year"]
    events = read_journal_tolerant(run_dir / "events.jsonl")[0]
    mismatches = []
    compared = []
    state = None
    for tick, state, _marks in replay(events, census, projection, ticks_per_year, reset_yearly=False):
        year = (tick + 1) // ticks_per_year
        if (tick + 1) % ticks_per_year == 0 and year in census:
            compared.append(year)
            for cid, (citizen, row) in enumerate(zip(state.citizens, census[year])):
                if _view(citizen.role, citizen.office, citizen.pledged, citizen.revealed, exact) != _view(
                        row["role"], row["office"], row["pledged_platform"], row["revealed_position"], exact):
                    mismatches.append(f"census of year {year}, citizen {cid}")
    if compared != sorted(y for y in census if y > 0):
        mismatches.append(f"censuses compared {compared}, recorded {sorted(census)}")
    assert state is not None
    for cid, saved in enumerate(load_checkpoint(run_dir / "checkpoint.json").state.citizens):
        replayed = state.citizens[cid]
        if (*_view(saved.role.value, saved.office.value, saved.pledged_platform, saved.revealed_position, exact),
                saved.sortition_seat_until_tick is not None) != (
                *_view(replayed.role, replayed.office, replayed.pledged, replayed.revealed, exact), cid in state.chamber):
            mismatches.append(f"final checkpoint, citizen {cid}")
    return mismatches
