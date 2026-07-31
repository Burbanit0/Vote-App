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
