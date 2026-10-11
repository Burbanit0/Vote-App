"""OBS-047's numbers come from scripts/check_observations.py recalls: its reading of a journal, on a small one."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_observations.py"


def _event(tick: int, kind: str, payload: dict, citizen: int | None = None) -> str:
    return json.dumps({"tick": tick, "event_type": kind, "citizen_id": citizen, "payload": payload}) + "\n"


def test_recalls_reads_presidencies_pressure_and_replays_the_legitimacy_rules(tmp_path: Path) -> None:
    run = tmp_path / "run"
    run.mkdir()
    lines = [_event(0, "elected", {"office": "president", "attempt": 0}, 1)]
    for tick in range(4):  # approved by 70%, under pressure 0.3: legitimacy 0.8 -> 0.495 -> 0.22 -> 0 (clamped)
        lines.append(_event(tick, "legitimacy_updated", {"office": "president", "mandate_strength": 0.8, "approval": 0.7,
                                                         "ecart": 0.3, "legitimacy": 0.5}, 1))
        lines += [_event(tick, "pressure_action", {"act": act}, 50 + i) for i, act in enumerate((3, 3, 1, 0))]
    lines += [
        _event(3, "recalled", {"office": "president", "trigger": "legitimacy_floor"}, 1),
        _event(4, "elected", {"office": "president", "attempt": 1}, 2),  # the snap winner, to the next election
        _event(4, "legitimacy_updated", {"office": "president", "mandate_strength": 0.6, "approval": 0.6, "ecart": 0.0,
                                         "legitimacy": 0.6}, 2),
        _event(8, "elected", {"office": "president", "attempt": 0}, 3),  # elected on the run's last tick
        _event(8, "legitimacy_updated", {"office": "president", "mandate_strength": 0.7, "approval": 0.7, "ecart": 0.0,
                                         "legitimacy": 0.7}, 3),
    ]
    (run / "events.jsonl").write_text("".join(lines), encoding="utf-8")
    out = subprocess.run([sys.executable, str(SCRIPT), "recalls", str(tmp_path)], capture_output=True, text=True,
                         check=True).stdout
    assert "presidential elections 3, recalled 1, full terms 0" in out
    assert "approved by a majority 1; ticks in office median 3" in out
    assert "snap winners to the next election 1, elected on the run's last tick 1, other 0" in out
    assert "pressure acts 16, MOBILIZE 8 (50.0%), SIGN 4" in out
    assert "recalled: mobilize 2.0, sign 1.0, consulted 4.0" in out
    rules = {line.split("recalled in the span served")[0].strip(): line.split("served")[1].split(";")[0].strip()
             for line in out.splitlines() if "recalled in the span served" in line}
    assert rules["shipped: 0.9 L + 0.1 m - e"] == "1 of 1"
    assert rules["pressure on support's scale: 0.9 L + 0.1 (m - e)"] == "0 of 1"
    assert rules["the floor recalls only a president a majority disapproves"] == "0 of 1"
