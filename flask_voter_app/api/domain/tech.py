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
from typing import Any, Dict, List

import numpy as _np



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

def _e2e_demo_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /tech/e2e-demo — extracted for FastAPI v2."""
    candidates     = data.get("candidates") or ["Alice", "Bob", "Carol"]
    num_voters     = max(5, min(20, int(
        data.get("num_demo_voters") or data.get("num_voters") or 10
    )))
    seed           = int(data.get("seed", 42))
    user_vote      = str(data.get("user_vote", ""))

    if len(candidates) < 2:
        return {"error": "At least 2 candidates required"}, 400
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

    return {
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
    }, 200




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


def _polis_simulation_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /tech/polis-simulation — extracted for FastAPI v2."""
    statements       = (data.get("statements") or _DEFAULT_STATEMENTS)[:15]
    num_participants = max(20, min(500, int(data.get("num_participants", 100))))
    ideology         = str(data.get("ideology", "random"))
    seed             = int(data.get("seed", 42))
    num_clusters     = max(1, min(5, int(data.get("num_clusters", 3))))

    if len(statements) < 2:
        return {"error": "At least 2 statements required"}, 400

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

    return {
        "clusters":               clusters,
        "consensus_statements":   consensus_statements,
        "polarizing_statements":  polarizing_statements,
        "participant_positions":  participant_positions,
        "num_clusters":           num_clusters,
        "num_participants":       num_participants,
    }, 200




# ── Pol.is with candidate evaluation ─────────────────────────────────────────

_POLIS_DEFAULT_STATEMENTS: List[Dict[str, str]] = [
    {"text": "Les chauffeurs VTC doivent être officiellement déclarés", "category": "economie"},
    {"text": "Les plateformes doivent payer des taxes locales",         "category": "economie"},
    {"text": "La sécurité des passagers doit être prioritaire",         "category": "social"},
    {"text": "Les chauffeurs doivent bénéficier d'une protection sociale", "category": "social"},
    {"text": "La tarification dynamique doit être encadrée par la loi", "category": "economie"},
    {"text": "Les nouvelles plateformes doivent être réglementées comme les taxis", "category": "economie"},
    {"text": "L'innovation technologique prime sur la réglementation",  "category": "economie"},
    {"text": "Les données des utilisateurs doivent être protégées",     "category": "social"},
    {"text": "L'accès à ces services doit être universel",              "category": "social"},
    {"text": "Les villes doivent contrôler les licences de location",   "category": "social"},
]

_CATEGORY_BIAS: Dict[str, float] = {
    "economie": 0.25, "social": -0.25,
    "securite": 0.55, "environnement": -0.55, "default": 0.0,
}


