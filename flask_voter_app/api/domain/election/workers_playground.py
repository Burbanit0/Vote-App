"""
api.domain.election.workers_playground — the Lab-reshape *playground* workers,
split out of the workers.py monolith (incremental decomposition).

Pure `data: dict -> (body, http_status)` workers for the single-electorate
playground: profile-simulate (P1), assembly + scorecard (P3/P5), and the
democratic-frontier modules (temporal, issue-voting, structural fairness).
Self-contained: depends only on the engine utils and ._helpers.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

import numpy as _np

from api.engine.utils.simulation_metrics import compare_all_methods
from api.engine.utils.profile_engine import (
    build_profile, cycle_rate, project_ballot, ballot_metrics, compatible_methods,
    turnout_mask, community_voters, spatial_cycle_rate,
)
from api.engine.utils.simulation_multiwinner_utils import (
    compute_proportionality_metrics, get_dhondt_winners, get_sainte_lague_winners,
)
from ._helpers import inter_method_agreement as _inter_method_agreement


# ── Profile-simulate (Lab reshape P1) ─────────────────────────────────────────

_PROFILE_DEFAULT_CANDS = [
    {"name": "Alice", "x": -0.5, "y": -0.2},
    {"name": "Bob",   "x":  0.5, "y":  0.2},
    {"name": "Carol", "x":  0.0, "y":  0.3},
]


def _profile_simulate_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /profile-simulate (Lab reshape P1).

    Builds a preference profile from a user-chosen source (spatial / impartial /
    mallows / urn / handcrafted), applies the behaviour transform, runs every method
    via compare_all_methods(override_utilities=...), and returns winners + the
    profile's 2D embedding + the paradox/cycle rate (the robustness read-out).
    """
    source       = str(data.get("source", "spatial"))
    behavior     = str(data.get("behavior", "sincere"))
    dims         = max(1, min(3, int(data.get("dims", 2))))
    valence      = bool(data.get("valence", False))
    num_voters   = max(10, min(1000, int(data.get("num_voters", 300))))
    seed         = int(data.get("seed", 42))
    source_params: Dict[str, float] = {
        k: float(v) for k, v in (data.get("source_params") or {}).items()
    }
    cand_specs   = (data.get("candidates") or _PROFILE_DEFAULT_CANDS)[:8]
    handcrafted  = data.get("handcrafted_matrix")
    turnout_cfg  = data.get("turnout") or {}
    turnout_model = str(turnout_cfg.get("model", "full"))
    turnout_int   = float(turnout_cfg.get("intensity", 0.0))

    names_in = [str(c.get("name", f"C{i}")) for i, c in enumerate(cand_specs)]
    if len(names_in) < 2:
        return {"error": "At least 2 candidates required"}, 400
    if source == "handcrafted":
        if not handcrafted or len(handcrafted) < 1:
            return {"error": "handcrafted source requires a non-empty matrix"}, 400
        if any(len(row) != len(names_in) for row in handcrafted):
            return {"error": "each handcrafted row must match the candidate count"}, 400

    electorate = data.get("electorate")
    composed = bool(electorate and electorate.get("mode") == "composed"
                    and electorate.get("communities"))
    try:
        built = build_profile(
            source, cand_specs, num_voters, dims, valence, behavior,
            source_params, seed, handcrafted_matrix=handcrafted,
            turnout_model=turnout_model, turnout_intensity=turnout_int,
            electorate=electorate if composed else None,
        )
    except ValueError as exc:
        return {"error": str(exc)}, 400

    matrix = built["matrix"]
    names  = built["names"]
    voters     = [{"id": vid} for vid in matrix]
    candidates = [{"name": n} for n in names]

    # ── Ballot projection (frontier FA-1) ──────────────────────────────────
    # The counting rules see the EXPRESSED ballot, not the true utilities.
    ballot_cfg  = data.get("ballot") or {}
    ballot_type = str(ballot_cfg.get("type", "full"))
    truncate_at = ballot_cfg.get("truncate_at")
    score_lv    = int(ballot_cfg.get("score_levels") or 6)
    try:
        projected = project_ballot(
            matrix, names, ballot_type,
            truncate_at=int(truncate_at) if truncate_at else None,
            score_levels=score_lv,
        )
    except ValueError as exc:
        return {"error": str(exc)}, 400

    compat = compatible_methods(ballot_type)
    # The live read-out only needs winners + cycle rate, so the O(voters × methods)
    # strategic-vulnerability pass is skipped by default; the on-demand strategic
    # module opts in via compute_strategic=True.
    want_strategic = bool(data.get("compute_strategic", False))
    result = compare_all_methods(
        voters, candidates, [], override_utilities=projected,
        compute_strategic=want_strategic,
    )
    raw_methods = result.get("methods", {})
    methods_out: Dict[str, Any] = {
        name: (
            {"winner": md.get("winner"), "strategic_vulnerability": md.get("strategic_vulnerability")}
            if want_strategic else {"winner": md.get("winner")}
        )
        for name, md in raw_methods.items()
        if name in compat
    }
    incompatible = sorted(set(raw_methods) - compat)

    # Headline demo: same counting rule, different ballot → different winner.
    winner_flips: List[str] = []
    if ballot_type != "full":
        full_run = compare_all_methods(
            voters, candidates, [], override_utilities=matrix, compute_strategic=False
        )
        full_methods = full_run.get("methods", {})
        winner_flips = sorted(
            name for name in methods_out
            if full_methods.get(name, {}).get("winner") != methods_out[name]["winner"]
        )

    metrics = ballot_metrics(
        ballot_type, len(names),
        truncate_at=int(truncate_at) if truncate_at else None,
        score_levels=score_lv,
    )
    first_vid = next(iter(projected))
    sample_ballot = {n: round(float(v), 3) for n, v in projected[first_vid].items()}

    # Paradox rate: for a COMPOSED spatial electorate, compute a real spatial
    # cycle rate by re-sampling the mixture (a multimodal electorate can produce
    # genuine majority cycles); otherwise the statistical-culture estimator (0 for
    # the single-Gaussian spatial source).
    if source == "spatial" and composed:
        paradox_rate = spatial_cycle_rate(cand_specs, electorate, min(num_voters, 200), seed)
    else:
        paradox_rate = cycle_rate(source, names, min(num_voters, 200), source_params, seed)

    return {
        "methods":                methods_out,
        "condorcet_winner":       result.get("condorcet_winner"),
        "inter_method_agreement": _inter_method_agreement(methods_out),
        "cycle_rate":             paradox_rate,
        "candidate_names":        names,
        "display_points":         built["display_points"],
        "candidate_points":       built["candidate_points"],
        "num_voters":             len(matrix),
        "turnout_rate":           round(len(matrix) / max(1, num_voters), 4),
        "ballot_type":            ballot_type,
        "ballot_expressiveness":  metrics["expressiveness"],
        "ballot_cognitive_load":  metrics["cognitive_load"],
        "sample_ballot":          sample_ballot,
        "winner_flips":           winner_flips,
        "incompatible_methods":   incompatible,
    }, 200


