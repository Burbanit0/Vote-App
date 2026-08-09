"""Lot 1 — config.py: typed loading + validation of polity_config.yaml.

Contract (dev-plan-v0-worktree.md §3, Lot 1): an invalid config file fails
explicitly, never silently.
"""
import copy

import pytest
import yaml

from api.domain.polity.config import PolityConfigError, load_config


def test_loads_the_real_polity_config_with_expected_v0_values():
    config = load_config()
    assert config.run.seed == 42
    assert config.run.ticks_per_year == 4
    assert config.run.duration_years == 30
    assert config.run.total_ticks == 120
    assert config.run.population_size == 100
    assert config.institutions.presidential_method == "two_round"
    assert config.institutions.assembly_seats == 100
    assert config.institutions.seat_allocation == "dhondt"
    assert config.institutions.president_term_limit is None
    assert config.parties.initial_count == 5
    assert config.parties.coalition_tiebreak == ("seats", "votes", "party_id")
    assert config.citizens.issue_count == 20
    assert config.legitimacy.enabled is False
    assert config.journal.enabled is True
    assert config.metrics.effective_parties is True
    assert config.llm.enabled is False
    assert config.llm.provider == "ollama"
    assert config.llm.base_url == "http://localhost:11434/v1"
    assert config.llm.model == "qwen3:8b"
    assert config.llm.temperature == 0.0
    assert config.llm.max_batch_size == 25
    assert config.llm.batch_sharding == "static"
    assert config.llm.codebook_version == "1.0"
    assert config.llm.personas_count == 30
    assert config.campaign.max_positioning_delta == 0.3
    assert config.campaign.max_positioning_shifts == 3
    assert config.parallel.runs_in_parallel == 1
    assert config.parallel.intra_run_workers == 1


def test_missing_file_raises_explicitly(tmp_path):
    with pytest.raises(PolityConfigError, match="not found"):
        load_config(tmp_path / "does_not_exist.yaml")


