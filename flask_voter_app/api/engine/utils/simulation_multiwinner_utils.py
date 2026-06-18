"""
simulation_multiwinner_utils.py
Proportional and multi-winner voting methods.

Arrow's theorem applies to single-winner ranked rules; these multi-winner
methods satisfy different axiomatic properties and are designed to ensure
representational proportionality rather than a single collective choice.
"""
import math
from collections import defaultdict
from typing import Callable, Dict, List, Optional, Any


# ── Internal helpers ───────────────────────────────────────────────────────

def _normalise_votes(party_votes: Dict[str, float]) -> Dict[str, float]:
    """Return a copy with all values converted to floats (handles % inputs)."""
    return {p: float(v) for p, v in party_votes.items() if float(v) > 0}


# ── Single Transferable Vote ───────────────────────────────────────────────

def get_stv_winners(votes: list[Any], num_winners: int) -> List[str]:
    """
    Single Transferable Vote with Droop quota and fractional surplus transfer.

    Each vote is either a list of candidate names (ranking) or a dict with a
    'ranking' key (same format as simulation_ranked_utils).

    Returns the ordered list of elected candidates.
    """
    if not votes or num_winners <= 0:
        return []

    # Normalise input
    ballots: List[List[str]] = []
    for v in votes:
        if isinstance(v, dict):
            ballots.append(list(v.get("ranking", [])))
        else:
            ballots.append(list(v))

    n = len(ballots)
    droop_quota = n // (num_winners + 1) + 1

    # Pool: list of (weight, remaining_ranking)
    pool: List[tuple[float, List[str]]] = [(1.0, r[:]) for r in ballots]

    elected: List[str] = []
    eliminated: set[str] = set()

    def _first_active(ranking: List[str], excl: set[str]) -> Optional[str]:
        return next((c for c in ranking if c not in excl), None)

    while len(elected) < num_winners:
        excluded = eliminated | set(elected)

        # Tally first active choices
        counts: Dict[str, float] = defaultdict(float)
        for w, r in pool:
            c = _first_active(r, excluded)
            if c:
                counts[c] += w

        if not counts:
            break

        remaining_seats = num_winners - len(elected)

        # If ≤ remaining seats left, elect them all
        if len(counts) <= remaining_seats:
            elected.extend(sorted(counts, key=lambda c: -counts[c]))
            break

        # Any candidate at or above quota?
        above_quota = [(c, v) for c, v in counts.items() if v >= droop_quota]

        if above_quota:
            above_quota.sort(key=lambda x: -x[1])
            winner, winner_votes = above_quota[0]

            surplus = winner_votes - droop_quota
            transfer_factor = surplus / winner_votes if winner_votes > 0 else 0.0

            # Rebuild pool: ballots going to winner get multiplied by transfer_factor
            prev_excluded = eliminated | set(elected)  # state BEFORE electing winner
            new_pool: List[tuple[float, List[str]]] = []
            for w, r in pool:
                first = _first_active(r, prev_excluded)
                new_r = [c for c in r if c != winner]
                if not new_r:
                    continue  # exhausted ballot
                if first == winner:
                    new_pool.append((w * transfer_factor, new_r))
                else:
                    new_pool.append((w, new_r))

            pool = new_pool
            elected.append(winner)

        else:
            # Eliminate candidate with fewest first-choice votes (tie-break: alphabetical)
            min_v = min(counts.values())
            loser = min(c for c, v in counts.items() if v == min_v)
            eliminated.add(loser)
            # Ballots referencing loser will skip them via _first_active

    return elected[:num_winners]


# ── STV with full round-by-round detail ──────────────────────────────────────

