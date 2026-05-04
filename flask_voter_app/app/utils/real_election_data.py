"""
real_election_data.py
Real historical election data and analysis tools.

Empirical demonstration: the same real population, different winners
depending on the voting method used.
"""
import math
from typing import Dict, List, Optional, Any

from .simulation_ranked_utils import (
    get_condorcet_winner,
    get_plurality_winner,
    get_two_round_winner,
    get_borda_winner,
    get_approval_winner,
    get_irv_winner,
    get_coombs_winner,
    get_bucklin_winner,
    get_minimax_winner,
    get_schulze_winner,
    get_positional_score_winner,
)
from .simulation_score_utils import (
    get_simple_score_winner,
    get_star_voting_winner,
    get_median_voting_winner,
    get_mean_median_hybrid_winner,
    get_variance_based_winner,
)

# ── Candidate ideological positions [0 = far-left, 1 = far-right] ─────────

CANDIDATE_POSITIONS: Dict[str, Dict[str, float]] = {
    "france_2002": {
        "Chirac":        0.62,
        "Le Pen":        0.92,
        "Jospin":        0.28,
        "Bayrou":        0.50,
        "Laguiller":     0.05,
        "Chevènement":   0.38,
        "Mamère":        0.20,
        "Besancenot":    0.08,
        "Saint-Josse":   0.70,
        "Madelin":       0.75,
        "Hué":           0.12,
        "Mégret":        0.95,
        "Taubira":       0.22,
    },
    "us_1992": {
        "Clinton": 0.30,
        "Bush":    0.70,
        "Perot":   0.52,
    },
    "uk_2015": {
        "Conservative":     0.72,
        "Labour":           0.28,
        "UKIP":             0.90,
        "Liberal Democrat": 0.50,
        "SNP":              0.20,
        "Green":            0.15,
        "Others":           0.45,
    },
}

# ── Real election data ─────────────────────────────────────────────────────