def test_malformed_yaml_raises_explicitly(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("run: [unclosed", encoding="utf-8")
    with pytest.raises(PolityConfigError, match="invalid YAML"):
        load_config(bad)


def test_top_level_must_be_a_mapping(tmp_path):
    bad = tmp_path / "list.yaml"
    bad.write_text("- 1\n- 2\n", encoding="utf-8")
    with pytest.raises(PolityConfigError, match="mapping"):
        load_config(bad)


def _valid_dict() -> dict:
    return copy.deepcopy(load_config().raw)


def _write(tmp_path, mutate):
    data = _valid_dict()
    mutate(data)
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def test_missing_required_key_raises_and_names_it(tmp_path):
    path = _write(tmp_path, lambda d: d["run"].pop("seed"))
    with pytest.raises(PolityConfigError, match="run.seed"):
        load_config(path)


def test_wrong_type_raises_and_names_it(tmp_path):
    path = _write(tmp_path, lambda d: d["run"].__setitem__("seed", "not-an-int"))
    with pytest.raises(PolityConfigError, match="run.seed"):
        load_config(path)


def test_bool_is_rejected_where_int_is_expected(tmp_path):
    """bool is a subclass of int in Python — a plain isinstance(x, int) check
    would silently accept `seed: true`. Must be rejected explicitly."""
    path = _write(tmp_path, lambda d: d["run"].__setitem__("seed", True))
    with pytest.raises(PolityConfigError, match="run.seed"):
        load_config(path)


def test_unknown_enum_value_raises(tmp_path):
    path = _write(
        tmp_path, lambda d: d["institutions"].__setitem__("presidential_method", "coin_flip")
    )
    with pytest.raises(PolityConfigError, match="presidential_method"):
        load_config(path)


def test_ratio_out_of_range_raises(tmp_path):
    path = _write(
        tmp_path, lambda d: d["institutions"].__setitem__("electoral_threshold", 1.5)
    )
    with pytest.raises(PolityConfigError, match="electoral_threshold"):
        load_config(path)


def test_coalition_tiebreak_rejects_unknown_key(tmp_path):
    path = _write(
        tmp_path,
        lambda d: d["parties"].__setitem__("coalition_tiebreak", ["seats", "coin_flip"]),
    )
    with pytest.raises(PolityConfigError, match="coalition_tiebreak"):
        load_config(path)


def test_coalition_tiebreak_rejects_duplicates(tmp_path):
    path = _write(
        tmp_path,
        lambda d: d["parties"].__setitem__("coalition_tiebreak", ["seats", "seats"]),
    )
    with pytest.raises(PolityConfigError, match="coalition_tiebreak"):
        load_config(path)


def test_coalition_tiebreak_rejects_empty(tmp_path):
    path = _write(tmp_path, lambda d: d["parties"].__setitem__("coalition_tiebreak", []))
    with pytest.raises(PolityConfigError, match="coalition_tiebreak"):
        load_config(path)


# ── llm / parallel (v2 increment 1) ──────────────────────────────────────

def test_llm_model_without_a_tag_raises(tmp_path):
    path = _write(tmp_path, lambda d: d["llm"].__setitem__("model", "qwen3"))
    with pytest.raises(PolityConfigError, match="llm.model"):
        load_config(path)


def test_llm_model_pinned_to_latest_raises(tmp_path):
    path = _write(tmp_path, lambda d: d["llm"].__setitem__("model", "qwen3:latest"))
    with pytest.raises(PolityConfigError, match="llm.model"):
        load_config(path)


def test_llm_provider_unknown_raises(tmp_path):
    path = _write(tmp_path, lambda d: d["llm"].__setitem__("provider", "openai"))
    with pytest.raises(PolityConfigError, match="provider"):
        load_config(path)


def test_llm_batch_sharding_unknown_raises(tmp_path):
    path = _write(tmp_path, lambda d: d["llm"].__setitem__("batch_sharding", "round_robin"))
    with pytest.raises(PolityConfigError, match="batch_sharding"):
        load_config(path)


def test_llm_max_batch_size_must_be_positive(tmp_path):
    path = _write(tmp_path, lambda d: d["llm"].__setitem__("max_batch_size", 0))
    with pytest.raises(PolityConfigError, match="max_batch_size"):
        load_config(path)


def test_llm_enabled_with_nonzero_temperature_raises(tmp_path):
    def mutate(d):
        d["llm"]["enabled"] = True
        d["llm"]["temperature"] = 0.7

    path = _write(tmp_path, mutate)
    with pytest.raises(PolityConfigError, match="temperature"):
        load_config(path)


def test_llm_disabled_with_nonzero_temperature_is_allowed(tmp_path):
    path = _write(tmp_path, lambda d: d["llm"].__setitem__("temperature", 0.7))
    config = load_config(path)
    assert config.llm.temperature == 0.7
    assert config.llm.enabled is False


def test_llm_base_url_without_scheme_raises(tmp_path):
    path = _write(tmp_path, lambda d: d["llm"].__setitem__("base_url", "localhost:11434/v1"))
    with pytest.raises(PolityConfigError, match="base_url"):
        load_config(path)


def test_llm_base_url_trailing_slash_is_stripped(tmp_path):
    path = _write(tmp_path, lambda d: d["llm"].__setitem__("base_url", "http://localhost:11434/v1/"))
    config = load_config(path)
    assert config.llm.base_url == "http://localhost:11434/v1"


def test_parallel_intra_run_workers_must_be_positive(tmp_path):
    path = _write(tmp_path, lambda d: d["parallel"].__setitem__("intra_run_workers", 0))
    with pytest.raises(PolityConfigError, match="intra_run_workers"):
        load_config(path)


# ── campaign (v2 increment 4) ─────────────────────────────────────────────

def test_campaign_max_positioning_delta_out_of_range_raises(tmp_path):
    path = _write(tmp_path, lambda d: d["campaign"].__setitem__("max_positioning_delta", 1.5))
    with pytest.raises(PolityConfigError, match="max_positioning_delta"):
        load_config(path)


def test_campaign_max_positioning_shifts_must_be_positive(tmp_path):
    path = _write(tmp_path, lambda d: d["campaign"].__setitem__("max_positioning_shifts", 0))
    with pytest.raises(PolityConfigError, match="max_positioning_shifts"):
        load_config(path)
