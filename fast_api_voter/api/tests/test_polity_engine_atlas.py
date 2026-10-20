"""The polity engine atlas (scripts/build_engine_atlas.py): its code references stay true, its links resolve,
every journaled event type has a place in the replay, and it builds for a recorded run."""

from __future__ import annotations

import copy
import importlib.util
import json
import re
import sys
from pathlib import Path
from types import ModuleType

import yaml

from api.domain.polity.events import EVENT_TYPES, INSTITUTIONAL_EVENT_TYPES
from api.domain.polity.run_polity_simulation import TICK_PHASES

BACKEND = Path(__file__).resolve().parents[2]
FIXTURE_RUN = BACKEND / "polity_fixtures" / "runs" / "explorer-fixture"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "build_engine_atlas", BACKEND / "scripts" / "build_engine_atlas.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["build_engine_atlas"] = module
    spec.loader.exec_module(module)
    return module


atlas = _load()


def test_every_code_reference_still_points_at_the_line_it_names() -> None:
    stale = atlas.stale_refs(atlas.load_content())
    assert stale == [], (
        "the atlas points at code that moved or changed: run `python scripts/build_engine_atlas.py "
        "--relocate` (from fast_api_voter/); if the code itself changed, update scripts/engine_atlas/content.json",
        stale,
    )


def test_every_mechanic_named_by_a_phase_a_link_or_a_lane_exists() -> None:
    content = atlas.load_content()
    mechanics = set(content["mechanics"])
    named = {m for phase in content["phases"] for m in phase["mechanics"]}
    named |= {
        m
        for mech in content["mechanics"].values()
        for m in mech["feeds"] + mech["fedBy"]
    }
    named |= {lane["mech"] for lane in content["lanes"] if lane["mech"] is not None}
    assert named - mechanics == set()
    assert {mech["phase"] for mech in content["mechanics"].values()} <= set(
        range(0, len(content["phases"]) + 1)
    )
    assert {mech["fam"] for mech in content["mechanics"].values()} <= {
        f["id"] for f in content["families"]
    }


def test_every_event_type_the_engine_journals_has_a_lane_in_the_replay() -> None:
    # A new event class fails here until the atlas says which mechanic it belongs to.
    lanes = {
        t.split(":")[0] for lane in atlas.load_content()["lanes"] for t in lane["types"]
    }
    assert set(EVENT_TYPES) - lanes == set(), (
        "add the new event type to a lane in scripts/engine_atlas/content.json"
    )
    assert lanes - set(EVENT_TYPES) == set(), (
        "a lane names an event type the engine no longer journals"
    )


def test_relocate_follows_code_that_only_moved_and_reports_code_that_changed() -> None:
    lines = (
        (BACKEND / "api" / "domain" / "polity" / "legitimacy.py")
        .read_text()
        .splitlines()
    )
    true_line = next(
        i
        for i, line in enumerate(lines, start=1)
        if line.startswith("def update_legitimacy(")
    )
    content = {
        "refs": [
            {"file": "legitimacy.py", "line": 1, "expect": "def update_legitimacy("},
            {"file": "legitimacy.py", "line": 1, "expect": "def no_such_function("},
        ]
    }
    moved = copy.deepcopy(content)
    unresolved = atlas.relocate(moved)
    assert moved["refs"][0]["line"] == true_line
    assert len(unresolved) == 1 and "no_such_function" in unresolved[0]
    assert atlas.stale_refs(moved) == [
        unresolved[0].split(":")[0] + ":1 no longer reads 'def no_such_function('"
    ]


def test_the_atlas_builds_for_the_committed_fixture_run(tmp_path: Path) -> None:
    page = atlas.build(FIXTURE_RUN, tmp_path / "atlas.html").read_text()
    assert "/*ATLAS_DATA*/" not in page and "/*REPLAY_DATA*/" not in page
    blocks = dict(
        re.findall(
            r'<script type="application/json" id="([a-z-]+)">(.*?)</script>', page, re.S
        )
    )
    content, replay = (
        json.loads(blocks["atlas-data"]),
        json.loads(blocks["replay-data"]),
    )
    events = [
        json.loads(line)
        for line in (FIXTURE_RUN / "events.jsonl").read_text().splitlines()
        if line.strip()
    ]
    assert len(replay["events"]) == len(events) and replay["meta"]["ticks"] == max(
        e["tick"] for e in events
    )
    assert len(replay["series"]) == replay["meta"]["ticks"] + 1
    assert content["institutional"] == sorted(
        INSTITUTIONAL_EVENT_TYPES
    )  # read from the code, not copied
    assert all(" None" not in e["s"] for e in replay["events"] if e["ty"] == "elected")


