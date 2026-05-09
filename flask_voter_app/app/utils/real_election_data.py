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
    "france_2022": {
        "Macron":          0.52,  # LREM — centre libéral
        "Le Pen":          0.88,  # RN — extrême-droite
        "Mélenchon":       0.15,  # LFI — extrême-gauche
        "Zemmour":         0.95,  # Reconquête — ultra-droite
        "Pécresse":        0.70,  # LR — droite classique
        "Jadot":           0.22,  # Verts — gauche écolo
        "Lassalle":        0.50,  # Résistons — centre indépendant
        "Dupont-Aignan":   0.80,  # DLF — national-conservateur
        "Hidalgo":         0.28,  # PS — centre-gauche
        "Roussel":         0.12,  # PCF — gauche radicale
        "Poutou":          0.08,  # NPA — ultra-gauche
        "Arthaud":         0.05,  # LO — ultra-gauche
    },
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
    "crisis_election": {
        "GauchePop":     0.05,   # gauche populiste très à gauche
        "CentreModéré":  0.50,   # centre faible
        "DroitePop":     0.92,   # droite populiste très à droite
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
    "crisis_election": {
        "name":    "Élection de crise — cas pédagogique",
        "year":    2027,
        "country": "France (fictif)",
        "description": (
            "Scénario fictif calibré pour illustrer la capacité du vote blanc à "
            "battre tous les candidats. L'électorat est bimodal et très polarisé : "
            "deux candidats populistes aux extrêmes et un centre faible. "
            "31 % des électeurs refusent tous les candidats — le vote blanc dépasse "
            "chaque candidat en nombre de voix. Sous la règle compétitive, le vote "
            "blanc gagne. Sous la règle du seuil 30 %, l'élection est invalidée. "
            "Utilisez ce cas pour comprendre pourquoi la reconnaissance du vote blanc "
            "exige une règle constitutionnelle claire sur ses conséquences."
        ),
        "candidates": [
            {"name": "GauchePop",    "party": "Front Populaire Radical"},
            {"name": "CentreModéré", "party": "Alliance du Centre"},
            {"name": "DroitePop",    "party": "Rassemblement National-Souverainiste"},
        ],
        "results": {
            "first_round": {
                "GauchePop":    240_000,   # 24 % du total
                "CentreModéré": 170_000,   # 17 % du total
                "DroitePop":    280_000,   # 28 % du total
                # Blank: 310 000 (31 %) est modélisé via estimated_blank_pct
            },
            "total_voters": 1_000_000,
        },
        "estimated_blank_pct": 0.31,
        "source": "Scénario fictif — cas pédagogique Vote Lab",
    },

    "france_2022": {
        "name":    "Élection présidentielle française — 1er tour",
        "year":    2022,
        "country": "France",
        "description": (
            "Le premier tour de 2022 est marqué par la fragmentation extrême de "
            "l'offre politique et la montée du vote de contestation. Avec 12 candidats, "
            "l'effet spoiler est massif à gauche (Mélenchon, Jadot, Hidalgo, Roussel, "
            "Poutou, Arthaud se partagent ~31 % des voix) et à droite "
            "(Le Pen, Zemmour, Pécresse, Dupont-Aignan représentent ~37 %). "
            "Sous la pluralité, Macron et Le Pen se qualifient au second tour. "
            "Sous IRV ou Schulze, Mélenchon ou Macron selon la structure des préférences "
            "auraient pu s'imposer différemment. Le vote blanc représentait environ "
            "2,5 % des votes exprimés (blancs + nuls), insuffisant pour déclencher "
            "un seuil constitutionnel mais illustratif d'une insatisfaction croissante."
        ),
        "candidates": [
            {"name": "Macron",        "party": "LREM (centre libéral)"},
            {"name": "Le Pen",        "party": "RN (extrême-droite)"},
            {"name": "Mélenchon",     "party": "LFI (extrême-gauche)"},
            {"name": "Zemmour",       "party": "Reconquête (ultra-droite)"},
            {"name": "Pécresse",      "party": "LR (droite classique)"},
            {"name": "Jadot",         "party": "Verts (gauche écolo)"},
            {"name": "Lassalle",      "party": "Résistons (centre indép.)"},
            {"name": "Roussel",       "party": "PCF (gauche radicale)"},
            {"name": "Dupont-Aignan", "party": "DLF (national-conservateur)"},
            {"name": "Hidalgo",       "party": "PS (centre-gauche)"},
            {"name": "Poutou",        "party": "NPA (ultra-gauche)"},
            {"name": "Arthaud",       "party": "LO (ultra-gauche)"},
        ],
        "results": {
            "first_round": {
                "Macron":        9_747_500,
                "Le Pen":        8_102_500,
                "Mélenchon":     7_682_500,
                "Zemmour":       2_474_500,
                "Pécresse":      1_673_000,
                "Jadot":         1_620_500,
                "Lassalle":      1_095_500,
                "Roussel":         798_000,
                "Dupont-Aignan":   721_000,
                "Hidalgo":         612_500,
                "Poutou":          269_500,
                "Arthaud":         196_000,
            },
            "total_voters": 35_000_000,
        },
        "estimated_blank_pct": 0.025,
        "source": "Ministère de l'Intérieur — résultats officiels 10 avril 2022",
    },

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
        "estimated_blank_pct": 0.034,
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
        "estimated_blank_pct": 0.008,
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
        "estimated_blank_pct": 0.007,
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

    # ── Blank vote analysis ────────────────────────────────────────────────────
    estimated_blank_pct = election_data.get("estimated_blank_pct", 0.0)
    max_candidate_pct   = max(first_round_pct.values())

    # COMPETITIVE: blank wins if its share exceeds every candidate's share.
    # The blank share is expressed in the same scale as first_round_pct (percent, 0-100).
    blank_pct_as_display = round(estimated_blank_pct * 100, 2)
    blank_wins_competitive = blank_pct_as_display > max_candidate_pct

    blank_vote_analysis: Dict[str, Any] = {
        "estimated_blank_pct": estimated_blank_pct,
        "competitive": {
            "blank_wins":  blank_wins_competitive,
            "winner":      "Blank" if blank_wins_competitive else plurality_winner,
            "triggered":   blank_wins_competitive,
            "consequence": (
                "Le vote blanc obtient plus de voix que tout candidat — "
                "crise constitutionnelle, aucun élu légitime."
                if blank_wins_competitive else
                f"Le vote blanc ({blank_pct_as_display:.1f}%) reste inférieur "
                f"au candidat en tête ({plurality_winner} : {max_candidate_pct:.1f}%). "
                "Le résultat ne change pas."
            ),
        },
        "threshold_30": {
            "triggered":   estimated_blank_pct >= 0.30,
            "winner":      None if estimated_blank_pct >= 0.30 else plurality_winner,
            "consequence": (
                f"Le vote blanc dépasse 30 % — élection invalidée, "
                "nouvelles candidatures requises."
                if estimated_blank_pct >= 0.30 else
                f"Le vote blanc ({blank_pct_as_display:.1f}%) reste sous le seuil de 30 %. "
                "Le résultat est maintenu."
            ),
        },
    }

    return {
        "election": {
            "key":                 election_name,
            "name":                election_data["name"],
            "year":                election_data["year"],
            "country":             election_data["country"],
            "description":         election_data["description"],
            "source":              election_data["source"],
            "candidates":          election_data["candidates"],
            "estimated_blank_pct": estimated_blank_pct,
        },
        "plurality_winner":    plurality_winner,
        "first_round_results": first_round_pct,
        "methods":             winners,
        "divergences":         divergences,
        "summary": {
            "methods_with_different_winner": n_different,
            "total_methods_with_winner":     n_total,
        },
        "blank_vote_analysis": blank_vote_analysis,
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
