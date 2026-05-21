"""
tech.py — Pedagogical technology-democracy endpoints.

  POST /api/tech/e2e-demo          Simplified E2E-V protocol demonstration
  POST /api/tech/polis-simulation  Pol.is-style consensus clustering (PCA + k-means)
"""
from __future__ import annotations

import hashlib
import math
import random as _random
from collections import Counter
from typing import Any, Dict, List, Optional

import numpy as _np
from flask import Blueprint, Response, jsonify, request

from app.extensions import sim_limiter

tech_bp = Blueprint("tech", __name__, url_prefix="/api/tech")

# ── Helpers ───────────────────────────────────────────────────────────────────

def _pca_2d(matrix: _np.ndarray) -> _np.ndarray:
    """Reduce (n, m) matrix to (n, 2) via SVD-based PCA."""
    centered = matrix - matrix.mean(axis=0)
    if centered.std() < 1e-12:
        return _np.zeros((matrix.shape[0], 2))
    _, _, vt = _np.linalg.svd(centered, full_matrices=False)
    n_comp = min(2, vt.shape[0])
    coords = centered @ vt[:n_comp].T
    if n_comp < 2:
        coords = _np.column_stack([coords, _np.zeros(len(coords))])
    return coords


def _kmeans(data: _np.ndarray, k: int, seed: int, max_iter: int = 150) -> _np.ndarray:
    """Lloyd's k-means; returns integer label array."""
    rng   = _np.random.RandomState(seed)
    n, _  = data.shape
    if n <= k:
        return _np.arange(n) % k
    idx        = rng.choice(n, k, replace=False)
    centroids  = data[idx].copy().astype(float)
    labels     = _np.zeros(n, dtype=int)

    for _ in range(max_iter):
        diffs      = data[:, None, :] - centroids[None, :, :]   # (n, k, d)
        dists      = (diffs ** 2).sum(axis=2)                   # (n, k)
        new_labels = dists.argmin(axis=1)
        if (new_labels == labels).all():
            break
        labels = new_labels
        for j in range(k):
            mask = labels == j
            if mask.any():
                centroids[j] = data[mask].mean(axis=0)

    return labels


# ── E2E-V demo ────────────────────────────────────────────────────────────────

