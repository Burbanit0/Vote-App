"""
blank_contagion.py — SIS epidemic model of blank-vote contagion.

The blank vote is modelled as an "infection" that spreads across a social
network of voters:

    S (normal voter) → I (blank voter)  with rate β per infected contact
    I (blank voter)  → S (normal voter) with rate γ per round

Key metric — Basic Reproduction Number:
    R₀ = β / γ
    R₀ < 1 : epidemic dies out
    R₀ > 1 : epidemic reaches a non-zero endemic equilibrium

Three network topologies are supported (stdlib + numpy only, no networkx):
    random      — Erdős-Rényi G(n, p=0.01)
    clustered   — stochastic block model, 3 communities
    small-world — Watts-Strogatz (k=6, β_rewire=0.1)
"""
from __future__ import annotations

from typing import Any, Optional

import numpy as np


# ── Network builders ─────────────────────────────────────────────────────────

def _build_random(n: int, rng: np.random.RandomState, p: float = 0.01) -> list[list[int]]:
    """Erdős-Rényi random graph G(n, p) using vectorised edge sampling."""
    adj: list[list[int]] = [[] for _ in range(n)]
    rows, cols = np.triu_indices(n, k=1)       # all upper-triangle pairs
    mask = rng.random(len(rows)) < p
    for i, j in zip(rows[mask].tolist(), cols[mask].tolist()):
        adj[i].append(j)
        adj[j].append(i)
    return adj


