"""Lot 8 — run_polity_simulation.py: orchestration + the reproducibility test.

Contracts (dev-plan-v0-worktree.md §3-4, Lot 8):
- Integration: a full 30-year run completes without error and produces a
  non-empty journal.
- Transversal, "the test that matters more than the others": two full runs
  with the same seed produce byte-identical journals.
"""
import dataclasses
import json

import numpy as np
import pytest

import api.domain.polity.run_polity_simulation as run_polity_simulation_module
from api.domain.polity.accountability import chamber_deviation, unified_mandate_deviation, update_street_pressure
from api.domain.polity.citizen import Citizen, Office, Role, generate_population
from api.domain.polity.codebook import EventType, ReactionMotif
from api.domain.polity.config import PolityConfig, load_config
from api.domain.polity.journal import Journal
from api.domain.polity.llm_behavior_engine import _VOTE_CAST_RETRY_TEMPERATURE
from api.domain.polity.llm_client import LlmResponseError, OllamaJsonClient, VllmJsonClient
from api.domain.polity.metrics import consultation_rate, mobilization_rate
from api.domain.polity.parties import Party, initialize_parties
from api.domain.polity.run_polity_simulation import (
    ExogenousEventsOutcome,
    PendingRerun,
    _attempt_rupture_candidacies,
    _declare_nominees_llm,
    _hold_presidential_election,
    _llm_client_scope,
    _run_accountability_phase,
    _run_chamber_deliberation,
    _run_exogenous_events,
    _run_sortition_rotation,
    _warm_up_llm_client,
    _warn_if_no_candidate_is_possible,
    run_simulation,
)
from api.domain.polity.simple_rules import assign_party_affiliation, declare_candidacy
from api.domain.polity.social_graph import SocialGraph

_PETITION_LIFECYCLE_EVENT_TYPES = {
    "petition_launched", "petition_signed", "petition_expired",
    "confidence_vote_triggered", "confidence_vote_result",
}


def _config_with_output_dir(output_dir) -> PolityConfig:
    config = load_config()
    return dataclasses.replace(
        config,
        # index_after_run=False here (every other _config_with_* helper
        # chains through this one, and dataclasses.replace only touches
        # the field it's given -- so this propagates everywhere): compaction
        # is real DuckDB work (v4 storage lot, §16.6) and this suite builds
        # journals with thousands of events under awakening/mobilization/
        # petition, which measurably dominates wall-clock (~190s across
        # this file alone). The shipped YAML default (true) is untouched --
        # tests that specifically exercise compaction turn it back on
        # explicitly. See test_polity_compaction.py for offline coverage.
        journal=dataclasses.replace(config.journal, output_dir=str(output_dir), index_after_run=False),
    )


def _events(journal_path):
    return [json.loads(line) for line in journal_path.read_text(encoding="utf-8").splitlines()]


# ── _llm_client_scope (v4 vLLM switch, §15bis.6 — dispatch on provider) ──
# Constructing OllamaJsonClient/VllmJsonClient opens no socket (httpx.Client
# doesn't connect until a request is sent), so these stay fully offline.
# The two provider-dispatch tests below patch _warm_up_llm_client to a
# no-op: entering _llm_client_scope's `with` block now runs one real,
# best-effort warm-up call on an owned (non-injected) client (GPU
# reliability fix, see that function's own docstring) -- without patching
# it here these tests would attempt real network I/O against a real
# client just to check its TYPE, breaking the "fully offline" contract
# above. The two tests that already inject a client (sentinel / None-when-
# disabled) never reach _warm_up_llm_client at all -- it's called only
# inside the `with build_json_client(...) as owned_client:` branch -- so
# they need no patch.

def test_llm_client_scope_yields_the_injected_client_untouched():
    config = load_config()
    sentinel = object()
    with _llm_client_scope(config, sentinel) as client:  # type: ignore[arg-type]
        assert client is sentinel


def test_llm_client_scope_yields_none_when_llm_is_disabled():
    config = load_config()
    assert config.llm.enabled is False  # shipped default
    with _llm_client_scope(config, None) as client:
        assert client is None


def test_llm_client_scope_builds_an_ollama_client_for_the_ollama_provider(monkeypatch):
    monkeypatch.setattr(run_polity_simulation_module, "_warm_up_llm_client", lambda client: None)
    config = load_config()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, enabled=True, provider="ollama"))
    with _llm_client_scope(config, None) as client:
        assert isinstance(client, OllamaJsonClient)


def test_llm_client_scope_builds_a_vllm_client_for_the_vllm_provider(monkeypatch):
    monkeypatch.setattr(run_polity_simulation_module, "_warm_up_llm_client", lambda client: None)
    config = load_config()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, enabled=True, provider="vllm"))
    with _llm_client_scope(config, None) as client:
        assert isinstance(client, VllmJsonClient)


def test_llm_client_scope_calls_warm_up_exactly_once_for_an_owned_client(monkeypatch):
    calls = []
    monkeypatch.setattr(run_polity_simulation_module, "_warm_up_llm_client", lambda client: calls.append(client))
    config = load_config()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, enabled=True, provider="ollama"))
    with _llm_client_scope(config, None) as client:
        assert calls == [client]


def test_llm_client_scope_never_warms_up_an_injected_client(monkeypatch):
    calls = []
    monkeypatch.setattr(run_polity_simulation_module, "_warm_up_llm_client", lambda client: calls.append(client))
    config = load_config()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, enabled=True, provider="ollama"))
    sentinel = object()
    with _llm_client_scope(config, sentinel):  # type: ignore[arg-type]
        pass
    assert calls == []


def test_llm_client_scope_rejects_the_api_provider_at_run_start():
    config = load_config()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, enabled=True, provider="api"))
    with pytest.raises(NotImplementedError, match="provider"):
        with _llm_client_scope(config, None):
            pass


# ── _warm_up_llm_client (GPU cold-start reliability fix) ──────────────────
# scripts/llm_batching_determinism_results_gpu.md, "cold start vs warm"
# section: a freshly loaded Ollama model's first inference pass is
# measurably non-deterministic; every subsequent call with the same input
# is not. This exercises one call through each endpoint shape before any
# real decision runs.

class _RecordingClient:
    def __init__(self, *, fail_think: bool = False) -> None:
        self.calls: list[bool] = []
        self._fail_think = fail_think

    def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
        self.calls.append(think)
        if think is self._fail_think:
            raise RuntimeError("simulated warm-up failure")
        return '{"ok": true}'


def test_warm_up_llm_client_calls_both_endpoint_shapes_once_each():
    client = _RecordingClient()
    _warm_up_llm_client(client)
    assert client.calls == [True, False]


def test_warm_up_llm_client_swallows_a_failure_on_one_endpoint_and_still_tries_the_other():
    client = _RecordingClient(fail_think=True)
    _warm_up_llm_client(client)  # must not raise
    assert client.calls == [True, False]


def test_warm_up_llm_client_never_raises_even_when_both_endpoints_fail():
    class _AlwaysFailingClient:
        def complete_json(self, **kwargs):
            raise RuntimeError("simulated warm-up failure")

    _warm_up_llm_client(_AlwaysFailingClient())  # must not raise


# ── compaction wiring (v4 storage lot, §16.6) ─────────────────────────────
# _config_with_output_dir sets index_after_run=False for this whole suite's
# wall-clock (see its own docstring) -- every test below that actually
# exercises compaction re-enables it explicitly. The shipped YAML default
# is true; test_loads_the_real_polity_config_with_expected_v0_values
# (test_polity_config.py) is what pins that.

def test_run_simulation_writes_a_duckdb_beside_the_journal_when_index_after_run(tmp_path):
    config = _config_with_output_dir(tmp_path)
    config = dataclasses.replace(config, journal=dataclasses.replace(config.journal, index_after_run=True))
    journal_path = run_simulation(config, run_id="compaction-on")
    assert journal_path.with_name("events.duckdb").is_file()


def test_run_simulation_writes_no_duckdb_when_index_after_run_is_false(tmp_path):
    config = _config_with_output_dir(tmp_path)
    assert config.journal.index_after_run is False
    journal_path = run_simulation(config, run_id="compaction-off")
    assert journal_path.is_file()
    assert not journal_path.with_name("events.duckdb").exists()


def test_compaction_does_not_change_a_single_journal_byte(tmp_path):
    # The non-negotiable check: compacting must never perturb journal.py's
    # writer behavior or any existing journal byte.
    config_on = _config_with_output_dir(tmp_path / "on")
    config_on = dataclasses.replace(config_on, journal=dataclasses.replace(config_on.journal, index_after_run=True))
    config_off = _config_with_output_dir(tmp_path / "off")
    assert config_off.journal.index_after_run is False

    path_on = run_simulation(config_on, run_id="same-run-id")
    path_off = run_simulation(config_off, run_id="same-run-id")

    assert path_on.read_bytes() == path_off.read_bytes()


def test_full_run_completes_and_produces_a_non_empty_journal(tmp_path):
    journal_path = run_simulation(_config_with_output_dir(tmp_path), run_id="baseline")
    assert journal_path.is_file()
    lines = journal_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) > 0
    for line in lines:
        json.loads(line)  # every line is valid, complete JSON


def test_election_counts_match_the_calendar(tmp_path):
    journal_path = run_simulation(_config_with_output_dir(tmp_path), run_id="baseline")
    events = _events(journal_path)
    presidential_outcomes = [e for e in events if e["event_type"] in ("elected", "election_no_winner")]
    legislative_results = [e for e in events if e["event_type"] == "legislative_result"]
    assert len(presidential_outcomes) == 8
    assert len(legislative_results) == 8


def test_every_legislative_result_allocates_all_seats(tmp_path):
    journal_path = run_simulation(_config_with_output_dir(tmp_path), run_id="baseline")
    config = load_config()
    for event in _events(journal_path):
        if event["event_type"] == "legislative_result":
            assert sum(event["payload"]["seats"].values()) == config.institutions.assembly_seats


def test_two_runs_with_the_same_seed_produce_byte_identical_journals(tmp_path):
    path_a = run_simulation(_config_with_output_dir(tmp_path / "a"), run_id="same-run-id")
    path_b = run_simulation(_config_with_output_dir(tmp_path / "b"), run_id="same-run-id")
    assert path_a.read_bytes() == path_b.read_bytes()


def test_different_seed_produces_a_different_journal(tmp_path):
    config_a = _config_with_output_dir(tmp_path / "a")
    config_b = _config_with_output_dir(tmp_path / "b")
    config_b = dataclasses.replace(config_b, run=dataclasses.replace(config_b.run, seed=999))
    path_a = run_simulation(config_a, run_id="r")
    path_b = run_simulation(config_b, run_id="r")
    assert path_a.read_bytes() != path_b.read_bytes()


# ── run_metadata.json (backend-traceability gap, prompt-verification-gpu-
# determinisme.md's step 3) -- a sibling of events.jsonl, NOT a journal
# event, so the journal's own byte-identical contract is untouched.

def test_run_metadata_json_is_written_beside_the_journal(tmp_path):
    journal_path = run_simulation(_config_with_output_dir(tmp_path), run_id="r")
    metadata_path = journal_path.parent / "run_metadata.json"
    assert metadata_path.exists()
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["run_id"] == "r"


