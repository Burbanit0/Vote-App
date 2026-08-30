"""api.domain.polity.cli — argument handling and run-status bookkeeping.

The module holds no simulation logic, so neither does this file: what is
under test is that a mistyped override fails loudly at startup instead of
silently defaulting, and that every way a run can end leaves a
`run_status.json` saying so. Both matter because the caller this exists for
is a supervisor that will never see the process's stderr.

Runs are kept to one simulated year with compaction off -- this suite is
about the wrapper, and DuckDB work here would buy nothing.
"""
import json
import signal
import subprocess
import sys
from pathlib import Path

import pytest

from api.domain.polity import cli
from api.domain.polity.cli import (
    COMPLETED,
    FAILED,
    INTERRUPTED,
    RUNNING,
    STATUS_FILENAME,
    CliError,
    _Terminated,
    apply_overrides,
    main,
    parse_overrides,
    write_status,
)
from api.domain.polity.config import load_config


def _fast_run_args(output_dir: Path, run_id: str) -> list[str]:
    return [
        "--run-id", run_id,
        "--output-dir", str(output_dir),
        "--set", "run.duration_years=1",
        "--set", "journal.index_after_run=false",
    ]


def _status(output_dir: Path, run_id: str) -> dict:
    return json.loads((output_dir / run_id / STATUS_FILENAME).read_text(encoding="utf-8"))


# ── parse_overrides ───────────────────────────────────────────────────────

def test_parse_overrides_groups_assignments_by_section():
    parsed = parse_overrides(["run.seed=7", "run.duration_years=2", "llm.enabled=true"])
    assert set(parsed) == {"run", "llm"}
    assert set(parsed["run"]) == {"seed", "duration_years"}


def test_parse_overrides_rejects_a_pair_without_an_equals_sign():
    with pytest.raises(CliError, match="section.field=value"):
        parse_overrides(["run.seed"])


@pytest.mark.parametrize("key", ["seed", "run.llm.seed"])
def test_parse_overrides_rejects_a_key_that_is_not_exactly_section_dot_field(key):
    with pytest.raises(CliError, match="exactly one dot"):
        parse_overrides([f"{key}=7"])


def test_parse_overrides_keeps_a_value_containing_an_equals_sign():
    # partition, not split: a base_url with a query string must survive.
    parsed = parse_overrides(["llm.base_url=http://h/v1?a=b"])
    assert parsed["llm"]["base_url"][0] == "http://h/v1?a=b"


# ── apply_overrides: coercion ─────────────────────────────────────────────

def test_apply_overrides_coerces_int_float_str_and_bool():
    config = apply_overrides(
        load_config(),
        [
            "run.seed=7",
            "institutions.electoral_threshold=0.1",
            "run.run_label=demo",
            "llm.enabled=true",
        ],
    )
    assert config.run.seed == 7
    assert config.institutions.electoral_threshold == pytest.approx(0.1)
    assert config.run.run_label == "demo"
    assert config.llm.enabled is True


@pytest.mark.parametrize("raw,expected", [("true", True), ("1", True), ("yes", True),
                                          ("false", False), ("0", False), ("no", False),
                                          ("TRUE", True), ("False", False)])
def test_apply_overrides_accepts_both_spellings_and_cases_of_a_boolean(raw, expected):
    assert apply_overrides(load_config(), [f"llm.enabled={raw}"]).llm.enabled is expected


def test_apply_overrides_rejects_a_non_boolean_for_a_boolean_field():
    # The expensive failure this guards: bool("false") is True, so a
    # permissive cast would turn `llm.enabled=false` into a GPU run.
    with pytest.raises(CliError, match="expected a boolean"):
        apply_overrides(load_config(), ["llm.enabled=maybe"])


def test_apply_overrides_rejects_a_non_integer_for_an_integer_field():
    with pytest.raises(CliError, match="expected an integer"):
        apply_overrides(load_config(), ["run.seed=abc"])