@tech_bp.route("/e2e-demo", methods=["POST"])
@sim_limiter.limit("20 per minute")
def e2e_demo() -> tuple[Response, int]:
    """
    POST /api/tech/e2e-demo

    Enhanced pedagogical E2E-V simulation.  Returns:
    - voters[]: each voter's encrypted ballot + verification code + vote_HIDDEN
    - public_bulletin_board[]: SHUFFLED bulletin board (anonymised order)
    - aggregate_result: homomorphic-style count (no individual decryption)
    - winner: plurality winner
    - audit_proof: proof message

    Optional: user_vote — if set, voter #1 is the demo user's own ballot.
    """
    data           = request.get_json() or {}
    candidates     = data.get("candidates", ["Alice", "Bob", "Carol"])
    num_voters     = max(5, min(20, int(
        data.get("num_demo_voters", data.get("num_voters", 10))
    )))
    seed           = int(data.get("seed", 42))
    user_vote      = str(data.get("user_vote", ""))

    if len(candidates) < 2:
        return jsonify({"error": "At least 2 candidates required"}), 400
    if user_vote and user_vote not in candidates:
        user_vote = ""

    rng = _random.Random(seed)

    # ── Generate votes ────────────────────────────────────────────────────
    choices: list[str] = [rng.choice(candidates) for _ in range(num_voters)]
    if user_vote:
        choices[0] = user_vote       # voter 1 = the demo user

    voters_out:       list[Dict[str, Any]] = []
    verification_codes: list[str]           = []
    encrypted_ballots_legacy: list[Dict[str, Any]] = []   # backward compat

    for i, choice in enumerate(choices):
        salt        = rng.randint(100_000, 999_999)
        bhash       = hashlib.md5(f"{choice}{salt}".encode()).hexdigest().upper()
        display     = bhash[:8]
        code_raw    = hashlib.md5(f"voter-{i}-{bhash}".encode()).hexdigest().upper()
        code        = f"{code_raw[:3]}-{code_raw[3:6]}-{code_raw[6:9]}"

        voters_out.append({
            "id":               i + 1,
            "encrypted_ballot": f"[{display}…]",
            "verification_code": code,
            "vote_HIDDEN":      choice,   # revealed only in step 4 of the demo
        })
        verification_codes.append(code)
        encrypted_ballots_legacy.append({
            "voter_id":  i + 1,
            "encrypted": f"[{display}…]",
            "code":      code,
        })

    # ── Public bulletin board — SHUFFLED (anonymisation by mixing) ─────────
    bulletin_board: list[Dict[str, Any]] = [
        {"encrypted_ballot": v["encrypted_ballot"],
         "verification_code": v["verification_code"]}
        for v in voters_out
    ]
    shuffle_rng = _random.Random(seed + 999)
    shuffle_rng.shuffle(bulletin_board)

    # ── Aggregate (homomorphic-style) ─────────────────────────────────────
    aggregate: Dict[str, int] = Counter(choices)
    for c in candidates:
        aggregate.setdefault(c, 0)
    winner = max(aggregate, key=aggregate.__getitem__)

    # ── Audit proof ───────────────────────────────────────────────────────
    ahash      = hashlib.md5(str(sorted(aggregate.items())).encode()).hexdigest().upper()[:16]
    audit_proof = (
        f"Tous les {num_voters} bulletins chiffrés sont dans l'urne. "
        f"Décompte effectué sans déchiffrement individuel. "
        f"Empreinte de l'urne : {ahash}…"
    )

    return jsonify({
        # ── New rich fields ──────────────────────────────────────────────
        "voters":                voters_out,
        "public_bulletin_board": bulletin_board,
        "aggregate_result":      dict(aggregate),
        "winner":                winner,
        "audit_proof":           audit_proof,
        # ── Legacy fields (backward-compatible with existing tests) ──────
        "num_voters":            num_voters,
        "candidates":            candidates,
        "encrypted_ballots":     encrypted_ballots_legacy,
        "verification_demonstration": {
            "sample_voter_id": 1,
            "sample_code":     verification_codes[0],
            "board_excerpt":   [b["verification_code"] for b in bulletin_board[:5]],
        },
        "privacy_guarantee": (
            "Aucun bulletin individuel n'est révélé. Chaque électeur peut "
            "vérifier son code dans le tableau public sans que personne ne "
            "sache pour qui il a voté."
        ),
    }), 200


# ── Pol.is simulation ─────────────────────────────────────────────────────────

_DEFAULT_STATEMENTS = [
    "Les plateformes de location courte durée doivent être réglementées.",
    "Les hôtes devraient payer des taxes identiques aux hôtels.",
    "Les VTC doivent respecter les mêmes obligations que les taxis.",
    "La tarification dynamique est équitable pour les consommateurs.",
    "La sécurité des passagers prime sur la commodité des plateformes.",
    "Les travailleurs de plateforme méritent des protections sociales.",
    "L'innovation technologique devrait primer sur la réglementation.",
    "Les gouvernements locaux devraient contrôler les plateformes.",
    "La concurrence entre plateformes bénéficie aux consommateurs.",
    "Les données des utilisateurs appartiennent aux utilisateurs, pas aux plateformes.",
]


