"""Build the real-election backtest fixture from published ranked-ballot data.

Real elections are the honest test of the project's thesis ("the method changes
the winner"): on the SAME real ballots, different rules elect different people.

Two ballot boxes ship:

· Burlington VT 2009 — the textbook case: plurality elects Wright, IRV elects
  Kiss, the Condorcet winner is Montroll. Three methods, three winners.
  Source: PrefLib .toi (original, ties-incomplete) — unranked candidates are
  absent (not imputed), so ballot truncation is preserved honestly.
  Provenance: https://preflib.github.io/PrefLib-Jekyll/dataset/00005
              file 00005-00000002.toi (8980 ballots, 6 candidates, 384 orders).

· Alaska 2022 special (US House, 16 Aug) — the modern, famous Condorcet failure
  of IRV: Peltola wins, yet Begich beats BOTH rivals head-to-head and is
  eliminated first for having the fewest first choices.
  Source: Graham-Squire & McCune, "Ranked Choice Voting And Condorcet Failure in
  the Alaska 2022 Special Election", arXiv:2303.00108, Table 4 — the published
  ballot-type breakdown of the state's cast vote record. NOT the raw CVR: it is
  the paper's cleaned 9-type profile over the three named candidates. We assert
  below that it reproduces every aggregate the paper reports (first-round counts,
  the Begich transfers, all three head-to-heads and the final round) — if any of
  those checks fail, the numbers are wrong and the build stops.

Output : voter-app/src/lib/__fixtures__/realElections.json — a compact weighted
         partial-order profile the client backtest engine reads.

Run:  python voter-app/scripts/gen_real_elections.py [path/to/00005-00000002.toi]
      Without the .toi, the existing Burlington entry is carried over unchanged
      and only Alaska is rebuilt.
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


# ── Alaska 2022 special ──────────────────────────────────────────────────────
# Graham-Squire & McCune, arXiv:2303.00108, Table 4 (ballot-type breakdown of the
# state's cast vote record). Index order below: 0 Begich · 1 Palin · 2 Peltola.
# A "—" in the paper means the voter expressed no further usable preference, so
# the remaining candidates are simply absent from the groups (never imputed).
AK_CANDIDATES = ["Begich", "Palin", "Peltola"]
AK_BALLOTS = [
    {"n": 11290, "groups": [[0]]},            # Begich only
    {"n": 27053, "groups": [[0], [1], [2]]},  # Begich > Palin > Peltola
    {"n": 15467, "groups": [[0], [2], [1]]},  # Begich > Peltola > Palin
    {"n": 21272, "groups": [[1]]},            # Palin only
    {"n": 34049, "groups": [[1], [0], [2]]},  # Palin > Begich > Peltola
    {"n": 3652, "groups": [[1], [2], [0]]},   # Palin > Peltola > Begich
    {"n": 23747, "groups": [[2]]},            # Peltola only
    {"n": 47407, "groups": [[2], [0], [1]]},  # Peltola > Begich > Palin
    {"n": 4645, "groups": [[2], [1], [0]]},   # Peltola > Palin > Begich
]

# Every figure the paper reports. These are the honesty gate: the 9 ballot types
# above must reproduce all of them, or we are shipping fiction.
AK_PUBLISHED_FIRST = {"Begich": 53810, "Palin": 58973, "Peltola": 75799}
AK_PUBLISHED_PAIRWISE = {  # (a, b): (a over b, b over a)
    ("Begich", "Palin"): (101217, 63618),
    ("Begich", "Peltola"): (87859, 79451),
    ("Peltola", "Palin"): (91266, 86026),
}
AK_PUBLISHED_TRANSFERS = {"Palin": 27053, "Peltola": 15467, "exhausted": 11290}
AK_PUBLISHED_FINAL = {"Peltola": 91266, "Palin": 86026}


def _rank_of(ballot: dict, cand: int) -> float:
    for g, grp in enumerate(ballot["groups"]):
        if cand in grp:
            return g
    return float("inf")  # unranked sits below everything ranked


def verify_alaska() -> None:
    """Re-derive the paper's own aggregates from the ballot types; abort on drift."""
    idx = {n: i for i, n in enumerate(AK_CANDIDATES)}

    first = {n: 0 for n in AK_CANDIDATES}
    for b in AK_BALLOTS:
        first[AK_CANDIDATES[b["groups"][0][0]]] += b["n"]
    assert first == AK_PUBLISHED_FIRST, f"first prefs {first} != {AK_PUBLISHED_FIRST}"

    for (a, b), (ab, ba) in AK_PUBLISHED_PAIRWISE.items():
        ia, ib = idx[a], idx[b]
        got_ab = sum(x["n"] for x in AK_BALLOTS if _rank_of(x, ia) < _rank_of(x, ib))
        got_ba = sum(x["n"] for x in AK_BALLOTS if _rank_of(x, ib) < _rank_of(x, ia))
        assert (got_ab, got_ba) == (ab, ba), f"{a} vs {b}: {(got_ab, got_ba)} != {(ab, ba)}"

    # Begich has the fewest first choices and is eliminated first.
    assert min(first, key=lambda k: first[k]) == "Begich"
    transfers = {"Palin": 0, "Peltola": 0, "exhausted": 0}
    for b in AK_BALLOTS:
        if b["groups"][0][0] != idx["Begich"]:
            continue
        rest = [g[0] for g in b["groups"][1:]]
        if rest:
            transfers[AK_CANDIDATES[rest[0]]] += b["n"]
        else:
            transfers["exhausted"] += b["n"]
    assert transfers == AK_PUBLISHED_TRANSFERS, f"transfers {transfers}"

    final = {
        "Palin": first["Palin"] + transfers["Palin"],
        "Peltola": first["Peltola"] + transfers["Peltola"],
    }
    assert final == AK_PUBLISHED_FINAL, f"final {final} != {AK_PUBLISHED_FINAL}"
    print(f"alaska: verified against arXiv:2303.00108 — {sum(b['n'] for b in AK_BALLOTS)} ballots")