def test_run_metadata_records_none_for_llm_fields_when_the_llm_is_disabled(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(
        run_polity_simulation_module, "_capture_gpu_driver_info", lambda: calls.append(1) or ("999.99", "13.1")
    )
    journal_path = run_simulation(_config_with_output_dir(tmp_path), run_id="r")
    metadata = json.loads((journal_path.parent / "run_metadata.json").read_text(encoding="utf-8"))
    assert metadata["llm_enabled"] is False
    assert metadata["llm_provider"] is None
    assert metadata["llm_base_url"] is None
    assert metadata["llm_model"] is None
    # gpu_driver_version/gpu_cuda_version stay None when llm.enabled=False -- the capture
    # helper is never even called, not just discarded (a subprocess call has no use for a
    # deterministic-only run, and >100 test invocations of run_simulation share this path).
    assert calls == []
    assert metadata["gpu_driver_version"] is None
    assert metadata["gpu_cuda_version"] is None


def test_run_metadata_records_the_llm_provider_base_url_and_model_when_enabled(tmp_path, monkeypatch):
    monkeypatch.setattr(
        run_polity_simulation_module, "_capture_gpu_driver_info", lambda: ("591.86", "13.1")
    )
    config = _config_with_llm_enabled(tmp_path)
    journal_path = run_simulation(config, run_id="r", llm_client=_FakeLlmClient())
    metadata = json.loads((journal_path.parent / "run_metadata.json").read_text(encoding="utf-8"))
    assert metadata["llm_enabled"] is True
    assert metadata["llm_provider"] == config.llm.provider
    assert metadata["llm_base_url"] == config.llm.base_url
    assert metadata["llm_model"] == config.llm.model
    assert metadata["gpu_driver_version"] == "591.86"
    assert metadata["gpu_cuda_version"] == "13.1"


def test_run_metadata_gpu_fields_fall_back_to_none_when_the_capture_helper_finds_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(run_polity_simulation_module, "_capture_gpu_driver_info", lambda: (None, None))
    config = _config_with_llm_enabled(tmp_path)
    journal_path = run_simulation(config, run_id="r", llm_client=_FakeLlmClient())
    metadata = json.loads((journal_path.parent / "run_metadata.json").read_text(encoding="utf-8"))
    assert metadata["gpu_driver_version"] is None
    assert metadata["gpu_cuda_version"] is None


class _FakeCompletedProcess:
    def __init__(self, stdout: str) -> None:
        self.stdout = stdout


def test_capture_gpu_driver_info_parses_driver_and_cuda_version(monkeypatch):
    responses = iter([
        _FakeCompletedProcess("591.86\n"),
        _FakeCompletedProcess(
            "Sat Aug 22 13:30:00 2026       \n"
            "+-----------------------------------------------------------------------------------------+\n"
            "| NVIDIA-SMI 591.86                 Driver Version: 591.86         CUDA Version: 13.1     |\n"
        ),
    ])
    monkeypatch.setattr(
        run_polity_simulation_module.subprocess, "run", lambda *a, **kw: next(responses)
    )
    driver_version, cuda_version = run_polity_simulation_module._capture_gpu_driver_info()
    assert driver_version == "591.86"
    assert cuda_version == "13.1"


def test_capture_gpu_driver_info_degrades_to_none_on_subprocess_failure(monkeypatch):
    def _raise(*args, **kwargs):
        raise FileNotFoundError("nvidia-smi not found")

    monkeypatch.setattr(run_polity_simulation_module.subprocess, "run", _raise)
    driver_version, cuda_version = run_polity_simulation_module._capture_gpu_driver_info()
    assert driver_version is None
    assert cuda_version is None


def test_capture_gpu_driver_info_degrades_to_none_when_cuda_version_marker_is_absent(monkeypatch):
    responses = iter([
        _FakeCompletedProcess("591.86\n"),
        _FakeCompletedProcess("no CUDA marker in this output\n"),
    ])
    monkeypatch.setattr(
        run_polity_simulation_module.subprocess, "run", lambda *a, **kw: next(responses)
    )
    driver_version, cuda_version = run_polity_simulation_module._capture_gpu_driver_info()
    assert driver_version == "591.86"
    assert cuda_version is None


def test_run_metadata_does_not_perturb_the_journals_own_byte_identical_reproducibility(tmp_path):
    path_a = run_simulation(_config_with_output_dir(tmp_path / "a"), run_id="same-run-id")
    path_b = run_simulation(_config_with_output_dir(tmp_path / "b"), run_id="same-run-id")
    assert path_a.read_bytes() == path_b.read_bytes()
    assert (path_a.parent / "run_metadata.json").exists()
    assert (path_b.parent / "run_metadata.json").exists()


# ── outgoing president's stale office/role reset ─────────────────────────

def _office_test_citizen(cid, position):
    return Citizen(
        citizen_id=cid,
        issue_positions=(position,),
        issue_priorities=(1.0,),
        blank_threshold=1.0,
        ambition_score=0.5,
    )


def test_outgoing_president_is_reset_when_the_next_presidential_election_runs(tmp_path):
    # Regression test: without the fix, a president who isn't immediately
    # re-nominated keeps role=ELECTED/office=PRESIDENT forever, so a second
    # election leaves two citizens simultaneously holding Office.PRESIDENT.
    config = load_config()
    term_ticks = config.institutions.president_term_years * config.run.ticks_per_year

    citizen_a = _office_test_citizen(0, 0.1)
    citizen_b = _office_test_citizen(1, 0.9)
    electors = [_office_test_citizen(i, 0.5) for i in range(2, 7)]
    declare_candidacy(citizen_a)

    with Journal(tmp_path / "run.jsonl", run_id="r") as journal:
        # Tick 0: A stands uncontested and wins.
        _hold_presidential_election([citizen_a] + electors, [], config, journal, tick=0, llm_client=None)
        assert citizen_a.role == Role.ELECTED
        assert citizen_a.office == Office.PRESIDENT
        assert citizen_a.term_end_tick == term_ticks

        # Tick term_ticks: A's term has ended. A is not re-nominated -- only
        # B declares -- so B stands uncontested and wins.
        declare_candidacy(citizen_b)
        _hold_presidential_election(
            [citizen_a, citizen_b] + electors, [], config, journal, tick=term_ticks, llm_client=None
        )

    assert citizen_b.role == Role.ELECTED
    assert citizen_b.office == Office.PRESIDENT
    assert citizen_b.term_end_tick == 2 * term_ticks

    assert citizen_a.role == Role.ELECTOR
    assert citizen_a.office == Office.NONE
    assert citizen_a.term_end_tick is None


def test_a_reelected_president_keeps_office_and_accumulates_mandates(tmp_path):
    # A's own party re-nominates them each cycle (select_party_nominee has
    # no role filter, so this works whether A is currently ELECTOR or
    # ELECTED) -- the realistic path an incumbent's re-election takes,
    # unlike manually pre-declaring candidacy between calls: the reset at
    # the top of _hold_presidential_election runs before nominees are
    # (re)declared each time it's called, so a role set before the call
    # would just be overwritten by it.
    config = load_config()
    term_ticks = config.institutions.president_term_years * config.run.ticks_per_year

    citizen_a = _office_test_citizen(0, 0.1)
    citizen_a.ambition_score = 1.0
    citizen_a.party_affiliation = 0
    party = Party(party_id=0, platform=(0.1,))
    electors = [_office_test_citizen(i, 0.5) for i in range(1, 6)]

    with Journal(tmp_path / "run.jsonl", run_id="r") as journal:
        _hold_presidential_election([citizen_a] + electors, [party], config, journal, tick=0, llm_client=None)
        assert citizen_a.mandates_served == 1
        assert citizen_a.office == Office.PRESIDENT

        _hold_presidential_election(
            [citizen_a] + electors, [party], config, journal, tick=term_ticks, llm_client=None
        )

    assert citizen_a.role == Role.ELECTED
    assert citizen_a.office == Office.PRESIDENT
    assert citizen_a.term_end_tick == 2 * term_ticks
    assert citizen_a.mandates_served == 2


def _config_with_rupture_enabled(output_dir) -> PolityConfig:
    config = _config_with_output_dir(output_dir)
    return dataclasses.replace(
        config,
        candidacy=dataclasses.replace(
            config.candidacy,
            rupture_path_enabled=True,
            rupture_base_probability=0.05,
            rupture_signature_ratio=0.01,
        ),
    )


def test_rupture_path_produces_a_rupture_candidacy_event(tmp_path):
    journal_path = run_simulation(_config_with_rupture_enabled(tmp_path), run_id="rupture")
    events = _events(journal_path)
    rupture_events = [
        e for e in events if e["event_type"] == "candidacy_declared" and e["payload"].get("path") == "rupture"
    ]
    assert len(rupture_events) > 0


def test_two_runs_with_rupture_enabled_produce_byte_identical_journals(tmp_path):
    path_a = run_simulation(_config_with_rupture_enabled(tmp_path / "a"), run_id="same-run-id")
    path_b = run_simulation(_config_with_rupture_enabled(tmp_path / "b"), run_id="same-run-id")
    assert path_a.read_bytes() == path_b.read_bytes()


# ── mandate tracking (v4 Lot 2) ──────────────────────────────────────────

def _config_with_mandate_enabled(output_dir) -> PolityConfig:
    config = _config_with_output_dir(output_dir)
    return dataclasses.replace(config, mandate=dataclasses.replace(config.mandate, enabled=True))


def _config_with_mandate_enabled_and_guaranteed_winners(output_dir) -> PolityConfig:
    # The shipped default ambition_threshold (0.7) never actually produces a
    # presidential winner at seed=42 (every election_no_winner) -- lowering
    # it to 0 guarantees nominees, and therefore `elected` events to assert
    # mandate_pledge_declared against.
    config = _config_with_mandate_enabled(output_dir)
    return dataclasses.replace(config, candidacy=dataclasses.replace(config.candidacy, ambition_threshold=0.0))


def test_default_config_run_emits_no_mandate_events(tmp_path):
    # The accountability phase is wired into every tick (v4 Lot 2's
    # structural change) but must stay inert under the shipped default
    # (mandate.enabled: false) -- zero new journal bytes.
    journal_path = run_simulation(_config_with_output_dir(tmp_path), run_id="baseline")
    events = _events(journal_path)
    assert not [e for e in events if e["event_type"] in ("mandate_pledge_declared", "mandate_deviation_recorded")]


def test_mandate_enabled_run_declares_a_pledge_per_election_and_records_no_deviation(tmp_path):
    # §7bis.5 control case: without representative_response (Lot 6),
    # revealed_position never diverges from pledged_platform, so deviation
    # is 0 everywhere through Lot 5 -- asserted here, not just claimed.
    journal_path = run_simulation(_config_with_mandate_enabled_and_guaranteed_winners(tmp_path), run_id="mandate-on")
    events = _events(journal_path)
    elected = [e for e in events if e["event_type"] == "elected"]
    pledges = [e for e in events if e["event_type"] == "mandate_pledge_declared"]
    deviations = [e for e in events if e["event_type"] == "mandate_deviation_recorded"]
    assert len(elected) > 0
    assert len(pledges) == len(elected)
    for pledge in pledges:
        assert len(pledge["payload"]["pledged_platform"]) == load_config().citizens.issue_count
        assert pledge["payload"]["lame_duck"] is False
    assert deviations == []


def test_two_mandate_enabled_runs_produce_byte_identical_journals(tmp_path):
    path_a = run_simulation(_config_with_mandate_enabled(tmp_path / "a"), run_id="same-run-id")
    path_b = run_simulation(_config_with_mandate_enabled(tmp_path / "b"), run_id="same-run-id")
    assert path_a.read_bytes() == path_b.read_bytes()


def test_accountability_phase_records_deviation_only_above_the_threshold(tmp_path):
    # The only way to exercise mandate_deviation_recorded's write path before
    # Lot 6 exists: nothing in the tick loop can produce a nonzero deviation
    # on its own, so this perturbs revealed_position directly.
    config = _config_with_mandate_enabled(tmp_path)
    citizens = [
        Citizen(
            citizen_id=0,
            issue_positions=tuple(0.5 for _ in range(config.citizens.issue_count)),
            issue_priorities=tuple(1.0 / config.citizens.issue_count for _ in range(config.citizens.issue_count)),
            blank_threshold=0.5,
            ambition_score=0.5,
            role=Role.ELECTED,
            office=Office.PRESIDENT,
        )
    ]
    top_dim = 0  # uniform priorities -- any dimension is "the" top one
    pledged = tuple(0.5 for _ in range(config.citizens.issue_count))
    below_threshold = list(pledged)
    below_threshold[top_dim] += 0.05
    above_threshold = list(pledged)
    above_threshold[top_dim] += 0.9

    below_path = tmp_path / "below.jsonl"
    with Journal(below_path, run_id="below") as journal:
        citizens[0].pledged_platform = pledged
        citizens[0].revealed_position = tuple(below_threshold)
        _run_accountability_phase(citizens, config, journal, tick=0)
    assert _events(below_path) == []

    above_path = tmp_path / "above.jsonl"
    with Journal(above_path, run_id="above") as journal:
        citizens[0].pledged_platform = pledged
        citizens[0].revealed_position = tuple(above_threshold)
        _run_accountability_phase(citizens, config, journal, tick=0)
    above_events = _events(above_path)
    assert len(above_events) == 1
    assert above_events[0]["event_type"] == "mandate_deviation_recorded"
    assert above_events[0]["citizen_id"] == 0
    assert above_events[0]["payload"]["deviation"] > config.mandate.deviation_log_threshold
    # v6b, production-wiring lot: both scopes carried on the same event.
    assert above_events[0]["payload"]["unified_deviation"] > 0.0


# ── term limits (v4 Lot 2, §6bis.1) ──────────────────────────────────────

def test_term_limited_incumbent_is_not_re_nominated(tmp_path):
    config = dataclasses.replace(
        load_config(), institutions=dataclasses.replace(load_config().institutions, president_term_limit=1)
    )
    term_ticks = config.institutions.president_term_years * config.run.ticks_per_year

    citizen_a = _office_test_citizen(0, 0.1)
    citizen_a.ambition_score = 1.0
    citizen_a.party_affiliation = 0
    citizen_b = _office_test_citizen(1, 0.9)
    citizen_b.ambition_score = 1.0
    citizen_b.party_affiliation = 1
    party_a = Party(party_id=0, platform=(0.1,))
    party_b = Party(party_id=1, platform=(0.9,))
    # Electors sit next to A so A wins the first, contested election clearly.
    electors = [_office_test_citizen(i, 0.1) for i in range(2, 7)]

    with Journal(tmp_path / "run.jsonl", run_id="r") as journal:
        _hold_presidential_election(
            [citizen_a, citizen_b] + electors, [party_a, party_b], config, journal, tick=0, llm_client=None
        )
        assert citizen_a.office == Office.PRESIDENT
        assert citizen_a.mandates_served == 1

        # A has now served their one permitted mandate: excluded from the
        # eligible pool, so B is the only nominee and wins uncontested even
        # though the electorate still sits next to A's platform.
        _hold_presidential_election(
            [citizen_a, citizen_b] + electors, [party_a, party_b], config, journal, tick=term_ticks, llm_client=None
        )

    assert citizen_b.office == Office.PRESIDENT
    assert citizen_b.role == Role.ELECTED
    assert citizen_a.office == Office.NONE
    assert citizen_a.role == Role.ELECTOR
    assert citizen_a.mandates_served == 1


# ── competitive blank voting (v4 Lot 9, §6bis.2) ─────────────────────────

def _blank_config(**institution_overrides) -> PolityConfig:
    config = load_config()
    return dataclasses.replace(
        config,
        institutions=dataclasses.replace(
            config.institutions, blank_vote_competitive=True, **institution_overrides
        ),
    )


def _blank_leaning_citizen(cid, position, blank_threshold=0.0, ambition=1.0, party=None):
    return Citizen(
        citizen_id=cid,
        issue_positions=(position,),
        issue_priorities=(1.0,),
        blank_threshold=blank_threshold,
        ambition_score=ambition,
        party_affiliation=party,
    )


def _config_with_blank_vote_competitive_enabled(output_dir, **overrides) -> PolityConfig:
    config = _config_with_output_dir(output_dir)
    return dataclasses.replace(
        config,
        institutions=dataclasses.replace(config.institutions, blank_vote_competitive=True, **overrides),
    )


def test_default_config_run_emits_no_election_invalidated_events(tmp_path):
    journal_path = run_simulation(_config_with_output_dir(tmp_path), run_id="baseline")
    events = _events(journal_path)
    assert not [e for e in events if e["event_type"] == "election_invalidated"]


def test_two_runs_with_blank_vote_competitive_enabled_produce_byte_identical_journals(tmp_path):
    path_a = run_simulation(_config_with_blank_vote_competitive_enabled(tmp_path / "a"), run_id="same-run-id")
    path_b = run_simulation(_config_with_blank_vote_competitive_enabled(tmp_path / "b"), run_id="same-run-id")
    assert path_a.read_bytes() == path_b.read_bytes()


def _config_with_a_structurally_empty_candidate_field(output_dir, **overrides) -> PolityConfig:
    """president_term_limit=0 makes is_term_limited (accountability.py) true for
    EVERY citizen -- `term_limit is not None and mandates_served >= 0` holds
    before anyone has served anything -- so _declare_nominees's `eligible` list
    is empty by construction, at every tick, for every seed, independently of
    any RNG draw.

    This replaces the mechanism these proofs used to rest on: until ADR-002 was
    closed (2026-08-29) the shipped ambition_threshold of 0.7 emptied the pool
    on its own, and that was a DEFECT being used as a fixture. The shipped
    threshold is now 0.30 and fields ~5 nominees per election, so an empty
    candidate field has to be produced deliberately -- and this way of producing
    it is exact rather than distributional, which the previous one only
    approximately was."""
    config = _config_with_output_dir(output_dir)
    return dataclasses.replace(
        config,
        institutions=dataclasses.replace(config.institutions, president_term_limit=0, **overrides),
    )


def test_a_structurally_empty_candidate_field_really_is_empty(tmp_path):
    # Guards the fixture the two byte-identity proofs below depend on: if
    # president_term_limit=0 ever stopped emptying the field, those proofs would
    # silently degrade into "happens not to trigger this seed" without failing.
    journal_path = run_simulation(_config_with_a_structurally_empty_candidate_field(tmp_path), run_id="empty")
    events = _events(journal_path)
    assert not [e for e in events if e["event_type"] == "candidacy_declared"]
    no_winner = [e for e in events if e["event_type"] == "election_no_winner"]
    assert no_winner
    assert all(e["payload"]["reason"] == "no_candidates" for e in no_winner)


def test_blank_vote_competitive_enabled_but_never_triggered_matches_the_default_journal_byte_for_byte(tmp_path):
    # The load-bearing off-vs-on proof. With an empty candidate field, nominees
    # is always [] and the invalidation check inside `if nominees:` never even
    # runs -- turning the gate on is a true no-op here, not merely "happens not
    # to trigger this seed". Both arms are term-limited identically, so the
    # comparison isolates blank_vote_competitive and nothing else.
    path_off = run_simulation(
        _config_with_a_structurally_empty_candidate_field(tmp_path / "off"), run_id="same-run-id"
    )
    path_on = run_simulation(
        _config_with_a_structurally_empty_candidate_field(tmp_path / "on", blank_vote_competitive=True),
        run_id="same-run-id",
    )
    events_on = _events(path_on)
    assert not [e for e in events_on if e["event_type"] == "election_invalidated"]
    assert not any("attempt" in e["payload"] for e in events_on if e["event_type"] in ("elected", "election_no_winner"))
    assert path_off.read_bytes() == path_on.read_bytes()


def test_election_invalidated_when_blank_share_exceeds_threshold(tmp_path):
    config = _blank_config()
    candidate = _blank_leaning_citizen(0, 0.5, ambition=1.0, party=0)
    party = Party(party_id=0, platform=(0.5,))
    # blank_threshold=0.0, positioned far from the candidate: every elector
    # rejects the candidate outright, so Blank is their top preference.
    electors = [_blank_leaning_citizen(i, 0.0, ambition=0.0) for i in range(1, 8)]

    with Journal(tmp_path / "run.jsonl", run_id="r") as journal:
        result = _hold_presidential_election(
            [candidate] + electors, [party], config, journal, tick=0, llm_client=None
        )

    events = _events(tmp_path / "run.jsonl")
    invalidated = [e for e in events if e["event_type"] == "election_invalidated"]
    assert len(invalidated) == 1
    assert invalidated[0]["payload"]["blank_share"] == pytest.approx(7 / 8)
    assert invalidated[0]["payload"]["threshold"] == 0.5
    assert invalidated[0]["payload"]["attempt"] == 1
    assert result == PendingRerun(attempt=1, next_tick=1, barred_candidate_ids=frozenset({0}))
    assert not [e for e in events if e["event_type"] in ("elected", "election_no_winner")]


def test_election_not_invalidated_when_blank_share_is_below_threshold(tmp_path):
    config = _blank_config()
    candidate = _blank_leaning_citizen(0, 0.5, ambition=1.0, party=0)
    party = Party(party_id=0, platform=(0.5,))
    # blank_threshold=1.0: every elector accepts the (only) candidate.
    electors = [_blank_leaning_citizen(i, 0.0, blank_threshold=1.0, ambition=0.0) for i in range(1, 4)]

    with Journal(tmp_path / "run.jsonl", run_id="r") as journal:
        result = _hold_presidential_election(
            [candidate] + electors, [party], config, journal, tick=0, llm_client=None
        )

    events = _events(tmp_path / "run.jsonl")
    assert not [e for e in events if e["event_type"] == "election_invalidated"]
    assert result is None


def test_election_invalidated_uses_strict_comparison_at_the_exact_threshold(tmp_path):
    config = _blank_config()
    candidate = _blank_leaning_citizen(0, 0.5, ambition=1.0, party=0)
    party = Party(party_id=0, platform=(0.5,))
    # Exactly 2 of 4 cast ballots (candidate's own self-vote + 1 accepting
    # elector are non-blank; 2 rejecting electors are blank) -- blank_share
    # == 0.5 exactly, the shipped threshold. "dépasse" (exceeds) reads as
    # strict >, not >=.
    accepting = _blank_leaning_citizen(1, 0.0, blank_threshold=1.0, ambition=0.0)
    rejecting = [_blank_leaning_citizen(i, 0.0, ambition=0.0) for i in (2, 3)]

    with Journal(tmp_path / "run.jsonl", run_id="r") as journal:
        result = _hold_presidential_election(
            [candidate, accepting] + rejecting, [party], config, journal, tick=0, llm_client=None
        )

    events = _events(tmp_path / "run.jsonl")
    assert not [e for e in events if e["event_type"] == "election_invalidated"]
    assert [e for e in events if e["event_type"] in ("elected", "election_no_winner")]
    assert result is None


def test_forced_attempt_accepts_the_result_even_when_blank_share_still_exceeds_threshold(tmp_path):
    config = _blank_config()  # shipped reelection_max_attempts == 2
    candidate = _blank_leaning_citizen(0, 0.5, ambition=1.0, party=0)
    party = Party(party_id=0, platform=(0.5,))
    electors = [_blank_leaning_citizen(i, 0.0, ambition=0.0) for i in range(1, 8)]
    forced_pending_rerun = PendingRerun(attempt=3, next_tick=5, barred_candidate_ids=frozenset())

    with Journal(tmp_path / "run.jsonl", run_id="r") as journal:
        result = _hold_presidential_election(
            [candidate] + electors, [party], config, journal, tick=5, llm_client=None,
            pending_rerun=forced_pending_rerun,
        )

    events = _events(tmp_path / "run.jsonl")
    assert not [e for e in events if e["event_type"] == "election_invalidated"]
    outcomes = [e for e in events if e["event_type"] in ("elected", "election_no_winner")]
    assert len(outcomes) == 1
    assert outcomes[0]["payload"]["attempt"] == 3
    assert outcomes[0]["payload"]["forced"] == 1
    assert result is None


def test_non_forced_rerun_payload_carries_attempt_but_not_forced(tmp_path):
    config = _blank_config()
    candidate = _blank_leaning_citizen(0, 0.5, ambition=1.0, party=0)
    party = Party(party_id=0, platform=(0.5,))
    electors = [_blank_leaning_citizen(i, 0.0, blank_threshold=1.0, ambition=0.0) for i in range(1, 4)]
    pending_rerun = PendingRerun(attempt=1, next_tick=1, barred_candidate_ids=frozenset())

    with Journal(tmp_path / "run.jsonl", run_id="r") as journal:
        result = _hold_presidential_election(
            [candidate] + electors, [party], config, journal, tick=1, llm_client=None,
            pending_rerun=pending_rerun,
        )

    events = _events(tmp_path / "run.jsonl")
    outcomes = [e for e in events if e["event_type"] in ("elected", "election_no_winner")]
    assert len(outcomes) == 1
    assert outcomes[0]["payload"]["attempt"] == 1
    assert outcomes[0]["payload"]["forced"] == 0
    assert result is None


def test_barred_candidates_are_excluded_from_the_next_partys_nomination(tmp_path):
    config = _blank_config()
    candidate = _blank_leaning_citizen(0, 0.5, ambition=1.0, party=0)
    party = Party(party_id=0, platform=(0.5,))
    electors = [_blank_leaning_citizen(i, 0.0, ambition=0.0) for i in range(1, 8)]

    with Journal(tmp_path / "run.jsonl", run_id="r") as journal:
        pending_rerun = _hold_presidential_election(
            [candidate] + electors, [party], config, journal, tick=0, llm_client=None
        )
        assert pending_rerun is not None and 0 in pending_rerun.barred_candidate_ids

        result = _hold_presidential_election(
            [candidate] + electors, [party], config, journal, tick=1, llm_client=None,
            pending_rerun=pending_rerun,
        )

    events = _events(tmp_path / "run.jsonl")
    declared_at_tick_1 = [e for e in events if e["tick"] == 1 and e["event_type"] == "candidacy_declared"]
    assert declared_at_tick_1 == []
    outcomes_at_tick_1 = [e for e in events if e["tick"] == 1 and e["event_type"] in ("elected", "election_no_winner")]
    assert len(outcomes_at_tick_1) == 1
    assert outcomes_at_tick_1[0]["event_type"] == "election_no_winner"
    assert result is None


def test_barred_candidates_cannot_declare_a_rupture_candidacy(tmp_path):
    # blank_vote_competitive itself is irrelevant to this call --
    # _attempt_rupture_candidacies only reads config.candidacy and the
    # barred_candidate_ids argument directly.
    config = load_config()
    config = dataclasses.replace(
        config,
        candidacy=dataclasses.replace(
            config.candidacy,
            rupture_path_enabled=True,
            rupture_base_probability=1.0,
            rupture_signature_ratio=0.0,
        ),
    )
    citizen = _blank_leaning_citizen(0, 0.5, blank_threshold=1.0, ambition=0.0)
    citizen.role = Role.ELECTOR
    population = [citizen] + [_blank_leaning_citizen(i, 0.5, blank_threshold=1.0, ambition=0.0) for i in range(1, 4)]
    rng = np.random.default_rng(0)

    with Journal(tmp_path / "run.jsonl", run_id="r") as journal:
        _attempt_rupture_candidacies(
            population, config, journal, tick=0, rng=rng, barred_candidate_ids=frozenset({0})
        )

    events = _events(tmp_path / "run.jsonl")
    assert not [e for e in events if e["citizen_id"] == 0]
    assert citizen.role == Role.ELECTOR


def test_barred_from_immediate_rerun_false_allows_the_same_candidates_to_restand(tmp_path):
    config = _blank_config(barred_from_immediate_rerun=False)
    candidate = _blank_leaning_citizen(0, 0.5, ambition=1.0, party=0)
    party = Party(party_id=0, platform=(0.5,))
    electors = [_blank_leaning_citizen(i, 0.0, ambition=0.0) for i in range(1, 8)]

    with Journal(tmp_path / "run.jsonl", run_id="r") as journal:
        result = _hold_presidential_election(
            [candidate] + electors, [party], config, journal, tick=0, llm_client=None
        )

    events = _events(tmp_path / "run.jsonl")
    invalidated = [e for e in events if e["event_type"] == "election_invalidated"]
    assert len(invalidated) == 1
    assert invalidated[0]["payload"]["candidate_ids"] == [0]
    assert result == PendingRerun(attempt=1, next_tick=1, barred_candidate_ids=frozenset())


def test_barred_candidate_ids_accumulate_across_repeated_invalidations(tmp_path):
    config = _blank_config()
    candidate_a = _blank_leaning_citizen(0, 0.5, ambition=1.0, party=0)
    candidate_b = _blank_leaning_citizen(1, 0.5, ambition=1.0, party=1)
    party_a = Party(party_id=0, platform=(0.5,))
    party_b = Party(party_id=1, platform=(0.5,))
    electors = [_blank_leaning_citizen(i, 0.0, ambition=0.0) for i in range(2, 9)]

    with Journal(tmp_path / "run.jsonl", run_id="r") as journal:
        first = _hold_presidential_election(
            [candidate_a, candidate_b] + electors, [party_a], config, journal, tick=0, llm_client=None
        )
        assert first is not None and first.barred_candidate_ids == frozenset({0})

        second = _hold_presidential_election(
            [candidate_a, candidate_b] + electors, [party_b], config, journal, tick=1, llm_client=None,
            pending_rerun=first,
        )

    assert second is not None
    assert second.attempt == 2
    assert second.barred_candidate_ids == frozenset({0, 1})


def test_pending_rerun_resets_after_a_real_winner_is_elected(tmp_path):
    config = _blank_config()
    candidate_a = _blank_leaning_citizen(0, 0.5, ambition=1.0, party=0)
    candidate_b = _blank_leaning_citizen(1, 0.0, ambition=1.0, party=1)
    party_a = Party(party_id=0, platform=(0.5,))
    party_b = Party(party_id=1, platform=(0.0,))
    # blank_threshold=0.0, positioned at 0.0: reject A (distance 0.5), accept B (distance 0).
    electors = [_blank_leaning_citizen(i, 0.0, ambition=0.0) for i in range(2, 9)]

    with Journal(tmp_path / "run.jsonl", run_id="r") as journal:
        first = _hold_presidential_election(
            [candidate_a, candidate_b] + electors, [party_a], config, journal, tick=0, llm_client=None
        )
        assert first is not None

        second = _hold_presidential_election(
            [candidate_a, candidate_b] + electors, [party_b], config, journal, tick=1, llm_client=None,
            pending_rerun=first,
        )

    assert second is None
    assert candidate_b.office == Office.PRESIDENT


def test_zero_nominees_after_barring_resolves_as_election_no_winner_and_clears_pending_rerun(tmp_path):
    config = _blank_config()
    candidate = _blank_leaning_citizen(0, 0.5, ambition=1.0, party=0)
    party = Party(party_id=0, platform=(0.5,))
    electors = [_blank_leaning_citizen(i, 0.0, ambition=0.0) for i in range(1, 8)]

    with Journal(tmp_path / "run.jsonl", run_id="r") as journal:
        first = _hold_presidential_election(
            [candidate] + electors, [party], config, journal, tick=0, llm_client=None
        )
        assert first is not None

        second = _hold_presidential_election(
            [candidate] + electors, [party], config, journal, tick=1, llm_client=None,
            pending_rerun=first,
        )

    events = _events(tmp_path / "run.jsonl")
    outcomes_at_tick_1 = [e for e in events if e["tick"] == 1 and e["event_type"] in ("elected", "election_no_winner")]
    assert len(outcomes_at_tick_1) == 1
    assert outcomes_at_tick_1[0]["event_type"] == "election_no_winner"
    assert second is None


def test_election_invalidated_payload_shape(tmp_path):
    config = _blank_config()
    candidate = _blank_leaning_citizen(0, 0.5, ambition=1.0, party=0)
    party = Party(party_id=0, platform=(0.5,))
    electors = [_blank_leaning_citizen(i, 0.0, ambition=0.0) for i in range(1, 8)]

    with Journal(tmp_path / "run.jsonl", run_id="r") as journal:
        _hold_presidential_election([candidate] + electors, [party], config, journal, tick=0, llm_client=None)

    events = _events(tmp_path / "run.jsonl")
    invalidated = [e for e in events if e["event_type"] == "election_invalidated"]
    assert len(invalidated) == 1
    assert set(invalidated[0]["payload"].keys()) == {
        "office", "blank_share", "threshold", "attempt", "candidate_ids", "barred_candidate_ids", "next_attempt_tick",
    }
    assert invalidated[0]["citizen_id"] is None


def _config_with_blank_vote_competitive_lifecycle(output_dir) -> PolityConfig:
    config = _config_with_output_dir(output_dir)
    return dataclasses.replace(
        config,
        institutions=dataclasses.replace(
            config.institutions, blank_vote_competitive=True, reelection_delay_ticks=1, reelection_max_attempts=2,
        ),
        citizens=dataclasses.replace(config.citizens, blank_threshold_dist="beta(1,50)"),
        candidacy=dataclasses.replace(config.candidacy, ambition_threshold=0.0),
        run=dataclasses.replace(config.run, duration_years=8),
    )


def test_full_invalidate_rerun_bar_eventually_resolve_lifecycle(tmp_path):
    # Empirically confirmed (not just reasoned about) against this exact
    # config: at seed=42, tick 0's presidential election invalidates twice
    # (attempts 1, 2) then forces a result at attempt 3 -- reelection_delay_ticks=1
    # means each rerun lands exactly one tick after the last, not at the
    # next regular calendar slot (16 ticks away).
    journal_path = run_simulation(_config_with_blank_vote_competitive_lifecycle(tmp_path), run_id="lifecycle")
    events = _events(journal_path)
    invalidated = [e for e in events if e["event_type"] == "election_invalidated" and e["tick"] < 16]
    assert len(invalidated) >= 1
    for e in invalidated:
        assert e["payload"]["next_attempt_tick"] == e["tick"] + 1

    forced = [
        e for e in events
        if e["event_type"] in ("elected", "election_no_winner") and e["tick"] < 16 and e["payload"].get("forced") == 1
    ]
    assert len(forced) == 1

    # No barred candidate re-declares at the very next tick within this
    # cycle -- the per-cycle non-reappearance property, checked end to end
    # (the direct-call tests above pin the same property in isolation).
    for e in invalidated:
        barred_at_this_point = set(e["payload"]["barred_candidate_ids"])
        redeclared = [
            d for d in events
            if d["event_type"] == "candidacy_declared"
            and d["tick"] == e["tick"] + 1
            and d["citizen_id"] in barred_at_this_point
        ]
        assert redeclared == []


def test_legislative_elections_continue_on_schedule_while_a_presidential_rerun_is_pending(tmp_path):
    config = _config_with_blank_vote_competitive_lifecycle(tmp_path)
    journal_path = run_simulation(config, run_id="lifecycle-legislative")
    events = _events(journal_path)
    legislative = [e for e in events if e["event_type"] == "legislative_result"]
    term_ticks = config.institutions.assembly_term_years * config.run.ticks_per_year
    offset_ticks = config.institutions.assembly_offset_years * config.run.ticks_per_year
    assert [e["tick"] for e in legislative] == [offset_ticks + term_ticks * i for i in range(len(legislative))]
    assert len(legislative) > 0


def test_barred_candidate_ids_do_not_leak_into_a_later_unrelated_cycle(tmp_path):
    config = _blank_config()
    candidate_a = _blank_leaning_citizen(0, 0.5, ambition=1.0, party=0)
    party_a = Party(party_id=0, platform=(0.5,))
    electors = [_blank_leaning_citizen(i, 0.0, ambition=0.0) for i in range(2, 9)]

    with Journal(tmp_path / "run.jsonl", run_id="r") as journal:
        first_cycle = _hold_presidential_election(
            [candidate_a] + electors, [party_a], config, journal, tick=0, llm_client=None
        )
        assert first_cycle is not None and first_cycle.barred_candidate_ids == frozenset({0})

        # Candidate B, unrelated to A's cycle, stands alone at a later tick
        # (a fresh call with pending_rerun=None -- the first cycle already
        # resolved to election_no_winner once A was barred and nobody else
        # stood, so the SECOND election below starts a wholly new cycle).
        resolved = _hold_presidential_election(
            [candidate_a] + electors, [party_a], config, journal, tick=1, llm_client=None,
            pending_rerun=first_cycle,
        )
        assert resolved is None

        candidate_b = _blank_leaning_citizen(1, 0.5, ambition=1.0, party=1)
        party_b = Party(party_id=1, platform=(0.5,))
        second_cycle = _hold_presidential_election(
            [candidate_a, candidate_b] + electors, [party_b], config, journal, tick=2, llm_client=None
        )

    assert second_cycle is not None
    assert second_cycle.barred_candidate_ids == frozenset({1})
    assert 0 not in second_cycle.barred_candidate_ids


# ── legitimacy (v4 Lot 3) ─────────────────────────────────────────────────

def _config_with_legitimacy_enabled(output_dir, **overrides) -> PolityConfig:
    config = _config_with_output_dir(output_dir)
    legitimacy = dataclasses.replace(config.legitimacy, enabled=True, **overrides)
    return dataclasses.replace(config, legitimacy=legitimacy)


def _config_with_legitimacy_enabled_and_guaranteed_winners(output_dir, **overrides) -> PolityConfig:
    # Same rationale as mandate's own helper: ambition_threshold=0.7 never
    # produces a presidential winner at seed=42.
    config = _config_with_legitimacy_enabled(output_dir, **overrides)
    return dataclasses.replace(config, candidacy=dataclasses.replace(config.candidacy, ambition_threshold=0.0))


def test_default_config_run_emits_no_legitimacy_events(tmp_path):
    journal_path = run_simulation(_config_with_output_dir(tmp_path), run_id="baseline")
    events = _events(journal_path)
    assert not [e for e in events if e["event_type"] in ("legitimacy_updated", "recalled")]


def test_legitimacy_is_flat_at_mandate_strength_for_the_entire_run(tmp_path):
    # §7bis.6's central claim, now a passing test: with no citizen pressure
    # (Lots 4-5 not built yet) and recall_floor=0.0 isolating this from the
    # recall mechanism, L(t) == m at every single tick, every term.
    config = _config_with_legitimacy_enabled_and_guaranteed_winners(tmp_path, recall_floor=0.0)
    # Pinned to uniform regardless of citizens.position_dist's shipped
    # default (plan-distribution-positions-seeds.md, Phase 3): m=0.51 below
    # was computed for this seed specifically under uniform.
    config = dataclasses.replace(config, citizens=dataclasses.replace(config.citizens, position_dist="uniform"))
    journal_path = run_simulation(config, run_id="legitimacy-flat")
    events = _events(journal_path)
    updates = [e for e in events if e["event_type"] == "legitimacy_updated"]
    assert not [e for e in events if e["event_type"] == "recalled"]
    # Exactly one update per tick for the whole run -- elections hand off
    # the office with zero vacancy gap, so there's no term-boundary
    # double-count or undercount to account for (the last term is simply
    # truncated by the run's own end, not by anything this test predicts).
    assert len(updates) == config.run.duration_years * config.run.ticks_per_year + 1
    for update in updates:
        assert update["payload"]["mandate_strength"] == pytest.approx(0.51)
        assert update["payload"]["legitimacy"] == pytest.approx(update["payload"]["mandate_strength"])


@pytest.mark.parametrize(
    "method,expected_winner_cid,expected_m",
    [
        ("two_round", 62, 0.51),
        ("irv", 62, 0.51),
        ("borda", 48, 0.56),
        ("schulze", 48, 0.56),
    ],
)
def test_mandate_strength_is_correct_and_method_agnostic(tmp_path, method, expected_winner_cid, expected_m):
    config = _config_with_legitimacy_enabled_and_guaranteed_winners(tmp_path)
    # Pinned to uniform (see the sibling "flat at m" test above): the
    # expected winners/m above were computed for this seed under uniform,
    # independent of citizens.position_dist's shipped default.
    config = dataclasses.replace(config, citizens=dataclasses.replace(config.citizens, position_dist="uniform"))
    config = dataclasses.replace(config, institutions=dataclasses.replace(config.institutions, presidential_method=method))
    citizens = generate_population(config.citizens, config.run.population_size, config.run.seed)
    parties = initialize_parties(citizens, config.parties.initial_count, config.run.seed)
    for citizen in citizens:
        citizen.party_affiliation = assign_party_affiliation(citizen, parties)

    with Journal(tmp_path / "run.jsonl", run_id="m") as journal:
        _hold_presidential_election(citizens, parties, config, journal, tick=0, llm_client=None)

    winner = next(c for c in citizens if c.office == Office.PRESIDENT)
    assert winner.citizen_id == expected_winner_cid
    assert winner.mandate_strength == pytest.approx(expected_m)
    assert winner.legitimacy_capital == pytest.approx(expected_m)


def test_two_legitimacy_enabled_runs_produce_byte_identical_journals(tmp_path):
    path_a = run_simulation(_config_with_legitimacy_enabled(tmp_path / "a"), run_id="same-run-id")
    path_b = run_simulation(_config_with_legitimacy_enabled(tmp_path / "b"), run_id="same-run-id")
    assert path_a.read_bytes() == path_b.read_bytes()


def test_legitimacy_enabled_without_mandate_enabled_emits_no_deviation_events(tmp_path):
    # Independent toggles: legitimacy.enabled does not imply mandate.enabled.
    config = _config_with_legitimacy_enabled_and_guaranteed_winners(tmp_path)
    journal_path = run_simulation(config, run_id="legitimacy-only")
    events = _events(journal_path)
    assert [e for e in events if e["event_type"] == "legitimacy_updated"]
    assert not [e for e in events if e["event_type"] == "mandate_deviation_recorded"]


def _legitimacy_test_citizen(cid, legitimacy_capital, mandate_strength_value):
    return Citizen(
        citizen_id=cid,
        issue_positions=(0.5,),
        issue_priorities=(1.0,),
        blank_threshold=0.5,
        ambition_score=0.5,
        role=Role.ELECTED,
        office=Office.PRESIDENT,
        legitimacy_capital=legitimacy_capital,
        mandate_strength=mandate_strength_value,
    )


def test_recall_fires_when_legitimacy_crosses_the_floor_and_vacates_the_office(tmp_path):
    # Fixed point at m=0.1, below the shipped recall_floor (0.2): stays
    # below every tick, so the floor fires on the very first call.
    config = _config_with_legitimacy_enabled(tmp_path)
    citizens = [_legitimacy_test_citizen(0, legitimacy_capital=0.1, mandate_strength_value=0.1)]

    journal_path = tmp_path / "recall.jsonl"
    with Journal(journal_path, run_id="recall") as journal:
        _run_accountability_phase(citizens, config, journal, tick=0)
    events = _events(journal_path)
    assert [e["event_type"] for e in events] == ["legitimacy_updated", "recalled"]
    assert events[0]["payload"]["legitimacy"] == pytest.approx(0.1)
    assert events[1]["payload"]["legitimacy"] == pytest.approx(0.1)
    assert events[1]["payload"]["recall_floor"] == config.legitimacy.recall_floor

    holder = citizens[0]
    assert holder.role == Role.ELECTOR
    assert holder.office == Office.NONE
    assert holder.term_end_tick is None
    # Not reset -- post-mortem legibility, same precedent as Lot 2's
    # pledged_platform/revealed_position on a term-end vacate.
    assert holder.legitimacy_capital == pytest.approx(0.1)
    assert holder.mandate_strength == pytest.approx(0.1)

    # Office is now vacant: a second call is a no-op.
    with Journal(tmp_path / "recall2.jsonl", run_id="recall2") as journal:
        _run_accountability_phase(citizens, config, journal, tick=1)
    assert _events(tmp_path / "recall2.jsonl") == []


def test_same_tick_election_recall_is_reachable(tmp_path):
    # A fixed, externally-legible floor means exactly this can happen: a
    # winner with m below the floor is recalled the tick they're elected.
    config = _config_with_legitimacy_enabled_and_guaranteed_winners(tmp_path, recall_floor=0.99)
    journal_path = run_simulation(config, run_id="same-tick-recall")
    events = _events(journal_path)
    elected_ticks = [e["tick"] for e in events if e["event_type"] == "elected"]
    recalled_ticks = [e["tick"] for e in events if e["event_type"] == "recalled"]
    assert elected_ticks
    assert elected_ticks == recalled_ticks


def test_passive_erosion_applies_without_mandate_tracking_enabled(tmp_path):
    # Guards the gating design's own silent-zero gap: passive_erosion_weight
    # must still erode L even when mandate.enabled is False, since
    # measurement is free and only the mandate_deviation_recorded *write*
    # is gated on mandate.enabled.
    config = _config_with_legitimacy_enabled(tmp_path, passive_erosion_weight=0.5)
    assert config.mandate.enabled is False
    citizen = _legitimacy_test_citizen(0, legitimacy_capital=0.5, mandate_strength_value=0.5)
    citizen.pledged_platform = (0.0,)
    citizen.revealed_position = (1.0,)  # deviation = 1.0

    journal_path = tmp_path / "passive.jsonl"
    with Journal(journal_path, run_id="passive") as journal:
        _run_accountability_phase([citizen], config, journal, tick=0)
    events = _events(journal_path)
    update = next(e for e in events if e["event_type"] == "legitimacy_updated")
    assert update["payload"]["ecart"] == pytest.approx(0.5 * 1.0)
    assert not [e for e in events if e["event_type"] == "mandate_deviation_recorded"]


# ── awakening / mobilization (v4 Lot 4) ──────────────────────────────────

def _config_with_awakening_enabled(output_dir, **overrides) -> PolityConfig:
    config = _config_with_legitimacy_enabled(output_dir)
    # Pinned to uniform regardless of citizens.position_dist's shipped
    # default (plan-distribution-positions-seeds.md, Phase 3): every test
    # built on this helper (mobilization, petition lifecycle, awakening-gate
    # consultation rate) relies on tuned base_threshold_dist/signature
    # thresholds calibrated against uniform's self_gap distribution
    # specifically (scripts/awakening_calibration_results.md,
    # scripts/petition_calibration_results.md) -- those tunings don't
    # transfer to a different position distribution's own self_gap shape
    # (e.g. factor_structure's higher mean acceptability consults fewer
    # citizens at the same base_threshold_dist).
    config = dataclasses.replace(config, citizens=dataclasses.replace(config.citizens, position_dist="uniform"))
    return dataclasses.replace(config, awakening=dataclasses.replace(config.awakening, enabled=True, **overrides))


def _config_with_awakening_enabled_and_guaranteed_winners(output_dir, **overrides) -> PolityConfig:
    config = _config_with_awakening_enabled(output_dir, **overrides)
    return dataclasses.replace(config, candidacy=dataclasses.replace(config.candidacy, ambition_threshold=0.0))


def _config_with_mobilization_enabled(output_dir, base_threshold_dist=None):
    config = _config_with_awakening_enabled_and_guaranteed_winners(output_dir)
    config = dataclasses.replace(
        config,
        pressure_menu=dataclasses.replace(config.pressure_menu, electoral_only=False, mobilization_enabled=True),
        street_pressure=dataclasses.replace(config.street_pressure, enabled=True),
    )
    if base_threshold_dist is not None:
        config = dataclasses.replace(config, citizens=dataclasses.replace(config.citizens, base_threshold_dist=base_threshold_dist))
    return config


def test_default_config_run_emits_no_pressure_action_events(tmp_path):
    journal_path = run_simulation(_config_with_output_dir(tmp_path), run_id="baseline")
    events = _events(journal_path)
    assert not [e for e in events if e["event_type"] == "pressure_action"]


def test_two_awakening_enabled_runs_produce_byte_identical_journals(tmp_path):
    path_a = run_simulation(_config_with_awakening_enabled(tmp_path / "a"), run_id="same-run-id")
    path_b = run_simulation(_config_with_awakening_enabled(tmp_path / "b"), run_id="same-run-id")
    assert path_a.read_bytes() == path_b.read_bytes()


def test_two_mobilization_enabled_runs_produce_byte_identical_journals(tmp_path):
    path_a = run_simulation(_config_with_mobilization_enabled(tmp_path / "a"), run_id="same-run-id")
    path_b = run_simulation(_config_with_mobilization_enabled(tmp_path / "b"), run_id="same-run-id")
    assert path_a.read_bytes() == path_b.read_bytes()


def test_electoral_only_control_arm_is_flat_legitimacy_and_only_nothing_or_wait(tmp_path):
    # The control arm this whole palier compares against: awakening AND
    # legitimacy both on, but electoral_only leaves no real lever to pull.
    config = _config_with_awakening_enabled_and_guaranteed_winners(tmp_path)
    journal_path = run_simulation(config, run_id="control-arm")
    events = _events(journal_path)

    pressure_events = [e for e in events if e["event_type"] == "pressure_action"]
    assert pressure_events
    acts = {e["payload"]["act"] for e in pressure_events}
    assert acts == {0, 4}  # both members of the DoD's stated set actually occur

    updates = [e for e in events if e["event_type"] == "legitimacy_updated"]
    assert updates
    for update in updates:
        assert update["payload"]["legitimacy"] == pytest.approx(update["payload"]["mandate_strength"])
    assert not [e for e in events if e["event_type"] == "recalled"]


def test_mobilization_moves_and_recovers_legitimacy(tmp_path):
    # A tuned (not shipped) base_threshold_dist so L dips without hitting
    # the recall floor, so a "recovery" is actually observable -- the
    # shipped beta(3,5) recalls on essentially the first tick of every term
    # (see scripts/awakening_calibration_results.md).
    config = _config_with_mobilization_enabled(tmp_path, base_threshold_dist="beta(7,3)")
    journal_path = run_simulation(config, run_id="mobilization")
    events = _events(journal_path)
    assert not [e for e in events if e["event_type"] == "recalled"]

    term_ticks = config.institutions.president_term_years * config.run.ticks_per_year
    updates = [e for e in events if e["event_type"] == "legitimacy_updated"]
    first_term = [e for e in updates if e["tick"] < term_ticks]
    legitimacies = [e["payload"]["legitimacy"] for e in first_term]

    assert min(legitimacies) < legitimacies[0]  # L actually moves below m
    min_index = legitimacies.index(min(legitimacies))
    assert legitimacies[-1] > legitimacies[min_index]  # and recovers before the next election


def test_pressure_action_journals_act_zero_when_it_occurs(tmp_path):
    # §16.3: "y compris act=0 (inaction)" -- not just theoretically legal.
    config = _config_with_awakening_enabled_and_guaranteed_winners(tmp_path)
    journal_path = run_simulation(config, run_id="act-zero")
    events = _events(journal_path)
    assert any(e["event_type"] == "pressure_action" and e["payload"]["act"] == 0 for e in events)


def test_pressure_action_events_precede_legitimacy_updated_and_are_ascending_within_a_tick(tmp_path):
    config = _config_with_awakening_enabled_and_guaranteed_winners(tmp_path)
    journal_path = run_simulation(config, run_id="ordering")
    events = _events(journal_path)
    for tick in {e["tick"] for e in events}:
        tick_events = [e for e in events if e["tick"] == tick]
        types = [e["event_type"] for e in tick_events]
        pressure_indices = [i for i, t in enumerate(types) if t == "pressure_action"]
        legitimacy_indices = [i for i, t in enumerate(types) if t == "legitimacy_updated"]
        if pressure_indices and legitimacy_indices:
            assert max(pressure_indices) < min(legitimacy_indices)
        cids = [tick_events[i]["citizen_id"] for i in pressure_indices]
        assert cids == sorted(cids)


def test_no_pressure_action_events_while_the_presidency_is_vacant(tmp_path):
    # president_term_limit=0 keeps the candidate field empty for the whole run
    # (see _config_with_a_structurally_empty_candidate_field), so the presidency
    # never fills. Before ADR-002 was closed this vacancy came for free from the
    # shipped ambition_threshold of 0.7 -- i.e. from the defect, not from
    # anything this test was asserting.
    config = dataclasses.replace(
        _config_with_awakening_enabled(tmp_path),
        institutions=dataclasses.replace(load_config().institutions, president_term_limit=0),
    )
    journal_path = run_simulation(config, run_id="vacant")
    events = _events(journal_path)
    assert not [e for e in events if e["event_type"] == "elected"]
    assert not [e for e in events if e["event_type"] == "pressure_action"]


def test_reelected_president_street_pressure_resets_at_the_new_term(tmp_path):
    config = load_config()
    config = dataclasses.replace(config, street_pressure=dataclasses.replace(config.street_pressure, enabled=True))
    term_ticks = config.institutions.president_term_years * config.run.ticks_per_year

    citizen_a = _office_test_citizen(0, 0.1)
    citizen_a.ambition_score = 1.0
    citizen_a.party_affiliation = 0
    party = Party(party_id=0, platform=(0.1,))
    electors = [_office_test_citizen(i, 0.5) for i in range(1, 6)]

    with Journal(tmp_path / "run.jsonl", run_id="r") as journal:
        _hold_presidential_election([citizen_a] + electors, [party], config, journal, tick=0, llm_client=None)
        citizen_a.street_pressure = 0.75  # simulate pressure accumulated during the term

        _hold_presidential_election(
            [citizen_a] + electors, [party], config, journal, tick=term_ticks, llm_client=None
        )

    assert citizen_a.office == Office.PRESIDENT
    assert citizen_a.street_pressure == 0.0


# ── petition + confidence vote (v4 Lot 5) ─────────────────────────────────

def _config_with_petition_enabled(output_dir, base_threshold_dist=None, **petition_overrides) -> PolityConfig:
    config = _config_with_awakening_enabled_and_guaranteed_winners(output_dir)
    config = dataclasses.replace(
        config,
        pressure_menu=dataclasses.replace(config.pressure_menu, electoral_only=False, petition_enabled=True),
        petition=dataclasses.replace(config.petition, enabled=True, **petition_overrides),
    )
    if base_threshold_dist is not None:
        config = dataclasses.replace(config, citizens=dataclasses.replace(config.citizens, base_threshold_dist=base_threshold_dist))
    return config


def _config_with_full_menu_enabled(output_dir, base_threshold_dist=None) -> PolityConfig:
    config = _config_with_petition_enabled(output_dir, base_threshold_dist=base_threshold_dist)
    return dataclasses.replace(
        config,
        pressure_menu=dataclasses.replace(config.pressure_menu, mobilization_enabled=True),
        street_pressure=dataclasses.replace(config.street_pressure, enabled=True),
    )


def test_default_config_run_emits_no_petition_events(tmp_path):
    journal_path = run_simulation(_config_with_output_dir(tmp_path), run_id="baseline")
    events = _events(journal_path)
    assert not [e for e in events if e["event_type"] in _PETITION_LIFECYCLE_EVENT_TYPES]
    # No recalled event carries a trigger key under the shipped default --
    # legitimacy is disabled entirely, so no recalled event occurs at all.
    assert not [e for e in events if e["event_type"] == "recalled"]


def test_two_petition_enabled_runs_produce_byte_identical_journals(tmp_path):
    path_a = run_simulation(_config_with_petition_enabled(tmp_path / "a"), run_id="same-run-id")
    path_b = run_simulation(_config_with_petition_enabled(tmp_path / "b"), run_id="same-run-id")
    assert path_a.read_bytes() == path_b.read_bytes()


def test_two_full_menu_runs_produce_byte_identical_journals(tmp_path):
    path_a = run_simulation(_config_with_full_menu_enabled(tmp_path / "a"), run_id="same-run-id")
    path_b = run_simulation(_config_with_full_menu_enabled(tmp_path / "b"), run_id="same-run-id")
    assert path_a.read_bytes() == path_b.read_bytes()


def test_petition_only_run_journals_a_complete_petition_lifecycle(tmp_path):
    # Headline DoD: the full §7bis.4a lifecycle actually occurs in a
    # petition-only run, not just as unit-tested primitives.
    config = _config_with_petition_enabled(tmp_path)
    journal_path = run_simulation(config, run_id="petition-lifecycle")
    events = _events(journal_path)

    assert [e for e in events if e["event_type"] == "petition_launched"]
    assert [e for e in events if e["event_type"] == "petition_signed"]
    assert [e for e in events if e["event_type"] == "confidence_vote_triggered"]
    assert [e for e in events if e["event_type"] == "confidence_vote_result"]

    # Walk the journal reconstructing petition "epochs": launch resets the
    # signature count to 1, each sign increments it by exactly 1, and a
    # resolution (trigger, expiry, OR a floor recall that overtakes an
    # unresolved petition -- Lot 4's own predicted dynamic: w_pet's
    # amplification can cross the floor before a petition's own threshold
    # or lifespan resolves it, orphaning it without a closing petition
    # event of its own) clears it -- no two petitions ever overlap
    # (concurrent_allowed is TRANCHÉ false).
    current_signatures = None
    for e in events:
        t = e["event_type"]
        if t == "petition_launched":
            assert current_signatures is None
            current_signatures = e["payload"]["signatures"]
            assert current_signatures == 1
        elif t == "petition_signed":
            assert current_signatures is not None
            assert e["payload"]["signatures"] == current_signatures + 1
            current_signatures = e["payload"]["signatures"]
        elif t in ("confidence_vote_triggered", "petition_expired", "recalled"):
            current_signatures = None

    # Every confidence_vote_triggered is immediately followed by its own
    # confidence_vote_result -- never short-circuited, never deferred.
    for i, e in enumerate(events):
        if e["event_type"] == "confidence_vote_triggered":
            assert events[i + 1]["event_type"] == "confidence_vote_result"


def test_petition_expires_when_its_threshold_is_unreachable(tmp_path):
    # signature_threshold > 1.0 is structurally unreachable (signed_ratio's
    # numerator can never exceed its denominator) -- a tuned config, not a
    # reading of the shipped default (Lot 4's own precedent). base_threshold_dist
    # is ALSO tuned gentler (Lot 4's own beta(7,3), which avoids floor-crashing
    # every term) so a petition survives long enough to actually reach its own
    # lifespan instead of being orphaned by a floor recall first.
    config = _config_with_petition_enabled(tmp_path, base_threshold_dist="beta(7,3)", signature_threshold=1.5)
    journal_path = run_simulation(config, run_id="petition-expiry")
    events = _events(journal_path)
    assert not [e for e in events if e["event_type"] == "confidence_vote_triggered"]
    launched = [e for e in events if e["event_type"] == "petition_launched"]
    expired = [e for e in events if e["event_type"] == "petition_expired"]
    assert launched
    assert expired
    for e in expired:
        matching_launch = next(le for le in launched if le["payload"]["expires_at_tick"] == e["tick"])
        assert e["payload"]["opened_at_tick"] == matching_launch["tick"]


def test_petition_events_follow_their_own_pressure_action_within_a_tick(tmp_path):
    config = _config_with_petition_enabled(tmp_path)
    journal_path = run_simulation(config, run_id="petition-ordering")
    events = _events(journal_path)
    for tick in {e["tick"] for e in events}:
        tick_events = [e for e in events if e["tick"] == tick]
        for i, e in enumerate(tick_events):
            if e["event_type"] in ("petition_launched", "petition_signed"):
                assert i > 0
                prev = tick_events[i - 1]
                assert prev["event_type"] == "pressure_action"
                assert prev["citizen_id"] == e["citizen_id"]


def test_petition_threshold_uses_signatures_gathered_this_same_tick(tmp_path):
    # Direct call: population_size=2 so the launcher's own seed signature
    # alone already clears signature_threshold on the launch tick itself.
    config = _config_with_legitimacy_enabled(tmp_path)
    config = dataclasses.replace(
        config,
        run=dataclasses.replace(config.run, population_size=2),
        awakening=dataclasses.replace(config.awakening, enabled=True, modulation_amplitude=0.0),
        pressure_menu=dataclasses.replace(config.pressure_menu, electoral_only=False, petition_enabled=True),
        petition=dataclasses.replace(config.petition, enabled=True, signature_threshold=0.4),
    )
    holder = _legitimacy_test_citizen(0, legitimacy_capital=0.5, mandate_strength_value=0.5)
    holder.revealed_position = (0.5,)
    launcher = Citizen(
        citizen_id=1, issue_positions=(0.0,), issue_priorities=(1.0,), blank_threshold=0.0,
        ambition_score=0.5, base_threshold=0.0,
    )
    journal_path = tmp_path / "same-tick.jsonl"
    with Journal(journal_path, run_id="same-tick") as journal:
        _run_accountability_phase([holder, launcher], config, journal, tick=0)
    events = _events(journal_path)
    launched = next(e for e in events if e["event_type"] == "petition_launched")
    triggered = next(e for e in events if e["event_type"] == "confidence_vote_triggered")
    assert launched["tick"] == triggered["tick"] == 0
    assert triggered["payload"]["opened_at_tick"] == 0


def test_petition_pressure_enters_ecart_on_the_same_tick_as_its_signatures(tmp_path):
    config = _config_with_legitimacy_enabled(tmp_path)
    config = dataclasses.replace(
        config,
        run=dataclasses.replace(config.run, population_size=2),
        awakening=dataclasses.replace(config.awakening, enabled=True, modulation_amplitude=0.0),
        pressure_menu=dataclasses.replace(config.pressure_menu, electoral_only=False, petition_enabled=True),
        petition=dataclasses.replace(config.petition, enabled=True, signature_threshold=0.99),
    )
    holder = _legitimacy_test_citizen(0, legitimacy_capital=0.5, mandate_strength_value=0.5)
    holder.revealed_position = (0.5,)
    launcher = Citizen(
        citizen_id=1, issue_positions=(0.0,), issue_priorities=(1.0,), blank_threshold=0.0,
        ambition_score=0.5, base_threshold=0.0,
    )
    journal_path = tmp_path / "ecart.jsonl"
    with Journal(journal_path, run_id="ecart") as journal:
        _run_accountability_phase([holder, launcher], config, journal, tick=0)
    events = _events(journal_path)
    update = next(e for e in events if e["event_type"] == "legitimacy_updated")
    expected = config.petition.weight_in_ecart * 0.5 + config.street_pressure.weight_in_ecart * 0.0
    assert update["payload"]["ecart"] == pytest.approx(expected)


def test_the_hard_floor_beats_the_petition_on_a_same_tick_collision(tmp_path):
    config = _config_with_legitimacy_enabled(tmp_path)
    config = dataclasses.replace(
        config,
        run=dataclasses.replace(config.run, population_size=4),
        petition=dataclasses.replace(config.petition, enabled=True),
    )
    # Fixed point at m=0.1, below the shipped recall_floor -- the floor
    # fires regardless of the petition's own ecart contribution.
    holder = _legitimacy_test_citizen(0, legitimacy_capital=0.1, mandate_strength_value=0.1)
    holder.revealed_position = (0.5,)
    holder.petition_open_since_tick = 0
    holder.petition_signers = frozenset({1, 2, 3})  # 3/4 = 0.75 >= signature_threshold (0.25)
    voters = [
        Citizen(citizen_id=i, issue_positions=(0.0,), issue_priorities=(1.0,), blank_threshold=0.0, ambition_score=0.5)
        for i in (1, 2, 3)
    ]  # each sits 0.5 away from holder.revealed_position, beyond their own 0.0 tolerance -> votes remove

    journal_path = tmp_path / "collision.jsonl"
    with Journal(journal_path, run_id="collision") as journal:
        _run_accountability_phase([holder] + voters, config, journal, tick=5)

    events = _events(journal_path)
    assert [e["event_type"] for e in events] == [
        "legitimacy_updated", "confidence_vote_triggered", "confidence_vote_result", "recalled",
    ]
    # Anti-short-circuit: the confidence vote still ran and journaled in
    # full even though the floor is what ultimately wins the attribution.
    assert events[2]["payload"]["retained"] is False
    assert events[3]["payload"]["trigger"] == "legitimacy_floor"

    assert holder.role == Role.ELECTOR
    assert holder.office == Office.NONE
    assert holder.petition_open_since_tick is None
    assert holder.petition_cooldown_until_tick == 5 + config.petition.cooldown_ticks


def test_a_lost_confidence_vote_recalls_and_vacates_the_office(tmp_path):
    config = _config_with_legitimacy_enabled(tmp_path, recall_floor=0.0)
    config = dataclasses.replace(
        config,
        run=dataclasses.replace(config.run, population_size=4),
        petition=dataclasses.replace(config.petition, enabled=True),
    )
    holder = _legitimacy_test_citizen(0, legitimacy_capital=0.9, mandate_strength_value=0.9)
    holder.revealed_position = (0.5,)
    holder.petition_open_since_tick = 0
    holder.petition_signers = frozenset({1, 2, 3})
    voters = [
        Citizen(citizen_id=i, issue_positions=(0.0,), issue_priorities=(1.0,), blank_threshold=0.0, ambition_score=0.5)
        for i in (1, 2, 3)
    ]

    journal_path = tmp_path / "lost-confidence.jsonl"
    with Journal(journal_path, run_id="lost-confidence") as journal:
        _run_accountability_phase([holder] + voters, config, journal, tick=3)

    events = _events(journal_path)
    recalled = next(e for e in events if e["event_type"] == "recalled")
    assert recalled["payload"]["trigger"] == "confidence_vote"

    assert holder.role == Role.ELECTOR
    assert holder.office == Office.NONE
    assert holder.term_end_tick is None
    update_event = next(e for e in events if e["event_type"] == "legitimacy_updated")
    # Not reset by the recall -- same precedent as the floor-recall path.
    assert holder.legitimacy_capital == pytest.approx(update_event["payload"]["legitimacy"])

    # Office is now vacant: a second call is a no-op.
    with Journal(tmp_path / "lost-confidence-2.jsonl", run_id="lost-confidence-2") as journal:
        _run_accountability_phase([holder] + voters, config, journal, tick=4)
    assert _events(tmp_path / "lost-confidence-2.jsonl") == []


def test_a_survived_confidence_vote_leaves_legitimacy_untouched_and_opens_the_cooldown(tmp_path):
    config = _config_with_legitimacy_enabled(tmp_path, recall_floor=0.0)
    config = dataclasses.replace(
        config,
        run=dataclasses.replace(config.run, population_size=4),
        petition=dataclasses.replace(config.petition, enabled=True),
    )
    holder = _legitimacy_test_citizen(0, legitimacy_capital=0.9, mandate_strength_value=0.9)
    holder.revealed_position = (0.5,)
    holder.petition_open_since_tick = 0
    holder.petition_signers = frozenset({1, 2, 3})
    voters = [
        Citizen(citizen_id=i, issue_positions=(0.5,), issue_priorities=(1.0,), blank_threshold=0.5, ambition_score=0.5)
        for i in (1, 2, 3)
    ]  # each sits exactly on holder.revealed_position -> votes keep

    journal_path = tmp_path / "survived.jsonl"
    with Journal(journal_path, run_id="survived") as journal:
        _run_accountability_phase([holder] + voters, config, journal, tick=7)

    events = _events(journal_path)
    assert not [e for e in events if e["event_type"] == "recalled"]
    result = next(e for e in events if e["event_type"] == "confidence_vote_result")
    assert result["payload"]["retained"] is True

    update_event = next(e for e in events if e["event_type"] == "legitimacy_updated")
    # No L change attributable to surviving -- legitimacy_updated (step 4)
    # already ran before the vote resolved (step 5).
    assert holder.legitimacy_capital == pytest.approx(update_event["payload"]["legitimacy"])
    assert holder.petition_open_since_tick is None
    assert holder.petition_cooldown_until_tick == 7 + config.petition.cooldown_ticks


def test_a_second_petition_cannot_launch_during_the_cooldown(tmp_path):
    config = _config_with_legitimacy_enabled(tmp_path, recall_floor=0.0)
    config = dataclasses.replace(
        config,
        run=dataclasses.replace(config.run, population_size=2),
        awakening=dataclasses.replace(config.awakening, enabled=True, modulation_amplitude=0.0),
        pressure_menu=dataclasses.replace(config.pressure_menu, electoral_only=False, petition_enabled=True),
        petition=dataclasses.replace(config.petition, enabled=True),
    )
    holder = _legitimacy_test_citizen(0, legitimacy_capital=0.9, mandate_strength_value=0.9)
    holder.revealed_position = (0.5,)
    holder.petition_cooldown_until_tick = 5
    launcher = Citizen(
        citizen_id=1, issue_positions=(0.0,), issue_priorities=(1.0,), blank_threshold=0.0,
        ambition_score=0.5, base_threshold=0.0,
    )

    launched_ticks = []
    for tick in range(1, 6):
        journal_path = tmp_path / f"tick-{tick}.jsonl"
        with Journal(journal_path, run_id=f"t{tick}") as journal:
            _run_accountability_phase([holder, launcher], config, journal, tick=tick)
        launched_ticks += [e["tick"] for e in _events(journal_path) if e["event_type"] == "petition_launched"]

    assert launched_ticks == [5]


def test_reelected_president_petition_state_resets_at_the_new_term(tmp_path):
    config = load_config()
    config = dataclasses.replace(config, petition=dataclasses.replace(config.petition, enabled=True))
    term_ticks = config.institutions.president_term_years * config.run.ticks_per_year

    citizen_a = _office_test_citizen(0, 0.1)
    citizen_a.ambition_score = 1.0
    citizen_a.party_affiliation = 0
    party = Party(party_id=0, platform=(0.1,))
    electors = [_office_test_citizen(i, 0.5) for i in range(1, 6)]

    with Journal(tmp_path / "run.jsonl", run_id="r") as journal:
        _hold_presidential_election([citizen_a] + electors, [party], config, journal, tick=0, llm_client=None)
        citizen_a.petition_open_since_tick = 3
        citizen_a.petition_signers = frozenset({1, 2})
        citizen_a.petition_cooldown_until_tick = 10

        _hold_presidential_election(
            [citizen_a] + electors, [party], config, journal, tick=term_ticks, llm_client=None
        )

    assert citizen_a.office == Office.PRESIDENT
    assert citizen_a.petition_open_since_tick is None
    assert citizen_a.petition_signers == frozenset()
    assert citizen_a.petition_cooldown_until_tick is None


def test_a_defeated_incumbents_petition_state_is_deliberately_not_cleared(tmp_path):
    config = dataclasses.replace(
        load_config(), institutions=dataclasses.replace(load_config().institutions, president_term_limit=1)
    )
    config = dataclasses.replace(config, petition=dataclasses.replace(config.petition, enabled=True))
    term_ticks = config.institutions.president_term_years * config.run.ticks_per_year

    citizen_a = _office_test_citizen(0, 0.1)
    citizen_a.ambition_score = 1.0
    citizen_a.party_affiliation = 0
    citizen_b = _office_test_citizen(1, 0.9)
    citizen_b.ambition_score = 1.0
    citizen_b.party_affiliation = 1
    party_a = Party(party_id=0, platform=(0.1,))
    party_b = Party(party_id=1, platform=(0.9,))
    electors = [_office_test_citizen(i, 0.1) for i in range(2, 7)]

    with Journal(tmp_path / "run.jsonl", run_id="r") as journal:
        _hold_presidential_election(
            [citizen_a, citizen_b] + electors, [party_a, party_b], config, journal, tick=0, llm_client=None
        )
        citizen_a.petition_open_since_tick = 3
        citizen_a.petition_signers = frozenset({2})

        _hold_presidential_election(
            [citizen_a, citizen_b] + electors, [party_a, party_b], config, journal, tick=term_ticks, llm_client=None
        )

    assert citizen_a.office == Office.NONE
    assert citizen_a.petition_open_since_tick == 3
    assert citizen_a.petition_signers == frozenset({2})


def test_no_petition_events_while_the_presidency_is_vacant(tmp_path):
    # Same structurally-empty candidate field as the pressure_action twin above.
    config = _config_with_awakening_enabled(tmp_path)
    config = dataclasses.replace(
        config,
        institutions=dataclasses.replace(load_config().institutions, president_term_limit=0),
        pressure_menu=dataclasses.replace(config.pressure_menu, electoral_only=False, petition_enabled=True),
        petition=dataclasses.replace(config.petition, enabled=True),
    )
    journal_path = run_simulation(config, run_id="vacant-petition")
    events = _events(journal_path)
    assert not [e for e in events if e["event_type"] == "elected"]
    assert not [e for e in events if e["event_type"] in _PETITION_LIFECYCLE_EVENT_TYPES]


def test_full_menu_run_reaches_sign_launch_and_mobilize_acts(tmp_path):
    config = _config_with_full_menu_enabled(tmp_path)
    journal_path = run_simulation(config, run_id="full-menu")
    events = _events(journal_path)
    acts = {e["payload"]["act"] for e in events if e["event_type"] == "pressure_action"}
    assert {0, 1, 2, 3}.issubset(acts)


def test_confidence_vote_keep_ratio_equals_mandate_strength_on_the_deterministic_path(tmp_path):
    # Lot 6 is what breaks this identity, on purpose (build_confidence_ballot's
    # own docstring): once revealed_position can drift, the two decouple.
    config = _config_with_petition_enabled(tmp_path)
    journal_path = run_simulation(config, run_id="keep-ratio-identity")
    events = _events(journal_path)
    results = [e for e in events if e["event_type"] == "confidence_vote_result"]
    assert results
    for result in results:
        same_tick_updates = [
            e for e in events
            if e["event_type"] == "legitimacy_updated"
            and e["tick"] == result["tick"]
            and e["citizen_id"] == result["citizen_id"]
        ]
        assert same_tick_updates
        assert result["payload"]["keep_ratio"] == pytest.approx(same_tick_updates[-1]["payload"]["mandate_strength"])


# ── LLM-enabled path (v2 increments 1-2) ─────────────────────────────────

class _FakeLlmClient:
    """Deterministic fake dispatching on user_prompt shape, since one client
    instance now serves decide_candidacies ("citizens" key),
    decide_party_nominations ("parties" key), decide_campaign_positioning
    ("nominees" key), decide_coalition ("responders" key),
    decide_representative_response ("holders" key),
    decide_pressure_actions ("consulted" key), decide_reaction_to_event
    ("reactors" key), decide_chamber_deliberation ("members" key), and
    cast_votes ("voters"/"candidates" keys) within the same run.
    Candidacy: declares (outcome=1) whenever ambition_score >= 0.1 --
    config.candidacy.ambition_threshold is NOT consulted by the LLM path at
    all (decide_candidacies never reads it; only the deterministic
    decide_candidacy does), so this fake owns its own threshold rather than
    reading one from config. Party nomination: picks the highest-ambition
    candidate per contested party (motif 206). Campaign positioning: every
    nominee shifts dimension 0 by +0.1 (motif 602) -- always non-empty, so
    tests can assert a real pledged_platform change, well within the
    default config.campaign bounds (max_positioning_delta=0.3,
    max_positioning_shifts=3). Coalition: every responder joins (motif 501)
    -- the assemble_coalition parity invariant (unanimous join ==
    form_coalition's own output) means this fake's coalitions match the
    deterministic baseline exactly, useful for the byte-identical
    reproducibility test. Representative response: every holder concedes,
    shifting dimension 0 by +0.1 (stance=1, motif=301) -- within the
    shipped mandate.max_response_delta=0.3/max_response_shifts=3 bounds and
    coherent under ResponseDecision's own stance/motif validator; the
    +0.1/tick drift saturates at apply_shifts's [0,1] clamp after ~10 ticks,
    itself worth having show up in an integration run. Pressure action:
    every consulted citizen mobilizes (act=3, motif=301) -- always
    menu-legal whenever mobilization_enabled, and exercises
    street_pressure/participants exactly like the deterministic baseline's
    own MOBILIZE branch. Reaction to event: every reactor gets
    salience_delta=0.1 and the call's own grounding motif (401 for
    SCANDAL, 402 for ECONOMIC_SHOCK), read off the shared "event" block --
    within the shipped events.max_reaction_delta=0.3 bound and coherent
    under ReactionDecision's own salience_delta/motif validator. Voting:
    every citizen votes blank -- enough to
    exercise the integration plumbing (journal writes, reproducibility,
    error propagation) without needing real vote-quality logic."""

    def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
        payload = json.loads(user_prompt)
        if "citizens" in payload:
            decisions = [
                {"cid": c["cid"], "outcome": 1, "motif": 203}
                if c["ambition_score"] >= 0.1
                else {"cid": c["cid"], "outcome": 0, "motif": 201}
                for c in payload["citizens"]
            ]
            return json.dumps({"decisions": decisions})
        if "parties" in payload:
            decisions = [
                {
                    "party_id": p["party_id"],
                    "winner_position": max(p["candidates"], key=lambda c: c["ambition_score"])["position"],
                    "motif": 206,
                }
                for p in payload["parties"]
            ]
            return json.dumps({"decisions": decisions})
        if "nominees" in payload:
            decisions = [
                {"cid": n["cid"], "shifts": [{"dimension": 0, "delta": 0.1}], "motif": 602}
                for n in payload["nominees"]
            ]
            return json.dumps({"decisions": decisions})
        if "responders" in payload:
            decisions = [{"party_id": r["party_id"], "action": 1, "motif": 501} for r in payload["responders"]]
            return json.dumps({"decisions": decisions})
        if "holders" in payload:
            decisions = [
                {"cid": h["cid"], "shifts": [{"dimension": 0, "delta": 0.1}], "stance": 1, "motif": 301}
                for h in payload["holders"]
            ]
            return json.dumps({"decisions": decisions})
        if "consulted" in payload:
            return json.dumps({"decisions": self._pressure_decisions(payload["consulted"])})
        if "reactors" in payload:
            grounding = 401 if payload["event"]["event_type"] == 1 else 402
            decisions = [{"cid": r["cid"], "salience_delta": 0.1, "motif": grounding} for r in payload["reactors"]]
            return json.dumps({"decisions": decisions})
        if "members" in payload:
            decisions = [
                {"cid": m["cid"], "shifts": [{"dimension": 0, "delta": 0.1}], "motif": 702}
                for m in payload["members"]
            ]
            return json.dumps({"decisions": decisions})
        return json.dumps({"decisions": self._vote_decisions(payload["voters"])})

    def _vote_decisions(self, voters):
        return [{"cid": v["cid"], "blank": 1, "ranking": [], "motif": 101} for v in voters]

    def _pressure_decisions(self, consulted):
        # Same priority order as deterministic_pressure_action's own chain
        # (sign > launch > mobilize > wait), restricted to each citizen's
        # own frozen `available` list -- reading `available` from the
        # payload itself, rather than hardcoding one act, is what keeps
        # this fake menu-aware across every pressure_menu modality the
        # test suite exercises without needing the config directly. A
        # naive "prefer the largest available code" fallback was tried
        # first and rejected: 4 (WAIT_FOR_ELECTION) is always legal, so it
        # always wins under max(), starving the petition lever entirely
        # and silently breaking every test that expects a petition to
        # ever launch.
        priority = (1, 2, 3, 4)
        decisions = []
        for c in consulted:
            available = c["available"]
            act = next((a for a in priority if a in available), 0)
            decisions.append({"cid": c["cid"], "target": c["target"], "act": act, "motif": 301})
        return decisions


class _ElectingFakeLlmClient(_FakeLlmClient):
    """Same as _FakeLlmClient in every other respect, but every voter ranks
    the first candidate (by position) instead of voting blank -- unanimous
    support, so a winner is elected every term under any ranked method.
    _FakeLlmClient's own "everyone votes blank" behavior means NO
    presidential election ever produces a winner (confirmed: every existing
    LLM-path test either doesn't check `elected` at all, or explicitly
    asserts its absence) -- harmless for candidacy/positioning/coalition
    tests, but v4 Lot 6's representative_response needs a real, sitting
    officeholder to exercise at all."""

    def _vote_decisions(self, voters):
        return [{"cid": v["cid"], "blank": 0, "ranking": [1], "motif": 104} for v in voters]


class _LaunchingFakeLlmClient(_ElectingFakeLlmClient):
    """v4 Lot 7: every consulted citizen tries to LAUNCH a petition (act=2,
    motif=301) -- the pathological input the central judgment call (a
    frozen batch call vs. live, sequential petition state) exists to
    resolve. Under concurrent_allowed=false, only the first (lowest
    citizen_id) citizen's launch can actually succeed; every later
    citizen's decided act=2 must be downgraded by
    accountability.applicable_pressure_act to a signature (or, if petitions
    are off/unavailable, to NOTHING) -- see
    test_a_second_launch_in_the_same_tick_is_journaled_as_act_2_then_petition_signed."""

    def _pressure_decisions(self, consulted):
        return [{"cid": c["cid"], "target": c["target"], "act": 2, "motif": 301} for c in consulted]


def _config_with_llm_enabled(output_dir) -> PolityConfig:
    config = _config_with_output_dir(output_dir)
    return dataclasses.replace(config, llm=dataclasses.replace(config.llm, enabled=True))


def test_llm_path_completes_and_journals_vote_cast_events(tmp_path):
    config = _config_with_llm_enabled(tmp_path)
    journal_path = run_simulation(config, run_id="llm", llm_client=_FakeLlmClient())
    events = _events(journal_path)
    vote_events = [e for e in events if e["event_type"] == "vote_cast"]
    assert len(vote_events) == config.run.population_size * 8
    assert all(e["motif"] == "101" for e in vote_events)
    assert all(e["codebook_version"] == config.llm.codebook_version for e in vote_events)
    # A clean run never retries, so the local sampling-variation exception
    # (cache_recycle_chunk_size_tension_findings.md) never engages.
    assert all(e["payload"]["retry_sampling_varied"] == 0 for e in vote_events)


def test_two_llm_runs_with_the_same_seed_produce_byte_identical_journals(tmp_path):
    config_a = _config_with_llm_enabled(tmp_path / "a")
    config_b = _config_with_llm_enabled(tmp_path / "b")
    path_a = run_simulation(config_a, run_id="same-run-id", llm_client=_FakeLlmClient())
    path_b = run_simulation(config_b, run_id="same-run-id", llm_client=_FakeLlmClient())
    assert path_a.read_bytes() == path_b.read_bytes()


# ── representative_response (v4 Lot 6, dt=6) ─────────────────────────────

def _config_with_mandate_llm_enabled(output_dir, **overrides) -> PolityConfig:
    config = _config_with_llm_enabled(output_dir)
    config = dataclasses.replace(config, legitimacy=dataclasses.replace(config.legitimacy, enabled=True))
    return dataclasses.replace(config, mandate=dataclasses.replace(config.mandate, enabled=True, **overrides))


def test_default_config_run_emits_no_representative_response_events(tmp_path):
    journal_path = run_simulation(_config_with_output_dir(tmp_path), run_id="baseline")
    events = _events(journal_path)
    assert not [e for e in events if e["event_type"] == "representative_response"]


def test_default_config_run_emits_no_unified_deviation_anywhere(tmp_path):
    # v6b, production-wiring lot: the byte-identity claim, as a direct test
    # rather than only an argument -- the shipped default writes zero
    # representative_response/mandate_deviation_recorded events at all, so
    # "unified_deviation" cannot appear in any payload.
    journal_path = run_simulation(_config_with_output_dir(tmp_path), run_id="baseline")
    events = _events(journal_path)
    assert not any("unified_deviation" in e["payload"] for e in events)


def test_llm_enabled_without_mandate_tracking_emits_no_representative_response_events(tmp_path):
    # mandate.enabled stays at its shipped False -- this is also why the two
    # existing byte-identical LLM reproducibility tests need no edit.
    config = _config_with_llm_enabled(tmp_path)
    journal_path = run_simulation(config, run_id="llm-no-mandate", llm_client=_FakeLlmClient())
    events = _events(journal_path)
    assert not [e for e in events if e["event_type"] == "representative_response"]


def test_mandate_tracking_without_the_llm_never_moves_revealed_position(tmp_path):
    # §7bis.5 control case, re-asserted now that the gate exists: with
    # llm.enabled False, nothing can diverge revealed_position from
    # pledged_platform -- "no delta, stance=silence" by construction.
    config = _config_with_mandate_enabled_and_guaranteed_winners(tmp_path)
    journal_path = run_simulation(config, run_id="mandate-no-llm")
    events = _events(journal_path)
    assert not [e for e in events if e["event_type"] == "representative_response"]
    assert not [e for e in events if e["event_type"] == "mandate_deviation_recorded"]


def test_representative_response_is_journalled_once_per_presided_tick(tmp_path):
    config = _config_with_mandate_llm_enabled(tmp_path)
    journal_path = run_simulation(config, run_id="dt6", llm_client=_ElectingFakeLlmClient())
    events = _events(journal_path)
    response_events = [e for e in events if e["event_type"] == "representative_response"]
    legitimacy_events = [e for e in events if e["event_type"] == "legitimacy_updated"]
    assert response_events
    # legitimacy_updated is already a proven once-per-presided-tick invariant
    # (Lot 3) -- cross-checking against it avoids hardcoding a tick count.
    assert {e["tick"] for e in response_events} == {e["tick"] for e in legitimacy_events}

    for e in response_events:
        assert e["payload"]["office"] == Office.PRESIDENT.value
        assert set(e["payload"].keys()) == {"office", "stance", "shifts", "ctx", "unified_deviation"}
        assert set(e["payload"]["ctx"].keys()) == {"L", "mandate_dev", "street", "lame_duck", "ticks_left"}
        assert e["payload"]["ctx"]["lame_duck"] in (0, 1)
        assert e["motif"] == "301"
        assert e["codebook_version"] == config.llm.codebook_version


def test_representative_response_sees_the_previous_ticks_street_pressure(tmp_path):
    # DoD: the one-tick lag is an emergent property of step ordering, pinned
    # here so a later refactor that silently breaks it fails loudly.
    config = _config_with_llm_enabled(tmp_path)
    config = dataclasses.replace(
        config,
        mandate=dataclasses.replace(config.mandate, enabled=True),
        legitimacy=dataclasses.replace(config.legitimacy, enabled=True),
        awakening=dataclasses.replace(config.awakening, enabled=True, modulation_amplitude=0.0),
        pressure_menu=dataclasses.replace(config.pressure_menu, electoral_only=False, mobilization_enabled=True),
        street_pressure=dataclasses.replace(config.street_pressure, enabled=True),
        run=dataclasses.replace(config.run, population_size=2),
    )
    holder = _legitimacy_test_citizen(0, legitimacy_capital=0.9, mandate_strength_value=0.9)
    holder.pledged_platform = (0.5,)
    holder.revealed_position = (0.5,)
    mobilizer = Citizen(
        citizen_id=1, issue_positions=(0.0,), issue_priorities=(1.0,), blank_threshold=0.0,
        ambition_score=0.5, base_threshold=0.0,
    )

    seen_street = []

    class RecordingClient:
        def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
            payload = json.loads(user_prompt)
            if "consulted" in payload:
                # dt=10 now also fires (llm.enabled + awakening.enabled): every
                # consulted citizen mobilizes, preserving this test's own intent
                # (the mobilizer raises street_pressure) now that the act comes
                # from the LLM path instead of deterministic_pressure_action.
                decisions = [
                    {"cid": c["cid"], "target": c["target"], "act": 3, "motif": 301} for c in payload["consulted"]
                ]
                return json.dumps({"decisions": decisions})
            seen_street.append(payload["holders"][0]["ctx"]["street"])
            decisions = [{"cid": h["cid"], "shifts": [], "stance": 3, "motif": 308} for h in payload["holders"]]
            return json.dumps({"decisions": decisions})

    client = RecordingClient()
    with Journal(tmp_path / "tick0.jsonl", run_id="tick0") as journal:
        _run_accountability_phase([holder, mobilizer], config, journal, tick=0, llm_client=client)
    street_after_tick0 = holder.street_pressure

    with Journal(tmp_path / "tick1.jsonl", run_id="tick1") as journal:
        _run_accountability_phase([holder, mobilizer], config, journal, tick=1, llm_client=client)

    assert seen_street[0] == 0.0  # tick 0: nothing has mobilized yet
    assert street_after_tick0 > 0.0  # tick 0's OWN mobilization raised it
    assert seen_street[1] == pytest.approx(street_after_tick0)  # tick 1 sees tick 0's write, not tick 1's


def test_mandate_deviation_is_recorded_once_revealed_position_drifts(tmp_path):
    # The first nonzero mandate_deviation_recorded in the project's history.
    # pledge_scope=full_platform so dimension 0 (the only one
    # _ElectingFakeLlmClient/_FakeLlmClient's holders branch ever shifts)
    # always carries nonzero weight, regardless of whether it happens to
    # land in the officeholder's own top-5 priority dimensions.
    config = _config_with_mandate_llm_enabled(tmp_path, pledge_scope="full_platform")
    journal_path = run_simulation(config, run_id="drift", llm_client=_ElectingFakeLlmClient())
    events = _events(journal_path)
    deviations = [e for e in events if e["event_type"] == "mandate_deviation_recorded"]
    assert deviations
    assert all(e["payload"]["deviation"] > config.mandate.deviation_log_threshold for e in deviations)
    pledges = [e for e in events if e["event_type"] == "mandate_pledge_declared"]
    assert pledges
    # pledged_platform is never touched by representative_response -- every
    # pledge event's platform is a fresh 20-dim vector from election time,
    # never itself drifting across a term.
    assert all(len(p["payload"]["pledged_platform"]) == config.citizens.issue_count for p in pledges)


def test_representative_response_precedes_the_rest_of_the_tick(tmp_path):
    config = _config_with_mandate_llm_enabled(tmp_path)
    journal_path = run_simulation(config, run_id="ordering", llm_client=_ElectingFakeLlmClient())
    events = _events(journal_path)
    for tick in {e["tick"] for e in events}:
        tick_events = [e for e in events if e["tick"] == tick]
        types = [e["event_type"] for e in tick_events]
        if "representative_response" in types and "legitimacy_updated" in types:
            assert types.index("representative_response") < types.index("legitimacy_updated")


def test_ctx_mandate_dev_is_the_pre_decision_deviation(tmp_path):
    config = _config_with_legitimacy_enabled(tmp_path)
    config = dataclasses.replace(
        config,
        llm=dataclasses.replace(config.llm, enabled=True),
        mandate=dataclasses.replace(config.mandate, enabled=True),
    )
    holder = _legitimacy_test_citizen(0, legitimacy_capital=0.9, mandate_strength_value=0.9)
    holder.pledged_platform = (0.5,)
    holder.revealed_position = (0.5,)

    seen_mandate_devs = []

    class RecordingClient:
        def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
            payload = json.loads(user_prompt)
            seen_mandate_devs.append(payload["holders"][0]["ctx"]["mandate_dev"])
            decisions = [
                {"cid": h["cid"], "shifts": [{"dimension": 0, "delta": 0.2}], "stance": 1, "motif": 301}
                for h in payload["holders"]
            ]
            return json.dumps({"decisions": decisions})

    client = RecordingClient()
    with Journal(tmp_path / "t0.jsonl", run_id="t0") as journal:
        _run_accountability_phase([holder], config, journal, tick=0, llm_client=client)
    events_t0 = _events(tmp_path / "t0.jsonl")
    deviation_t0 = next(e["payload"]["deviation"] for e in events_t0 if e["event_type"] == "mandate_deviation_recorded")

    with Journal(tmp_path / "t1.jsonl", run_id="t1") as journal:
        _run_accountability_phase([holder], config, journal, tick=1, llm_client=client)

    assert seen_mandate_devs[0] == 0.0  # tick 0: no drift yet -- pre-decision
    assert seen_mandate_devs[1] == pytest.approx(deviation_t0)  # tick 1 sees tick 0's post-decision deviation


def test_unified_deviation_is_the_pre_decision_value_like_ctx_mandate_dev(tmp_path):
    # v6b, production-wiring lot: unified_deviation is computed at the SAME
    # instant as ctx.mandate_dev -- same lag, same pairing.
    config = _config_with_legitimacy_enabled(tmp_path)
    config = dataclasses.replace(
        config,
        llm=dataclasses.replace(config.llm, enabled=True),
        mandate=dataclasses.replace(config.mandate, enabled=True),
    )
    holder = _legitimacy_test_citizen(0, legitimacy_capital=0.9, mandate_strength_value=0.9)
    holder.pledged_platform = (0.5,)
    holder.revealed_position = (0.5,)

    class RecordingClient:
        def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
            payload = json.loads(user_prompt)
            decisions = [
                {"cid": h["cid"], "shifts": [{"dimension": 0, "delta": 0.2}], "stance": 1, "motif": 301}
                for h in payload["holders"]
            ]
            return json.dumps({"decisions": decisions})

    client = RecordingClient()
    with Journal(tmp_path / "t0.jsonl", run_id="t0") as journal:
        _run_accountability_phase([holder], config, journal, tick=0, llm_client=client)
    events_t0 = _events(tmp_path / "t0.jsonl")
    response_t0 = next(e for e in events_t0 if e["event_type"] == "representative_response")
    assert response_t0["payload"]["unified_deviation"] == 0.0  # tick 0: no drift yet -- pre-decision
    expected_t1 = unified_mandate_deviation(holder)  # holder mutated in place by tick 0's own shift

    with Journal(tmp_path / "t1.jsonl", run_id="t1") as journal:
        _run_accountability_phase([holder], config, journal, tick=1, llm_client=client)
    events_t1 = _events(tmp_path / "t1.jsonl")
    response_t1 = next(e for e in events_t1 if e["event_type"] == "representative_response")
    assert response_t1["payload"]["unified_deviation"] == pytest.approx(expected_t1)


def test_unified_deviation_is_nonzero_where_the_top_k_scoped_ctx_reads_zero(tmp_path):
    # dim 0 (priority 0.1) sits outside the shipped top-2 -- ctx.mandate_dev
    # stays blind to a drift there while unified_deviation, on the SAME
    # event, sees it (both pre-decision, at the start of tick 1, reflecting
    # the shift tick 0 already applied).
    config = _config_with_mandate_llm_enabled(tmp_path, pledge_top_k=2)
    holder = Citizen(
        citizen_id=0, issue_positions=(0.5, 0.5, 0.5), issue_priorities=(0.1, 0.6, 0.3),
        blank_threshold=0.5, ambition_score=0.5, role=Role.ELECTED, office=Office.PRESIDENT,
        # legitimacy.enabled is also on (_config_with_mandate_llm_enabled's own
        # shape) -- comfortably above recall_floor so the office survives to
        # tick 1; a floor-crossing recall is not what this test is about.
        legitimacy_capital=0.9, mandate_strength=0.9,
    )
    holder.pledged_platform = (0.5, 0.5, 0.5)
    holder.revealed_position = (0.5, 0.5, 0.5)

    class ShiftDim0Client:
        def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
            payload = json.loads(user_prompt)
            decisions = [
                {"cid": h["cid"], "shifts": [{"dimension": 0, "delta": 0.3}], "stance": 1, "motif": 301}
                for h in payload["holders"]
            ]
            return json.dumps({"decisions": decisions})

    client = ShiftDim0Client()
    with Journal(tmp_path / "t0.jsonl", run_id="t0") as journal:
        _run_accountability_phase([holder], config, journal, tick=0, llm_client=client)
    with Journal(tmp_path / "t1.jsonl", run_id="t1") as journal:
        _run_accountability_phase([holder], config, journal, tick=1, llm_client=client)

    events_t1 = _events(tmp_path / "t1.jsonl")
    response_t1 = next(e for e in events_t1 if e["event_type"] == "representative_response")
    assert response_t1["payload"]["ctx"]["mandate_dev"] == 0.0
    assert response_t1["payload"]["unified_deviation"] > 0.0


def test_no_representative_response_while_the_presidency_is_vacant(tmp_path):
    config = _config_with_llm_enabled(tmp_path)
    config = dataclasses.replace(config, mandate=dataclasses.replace(config.mandate, enabled=True))

    class VacantClient:
        """Declines every candidacy -- the presidency stays vacant the
        entire run, and no vote_cast/holders call ever happens. Legislative
        elections/coalitions are unaffected (choose_party is deterministic,
        never LLM-gated) -- still need to answer "responders" so a
        contested coalition round doesn't fail schema validation on an
        empty decisions list."""

        def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
            payload = json.loads(user_prompt)
            if "citizens" in payload:
                decisions = [{"cid": c["cid"], "outcome": 0, "motif": 201} for c in payload["citizens"]]
                return json.dumps({"decisions": decisions})
            if "responders" in payload:
                decisions = [{"party_id": r["party_id"], "action": 2, "motif": 504} for r in payload["responders"]]
                return json.dumps({"decisions": decisions})
            decisions = [{"cid": v["cid"], "blank": 1, "ranking": [], "motif": 101} for v in payload.get("voters", [])]
            return json.dumps({"decisions": decisions})

    journal_path = run_simulation(config, run_id="vacant-llm", llm_client=VacantClient())
    events = _events(journal_path)
    assert not [e for e in events if e["event_type"] == "elected"]
    assert not [e for e in events if e["event_type"] == "representative_response"]


def test_two_mandate_llm_runs_produce_byte_identical_journals(tmp_path):
    path_a = run_simulation(
        _config_with_mandate_llm_enabled(tmp_path / "a"), run_id="same-run-id", llm_client=_ElectingFakeLlmClient()
    )
    path_b = run_simulation(
        _config_with_mandate_llm_enabled(tmp_path / "b"), run_id="same-run-id", llm_client=_ElectingFakeLlmClient()
    )
    assert path_a.read_bytes() == path_b.read_bytes()


def test_ctx_omits_street_pressure_when_it_is_not_visible_to_the_representative(tmp_path):
    config = _config_with_mandate_llm_enabled(tmp_path)
    config = dataclasses.replace(
        config,
        awakening=dataclasses.replace(config.awakening, enabled=True),
        pressure_menu=dataclasses.replace(config.pressure_menu, electoral_only=False, mobilization_enabled=True),
        street_pressure=dataclasses.replace(config.street_pressure, enabled=True, visible_to_representative=False),
    )
    journal_path = run_simulation(config, run_id="street-invisible", llm_client=_ElectingFakeLlmClient())
    events = _events(journal_path)
    response_events = [e for e in events if e["event_type"] == "representative_response"]
    assert response_events
    assert all(e["payload"]["ctx"]["street"] is None for e in response_events)


def test_confidence_vote_keep_ratio_decouples_from_mandate_strength_once_the_position_drifts(tmp_path):
    # Lot 5's own test_confidence_vote_keep_ratio_equals_mandate_strength_on_the_deterministic_path
    # stays green UNMODIFIED (it runs with llm.enabled=False) -- this is the
    # LLM-path counterpart, deliberately breaking the identity dt=6 was
    # named for breaking (build_confidence_ballot's own docstring).
    config = _config_with_mandate_llm_enabled(tmp_path)
    config = dataclasses.replace(
        config,
        awakening=dataclasses.replace(config.awakening, enabled=True),
        pressure_menu=dataclasses.replace(config.pressure_menu, electoral_only=False, petition_enabled=True),
        petition=dataclasses.replace(config.petition, enabled=True, signature_threshold=0.05),
    )
    journal_path = run_simulation(config, run_id="decouple", llm_client=_ElectingFakeLlmClient())
    events = _events(journal_path)
    results = [e for e in events if e["event_type"] == "confidence_vote_result"]
    assert results

    mismatches = 0
    for result in results:
        same_tick_updates = [
            e for e in events
            if e["event_type"] == "legitimacy_updated"
            and e["tick"] == result["tick"]
            and e["citizen_id"] == result["citizen_id"]
        ]
        assert same_tick_updates
        if result["payload"]["keep_ratio"] != pytest.approx(same_tick_updates[-1]["payload"]["mandate_strength"]):
            mismatches += 1
    assert mismatches > 0  # the identity deliberately breaks once the position has drifted


def test_llm_batch_misalignment_aborts_the_run_with_no_partial_journal(tmp_path):
    class _ShortClient:
        """Answers candidacy calls in full (so nominees exist to vote on),
        but answers every vote call with a decision for a cid that was
        never asked -- isolates the misalignment failure to cast_votes
        specifically. A wrong cid, not "drop all but the first" or an
        empty decisions list: cast_votes now chunks at
        _VOTE_CAST_MAX_CHUNK_SIZE=1, so a chunk's own expected_cids is
        already length 1 -- "first decision only" would no longer be a
        mismatch at that chunk size, it would coincidentally match; and
        VoteCastBatch's own min_length=1 would turn an empty list into a
        schema-validation LlmResponseError, not the "misaligned" one this
        test asserts on."""

        def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
            payload = json.loads(user_prompt)
            if "citizens" in payload:
                decisions = [
                    {"cid": c["cid"], "outcome": 1, "motif": 203}
                    if c["ambition_score"] >= 0.1
                    else {"cid": c["cid"], "outcome": 0, "motif": 201}
                    for c in payload["citizens"]
                ]
                return json.dumps({"decisions": decisions})
            if "parties" in payload:
                decisions = [
                    {
                        "party_id": p["party_id"],
                        "winner_position": max(p["candidates"], key=lambda c: c["ambition_score"])["position"],
                        "motif": 206,
                    }
                    for p in payload["parties"]
                ]
                return json.dumps({"decisions": decisions})
            if "nominees" in payload:
                decisions = [{"cid": n["cid"], "shifts": [], "motif": 601} for n in payload["nominees"]]
                return json.dumps({"decisions": decisions})
            return json.dumps({"decisions": [{"cid": 999999, "blank": 1, "ranking": [], "motif": 101}]})

    config = _config_with_llm_enabled(tmp_path)
    with pytest.raises(LlmResponseError, match="misaligned"):
        run_simulation(config, run_id="r", llm_client=_ShortClient())


# ── llm.max_batch_replays (v4 Lot 8) ─────────────────────────────────────

class _RecoveringClient:
    """Wraps another client but answers malformed JSON on its own very
    first call, then delegates every call after -- proves
    max_batch_replays lets a run recover from exactly one misaligned batch
    instead of aborting it, without needing to know which decision type
    happens to be the run's first LLM call."""

    def __init__(self, inner):
        self._inner = inner
        self.calls = 0

    def complete_json(self, **kwargs):
        self.calls += 1
        if self.calls == 1:
            return "not valid json"
        return self._inner.complete_json(**kwargs)


def test_a_replayed_batch_lets_the_run_complete(tmp_path):
    config = _config_with_llm_enabled(tmp_path)
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, max_batch_replays=2))
    journal_path = run_simulation(config, run_id="replay-recovers", llm_client=_RecoveringClient(_FakeLlmClient()))
    events = _events(journal_path)
    assert events  # completed with a non-empty journal, not aborted