REAL_ELECTIONS: Dict[str, Dict] = {
    "france_2002": {
        "name":        "French Presidential Election — 1st round",
        "year":        2002,
        "country":     "France",
        "description": (
            "The 2002 French presidential election first round is the canonical "
            "example of how plurality voting can produce paradoxical outcomes. "
            "Jospin, the socialist prime minister and expected second-round "
            "finalist, was eliminated by Le Pen (far-right) due to left-wing "
            "vote splitting across 8 candidates. Under most other methods, "
            "Jospin would likely have proceeded to the second round or won outright."
        ),
        "candidates": [
            {"name": "Chirac",       "party": "RPR (centre-right)"},
            {"name": "Le Pen",       "party": "FN (far-right)"},
            {"name": "Jospin",       "party": "PS (centre-left)"},
            {"name": "Bayrou",       "party": "UDF (centre)"},
            {"name": "Laguiller",    "party": "LO (far-left)"},
            {"name": "Chevènement",  "party": "MDC (left-sovereign)"},
            {"name": "Mamère",       "party": "Verts (green-left)"},
            {"name": "Besancenot",   "party": "LCR (far-left)"},
            {"name": "Saint-Josse",  "party": "CPNT (rural/hunting)"},
            {"name": "Madelin",      "party": "DL (liberal-right)"},
            {"name": "Hué",          "party": "PCF (communist)"},
            {"name": "Mégret",       "party": "MNR (far-right)"},
            {"name": "Taubira",      "party": "PRG (left-radical)"},
        ],
        "results": {
            "first_round": {
                "Chirac":      5665855,
                "Le Pen":      4804713,
                "Jospin":      4610113,
                "Bayrou":      1949170,
                "Laguiller":   1630045,
                "Chevènement": 1518528,
                "Mamère":      1495724,
                "Besancenot":  1210562,
                "Saint-Josse": 1204689,
                "Madelin":     1113484,
                "Hué":          960480,
                "Mégret":       667026,
                "Taubira":      660447,
            },
            "total_voters": 28498471,
        },
        "source": "Conseil constitutionnel — résultats officiels 21 avril 2002",
    },

    "us_1992": {
        "name":        "US Presidential Election",
        "year":        1992,
        "country":     "United States",
        "description": (
            "The 1992 US presidential election is the classic spoiler-effect "
            "case study. Ross Perot, running as an independent centrist, received "
            "18.9% of the popular vote — the best third-party result since 1912. "
            "Many analysts argue Perot split the centre-right vote, costing Bush "
            "re-election. Under Condorcet or Borda, Perot's centrist position "
            "between Clinton and Bush would likely make him a very competitive "
            "candidate despite finishing third under plurality."
        ),
        "candidates": [
            {"name": "Clinton", "party": "Democratic"},
            {"name": "Bush",    "party": "Republican"},
            {"name": "Perot",   "party": "Independent"},
        ],
        "results": {
            "first_round": {
                "Clinton": 44909806,
                "Bush":    39103882,
                "Perot":   19741048,
            },
            "total_voters": 103755784,
        },
        "source": "Federal Election Commission — Official 1992 Presidential Results",
    },

    "uk_2015": {
        "name":        "UK General Election (national vote shares)",
        "year":        2015,
        "country":     "United Kingdom",
        "description": (
            "The 2015 UK general election produced one of the most disproportionate "
            "results in modern British history. UKIP received 12.6% of the national "
            "vote but won only 1 seat in Parliament. The SNP won 56 seats with 4.7%. "
            "This data uses national popular vote totals — the actual seat allocation "
            "by First-Past-The-Post constituency is not modelled here. This election "
            "is a textbook demonstration of why FPTP (plurality) fails proportionality."
        ),
        "candidates": [
            {"name": "Conservative",     "party": "Conservative"},
            {"name": "Labour",           "party": "Labour"},
            {"name": "UKIP",             "party": "UKIP"},
            {"name": "Liberal Democrat", "party": "Liberal Democrat"},
            {"name": "SNP",              "party": "SNP"},
            {"name": "Green",            "party": "Green"},
            {"name": "Others",           "party": "Other parties"},
        ],
        "results": {
            "first_round": {
                "Conservative":     11334576,
                "Labour":            9347304,
                "UKIP":              3881099,
                "Liberal Democrat":  2415916,
                "SNP":               1454436,
                "Green":             1157613,
                "Others":            1140666,
            },
            "total_voters": 30731610,
        },
        "source": "Electoral Commission — 2015 UK Parliamentary general election results",
    },
}


# ── Conversion: real votes → synthetic rankings ────────────────────────────

def convert_to_rankings(
    election_name: str,
    election_data: Dict,
    num_voters: int = 1000,
) -> List[List[str]]:
    """
    Convert real first-round vote counts into synthetic ranked ballots.

    Model: a voter who chose candidate X ranks all other candidates by
    ideological proximity to X (ascending distance). This reflects the
    assumption that left-wing voters prefer other left-wing candidates
    over right-wing ones, and vice versa.

    The number of synthetic voters for each candidate is proportional
    to their real vote share.
    """
    first_round = election_data["results"]["first_round"]
    total_votes = sum(first_round.values())
    positions = CANDIDATE_POSITIONS.get(election_name, {})
    candidate_names = list(first_round.keys())

    rankings: List[List[str]] = []

    for candidate, votes in first_round.items():
        n = max(1, round(num_voters * votes / total_votes))
        c_pos = positions.get(candidate, 0.5)

        # Sort all candidates by ideological distance to this voter's first choice
        ranking = sorted(
            candidate_names,
            key=lambda c: (
                -1.0 if c == candidate          # first choice always first
                else abs(positions.get(c, 0.5) - c_pos)
            ),
        )
        for _ in range(n):
            rankings.append(ranking)

    return rankings


