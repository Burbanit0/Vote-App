"""
simulation_advanced.py — Advanced analysis endpoints.

Serves SimulationComparePage (/simulation/compare) tabs:
Bandwagon, Monte Carlo, Multi-winner, Real Elections.

All endpoints use the spatial utility pipeline.

Phase 4.5.a.8: the request logic lives in framework-agnostic `_*_worker`
functions (return `(body, status)`) so the FastAPI sibling
(api/routes/simulations.py) can reuse it. The Flask routes below are thin
delegates kept as a rollback target.
"""
import math
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple




from api.domain.election._helpers import modal_keys
from api.engine.utils.demographic_data import unseeded_rng_pair
from api.engine.utils.simulation_metrics import compare_all_methods_mc
from api.engine.utils.error_handling import log_and_error_response
from api.domain.simulations.helpers import (
    _parse_candidate_configs, _build_population,
)
from api.engine.utils.logger import get_logger

log = get_logger(__name__)



# ── /simulations/bandwagon ──────────────────────────────────────────────────





# ── /simulations/monte-carlo ────────────────────────────────────────────────

def _monte_carlo_worker(data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """
    Run compare_all_methods_mc() N times in parallel and aggregate
    statistical distributions for each voting method.

    (Synchronous aggregation variant — distinct from the Socket.IO streaming
    Monte Carlo migrated in Phase 4.4.)
    """
    num_runs       = int(data.get("num_runs", 100))
    num_voters     = int(data.get("num_voters", 150))
    ideology_dist  = data.get("ideology_distribution", "random")
    raw_candidates = data.get("candidates", ["Alice", "Bob", "Charlie"])

    candidate_configs = _parse_candidate_configs(raw_candidates)
    if len(candidate_configs) < 2:
        return {"error": "At least 2 candidates required"}, 400

    def _single_run(_: Any) -> Dict[str, Any]:
        # Fresh, unseeded, per-call local RNG pair — this Monte Carlo run has
        # no reproducibility contract, but each call executes in its own
        # ThreadPoolExecutor worker thread, so drawing from the shared
        # random/np.random singletons would race every other concurrent run
        # (in this pool and any other seeded/unseeded caller in the process).
        rng, np_rng = unseeded_rng_pair()
        voters, candidates, issues = _build_population(
            candidate_configs, num_voters, ideology_dist, rng=rng, np_rng=np_rng
        )
        return compare_all_methods_mc(voters, candidates, issues)

    try:
        with ThreadPoolExecutor(max_workers=min(4, num_runs)) as executor:
            futures = [executor.submit(_single_run, i) for i in range(num_runs)]
            run_results = [f.result() for f in as_completed(futures)]

        method_names = list(run_results[0]["methods"].keys())
        n_candidates = len(candidate_configs)

        winner_counts: Dict[str, Any]    = {m: defaultdict(int) for m in method_names}
        regrets:       Dict[str, List[float]] = {m: [] for m in method_names}
        satisfactions: Dict[str, List[float]] = {m: [] for m in method_names}
        condorcet_hits = {m: 0 for m in method_names}
        condorcet_runs = {m: 0 for m in method_names}
        agreement_counts: Dict[str, int] = defaultdict(int)
        agreement_total:  Dict[str, int] = defaultdict(int)
        condorcet_exists = 0

        for run in run_results:
            if run["condorcet_winner"]:
                condorcet_exists += 1
            run_winners = {}
            for m, d in run["methods"].items():
                w = d.get("winner")
                run_winners[m] = w
                if w:
                    winner_counts[m][w] += 1
                r = d.get("bayesian_regret")
                if r is not None:
                    regrets[m].append(r)
                s = d.get("majority_satisfaction")
                if s is not None:
                    satisfactions[m].append(s)
                cc = d.get("condorcet_consistent")
                if cc is not None:
                    condorcet_runs[m] += 1
                    if cc:
                        condorcet_hits[m] += 1
            for i, m1 in enumerate(method_names):
                for m2 in method_names[i + 1:]:
                    key = f"{m1}|{m2}"
                    agreement_total[key] += 1
                    if run_winners.get(m1) and run_winners[m1] == run_winners.get(m2):
                        agreement_counts[key] += 1

        def _ci95(values: List[float]) -> List[Optional[float]]:
            if len(values) < 2:
                return [None, None]
            mu = sum(values) / len(values)
            var = sum((v - mu) ** 2 for v in values) / (len(values) - 1)
            margin = 1.96 * math.sqrt(var) / math.sqrt(len(values))
            return [round(mu - margin, 6), round(mu + margin, 6)]

        def _entropy(dist: Dict[str, float], n_cand: int) -> float:
            e = -sum(p * math.log2(p) for p in dist.values() if p > 0)
            max_e = math.log2(n_cand) if n_cand > 1 else 1.0
            return round(e / max_e if max_e > 0 else 0.0, 4)

        methods_stats = {}
        for m in method_names:
            dist = {c: round(cnt / num_runs, 4) for c, cnt in winner_counts[m].items()}
            # Every candidate tied for most runs won. `max()` returned whichever
            # was counted first, and `run_results` comes off `as_completed`, so on
            # a tie two identical requests could disagree. Empty only when no run
            # produced a winner.
            most_common: List[str] = modal_keys(winner_counts[m])
            regs = regrets[m]
            sats = satisfactions[m]
            reg_mean = round(sum(regs) / len(regs), 6) if regs else None
            reg_std = round(
                math.sqrt(sum((v - reg_mean) ** 2 for v in regs) / max(1, len(regs) - 1)), 6
            ) if regs and len(regs) > 1 and reg_mean is not None else None
            methods_stats[m] = {
                "winner_distribution":         dist,
                "most_common_winner":          most_common,
                "winner_stability":            _entropy(dist, n_candidates),
                "bayesian_regret_mean":        reg_mean,
                "bayesian_regret_std":         reg_std,
                "bayesian_regret_ci_95":       _ci95(regs),
                "majority_satisfaction_mean":  round(sum(sats) / len(sats), 4) if sats else None,
                "majority_satisfaction_ci_95": _ci95(sats),
                "condorcet_compliance_rate":   (
                    round(condorcet_hits[m] / condorcet_runs[m], 4)
                    if condorcet_runs[m] > 0 else None
                ),
            }

        inter_agreement = {
            key: round(agreement_counts[key] / agreement_total[key], 4)
            for key in agreement_total if agreement_total[key] > 0
        }

        return {
            "num_runs":                     num_runs,
            "num_voters_per_run":           num_voters,
            "config": {
                "candidates":            [cfg["name"] for cfg in candidate_configs],
                "ideology_distribution": ideology_dist,
            },
            "methods":                      methods_stats,
            "condorcet_winner_exists_rate": round(condorcet_exists / num_runs, 4),
            "inter_method_agreement":       inter_agreement,
        }, 200

    except Exception as e:
        return log_and_error_response(log, "simulation.monte_carlo.failed", {"error": str(e)})




# ── /simulations/multiwinner ────────────────────────────────────────────────





# ── /simulations/real-elections (GET) ───────────────────────────────────────





# ── /simulations/blank-history (GET) ─────────────────────────────────────────





# ── /simulations/real-election (POST) ────────────────────────────────────────





# ── /simulations/constitutional-scenario ──────────────────────────────────



# ── /simulations/blank-contagion ─────────────────────────────────────────────