def existing_burlington() -> dict:
    """Carry the already-generated Burlington entry over when no .toi is supplied."""
    with open(OUT, encoding="utf-8") as f:
        for e in json.load(f)["elections"]:
            if e["id"] == "btv-2009":
                return e
    sys.exit("no btv-2009 in the fixture and no .toi given — pass the PrefLib file")


def build_burlington(src: str) -> dict:
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

    return {
        "id": "btv-2009",
        "title": "Burlington (VT) — maire 2009",
        "titleEn": "Burlington VT — 2009 mayor",
        "source": "PrefLib 00005-00000002 · 8980 bulletins classés (IRV réel)",
        "candidates": BTV_CANDIDATES,
        "voters": total,
        "ballots": ballots,
    }


def build_alaska() -> dict:
    verify_alaska()
    return {
        "id": "ak-2022-special",
        "title": "Alaska — spéciale US House 2022",
        "titleEn": "Alaska — 2022 US House special",
        "source": "Graham-Squire & McCune, arXiv:2303.00108, tab. 4 · 188 582 bulletins classés (IRV réel)",
        "candidates": AK_CANDIDATES,
        "voters": sum(b["n"] for b in AK_BALLOTS),
        "ballots": AK_BALLOTS,
    }


def main() -> None:
    src = sys.argv[1] if len(sys.argv) > 1 else None
    burlington = build_burlington(src) if src and os.path.exists(src) else existing_burlington()
    if not src:
        print("no .toi given — carrying the existing Burlington entry over unchanged")

    payload = {
        "_source": "PrefLib 00005-00000002.toi · arXiv:2303.00108 tab. 4",
        "_url": "https://preflib.github.io/PrefLib-Jekyll/dataset/00005 · https://arxiv.org/abs/2303.00108",
        "elections": [burlington, build_alaska()],
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
        f.write("\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
