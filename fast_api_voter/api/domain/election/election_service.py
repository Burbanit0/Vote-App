"""
election_service.py — pure orchestration of the unified election simulation.

This is the business logic that used to live inside _simulate_worker() in
app/routes/election/__init__.py. Extracting it as a service:

  - Decouples the simulation from Flask (no `request`, no `jsonify`, no
    app context) so it's directly testable, runnable from a CLI / batch
    job, and reusable from other entry points (WebSocket events, future
    REST v2, etc.).
  - Makes the route file a thin HTTP adapter: parse JSON → call service
    → format response. The route owns cross-cutting concerns
    (rate-limiting, tpool dispatch, caching); the service owns the
    simulation logic.

Contract:
    ElectionService.simulate(data: dict) -> tuple[dict, int]
        data:   the parsed request body (or any dict with the same shape)
        return: (response_body, http_status)

Errors that are user-facing (e.g. "At least 2 candidates required") return
a 400 status with an "error" key. Internal exceptions propagate to the
caller — the route's @heavy_endpoint wrapper turns them into 500s.
"""
from __future__ import annotations

import random as _random
from typing import Any, Dict, Optional

import numpy as _np

from api.engine.constants import DEFAULT_ISSUES
from api.domain.election._helpers import (
    SINGLE_WINNER_CAP,
    build_candidate_from_xy,
    inter_method_agreement,
)
from api.engine.utils.blank_contagion import simulate_blank_contagion
from api.engine.utils.blank_vote_rules import BlankVoteRule, apply_blank_rule
from api.engine.utils.campaign_dynamics import simulate_campaign
from api.engine.utils.information_model import apply_information_asymmetry
from api.engine.utils.simulation_metrics import compare_all_methods
from api.engine.utils.simulation_voting_utils import calculate_utility, create_voter


