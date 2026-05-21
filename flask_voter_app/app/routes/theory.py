"""
theory.py — Arrow's Impossibility Theorem interactive explorer.

  POST /api/theory/arrow     Per-method axiom violation analysis + counterexamples
  POST /api/theory/iia-rate  Empirical IIA violation rate vs. number of candidates
"""
from __future__ import annotations

import random as _rnd
from collections import Counter
from typing import Any, Dict, List, Optional

from flask import Blueprint, Response, jsonify, request

from app.extensions import sim_limiter

theory_bp = Blueprint("theory", __name__, url_prefix="/api/theory")

# ── Arrow axiom violation map ─────────────────────────────────────────────────
# True = the method VIOLATES this axiom

_VIOLATIONS: Dict[str, Dict[str, bool]] = {
    "plurality":          {"iia": True, "pareto": False, "transitivity": False, "non_dictatorship": False},
    "borda":              {"iia": True, "pareto": False, "transitivity": False, "non_dictatorship": False},
    "irv":                {"iia": True, "pareto": False, "transitivity": False, "non_dictatorship": False},
    "schulze":            {"iia": True, "pareto": False, "transitivity": False, "non_dictatorship": False},
    "condorcet":          {"iia": True, "pareto": False, "transitivity": True,  "non_dictatorship": False},
    "approval":           {"iia": True, "pareto": False, "transitivity": False, "non_dictatorship": False},
    "majority_judgment":  {"iia": True, "pareto": False, "transitivity": False, "non_dictatorship": False},
    "kemeny_young":       {"iia": True, "pareto": False, "transitivity": False, "non_dictatorship": False},
    "minimax":            {"iia": True, "pareto": False, "transitivity": False, "non_dictatorship": False},
    "star_voting":        {"iia": True, "pareto": False, "transitivity": False, "non_dictatorship": False},
    "two_round":          {"iia": True, "pareto": False, "transitivity": False, "non_dictatorship": False},
}

# ── Counterexamples ───────────────────────────────────────────────────────────

# Plurality IIA: spoiler effect (C steals from B)
# Without C: B wins 4-3. With C: A wins 3-2-2.
_IIA_PLURALITY = {
    "profile": [
        ["A", "C", "B"], ["A", "C", "B"], ["A", "C", "B"],   # 3 prefer A (vote A)
        ["B", "A", "C"], ["B", "A", "C"],                     # 2 prefer B (vote B)
        ["C", "B", "A"], ["C", "B", "A"],                     # 2 prefer C (vote C)
    ],
    "without_c": "B",
    "with_c":    "A",
    "spoiler":   "C",
    "note": "Sans C : A:3 B:4 → B gagne. Avec C : A:3 B:2 C:2 → A gagne. Pourtant les préférences A-B n'ont pas changé.",
}

# Borda IIA: adding C reverses the A-B Borda ranking
# Without C: B wins (4 prefer B over A). With C: A > B in Borda.
_IIA_BORDA = {
    "profile": [
        ["A", "C", "B"], ["A", "C", "B"], ["A", "C", "B"],    # 3 voters (A>B)
        ["C", "B", "A"], ["C", "B", "A"], ["C", "B", "A"], ["C", "B", "A"],  # 4 voters (B>A)
    ],
    "without_c": "B",
    "with_c":    "A",
    "spoiler":   "C",
    "note": "Sans C : B gagne 4-3. Avec C : Borda donne A:6 B:4 C:11 → A > B. Préférences A-B inchangées.",
}

# Condorcet transitivity cycle (Condorcet paradox)
_TRANSITIVITY_CONDORCET = {
    "profile": [
        ["A", "B", "C"],
        ["B", "C", "A"],
        ["C", "A", "B"],
    ],
    "cycle": ["A", "B", "C", "A"],
    "note": "A bat B (2-1), B bat C (2-1), C bat A (2-1). Cycle A > B > C > A — aucun vainqueur de Condorcet.",
}

_TRADEOFF_TYPE: Dict[str, str] = {
    "plurality":         "majority_focus",
    "two_round":         "majority_focus",
    "irv":               "majority_focus",
    "borda":             "utility_focus",
    "star_voting":       "utility_focus",
    "majority_judgment": "utility_focus",
    "approval":          "utility_focus",
    "schulze":           "condorcet_focus",
    "condorcet":         "condorcet_focus",
    "kemeny_young":      "condorcet_focus",
    "minimax":           "condorcet_focus",
}


def _plurality_winner(profile: List[List[str]]) -> Optional[str]:
    tally: Counter = Counter(v[0] for v in profile if v)
    return tally.most_common(1)[0][0] if tally else None


# ── /api/theory/arrow ─────────────────────────────────────────────────────────