def test_an_event_summary_reads_as_a_sentence() -> None:
    assert (
        atlas.summary(
            {
                "event_type": "elected",
                "citizen_id": 2,
                "payload": {"office": "president"},
            }
        )
        == "citizen 2 elected president"
    )
    assert (
        atlas.summary(
            {"event_type": "party_dissolved", "payload": {"party_id": 4, "members": 1}}
        )
        == "party 4 dissolved (1 member)"
    )
    assert (
        atlas.summary(
            {
                "event_type": "pressure_action",
                "citizen_id": 7,
                "motif": "301",
                "payload": {"act": 3},
            }
        )
        == "citizen 7: mobilise (motif 301)"
    )
    assert (
        atlas.summary(
            {"event_type": "brand_new_event", "citizen_id": None, "payload": {}}
        )
        == "brand new event"
    )


def test_the_phases_are_the_engine_s_own_in_the_engine_s_order() -> None:
    phases = atlas.load_content()["phases"]
    assert [p["ref"]["label"] for p in phases] == [
        phase.__name__ for phase in TICK_PHASES
    ]
    assert [p["n"] for p in phases] == list(range(1, len(TICK_PHASES) + 1))


def test_the_ids_the_page_starts_from_exist() -> None:
    content = atlas.load_content()
    assert {node[0] for node in content["loop_nodes"]} | {
        content["start_mechanic"]
    } <= set(content["mechanics"])
    assert content["start_module"] in {
        m["name"] for g in content["groups"] for m in g["modules"]
    }


def _default_text(value: object) -> str:
    return (
        {True: "true", False: "false", None: "null"}.get(value, str(value))
        if isinstance(value, bool) or value is None
        else str(value)
    )


def test_every_knob_names_a_real_setting_with_its_real_default() -> None:
    # The default column is prose: this keeps it equal to polity_config.yaml (the profile columns are not checked).
    config = yaml.safe_load(
        (BACKEND / "api" / "domain" / "polity" / "polity_config.yaml").read_text()
    )
    wrong = []
    for mechanic in atlas.load_content()["mechanics"].values():
        for name, default, *_ in mechanic["knobs"]:
            for path in (part.strip() for part in name.split("/")):
                node: object = config
                for key in path.split("."):
                    node = (
                        node.get(key, KeyError) if isinstance(node, dict) else KeyError
                    )
                stated = default.split(" ")[0]
                if node is KeyError:
                    wrong.append(f"{path}: no such setting")
                elif not (
                    _default_text(node) == stated
                    or (
                        isinstance(node, (int, float))
                        and not isinstance(node, bool)
                        and stated.replace(".", "", 1).isdigit()
                        and float(stated) == float(node)
                    )
                ):
                    wrong.append(
                        f"{path}: the atlas says {default!r}, polity_config.yaml says {node!r}"
                    )
    assert wrong == []


def test_embedded_data_cannot_close_or_open_a_script_element(tmp_path: Path) -> None:
    hostile = "<!--<script></script><img src=x onerror=alert(1)>&"
    text = atlas._embed({"s": hostile})
    assert "<" not in text and ">" not in text and "&" not in text
    assert json.loads(text) == {"s": hostile}


def test_institutional_summaries_name_who_did_what() -> None:
    joined = {
        "event_type": "coalition_decision",
        "payload": {"party_id": 3, "action": 1, "initiator": 2, "round": 1},
    }
    assert atlas.summary(joined) == "party 3 joins party 2's coalition (round 1)"
    floor = {
        "event_type": "confidence_vote_triggered",
        "citizen_id": 10,
        "payload": {"office": "president", "cause": "legitimacy_floor"},
    }
    assert (
        atlas.summary(floor)
        == "confidence vote on the president: legitimacy fell below the floor"
    )
    assert (
        atlas.summary(
            {"event_type": "coalition_formed", "payload": {"coalition": [0, 1]}}
        )
        == "coalition of parties 0, 1"
    )