class ElectionService:
    """Pure orchestration of the unified election simulation."""

    @staticmethod
    def simulate(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
        """Run the full election pipeline:

          1. Parse params + clamp ranges
          2. Seed PRNGs
          3. Build candidates (from explicit x/y) + voters (from ideology distribution)
          4. Compute true utilities (voter ↔ candidate)
          5. Apply campaign dynamics (optional)
          6. Apply blank-vote contagion (optional)
          7. Apply information asymmetry (optional)
          8. Run all voting methods
          9. Apply blank-vote constitutional rule (optional)
         10. Build voter snapshot + return result
        """

        # ── Parse params ──────────────────────────────────────────────────
        num_voters   = max(10, min(1000, int(data.get("num_voters",  300))))
        ideology     = str(data.get("ideology",   "random"))
        seed         = int(data.get("seed",        42))
        cand_specs   = data.get("candidates", [
            {"name": "Alice", "x": -0.5, "y": -0.2},
            {"name": "Bob",   "x":  0.5, "y":  0.2},
            {"name": "Carol", "x":  0.0, "y":  0.3},
        ])[:SINGLE_WINNER_CAP]

        blank_cfg       = data.get("blank_vote", {}) or {}
        blank_enabled   = bool(blank_cfg.get("enabled", False))
        blank_rule_str  = str(blank_cfg.get("rule", "symbolic"))
        contagion_cfg   = blank_cfg.get("contagion", {}) or {}
        contagion_on    = bool(contagion_cfg.get("enabled", False))

        info_cfg        = data.get("information_model", {}) or {}
        info_enabled    = bool(info_cfg.get("enabled", False))

        campaign_cfg    = data.get("campaign", {}) or {}
        campaign_on     = bool(campaign_cfg.get("enabled", False))
        num_days        = max(7, min(60, int(campaign_cfg.get("num_days",       30))))
        polling_effect  = max(0.0, min(1.0, float(campaign_cfg.get("polling_effect", 0.3))))

        if len(cand_specs) < 2:
            return {"error": "At least 2 candidates required"}, 400

        # ── Seed both PRNGs ───────────────────────────────────────────────
        _random.seed(seed)
        _np.random.seed(seed)

        issues     = DEFAULT_ISSUES
        cand_names = [str(s.get("name", f"C{i}")) for i, s in enumerate(cand_specs)]

        # ── 1. Build candidates ───────────────────────────────────────────
        candidates = [
            build_candidate_from_xy(
                i,
                cand_names[i],
                max(-1.0, min(1.0, float(s.get("x", 0.0)))),
                max(-1.0, min(1.0, float(s.get("y", 0.0)))),
                issues,
            )
            for i, s in enumerate(cand_specs)
        ]

        # ── 2. Build electorate ───────────────────────────────────────────
        voters = [
            create_voter(issues, i, ideology_distribution=ideology)
            for i in range(num_voters)
        ]

        # ── 3. Compute true utilities ─────────────────────────────────────
        true_utilities: Dict[Any, Dict[str, float]] = {
            v["id"]: {
                c["name"]: calculate_utility(v, c, issues)["utility"]
                for c in candidates
            }
            for v in voters
        }

        # ── 4. Campaign dynamics (optional) ───────────────────────────────
        campaign_trajectory: Optional[Dict[str, Any]] = None
        if campaign_on:
            camp = simulate_campaign(
                num_candidates=len(candidates),
                num_voters=num_voters,
                num_days=num_days,
                events=[],
                seed=seed,
            )
            campaign_trajectory = camp
            camp_cands = camp.get("candidates", [])
            final_shares: Dict[str, float] = {}
            for camp_idx, camp_name in enumerate(camp_cands):
                if camp_idx < len(cand_names):
                    our_name = cand_names[camp_idx]
                    shares_list = camp.get("daily_scores", {}).get(camp_name, [50.0])
                    final_shares[our_name] = shares_list[-1] / 100.0

            for v in voters:
                for c_name in cand_names:
                    share = final_shares.get(c_name, 1.0 / len(cand_names))
                    u     = true_utilities[v["id"]][c_name]
                    blended = u * (1.0 - polling_effect * 0.4) + share * (polling_effect * 0.4)
                    true_utilities[v["id"]][c_name] = max(0.0, min(1.0, blended))

        # ── 5. Blank-vote contagion (optional) ────────────────────────────
        if contagion_on and blank_enabled:
            beta    = max(0.0, min(1.0, float(contagion_cfg.get("beta",  0.15))))
            gamma   = max(0.0, min(1.0, float(contagion_cfg.get("gamma", 0.10))))
            net_map = {"random": "random", "watts_strogatz": "small-world", "block": "clustered"}
            net     = net_map.get(str(contagion_cfg.get("network", "random")), "random")

            contagion_result = simulate_blank_contagion(
                num_voters=num_voters,
                initial_blank_rate=0.05,
                contagion_rate=beta,
                recovery_rate=gamma,
                num_rounds=10,
                network_type=net,
                seed=seed,
            )
            final_blank_rate = contagion_result.get("final_blank_rate", 0.05)
            threshold_reduction = final_blank_rate * 0.4
            for v in voters:
                v["blank_threshold"] = max(0.05, v["blank_threshold"] - threshold_reduction)

        # ── 6. Information model (optional) ───────────────────────────────
        effective_utilities = true_utilities
        if info_enabled:
            raw_bias   = info_cfg.get("media_bias", {}) or {}
            media_bias = {
                str(i): float(raw_bias.get(c["name"], 0.0))
                for i, c in enumerate(candidates)
            }
            vseg = info_cfg.get("voter_segments") or {}
            voter_segments = {
                "low_info":    float(vseg.get("low_info",    0.3)),
                "medium_info": float(vseg.get("medium_info", 0.5)),
                "high_info":   float(vseg.get("high_info",   0.2)),
            }
            true_list = [
                [true_utilities[v["id"]][c["name"]] for c in candidates]
                for v in voters
            ]
            perceived_list = apply_information_asymmetry(
                true_list, media_bias, voter_segments, seed=seed
            )
            effective_utilities = {
                v["id"]: {c["name"]: perceived_list[idx][j] for j, c in enumerate(candidates)}
                for idx, v in enumerate(voters)
            }

        # ── 7. Run all voting methods ─────────────────────────────────────
        result = compare_all_methods(
            voters,
            candidates,
            issues,
            blank_vote=blank_enabled,
            override_utilities=effective_utilities,
        )

        condorcet_winner = result.get("condorcet_winner")
        blank_pct        = result.get("blank_pct") or 0.0
        methods_data     = result.get("methods", {})

        # ── 8. Apply constitutional blank-vote rule ───────────────────────
        try:
            blank_rule = BlankVoteRule(blank_rule_str)
        except ValueError:
            blank_rule = BlankVoteRule.SYMBOLIC

        methods_out: Dict[str, Any] = {}
        for method_name, md in methods_data.items():
            winner = md.get("winner")
            entry: Dict[str, Any] = {
                "winner":               winner,
                "bayesian_regret":      md.get("bayesian_regret"),
                "majority_satisfaction": md.get("majority_satisfaction"),
                "condorcet_consistent": md.get("condorcet_consistent"),
            }
            if blank_enabled:
                rule_result = apply_blank_rule(
                    winner=winner, blank_pct=blank_pct, rule=blank_rule
                )
                entry["winner_with_blank"]  = rule_result.get("winner")
                entry["blank_triggered"]    = rule_result.get("blank_triggered", False)
            methods_out[method_name] = entry

        # ── 9. Build voter snapshot for ideology map ──────────────────────
        voters_snapshot = [
            {
                "id": v["id"],
                "x":  round(2.0 * v["issue_positions"].get("economy",       0.5) - 1.0, 3),
                "y":  round(2.0 * v["issue_positions"].get("social_welfare", 0.5) - 1.0, 3),
                "blank_threshold_final": round(v["blank_threshold"], 4),
            }
            for v in voters
        ]

        candidates_out = [
            {
                "name":  c["name"],
                "x":     round(2.0 * c["ideology_position"] - 1.0, 3),
                "y":     round(2.0 * c["policies"].get("social_welfare", 0.5) - 1.0, 3),
                "party": c["party"],
            }
            for c in candidates
        ]

        return {
            "config":                 data,
            "voters_snapshot":        voters_snapshot,
            "candidates":             candidates_out,
            "methods":                methods_out,
            "condorcet_winner":       condorcet_winner,
            "blank_rate":             round(blank_pct, 4),
            "campaign_trajectory":    campaign_trajectory,
            "inter_method_agreement": inter_method_agreement(methods_out),
            "condorcet_exists":       condorcet_winner is not None,
        }, 200