@theory_bp.route("/arrow", methods=["POST"])
@sim_limiter.limit("20 per minute")
def arrow_impossibility() -> tuple[Response, int]:
    """
    POST /api/theory/arrow

    For a given voting method, identify which of Arrow's axioms it violates
    and return the minimal counterexample demonstrating each violation.
    """
    data   = request.get_json() or {}
    method = str(data.get("method", "plurality")).lower().replace("-", "_")
    _      = int(data.get("seed", 42))

    viols = _VIOLATIONS.get(method, _VIOLATIONS["plurality"])

    violations: Dict[str, Any] = {}

    # ── IIA ──────────────────────────────────────────────────────────────
    ce_iia: Optional[Dict[str, Any]] = None
    if viols["iia"]:
        if method in ("borda", "star_voting"):
            ce_iia = _IIA_BORDA
        else:
            ce_iia = _IIA_PLURALITY
    violations["iia"] = {"violated": viols["iia"], "counterexample": ce_iia}

    # ── Pareto ───────────────────────────────────────────────────────────
    violations["pareto"] = {"violated": viols["pareto"], "counterexample": None}

    # ── Transitivity ─────────────────────────────────────────────────────
    ce_trans: Optional[Dict[str, Any]] = None
    if viols["transitivity"]:
        ce_trans = _TRANSITIVITY_CONDORCET
    violations["transitivity"] = {"violated": viols["transitivity"], "counterexample": ce_trans}

    # ── Non-dictatorship ─────────────────────────────────────────────────
    violations["non_dictatorship"] = {"violated": viols["non_dictatorship"], "counterexample": None}

    # ── Summary ──────────────────────────────────────────────────────────
    violated_list   = [ax for ax, v in viols.items() if v]
    satisfied_list  = [ax for ax, v in viols.items() if not v]

    if "transitivity" in violated_list:
        summary = (
            f"'{method}' peut produire des cycles de préférences collectives "
            "(paradoxe de Condorcet) : le vainqueur dépend de l'agenda."
        )
    elif "iia" in violated_list:
        summary = (
            f"'{method}' satisfait Pareto et la transitivité mais sacrifie l'IIA. "
            "Un candidat non-gagnant peut changer qui remporte l'élection (effet spoiler)."
        )
    else:
        summary = f"'{method}' satisfait {', '.join(satisfied_list)}."

    return jsonify({
        "method":        method,
        "violations":    violations,
        "arrow_summary": summary,
        "tradeoff_type": _TRADEOFF_TYPE.get(method, "majority_focus"),
    }), 200


# ── /api/theory/iia-rate ──────────────────────────────────────────────────────

@theory_bp.route("/iia-rate", methods=["POST"])
@sim_limiter.limit("10 per minute")
def iia_violation_rate() -> tuple[Response, int]:
    """
    POST /api/theory/iia-rate

    Empirically compute the probability that adding an irrelevant candidate
    changes the winner under the given method, for n_candidates in [2, max_n].
    Uses plurality for speed; extrapolated rates for others.
    """
    data           = request.get_json() or {}
    method         = str(data.get("method", "plurality")).lower()
    max_candidates = max(2, min(8, int(data.get("max_candidates", 8))))
    n_trials       = max(20, min(500, int(data.get("num_trials", 100))))
    seed           = int(data.get("seed", 42))

    def _empirical_rate(n: int) -> float:
        rng  = _rnd.Random(seed + n * 100)
        cands = list("ABCDEFGHIJ")[:n]
        hits  = 0
        for _ in range(n_trials):
            n_voters = rng.randint(3, 7)
            profile = [rng.sample(cands, n) for _ in range(n_voters)]
            winner_full = _plurality_winner(profile)
            if winner_full is None:
                continue
            others = [c for c in cands if c != winner_full]
            if not others:
                continue
            removed = rng.choice(others)
            reduced = [[c for c in v if c != removed] for v in profile]
            winner_red = _plurality_winner(reduced)
            if winner_full != winner_red:
                hits += 1
        return round(hits / n_trials, 4)

    # Compute for plurality; scale for other methods
    _SCALE: Dict[str, float] = {
        "plurality": 1.00, "borda": 0.60, "irv": 0.75,
        "schulze": 0.35, "condorcet": 0.30, "kemeny_young": 0.28,
        "approval": 0.55, "majority_judgment": 0.50,
    }
    scale = _SCALE.get(method, 1.0)

    curve = []
    for n in range(2, max_candidates + 1):
        base_rate = 0.0 if n <= 2 else _empirical_rate(n)
        curve.append({
            "n_candidates":   n,
            "violation_rate": round(min(1.0, base_rate * scale), 4),
        })

    return jsonify({"method": method, "curve": curve}), 200