class _FlakyVoteClient:
    """Wraps _FakeLlmClient but fails the FIRST vote_cast call only
    (detected by the "voters" fallback key -- see _FakeLlmClient's own
    dispatch), recording the temperature kwarg each call receives.
    Exercises cast_votes's own local, deliberate retry_temperature
    exception (llm_behavior_engine._VOTE_CAST_RETRY_TEMPERATURE) at the
    full run_simulation level, including the journal's own
    retry_sampling_varied marker."""

    def __init__(self, inner):
        self._inner = inner
        self._vote_calls = 0
        self.temperatures: list[float | None] = []

    def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True, temperature=None):
        self.temperatures.append(temperature)
        payload = json.loads(user_prompt)
        is_vote_call = not any(k in payload for k in ("citizens", "parties", "nominees", "responders", "holders", "consulted", "reactors", "members"))
        if is_vote_call:
            self._vote_calls += 1
            if self._vote_calls == 1:
                return "not valid json"
        return self._inner.complete_json(
            system_prompt=system_prompt, user_prompt=user_prompt, json_schema=json_schema,
            max_tokens=max_tokens, think=think,
        )


def test_vote_cast_retries_at_a_varied_temperature_and_journals_the_marker(tmp_path):
    config = _config_with_llm_enabled(tmp_path)
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, max_batch_replays=1))
    client = _FlakyVoteClient(_FakeLlmClient())
    journal_path = run_simulation(config, run_id="vote-retry", llm_client=client)
    events = _events(journal_path)
    vote_events = [e for e in events if e["event_type"] == "vote_cast"]
    assert vote_events  # the run completed, the retry recovered it
    # Exactly one voter's decision came from a retry -- the one whose
    # first attempt this fake deliberately broke.
    varied = [e for e in vote_events if e["payload"]["retry_sampling_varied"] == 1]
    assert len(varied) == 1
    # First attempt (the failure): no override. The recovering retry: the
    # local exception's own temperature.
    assert client.temperatures[0] is None
    assert _VOTE_CAST_RETRY_TEMPERATURE in client.temperatures