def _build_clustered(
    n: int, rng: np.random.RandomState,
    p_in: float = 0.08, p_out: float = 0.003,
) -> list[list[int]]:
    """
    Stochastic block model with 3 equal-sized communities.

    Edges within a block are drawn with probability p_in ≫ p_out.
    """
    adj: list[list[int]] = [[] for _ in range(n)]
    block = np.minimum(2, np.arange(n) * 3 // n)      # block label per voter

    rows, cols = np.triu_indices(n, k=1)
    same_block = block[rows] == block[cols]
    probs = np.where(same_block, p_in, p_out)
    mask = rng.random(len(rows)) < probs
    for i, j in zip(rows[mask].tolist(), cols[mask].tolist()):
        adj[i].append(j)
        adj[j].append(i)
    return adj


def _build_small_world(
    n: int, rng: np.random.RandomState,
    k: int = 6, beta_rewire: float = 0.10,
) -> list[list[int]]:
    """Watts-Strogatz small-world graph."""
    k = max(2, k - k % 2)          # ensure even
    half_k = k // 2
    adj_sets: list[set[int]] = [set() for _ in range(n)]

    # Ring lattice
    for i in range(n):
        for offset in range(1, half_k + 1):
            j = (i + offset) % n
            adj_sets[i].add(j)
            adj_sets[j].add(i)

    # Rewiring
    for i in range(n):
        for offset in range(1, half_k + 1):
            j = (i + offset) % n
            if j not in adj_sets[i]:
                continue                       # already rewired
            if rng.random() >= beta_rewire:
                continue
            # Remove old edge
            adj_sets[i].discard(j)
            adj_sets[j].discard(i)
            # Add new random edge (avoid self-loop and multi-edge)
            for _ in range(n):
                new_j = int(rng.randint(0, n))
                if new_j != i and new_j not in adj_sets[i]:
                    adj_sets[i].add(new_j)
                    adj_sets[new_j].add(i)
                    break

    return [list(s) for s in adj_sets]


# ── SIS model ─────────────────────────────────────────────────────────────────

def simulate_blank_contagion(
    num_voters: int,
    initial_blank_rate: float,
    contagion_rate: float,
    recovery_rate: float,
    num_rounds: int = 10,
    network_type: str = "random",
    seed: Optional[int] = None,
) -> dict[str, Any]:
    """
    Simulate blank-vote spreading via a synchronous SIS epidemic model.

    Parameters
    ----------
    num_voters : int            10 – 1 000
    initial_blank_rate : float  Fraction of voters starting as blank (0 – 1).
    contagion_rate : float      β — probability that one infected contact
                                converts a susceptible voter per round.
    recovery_rate : float       γ — probability that a blank voter returns
                                to normal voting per round.
    num_rounds : int            1 – 50
    network_type : str          "random" | "clustered" | "small-world"
    seed : int | None           Optional RNG seed.

    Returns
    -------
    dict with keys:
        rounds                : list[int]
        blank_rate_by_round   : list[float]   one per round (0 … num_rounds)
        final_blank_rate      : float
        epidemic_threshold    : float          R₀ = β / γ
        reached_equilibrium   : bool
        network_type          : str
        r0                    : float          same as epidemic_threshold
    """
    if network_type not in ("random", "clustered", "small-world"):
        raise ValueError(
            f"Unknown network_type '{network_type}'. "
            "Choose 'random', 'clustered', or 'small-world'."
        )

    n       = max(10, min(1_000, int(num_voters)))
    init    = max(0.0, min(1.0, float(initial_blank_rate)))
    beta    = max(0.0, min(1.0, float(contagion_rate)))
    gamma   = max(0.0, min(1.0, float(recovery_rate)))
    rounds  = max(1, min(50, int(num_rounds)))

    rng = np.random.RandomState(seed)

    # ── Build network ────────────────────────────────────────────────────────
    if network_type == "clustered":
        adj = _build_clustered(n, rng)
    elif network_type == "small-world":
        adj = _build_small_world(n, rng)
    else:
        adj = _build_random(n, rng)

    # Pre-convert adjacency lists to numpy arrays for fast indexing
    adj_np: list[np.ndarray[Any, np.dtype[np.int32]]] = [np.array(nb, dtype=np.int32) for nb in adj]

    # ── Initial state — 0 = susceptible (S), 1 = infected (I / blank) ───────
    state = np.zeros(n, dtype=np.int8)
    n_infected = round(n * init)
    if n_infected > 0:
        state[rng.choice(n, n_infected, replace=False)] = 1

    # ── SIS rounds ───────────────────────────────────────────────────────────
    blank_rates: list[float] = []
    equilibrium_streak = 0
    reached_equilibrium = False
    prev_rate = -1.0

    for rnd in range(rounds + 1):
        cur_rate = float(state.mean())
        blank_rates.append(round(cur_rate, 6))

        if abs(cur_rate - prev_rate) < 1e-4:
            equilibrium_streak += 1
            if equilibrium_streak >= 3:
                reached_equilibrium = True
        else:
            equilibrium_streak = 0
        prev_rate = cur_rate

        if rnd == rounds:
            break

        # ── Count infected neighbours for each voter (vectorised) ─────────
        infected_nb = np.array(
            [state[adj_np[i]].sum() if len(adj_np[i]) else 0 for i in range(n)],
            dtype=np.float64,
        )

        susceptible = state == 0
        infected    = state == 1

        # P(infection) = 1 − (1 − β)^k  where k = number of infected neighbours
        p_infect = np.where(
            susceptible,
            1.0 - (1.0 - beta) ** infected_nb,
            0.0,
        )
        new_infections = susceptible & (rng.random(n) < p_infect)

        # P(recovery) = γ
        new_recoveries = infected & (rng.random(n) < gamma)

        # Synchronous update
        state = state.copy()
        state[new_infections] = 1
        state[new_recoveries] = 0

    # ── Epidemic metrics ─────────────────────────────────────────────────────
    r0 = (beta / gamma) if gamma > 1e-9 else 100.0
    r0 = min(r0, 100.0)

    return {
        "rounds":              list(range(len(blank_rates))),
        "blank_rate_by_round": [round(r * 100, 3) for r in blank_rates],  # in %
        "final_blank_rate":    round(blank_rates[-1] * 100, 3),
        "epidemic_threshold":  round(r0, 4),
        "reached_equilibrium": reached_equilibrium,
        "network_type":        network_type,
        "r0":                  round(r0, 3),
    }
