"""
app.utils — shim package (Phase 4.5.b.3).

The compute engine moved to api_v2/engine/utils. The relocated submodules are
re-aliased here under their old `app.utils.*` paths so the still-living Flask app
(and its tests) keep importing them unchanged until app/ is deleted in the final
teardown. The four Flask-coupled helpers below remain real files in this package:
auth_utils, cache, decorators, response_utils.
"""
import importlib
import sys

_RELOCATED = [
    "arrow_criteria", "blank_contagion", "blank_vote_rules", "campaign_dynamics",
    "demographic_data", "gibbard_satterthwaite", "information_model", "logger",
    "quadratic_voting", "real_election_data", "simul", "simulation_metrics",
    "simulation_multiwinner_utils", "simulation_ranked_utils",
    "simulation_score_utils", "simulation_voting_utils", "utils",
]

for _name in _RELOCATED:
    sys.modules[f"{__name__}.{_name}"] = importlib.import_module(
        f"api_v2.engine.utils.{_name}"
    )
