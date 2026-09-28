"""The constitution (ADR-015): amendable articles, scripted amendments, the rules in force."""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import yaml
from hypothesis import given, settings
from hypothesis import strategies as st

from api.domain.polity import run_polity_simulation as engine
from api.domain.polity.config import (
    _DEFAULT_CONFIG_PATH,
    ARTICLES,
    Article,
    PolityConfigError,
    ScriptedAmendment,
    load_config,
    validate_config,
)
from api.domain.polity.constitution import Constitution, amend, article_value, in_force
from api.domain.polity.journal import Journal
from api.domain.polity.run_polity_simulation import _phase_constitution, run_simulation
from api.tests.polity_golden import golden_config

_CONFIG = load_config()


def test_an_article_allows_only_its_values() -> None:
    method = ARTICLES["institutions.presidential_method"]
    assert method.allows("borda") and not method.allows("star") and not method.allows(True)
    limit = ARTICLES["institutions.president_term_limit"]
    assert limit.allows(None) and limit.allows(2) and not limit.allows(True) and not limit.allows(4)
    seats = ARTICLES["institutions.assembly_seats"]
    assert seats.allows(150) and not seats.allows(150.0) and not seats.allows(10) and not seats.allows("150")
    floor = Article("legitimacy.recall_floor", low=0.0, high=0.5)
    assert floor.allows(0.2) and floor.allows(0) and not floor.allows(0.6)


def test_the_rules_in_force_lay_each_amendment_over_the_founding_config() -> None:
    constitution = amend(amend(None, "institutions.presidential_method", "borda"), "legitimacy.recall_floor", 0.1)
    assert constitution == Constitution(version=2, values={"institutions.presidential_method": "borda", "legitimacy.recall_floor": 0.1})
    rules = in_force(_CONFIG, constitution)
    assert (rules.institutions.presidential_method, rules.legitimacy.recall_floor) == ("borda", 0.1)
    assert article_value(_CONFIG, "institutions.presidential_method") == "two_round"
    assert in_force(_CONFIG, None) is _CONFIG


# ── scripted amendments in the config ─────────────────────────────────────