# ── pressure_action (v4 Lot 7, dt=10) ────────────────────────────────────

def _config_with_awakening_llm_enabled(output_dir, **overrides) -> PolityConfig:
    config = _config_with_llm_enabled(output_dir)
    config = dataclasses.replace(config, legitimacy=dataclasses.replace(config.legitimacy, enabled=True))
    config = dataclasses.replace(config, candidacy=dataclasses.replace(config.candidacy, ambition_threshold=0.0))
    return dataclasses.replace(config, awakening=dataclasses.replace(config.awakening, enabled=True, **overrides))


def _config_with_full_menu_llm_enabled(output_dir) -> PolityConfig:
    config = _config_with_awakening_llm_enabled(output_dir)
    return dataclasses.replace(
        config,
        pressure_menu=dataclasses.replace(
            config.pressure_menu, electoral_only=False, petition_enabled=True, mobilization_enabled=True
        ),
        petition=dataclasses.replace(config.petition, enabled=True),
        street_pressure=dataclasses.replace(config.street_pressure, enabled=True),
    )


def _pressure_test_citizen(cid, base_threshold=0.0):
    return Citizen(
        citizen_id=cid, issue_positions=(0.0,), issue_priorities=(1.0,), blank_threshold=0.0,
        ambition_score=0.5, base_threshold=base_threshold,
    )


