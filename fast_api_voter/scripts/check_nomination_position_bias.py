"""OBS-013: does a party's nomination follow the candidate, or the position it is listed at?

Reads a bake-off session on a bank with `nomination_permutation` cases (each population rendered twice,
the second time with every candidate list reversed) and compares the picks with what a uniform choice
would give. The frozen bank has five populations; a larger one is a bank of its own:

    python - <<'EOF'
    import sys; sys.path.insert(0, "scripts")
    from pathlib import Path
    from api.domain.polity import bakeoff_cases as bc
    from api.domain.polity.bakeoff_bank import LOGPROB_GATE_FAMILY, write_bank
    from bakeoff_cases import reference_config
    bc.NOMINATION_SEEDS = tuple(range(101, 161))
    bank = bc.generate_bank(reference_config(), families=[LOGPROB_GATE_FAMILY, "nomination_permutation"])
    write_bank(bank, Path("scripts/bakeoff_runs/bank_nomination_60_seeds.jsonl"))
    EOF
    python scripts/run_bakeoff.py --label nomination-60-seeds --families nomination_permutation \\
        --bank scripts/bakeoff_runs/bank_nomination_60_seeds.jsonl
    python scripts/check_nomination_position_bias.py scripts/bakeoff_runs/bank_nomination_60_seeds.jsonl \\
        scripts/bakeoff_runs/nomination-60-seeds

Usage (from fast_api_voter/): python scripts/check_nomination_position_bias.py <bank> <session directory>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.bakeoff_bank import read_bank  # noqa: E402
from api.domain.polity.bakeoff_statistics import wilson_interval  # noqa: E402


def upper_tail(sizes: list[int], hits: int) -> tuple[float, float]:
    """The hits a uniform pick over each list would give, and P(at least `hits`), exactly: the picks are
    independent Bernoulli(1/size) draws under that null, so the count follows a Poisson binomial."""
    distribution = [1.0]
    for size in sizes:
        p = 1 / size
        distribution = [
            (distribution[k] * (1 - p) if k < len(distribution) else 0.0) + (distribution[k - 1] * p if k > 0 else 0.0)
            for k in range(len(distribution) + 1)
        ]
    return sum(1 / size for size in sizes), sum(distribution[hits:])


def read_units(bank_path: Path, session: Path) -> list[dict[str, Any]]:
    """One row per party unit answered validly in both renderings: its list size, the position picked
    in each, and whether both picks are the same citizen."""
    cases = {c.case_id: c for c in read_bank(bank_path).cases if c.family == "nomination_permutation"}
    answered: dict[str, dict[str, Any]] = {}
    for line in (session / "results.jsonl").read_text(encoding="utf-8").splitlines():
        result = json.loads(line)
        if result["case_id"] in cases and result["pass"] == "main" and result["valid"]:
            answered[result["case_id"]] = result["answers"]
    renderings: dict[str, dict[str, str]] = {}
    for case_id, case in cases.items():
        renderings.setdefault(case.labels["pair"], {})[case.labels["rendering"]] = case_id
    units = []
    for pair in renderings.values():
        if pair.get("original") not in answered or pair.get("renumbered") not in answered:
            continue
        original, renumbered = cases[pair["original"]], cases[pair["renumbered"]]
        for party, listed in original.labels["listed"].items():
            picks = (answered[pair["original"]].get(party), answered[pair["renumbered"]].get(party))
            reversed_list = renumbered.labels["listed"][party]
            size = len(listed)
            if all(isinstance(p, int) and 1 <= p <= size for p in picks):
                units.append({"size": size, "pick": picks, "same": listed[str(picks[0])] == reversed_list[str(picks[1])]})
    return units


def report(label: str, units: list[dict[str, Any]]) -> None:
    if not units:
        return
    sizes = [u["size"] for u in units for _ in range(2)]
    last = sum((u["pick"][0] == u["size"]) + (u["pick"][1] == u["size"]) for u in units)
    first = sum((u["pick"][0] == 1) + (u["pick"][1] == 1) for u in units)
    expected, p_last = upper_tail(sizes, last)
    _, p_first = upper_tail(sizes, first)
    same = sum(u["same"] for u in units)
    position = sum(u["pick"][0] == u["pick"][1] for u in units)
    same_lo, same_hi = wilson_interval(same, len(units)) or (0.0, 1.0)
    pos_lo, pos_hi = wilson_interval(position, len(units)) or (0.0, 1.0)
    print(f"{label}: {len(units)} units, {min(u['size'] for u in units)}-{max(u['size'] for u in units)} contenders "
          f"(mean {sum(u['size'] for u in units) / len(units):.1f})")
    print(f"  last listed:  {last}/{len(sizes)} picks, {expected:.1f} expected, P(at least that many | uniform) = {p_last:.4f}")
    print(f"  first listed: {first}/{len(sizes)} picks, {expected:.1f} expected, P(at least that many | uniform) = {p_first:.4f}")
    print(f"  same citizen in both orders:  {same}/{len(units)} = {same / len(units):.1%} [{same_lo:.1%}, {same_hi:.1%}]")
    print(f"  same position in both orders: {position}/{len(units)} = {position / len(units):.1%} [{pos_lo:.1%}, {pos_hi:.1%}]")


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        print(__doc__)
        return 2
    units = read_units(Path(args[0]), Path(args[1]))
    report("all", units)
    report("2-4 contenders", [u for u in units if u["size"] <= 4])
    report("5 or more contenders", [u for u in units if u["size"] >= 5])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