def _polis_with_candidates_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /tech/polis — extracted for FastAPI v2."""
    cand_specs         = (data.get("candidates") or [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.1},
    ])[:6]
    stmts_raw          = (data.get("statements") or _POLIS_DEFAULT_STATEMENTS)[:15]
    num_participants   = max(20,  min(500, int(data.get("num_participants",    100))))
    ideology           = str(data.get("ideology",              "random"))
    seed               = int(data.get("seed",                   42))
    num_clusters       = max(1,   min(5,   int(data.get("num_clusters",          3))))
    method_compare     = str(data.get("method_to_compare",     "plurality"))
    min_thr            = max(0.0, min(1.0, float(data.get("min_consensus_threshold", 0.80))))

    if len(stmts_raw) < 2:
        return {"error": "At least 2 statements required"}, 400

    _np.random.seed(seed)
    _random.seed(seed)

    # ── Participant ideology positions ────────────────────────────────────
    if ideology == "polarized":
        h = num_participants // 2
        pax = _np.clip(_np.concatenate([
            _np.random.normal(-0.65, 0.18, h),
            _np.random.normal( 0.65, 0.18, num_participants - h),
        ]), -1, 1)
    elif ideology == "centrist":
        pax = _np.clip(_np.random.normal(0.0, 0.25, num_participants), -1, 1)
    else:
        pax = _np.random.uniform(-1, 1, num_participants)

    # ── Statement positions ───────────────────────────────────────────────
    stmt_rng = _random.Random(seed + 100)
    stmts: List[Dict[str, Any]] = []
    stmt_pos: List[float]        = []

    for s in stmts_raw:
        cat  = str(s.get("category", "default")).lower()
        base = _CATEGORY_BIAS.get(cat, 0.0)
        pos  = float(_np.clip(base + stmt_rng.uniform(-0.3, 0.3), -1, 1))
        stmts.append({"text": str(s.get("text", "?")), "category": cat, "position": pos})
        stmt_pos.append(pos)

    n_stmts = len(stmts)
    spos    = _np.array(stmt_pos)

    # ── Vote matrix (participants × statements) ───────────────────────────
    # alignment = participant_x * statement_pos  (positive = same side)
    align    = _np.outer(pax, spos)                       # (N, M)
    noise    = _np.random.RandomState(seed + 200).uniform(-0.2, 0.2, align.shape)
    p_yes    = 1.0 / (1.0 + _np.exp(-(align * 2.5 + noise)))

    votes    = _np.zeros_like(p_yes)
    votes[p_yes > 0.60] =  1.0
    votes[p_yes < 0.40] = -1.0

    # ── PCA + k-means ─────────────────────────────────────────────────────
    coords   = _pca_2d(votes)
    labels   = _kmeans(coords, num_clusters, seed)

    # ── Cluster summaries ─────────────────────────────────────────────────
    clusters_out: List[Dict[str, Any]] = []
    for cid in range(num_clusters):
        mask = labels == cid
        size = int(mask.sum())
        ca   = {
            j: round(float((votes[mask, j] == 1).sum()) / size, 3) if size else 0.0
            for j in range(n_stmts)
        }
        cx   = float(pax[mask].mean()) if mask.any() else 0.0
        if cx < -0.2:    lbl = "progressistes"
        elif cx > 0.2:   lbl = "conservateurs"
        else:            lbl = f"groupe {cid + 1}"
        clusters_out.append({
            "id": cid, "size": size, "label": lbl,
            "center": {"x": round(cx, 3),
                       "y": round(float(coords[mask, 1].mean()), 3) if mask.any() else 0.0},
            "votes": ca,
        })

    # ── Statement analysis ────────────────────────────────────────────────
    stmts_out: List[Dict[str, Any]] = []
    consensus_count = polarizing_count = silent_count = 0

    for j, stmt in enumerate(stmts):
        ca          = [c["votes"][j] for c in clusters_out]
        global_app  = round(float((votes[:, j] == 1).sum()) / num_participants, 3)
        delta       = (max(ca) - min(ca)) if len(ca) > 1 else 0.0

        is_cons     = all(v >= min_thr for v in ca)
        is_pol      = (delta > 0.5) and not is_cons
        is_silent   = (global_app > 0.60) and not is_cons and (min(ca) < min_thr)

        if is_cons:   consensus_count  += 1
        if is_pol:    polarizing_count += 1
        if is_silent: silent_count     += 1

        stmts_out.append({
            "text":              stmt["text"],
            "global_approval":   global_app,
            "is_consensus":      is_cons,
            "is_polarizing":     is_pol,
            "cluster_approvals": ca,
        })

    # ── Candidate scoring ─────────────────────────────────────────────────
    cand_names = [str(s.get("name", f"C{i}")) for i, s in enumerate(cand_specs)]
    cand_x     = [max(-1.0, min(1.0, float(s.get("x", 0.0)))) for s in cand_specs]

    target_indices = [j for j, s in enumerate(stmts_out) if s["is_consensus"]] or list(range(n_stmts))

    cand_scores: Dict[str, float] = {}
    for ci, cname in enumerate(cand_names):
        score = sum(1.0 - abs(cand_x[ci] - stmts[j]["position"]) for j in target_indices)
        cand_scores[cname] = round(score / len(target_indices), 4)

    polis_winner    = max(cand_scores, key=cand_scores.__getitem__)

    # ── Classical election (plurality by ideology proximity) ──────────────
    vote_tally: Counter = Counter()
    for px in pax:
        vote_tally[cand_names[int(_np.argmin([abs(px - cx) for cx in cand_x]))]] += 1
    election_winner = vote_tally.most_common(1)[0][0] if vote_tally else cand_names[0]
    winners_agree   = polis_winner == election_winner

    # ── Participant positions ─────────────────────────────────────────────
    participant_positions = [
        {"id": i, "x_pca": round(float(coords[i, 0]), 3),
         "y_pca": round(float(coords[i, 1]), 3), "cluster_id": int(labels[i])}
        for i in range(num_participants)
    ]

    note = (
        f"Pol.is révèle {consensus_count} propositions consensuelles, "
        f"{polarizing_count} polarisantes et {silent_count} majorités silencieuses "
        f"sur {n_stmts} propositions. "
        f"Candidat Pol.is : '{polis_winner}' "
        f"({'= ' if winners_agree else '≠ '}"
        f"vainqueur {method_compare} : '{election_winner}')."
    )

    return {
        "clusters":              clusters_out,
        "statements":            stmts_out,
        "participant_positions": participant_positions,
        "polis_winner":          polis_winner,
        "election_winner":       election_winner,
        "winners_agree":         winners_agree,
        "consensus_count":       consensus_count,
        "polarizing_count":      polarizing_count,
        "silent_majority_count": silent_count,
        "candidate_scores":      cand_scores,
        "pedagogical_note":      note,
    }, 200