def test_llm_enabled_without_awakening_emits_no_pressure_action_events(tmp_path):
    # awakening.enabled stays at its shipped False -- this is also why the
    # existing LLM byte-identical tests need no edit.
    config = _config_with_llm_enabled(tmp_path)
    journal_path = run_simulation(config, run_id="llm-no-awakening", llm_client=_FakeLlmClient())
    events = _events(journal_path)
    assert not [e for e in events if e["event_type"] == "pressure_action"]


def test_awakening_without_the_llm_still_uses_the_deterministic_baseline(tmp_path):
    config = _config_with_awakening_enabled_and_guaranteed_winners(tmp_path)
    journal_path = run_simulation(config, run_id="awakening-no-llm")
    events = _events(journal_path)
    pressure_events = [e for e in events if e["event_type"] == "pressure_action"]
    assert pressure_events
    for e in pressure_events:
        assert set(e["payload"].keys()) == {"target", "act"}  # byte-identical to Lot 4's shape, no ctx
        assert e["motif"] is None
        assert e["codebook_version"] == ""


def test_pressure_action_is_journalled_once_per_consulted_citizen_with_its_ctx(tmp_path):
    config = _config_with_awakening_llm_enabled(tmp_path)
    config = dataclasses.replace(
        config, pressure_menu=dataclasses.replace(config.pressure_menu, electoral_only=False, mobilization_enabled=True)
    )
    journal_path = run_simulation(config, run_id="dt10", llm_client=_ElectingFakeLlmClient())
    events = _events(journal_path)
    pressure_events = [e for e in events if e["event_type"] == "pressure_action"]
    assert pressure_events
    for e in pressure_events:
        assert set(e["payload"].keys()) == {"target", "act", "ctx"}
        assert set(e["payload"]["ctx"].keys()) == {"self_gap", "mandate_dev", "neighbors_acting", "ticks_to_election"}
        assert e["payload"]["ctx"]["neighbors_acting"] is None
        assert e["motif"] == "301"
        assert e["codebook_version"] == config.llm.codebook_version
    for tick in {e["tick"] for e in pressure_events}:
        cids = [e["citizen_id"] for e in pressure_events if e["tick"] == tick]
        assert cids == sorted(cids)


def test_a_second_launch_in_the_same_tick_is_journaled_as_act_2_then_petition_signed(tmp_path):
    # DoD, the central judgment call: a frozen batch call vs LIVE petition
    # state. Every consulted citizen decides LAUNCH (act=2); under
    # concurrent_allowed=false, only the lowest-cid citizen's launch can
    # actually succeed -- every later citizen's decided act=2 must be
    # downgraded by applicable_pressure_act to a signature.
    config = _config_with_petition_enabled(tmp_path)
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, enabled=True))
    holder = _legitimacy_test_citizen(0, legitimacy_capital=0.9, mandate_strength_value=0.9)
    holder.revealed_position = (0.5,)
    citizens = [holder] + [_pressure_test_citizen(i) for i in range(1, 4)]

    class AllLaunchClient:
        def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
            payload = json.loads(user_prompt)
            decisions = [
                {"cid": c["cid"], "target": c["target"], "act": 2, "motif": 301} for c in payload["consulted"]
            ]
            return json.dumps({"decisions": decisions})

    journal_path = tmp_path / "collision.jsonl"
    with Journal(journal_path, run_id="collision") as journal:
        _run_accountability_phase(citizens, config, journal, tick=0, llm_client=AllLaunchClient())
    events = _events(journal_path)

    launches = [e for e in events if e["event_type"] == "petition_launched"]
    signs = [e for e in events if e["event_type"] == "petition_signed"]
    assert len(launches) == 1
    assert launches[0]["citizen_id"] == 1  # lowest consulted citizen_id
    assert len(signs) == 2  # citizens 2 and 3, downgraded

    pressure_events = [e for e in events if e["event_type"] == "pressure_action"]
    assert all(e["payload"]["act"] == 2 for e in pressure_events)  # decided act, never rewritten
    for i, e in enumerate(events):
        if e["event_type"] == "pressure_action" and e["citizen_id"] != 1:
            assert events[i + 1]["event_type"] == "petition_signed"
            assert events[i + 1]["citizen_id"] == e["citizen_id"]

    assert holder.petition_signers == {1, 2, 3}


def test_an_out_of_menu_act_aborts_the_run_with_no_partial_journal(tmp_path):
    config = _config_with_awakening_llm_enabled(tmp_path)  # shipped electoral_only menu, legal={0,4}

    class OutOfMenuClient(_ElectingFakeLlmClient):
        def _pressure_decisions(self, consulted):
            return [{"cid": c["cid"], "target": c["target"], "act": 3, "motif": 301} for c in consulted]

    with pytest.raises(LlmResponseError, match="outside the active"):
        run_simulation(config, run_id="out-of-menu", llm_client=OutOfMenuClient())


def test_a_stale_sign_does_not_abort_the_run(tmp_path):
    # The two-tier split proven end to end: act=1 is menu-legal but
    # unsatisfiable live (no petition open, target still in cooldown) --
    # validate_pressure_decision does not reject it; applicable_pressure_act
    # downgrades it to NOTHING instead of aborting the whole batch.
    config = _config_with_petition_enabled(tmp_path)
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, enabled=True))
    holder = _legitimacy_test_citizen(0, legitimacy_capital=0.9, mandate_strength_value=0.9)
    holder.revealed_position = (0.5,)
    holder.petition_cooldown_until_tick = 100  # still cooling down: can_launch is False
    citizen = _pressure_test_citizen(1)

    class AlwaysSignClient:
        def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
            payload = json.loads(user_prompt)
            decisions = [
                {"cid": c["cid"], "target": c["target"], "act": 1, "motif": 301} for c in payload["consulted"]
            ]
            return json.dumps({"decisions": decisions})

    journal_path = tmp_path / "stale.jsonl"
    with Journal(journal_path, run_id="stale") as journal:
        _run_accountability_phase([holder, citizen], config, journal, tick=0, llm_client=AlwaysSignClient())
    events = _events(journal_path)
    pressure_events = [e for e in events if e["event_type"] == "pressure_action"]
    assert pressure_events
    assert pressure_events[0]["payload"]["act"] == 1  # decided act, unchanged in the journal
    assert not [e for e in events if e["event_type"] in ("petition_launched", "petition_signed")]
    assert holder.petition_open_since_tick is None


def test_pressure_action_ctx_reflects_this_ticks_revealed_position(tmp_path):
    # The no-lag pin, the symmetric twin of
    # test_representative_response_sees_the_previous_ticks_street_pressure:
    # dt=10 sees THIS tick's revealed_position, including a shift dt=6 just
    # made earlier in the SAME tick.
    config = _config_with_mandate_llm_enabled(tmp_path)
    config = dataclasses.replace(
        config,
        awakening=dataclasses.replace(config.awakening, enabled=True, modulation_amplitude=0.0),
        pressure_menu=dataclasses.replace(config.pressure_menu, electoral_only=False, mobilization_enabled=True),
    )
    holder = _legitimacy_test_citizen(0, legitimacy_capital=0.9, mandate_strength_value=0.9)
    holder.pledged_platform = (0.5,)
    holder.revealed_position = (0.5,)
    citizen = _pressure_test_citizen(1)

    seen_self_gap = []

    class RecordingClient:
        def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
            payload = json.loads(user_prompt)
            if "holders" in payload:
                decisions = [
                    {"cid": h["cid"], "shifts": [{"dimension": 0, "delta": 0.3}], "stance": 1, "motif": 301}
                    for h in payload["holders"]
                ]
                return json.dumps({"decisions": decisions})
            seen_self_gap.append(payload["consulted"][0]["ctx"]["self_gap"])
            decisions = [
                {"cid": c["cid"], "target": c["target"], "act": 3, "motif": 301} for c in payload["consulted"]
            ]
            return json.dumps({"decisions": decisions})

    with Journal(tmp_path / "tick0.jsonl", run_id="t0") as journal:
        _run_accountability_phase([holder, citizen], config, journal, tick=0, llm_client=RecordingClient())

    # dt=6 shifted holder.revealed_position by +0.3 (0.5 -> 0.8) THIS tick,
    # before dt=10 ran -- ctx.self_gap must reflect 0.8, not the stale 0.5.
    assert holder.revealed_position[0] == pytest.approx(0.8)
    expected_gap = abs(citizen.issue_positions[0] - holder.revealed_position[0])
    assert seen_self_gap[0] == pytest.approx(expected_gap)


def test_pressure_action_ctx_never_carries_street_pressure(tmp_path):
    # The asymmetry with dt=6 asserted, not just implemented: the same run's
    # representative_response.ctx.street is populated while
    # pressure_action's ctx never contains a street-pressure key at all.
    config = _config_with_mandate_llm_enabled(tmp_path)
    config = dataclasses.replace(
        config,
        awakening=dataclasses.replace(config.awakening, enabled=True),
        pressure_menu=dataclasses.replace(config.pressure_menu, electoral_only=False, mobilization_enabled=True),
        street_pressure=dataclasses.replace(config.street_pressure, enabled=True, visible_to_representative=True),
    )
    journal_path = run_simulation(config, run_id="no-street-leak", llm_client=_ElectingFakeLlmClient())
    events = _events(journal_path)
    pressure_events = [e for e in events if e["event_type"] == "pressure_action"]
    response_events = [e for e in events if e["event_type"] == "representative_response"]
    assert pressure_events
    assert response_events
    assert any(e["payload"]["ctx"]["street"] is not None for e in response_events)
    for e in pressure_events:
        assert set(e["payload"]["ctx"].keys()) == {"self_gap", "mandate_dev", "neighbors_acting", "ticks_to_election"}


def test_two_awakening_llm_runs_produce_byte_identical_journals(tmp_path):
    path_a = run_simulation(
        _config_with_awakening_llm_enabled(tmp_path / "a"), run_id="same-run-id", llm_client=_ElectingFakeLlmClient()
    )
    path_b = run_simulation(
        _config_with_awakening_llm_enabled(tmp_path / "b"), run_id="same-run-id", llm_client=_ElectingFakeLlmClient()
    )
    assert path_a.read_bytes() == path_b.read_bytes()


def test_two_full_menu_llm_runs_produce_byte_identical_journals(tmp_path):
    path_a = run_simulation(
        _config_with_full_menu_llm_enabled(tmp_path / "a"), run_id="same-run-id", llm_client=_ElectingFakeLlmClient()
    )
    path_b = run_simulation(
        _config_with_full_menu_llm_enabled(tmp_path / "b"), run_id="same-run-id", llm_client=_ElectingFakeLlmClient()
    )
    assert path_a.read_bytes() == path_b.read_bytes()


def test_llm_pressure_actions_reach_every_menu_modality(tmp_path):
    # Unlike the shared _FakeLlmClient's fixed sign>launch>mobilize>wait
    # priority order -- which under a full menu never lets act 0 or 4 win,
    # since MOBILIZE is always reachable first -- this fake varies its
    # preference by cid so a full-menu run exercises every PressureAct.
    class AllActsClient(_ElectingFakeLlmClient):
        def _pressure_decisions(self, consulted):
            decisions = []
            for c in consulted:
                available = c["available"]
                preferred = c["cid"] % 5
                act = preferred if preferred in available else next(iter(available))
                decisions.append({"cid": c["cid"], "target": c["target"], "act": act, "motif": 301})
            return decisions

    config = _config_with_full_menu_llm_enabled(tmp_path)
    journal_path = run_simulation(config, run_id="full-menu-llm", llm_client=AllActsClient())
    events = _events(journal_path)
    pressure_events = [e for e in events if e["event_type"] == "pressure_action"]
    assert pressure_events
    acts = {e["payload"]["act"] for e in pressure_events}
    assert acts == {0, 1, 2, 3, 4}


