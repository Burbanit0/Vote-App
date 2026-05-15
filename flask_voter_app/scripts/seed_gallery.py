#!/usr/bin/env python
"""
seed_gallery.py — Pre-populate the public scenario gallery.

Run from the flask_voter_app directory:
    FLASK_ENV=testing python scripts/seed_gallery.py
    python scripts/seed_gallery.py   # uses default config
"""
from __future__ import annotations

import os
import sys

# Allow running from any directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SCENARIOS = [
    # ── 1. Le paradoxe de Condorcet ──────────────────────────────────────────
    {
        "title":       "Le paradoxe de Condorcet",
        "description": (
            "Trois candidats où les préférences collectives forment un cycle : "
            "Alice bat Bob, Bob bat Carol, mais Carol bat Alice. "
            "Aucun vainqueur de Condorcet n'existe — toute méthode doit choisir "
            "arbitrairement entre des candidats qui ont tous perdu un duel direct. "
            "Un exemple fondamental de la difficulté du choix social."
        ),
        "params": {
            "candidates":            ["Alice", "Bob", "Carol"],
            "num_voters":            300,
            "ideology_distribution": "polarized",
            "num_simulations":       10,
        },
        "results_summary": {
            "condorcet_winner": None,
            "cycle":            ["Alice>Bob", "Bob>Carol", "Carol>Alice"],
            "winners": {
                "plurality":  "Alice",
                "borda":      "Bob",
                "schulze":    "Alice",
                "irv":        "Carol",
                "approval":   "Alice",
            },
            "methods_agree": False,
            "note": "Aucun vainqueur de Condorcet — cycle complet.",
        },
        "tags":        ["paradoxe", "condorcet", "cycle", "borda", "irv"],
        "is_featured": True,
    },

    # ── 2. Vote blanc décisif ─────────────────────────────────────────────────
    {
        "title":       "Vote blanc décisif",
        "description": (
            "Un électorat très polarisé où 31% des électeurs rejettent tous les candidats. "
            "Sous la règle THRESHOLD_30 (en vigueur en Colombie), l'élection est annulée "
            "et de nouvelles candidatures sont requises. "
            "Illustre comment le vote blanc peut forcer un renouvellement de l'offre politique."
        ),
        "params": {
            "candidates":   ["GauchePop", "CentreModéré", "DroitePop"],
            "num_voters":   500,
            "blank_rule":   "threshold_30",
            "blank_vote":   True,
            "ideology_distribution": "polarized",
        },
        "results_summary": {
            "condorcet_winner": "GauchePop",
            "blank_pct":        0.31,
            "election_invalid": True,
            "winners": {
                "plurality":  "DroitePop",
                "borda":      "CentreModéré",
                "schulze":    "GauchePop",
            },
            "blank_rule_applied": "threshold_30",
            "note": "Le vote blanc dépasse 30% — élection invalidée.",
        },
        "tags":        ["vote-blanc", "threshold_30", "crise-constitutionnelle", "polarisation"],
        "is_featured": True,
    },

    # ── 3. L'effet du vote utile ──────────────────────────────────────────────
    {
        "title":       "L'effet du vote utile",
        "description": (
            "Avec 3 candidats (Alice, Bob, Carol), Carol est classée 3e en intentions "
            "de vote mais est en réalité la préférée de la majorité. "
            "La pluralité élit Alice grâce à l'effet spoiler (Carol divise la gauche), "
            "tandis qu'IRV transfère les votes de Carol et inverse le résultat. "
            "Exemple classique du paradoxe du vote utile."
        ),
        "params": {
            "candidates":            ["Alice", "Bob", "Carol"],
            "num_voters":            400,
            "ideology_distribution": "left_skewed",
        },
        "results_summary": {
            "condorcet_winner": "Carol",
            "winners": {
                "plurality": "Alice",
                "borda":     "Carol",
                "irv":       "Carol",
                "schulze":   "Carol",
                "approval":  "Carol",
            },
            "methods_agree": False,
            "note": "Pluralité élit Alice ; IRV, Borda, Schulze élisent Carol.",
        },
        "tags":        ["vote-utile", "irv", "plurality", "effet-spoiler", "condorcet"],
        "is_featured": True,
    },

    # ── 4. Borda vs Schulze ───────────────────────────────────────────────────
    {
        "title":       "Borda contre Schulze",
        "description": (
            "Une élection à 4 candidats où Borda et Schulze élisent des vainqueurs différents. "
            "Borda récompense le candidat avec la meilleure position moyenne dans les classements, "
            "tandis que Schulze calcule les chaînes de victoires pairwise les plus solides. "
            "Illustre pourquoi deux méthodes 'raisonnables' peuvent produire des résultats opposés."
        ),
        "params": {
            "candidates":            ["Alice", "Bob", "Carol", "Dave"],
            "num_voters":            600,
            "ideology_distribution": "random",
        },
        "results_summary": {
            "condorcet_winner": "Bob",
            "winners": {
                "plurality":  "Alice",
                "borda":      "Alice",
                "schulze":    "Bob",
                "irv":        "Alice",
                "approval":   "Bob",
                "condorcet":  "Bob",
            },
            "methods_agree": False,
            "note": "Borda élit Alice ; Schulze et Condorcet élisent Bob.",
        },
        "tags":        ["borda", "schulze", "paradoxe", "condorcet", "4-candidats"],
        "is_featured": True,
    },

    # ── 5. Élection fragmentée ────────────────────────────────────────────────
    {
        "title":       "Élection fragmentée",
        "description": (
            "Six candidats se partagent l'électorat de manière presque égale, "
            "aucun ne dépassant 25% des voix. "
            "La pluralité élit le candidat avec seulement 20% — une minorité. "
            "Les méthodes de classement (IRV, Schulze) agrègent les préférences "
            "et identifient un consensus différent. Similaire aux élections françaises "
            "de 2002 avec 16 candidats."
        ),
        "params": {
            "candidates":            ["Alice", "Bob", "Carol", "Dave", "Eve", "Frank"],
            "num_voters":            800,
            "ideology_distribution": "random",
        },
        "results_summary": {
            "condorcet_winner": "Carol",
            "winners": {
                "plurality":  "Alice",
                "borda":      "Carol",
                "irv":        "Dave",
                "schulze":    "Carol",
                "approval":   "Carol",
            },
            "methods_agree": False,
            "note": "6 candidats — pluralité élit Alice avec ~20% ; Carol gagne sous Borda/Schulze.",
        },
        "tags":        ["fragmentation", "6-candidats", "pluralité", "consensus", "représentation"],
        "is_featured": True,
    },

    # ── 6. STAR vs Score ──────────────────────────────────────────────────────
    {
        "title":       "STAR contre Score simple",
        "description": (
            "STAR (Score Then Automatic Runoff) et le score simple élisent des candidats différents. "
            "Le score moyen favorise Alice (largement appréciée mais pas la préférée), "
            "tandis que le second tour automatique de STAR révèle que Bob est préféré "
            "en face à face par la majorité. "
            "Illustre l'importance de la phase de runoff pour résister à la polarisation stratégique."
        ),
        "params": {
            "candidates":            ["Alice", "Bob", "Carol"],
            "num_voters":            350,
            "ideology_distribution": "centrist",
        },
        "results_summary": {
            "condorcet_winner": "Bob",
            "winners": {
                "simple_score":  "Alice",
                "star_voting":   "Bob",
                "median_voting": "Bob",
                "plurality":     "Alice",
                "borda":         "Bob",
            },
            "methods_agree": False,
            "note": "Score simple élit Alice ; STAR, médiane et Borda élisent Bob.",
        },
        "tags":        ["star", "score", "second-tour", "runoff", "intensité"],
        "is_featured": True,
    },
]


def seed(app=None, clear: bool = True) -> int:
    """
    Insert the 6 demonstration scenarios into the database.

    Parameters
    ----------
    app : Flask app instance — created automatically if None.
    clear : If True, removes existing gallery scenarios first.

    Returns the number of scenarios inserted.
    """
    if app is None:
        from app import create_app
        app = create_app()

    from app import db
    from app.models import GalleryScenario

    with app.app_context():
        if clear:
            GalleryScenario.query.delete()
            db.session.commit()

        inserted = 0
        for data in SCENARIOS:
            s = GalleryScenario(
                title=data["title"],
                description=data["description"],
                params=data["params"],
                results_summary=data["results_summary"],
                tags=data["tags"],
                is_featured=data.get("is_featured", False),
            )
            db.session.add(s)
            inserted += 1

        db.session.commit()
        return inserted


if __name__ == "__main__":
    n = seed()
    print(f"✓ Inserted {n} gallery scenarios.")
