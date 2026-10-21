"""The polity engine atlas (scripts/build_engine_atlas.py): its code references stay true, its links resolve,
every journaled event type has a place in the replay, and it builds for a recorded run."""

from __future__ import annotations

import copy
import http.client
import importlib.util
import json
import re
import shutil
import sys
import threading
import time
import urllib.parse
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
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
    # Each data block is one line of compact JSON, written in as the value of `const A` / `let R`.
    blocks = dict(re.findall(r"^(?:const|let) ([AR]) = (.*);$", page, re.M))
    content, replay = json.loads(blocks["A"]), json.loads(blocks["R"])
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


def test_a_run_still_being_written_reads_without_its_half_written_last_line(
    tmp_path: Path,
) -> None:
    journal = tmp_path / "events.jsonl"
    whole = (FIXTURE_RUN / "events.jsonl").read_text().splitlines()[:3]
    journal.write_text("\n".join(whole) + '\n{"event_id": "torn", "ti')
    assert [e["event_id"] for e in atlas.read_events(journal)] == [
        json.loads(line)["event_id"] for line in whole
    ]
    for broken in (
        whole[0] + '\n{"torn"\n' + whole[1],  # in the middle
        "\n".join(whole)
        + '\n{"torn"\n',  # last, but newline-ended: written whole, and wrong
    ):
        journal.write_text(broken)
        with pytest.raises(json.JSONDecodeError):
            atlas.read_events(journal)


def _root_with_the_fixture(tmp_path: Path) -> Path:
    root = tmp_path / "runs"
    shutil.copytree(FIXTURE_RUN, root / "sweep" / "explorer-fixture")
    return root


def test_the_index_lists_runs_by_key_and_rereads_one_only_when_it_changes(
    tmp_path: Path,
) -> None:
    root = _root_with_the_fixture(tmp_path)
    index = atlas.RunIndex([root])
    [run] = index.listing()
    assert run["key"] == "0:sweep/explorer-fixture"
    assert run["status"] == "completed"  # no digest, but every planned tick journaled
    first = index.replay(run["key"])
    assert first is not None and json.loads(first)["config"]["run"]["seed"] is not None
    assert index.replay(run["key"]) is first  # unchanged files: the cached bytes
    (root / "sweep" / "explorer-fixture" / "progress.json").touch()  # a heartbeat
    assert index.replay(run["key"]) is first  # is no new event
    journal = root / "sweep" / "explorer-fixture" / "events.jsonl"
    journal.write_text("\n".join(journal.read_text().splitlines()[:5]) + "\n")
    assert len(json.loads(index.replay(run["key"]) or b"")["events"]) == 5
    assert (
        index.replay("0:../../etc") is None
        and index.replay("1:sweep/explorer-fixture") is None
    )


def test_a_run_s_status_comes_from_its_digest_else_from_how_far_and_how_lately_it_wrote() -> (
    None
):
    now, old = time.time(), time.time() - atlas.LIVE_SECONDS - 60
    midway = {"outcome": None, "ticks_reached": 7, "ticks_planned": 12}
    assert atlas.run_status(midway, {"tick_in_progress": 8}, now) == "live"
    assert atlas.run_status(midway, {"tick_in_progress": 8}, old) == "stopped"
    last = {**midway, "ticks_reached": 12}
    assert atlas.run_status(last, {"tick_in_progress": None}, now) == "completed"
    assert (
        atlas.run_status(last, {"tick_in_progress": 12}, now) == "live"
    )  # writing its last tick
    assert (
        atlas.run_status({**midway, "outcome": "interrupted"}, {}, now) == "interrupted"
    )


def test_the_server_serves_the_page_the_listing_and_a_run(tmp_path: Path) -> None:
    index = atlas.RunIndex([_root_with_the_fixture(tmp_path)])
    server = ThreadingHTTPServer(("127.0.0.1", 0), atlas.make_handler(index))
    threading.Thread(target=server.serve_forever, daemon=True).start()

    def get(path: str) -> tuple[int, bytes]:
        connection = http.client.HTTPConnection("127.0.0.1", server.server_address[1])
        try:
            connection.request("GET", path)
            response = connection.getresponse()
            return response.status, response.read()
        finally:
            connection.close()

    try:
        status, page = get("/")
        assert status == 200
        assert re.search(
            r"^let R = null;$", page.decode(), re.M
        )  # the page fetches its runs
        [run] = json.loads(get("/runs")[1])
        status, body = get("/run?k=" + urllib.parse.quote(run["key"]))
        assert status == 200 and json.loads(body)["meta"]["run_id"] == run["run_id"]
        assert (
            json.loads(body)["config"]["run"]["seed"] is not None
        )  # what the comparison diffs
        assert get("/run?k=nope")[0] == 404 and get("/elsewhere")[0] == 404
    finally:
        server.shutdown()
        server.server_close()


# ── the crowd panel (plan-scenarios-v1, step 1b) ──────────────────────────