def test_apply_overrides_rejects_a_non_number_for_a_float_field():
    with pytest.raises(CliError, match="expected a number"):
        apply_overrides(load_config(), ["institutions.electoral_threshold=high"])


@pytest.mark.parametrize("spelling", ["null", "none", "NULL", "None"])
def test_apply_overrides_sets_an_optional_field_to_none(spelling):
    config = apply_overrides(load_config(), [f"institutions.president_term_limit={spelling}"])
    assert config.institutions.president_term_limit is None


def test_apply_overrides_still_sets_a_value_on_an_optional_field():
    config = apply_overrides(load_config(), ["institutions.president_term_limit=2"])
    assert config.institutions.president_term_limit == 2


# ── apply_overrides: rejection ────────────────────────────────────────────

def test_apply_overrides_rejects_an_unknown_section_and_lists_the_known_ones():
    with pytest.raises(CliError, match="unknown config section"):
        apply_overrides(load_config(), ["nosuch.field=1"])


def test_apply_overrides_rejects_an_unknown_field_and_names_the_key():
    with pytest.raises(CliError, match=r"run\.duraton_years"):
        apply_overrides(load_config(), ["run.duraton_years=8"])


def test_apply_overrides_rejects_the_raw_section():
    # `raw` is a dict, not a config section -- settable only by accident.
    with pytest.raises(CliError, match="unknown config section"):
        apply_overrides(load_config(), ["raw.anything=1"])


def test_apply_overrides_rejects_a_derived_property():
    # run.total_ticks is ticks_per_year * duration_years. Setting it would
    # produce a config that disagrees with itself.
    with pytest.raises(CliError, match="unknown field"):
        apply_overrides(load_config(), ["run.total_ticks=40"])


def test_apply_overrides_leaves_the_config_untouched_when_no_overrides_are_given():
    config = load_config()
    assert apply_overrides(config, []) == config


@pytest.mark.parametrize("key,value", [
    ("awakening.context_modulation", "{}"),   # nested dataclass
    ("parties.coalition_tiebreak", "a,b"),    # tuple[str, ...]
    ("parties.manual_platforms", "[]"),       # list[Any]
])
def test_apply_overrides_refuses_a_non_scalar_field_and_points_at_the_config_file(key, value):
    # The ceiling is deliberate: a config whose structure changes wants a
    # YAML file that can be diffed and committed, not a shell string.
    with pytest.raises(CliError, match="unsupported field type"):
        apply_overrides(load_config(), [f"{key}={value}"])


# ── write_status ──────────────────────────────────────────────────────────

def test_write_status_creates_the_directory_and_records_the_pid(tmp_path):
    write_status(tmp_path / "nested" / "run", "r", RUNNING, error=None)
    payload = json.loads((tmp_path / "nested" / "run" / STATUS_FILENAME).read_text(encoding="utf-8"))
    assert payload["status"] == RUNNING
    assert payload["run_id"] == "r"
    assert isinstance(payload["pid"], int)
    assert payload["error"] is None


def test_write_status_swallows_an_unwritable_directory(tmp_path, monkeypatch):
    # Describing a run must never be the reason the run is reported failed.
    monkeypatch.setattr(Path, "mkdir", lambda *a, **kw: (_ for _ in ()).throw(OSError("nope")))
    write_status(tmp_path / "x", "r", RUNNING)  # must not raise


# ── main: the four terminal states ────────────────────────────────────────

def test_main_runs_a_simulation_and_reports_completed(tmp_path, capsys):
    assert main(_fast_run_args(tmp_path, "ok")) == 0
    status = _status(tmp_path, "ok")
    assert status["status"] == COMPLETED
    assert status["exit_code"] == 0
    assert status["error"] is None
    assert Path(status["journal_path"]).is_file()
    # stdout is the journal path, so a caller can pipe it.
    assert capsys.readouterr().out.strip() == status["journal_path"]