def _load(tmp_path: Path, scripted: Any) -> Any:
    data = yaml.safe_load(_DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
    data["constitution"]["scripted"] = scripted
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return load_config(path)


def test_a_scripted_amendment_is_read_from_the_config(tmp_path: Path) -> None:
    config = _load(tmp_path, [{"tick": 40, "article": "institutions.presidential_method", "value": "borda"}])
    assert config.constitution.scripted == (ScriptedAmendment(tick=40, article="institutions.presidential_method", value="borda"),)


@pytest.mark.parametrize("scripted,message", [
    ([{"tick": 4, "article": "run.seed", "value": 1}], "not an amendable article"),
    ([{"tick": 4, "article": "institutions.presidential_method", "value": "star"}], "not a value"),
    ([{"tick": -1, "article": "legitimacy.recall_floor", "value": 0.1}], "expected a tick"),
    ([{"tick": 4, "article": "legitimacy.recall_floor"}], "exactly tick, article and value"),
    (["borda"], "exactly tick, article and value"),
])
def test_a_scripted_amendment_the_constitution_cannot_make_is_refused(tmp_path: Path, scripted: Any, message: str) -> None:
    with pytest.raises(PolityConfigError, match=message):
        _load(tmp_path, scripted)


def test_the_rules_are_checked_after_each_amendment(monkeypatch: pytest.MonkeyPatch) -> None:
    config = dataclasses.replace(_CONFIG, constitution=dataclasses.replace(
        _CONFIG.constitution, scripted=(ScriptedAmendment(tick=8, article="legitimacy.recall_floor", value=0.4),),
    ))
    validate_config(config)
    monkeypatch.setattr("api.domain.polity.config._CONFIG_RULES", (
        lambda c: "the floor is too high" if c.legitimacy.recall_floor > 0.3 else None,
    ))
    with pytest.raises(PolityConfigError, match=r"the floor is too high \(after the amendment at tick 8\)"):
        validate_config(config)


# ── the tick ──────────────────────────────────────────────────────────────

def test_a_tick_s_amendments_come_first_and_are_journaled(tmp_path: Path) -> None:
    config = dataclasses.replace(_CONFIG, constitution=dataclasses.replace(_CONFIG.constitution, scripted=(
        ScriptedAmendment(tick=5, article="legitimacy.recall_floor", value=0.3),
        ScriptedAmendment(tick=4, article="institutions.presidential_method", value="borda"),
        ScriptedAmendment(tick=4, article="institutions.president_term_limit", value=None),
    )))
    state = SimpleNamespace(constitution=None)
    with Journal(tmp_path / "events.jsonl", "r") as journal:
        context = SimpleNamespace(tick=4, config=config, journal=journal)
        _phase_constitution(context, state)  # type: ignore[arg-type]
    rules = context.config.institutions
    assert (rules.presidential_method, rules.president_term_limit, context.config.legitimacy.recall_floor) == ("borda", None, 0.2)
    events = [json.loads(line) for line in (tmp_path / "events.jsonl").read_text().splitlines()]
    assert [(e["event_type"], e["payload"]["article"], e["payload"]["old"], e["payload"]["new"], e["payload"]["version"]) for e in events] == [
        ("constitution_amended", "institutions.presidential_method", "two_round", "borda", 1),
        ("constitution_amended", "institutions.president_term_limit", 2, None, 2),
    ]


def _amending_config(output_dir: Path) -> Any:
    config = golden_config(output_dir, llm=False)
    return dataclasses.replace(config, constitution=dataclasses.replace(config.constitution, scripted=(
        ScriptedAmendment(tick=3, article="institutions.presidential_method", value="borda"),
        ScriptedAmendment(tick=5, article="institutions.president_term_limit", value=1),
    )))


class _Crash(Exception):
    pass


def test_a_run_amends_itself_and_resumes_under_the_amended_rules(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    uninterrupted = run_simulation(_amending_config(tmp_path / "a"), run_id="run")
    amendments = [json.loads(line) for line in uninterrupted.read_text().splitlines() if '"constitution_amended"' in line]
    assert [(e["tick"], e["payload"]["new"], e["payload"]["version"]) for e in amendments] == [(3, "borda", 1), (5, 1, 2)]
    checkpoint = json.loads((uninterrupted.parent / "checkpoint.json").read_text())
    assert checkpoint["constitution"] == {
        "version": 2, "values": {"institutions.presidential_method": "borda", "institutions.president_term_limit": 1},
    }
    real_phase = engine._run_accountability_phase

    def crash_at_tick_6(citizens: Any, config: Any, journal: Any, tick: int, llm_client: Any = None, **kwargs: Any) -> Any:
        if tick == 6:
            raise _Crash("killed mid-tick")
        return real_phase(citizens, config, journal, tick, llm_client, **kwargs)

    monkeypatch.setattr(engine, "_run_accountability_phase", crash_at_tick_6)
    with pytest.raises(_Crash):
        run_simulation(_amending_config(tmp_path / "b"), run_id="run")
    monkeypatch.undo()
    resumed = run_simulation(_amending_config(tmp_path / "b"), run_id="run", resume=True)
    assert resumed.read_bytes() == uninterrupted.read_bytes()


def _legal_value(article: Article) -> st.SearchStrategy[Any]:
    if article.choices:
        return st.sampled_from(article.choices)
    if article.integer:
        return st.integers(int(article.low), int(article.high))
    return st.floats(article.low, article.high, allow_nan=False)


@settings(max_examples=12, deadline=None)
@given(constitution=st.fixed_dictionaries({path: _legal_value(article) for path, article in ARTICLES.items()}))
def test_any_legal_constitution_keeps_the_rules_and_runs(tmp_path_factory: pytest.TempPathFactory, constitution: dict[str, Any]) -> None:
    config = golden_config(tmp_path_factory.mktemp("constitution"), llm=False)
    config = dataclasses.replace(
        config,
        run=dataclasses.replace(config.run, duration_years=1),
        constitution=dataclasses.replace(config.constitution, scripted=tuple(
            ScriptedAmendment(tick=0, article=path, value=value) for path, value in constitution.items()
        )),
    )
    validate_config(config)
    events = run_simulation(config, run_id="any").read_text().splitlines()
    assert sum('"constitution_amended"' in line for line in events) == len(ARTICLES)