def test_street_pressure_counts_llm_mobilize_decisions(tmp_path):
    config = _config_with_legitimacy_enabled(tmp_path)
    config = dataclasses.replace(
        config,
        llm=dataclasses.replace(config.llm, enabled=True),
        awakening=dataclasses.replace(config.awakening, enabled=True, modulation_amplitude=0.0),
        pressure_menu=dataclasses.replace(config.pressure_menu, electoral_only=False, mobilization_enabled=True),
        street_pressure=dataclasses.replace(config.street_pressure, enabled=True),
        run=dataclasses.replace(config.run, population_size=4),
    )
    holder = _legitimacy_test_citizen(0, legitimacy_capital=0.9, mandate_strength_value=0.9)
    holder.revealed_position = (0.5,)
    citizens = [holder] + [_pressure_test_citizen(i) for i in range(1, 4)]

    class MobilizeClient:
        def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
            payload = json.loads(user_prompt)
            decisions = [
                {"cid": c["cid"], "target": c["target"], "act": 3, "motif": 301} for c in payload["consulted"]
            ]
            return json.dumps({"decisions": decisions})

    journal_path = tmp_path / "mobilize.jsonl"
    with Journal(journal_path, run_id="mobilize") as journal:
        _run_accountability_phase(citizens, config, journal, tick=0, llm_client=MobilizeClient())

    expected = update_street_pressure(0.0, mobilization_rate(3, 4), config.street_pressure)
    assert holder.street_pressure == pytest.approx(expected)


def test_no_pressure_action_llm_call_while_the_presidency_is_vacant(tmp_path):
    # Shipped ambition_threshold never produces a winner -- the presidency
    # stays vacant, so decide_pressure_actions must never even be called.
    config = _config_with_llm_enabled(tmp_path)
    config = dataclasses.replace(config, awakening=dataclasses.replace(config.awakening, enabled=True))

    class RecordingVacantClient(_FakeLlmClient):
        def __init__(self):
            self.pressure_calls = 0

        def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
            payload = json.loads(user_prompt)
            if "consulted" in payload:
                self.pressure_calls += 1
            return super().complete_json(
                system_prompt=system_prompt, user_prompt=user_prompt, json_schema=json_schema,
                max_tokens=max_tokens, think=think,
            )

    client = RecordingVacantClient()
    journal_path = run_simulation(config, run_id="vacant-dt10", llm_client=client)
    events = _events(journal_path)
    assert not [e for e in events if e["event_type"] == "elected"]
    assert not [e for e in events if e["event_type"] == "pressure_action"]
    assert client.pressure_calls == 0


def test_a_cohort_of_one_still_produces_a_single_call(tmp_path):
    # The small-cohort path MIN_SAFE_BATCH_SIZE's default floor would have
    # aborted -- exercised through the real wiring, not just chunk_voters
    # directly.
    config = _config_with_legitimacy_enabled(tmp_path)
    config = dataclasses.replace(
        config,
        llm=dataclasses.replace(config.llm, enabled=True),
        awakening=dataclasses.replace(config.awakening, enabled=True, modulation_amplitude=0.0),
        pressure_menu=dataclasses.replace(config.pressure_menu, electoral_only=False, mobilization_enabled=True),
    )
    holder = _legitimacy_test_citizen(0, legitimacy_capital=0.9, mandate_strength_value=0.9)
    holder.revealed_position = (0.5,)
    citizen = _pressure_test_citizen(1)

    class RecordingClient:
        def __init__(self):
            self.calls = 0

        def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
            self.calls += 1
            payload = json.loads(user_prompt)
            decisions = [
                {"cid": c["cid"], "target": c["target"], "act": 3, "motif": 301} for c in payload["consulted"]
            ]
            return json.dumps({"decisions": decisions})

    client = RecordingClient()
    journal_path = tmp_path / "cohort_one.jsonl"
    with Journal(journal_path, run_id="cohort-one") as journal:
        _run_accountability_phase([holder, citizen], config, journal, tick=0, llm_client=client)
    assert client.calls == 1
    events = _events(journal_path)
    assert [e for e in events if e["event_type"] == "pressure_action"]


# ── neighbors_acting (v6 Lot 3, §5) ──────────────────────────────────────

def test_neighbors_acting_is_present_in_pressure_action_ctx_when_the_graph_is_enabled(tmp_path):
    config = _config_with_full_menu_llm_enabled(tmp_path)
    config = dataclasses.replace(config, social_graph=dataclasses.replace(config.social_graph, enabled=True))
    journal_path = run_simulation(config, run_id="graph-ctx", llm_client=_ElectingFakeLlmClient())
    events = _events(journal_path)
    pressure_events = [e for e in events if e["event_type"] == "pressure_action"]
    assert pressure_events
    for event in pressure_events:
        neighbors_acting_value = event["payload"]["ctx"]["neighbors_acting"]
        assert neighbors_acting_value is not None
        assert 0.0 <= neighbors_acting_value <= 1.0


def test_pressure_action_ctx_reflects_the_previous_ticks_mobilization(tmp_path):
    # v6 Lot 3, the one-tick-lag DoD -- mirrors dt=6's own
    # test_representative_response_sees_the_previous_ticks_street_pressure.
    # decide_pressure_actions batches an entire cohort's decisions in one
    # frozen call, so a neighbor's SAME-tick decision cannot be seen by
    # construction -- only a neighbor's prior, already-APPLIED action feeds
    # this tick's ctx. citizen_b's own base_threshold=0.0 keeps it
    # consulted every tick regardless of the (here, off) modulation flag,
    # isolating "what ctx value does B see" from "does the graph gate B's
    # own consultation" (the latter is its own test below).
    config = _config_with_awakening_llm_enabled(tmp_path)
    config = dataclasses.replace(
        config,
        social_graph=dataclasses.replace(config.social_graph, enabled=True),
        pressure_menu=dataclasses.replace(config.pressure_menu, electoral_only=False, mobilization_enabled=True),
    )
    holder = _legitimacy_test_citizen(0, legitimacy_capital=0.9, mandate_strength_value=0.9)
    holder.revealed_position = (0.5,)
    citizen_a = _pressure_test_citizen(1)
    citizen_b = _pressure_test_citizen(2)
    graph = SocialGraph(neighbors={0: frozenset(), 1: frozenset({2}), 2: frozenset({1})})
    citizens = [holder, citizen_a, citizen_b]

    seen_neighbors_acting = []

    class RecordingClient:
        def __init__(self):
            self.call_index = 0

        def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
            decisions = []
            for c in json.loads(user_prompt)["consulted"]:
                if c["cid"] == citizen_b.citizen_id:
                    seen_neighbors_acting.append(c["ctx"]["neighbors_acting"])
                # citizen_a mobilizes only on the very first call, so tick
                # 1's mobilization is empty and tick 2 must see a reset.
                act = 3 if c["cid"] == citizen_a.citizen_id and self.call_index == 0 else 4
                decisions.append({"cid": c["cid"], "target": c["target"], "act": act, "motif": 301})
            self.call_index += 1
            return json.dumps({"decisions": decisions})

    client = RecordingClient()
    mobilized: dict = {}
    for tick in range(3):
        journal_path = tmp_path / f"lag-tick{tick}.jsonl"
        with Journal(journal_path, run_id=f"lag-tick{tick}") as journal:
            mobilized = _run_accountability_phase(
                citizens, config, journal, tick=tick, llm_client=client,
                graph=graph, mobilized_last_tick=mobilized,
            )

    assert seen_neighbors_acting == [0.0, 1.0, 0.0]


def test_neighbors_acting_can_bring_a_marginal_citizen_above_their_own_threshold(tmp_path):
    # v6 Lot 3: isolates the new awakening-gate term's real behavioral
    # effect end to end -- the closest this lot gets to demonstrating
    # Granovetter-style threshold diffusion without v6a Lot 4's own
    # acceptance run. self_gap=0.45 sits just under base_threshold=0.46 at
    # neighbors_acting=0.0 (0.46*(1-0.5*0)=0.46); once the mobilizer's own
    # tick-0 mobilization becomes visible to `marginal` (its only graph
    # neighbor), the modulated threshold drops to 0.23
    # (0.46*(1-0.5*1.0)), crossing self_gap.
    def marginal_is_ever_consulted(neighbors_acting_flag):
        config = _config_with_awakening_llm_enabled(tmp_path)
        config = dataclasses.replace(
            config,
            social_graph=dataclasses.replace(config.social_graph, enabled=True),
            pressure_menu=dataclasses.replace(config.pressure_menu, electoral_only=False, mobilization_enabled=True),
            awakening=dataclasses.replace(
                config.awakening,
                modulation_amplitude=0.5,
                context_modulation=dataclasses.replace(
                    config.awakening.context_modulation, neighbors_acting=neighbors_acting_flag
                ),
            ),
        )
        holder = _legitimacy_test_citizen(0, legitimacy_capital=0.9, mandate_strength_value=0.9)
        holder.revealed_position = (0.5,)
        mobilizer = _pressure_test_citizen(1, base_threshold=0.0)
        marginal = Citizen(
            citizen_id=2, issue_positions=(0.05,), issue_priorities=(1.0,), blank_threshold=0.0,
            ambition_score=0.5, base_threshold=0.46,
        )
        graph = SocialGraph(neighbors={0: frozenset(), 1: frozenset({2}), 2: frozenset({1})})
        citizens = [holder, mobilizer, marginal]

        class RecordingClient:
            def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
                decisions = [
                    {"cid": c["cid"], "target": c["target"], "act": 3 if c["cid"] == 1 else 4, "motif": 301}
                    for c in json.loads(user_prompt)["consulted"]
                ]
                return json.dumps({"decisions": decisions})

        client = RecordingClient()
        mobilized: dict = {}
        marginal_consulted = False
        for tick in range(2):
            journal_path = tmp_path / f"marginal-{neighbors_acting_flag}-{tick}.jsonl"
            with Journal(journal_path, run_id=f"marginal-{neighbors_acting_flag}-{tick}") as journal:
                mobilized = _run_accountability_phase(
                    citizens, config, journal, tick=tick, llm_client=client,
                    graph=graph, mobilized_last_tick=mobilized,
                )
            events = _events(journal_path)
            if any(e["event_type"] == "pressure_action" and e["citizen_id"] == 2 for e in events):
                marginal_consulted = True
        return marginal_consulted

    assert marginal_is_ever_consulted(True) is True
    assert marginal_is_ever_consulted(False) is False


def test_two_social_graph_llm_runs_produce_byte_identical_journals(tmp_path):
    config_a = _config_with_full_menu_llm_enabled(tmp_path / "a")
    config_a = dataclasses.replace(config_a, social_graph=dataclasses.replace(config_a.social_graph, enabled=True))
    config_b = _config_with_full_menu_llm_enabled(tmp_path / "b")
    config_b = dataclasses.replace(config_b, social_graph=dataclasses.replace(config_b.social_graph, enabled=True))
    path_a = run_simulation(config_a, run_id="same-run-id", llm_client=_ElectingFakeLlmClient())
    path_b = run_simulation(config_b, run_id="same-run-id", llm_client=_ElectingFakeLlmClient())
    assert path_a.read_bytes() == path_b.read_bytes()


def test_an_isolated_citizens_neighbors_acting_is_zero_not_a_crash(tmp_path):
    # Lot 2's own measured property: erdos_renyi at the shipped scale
    # (n=100, seed=42) isolates citizen_id=3 -- confirmed directly. No
    # crash, and every one of its own pressure_action events reads
    # neighbors_acting == 0.0, never a divide-by-zero.
    config = _config_with_full_menu_llm_enabled(tmp_path)
    config = dataclasses.replace(
        config, social_graph=dataclasses.replace(config.social_graph, enabled=True, topology="erdos_renyi")
    )
    journal_path = run_simulation(config, run_id="isolated-node", llm_client=_ElectingFakeLlmClient())
    events = _events(journal_path)
    isolated_events = [
        e for e in events if e["event_type"] == "pressure_action" and e["citizen_id"] == 3
    ]
    assert isolated_events
    assert all(e["payload"]["ctx"]["neighbors_acting"] == 0.0 for e in isolated_events)


# ── v6b Lot 2: sortition_chamber.py, whole-chamber rotation (§6bis.3) ────

def _sortition_test_citizen(citizen_id: int, **kwargs) -> Citizen:
    return Citizen(
        citizen_id=citizen_id, issue_positions=(0.5,), issue_priorities=(1.0,),
        blank_threshold=0.5, ambition_score=0.5, **kwargs,
    )


def test_default_config_run_emits_no_sortition_rotation_events(tmp_path):
    journal_path = run_simulation(_config_with_output_dir(tmp_path), run_id="baseline")
    events = _events(journal_path)
    assert not [e for e in events if e["event_type"] == "sortition_rotation"]


def test_sortition_rotation_seats_exactly_seats_members_on_the_first_rotation(tmp_path):
    config = _config_with_output_dir(tmp_path)
    config = dataclasses.replace(
        config, sortition_chamber=dataclasses.replace(config.sortition_chamber, enabled=True, seats=3)
    )
    citizens = [_sortition_test_citizen(i) for i in range(10)]
    journal_path = tmp_path / "rotation.jsonl"
    with Journal(journal_path, run_id="rotation") as journal:
        _run_sortition_rotation(citizens, config, journal, tick=0, rng=np.random.default_rng(0))
    events = _events(journal_path)
    rotations = [e for e in events if e["event_type"] == "sortition_rotation"]
    assert len(rotations) == 1
    payload = rotations[0]["payload"]
    assert payload["vacated"] == []
    assert len(payload["seated"]) == 3
    assert payload["pool_relaxed"] == 0
    seated_ids = set(payload["seated"])
    for citizen in citizens:
        if citizen.citizen_id in seated_ids:
            assert citizen.sortition_seat_until_tick == 4
            assert citizen.sortition_terms_served == 1
        else:
            assert citizen.sortition_seat_until_tick is None
            assert citizen.sortition_terms_served == 0


def test_a_second_rotation_vacates_the_first_cohort_and_seats_a_disjoint_one(tmp_path):
    config = _config_with_output_dir(tmp_path)
    config = dataclasses.replace(
        config, sortition_chamber=dataclasses.replace(config.sortition_chamber, enabled=True, seats=3)
    )
    citizens = [_sortition_test_citizen(i) for i in range(10)]
    rng = np.random.default_rng(0)
    journal_path = tmp_path / "rotation.jsonl"
    with Journal(journal_path, run_id="rotation") as journal:
        _run_sortition_rotation(citizens, config, journal, tick=0, rng=rng)
        _run_sortition_rotation(citizens, config, journal, tick=4, rng=rng)
    events = _events(journal_path)
    rotations = [e for e in events if e["event_type"] == "sortition_rotation"]
    assert len(rotations) == 2
    first_seated = set(rotations[0]["payload"]["seated"])
    second_vacated = set(rotations[1]["payload"]["vacated"])
    second_seated = set(rotations[1]["payload"]["seated"])
    assert second_vacated == first_seated
    assert second_seated.isdisjoint(first_seated)  # strict pool not yet exhausted at 10 citizens/3 seats


def test_pool_exhaustion_relaxes_eligibility_without_undersizing_the_chamber(tmp_path):
    # v6b Lot 2's own measured finding, reproduced at a small scale: once
    # the strict never-served pool can't fill `seats`, eligibility relaxes
    # BEFORE it would ever undersize the chamber (not after) -- 10
    # citizens, 3 seats/rotation: exhausts by the 4th rotation (9 served).
    config = _config_with_output_dir(tmp_path)
    config = dataclasses.replace(
        config, sortition_chamber=dataclasses.replace(config.sortition_chamber, enabled=True, seats=3)
    )
    citizens = [_sortition_test_citizen(i) for i in range(10)]
    rng = np.random.default_rng(0)
    journal_path = tmp_path / "rotation.jsonl"
    relaxed_flags = []
    seated_sizes = []
    with Journal(journal_path, run_id="rotation") as journal:
        for i in range(5):
            _run_sortition_rotation(citizens, config, journal, tick=i * 4, rng=rng)
    events = _events(journal_path)
    for e in events:
        if e["event_type"] == "sortition_rotation":
            relaxed_flags.append(bool(e["payload"]["pool_relaxed"]))
            seated_sizes.append(len(e["payload"]["seated"]))
    assert seated_sizes == [3, 3, 3, 3, 3]  # never undersized -- relaxation is proactive
    assert relaxed_flags == [False, False, False, True, True]


def test_sortition_rotation_excludes_a_citizen_at_the_sitting_president(tmp_path):
    config = _config_with_output_dir(tmp_path)
    config = dataclasses.replace(
        config,
        candidacy=dataclasses.replace(config.candidacy, ambition_threshold=0.0),
        sortition_chamber=dataclasses.replace(config.sortition_chamber, enabled=True),
    )
    journal_path = run_simulation(config, run_id="president-excluded")
    events = _events(journal_path)
    elected = next(e for e in events if e["event_type"] == "elected")
    president_id = elected["citizen_id"]
    rotation_at_0 = next(
        e for e in events if e["event_type"] == "sortition_rotation" and e["tick"] == 0
    )
    assert president_id not in rotation_at_0["payload"]["seated"]
    # Ordering pin: rotation runs AFTER the same-tick election, not before.
    assert rotation_at_0["event_id"] > elected["event_id"]


def test_two_sortition_enabled_runs_produce_byte_identical_journals(tmp_path):
    config_a = _config_with_output_dir(tmp_path / "a")
    config_a = dataclasses.replace(
        config_a, sortition_chamber=dataclasses.replace(config_a.sortition_chamber, enabled=True)
    )
    config_b = _config_with_output_dir(tmp_path / "b")
    config_b = dataclasses.replace(
        config_b, sortition_chamber=dataclasses.replace(config_b.sortition_chamber, enabled=True)
    )
    path_a = run_simulation(config_a, run_id="same-run-id")
    path_b = run_simulation(config_b, run_id="same-run-id")
    assert path_a.read_bytes() == path_b.read_bytes()


# ── v6b Lot 3: chamber_deliberation (dt=11, §6bis.3) ─────────────────────

def _config_with_sortition_llm_enabled(output_dir, seats=3) -> PolityConfig:
    config = _config_with_output_dir(output_dir)
    return dataclasses.replace(
        config,
        sortition_chamber=dataclasses.replace(config.sortition_chamber, enabled=True, seats=seats),
        llm=dataclasses.replace(config.llm, enabled=True),
    )


def test_default_config_run_emits_no_chamber_deliberation_events(tmp_path):
    journal_path = run_simulation(_config_with_output_dir(tmp_path), run_id="baseline")
    events = _events(journal_path)
    assert not [e for e in events if e["event_type"] == "chamber_deliberation"]


def test_sortition_chamber_enabled_without_the_llm_never_moves_chamber_position(tmp_path):
    config = _config_with_output_dir(tmp_path)
    config = dataclasses.replace(
        config, sortition_chamber=dataclasses.replace(config.sortition_chamber, enabled=True, seats=3)
    )
    journal_path = run_simulation(config, run_id="deterministic-sortition")
    events = _events(journal_path)
    # The absence of this call IS the fallback (see _run_chamber_deliberation's
    # own docstring): with llm.enabled=False, chamber_position stays pinned
    # to issue_positions forever, zero code, zero events.
    assert not [e for e in events if e["event_type"] == "chamber_deliberation"]
    assert [e for e in events if e["event_type"] == "sortition_rotation"]  # the chamber IS seated


def test_chamber_deliberation_is_journalled_once_per_seated_member_per_tick(tmp_path):
    config = _config_with_sortition_llm_enabled(tmp_path, seats=3)
    journal_path = run_simulation(config, run_id="chamber-deliberation", llm_client=_FakeLlmClient())
    events = _events(journal_path)
    tick0_events = [e for e in events if e["event_type"] == "chamber_deliberation" and e["tick"] == 0]
    assert [e["citizen_id"] for e in tick0_events] == sorted(e["citizen_id"] for e in tick0_events)
    assert len(tick0_events) == 3  # seats
    for e in tick0_events:
        assert set(e["payload"].keys()) == {"shifts", "ctx", "chamber_deviation"}
        assert set(e["payload"]["ctx"].keys()) == {"ticks_left"}
        assert e["motif"] in ("701", "702")
        assert e["codebook_version"] == config.llm.codebook_version


def test_chamber_deliberation_journals_chamber_deviation_after_the_shift_lands(tmp_path):
    # v6b Lot 4: chamber_deviation is the POST-decision value -- computed
    # AFTER member.chamber_position is updated, never a stale pre-shift
    # reading. Direct _run_chamber_deliberation call (not a full run) with a
    # fake client returning a fixed, hand-verifiable +0.1 shift on the
    # single-dimension _sortition_test_citizen fixture: issue_positions
    # (0.5,) -> chamber_position (0.6,), so
    # weighted_euclidean((0.5,), (0.6,), (1.0,)) == 0.1 exactly.
    config = _config_with_output_dir(tmp_path)
    config = dataclasses.replace(
        config,
        sortition_chamber=dataclasses.replace(config.sortition_chamber, enabled=True, seats=3),
        llm=dataclasses.replace(config.llm, enabled=True),
    )
    citizens = [
        _sortition_test_citizen(i, sortition_seat_until_tick=4, chamber_position=(0.5,)) for i in range(3)
    ]

    class _ShiftingClient:
        def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
            payload = json.loads(user_prompt)
            decisions = [
                {"cid": m["cid"], "shifts": [{"dimension": 0, "delta": 0.1}], "motif": 702}
                for m in payload["members"]
            ]
            return json.dumps({"decisions": decisions})

    journal_path = tmp_path / "deviation.jsonl"
    with Journal(journal_path, run_id="deviation") as journal:
        _run_chamber_deliberation(citizens, config, journal, tick=0, llm_client=_ShiftingClient())
    events = _events(journal_path)
    chamber_events = sorted(
        (e for e in events if e["event_type"] == "chamber_deliberation"), key=lambda e: e["citizen_id"]
    )
    assert len(chamber_events) == 3
    for e, citizen in zip(chamber_events, citizens):
        assert citizen.chamber_position == pytest.approx((0.6,))
        expected = chamber_deviation(citizen)
        assert expected == pytest.approx(0.1)
        assert e["payload"]["chamber_deviation"] == pytest.approx(expected)


def test_chamber_deviation_is_zero_when_the_model_returns_a_sincere_decision(tmp_path):
    config = _config_with_output_dir(tmp_path)
    config = dataclasses.replace(
        config,
        sortition_chamber=dataclasses.replace(config.sortition_chamber, enabled=True, seats=3),
        llm=dataclasses.replace(config.llm, enabled=True),
    )
    citizens = [
        _sortition_test_citizen(i, sortition_seat_until_tick=4, chamber_position=(0.5,)) for i in range(3)
    ]

    class _SincereClient:
        def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
            payload = json.loads(user_prompt)
            decisions = [{"cid": m["cid"], "shifts": [], "motif": 701} for m in payload["members"]]
            return json.dumps({"decisions": decisions})

    journal_path = tmp_path / "sincere.jsonl"
    with Journal(journal_path, run_id="sincere") as journal:
        _run_chamber_deliberation(citizens, config, journal, tick=0, llm_client=_SincereClient())
    events = _events(journal_path)
    chamber_events = [e for e in events if e["event_type"] == "chamber_deliberation"]
    assert len(chamber_events) == 3
    for e in chamber_events:
        assert e["payload"]["chamber_deviation"] == 0.0
        assert e["motif"] == "701"


def test_chamber_deliberation_never_fires_while_the_accountability_gate_is_entirely_off(tmp_path):
    # sortition_chamber.enabled + llm.enabled alone, with mandate/legitimacy/
    # awakening all at their shipped-off default -- chamber_deliberation is
    # dispatched directly from the tick loop, never nested inside
    # _run_accountability_phase, so it must fire regardless.
    config = _config_with_sortition_llm_enabled(tmp_path, seats=3)
    assert config.mandate.enabled is False
    assert config.legitimacy.enabled is False
    assert config.awakening.enabled is False
    journal_path = run_simulation(config, run_id="chamber-only", llm_client=_FakeLlmClient())
    events = _events(journal_path)
    assert [e for e in events if e["event_type"] == "chamber_deliberation"]
    assert not [e for e in events if e["event_type"] in ("pressure_action", "legitimacy_updated", "representative_response")]


def test_chamber_position_resets_to_the_sincere_position_at_each_new_seating(tmp_path):
    config = _config_with_output_dir(tmp_path)
    config = dataclasses.replace(
        config, sortition_chamber=dataclasses.replace(config.sortition_chamber, enabled=True, seats=3)
    )
    citizens = [_sortition_test_citizen(i) for i in range(4)]
    rng = np.random.default_rng(0)
    journal_path = tmp_path / "reseat.jsonl"
    with Journal(journal_path, run_id="reseat") as journal:
        _run_sortition_rotation(citizens, config, journal, tick=0, rng=rng)
        seated_first = [c for c in citizens if c.sortition_seat_until_tick is not None]
        for member in seated_first:
            member.chamber_position = tuple(x + 0.3 for x in member.chamber_position)  # simulate drift
        _run_sortition_rotation(citizens, config, journal, tick=4, rng=rng)
    for citizen in citizens:
        if citizen.sortition_seat_until_tick is not None:
            assert citizen.chamber_position == citizen.issue_positions


def test_chamber_deliberation_runs_on_every_tick_not_just_rotation_ticks(tmp_path):
    config = _config_with_sortition_llm_enabled(tmp_path, seats=3)
    journal_path = run_simulation(config, run_id="every-tick", llm_client=_FakeLlmClient())
    events = _events(journal_path)
    rotation_ticks = {e["tick"] for e in events if e["event_type"] == "sortition_rotation"}
    chamber_ticks = {e["tick"] for e in events if e["event_type"] == "chamber_deliberation"}
    # Between two rotation ticks the roster is unchanged, but chamber_deliberation
    # still fires every intermediate tick.
    assert any(tick not in rotation_ticks for tick in chamber_ticks)


def test_two_chamber_deliberation_llm_runs_produce_byte_identical_journals(tmp_path):
    config_a = _config_with_sortition_llm_enabled(tmp_path / "a", seats=3)
    config_b = _config_with_sortition_llm_enabled(tmp_path / "b", seats=3)
    path_a = run_simulation(config_a, run_id="same-run-id", llm_client=_FakeLlmClient())
    path_b = run_simulation(config_b, run_id="same-run-id", llm_client=_FakeLlmClient())
    assert path_a.read_bytes() == path_b.read_bytes()


