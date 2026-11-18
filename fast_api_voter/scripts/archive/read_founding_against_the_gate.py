"""EXP-030: does the model's party founding follow what its forum prompt says is allowed? CPU only, on the ten runs of EXP-028.

Finished experiment script (see archive/README.md): not imported, not type-checked, not collected by CI. Needs the runs'
`llm_prompts.jsonl` (POLITY_LOG_PROMPTS=1) and `llm_calls.jsonl`:

    python scripts/archive/read_founding_against_the_gate.py <model-runs-dir>

The model's answer is read from the call log (`content`, the raw JSON), NOT from the journal: `forum_post.party_move` journals
only what the kernel accepted, and a refused `found` is logged as an empty move. Each forum turn's user prompt carries
  - "N of the M citizens stand nearer to your positions than to their own party's platform, you included; founding a party needs K"
  - for a member of a party founded in the last year: "Your party P was founded at tick T: until tick U, its members can neither
    found a party nor be brought into one."
The script prints the model's `found` rate (raw) and the kernel's acceptance, by lock and by whether N reaches K, and by N.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

STAND = re.compile(
    r"(\d+) of the (\d+) citizens stand nearer to your positions than to their own party's platform, you included; founding a party needs (\d+)"
)
LOCK = "can neither found a party"


def main(base: Path) -> None:
    rows = []
    for seed in range(1, 11):
        run_id = f"stage2b-scenario-8y-p100-seed{seed}"
        d = base / run_id / "run" / run_id
        blob, prompts, calls = {}, {}, {}
        for line in (d / "llm_prompts.jsonl").read_text().splitlines():
            x = json.loads(line)
            if "blob" in x:
                blob[x["blob"]] = x["text"]
            else:
                prompts[x["call_id"]] = x
        for line in (d / "llm_calls.jsonl").read_text().splitlines():
            x = json.loads(line)
            if x.get("kind") == "decision":
                calls[x["call_id"]] = x
        for line in (d / "events.jsonl").read_text().splitlines():
            e = json.loads(line)
            if e["event_type"] != "forum_post":
                continue
            call_id = e["payload"]["llm_call_id"]
            user = blob[prompts[call_id]["user"]]
            m = STAND.search(user)
            rows.append(
                {
                    "seed": seed,
                    "tick": e["tick"],
                    "n": int(m[1]),
                    "need": int(m[3]),
                    "locked": LOCK in user,
                    "raw": json.loads(calls[call_id]["content"]).get("party_move"),
                    "kernel": (e["payload"].get("party_move") or "").split(" ")[0]
                    or "none",
                }
            )
    print(f"forum turns {len(rows)}")
    print(
        "model's answers:",
        dict(Counter(r["raw"] for r in rows)),
        "| kernel's journaled moves:",
        dict(Counter(r["kernel"] for r in rows)),
    )

    def line(label: str, rs: list[dict]) -> None:
        f, k = (
            sum(r["raw"] == "found" for r in rs),
            sum(r["kernel"] == "found" for r in rs),
        )
        print(
            f" {label:22s} turns {len(rs):5d}  model said found {f:4d} ({f / max(1, len(rs)):4.0%})  kernel accepted {k}"
        )

    unlocked = [r for r in rows if not r["locked"]]
    locked = [r for r in rows if r["locked"]]
    print("by lock and by whether N reaches the need:")
    line("unlocked, N below need", [r for r in unlocked if r["n"] < r["need"]])
    line("unlocked, N reaches need", [r for r in unlocked if r["n"] >= r["need"]])
    line("locked, N below need", [r for r in locked if r["n"] < r["need"]])
    line("locked, N reaches need", [r for r in locked if r["n"] >= r["need"]])
    bins = defaultdict(lambda: [0, 0, 0])
    for r in unlocked:
        k = r["n"] if r["n"] < 10 else 10 if r["n"] < 15 else 15 if r["n"] < 20 else 20
        bins[k][0] += r["raw"] == "found"
        bins[k][1] += 1
        bins[k][2] += r["kernel"] == "found"
    print(
        "unlocked turns by N (10 = 10-14, 15 = 15-19, 20 = 20 and over): model said found / turns (kernel accepted):"
    )
    print(
        " ",
        {k: f"{a}/{n} = {a / n:.0%} ({c})" for k, (a, n, c) in sorted(bins.items())},
    )
    print(
        "per seed: unlocked turns with N at the need, model said found, kernel accepted:"
    )
    for seed in range(1, 11):
        rs = [r for r in unlocked if r["seed"] == seed and r["n"] >= r["need"]]
        print(
            f"  seed {seed:2d}: {len(rs):3d} turns, {sum(r['raw'] == 'found' for r in rs):3d} found, {sum(r['kernel'] == 'found' for r in rs):3d} accepted"
        )


if __name__ == "__main__":
    main(Path(sys.argv[1]).expanduser())