def get_stv_result(
    votes:      List[List[str]],
    num_seats:  int,
    quota_type: str = "droop",
) -> Dict[str, Any]:
    """
    STV (Single Transferable Vote) with complete per-round audit trail.

    Parameters
    ----------
    votes      : List of full candidate rankings (each = one ballot).
    num_seats  : Number of seats to fill.
    quota_type : "droop" (default) or "hare".

    Returns
    -------
    {
        "elected": List[str],       # elected candidates in order
        "quota":   int,
        "rounds": [
            {
                "round":     int,
                "action":    "elect" | "eliminate" | "auto_elect",
                "candidate": str,
                "tallies":   {str: float},   # after transfers
                "transfers": {str: float},   # new votes received this round
            }
        ]
    }
    """
    if not votes or num_seats <= 0:
        return {"elected": [], "quota": 0, "rounds": []}

    n = len(votes)
    if quota_type == "hare":
        quota: int = max(1, n // num_seats)
    else:  # droop
        quota = n // (num_seats + 1) + 1

    # Pool: each entry is (weight: float, ranking: List[str])
    pool: List[tuple[float, List[str]]] = [(1.0, list(r)) for r in votes]

    elected:   List[str] = []
    eliminated: set[str] = set()
    rounds:    List[Dict[str, Any]] = []
    round_num  = 0

    def _tally() -> Dict[str, float]:
        excluded = eliminated | set(elected)
        counts: Dict[str, float] = defaultdict(float)
        for w, r in pool:
            first = next((c for c in r if c not in excluded), None)
            if first:
                counts[first] += w
        return dict(counts)

    while len(elected) < num_seats:
        excluded     = eliminated | set(elected)
        counts       = _tally()

        if not counts:
            break

        remaining_seats = num_seats - len(elected)

        # All active candidates (with or without current votes)
        all_candidate_names = sorted({c for r in votes for c in r})
        active_candidates   = [c for c in all_candidate_names if c not in excluded]

        # Auto-elect when active candidates ≤ remaining seats
        if len(active_candidates) <= remaining_seats:
            for c in sorted(active_candidates, key=lambda x: -counts.get(x, 0)):
                if c not in elected:
                    rounds.append({
                        "round":     round_num,
                        "action":    "auto_elect",
                        "candidate": c,
                        "tallies":   dict(counts),
                        "transfers": {},
                    })
                    elected.append(c)
                    round_num += 1
            break

        above_quota = [(c, v) for c, v in counts.items() if v >= quota]

        if above_quota:
            above_quota.sort(key=lambda x: (-x[1], x[0]))
            winner, winner_votes = above_quota[0]
            surplus         = winner_votes - quota
            transfer_factor = surplus / winner_votes if winner_votes > 0 else 0.0

            prev_excl     = eliminated | set(elected)
            transfers: Dict[str, float] = defaultdict(float)
            new_pool:  List[tuple[float, List[str]]] = []

            for w, r in pool:
                first = next((c for c in r if c not in prev_excl), None)
                new_r = [c for c in r if c != winner]
                if not new_r:
                    continue
                if first == winner:
                    new_w = w * transfer_factor
                    new_pool.append((new_w, new_r))
                    # Next active candidate after winner receives these votes
                    next_c = next((c for c in new_r if c not in prev_excl and c != winner), None)
                    if next_c:
                        transfers[next_c] += new_w
                else:
                    new_pool.append((w, new_r))

            pool = new_pool
            elected.append(winner)

            # Recompute tallies after transfer
            new_counts = _tally()
            rounds.append({
                "round":     round_num,
                "action":    "elect",
                "candidate": winner,
                "tallies":   dict(new_counts),
                "transfers": dict(transfers),
            })
            round_num += 1

        else:
            # Eliminate: candidate with fewest votes (tie-break alphabetical)
            min_v = min(counts.values())
            loser = min(c for c, v in counts.items() if v == min_v)
            eliminated.add(loser)

            new_counts = _tally()
            rounds.append({
                "round":     round_num,
                "action":    "eliminate",
                "candidate": loser,
                "tallies":   dict(new_counts),
                "transfers": {},
            })
            round_num += 1

    return {"elected": elected[:num_seats], "quota": quota, "rounds": rounds}


# ── Party-list methods ─────────────────────────────────────────────────────

def get_dhondt_winners(party_votes: Dict[str, float], num_seats: int) -> Dict[str, int]:
    """
    D'Hondt highest averages method.
    Divisor sequence: 1, 2, 3, 4, …  → favours larger parties slightly.
    Used for French European elections, Spanish general elections, etc.
    """
    pv = _normalise_votes(party_votes)
    seats: Dict[str, int] = {p: 0 for p in pv}
    for _ in range(num_seats):
        winner = max(pv, key=lambda p: pv[p] / (seats[p] + 1))
        seats[winner] += 1
    return seats


def get_sainte_lague_winners(party_votes: Dict[str, float], num_seats: int) -> Dict[str, int]:
    """
    Sainte-Laguë highest averages method.
    Divisor sequence: 1, 3, 5, 7, …  → more proportional than D'Hondt,
    especially for small parties. Used in Norway, Sweden, New Zealand.
    """
    pv = _normalise_votes(party_votes)
    seats: Dict[str, int] = {p: 0 for p in pv}
    for _ in range(num_seats):
        winner = max(pv, key=lambda p: pv[p] / (2 * seats[p] + 1))
        seats[winner] += 1
    return seats


def get_largest_remainder_winners(
    party_votes: Dict[str, float],
    num_seats: int,
    quota: str = "hare",
) -> Dict[str, int]:
    """
    Largest remainder method.
    - Hare quota  = total_votes / num_seats       (used in Israel, Ukraine)
    - Droop quota = floor(total / (seats+1)) + 1  (used in some countries)

    Each party gets floor(votes / quota) automatic seats; remaining seats
    go to parties with the largest fractional remainders.
    """
    pv = _normalise_votes(party_votes)
    total = sum(pv.values())
    if total == 0 or num_seats <= 0:
        return {p: 0 for p in pv}

    q = total / num_seats if quota == "hare" else (total // (num_seats + 1) + 1)

    auto: Dict[str, int] = {p: int(pv[p] / q) for p in pv}
    remainders: Dict[str, float] = {p: (pv[p] / q) - auto[p] for p in pv}

    remaining = num_seats - sum(auto.values())
    for p in sorted(remainders, key=lambda p: remainders[p], reverse=True)[:remaining]:
        auto[p] += 1

    return auto


# ── Proportionality metrics ────────────────────────────────────────────────

def compute_proportionality_metrics(
    party_votes: Dict[str, float],
    seats_won: Dict[str, int],
) -> Dict[str, Any]:
    """
    Calculate standard proportionality metrics for a seat allocation.

    Returns gallagher_index, largest_deviation, and the Laakso-Taagepera
    effective number of parties (in votes and in seats).
    """
    total_votes = sum(party_votes.values())
    total_seats = sum(seats_won.values())

    if total_votes == 0 or total_seats == 0:
        return {
            "gallagher_index": None,
            "largest_deviation": None,
            "effective_parties_votes": None,
            "effective_parties_seats": None,
        }

    all_parties = set(party_votes) | set(seats_won)
    vote_pct = {p: party_votes.get(p, 0.0) / total_votes for p in all_parties}
    seat_pct = {p: seats_won.get(p, 0) / total_seats for p in all_parties}

    # Gallagher index (LSq): sqrt(0.5 × Σ(seat% − vote%)²)
    gallagher = math.sqrt(
        0.5 * sum((seat_pct[p] - vote_pct[p]) ** 2 for p in all_parties)
    )

    # Largest absolute deviation
    deviations = {p: seat_pct[p] - vote_pct[p] for p in all_parties}
    ld_party = max(deviations, key=lambda p: abs(deviations[p]))

    # Laakso-Taagepera: 1 / Σp²
    eff_votes = 1.0 / sum(v ** 2 for v in vote_pct.values() if v > 0)
    eff_seats = 1.0 / sum(v ** 2 for v in seat_pct.values() if v > 0)

    return {
        "gallagher_index": round(gallagher, 4),
        "largest_deviation": {
            "party": ld_party,
            "deviation": round(deviations[ld_party], 4),
        },
        "effective_parties_votes": round(eff_votes, 3),
        "effective_parties_seats": round(eff_seats, 3),
    }


# ── Main comparison function ───────────────────────────────────────────────

def compare_multiwinner_methods(
    party_votes: Dict[str, float],
    num_seats: int,
    voter_rankings: Optional[List[Any]] = None,
) -> Dict[str, Any]:
    """
    Run all proportional methods on the same vote distribution and return
    seats + proportionality metrics for each, plus a ranking by Gallagher index.

    party_votes  — {party_name: vote_count_or_pct}
    num_seats    — total seats to fill
    voter_rankings — optional ranked ballots for STV (same format as
                     simulation_ranked_utils; candidates used as proxies)
    """
    pv = _normalise_votes(party_votes)
    results: Dict[str, Any] = {}

    # Party-list methods
    party_list_methods: List[tuple[str, Callable[[], Any]]] = [
        ("dhondt",                  lambda: get_dhondt_winners(pv, num_seats)),
        ("sainte_lague",            lambda: get_sainte_lague_winners(pv, num_seats)),
        ("largest_remainder_hare",  lambda: get_largest_remainder_winners(pv, num_seats, "hare")),
        ("largest_remainder_droop", lambda: get_largest_remainder_winners(pv, num_seats, "droop")),
    ]
    for key, fn in party_list_methods:
        seats = fn()
        results[key] = {
            "seats": seats,
            "metrics": compute_proportionality_metrics(pv, seats),
        }

    # STV (individual rankings)
    if voter_rankings:
        stv_elected = get_stv_winners(voter_rankings, num_seats)
        results["stv"] = {
            "winners": stv_elected,
            "seats": {},  # no party mapping without external lookup
        }

    # Comparison: rank by Gallagher index (lower = more proportional)
    ranked = sorted(
        [
            (key, results[key]["metrics"]["gallagher_index"])
            for key in ("dhondt", "sainte_lague", "largest_remainder_hare", "largest_remainder_droop")
            if results[key]["metrics"].get("gallagher_index") is not None
        ],
        key=lambda x: x[1],
    )

    results["comparison"] = {
        "most_proportional":  ranked[0][0]  if ranked else None,
        "least_proportional": ranked[-1][0] if ranked else None,
        "gallagher_ranking":  [m for m, _ in ranked],
    }

    return results


# ── SPAV ──────────────────────────────────────────────────────────────────────

def get_spav_result(
    approval_ballots: List[List[str]],
    num_seats:        int,
) -> Dict[str, Any]:
    """
    Sequential Proportional Approval Voting (SPAV).

    Each ballot is a list of approved candidate names.
    After each seat is filled, the weight of ballots that approved the winner
    is divided by (1 + number_of_elected_already_approved_by_that_ballot).

    Satisfies Proportional Justified Representation (PJR).

    Returns
    -------
    {
        "elected":  List[str],
        "rounds": [{"round": int, "winner": str, "scores": {cand: float}, "weights": [float]}]
    }
    """
    if not approval_ballots or num_seats <= 0:
        return {"elected": [], "rounds": []}

    # Derive candidate set from ballots
    all_cands: List[str] = []
    for b in approval_ballots:
        for c in b:
            if c not in all_cands:
                all_cands.append(c)

    n          = len(approval_ballots)
    weights    = [1.0] * n           # each ballot starts with weight 1
    elected:   List[str] = []
    rounds:    List[Dict[str, Any]] = []

    for seat in range(num_seats):
        remaining = [c for c in all_cands if c not in elected]
        if not remaining:
            break

        # Compute weighted approval score for each remaining candidate
        scores: Dict[str, float] = {c: 0.0 for c in remaining}
        for i, ballot in enumerate(approval_ballots):
            for c in ballot:
                if c in remaining:
                    scores[c] += weights[i]

        winner = max(remaining, key=lambda c: (scores[c], -all_cands.index(c)))
        elected.append(winner)

        rounds.append({
            "round":   seat,
            "winner":  winner,
            "scores":  {c: round(scores[c], 4) for c in remaining},
            "weights": [round(w, 4) for w in weights],
        })

        # Update weights: divide by (1 + number of elected already approved)
        for i, ballot in enumerate(approval_ballots):
            elected_in_ballot = sum(1 for c in elected if c in ballot)
            weights[i] = 1.0 / (1 + elected_in_ballot) if elected_in_ballot > 0 else weights[i]

    return {"elected": elected, "rounds": rounds}


# ── Phragmén ──────────────────────────────────────────────────────────────────

def get_phragmen_result(
    approval_ballots: List[List[str]],
    num_seats:        int,
) -> Dict[str, Any]:
    """
    Phragmén's sequential approval method (1894), "load" variant.

    Each ballot accumulates a "load" equal to the sum of loads of elected
    candidates it approved. The algorithm selects the candidate whose election
    minimises the maximum load on any ballot that approves them.

    Satisfies the maximin property: minimises the maximum load across ballots.
    Fairness guarantee stronger than D'Hondt for minority protection.

    Returns
    -------
    {
        "elected":  List[str],
        "rounds": [{"round": int, "winner": str, "max_load": float, "loads": [float]}]
    }
    """
    if not approval_ballots or num_seats <= 0:
        return {"elected": [], "rounds": []}

    all_cands: List[str] = []
    for b in approval_ballots:
        for c in b:
            if c not in all_cands:
                all_cands.append(c)

    n       = len(approval_ballots)
    loads   = [0.0] * n              # cumulative load per ballot
    elected: List[str] = []
    rounds:  List[Dict[str, Any]] = []

    for seat in range(num_seats):
        remaining = [c for c in all_cands if c not in elected]
        if not remaining:
            break

        best_candidate: Optional[str] = None
        best_max_load  = math.inf
        best_new_loads: List[float] = loads[:]

        for c in remaining:
            supporters = [i for i, b in enumerate(approval_ballots) if c in b]
            if not supporters:
                continue

            # Each supporter's new load = old_load + 1/|supporters|
            load_increment = 1.0 / len(supporters)
            new_max = max(
                (loads[i] + load_increment for i in supporters),
                default=0.0,
            )

            if new_max < best_max_load or (
                new_max == best_max_load
                and (best_candidate is None or c < best_candidate)
            ):
                best_max_load   = new_max
                best_candidate  = c
                best_new_loads  = loads[:]
                for i in supporters:
                    best_new_loads[i] += load_increment

        if best_candidate is None:
            break

        elected.append(best_candidate)
        loads = best_new_loads

        rounds.append({
            "round":    seat,
            "winner":   best_candidate,
            "max_load": round(best_max_load, 4),
            "loads":    [round(l, 4) for l in loads],
        })

    return {"elected": elected, "rounds": rounds}