def _ranking_to_score_dict(ranking: List[str]) -> Dict[str, float]:
    """Map a ranking to normalised 0-5 scores (1st = 5, last = 0)."""
    n = len(ranking)
    if n <= 1:
        return {c: 5.0 for c in ranking}
    return {
        c: round(5.0 * (n - 1 - i) / (n - 1), 2)
        for i, c in enumerate(ranking)
    }


# ── Analysis ───────────────────────────────────────────────────────────────

def analyze_real_election(
    election_name: str,
    num_voters: int = 1000,
) -> Dict[str, Any]:
    """
    Run every available voting method on a synthetic population derived
    from a real election's first-round results.

    Returns the winner per method, plus a list of divergences from the
    real plurality outcome.
    """
    if election_name not in REAL_ELECTIONS:
        raise ValueError(f"Unknown election: {election_name!r}. "
                         f"Available: {list(REAL_ELECTIONS)}")

    election_data = REAL_ELECTIONS[election_name]
    first_round   = election_data["results"]["first_round"]
    n_candidates  = len(first_round)

    rankings   = convert_to_rankings(election_name, election_data, num_voters)
    all_scores = [_ranking_to_score_dict(r) for r in rankings]

    # Real plurality winner (most first-round votes)
    plurality_winner = max(first_round, key=first_round.get)

    # Ranked methods
    ranked_methods: Dict[str, Any] = {
        "plurality":        get_plurality_winner,
        "two_round":        get_two_round_winner,
        "borda":            get_borda_winner,
        "approval":         get_approval_winner,
        "irv":              get_irv_winner,
        "coombs":           get_coombs_winner,
        "bucklin":          get_bucklin_winner,
        "minimax":          get_minimax_winner,
        "schulze":          get_schulze_winner,
        "condorcet":        get_condorcet_winner,
        "positional_score": get_positional_score_winner,
    }
    # Kemeny-Young is O(n!) — skip for elections with > 5 candidates
    if n_candidates <= 5:
        from .simulation_ranked_utils import get_kemeny_young_winner
        ranked_methods["kemeny_young"] = get_kemeny_young_winner

    score_methods: Dict[str, Any] = {
        "simple_score":      get_simple_score_winner,
        "star_voting":       get_star_voting_winner,
        "median_voting":     get_median_voting_winner,
        "mean_median_hybrid": get_mean_median_hybrid_winner,
        "variance_based":    get_variance_based_winner,
    }

    winners: Dict[str, Optional[str]] = {}

    for name, fn in ranked_methods.items():
        result = fn(rankings)
        winners[name] = result

    for name, fn in score_methods.items():
        result = fn(all_scores)
        if isinstance(result, dict):
            winners[name] = result.get("winner")
        else:
            winners[name] = result

    divergences = [
        {
            "method":                  method,
            "winner":                  winner,
            "differs_from_plurality":  winner != plurality_winner,
        }
        for method, winner in sorted(winners.items())
    ]

    # Summary counts
    n_different = sum(1 for d in divergences if d["differs_from_plurality"] and d["winner"])
    n_total     = sum(1 for d in divergences if d["winner"] is not None)

    # First-round percentages for display
    total_votes = sum(first_round.values())
    first_round_pct = {
        c: round(100.0 * v / total_votes, 2) for c, v in first_round.items()
    }

    return {
        "election": {
            "key":         election_name,
            "name":        election_data["name"],
            "year":        election_data["year"],
            "country":     election_data["country"],
            "description": election_data["description"],
            "source":      election_data["source"],
            "candidates":  election_data["candidates"],
        },
        "plurality_winner":    plurality_winner,
        "first_round_results": first_round_pct,
        "methods":             winners,
        "divergences":         divergences,
        "summary": {
            "methods_with_different_winner": n_different,
            "total_methods_with_winner":     n_total,
        },
    }


def list_elections() -> List[Dict]:
    """Return summary metadata for all available elections."""
    return [
        {
            "key":     key,
            "name":    data["name"],
            "year":    data["year"],
            "country": data["country"],
        }
        for key, data in REAL_ELECTIONS.items()
    ]
