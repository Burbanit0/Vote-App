"""OBS-048's numbers come from scripts/check_observations.py amendments: its reading of a journal, on a small one."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_observations.py"


def _proposal(citizen: int, article: str, old: object, value: object, reason: str) -> str:
    payload = {"article": article, "old": old, "value": value, "reason": reason, "threshold": 0.6}
    return json.dumps({"tick": 1, "event_type": "amendment_proposed", "citizen_id": citizen, "payload": payload}) + "\n"


def test_amendments_counts_each_distinct_proposal_once(tmp_path: Path) -> None:
    run = tmp_path / "arm" / "run"
    run.mkdir(parents=True)
    term = ("institutions.president_term_limit", 2, 3, "Secure long-term stability and policy continuity.")
    lines = [_proposal(5, *term)] * 9  # one president re-proposing a rejected change: one proposal
    lines += [
        _proposal(5, "institutions.presidential_method", "two_round", "plurality", "Switch to plurality to ensure re-election"),
        _proposal(5, "petition.signature_threshold", 0.25, 0.2, "Lower the bar for citizens"),  # lowers it: no hold
    ]
    (run / "events.jsonl").write_text("".join(lines), encoding="utf-8")
    out = subprocess.run([sys.executable, str(SCRIPT), "amendments", f"one={tmp_path / 'arm'}"], capture_output=True,
                         text=True, check=True).stdout
    assert out.strip() == ("one: 1 runs, 3 distinct proposals (11 with repeats); extending the president's hold 1 (33%) "
                           "in 1 runs; voting method 1 in 1 runs; a reason naming their own interest 1 (33%)")
