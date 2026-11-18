"""EXP-030: does the model's party founding follow what its forum prompt shows? CPU only, on the ten runs of EXP-028.

Finished experiment script (see archive/README.md): not imported, not type-checked, not collected by CI. Needs the runs'
`llm_prompts.jsonl` (POLITY_LOG_PROMPTS=1):

    python scripts/archive/read_founding_against_the_gate.py <model-runs-dir>

Every forum turn's user prompt carries one line, "N of the M citizens stand nearer to your positions than to their own party's
platform, you included; founding a party needs K". The kernel creates a party from a `found` turn only if N is at least K.
The script reads that N and K from each turn's prompt and prints how often the turn chose `found`, by whether N reaches K and
by N, per seed, plus the turns where the prompt also names a founding lock.
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


def main(base: Path) -> None:
    rows = []
    for seed in range(1, 11):
        run_id = f"stage2b-scenario-8y-p100-seed{seed}"
        d = base / run_id / "run" / run_id
        blob, calls = {}, {}
        for line in (d / "llm_prompts.jsonl").read_text().splitlines():
            x = json.loads(line)
            if "blob" in x:
                blob[x["blob"]] = x["text"]
            else:
                calls[x["call_id"]] = x
        for line in (d / "events.jsonl").read_text().splitlines():
            e = json.loads(line)
            if e["event_type"] != "forum_post":
                continue
            user = blob[calls[e["payload"]["llm_call_id"]]["user"]]
            m = STAND.search(user)
            move = (e["payload"].get("party_move") or "").split(" ")[0]
            rows.append(
                {
                    "seed": seed,
                    "tick": e["tick"],
                    "n": int(m[1]),
                    "pop": int(m[2]),
                    "need": int(m[3]),
                    "move": move,
                    "user": user,
                }
            )
    print(
        f"forum turns {len(rows)}; population values {sorted({r['pop'] for r in rows})}; needed values {sorted({r['need'] for r in rows})}"
    )
    found = lambda rs: sum(r["move"] == "found" for r in rs)  # noqa: E731
    elig = [r for r in rows if r["n"] >= r["need"]]
    inel = [r for r in rows if r["n"] < r["need"]]
    print(
        f"N reaches the need: {len(elig)} turns, {found(elig)} found ({found(elig) / len(elig):.1%}); N below it: {len(inel)} turns, {found(inel)} found"
    )
    print(
        "the turns that found with N below the need:",
        [
            (r["seed"], r["tick"], r["n"], r["need"])
            for r in inel
            if r["move"] == "found"
        ],
    )
    bins = defaultdict(lambda: [0, 0])
    for r in rows:
        k = r["n"] if r["n"] < 10 else 10 if r["n"] < 15 else 15 if r["n"] < 20 else 20
        bins[k][0] += r["move"] == "found"
        bins[k][1] += 1
    print(
        "by N (10 = 10-14, 15 = 15-19, 20 = 20 and over), found / turns:",
        {k: f"{a}/{b} = {a / b:.0%}" for k, (a, b) in sorted(bins.items())},
    )
    print("per seed, share of turns where N reaches the need / found among them:")
    for seed in range(1, 11):
        rs = [r for r in rows if r["seed"] == seed]
        el = [r for r in rs if r["n"] >= r["need"]]
        print(
            f"  seed {seed:2d}: {len(el) / len(rs):.0%} of {len(rs)} turns; found {found(el)}/{len(el)} = {found(el) / len(el):.0%}"
        )
    moves = Counter(r["move"] or "none" for r in rows)
    print("every forum turn's party_move:", dict(moves))
    print(
        "citizens: distinct founders per run are in EXP-028; first-year dissolutions there too"
    )


if __name__ == "__main__":
    main(Path(sys.argv[1]).expanduser())