# ── Assembly (Lab reshape P3) ─────────────────────────────────────────────────

def _assembly_voters(
    n: int, seed: int, ideology: str, electorate: Optional[Dict[str, Any]] = None
) -> "_np.ndarray":
    """Deterministic 2D voter cloud.

    When a composed `electorate` (community mixture) is supplied, the cloud is
    sampled from it so the parliament reflects the same electorate the leader
    views show; otherwise it falls back to the ideology presets.
    """
    if electorate and electorate.get("communities"):
        pts = community_voters(
            electorate["communities"],
            float(electorate.get("correlation", 0.0)),
            float(electorate.get("noise", 0.0)),
            n, seed, dims=2,
        )
        if pts.shape[0] >= 2:
            return pts
        # degenerate composition → fall through to the default cloud
    rng = _np.random.default_rng(seed)
    if ideology == "polarized":
        left = rng.random(n) < 0.5
        cx = _np.where(left, -0.5, 0.5)
        cy = _np.where(left, -0.3, 0.3)
        pts = _np.column_stack([rng.normal(cx, 0.22), rng.normal(cy, 0.3)])
    elif ideology == "centrist":
        pts = rng.normal(0.0, 0.25, size=(n, 2))
    else:
        pts = rng.normal(0.0, 0.45, size=(n, 2))
    return _np.clip(pts, -1.0, 1.0)


def _minimal_winning_coalitions(
    seats: Dict[str, int], positions: Dict[str, tuple], majority: int
) -> List[Dict[str, Any]]:
    """Minimal winning coalitions (every member pivotal), with ideological span =
    max pairwise distance between member parties. Sorted by smallest span (the
    'governable' ones first), capped at 12."""
    names = [p for p, s in seats.items() if s > 0]
    out: List[Dict[str, Any]] = []
    for mask in range(1, 1 << len(names)):
        members = [names[i] for i in range(len(names)) if mask >> i & 1]
        total = sum(seats[m] for m in members)
        if total < majority:
            continue
        # minimal: removing any member must drop below majority
        if any(total - seats[m] >= majority for m in members):
            continue
        span = 0.0
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                a, b = positions[members[i]], positions[members[j]]
                span = max(span, math.hypot(a[0] - b[0], a[1] - b[1]))
        out.append({"parties": sorted(members), "seats": total, "span": round(span, 4)})
    out.sort(key=lambda c: (c["span"], -c["seats"]))
    return out[:12]


