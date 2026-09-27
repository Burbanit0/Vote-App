"""
tech.py — Pedagogical technology-democracy endpoints.

  POST /api/tech/e2e-demo          Simplified E2E-V protocol demonstration
  POST /api/tech/polis-simulation  Pol.is-style consensus clustering (PCA + k-means)
"""
from __future__ import annotations

import random as _random
from collections import Counter
from typing import Any, Dict, List

import numpy as _np

from api.engine.utils.demographic_data import _seeded_rng_pair



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
    return _np.asarray(coords)


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





# ── Pol.is simulation ─────────────────────────────────────────────────────────

_DEFAULT_STATEMENTS = (
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
)


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
    min_thr            = max(0.0, min(1.0, float(data.get("min_consensus_threshold", 0.80))))

    if len(stmts_raw) < 2:
        return {"error": "At least 2 statements required"}, 400

    _, np_rng = _seeded_rng_pair(seed)

    # ── Participant ideology positions ────────────────────────────────────
    if ideology == "polarized":
        h = num_participants // 2
        pax = _np.clip(_np.concatenate([
            np_rng.normal(-0.65, 0.18, h),
            np_rng.normal( 0.65, 0.18, num_participants - h),
        ]), -1, 1)
    elif ideology == "centrist":
        pax = _np.clip(np_rng.normal(0.0, 0.25, num_participants), -1, 1)
    else:
        pax = np_rng.uniform(-1, 1, num_participants)

    # ── Statement positions ───────────────────────────────────────────────
    stmt_rng = _random.Random(seed + 100)
    stmts: List[Dict[str, Any]] = []
    stmt_pos: List[float]        = []

    for s in stmts_raw:
        # `_POLIS_DEFAULT_STATEMENTS` above is {"text", "category"} dicts,
        # but the request schema (PolisWithCandidatesRequest.statements)
        # promises plain strings — a real client sending exactly what the
        # schema documents crashed here with AttributeError, since only the
        # internal default happened to be dict-shaped (found by
        # Schemathesis, Lot 3). A caller-supplied string has no category, so
        # it falls back to "default" (already a real key in _CATEGORY_BIAS).
        if isinstance(s, dict):
            cat  = str(s.get("category", "default")).lower()
            text = str(s.get("text", "?"))
        else:
            cat  = "default"
            text = str(s)
        base = _CATEGORY_BIAS.get(cat, 0.0)
        pos  = float(_np.clip(base + stmt_rng.uniform(-0.3, 0.3), -1, 1))
        stmts.append({"text": text, "category": cat, "position": pos})
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
        ca_list     = [c["votes"][j] for c in clusters_out]
        global_app  = round(float((votes[:, j] == 1).sum()) / num_participants, 3)
        delta       = (max(ca_list) - min(ca_list)) if len(ca_list) > 1 else 0.0

        is_cons     = all(v >= min_thr for v in ca_list)
        is_pol      = (delta > 0.5) and not is_cons
        is_silent   = (global_app > 0.60) and not is_cons and (min(ca_list) < min_thr)

        if is_cons:   consensus_count  += 1
        if is_pol:    polarizing_count += 1
        if is_silent: silent_count     += 1

        stmts_out.append({
            "text":              stmt["text"],
            "global_approval":   global_app,
            "is_consensus":      is_cons,
            "is_polarizing":     is_pol,
            "cluster_approvals": ca_list,
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
    vote_tally: Counter[str] = Counter()
    for px in pax:
        vote_tally[cand_names[int(_np.argmin([abs(px - cx) for cx in cand_x]))]] += 1
    election_winner = min(vote_tally, key=lambda c: (-vote_tally[c], c)) if vote_tally else cand_names[0]
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
        f"vainqueur à la pluralité : '{election_winner}')."
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