def test_no_chamber_deliberation_llm_call_with_an_empty_chamber(tmp_path):
    config = _config_with_output_dir(tmp_path)
    config = dataclasses.replace(
        config,
        sortition_chamber=dataclasses.replace(config.sortition_chamber, enabled=True, seats=3),
        llm=dataclasses.replace(config.llm, enabled=True),
    )
    citizens: list[Citizen] = []  # deliberately drained -- no eligible pool at all

    class _RaisingClient:
        def complete_json(self, **kwargs):
            raise AssertionError("no client call expected for an empty chamber")

    journal_path = tmp_path / "empty.jsonl"
    with Journal(journal_path, run_id="empty") as journal:
        _run_chamber_deliberation(citizens, config, journal, tick=0, llm_client=_RaisingClient())
    events = _events(journal_path)
    assert not [e for e in events if e["event_type"] == "chamber_deliberation"]


# ── clamped_at_bound (apply_shifts's own observability gap, resolved) ────
# clamped_dimensions itself is unit-tested in test_polity_llm_behavior_engine.py;
# these confirm the three run_polity_simulation.py call sites (dt=5/6/11)
# actually journal the resulting event, adjacent to the decision it
# describes, only when a dimension genuinely saturates.

def test_default_config_run_emits_no_clamped_at_bound_events(tmp_path):
    journal_path = run_simulation(_config_with_output_dir(tmp_path), run_id="baseline")
    events = _events(journal_path)
    assert not [e for e in events if e["event_type"] == "clamped_at_bound"]


def test_chamber_deliberation_clamp_journals_clamped_at_bound_adjacent_to_the_decision(tmp_path):
    config = _config_with_output_dir(tmp_path)
    config = dataclasses.replace(
        config,
        sortition_chamber=dataclasses.replace(config.sortition_chamber, enabled=True, seats=1),
        llm=dataclasses.replace(config.llm, enabled=True),
    )
    citizens = [_sortition_test_citizen(0, sortition_seat_until_tick=4, chamber_position=(0.9,))]

    class _BigShiftClient:
        def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
            payload = json.loads(user_prompt)
            decisions = [
                {"cid": m["cid"], "shifts": [{"dimension": 0, "delta": 0.3}], "motif": 702}
                for m in payload["members"]
            ]
            return json.dumps({"decisions": decisions})

    journal_path = tmp_path / "chamber-clamp.jsonl"
    with Journal(journal_path, run_id="chamber-clamp") as journal:
        _run_chamber_deliberation(citizens, config, journal, tick=0, llm_client=_BigShiftClient())
    events = _events(journal_path)
    decision_event = next(e for e in events if e["event_type"] == "chamber_deliberation")
    clamp_event = next(e for e in events if e["event_type"] == "clamped_at_bound")
    assert clamp_event["tick"] == 0
    assert clamp_event["citizen_id"] == 0
    assert clamp_event["motif"] is None
    assert clamp_event["codebook_version"] == ""
    assert clamp_event["payload"] == {"decision_event": "chamber_deliberation", "dimensions": [0]}
    # adjacent: the very next event, immediately after the decision it describes.
    assert events.index(clamp_event) == events.index(decision_event) + 1


def test_chamber_deliberation_without_a_clamp_emits_no_clamped_at_bound_event(tmp_path):
    config = _config_with_output_dir(tmp_path)
    config = dataclasses.replace(
        config,
        sortition_chamber=dataclasses.replace(config.sortition_chamber, enabled=True, seats=1),
        llm=dataclasses.replace(config.llm, enabled=True),
    )
    citizens = [_sortition_test_citizen(0, sortition_seat_until_tick=4, chamber_position=(0.5,))]

    class _SmallShiftClient:
        def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
            payload = json.loads(user_prompt)
            decisions = [
                {"cid": m["cid"], "shifts": [{"dimension": 0, "delta": 0.1}], "motif": 702}
                for m in payload["members"]
            ]
            return json.dumps({"decisions": decisions})

    journal_path = tmp_path / "chamber-no-clamp.jsonl"
    with Journal(journal_path, run_id="chamber-no-clamp") as journal:
        _run_chamber_deliberation(citizens, config, journal, tick=0, llm_client=_SmallShiftClient())
    events = _events(journal_path)
    assert [e for e in events if e["event_type"] == "chamber_deliberation"]  # the decision itself fired
    assert not [e for e in events if e["event_type"] == "clamped_at_bound"]


def test_representative_response_clamp_journals_clamped_at_bound(tmp_path):
    config = _config_with_mandate_llm_enabled(tmp_path)
    holder = Citizen(
        citizen_id=0, issue_positions=(0.9,), issue_priorities=(1.0,),
        blank_threshold=0.5, ambition_score=0.5, role=Role.ELECTED, office=Office.PRESIDENT,
        legitimacy_capital=0.9, mandate_strength=0.9,  # comfortably above recall_floor
    )
    holder.pledged_platform = (0.9,)
    holder.revealed_position = (0.9,)

    class _BigShiftClient:
        def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
            payload = json.loads(user_prompt)
            decisions = [
                {"cid": h["cid"], "shifts": [{"dimension": 0, "delta": 0.3}], "stance": 1, "motif": 301}
                for h in payload["holders"]
            ]
            return json.dumps({"decisions": decisions})

    journal_path = tmp_path / "response-clamp.jsonl"
    with Journal(journal_path, run_id="response-clamp") as journal:
        _run_accountability_phase([holder], config, journal, tick=0, llm_client=_BigShiftClient())
    events = _events(journal_path)
    decision_event = next(e for e in events if e["event_type"] == "representative_response")
    clamp_event = next(e for e in events if e["event_type"] == "clamped_at_bound")
    assert clamp_event["citizen_id"] == 0
    assert clamp_event["motif"] is None
    assert clamp_event["payload"] == {"decision_event": "representative_response", "dimensions": [0]}
    assert events.index(clamp_event) == events.index(decision_event) + 1
    assert holder.revealed_position == pytest.approx((1.0,))


def test_campaign_positioning_clamp_journals_clamped_at_bound(tmp_path):
    # decide_candidacies (the "citizens" branch) batches population-scale via
    # chunk_voters, which floors at MIN_SAFE_BATCH_SIZE=20 -- a 1-citizen
    # population would raise NotImplementedError before ever reaching
    # positioning. 19 filler electors (never declare, party_affiliation
    # irrelevant) get the count above that floor; only cid=0 (party 1)
    # actually declares, so party 1 stays uncontested (no
    # party_nomination_choice/"parties" call expected).
    config = _config_with_llm_enabled(tmp_path)
    nominee = Citizen(
        citizen_id=0, issue_positions=(0.9,), issue_priorities=(1.0,),
        blank_threshold=0.5, ambition_score=0.5, party_affiliation=1,
    )
    fillers = [
        Citizen(citizen_id=i, issue_positions=(0.5,), issue_priorities=(1.0,), blank_threshold=0.5, ambition_score=0.0)
        for i in range(1, 20)
    ]
    citizens = [nominee, *fillers]
    parties = [Party(party_id=1, platform=(0.5,))]

    class _BigShiftClient:
        def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
            payload = json.loads(user_prompt)
            if "citizens" in payload:
                decisions = [
                    {"cid": c["cid"], "outcome": 1 if c["cid"] == 0 else 0, "motif": 203 if c["cid"] == 0 else 201}
                    for c in payload["citizens"]
                ]
                return json.dumps({"decisions": decisions})
            if "nominees" in payload:
                decisions = [
                    {"cid": n["cid"], "shifts": [{"dimension": 0, "delta": 0.3}], "motif": 602}
                    for n in payload["nominees"]
                ]
                return json.dumps({"decisions": decisions})
            raise AssertionError(f"unexpected payload shape (single-candidate party should be uncontested, "
                                  f"no party_nomination_choice call expected): {sorted(payload.keys())}")

    journal_path = tmp_path / "positioning-clamp.jsonl"
    with Journal(journal_path, run_id="positioning-clamp") as journal:
        _declare_nominees_llm(citizens, parties, config, journal, tick=0, llm_client=_BigShiftClient())
    events = _events(journal_path)
    decision_event = next(e for e in events if e["event_type"] == "campaign_positioning")
    clamp_event = next(e for e in events if e["event_type"] == "clamped_at_bound")
    assert clamp_event["citizen_id"] == 0
    assert clamp_event["motif"] is None
    assert clamp_event["payload"] == {"decision_event": "campaign_positioning", "dimensions": [0]}
    assert events.index(clamp_event) == events.index(decision_event) + 1
    assert nominee.pledged_platform == pytest.approx((1.0,))


# ── LLM candidacy path (v2 increment 2) ──────────────────────────────────

def test_llm_path_journals_candidacy_considered_for_every_evaluated_citizen(tmp_path):
    config = _config_with_llm_enabled(tmp_path)
    journal_path = run_simulation(config, run_id="llm-candidacy", llm_client=_FakeLlmClient())
    events = _events(journal_path)
    considered_events = [e for e in events if e["event_type"] == "candidacy_considered"]
    # One candidacy_considered event per citizen per presidential election
    # (8 in the default calendar) -- including the citizens who declined,
    # which the deterministic baseline never journals at all.
    assert len(considered_events) == config.run.population_size * 8
    assert all(e["payload"]["path"] == "dominant" for e in considered_events)
    assert all(e["codebook_version"] == config.llm.codebook_version for e in considered_events)
    assert {e["payload"]["outcome"] for e in considered_events} == {0, 1}


def test_llm_path_journals_candidacy_declared_only_for_outcome_one(tmp_path):
    config = _config_with_llm_enabled(tmp_path)
    journal_path = run_simulation(config, run_id="llm-candidacy-declared", llm_client=_FakeLlmClient())
    events = _events(journal_path)
    declared_cids = {
        e["citizen_id"] for e in events if e["event_type"] == "candidacy_declared" and e["payload"].get("path") == "dominant"
    }
    considered_declared_cids = {
        e["citizen_id"] for e in events if e["event_type"] == "candidacy_considered" and e["payload"]["outcome"] == 1
    }
    assert declared_cids.issubset(considered_declared_cids)


def test_llm_path_journals_nomination_lost_for_declared_but_unpicked_citizens(tmp_path):
    config = _config_with_llm_enabled(tmp_path)
    journal_path = run_simulation(config, run_id="llm-nomination-lost", llm_client=_FakeLlmClient())
    events = _events(journal_path)
    lost_events = [e for e in events if e["event_type"] == "nomination_lost"]
    assert len(lost_events) > 0  # default config has multiple ambitious members per party most ticks
    considered_declared_cids = {
        e["citizen_id"] for e in events if e["event_type"] == "candidacy_considered" and e["payload"]["outcome"] == 1
    }
    # Every lost citizen was genuinely LLM-approved (outcome=1) at some
    # point, and never also the party's chosen nominee in that same tick.
    assert set(e["citizen_id"] for e in lost_events).issubset(considered_declared_cids)
    for event in lost_events:
        assert event["citizen_id"] not in {
            e["citizen_id"]
            for e in events
            if e["event_type"] == "candidacy_declared" and e["tick"] == event["tick"]
        }


# ── LLM party-nomination path (v2 increment 3) ───────────────────────────

def test_llm_path_journals_party_nomination_choice_only_for_contested_parties(tmp_path):
    config = _config_with_llm_enabled(tmp_path)
    journal_path = run_simulation(config, run_id="llm-party-nomination", llm_client=_FakeLlmClient())
    events = _events(journal_path)
    nomination_events = [e for e in events if e["event_type"] == "party_nomination_choice"]
    # Default config + _FakeLlmClient's 0.1 ambition cutoff already produces
    # nomination_lost events (see the test above) -- proof some party is
    # contested most ticks, so this event must appear too.
    assert len(nomination_events) > 0
    for event in nomination_events:
        assert event["codebook_version"] == config.llm.codebook_version
        assert event["motif"] == "206"
        assert len(event["payload"]["contenders"]) >= 2
        assert event["citizen_id"] in event["payload"]["contenders"]

    declared = {
        (e["tick"], e["citizen_id"])
        for e in events
        if e["event_type"] == "candidacy_declared" and e["payload"].get("path") == "dominant"
    }
    for event in nomination_events:
        # Every contested party's LLM-chosen winner is also the tick's
        # candidacy_declared nominee -- decide_party_nominations' output
        # actually drives who runs, not just an unused side record.
        assert (event["tick"], event["citizen_id"]) in declared


# ── LLM campaign-positioning path (v2 increment 4) ───────────────────────

def test_llm_path_journals_campaign_positioning_once_per_dominant_nominee(tmp_path):
    config = _config_with_llm_enabled(tmp_path)
    journal_path = run_simulation(config, run_id="llm-campaign-positioning", llm_client=_FakeLlmClient())
    events = _events(journal_path)
    positioning_events = [e for e in events if e["event_type"] == "campaign_positioning"]
    declared_dominant = [
        e for e in events if e["event_type"] == "candidacy_declared" and e["payload"].get("path") == "dominant"
    ]
    assert len(positioning_events) > 0
    assert len(positioning_events) == len(declared_dominant)
    for event in positioning_events:
        assert event["codebook_version"] == config.llm.codebook_version
        assert event["motif"] == "602"
        # Non-empty shifts (the fake always shifts dimension 0 by +0.1) is
        # the observable proxy for a real pledged_platform change -- the
        # actual position math (apply_shifts) is unit-tested separately.
        assert event["payload"]["shifts"] == [{"dimension": 0, "delta": 0.1}]

    # Positioning fires for exactly the same (tick, nominee) pairs that get
    # declared dominant -- confirms rupture candidates are excluded (they're
    # never part of `nominees` when this runs) and every dominant nominee is
    # covered, not just a subset.
    declared_ticks_and_cids = {(e["tick"], e["citizen_id"]) for e in declared_dominant}
    positioning_ticks_and_cids = {(e["tick"], e["citizen_id"]) for e in positioning_events}
    assert positioning_ticks_and_cids == declared_ticks_and_cids


# ── LLM coalition path (v2 increment 5) ──────────────────────────────────

def test_llm_path_journals_coalition_decision_per_seated_non_initiator_party(tmp_path):
    config = _config_with_llm_enabled(tmp_path)
    journal_path = run_simulation(config, run_id="llm-coalition", llm_client=_FakeLlmClient())
    events = _events(journal_path)
    decision_events = [e for e in events if e["event_type"] == "coalition_decision"]
    aggregate_events = [e for e in events if e["event_type"] in ("coalition_formed", "coalition_failed")]

    assert len(aggregate_events) == 8  # one per legislative election, same as the deterministic baseline
    assert len(decision_events) > 0  # default 5-party config produces contested legislative ticks

    for event in decision_events:
        assert event["codebook_version"] == config.llm.codebook_version
        assert event["motif"] == "501"
        assert event["payload"]["action"] == 1
        assert "initiator" in event["payload"]
        assert "party_id" in event["payload"]


def test_llm_path_aggregate_coalition_payload_keeps_coalition_key_shape(tmp_path):
    # metrics.py's is_cohabitation/coalition_lifespans read payload["coalition"]
    # as a plain list[int] | None -- this must never change shape, on either
    # path, or those consumers break silently. v7 Lot 2 adds "rounds_used"
    # additively (see plan-coalition-negotiation-v7.md §4); _FakeLlmClient
    # never fails, so aborted_at_round/rounds_completed never fire here --
    # see test_llm_path_coalition_negotiation_aborts_gracefully_on_a_round_
    # two_failure for that shape instead.
    config = _config_with_llm_enabled(tmp_path)
    journal_path = run_simulation(config, run_id="llm-coalition-shape", llm_client=_FakeLlmClient())
    events = _events(journal_path)
    aggregate_events = [e for e in events if e["event_type"] in ("coalition_formed", "coalition_failed")]
    assert aggregate_events
    for event in aggregate_events:
        assert set(event["payload"].keys()) == {"coalition", "seats", "rounds_used"}
        assert event["payload"]["coalition"] is None or isinstance(event["payload"]["coalition"], list)


class _CoalitionRoundTwoFailsClient(_FakeLlmClient):
    """Identical to _FakeLlmClient for every other decision type. Coalition's
    first round succeeds (unanimous join, same as the parent); every
    coalition call after that returns malformed JSON, isolating
    _form_and_journal_coalition_llm's new aborted_at_round branch inside a
    real run -- not just decide_coalition in isolation (see
    test_decide_coalition_aborts_gracefully_on_a_round_two_failure in
    test_polity_llm_behavior_engine.py for that narrower unit test).
    Party composition never changes in this config (birth/death/split all
    off), so the responder set is identical across every legislative
    election -- a plain call counter would misattribute a LATER election's
    own round 1 as a revision round. The test that uses this fake
    constrains run.duration_years so only one election ever happens, side-
    stepping the ambiguity entirely rather than trying to disambiguate it."""

    def __init__(self):
        self._coalition_calls = 0

    def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
        payload = json.loads(user_prompt)
        if "responders" in payload:
            self._coalition_calls += 1
            if self._coalition_calls > 1:
                return "not json"
            decisions = [{"party_id": r["party_id"], "action": 1, "motif": 501} for r in payload["responders"]]
            return json.dumps({"decisions": decisions})
        return super().complete_json(
            system_prompt=system_prompt, user_prompt=user_prompt, json_schema=json_schema,
            max_tokens=max_tokens, think=think,
        )


def test_llm_path_coalition_negotiation_aborts_gracefully_on_a_round_two_failure(tmp_path):
    config = _config_with_llm_enabled(tmp_path)
    config = dataclasses.replace(
        config,
        run=dataclasses.replace(config.run, duration_years=5),  # exactly one legislative election, see the fake's own docstring
        llm=dataclasses.replace(config.llm, max_batch_replays=0),
    )
    journal_path = run_simulation(config, run_id="llm-coalition-abort", llm_client=_CoalitionRoundTwoFailsClient())
    events = _events(journal_path)

    failed_events = [e for e in events if e["event_type"] == "coalition_failed"]
    formed_events = [e for e in events if e["event_type"] == "coalition_formed"]
    assert len(failed_events) == 1  # isolated to exactly one election, see duration_years above
    assert formed_events == []
    event = failed_events[0]
    assert event["payload"]["coalition"] is None
    assert event["payload"]["aborted_at_round"] == 2
    assert event["payload"]["rounds_completed"] == 1
    assert set(event["payload"].keys()) == {"coalition", "seats", "aborted_at_round", "rounds_completed"}

    # round 1's own decisions are still journaled even though the
    # negotiation as a whole aborted -- nothing already-completed is lost.
    decision_events = [e for e in events if e["event_type"] == "coalition_decision"]
    assert decision_events
    assert all(e["payload"]["round"] == 1 for e in decision_events)


def test_deterministic_path_emits_no_coalition_decision_events(tmp_path):
    journal_path = run_simulation(_config_with_output_dir(tmp_path), run_id="baseline-coalition")
    events = _events(journal_path)
    assert [e for e in events if e["event_type"] == "coalition_decision"] == []
    aggregate_events = [e for e in events if e["event_type"] in ("coalition_formed", "coalition_failed")]
    assert len(aggregate_events) == 8
    for event in aggregate_events:
        assert set(event["payload"].keys()) == {"coalition", "seats"}


def test_llm_path_all_decline_produces_coalition_failed(tmp_path):
    class _AllDeclineClient:
        """Same dispatch as _FakeLlmClient for every decision type except
        coalition, where every responder refuses -- isolates
        assemble_coalition's all-decline None contract inside a full run."""

        def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
            payload = json.loads(user_prompt)
            if "citizens" in payload:
                decisions = [
                    {"cid": c["cid"], "outcome": 1, "motif": 203}
                    if c["ambition_score"] >= 0.1
                    else {"cid": c["cid"], "outcome": 0, "motif": 201}
                    for c in payload["citizens"]
                ]
                return json.dumps({"decisions": decisions})
            if "parties" in payload:
                decisions = [
                    {
                        "party_id": p["party_id"],
                        "winner_position": max(p["candidates"], key=lambda c: c["ambition_score"])["position"],
                        "motif": 206,
                    }
                    for p in payload["parties"]
                ]
                return json.dumps({"decisions": decisions})
            if "nominees" in payload:
                decisions = [{"cid": n["cid"], "shifts": [], "motif": 601} for n in payload["nominees"]]
                return json.dumps({"decisions": decisions})
            if "responders" in payload:
                decisions = [{"party_id": r["party_id"], "action": 2, "motif": 504} for r in payload["responders"]]
                return json.dumps({"decisions": decisions})
            decisions = [{"cid": v["cid"], "blank": 1, "ranking": [], "motif": 101} for v in payload["voters"]]
            return json.dumps({"decisions": decisions})

    config = _config_with_llm_enabled(tmp_path)
    journal_path = run_simulation(config, run_id="llm-coalition-all-decline", llm_client=_AllDeclineClient())
    events = _events(journal_path)
    decision_events = [e for e in events if e["event_type"] == "coalition_decision"]
    assert decision_events  # confirms responders were actually asked at least once
    assert all(e["payload"]["action"] == 2 for e in decision_events)
    failed_events = [e for e in events if e["event_type"] == "coalition_failed"]
    assert len(failed_events) > 0
    for event in failed_events:
        assert event["payload"]["coalition"] is None


def test_two_llm_coalition_runs_with_the_same_seed_produce_byte_identical_journals(tmp_path):
    config_a = _config_with_llm_enabled(tmp_path / "a")
    config_b = _config_with_llm_enabled(tmp_path / "b")
    path_a = run_simulation(config_a, run_id="same-run-id", llm_client=_FakeLlmClient())
    path_b = run_simulation(config_b, run_id="same-run-id", llm_client=_FakeLlmClient())
    assert path_a.read_bytes() == path_b.read_bytes()


def test_unsupported_presidential_method_raises_before_any_work(tmp_path):
    config = _config_with_output_dir(tmp_path)
    config = dataclasses.replace(
        config, institutions=dataclasses.replace(config.institutions, presidential_method="star")
    )
    with pytest.raises(NotImplementedError, match="star"):
        run_simulation(config, run_id="r")
    assert not (tmp_path / "r").exists()


# ── v5 Lot 2: shock.py -- Poisson scandal + AR(1) economic climate (§8) ────

def _config_with_events_enabled(output_dir, **overrides) -> PolityConfig:
    # awakening.enabled + context_modulation.event_salience are forced on by
    # config.py's own cross-field rule whenever events.enabled is true --
    # replicated here since dataclasses.replace bypasses load_config's own
    # validation. That forcing is exactly why _config_with_awakening_but_no_events
    # below exists: the off-arm of an events on/off comparison has to carry the
    # same awakening config, or the comparison silently measures awakening too.
    return dataclasses.replace(
        _config_with_awakening_but_no_events(output_dir),
        events=dataclasses.replace(
            load_config().events,
            **{**{"enabled": True, "scandal_enabled": True, "economic_shock_enabled": True}, **overrides},
        ),
    )


def _config_with_awakening_but_no_events(output_dir) -> PolityConfig:
    """The correct off-arm for any events on/off comparison: identical to
    _config_with_events_enabled except events stays off.

    Until ADR-002 was closed (2026-08-29) the off-arm was
    _config_with_output_dir, whose awakening is OFF -- and that comparison only
    passed because the shipped ambition_threshold of 0.7 left the presidency
    permanently vacant, so awakening had no officeholder to produce
    pressure_action events about and was inert on both sides by accident. At the
    calibrated threshold the on-arm emits 1421 pressure_action events the
    off-arm never had (64 journal lines vs 1485), which is a difference in
    AWAKENING, not in events -- the variable the test names."""
    config = _config_with_output_dir(output_dir)
    return dataclasses.replace(
        config,
        awakening=dataclasses.replace(
            config.awakening,
            enabled=True,
            context_modulation=dataclasses.replace(config.awakening.context_modulation, event_salience=True),
        ),
    )


def test_default_config_run_emits_no_shock_events(tmp_path):
    journal_path = run_simulation(_config_with_output_dir(tmp_path), run_id="baseline")
    events = _events(journal_path)
    assert not [e for e in events if e["event_type"] in ("scandal_occurred", "economic_shock_tick")]


def test_events_enabled_but_structurally_inert_matches_the_default_journal_byte_for_byte(tmp_path):
    # scandal_rate_per_tick=0.0 and economy_ar1_sigma=0.0 both draw from the
    # rng every tick (the sub-mechanisms are genuinely wired, not skipped)
    # but can never produce a nonzero outcome -- an EXACT, not probabilistic,
    # proof that turning events.enabled on is byte-identical to leaving it
    # off, the same register as v4 Lot 9's own analogous test.
    # The off-arm carries the SAME awakening config as the on-arm (see
    # _config_with_awakening_but_no_events) so the only variable is `events`.
    path_off = run_simulation(_config_with_awakening_but_no_events(tmp_path / "off"), run_id="same-run-id")
    path_on = run_simulation(
        _config_with_events_enabled(tmp_path / "on", scandal_rate_per_tick=0.0, economy_ar1_sigma=0.0),
        run_id="same-run-id",
    )
    events_on = _events(path_on)
    assert not [e for e in events_on if e["event_type"] in ("scandal_occurred", "economic_shock_tick")]
    assert path_off.read_bytes() == path_on.read_bytes()


def test_two_runs_with_events_enabled_produce_byte_identical_journals(tmp_path):
    config_kwargs = dict(scandal_rate_per_tick=1.0, economy_shock_threshold=0.0)
    path_a = run_simulation(_config_with_events_enabled(tmp_path / "a", **config_kwargs), run_id="same-run-id")
    path_b = run_simulation(_config_with_events_enabled(tmp_path / "b", **config_kwargs), run_id="same-run-id")
    assert path_a.read_bytes() == path_b.read_bytes()


