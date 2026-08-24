from typing import Any

import numpy as np

######################################################################
#
# Simulation d'une population sur une grille de repartition politique
#
######################################################################


def assign_voters_to_candidates(voters: Any, candidates: Any) -> list[Any]:
    assignements = []
    for voter in voters:
        distances = [
            np.linalg.norm(np.array(voter) - np.array(candidate))
            for candidate in candidates
        ]

        closest_candidate_index = np.argmin(distances)

        assignements.append(closest_candidate_index)

    return assignements