def _crowd_run(tmp_path: Path, *, graph: bool = True) -> Path:
    """A run dir with a census at ticks 0 and 2, a checkpoint at tick 3, and a config for five citizens."""
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    config = {
        "run": {"population_size": 5, "seed": 1, "ticks_per_year": 2, "duration_years": 2},
        "social_graph": {"enabled": graph, "topology": "watts_strogatz", "mean_degree": 2, "rewiring_prob": 0.0, "evolving": False},
    }
    (run_dir / "config.json").write_text(json.dumps(config), encoding="utf-8")
    census = [
        {"citizen_id": i, "tick": tick, "year": tick // 2, "issue_positions": [i / 5 + tick / 10, 1 - i / 5, 0.5],
         "party_affiliation": i % 2, "office": "president" if i == 0 and tick else "aucun", "role": "electeur", "event_salience": 0.0}
        for tick in (0, 2) for i in (4, 3, 2, 1, 0)  # out of id order on purpose
    ]
    (run_dir / "snapshots.jsonl").write_text("".join(json.dumps(row) + "\n" for row in census), encoding="utf-8")
    checkpoint = {
        "tick": 3,
        "mobilized_last_tick": {"4": 0, "1": 0},
        "citizens": [
            {"citizen_id": i, "issue_positions": [i / 5 + 0.3, 1 - i / 5, 0.5], "party_affiliation": i % 2,
             "office": "president" if i == 0 else "aucun", "role": "elu" if i == 0 else "electeur",
             "anger": i / 10, "engagement": "exited" if i == 4 else "active", "event_salience": 0.2}
            for i in range(5)
        ],
    }
    (run_dir / "checkpoint.json").write_text(json.dumps(checkpoint), encoding="utf-8")
    (run_dir / "events.jsonl").write_text("", encoding="utf-8")
    return run_dir


def test_the_crowd_payload_joins_the_census_and_the_checkpoint_on_one_set_of_axes(tmp_path: Path) -> None:
    payload = atlas.crowd_payload(_crowd_run(tmp_path), {})
    assert payload["ticks"] == [0, 2, 3] and set(payload["frames"]) == {"0", "2", "3"}
    first, last = payload["frames"]["0"], payload["frames"]["3"]
    assert len(first["xy"]) == 5 and all(len(p) == 2 for p in first["xy"])
    assert first["anger"] is None and first["engagement"] is None  # the census has no emotions
    assert first["party"] == [0, 1, 0, 1, 0] and first["acted"] == []  # in id order, whatever the file's order
    assert last["anger"] == [0.0, 0.1, 0.2, 0.3, 0.4] and last["engagement"][4] == "exited" and last["acted"] == [1, 4]
    assert last["office"][0] == "president" and "role" not in last and "factors" not in last  # the page reads xy
    assert payload["axes"] == "pca"  # no frame carries latent factors: the issue positions' own axes
    # The same axes for every frame: citizens moved +0.1 on the first issue per census, so the projection
    # of a citizen moves the same way from frame to frame instead of the cloud being re-centred.
    moves = [[b - a for a, b in zip(p0, p2)] for p0, p2 in zip(first["xy"], payload["frames"]["2"]["xy"])]
    assert all(abs(m[0] - moves[0][0]) < 0.002 and abs(m[1] - moves[0][1]) < 0.002 for m in moves)  # 3-decimal rounding
    assert abs(moves[0][0]) + abs(moves[0][1]) > 0.1
    assert payload["edges"] and all(i < j for i, j in payload["edges"]) and max(j for _, j in payload["edges"]) < 5


def test_the_crowd_has_no_ties_when_the_graph_is_off_and_no_frames_without_a_census(tmp_path: Path) -> None:
    assert atlas.crowd_payload(_crowd_run(tmp_path, graph=False), {})["edges"] == []
    assert atlas._edges({"run": {"population_size": 5, "seed": 1}, "social_graph": {"enabled": True}}) == []  # unreadable: no ties, not no replay
    bare = tmp_path / "bare"
    bare.mkdir()
    (bare / "events.jsonl").write_text("", encoding="utf-8")
    assert atlas.crowd_payload(bare, {}) == {"ticks": [], "frames": {}, "edges": [], "axes": None}


