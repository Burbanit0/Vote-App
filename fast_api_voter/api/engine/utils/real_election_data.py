"""
real_election_data.py
Real historical election data, served by the public /api/v1/real-elections list.
"""
from typing import Dict, Any


# ── Real election data ─────────────────────────────────────────────────────

REAL_ELECTIONS: Dict[str, Any] = {
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