def test_main_applies_the_output_dir_override(tmp_path):
    main(_fast_run_args(tmp_path, "here"))
    assert (tmp_path / "here" / "events.jsonl").is_file()


def test_main_falls_back_to_the_config_run_label_when_no_run_id_is_given(tmp_path):
    label = load_config().run.run_label
    assert main(["--output-dir", str(tmp_path), "--set", "run.duration_years=1",
                 "--set", "journal.index_after_run=false"]) == 0
    assert (tmp_path / label / "events.jsonl").is_file()


def test_main_reports_failed_with_the_exception_in_the_status_file(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "run_simulation", lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("boom")))
    assert main(_fast_run_args(tmp_path, "bad")) == 1
    status = _status(tmp_path, "bad")
    assert status["status"] == FAILED
    assert status["exit_code"] == 1
    assert "RuntimeError: boom" in status["error"]


@pytest.mark.parametrize("raised", [_Terminated, KeyboardInterrupt])
def test_main_reports_interrupted_rather_than_failed_when_stopped(tmp_path, monkeypatch, raised):
    # An operator pressing stop is not a failed run. If this ever regresses,
    # every use of the UI's stop button reads as if it broke the simulation.
    def _stop(*_args, **_kwargs):
        raise raised()

    monkeypatch.setattr(cli, "run_simulation", _stop)
    assert main(_fast_run_args(tmp_path, "stopped")) == 130
    status = _status(tmp_path, "stopped")
    assert status["status"] == INTERRUPTED
    assert status["error"] is None


def test_main_writes_running_before_the_simulation_starts(tmp_path, monkeypatch):
    seen = {}

    def _capture(config, run_id=None, llm_client=None):
        seen["status"] = _status(tmp_path, run_id)["status"]
        return tmp_path / run_id / "events.jsonl"

    monkeypatch.setattr(cli, "run_simulation", _capture)
    main(_fast_run_args(tmp_path, "phase"))
    assert seen["status"] == RUNNING


# ── main: usage errors ────────────────────────────────────────────────────

def test_main_exits_two_on_a_bad_override_without_creating_a_run_dir(tmp_path, capsys):
    assert main(_fast_run_args(tmp_path, "never") + ["--set", "run.nope=1"]) == 2
    assert "unknown field" in capsys.readouterr().err
    assert not (tmp_path / "never").exists()


def test_main_exits_two_on_a_missing_config_file(tmp_path, capsys):
    assert main(["--config", str(tmp_path / "absent.yaml"), "--output-dir", str(tmp_path)]) == 2
    assert "config file not found" in capsys.readouterr().err


# ── SIGTERM handling ──────────────────────────────────────────────────────

def test_terminated_is_a_base_exception_so_it_bypasses_the_failure_handler():
    # If it were an Exception, main's `except Exception` would classify a
    # requested stop as a failure -- the bug this inheritance prevents.
    assert issubclass(_Terminated, BaseException)
    assert not issubclass(_Terminated, Exception)


def test_install_sigterm_handler_raises_terminated_on_delivery():
    previous = signal.getsignal(signal.SIGTERM)
    try:
        cli._install_sigterm_handler()
        handler = signal.getsignal(signal.SIGTERM)
        assert callable(handler)
        with pytest.raises(_Terminated):
            handler(signal.SIGTERM, None)
    finally:
        signal.signal(signal.SIGTERM, previous)


# ── the module really is runnable as `python -m` ──────────────────────────

def test_module_is_executable_with_dash_m(tmp_path):
    # The supervisor spawns exactly this argv; a missing __main__ guard or a
    # bad package path would only ever show up here.
    result = subprocess.run(
        [sys.executable, "-m", "api.domain.polity.cli", *_fast_run_args(tmp_path, "spawned")],
        capture_output=True, text=True, timeout=180,
        cwd=str(Path(__file__).resolve().parents[2]),
    )
    assert result.returncode == 0, result.stderr
    assert _status(tmp_path, "spawned")["status"] == COMPLETED