def _allocate_assembly(
    d2: "_np.ndarray",
    band_axis: "_np.ndarray",
    names: List[str],
    sincere_choice: "_np.ndarray",
    structure: str,
    seats_total: int,
    threshold: float,
    appt: str,
    desertion: bool,
) -> Dict[str, Any]:
    """Core votes→seats allocation, shared by /assembly and /assembly-scorecard.

    `band_axis` is the voter coordinate used to draw the equal-population
    single-member districts (x normally; the gerrymander probe re-runs with y —
    a different 'map' over the same voters).
    Returns {choice, votes, seats, district_seats, excluded, threshold_waived,
    wasted, assembly_size}.
    """
    num_voters = len(sincere_choice)
    choice = sincere_choice.copy()

    # Duverger (P4): voters iteratively abandon non-viable parties for the
    # nearest viable one (FPTP: district top-2; PR/MMP lists: above-threshold).
    if desertion:
        order_b = _np.argsort(band_axis, kind="stable")
        d_bands = _np.array_split(order_b, seats_total) if structure == "fptp" else []
        for _ in range(3):  # a few best-response rounds reach a near fixed point
            new_choice = choice.copy()
            if structure == "fptp":
                for band in d_bands:
                    if len(band) < 2:
                        continue
                    counts = _np.bincount(choice[band], minlength=len(names))
                    viable = [int(i) for i in counts.argsort()[-2:] if counts[i] > 0]
                    if len(viable) < 2:
                        continue
                    sub = d2[_np.ix_(band, viable)]
                    nearest_viable = _np.array(viable)[sub.argmin(axis=1)]
                    movers = ~_np.isin(choice[band], viable)
                    new_choice[band[movers]] = nearest_viable[movers]
            else:
                counts = _np.bincount(choice, minlength=len(names))
                viable = [i for i in range(len(names))
                          if counts[i] > 0 and counts[i] / num_voters >= threshold]
                if viable and len(viable) < len(names):
                    sub = d2[:, viable]
                    nearest_viable = _np.array(viable)[sub.argmin(axis=1)]
                    movers = ~_np.isin(choice, viable)
                    new_choice[movers] = nearest_viable[movers]
            if (new_choice == choice).all():
                break
            choice = new_choice

    votes = {n: int((choice == i).sum()) for i, n in enumerate(names)}
    vote_share = {n: votes[n] / num_voters for n in names}
    allocate = get_sainte_lague_winners if appt == "sainte_lague" else get_dhondt_winners

    def _pr_alloc(n_seats: int) -> tuple[Dict[str, int], List[str], bool]:
        """Threshold-filtered proportional allocation. Returns (seats, excluded, waived)."""
        eligible = {n: votes[n] for n in names if vote_share[n] >= threshold and votes[n] > 0}
        waived = False
        if not eligible:  # nobody passes → waive the threshold rather than fail
            eligible = {n: votes[n] for n in names if votes[n] > 0}
            waived = True
        alloc = allocate(eligible, n_seats)
        seats = {n: int(alloc.get(n, 0)) for n in names}
        excluded = [n for n in names if n not in eligible]
        return seats, excluded, waived

    district_seats = {n: 0 for n in names}
    excluded: List[str] = []
    threshold_waived = False
    wasted = 0

    if structure == "fptp":
        # One single-member district per seat: equal-population bands along band_axis.
        order = _np.argsort(band_axis, kind="stable")
        bands = _np.array_split(order, seats_total)
        seats = {n: 0 for n in names}
        for band in bands:
            if len(band) == 0:
                continue
            counts = _np.bincount(choice[band], minlength=len(names))
            win = int(counts.argmax())
            seats[names[win]] += 1
            wasted += int(len(band) - counts[win])  # votes for district losers
        assembly_size = seats_total
    elif structure == "mmp":
        n_districts = max(1, seats_total // 2)
        order = _np.argsort(band_axis, kind="stable")
        bands = _np.array_split(order, n_districts)
        for band in bands:
            if len(band) == 0:
                continue
            counts = _np.bincount(choice[band], minlength=len(names))
            district_seats[names[int(counts.argmax())]] += 1
        target, excluded, threshold_waived = _pr_alloc(seats_total)
        # Compensatory top-up; overhang (district wins beyond target) is kept.
        seats = {n: max(target[n], district_seats[n]) for n in names}
        assembly_size = sum(seats.values())
        wasted = sum(votes[n] for n in excluded)
    else:  # pr
        seats, excluded, threshold_waived = _pr_alloc(seats_total)
        assembly_size = seats_total
        wasted = sum(votes[n] for n in excluded)

    return {
        "choice":           choice,
        "votes":            votes,
        "seats":            seats,
        "district_seats":   district_seats,
        "excluded":         excluded,
        "threshold_waived": threshold_waived,
        "wasted":           wasted,
        "assembly_size":    assembly_size,
    }


def _assembly_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /assembly (Lab reshape P3).

    One shared electorate, party-level question: votes → seats under
    PR (national lists, threshold + apportionment), FPTP (one single-member
    district per seat, districts drawn as equal-population bands along the x
    axis — geography correlates with ideology, which is what makes wasted votes
    and the winner's bonus legible), or MMP (half district seats, half
    compensatory top-up; overhang seats are kept, so the assembly can slightly
    exceed the nominal size).
    """
    parties_in  = (data.get("parties") or [])[:8]
    num_voters  = max(10, min(1000, int(data.get("num_voters", 400))))
    ideology    = str(data.get("ideology", "random"))
    seed        = int(data.get("seed", 42))
    structure   = str(data.get("structure", "pr"))
    seats_total = max(10, min(500, int(data.get("seats", 100))))
    threshold   = max(0.0, min(0.15, float(data.get("threshold", 0.05))))
    appt        = str(data.get("apportionment", "dhondt"))

    if len(parties_in) < 2:
        return {"error": "At least 2 parties required"}, 400

    names     = [str(p.get("name", f"P{i}")) for i, p in enumerate(parties_in)]
    positions = {n: (float(p.get("x", 0.0)), float(p.get("y", 0.0)))
                 for n, p in zip(names, parties_in)}
    pts = _np.array([[positions[n][0], positions[n][1]] for n in names])

    voters = _assembly_voters(num_voters, seed, ideology, data.get("electorate"))
    # Differential turnout (electorate realism): abstainers leave first.
    _tcfg = data.get("turnout") or {}
    voters = voters[turnout_mask(voters, pts, str(_tcfg.get("model", "full")),
                                 float(_tcfg.get("intensity", 0.0)))]
    num_voters = voters.shape[0]
    # Sincere party vote: nearest party in the plane.
    d2 = ((voters[:, None, :] - pts[None, :, :]) ** 2).sum(axis=2)
    sincere = d2.argmin(axis=1)

    alloc = _allocate_assembly(
        d2, voters[:, 0], names, sincere, structure, seats_total,
        threshold, appt, bool(data.get("strategic_desertion", False)),
    )
    votes            = alloc["votes"]
    vote_share       = {n: votes[n] / num_voters for n in names}
    seats            = alloc["seats"]
    district_seats   = alloc["district_seats"]
    excluded         = alloc["excluded"]
    threshold_waived = alloc["threshold_waived"]
    wasted           = alloc["wasted"]
    assembly_size    = alloc["assembly_size"]

    metrics = compute_proportionality_metrics(
        {n: float(votes[n]) for n in names}, seats
    )
    majority = assembly_size // 2 + 1
    coalitions = _minimal_winning_coalitions(seats, positions, majority)

    # ── Representation → governance (frontier FB-1) ─────────────────────────
    # (a) Ideological congruence: how far the elected body sits from the
    #     electorate's median — for the whole assembly (seat-weighted) and for
    #     the most cohesive minimal winning coalition (the likely government).
    seat_share_arr = _np.array([seats[n] for n in names], dtype=float) / max(1, assembly_size)
    assembly_pos = (seat_share_arr[:, None] * pts).sum(axis=0)
    median_pt = _np.median(voters, axis=0)
    governing_pos: Optional[List[float]] = None
    governing_gap: Optional[float] = None
    if coalitions:
        gov = coalitions[0]  # sorted most-cohesive first
        gov_seats = _np.array(
            [seats[n] if n in gov["parties"] else 0 for n in names], dtype=float
        )
        gov_seats /= max(1.0, gov_seats.sum())
        gp = (gov_seats[:, None] * pts).sum(axis=0)
        governing_pos = [round(float(gp[0]), 4), round(float(gp[1]), 4)]
        governing_gap = round(float(_np.linalg.norm(gp - median_pt)), 4)

    # (b) Descriptive mirror over the MODELLED attribute space: does the
    #     assembly look like the electorate, region by region of the plane?
    #     (No demographics are modelled, so none are invented.)
    regions = {
        "left_lib":   lambda a: (a[:, 0] < 0) & (a[:, 1] < 0),
        "left_cons":  lambda a: (a[:, 0] < 0) & (a[:, 1] >= 0),
        "right_lib":  lambda a: (a[:, 0] >= 0) & (a[:, 1] < 0),
        "right_cons": lambda a: (a[:, 0] >= 0) & (a[:, 1] >= 0),
    }
    mirror = []
    for key, pred in regions.items():
        elec = float(pred(voters).mean())
        in_region = pred(pts)
        asm = float((seat_share_arr * in_region).sum())
        mirror.append({
            "region": key,
            "electorate_share": round(elec, 4),
            "assembly_share": round(asm, 4),
        })

    return {
        "structure":      structure,
        "assembly_size":  assembly_size,
        "majority":       majority,
        "threshold_waived": threshold_waived,
        "parties": [
            {
                "name":           n,
                "x":              positions[n][0],
                "y":              positions[n][1],
                "votes":          votes[n],
                "vote_share":     round(vote_share[n], 4),
                "seats":          seats[n],
                "seat_share":     round(seats[n] / assembly_size, 4) if assembly_size else 0.0,
                "district_seats": district_seats[n],
                "excluded_by_threshold": n in excluded,
            }
            for n in names
        ],
        "gallagher_index":          metrics["gallagher_index"],
        "effective_parties_votes":  metrics["effective_parties_votes"],
        "effective_parties_seats":  metrics["effective_parties_seats"],
        "wasted_vote_share":        round(wasted / num_voters, 4),
        "coalitions": coalitions,
        "congruence": {
            "electorate_median": [round(float(median_pt[0]), 4), round(float(median_pt[1]), 4)],
            "assembly_position": [round(float(assembly_pos[0]), 4), round(float(assembly_pos[1]), 4)],
            "governing_position": governing_pos,
            "assembly_gap":  round(float(_np.linalg.norm(assembly_pos - median_pt)), 4),
            "governing_gap": governing_gap,
        },
        "mirror": mirror,
    }, 200


# ── Assembly scorecard (Lab reshape P5) ───────────────────────────────────────

_SCORECARD_STRUCTURES = ("pr", "fptp", "mmp")
_SCORECARD_AXES = (
    "proportionality", "pluralism", "effective_votes",
    "minority_representation", "governability", "gerrymander_resistance",
)


def _assembly_scorecard_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /assembly-scorecard (Lab reshape P5).

    Monte-Carlo scorecard: re-rolls the electorate `replications` times and, for
    EACH structure (pr / fptp / mmp) at the requested knobs, scores six axes in
    [0, 1] (higher = better, orientations stated):
      proportionality          1 − Gallagher/0.2 (clamped)
      pluralism                ENP(seats) / ENP(votes) — vote diversity surviving into seats
      effective_votes          1 − wasted-vote share
      minority_representation  share of parties ≥3% votes holding ≥1 seat
      governability            1 / size of the smallest winning coalition
      gerrymander_resistance   1 − seat-share shift when districts are redrawn
                               along y instead of x (PR: immune → 1)
    Every number carries a band (mean, p10, p90 over the re-rolls).
    """
    parties_in   = (data.get("parties") or [])[:8]
    num_voters   = max(10, min(1000, int(data.get("num_voters", 400))))
    ideology     = str(data.get("ideology", "random"))
    seed         = int(data.get("seed", 42))
    seats_total  = max(10, min(500, int(data.get("seats", 100))))
    threshold    = max(0.0, min(0.15, float(data.get("threshold", 0.05))))
    appt         = str(data.get("apportionment", "dhondt"))
    desertion    = bool(data.get("strategic_desertion", False))
    replications = max(8, min(40, int(data.get("replications", 24))))

    if len(parties_in) < 2:
        return {"error": "At least 2 parties required"}, 400

    names     = [str(p.get("name", f"P{i}")) for i, p in enumerate(parties_in)]
    positions = {n: (float(p.get("x", 0.0)), float(p.get("y", 0.0)))
                 for n, p in zip(names, parties_in)}
    pts = _np.array([[positions[n][0], positions[n][1]] for n in names])

    acc: Dict[str, Dict[str, List[float]]] = {
        s: {a: [] for a in _SCORECARD_AXES} for s in _SCORECARD_STRUCTURES
    }

    _tcfg = data.get("turnout") or {}
    _tmodel, _tint = str(_tcfg.get("model", "full")), float(_tcfg.get("intensity", 0.0))
    _electorate = data.get("electorate")
    for k in range(replications):
        voters = _assembly_voters(num_voters, seed + 101 * k, ideology, _electorate)
        voters = voters[turnout_mask(voters, pts, _tmodel, _tint)]
        nv = max(1, voters.shape[0])  # effective electorate after abstention
        d2 = ((voters[:, None, :] - pts[None, :, :]) ** 2).sum(axis=2)
        sincere = d2.argmin(axis=1)

        for structure in _SCORECARD_STRUCTURES:
            a = _allocate_assembly(d2, voters[:, 0], names, sincere, structure,
                                   seats_total, threshold, appt, desertion)
            votes, seats = a["votes"], a["seats"]
            size = max(1, a["assembly_size"])

            metrics = compute_proportionality_metrics(
                {n: float(votes[n]) for n in names}, seats
            )
            g   = float(metrics["gallagher_index"] or 0.0)
            env = float(metrics["effective_parties_votes"] or 1.0)
            ens = float(metrics["effective_parties_seats"] or 1.0)

            proportionality = max(0.0, 1.0 - g / 0.2)
            pluralism = min(1.0, ens / env) if env > 0 else 1.0
            effective_votes = 1.0 - a["wasted"] / nv
            visible = [n for n in names if votes[n] / nv >= 0.03]
            minority = (sum(1 for n in visible if seats[n] > 0) / len(visible)) if visible else 1.0
            majority = size // 2 + 1
            coalitions = _minimal_winning_coalitions(seats, positions, majority)
            min_size = min((len(c["parties"]) for c in coalitions), default=len(names))
            governability = 1.0 / max(1, min_size)
            if structure == "pr":
                gerry = 1.0  # no districts → redistricting cannot move seats
            else:
                b = _allocate_assembly(d2, voters[:, 1], names, sincere, structure,
                                       seats_total, threshold, appt, desertion)
                size_b = max(1, b["assembly_size"])
                tv = 0.5 * sum(abs(seats[n] / size - b["seats"][n] / size_b) for n in names)
                gerry = max(0.0, 1.0 - tv)

            acc[structure]["proportionality"].append(proportionality)
            acc[structure]["pluralism"].append(pluralism)
            acc[structure]["effective_votes"].append(effective_votes)
            acc[structure]["minority_representation"].append(minority)
            acc[structure]["governability"].append(governability)
            acc[structure]["gerrymander_resistance"].append(gerry)

    def _band(xs: List[float]) -> Dict[str, float]:
        arr = _np.array(xs, dtype=float)
        return {
            "mean": round(float(arr.mean()), 4),
            "lo":   round(float(_np.percentile(arr, 10)), 4),
            "hi":   round(float(_np.percentile(arr, 90)), 4),
        }

    return {
        "replications": replications,
        "structures": {
            s: {a: _band(acc[s][a]) for a in _SCORECARD_AXES}
            for s in _SCORECARD_STRUCTURES
        },
    }, 200


# ── Structural (un)fairness (frontier FC-2) ───────────────────────────────────

def _structural_fairness_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /structural-fairness (frontier FC-2).

    Four structural levers over the shared electorate, all stated conventions:
      · MALAPPORTIONMENT — districts of unequal population (sizes skewed by the
        `malapportionment` knob; bands along x): unequal vote weight, and the
        minimal vote share that can control a seat majority drops.
      · EFFICIENCY GAP — the gerrymander metric between the two largest
        parties on the (skewed) districting: (wasted_A − wasted_B) / two-party
        total, wasted = losing votes + surplus beyond 50 %+1.
      · PENROSE — council weighting demo over the same unequal districts:
        equal / proportional / square-root weights, with the citizen-power
        proxy weight_i/√pop_i (Penrose's approximation): √n equalises it.
      · CUMULATIVE vs BLOC at-large — M seats, one district: party-line bloc
        voting lets the plurality party sweep; cumulative voting with
        poll-informed nomination (k_i ≈ share·M candidates, votes spread
        evenly) lets a cohesive minority concentrate and win seats.
    """
    parties_in = (data.get("parties") or [])[:8]
    if len(parties_in) < 2:
        return {"error": "At least 2 parties required"}, 400
    num_voters = max(50, min(1000, int(data.get("num_voters", 400))))
    ideology   = str(data.get("ideology", "random"))
    seed       = int(data.get("seed", 42))
    n_dist     = max(5, min(60, int(data.get("districts", 20))))
    mal        = max(0.0, min(1.0, float(data.get("malapportionment", 0.6))))
    m_seats    = max(3, min(9, int(data.get("at_large_seats", 5))))

    names = [str(p.get("name", f"P{i}")) for i, p in enumerate(parties_in)]
    pts = _np.array([[float(p.get("x", 0.0)), float(p.get("y", 0.0))]
                     for p in parties_in])
    voters = _assembly_voters(num_voters, seed, ideology, data.get("electorate"))
    # A composed electorate is thinned by per-bloc turnout, so the effective count
    # can be below the request — use the actual count for the district splits and
    # the vote shares (otherwise over-scaled cuts leave empty trailing districts).
    num_voters = int(voters.shape[0])
    d2 = ((voters[:, None, :] - pts[None, :, :]) ** 2).sum(axis=2)
    choice = d2.argmin(axis=1)
    order = _np.argsort(voters[:, 0], kind="stable")

    # ── District splits: equal vs skewed populations (bands along x) ───────
    def _split(weights: "_np.ndarray") -> List["_np.ndarray"]:
        cuts = _np.cumsum(weights / weights.sum())[:-1]
        idx = (cuts * num_voters).astype(int)
        return _np.split(order, idx)

    equal_w  = _np.ones(n_dist)
    skewed_w = 1.0 + 3.0 * mal * (_np.arange(n_dist) / max(1, n_dist - 1))
    bands_eq, bands_sk = _split(equal_w), _split(skewed_w)

    def _fptp(bands: List["_np.ndarray"]) -> Dict[str, int]:
        seats = {n: 0 for n in names}
        for band in bands:
            if len(band) == 0:
                continue
            counts = _np.bincount(choice[band], minlength=len(names))
            seats[names[int(counts.argmax())]] += 1
        return seats

    votes_nat = {n: int((choice == i).sum()) for i, n in enumerate(names)}
    seats_eq, seats_sk = _fptp(bands_eq), _fptp(bands_sk)
    g_eq = compute_proportionality_metrics({n: float(votes_nat[n]) for n in names}, seats_eq)
    g_sk = compute_proportionality_metrics({n: float(votes_nat[n]) for n in names}, seats_sk)

    def _min_share_for_majority(bands: List["_np.ndarray"]) -> float:
        pops = sorted(len(b) for b in bands)
        need = n_dist // 2 + 1
        return sum(p // 2 + 1 for p in pops[:need]) / num_voters

    pops_sk = [len(b) for b in bands_sk]
    malapportionment_out = {
        "pop_per_seat_ratio": round(max(pops_sk) / max(1, min(pops_sk)), 3),
        "gallagher_equal":  g_eq["gallagher_index"],
        "gallagher_skewed": g_sk["gallagher_index"],
        "min_share_majority_equal":  round(_min_share_for_majority(bands_eq), 4),
        "min_share_majority_skewed": round(_min_share_for_majority(bands_sk), 4),
    }

    # ── Efficiency gap (two largest parties, skewed districting) ───────────
    top2 = sorted(range(len(names)), key=lambda i: -votes_nat[names[i]])[:2]
    a_i, b_i = top2
    wasted_a = wasted_b = two_party_total = 0
    for band in bands_sk:
        counts = _np.bincount(choice[band], minlength=len(names))
        va, vb = int(counts[a_i]), int(counts[b_i])
        two_party_total += va + vb
        win_threshold = (va + vb) // 2 + 1
        if va > vb:
            wasted_a += va - win_threshold
            wasted_b += vb
        else:
            wasted_b += vb - win_threshold
            wasted_a += va
    efficiency_gap_out = {
        "party_a": names[a_i],
        "party_b": names[b_i],
        "gap": round((wasted_a - wasted_b) / max(1, two_party_total), 4),
        "wasted_a": wasted_a,
        "wasted_b": wasted_b,
    }

    # ── Penrose square-root council over the unequal districts ─────────────
    # Floor populations at 1: a clustered (composed) electorate can leave a band
    # empty, and an empty district must not divide by zero — it is simply the
    # most malapportioned (a citizen there has unbounded relative weight, clamped).
    pops = _np.maximum(_np.array(pops_sk, dtype=float), 1.0)
    schemes = {
        "equal":        _np.ones(n_dist),
        "proportional": pops,
        "penrose":      _np.sqrt(pops),
    }
    penrose_out = {}
    for scheme, w in schemes.items():
        w = w / w.sum()
        citizen_power = w / _np.sqrt(pops)  # Penrose's per-citizen influence proxy
        penrose_out[scheme] = round(float(citizen_power.max() / citizen_power.min()), 3)

    # ── Cumulative vs bloc voting, M seats at large ─────────────────────────
    shares = _np.array([votes_nat[n] for n in names], dtype=float) / num_voters
    sweep = names[int(shares.argmax())]
    seats_bloc = {n: (m_seats if n == sweep else 0) for n in names}
    # Cumulative with poll-informed nomination: party i fields k_i candidates,
    # voters spread their M votes evenly → per-candidate strength share/k.
    k = _np.maximum(1, _np.round(shares * m_seats).astype(int))
    candidates = []
    for i, n in enumerate(names):
        if shares[i] <= 0:
            continue
        for _c in range(int(k[i])):
            candidates.append((shares[i] / k[i], n))
    candidates.sort(key=lambda t: -t[0])
    seats_cum = {n: 0 for n in names}
    for _strength, n in candidates[:m_seats]:
        seats_cum[n] += 1
    minority_seats_bloc = sum(s for n, s in seats_bloc.items() if n != sweep)
    minority_seats_cum  = sum(s for n, s in seats_cum.items() if n != sweep)
    cumulative_out = {
        "at_large_seats": m_seats,
        "largest_party": sweep,
        "seats_bloc": seats_bloc,
        "seats_cumulative": seats_cum,
        "minority_seats_bloc": minority_seats_bloc,
        "minority_seats_cumulative": minority_seats_cum,
    }

    return {
        "districts":        n_dist,
        "malapportionment": malapportionment_out,
        "efficiency_gap":   efficiency_gap_out,
        "penrose":          penrose_out,
        "cumulative":       cumulative_out,
    }, 200


# ── Issue voting & bundling paradoxes (frontier FB-2) ─────────────────────────

def _issue_voting_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /issue-voting (frontier FB-2).

    The bundling problem: voters elect a PACKAGE (the closest party platform,
    issue-agreement count), yet policy could also be decided ISSUE BY ISSUE
    (referendum majorities). The two can diverge — Ostrogorski's paradox /
    the discursive dilemma: a platform can win the election while the
    majority disagrees with it on every single issue.

    Modes (stated):
      · spatial — K issues are hyperplanes through the shared 2D electorate
        (deterministic from seed): a voter's stance on issue k is the side of
        hyperplane k they sit on; a party's platform likewise.
      · handcrafted — voter stances (V×K of ±1) and party platforms supplied
        directly, to build exact paradoxes.
    """
    mode = str(data.get("mode", "spatial"))

    if mode == "handcrafted":
        stances_in = data.get("voter_stances") or []
        platforms_in = data.get("party_platforms") or []
        if not stances_in or not platforms_in:
            return {"error": "handcrafted mode requires voter_stances and party_platforms"}, 400
        k = len(stances_in[0])
        if any(len(r) != k for r in stances_in) or any(len(p) != k for p in platforms_in):
            return {"error": "all stance/platform rows must share the same issue count"}, 400
        stances = _np.sign(_np.array(stances_in, dtype=float))
        platforms = _np.sign(_np.array(platforms_in, dtype=float))
        stances[stances == 0] = 1.0
        platforms[platforms == 0] = 1.0
        names = [str(n) for n in (data.get("party_names") or
                                  [f"P{i + 1}" for i in range(len(platforms_in))])]
        issue_labels = [f"Enjeu {j + 1}" for j in range(k)]
    else:
        parties_in = (data.get("parties") or [])[:8]
        if len(parties_in) < 2:
            return {"error": "At least 2 parties required"}, 400
        num_voters = max(10, min(1000, int(data.get("num_voters", 400))))
        ideology = str(data.get("ideology", "random"))
        seed = int(data.get("seed", 42))
        k = max(2, min(7, int(data.get("num_issues", 4))))
        names = [str(p.get("name", f"P{i}")) for i, p in enumerate(parties_in)]
        pts = _np.array([[float(p.get("x", 0.0)), float(p.get("y", 0.0))]
                         for p in parties_in])
        voters = _assembly_voters(num_voters, seed, ideology, data.get("electorate"))
        rng = _np.random.default_rng(seed + 7)
        # Issue k = a hyperplane w·x + b through the plane (stated convention).
        w = rng.normal(size=(k, 2))
        w /= _np.linalg.norm(w, axis=1, keepdims=True)
        b = rng.uniform(-0.25, 0.25, size=k)
        stances = _np.sign(voters @ w.T + b)
        platforms = _np.sign(pts @ w.T + b)
        stances[stances == 0] = 1.0
        platforms[platforms == 0] = 1.0
        issue_labels = [f"Enjeu {j + 1}" for j in range(k)]

    n_voters = stances.shape[0]
    # Bundled vote: closest platform by issue agreement (ties → first party).
    agreement = (stances[:, None, :] == platforms[None, :, :]).sum(axis=2)
    choice = agreement.argmax(axis=1)
    votes = _np.bincount(choice, minlength=len(names))
    winner_idx = int(votes.argmax())

    issues = []
    divergent_count = 0
    for j in range(stances.shape[1]):
        yes_share = float((stances[:, j] > 0).mean())
        majority = 1 if yes_share >= 0.5 else -1
        winner_plank = int(platforms[winner_idx, j])
        divergent = winner_plank != majority
        if divergent:
            divergent_count += 1
        issues.append({
            "label":          issue_labels[j],
            "yes_share":      round(yes_share, 4),
            "majority":       majority,
            "winner_plank":   winner_plank,
            "divergent":      divergent,
        })

    return {
        "mode":            mode,
        "parties": [
            {"name": names[i],
             "platform": [int(p) for p in platforms[i]],
             "votes": int(votes[i]),
             "vote_share": round(float(votes[i]) / n_voters, 4)}
            for i in range(len(names))
        ],
        "bundled_winner":   names[winner_idx],
        "issues":           issues,
        "divergent_count":  divergent_count,
        "num_issues":       stances.shape[1],
        # Strong Ostrogorski: the elected platform loses the issue-by-issue
        # majority on MORE THAN HALF of the issues.
        "ostrogorski_paradox": divergent_count * 2 > stances.shape[1],
    }, 200


# ── Temporal mode (frontier FA-3): democracy as a repeated game ───────────────

def _temporal_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /temporal (frontier FA-3).

    Runs N SEQUENTIAL elections on one starting electorate. Between rounds
    (stated, documented dynamics — knobs, not hidden assumptions):
      · parties ADAPT: myopic local search — each party tries 8 compass moves of
        `adaptation_step` and keeps the one maximising its own sincere support,
        others held fixed (vote-seeking Downsian dynamics);
      · voters ATTACH: each voter drifts `loyalty_drift` of the way toward the
        party they voted for (partisan identification → endogenous polarization).
    Tracked per round: positions, vote/seat shares, largest-party winner,
    ENP(votes/seats), Gallagher, polarization (vote-weighted dispersion of party
    positions), alternation (largest party changed), congruence gap (distance
    between the seat-weighted assembly position and the voter median).
    Reproducible by seed. The question it answers: is the system still good
    AFTER repeated play?
    """
    parties_in  = (data.get("parties") or [])[:8]
    num_voters  = max(10, min(1000, int(data.get("num_voters", 400))))
    ideology    = str(data.get("ideology", "random"))
    seed        = int(data.get("seed", 42))
    structure   = str(data.get("structure", "pr"))
    seats_total = max(10, min(500, int(data.get("seats", 100))))
    threshold   = max(0.0, min(0.15, float(data.get("threshold", 0.05))))
    appt        = str(data.get("apportionment", "dhondt"))
    desertion   = bool(data.get("strategic_desertion", False))
    rounds      = max(2, min(30, int(data.get("rounds", 20))))
    adapt_step  = max(0.0, min(0.2, float(data.get("adaptation_step", 0.06))))
    loyalty     = max(0.0, min(0.2, float(data.get("loyalty_drift", 0.05))))

    if len(parties_in) < 2:
        return {"error": "At least 2 parties required"}, 400

    names = [str(p.get("name", f"P{i}")) for i, p in enumerate(parties_in)]
    pts = _np.array(
        [[float(p.get("x", 0.0)), float(p.get("y", 0.0))] for p in parties_in],
        dtype=float,
    )
    voters = _assembly_voters(num_voters, seed, ideology, data.get("electorate"))

    compass = _np.array(
        [[1, 0], [-1, 0], [0, 1], [0, -1], [1, 1], [1, -1], [-1, 1], [-1, -1]],
        dtype=float,
    )
    compass /= _np.linalg.norm(compass, axis=1, keepdims=True)

    rounds_out: List[Dict[str, Any]] = []
    prev_winner: Optional[str] = None
    alternations = 0

    for r in range(rounds):
        d2 = ((voters[:, None, :] - pts[None, :, :]) ** 2).sum(axis=2)
        sincere = d2.argmin(axis=1)
        alloc = _allocate_assembly(
            d2, voters[:, 0], names, sincere, structure,
            seats_total, threshold, appt, desertion,
        )
        votes, seats = alloc["votes"], alloc["seats"]
        size = max(1, alloc["assembly_size"])
        shares = _np.array([votes[n] for n in names], dtype=float) / num_voters
        seat_shares = _np.array([seats[n] for n in names], dtype=float) / size

        metrics = compute_proportionality_metrics(
            {n: float(votes[n]) for n in names}, seats
        )
        # Vote-weighted dispersion of party positions (the polarization index).
        pbar = (shares[:, None] * pts).sum(axis=0) / max(1e-9, shares.sum())
        polarization = float(_np.sqrt((shares * ((pts - pbar) ** 2).sum(axis=1)).sum()))
        # Assembly position (seat-weighted) vs the voter median.
        assembly_pos = (seat_shares[:, None] * pts).sum(axis=0)
        median_pt = _np.median(voters, axis=0)
        congruence_gap = float(_np.linalg.norm(assembly_pos - median_pt))

        winner = names[int(_np.argmax([seats[n] for n in names]))]
        alternation = prev_winner is not None and winner != prev_winner
        if alternation:
            alternations += 1
        prev_winner = winner

        rounds_out.append({
            "round": r,
            "parties": [
                {"name": n, "x": round(float(pts[i, 0]), 4), "y": round(float(pts[i, 1]), 4),
                 "vote_share": round(float(shares[i]), 4), "seats": seats[n]}
                for i, n in enumerate(names)
            ],
            "winner":         winner,
            "enp_votes":      metrics["effective_parties_votes"],
            "enp_seats":      metrics["effective_parties_seats"],
            "gallagher":      metrics["gallagher_index"],
            "polarization":   round(polarization, 4),
            "alternation":    alternation,
            "congruence_gap": round(congruence_gap, 4),
        })

        if r == rounds - 1:
            break

        # ── Party adaptation: myopic vote-seeking local search ──────────────
        # Campaign resources follow EXPRESSED votes (stated convention): a
        # party starved by strategic desertion cannot reposition, while the
        # well-funded ones optimise freely — the second half of Duverger's
        # squeeze. Under PR with no threshold expressed = sincere, so all
        # parties adapt at full strength and the system sustains itself.
        if adapt_step > 0:
            expressed = _np.array([votes[n] for n in names], dtype=float)
            max_votes = expressed.max() or 1.0
            for i in range(len(names)):
                step_i = adapt_step * (expressed[i] / max_votes)
                if step_i <= 0:
                    continue
                others = _np.delete(_np.arange(len(names)), i)
                others_min = d2[:, others].min(axis=1)
                best_pos = pts[i].copy()
                best_support = int((d2[:, i] < others_min).sum())
                for step_dir in compass:
                    trial = _np.clip(pts[i] + step_i * step_dir, -1.0, 1.0)
                    trial_d2 = ((voters - trial) ** 2).sum(axis=1)
                    support = int((trial_d2 < others_min).sum())
                    if support > best_support:
                        best_support = support
                        best_pos = trial
                pts[i] = best_pos
                # keep d2 fresh for the next party's evaluation
                d2[:, i] = ((voters - pts[i]) ** 2).sum(axis=1)

        # ── Voter attachment: drift toward the party they VOTED for ─────────
        # The expressed vote (post-desertion), not the sincere favourite: a
        # deserter attaches to the viable party they chose — this realignment
        # is precisely how Duverger's squeeze compounds over repeated play.
        if loyalty > 0:
            voters = _np.clip(
                voters + loyalty * (pts[alloc["choice"]] - voters), -1.0, 1.0
            )

    first, last = rounds_out[0], rounds_out[-1]
    return {
        "rounds":               rounds_out,
        "alternation_rate":     round(alternations / max(1, rounds - 1), 4),
        "enp_votes_initial":    first["enp_votes"],
        "enp_votes_final":      last["enp_votes"],
        "polarization_initial": first["polarization"],
        "polarization_final":   last["polarization"],
    }, 200