def test_a_real_firing_events_run_produces_scandal_and_economic_shock_events(tmp_path):
    config = _config_with_events_enabled(tmp_path, scandal_rate_per_tick=1.0, economy_shock_threshold=0.0)
    journal_path = run_simulation(config, run_id="events-firing")
    events = _events(journal_path)
    scandals = [e for e in events if e["event_type"] == "scandal_occurred"]
    shocks = [e for e in events if e["event_type"] == "economic_shock_tick"]
    # scandal_rate_per_tick=1.0 -> exactly one scandal_occurred per tick.
    assert len(scandals) == config.run.total_ticks + 1
    # Target resolution is exercised in BOTH directions here, which it was not
    # before ADR-002 was closed: the shipped threshold used to leave the
    # presidency permanently vacant, so every target was null and the null
    # branch was the only one this run ever reached. At the calibrated
    # threshold a president exists for most of the run, so both branches fire.
    # (The per-branch contract itself is asserted by
    # test_scandal_occurred_targets_the_sitting_president_and_is_null_on_vacancy.)
    targets = {e["payload"]["target"] for e in scandals}
    assert None in targets, "tick 0 precedes the first election -- a vacancy must still be reachable"
    assert targets - {None}, "a sitting president must be targeted once one is elected"
    # economy_shock_threshold=0.0 -> abs(x) >= 0.0 is true for every x, so
    # every tick's step crosses, including tick 0 (economy_x is stepped
    # once, from its seeded 0.0, before tick 0's journal write happens).
    assert len(shocks) == config.run.total_ticks + 1
    for e in shocks:
        assert abs(e["payload"]["x"]) >= 0.0
        assert e["payload"]["threshold"] == 0.0


def _shock_test_citizen(cid, office=Office.NONE, role=Role.ELECTOR):
    return Citizen(
        citizen_id=cid,
        issue_positions=(0.5,),
        issue_priorities=(1.0,),
        blank_threshold=0.5,
        ambition_score=0.5,
        role=role,
        office=office,
    )


def test_scandal_occurred_targets_the_sitting_president_and_is_null_on_vacancy(tmp_path):
    # Direct call to _run_exogenous_events, not run_simulation -- this
    # function is deliberately independent of _run_accountability_phase (it
    # never calls select_consulted/awakening_threshold), so exercising it
    # directly against a hand-built citizen list is both the simplest test
    # AND the one that structurally cannot trip awakening_threshold's
    # still-pending event_salience guard.
    events_config = dataclasses.replace(
        load_config().events, enabled=True, scandal_enabled=True, scandal_rate_per_tick=1.0,
        economic_shock_enabled=False,
    )
    config = dataclasses.replace(load_config(), events=events_config)

    vacant_citizens = [_shock_test_citizen(0)]
    journal_path = tmp_path / "vacancy.jsonl"
    with Journal(journal_path, run_id="vacancy") as journal:
        _run_exogenous_events(vacant_citizens, config, journal, tick=0, rng=np.random.default_rng(0), economy_x=0.0)
    events = _events(journal_path)
    scandal_events = [e for e in events if e["event_type"] == "scandal_occurred"]
    assert len(scandal_events) == 1
    assert scandal_events[0]["payload"]["target"] is None
    assert scandal_events[0]["citizen_id"] is None

    president = _shock_test_citizen(7, office=Office.PRESIDENT, role=Role.ELECTED)
    occupied_citizens = [_shock_test_citizen(0), president]
    journal_path2 = tmp_path / "occupied.jsonl"
    with Journal(journal_path2, run_id="occupied") as journal:
        _run_exogenous_events(
            occupied_citizens, config, journal, tick=0, rng=np.random.default_rng(0), economy_x=0.0
        )
    events2 = _events(journal_path2)
    scandal_events2 = [e for e in events2 if e["event_type"] == "scandal_occurred"]
    assert len(scandal_events2) == 1
    assert scandal_events2[0]["payload"]["target"] == 7
    assert scandal_events2[0]["citizen_id"] == 7


def test_economic_shock_tick_only_journals_above_threshold(tmp_path):
    # economy_ar1_sigma=0.3 against phi=0.8 gives a steady-state std of
    # sigma/sqrt(1-phi^2)=0.5 -- right at the shipped threshold (0.5), so a
    # 120-tick run reliably produces both crossing and non-crossing ticks at
    # seed=42, proving the gate is neither vacuously always-true nor
    # never-true.
    config = _config_with_events_enabled(tmp_path, scandal_enabled=False, economy_ar1_sigma=0.3)
    journal_path = run_simulation(config, run_id="threshold")
    events = _events(journal_path)
    shocks = [e for e in events if e["event_type"] == "economic_shock_tick"]
    assert shocks
    assert len(shocks) < config.run.total_ticks + 1
    for e in shocks:
        assert abs(e["payload"]["x"]) >= config.events.economy_shock_threshold


# event_salience's own awakening_threshold coverage moved to
# test_polity_accountability.py (v5 Lot 3) -- the guard this test used to
# pin (`awakening_threshold` raising NotImplementedError for event_salience)
# was removed by that lot; awakening_threshold's real event_salience
# behavior is tested where its other three context_modulation terms already
# are.


# ── v5 Lot 3: event_salience, awakening extension, reaction_to_event ──────

def _config_with_events_and_awakening_enabled(output_dir, **overrides) -> PolityConfig:
    # Unlike _config_with_events_enabled, this helper is meant for tests
    # that WANT a real elected officeholder + real consultation dynamics --
    # ambition_threshold=0.0 guarantees a winner, safe now that v5 Lot 3
    # removed awakening_threshold's event_salience guard.
    config = _config_with_events_enabled(output_dir, **overrides)
    return dataclasses.replace(config, candidacy=dataclasses.replace(config.candidacy, ambition_threshold=0.0))


def _step_zero_direct_call_config() -> PolityConfig:
    # _run_accountability_phase's own top-level guard
    # (mandate.enabled or legitimacy.enabled or awakening.enabled) returns
    # early at the shipped default (all three False) -- legitimacy.enabled
    # is the minimal flag to flip so step 0 actually runs, and since these
    # tests build citizen lists with no PRESIDENT, the per-holder loop
    # (steps 1-6) stays a no-op regardless, keeping the journal to exactly
    # step 0's own events.
    config = load_config()
    return dataclasses.replace(config, legitimacy=dataclasses.replace(config.legitimacy, enabled=True))


def test_step_zero_direct_call_scandal_fired_journals_one_reaction_per_citizen(tmp_path):
    config = _step_zero_direct_call_config()
    citizens = [_shock_test_citizen(i) for i in range(5)]
    exogenous = ExogenousEventsOutcome(economy_x=0.0, scandal_fired=True, scandal_target=7, shock_crossed=False)
    journal_path = tmp_path / "step0-scandal.jsonl"
    with Journal(journal_path, run_id="step0-scandal") as journal:
        _run_accountability_phase(citizens, config, journal, tick=0, exogenous=exogenous)
    events = _events(journal_path)
    reactions = [e for e in events if e["event_type"] == "reaction_to_event"]
    assert len(reactions) == len(citizens)
    assert {e["citizen_id"] for e in reactions} == {c.citizen_id for c in citizens}
    for e in reactions:
        assert e["payload"]["event_type"] == int(EventType.SCANDAL)
        assert e["payload"]["target"] == 7
        assert e["payload"]["salience_delta"] == pytest.approx(config.events.scandal_magnitude)
        assert e["motif"] == str(ReactionMotif.SCANDAL_TRUST_EROSION)
        assert e["codebook_version"] == config.llm.codebook_version
    for citizen in citizens:
        assert citizen.event_salience == pytest.approx(
            config.events.salience_decay * 0.0 + config.events.scandal_magnitude
        )


def test_step_zero_direct_call_shock_crossed_journals_one_reaction_per_citizen(tmp_path):
    config = _step_zero_direct_call_config()
    citizens = [_shock_test_citizen(i) for i in range(5)]
    exogenous = ExogenousEventsOutcome(economy_x=0.7, scandal_fired=False, scandal_target=None, shock_crossed=True)
    journal_path = tmp_path / "step0-shock.jsonl"
    with Journal(journal_path, run_id="step0-shock") as journal:
        _run_accountability_phase(citizens, config, journal, tick=0, exogenous=exogenous)
    events = _events(journal_path)
    reactions = [e for e in events if e["event_type"] == "reaction_to_event"]
    assert len(reactions) == len(citizens)
    expected_delta = config.events.max_reaction_delta * min(1.0, abs(0.7))
    for e in reactions:
        assert e["payload"]["event_type"] == int(EventType.ECONOMIC_SHOCK)
        assert e["payload"]["target"] is None
        assert e["payload"]["magnitude"] == pytest.approx(0.7)
        assert e["payload"]["salience_delta"] == pytest.approx(expected_delta)
        assert e["motif"] == str(ReactionMotif.ECONOMIC_SHOCK_REACTION)
    for citizen in citizens:
        assert citizen.event_salience == pytest.approx(config.events.salience_decay * 0.0 + expected_delta)


def test_step_zero_direct_call_both_fired_applies_scandal_then_shock_in_order(tmp_path):
    config = _step_zero_direct_call_config()
    citizens = [_shock_test_citizen(0)]
    exogenous = ExogenousEventsOutcome(economy_x=0.7, scandal_fired=True, scandal_target=None, shock_crossed=True)
    journal_path = tmp_path / "step0-both.jsonl"
    with Journal(journal_path, run_id="step0-both") as journal:
        _run_accountability_phase(citizens, config, journal, tick=0, exogenous=exogenous)
    events = _events(journal_path)
    reactions = [e for e in events if e["event_type"] == "reaction_to_event"]
    assert len(reactions) == 2 * len(citizens)
    assert reactions[0]["payload"]["event_type"] == int(EventType.SCANDAL)
    assert reactions[1]["payload"]["event_type"] == int(EventType.ECONOMIC_SHOCK)
    # Two sequential update_event_salience applications, not one.
    scandal_delta = config.events.scandal_magnitude
    shock_delta = config.events.max_reaction_delta * min(1.0, abs(0.7))
    expected = config.events.salience_decay * (config.events.salience_decay * 0.0 + scandal_delta) + shock_delta
    assert citizens[0].event_salience == pytest.approx(expected)


def test_step_zero_exogenous_none_journals_nothing(tmp_path):
    # legitimacy.enabled=True so the phase genuinely runs (not an early
    # return) -- proves step 0's own `exogenous is None` guard, not just
    # that the top-level guard short-circuits.
    config = _step_zero_direct_call_config()
    citizens = [_shock_test_citizen(0)]
    journal_path = tmp_path / "step0-none.jsonl"
    with Journal(journal_path, run_id="step0-none") as journal:
        _run_accountability_phase(citizens, config, journal, tick=0)  # exogenous defaults to None
    assert _events(journal_path) == []
    assert citizens[0].event_salience == 0.0


def test_shock_ticks_measurably_raise_consultation_rate(tmp_path):
    # events.enabled=True, llm.enabled=False, a real elected president --
    # the roadmap's own "consultation rate measurably rises on shock ticks"
    # DoD, computed straight from journal counts via the already-shipped
    # consultation_rate.
    config = _config_with_events_and_awakening_enabled(
        tmp_path, scandal_rate_per_tick=0.3, economic_shock_enabled=False
    )
    journal_path = run_simulation(config, run_id="consultation-rate")
    events = _events(journal_path)
    scandal_ticks = {e["tick"] for e in events if e["event_type"] == "scandal_occurred"}
    pressure_by_tick: dict[int, int] = {}
    for e in events:
        if e["event_type"] == "pressure_action":
            pressure_by_tick[e["tick"]] = pressure_by_tick.get(e["tick"], 0) + 1
    all_ticks = set(range(config.run.total_ticks + 1))
    quiet_ticks = all_ticks - scandal_ticks
    shock_rates = [
        consultation_rate(pressure_by_tick.get(t, 0), config.run.population_size) for t in scandal_ticks
    ]
    quiet_rates = [
        consultation_rate(pressure_by_tick.get(t, 0), config.run.population_size) for t in quiet_ticks
    ]
    assert shock_rates and quiet_rates
    assert sum(shock_rates) / len(shock_rates) > sum(quiet_rates) / len(quiet_rates)


def test_event_salience_never_writes_legitimacy_or_ecart_directly(tmp_path):
    # Non-regression proof: under electoral_only (shipped default -- no
    # petition, no mobilization), deterministic_pressure_action always
    # returns WAIT_FOR_ELECTION regardless of how many more citizens got
    # consulted due to a lowered awakening_threshold -- so street_pressure/
    # petition_pressure never move, proving event_salience's only channel
    # into ecart(t)/L(t) is the pre-existing pressure_action path.
    def _config(output_dir, scandal_enabled):
        config = _config_with_events_and_awakening_enabled(
            output_dir, scandal_enabled=scandal_enabled, scandal_rate_per_tick=1.0, economic_shock_enabled=False
        )
        return dataclasses.replace(config, legitimacy=dataclasses.replace(config.legitimacy, enabled=True))

    path_off = run_simulation(_config(tmp_path / "off", scandal_enabled=False), run_id="control")
    path_on = run_simulation(_config(tmp_path / "on", scandal_enabled=True), run_id="firing")
    events_off = [e for e in _events(path_off) if e["event_type"] == "legitimacy_updated"]
    events_on = [e for e in _events(path_on) if e["event_type"] == "legitimacy_updated"]
    assert events_off
    assert [e["payload"] for e in events_off] == [e["payload"] for e in events_on]


# ── v5 Lot 4: reaction_to_event (dt=8), the LLM decision ──────────────────

def _config_with_events_and_llm_enabled(output_dir, **overrides) -> PolityConfig:
    config = _config_with_events_and_awakening_enabled(output_dir, **overrides)
    return dataclasses.replace(config, llm=dataclasses.replace(config.llm, enabled=True))


def test_default_config_run_emits_no_reaction_to_event_events_from_the_llm_path(tmp_path):
    # llm.enabled=True but events.enabled stays at its shipped default
    # (False) -- exogenous.scandal_fired/shock_crossed are always False
    # regardless of llm.enabled, so _run_reaction_to_event's LLM branch is
    # unreached.
    config = _config_with_llm_enabled(tmp_path)
    journal_path = run_simulation(config, run_id="llm-no-events", llm_client=_FakeLlmClient())
    events = _events(journal_path)
    assert not [e for e in events if e["event_type"] == "reaction_to_event"]


def test_events_enabled_without_the_llm_still_uses_the_deterministic_baseline(tmp_path):
    config = _config_with_events_and_awakening_enabled(  # llm.enabled stays False
        tmp_path, scandal_rate_per_tick=1.0, economic_shock_enabled=False
    )
    journal_path = run_simulation(config, run_id="events-no-llm")
    events = _events(journal_path)
    reactions = [e for e in events if e["event_type"] == "reaction_to_event"]
    assert reactions
    for e in reactions:
        assert set(e["payload"]) == {"event_type", "target", "salience_delta"}  # no "ctx"
        assert e["motif"] == str(ReactionMotif.SCANDAL_TRUST_EROSION)
        assert e["payload"]["salience_delta"] == pytest.approx(config.events.scandal_magnitude)


def test_reaction_to_event_is_journalled_once_per_citizen_per_firing_event_type_with_its_ctx(tmp_path):
    config = _config_with_events_and_llm_enabled(tmp_path, scandal_rate_per_tick=1.0, economic_shock_enabled=False)
    journal_path = run_simulation(config, run_id="reaction-llm", llm_client=_FakeLlmClient())
    events = _events(journal_path)
    scandal_tick = next(e["tick"] for e in events if e["event_type"] == "scandal_occurred")
    reactions = [e for e in events if e["event_type"] == "reaction_to_event" and e["tick"] == scandal_tick]
    assert len(reactions) == config.run.population_size
    assert [e["citizen_id"] for e in reactions] == sorted(e["citizen_id"] for e in reactions)
    for e in reactions:
        assert set(e["payload"]) == {"event_type", "target", "salience_delta", "ctx"}
        assert e["payload"]["event_type"] == int(EventType.SCANDAL)
        assert set(e["payload"]["ctx"]) == {"event_salience"}
        assert e["motif"] == str(ReactionMotif.SCANDAL_TRUST_EROSION)
        assert e["codebook_version"] == config.llm.codebook_version


def test_both_events_firing_same_tick_stays_deterministic_byte_for_byte_under_the_llm_path(tmp_path):
    # >= MIN_SAFE_BATCH_SIZE citizens: dt=8 does not override chunk_voters's
    # default floor (unlike decide_pressure_actions's min_batch_size=1).
    config = _config_with_events_and_llm_enabled(tmp_path)
    citizens = [_shock_test_citizen(i) for i in range(20)]
    exogenous = ExogenousEventsOutcome(economy_x=0.7, scandal_fired=True, scandal_target=None, shock_crossed=True)
    journal_path = tmp_path / "both-llm.jsonl"
    with Journal(journal_path, run_id="both-llm") as journal:
        _run_accountability_phase(citizens, config, journal, tick=0, llm_client=_FakeLlmClient(), exogenous=exogenous)
    events = _events(journal_path)
    reactions = [e for e in events if e["event_type"] == "reaction_to_event"]
    assert len(reactions) == 2 * len(citizens)
    assert [e["payload"]["event_type"] for e in reactions[:20]] == [int(EventType.SCANDAL)] * 20
    assert [e["payload"]["event_type"] for e in reactions[20:]] == [int(EventType.ECONOMIC_SHOCK)] * 20
    # The ECONOMIC_SHOCK call's ctx.event_salience must equal the value the
    # SCANDAL call's own update_event_salience application just wrote --
    # never the citizen's pre-tick starting value.
    scandal_delta = 0.1  # _FakeLlmClient's fixed salience_delta
    expected_after_scandal = config.events.salience_decay * 0.0 + scandal_delta
    for e in reactions[20:]:
        assert e["payload"]["ctx"]["event_salience"] == pytest.approx(expected_after_scandal)


def test_no_reaction_to_event_llm_call_on_a_vacancy_tick(tmp_path):
    config = _config_with_events_and_llm_enabled(tmp_path)
    citizens = [_shock_test_citizen(i) for i in range(20)]  # nobody holds Office.PRESIDENT
    exogenous = ExogenousEventsOutcome(economy_x=0.0, scandal_fired=True, scandal_target=None, shock_crossed=False)
    journal_path = tmp_path / "vacancy-llm.jsonl"
    with Journal(journal_path, run_id="vacancy-llm") as journal:
        _run_accountability_phase(citizens, config, journal, tick=0, llm_client=_FakeLlmClient(), exogenous=exogenous)
    events = _events(journal_path)
    reactions = [e for e in events if e["event_type"] == "reaction_to_event"]
    assert len(reactions) == len(citizens)
    assert all(e["payload"]["target"] is None for e in reactions)


def test_an_out_of_bound_salience_delta_aborts_the_run_with_no_partial_journal(tmp_path):
    config = _config_with_events_and_llm_enabled(tmp_path, scandal_rate_per_tick=1.0, economic_shock_enabled=False)

    class OverCapClient(_FakeLlmClient):
        """Behaves exactly like _FakeLlmClient for every other decision
        type (so candidacy/nomination/etc. still succeed), but returns an
        out-of-bound salience_delta for reaction_to_event specifically --
        isolates the abort to this lot's own validator."""

        def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
            payload = json.loads(user_prompt)
            if "reactors" in payload:
                decisions = [{"cid": r["cid"], "salience_delta": 1.0, "motif": 401} for r in payload["reactors"]]
                return json.dumps({"decisions": decisions})
            return super().complete_json(
                system_prompt=system_prompt, user_prompt=user_prompt, json_schema=json_schema,
                max_tokens=max_tokens, think=think,
            )

    with pytest.raises(LlmResponseError, match="max_reaction_delta"):
        run_simulation(config, run_id="over-cap", llm_client=OverCapClient())


def test_two_events_llm_runs_produce_byte_identical_journals(tmp_path):
    config_kwargs = dict(scandal_rate_per_tick=1.0, economic_shock_enabled=False)
    path_a = run_simulation(
        _config_with_events_and_llm_enabled(tmp_path / "a", **config_kwargs), run_id="same-run-id",
        llm_client=_FakeLlmClient(),
    )
    path_b = run_simulation(
        _config_with_events_and_llm_enabled(tmp_path / "b", **config_kwargs), run_id="same-run-id",
        llm_client=_FakeLlmClient(),
    )
    assert path_a.read_bytes() == path_b.read_bytes()


def test_reaction_to_event_llm_never_reads_self_gap_or_mandate_dev(tmp_path):
    config = _config_with_events_and_llm_enabled(tmp_path, scandal_rate_per_tick=1.0, economic_shock_enabled=False)
    journal_path = run_simulation(config, run_id="no-self-gap", llm_client=_FakeLlmClient())
    events = _events(journal_path)
    reactions = [e for e in events if e["event_type"] == "reaction_to_event"]
    assert reactions
    for e in reactions:
        assert "self_gap" not in e["payload"]["ctx"]
        assert "mandate_dev" not in e["payload"]["ctx"]


# ── ADR-002: the shipped candidacy config cannot elect, and said so silently ──


def _population_at_shipped_defaults() -> list[Citizen]:
    config = load_config()
    return generate_population(config.citizens, config.run.population_size, config.run.seed)


def test_a_config_whose_pool_is_empty_warns_that_no_candidacy_is_ever_possible(tmp_path, caplog):
    # ADR-002's guard. It used to be exercised by the SHIPPED config, because
    # the shipped config was the defect; since the calibration landed
    # (ambition_threshold 0.7 -> 0.30) an empty pool has to be asked for
    # explicitly. ambition_dist beta(2,8) is bounded above by 1.0 and draws are
    # continuous, so a threshold of 1.0 empties the pool for every seed.
    config = _config_with_output_dir(tmp_path)
    config = dataclasses.replace(config, candidacy=dataclasses.replace(config.candidacy, ambition_threshold=1.0))
    with caplog.at_level("WARNING", logger=run_polity_simulation_module.__name__):
        run_simulation(config, run_id="silent")
    assert "no citizen can ever declare a candidacy" in caplog.text
    assert "ADR-002" in caplog.text


def test_the_shipped_config_no_longer_warns(tmp_path, caplog):
    # The regression guard for the ADR-002 calibration itself: if the shipped
    # (ambition_dist, ambition_threshold) pair ever drifts back to a state where
    # no citizen can run, this fails rather than quietly returning to 39-seeds-
    # in-40 holding no election.
    with caplog.at_level("WARNING", logger=run_polity_simulation_module.__name__):
        journal_path = run_simulation(_config_with_output_dir(tmp_path), run_id="calibrated")
    assert "no citizen can ever declare a candidacy" not in caplog.text
    events = _events(journal_path)
    assert [e for e in events if e["event_type"] == "elected"]
    assert not [e for e in events if e["event_type"] == "election_no_winner"]


def test_no_candidacy_warning_when_at_least_one_citizen_clears_the_threshold(tmp_path, caplog):
    config = _config_with_output_dir(tmp_path)
    config = dataclasses.replace(config, candidacy=dataclasses.replace(config.candidacy, ambition_threshold=0.0))
    with caplog.at_level("WARNING", logger=run_polity_simulation_module.__name__):
        run_simulation(config, run_id="has-candidates")
    assert "no citizen can ever declare a candidacy" not in caplog.text


def test_no_candidacy_warning_on_the_llm_path(caplog):
    # _declare_nominees_llm never consults ambition_threshold at all (the model
    # arbitrates from ambition_score and perceived support), so an empty
    # deterministic pool is a non-event there -- warning here would cry wolf.
    config = load_config()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, enabled=True))
    with caplog.at_level("WARNING", logger=run_polity_simulation_module.__name__):
        _warn_if_no_candidate_is_possible(_population_at_shipped_defaults(), config)
    assert caplog.text == ""


def test_no_candidacy_warning_when_the_rupture_path_is_open(caplog):
    # §2.4's rupture path is threshold-independent: a candidacy can appear
    # without anyone clearing ambition_threshold, so the pool being empty no
    # longer implies no candidate.
    config = load_config()
    config = dataclasses.replace(config, candidacy=dataclasses.replace(config.candidacy, rupture_path_enabled=True))
    with caplog.at_level("WARNING", logger=run_polity_simulation_module.__name__):
        _warn_if_no_candidate_is_possible(_population_at_shipped_defaults(), config)
    assert caplog.text == ""


def test_election_no_winner_names_an_absent_candidate_field(tmp_path):
    # ADR-002: election_no_winner used to cover two structurally different
    # failures with the same payload. This is the "no candidate existed" one --
    # now produced deliberately (president_term_limit=0) rather than inherited
    # from the mis-calibrated shipped threshold.
    journal_path = run_simulation(
        _config_with_a_structurally_empty_candidate_field(tmp_path), run_id="no-field"
    )
    no_winner = [e for e in _events(journal_path) if e["event_type"] == "election_no_winner"]
    assert no_winner
    for event in no_winner:
        assert event["payload"]["reason"] == "no_candidates"


def test_election_no_winner_omits_reason_when_candidates_actually_ran(tmp_path):
    # The other failure: five nominees stood and Blank won the runoff outright
    # (uniform/seed=1 -- the §10.10 distribution failure mode). `reason` must
    # stay absent, since its whole job is to mark the empty-field case.
    config = _config_with_output_dir(tmp_path)
    config = dataclasses.replace(
        config,
        run=dataclasses.replace(config.run, seed=1),
        citizens=dataclasses.replace(config.citizens, position_dist="uniform"),
        candidacy=dataclasses.replace(config.candidacy, ambition_threshold=0.0),
    )
    journal_path = run_simulation(config, run_id="blank-won")
    events = _events(journal_path)
    no_winner = [e for e in events if e["event_type"] == "election_no_winner"]
    assert no_winner
    assert [e for e in events if e["event_type"] == "candidacy_declared"]
    for event in no_winner:
        assert "reason" not in event["payload"]


def test_elected_never_carries_a_reason(tmp_path):
    config = _config_with_output_dir(tmp_path)
    config = dataclasses.replace(config, candidacy=dataclasses.replace(config.candidacy, ambition_threshold=0.0))
    journal_path = run_simulation(config, run_id="elected-clean")
    elected = [e for e in _events(journal_path) if e["event_type"] == "elected"]
    assert elected
    for event in elected:
        assert "reason" not in event["payload"]