@tech_bp.route("/polis-simulation", methods=["POST"])
@sim_limiter.limit("10 per minute")
def polis_simulation() -> tuple[Response, int]:
    """
    POST /api/tech/polis-simulation

    Pol.is-style consensus clustering:
    1. Generate participants with ideology positions
    2. Each participant votes Yes/No on each statement (based on ideology alignment)
    3. PCA 2D + k-means clustering on the vote matrix
    4. Identify consensus (all clusters agree) and polarising statements
    """
    data             = request.get_json() or {}
    statements       = data.get("statements", _DEFAULT_STATEMENTS)[:15]
    num_participants = max(20, min(500, int(data.get("num_participants", 100))))
    ideology         = str(data.get("ideology", "random"))
    seed             = int(data.get("seed", 42))
    num_clusters     = max(1, min(5, int(data.get("num_clusters", 3))))

    if len(statements) < 2:
        return jsonify({"error": "At least 2 statements required"}), 400

    _np.random.seed(seed)
    n_stmt = len(statements)

    # ── Participant ideology positions ────────────────────────────────────
    if ideology in ("polarized", "bimodal"):
        half = num_participants // 2
        ideologies = _np.concatenate([
            _np.random.normal(-0.65, 0.15, half),
            _np.random.normal( 0.65, 0.15, num_participants - half),
        ])
    else:
        ideologies = _np.random.uniform(-1.0, 1.0, num_participants)
    ideologies = _np.clip(ideologies, -1.0, 1.0)

    # ── Statement positions (deterministic per seed) ──────────────────────
    stmt_rng    = _np.random.RandomState(seed + 100)
    stmt_pos    = _np.zeros(n_stmt)
    is_consensus = [False] * n_stmt

    for j in range(n_stmt):
        cycle = j % 4
        if cycle == 0:                                    # consensus item
            stmt_pos[j]    = 0.0
            is_consensus[j] = True
        elif cycle == 1:                                  # left-leaning
            stmt_pos[j] = float(stmt_rng.uniform(-1.0, -0.4))
        elif cycle == 2:                                  # right-leaning
            stmt_pos[j] = float(stmt_rng.uniform( 0.4,  1.0))
        else:                                             # mixed/centrist
            stmt_pos[j] = float(stmt_rng.uniform(-0.4,  0.4))

    # ── Vote matrix ───────────────────────────────────────────────────────
    vote_rng    = _np.random.RandomState(seed + 200)
    vote_matrix = _np.zeros((num_participants, n_stmt))

    for i in range(num_participants):
        for j in range(n_stmt):
            if is_consensus[j]:
                yes_prob = 0.82 + float(vote_rng.uniform(-0.08, 0.08))
            else:
                alignment = float(ideologies[i]) * float(stmt_pos[j])
                yes_prob  = 0.5 + 0.45 * math.tanh(alignment * 3.0)
            vote_matrix[i, j] = 1.0 if vote_rng.random() < yes_prob else 0.0

    # ── PCA + k-means ─────────────────────────────────────────────────────
    coords_2d = _pca_2d(vote_matrix)
    labels    = _kmeans(coords_2d, num_clusters, seed)

    # ── Per-cluster vote rates ────────────────────────────────────────────
    clusters: list[Dict[str, Any]] = []
    for cid in range(num_clusters):
        mask = labels == cid
        size = int(mask.sum())
        votes = {
            stmt: round(float(vote_matrix[mask, j].mean()), 3) if size else 0.0
            for j, stmt in enumerate(statements)
        }
        clusters.append({"id": cid, "size": size, "votes": votes})

    # ── Consensus and polarising ──────────────────────────────────────────
    consensus_threshold  = 0.60
    polarising_threshold = 0.35

    consensus_statements:  list[Dict[str, Any]] = []
    polarizing_statements: list[Dict[str, Any]] = []

    for j, stmt in enumerate(statements):
        rates       = [c["votes"].get(stmt, 0.0) for c in clusters]
        overall     = float(vote_matrix[:, j].mean())
        min_rate    = min(rates)
        max_rate    = max(rates)
        delta       = max_rate - min_rate

        if min_rate >= consensus_threshold:
            consensus_statements.append({
                "statement":    stmt,
                "approval_rate": round(overall, 3),
            })

        if delta >= polarising_threshold and num_clusters > 1:
            polarizing_statements.append({
                "statement":   stmt,
                "cluster_delta": round(delta, 3),
            })

    # ── Sort by relevance ─────────────────────────────────────────────────
    consensus_statements.sort(key=lambda s: -s["approval_rate"])
    polarizing_statements.sort(key=lambda s: -s["cluster_delta"])

    # ── Participant positions for scatter ─────────────────────────────────
    participant_positions = [
        {
            "id":         int(i),
            "x_pca":      round(float(coords_2d[i, 0]), 3),
            "y_pca":      round(float(coords_2d[i, 1]), 3),
            "cluster_id": int(labels[i]),
        }
        for i in range(num_participants)
    ]

    return jsonify({
        "clusters":               clusters,
        "consensus_statements":   consensus_statements,
        "polarizing_statements":  polarizing_statements,
        "participant_positions":  participant_positions,
        "num_clusters":           num_clusters,
        "num_participants":       num_participants,
    }), 200
