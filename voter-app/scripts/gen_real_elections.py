"""Build the real-election backtest fixture from PrefLib ranked-ballot data.

Real elections are the honest test of the project's thesis ("the method changes
the winner"): on the SAME real ballots, different rules elect different people.
Burlington VT 2009 is the textbook case — plurality elects Wright, IRV elects
Kiss, the Condorcet winner is Montroll: three methods, three winners, one ballot
box.

Input  : PrefLib .toi (original, ties-incomplete) — unranked candidates are
         absent (not imputed), so ballot truncation is preserved honestly.
Output : voter-app/src/lib/__fixtures__/realElections.json — a compact weighted
         partial-order profile the client backtest engine reads.

Provenance: https://preflib.github.io/PrefLib-Jekyll/dataset/00005
            file 00005-00000002.toi (8980 ballots, 6 candidates, 384 orders).

Run:  python voter-app/scripts/gen_real_elections.py path/to/00005-00000002.toi
"""

from __future__ import annotations

import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "src", "lib", "__fixtures__", "realElections.json")

# PrefLib candidate ids are 1-based in this file order.
BTV_CANDIDATES = ["Kiss", "Montroll", "Simpson", "Smith", "Wright", "Write-In"]


def parse_toi(path: str) -> list[dict]:
    """Parse a .toi into [{n, groups:[[idx,...],...]}], candidate idx 0-based.
    Each group is a set of candidates the voter ranked equal at that position;
    candidates the voter did not list are simply absent (ranked below all)."""
    ballots = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            count_str, rest = line.split(":", 1)
            n = int(count_str)
            groups = []
            # Tokens are either `7` or `{7,3,1}`; split on commas outside braces.
            for tok in re.findall(r"\{[^}]*\}|[0-9]+", rest):
                ids = [int(x) - 1 for x in re.findall(r"[0-9]+", tok)]
                groups.append(sorted(ids))
            ballots.append({"n": n, "groups": groups})
    return ballots


def main() -> None:
    src = sys.argv[1] if len(sys.argv) > 1 else None
    if not src or not os.path.exists(src):
        sys.exit("usage: gen_real_elections.py <path to 00005-00000002.toi>")
    ballots = parse_toi(src)
    total = sum(b["n"] for b in ballots)

    # Sanity print: first-preference tallies (singleton tops) — must match the
    # documented 2009 round-one counts (Wright 2951, Kiss 2585, Montroll 2063…).
    first = [0.0] * len(BTV_CANDIDATES)
    for b in ballots:
        top = b["groups"][0]
        for c in top:
            first[c] += b["n"] / len(top)
    print(f"ballots={total} orders={len(ballots)}")
    for i, name in enumerate(BTV_CANDIDATES):
        print(f"  {name:10s} {first[i]:.1f}")

    payload = {
        "_source": "PrefLib 00005-00000002.toi",
        "_url": "https://preflib.github.io/PrefLib-Jekyll/dataset/00005",
        "elections": [
            {
                "id": "btv-2009",
                "title": "Burlington (VT) — maire 2009",
                "titleEn": "Burlington VT — 2009 mayor",
                "source": "PrefLib 00005-00000002 · 8980 bulletins classés (IRV réel)",
                "candidates": BTV_CANDIDATES,
                "voters": total,
                "ballots": ballots,
            }
        ],
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
        f.write("\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