def test_a_half_written_checkpoint_waits_for_the_next_read_and_the_frames_seen_stay(tmp_path: Path) -> None:
    run_dir = _crowd_run(tmp_path)
    frames: dict[int, dict[str, Any]] = {}
    assert atlas.crowd_payload(run_dir, frames)["ticks"] == [0, 2, 3]
    whole = (run_dir / "checkpoint.json").read_text(encoding="utf-8")
    (run_dir / "checkpoint.json").write_text(whole[: len(whole) // 2], encoding="utf-8")  # mid-rewrite
    assert atlas.crowd_payload(run_dir, frames)["ticks"] == [0, 2, 3]  # tick 3 kept from the earlier read
    (run_dir / "checkpoint.json").write_text(whole.replace('"tick": 3', '"tick": 4'), encoding="utf-8")
    assert atlas.crowd_payload(run_dir, frames)["ticks"] == [0, 2, 3, 4]  # the history accumulates


def test_a_census_tick_is_taken_only_once_every_citizen_is_in_it(tmp_path: Path) -> None:
    run_dir = _crowd_run(tmp_path)
    state: dict[str, Any] = {}
    rows = [json.dumps({"citizen_id": i, "tick": 4, "year": 2, "issue_positions": [0.5, 0.5, 0.5], "party_affiliation": 0, "office": "aucun"}) + "\n" for i in range(5)]
    with (run_dir / "snapshots.jsonl").open("a", encoding="utf-8") as census:
        census.write("".join(rows[:3]))  # the run is still writing tick 4's census
    assert atlas.crowd_payload(run_dir, state)["ticks"] == [0, 2, 3]
    with (run_dir / "snapshots.jsonl").open("a", encoding="utf-8") as census:
        census.write("".join(rows[3:]))
    assert atlas.crowd_payload(run_dir, state)["ticks"] == [0, 2, 3, 4]


def test_frames_with_latent_factors_are_drawn_on_them_and_the_others_mapped_onto_the_same_axes(tmp_path: Path) -> None:
    run_dir = _crowd_run(tmp_path)
    checkpoint = json.loads((run_dir / "checkpoint.json").read_text(encoding="utf-8"))
    for c in checkpoint["citizens"]:  # positions are a linear picture of two factors, as the kernel's sigmoid is near its middle
        c["latent_factors"] = [c["issue_positions"][0] * 2.0, c["issue_positions"][1] - 1.0]
    (run_dir / "checkpoint.json").write_text(json.dumps(checkpoint), encoding="utf-8")
    payload = atlas.crowd_payload(run_dir, {})
    assert payload["axes"] == "latent"
    for c, xy in zip(sorted(checkpoint["citizens"], key=lambda c: c["citizen_id"]), payload["frames"]["3"]["xy"]):
        assert xy == pytest.approx(c["latent_factors"], abs=2e-3)  # f1, f2 themselves where the frame has them
    census_xy = payload["frames"]["0"]["xy"]  # the year-0 census has no factors: the same map gives it the same axes
    assert len(census_xy) == 5 and census_xy != payload["frames"]["3"]["xy"]


def test_the_ring_keeps_every_census_frame_and_the_latest_checkpoint_frames(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run_dir = _crowd_run(tmp_path)
    monkeypatch.setattr(atlas, "CROWD_FRAMES", 2)
    state: dict[str, Any] = {}
    whole = (run_dir / "checkpoint.json").read_text(encoding="utf-8")
    for tick in (3, 5, 7):  # ticks between censuses (ticks_per_year is 2)
        (run_dir / "checkpoint.json").write_text(whole.replace('"tick": 3', f'"tick": {tick}'), encoding="utf-8")
        atlas.crowd_payload(run_dir, state)
    assert atlas.crowd_payload(run_dir, state)["ticks"] == [0, 2, 5, 7]  # tick 3 fell out of the ring; the census stayed


def test_the_ties_are_generated_once_per_run_and_kept_with_the_frames(tmp_path: Path) -> None:
    run_dir = _crowd_run(tmp_path)
    state: dict[str, Any] = {}
    edges = atlas.crowd_payload(run_dir, state)["edges"]
    (run_dir / "config.json").unlink()  # a second call needs neither the config nor the graph again
    assert atlas.crowd_payload(run_dir, state)["edges"] == edges and edges


def test_the_stamp_follows_the_checkpoint_so_a_new_tick_rebuilds_the_replay(tmp_path: Path) -> None:
    run_dir = _crowd_run(tmp_path)
    before = atlas._stamp(run_dir)
    checkpoint = run_dir / "checkpoint.json"
    checkpoint.write_text(checkpoint.read_text(encoding="utf-8") + " ", encoding="utf-8")
    assert atlas._stamp(run_dir) != before


def test_the_page_carries_the_crowd_panel_and_the_fixture_s_crowd(tmp_path: Path) -> None:
    page = atlas.build(FIXTURE_RUN, tmp_path / "atlas.html").read_text()
    # The fragment builds its block from script (block.id = "crowdblock"), so the page carries the name, not markup.
    assert atlas.CROWD_SLOT not in page and 'block.id = "crowdblock"' in page and "(function crowd()" in page
    replay = json.loads(dict(re.findall(r"^(?:const|let) ([AR]) = (.*);$", page, re.M))["R"])
    crowd = replay["crowd"]
    assert crowd["ticks"] == [0, 4, 8, 12] and crowd["frames"]["12"]["acted"] == [8, 29]
    assert len(crowd["frames"]["0"]["xy"]) == 40 and crowd["edges"]
