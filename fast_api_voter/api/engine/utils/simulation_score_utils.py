from collections import defaultdict
from operator import itemgetter
from typing import Any, Dict, List, Optional
import math
import statistics


def get_simple_score_winner(all_scores: Any) -> Dict[str, Any]:
    candidate_scores: "defaultdict[Any, dict[str, Any]]" = defaultdict(
        lambda: {"sum": 0, "count": 0}
    )

    for vote in all_scores:
        for candidate, score in vote.items():
            candidate_scores[candidate]["sum"] += score
            candidate_scores[candidate]["count"] += 1

    # Calculate averages
    averages = []
    for candidate, data in candidate_scores.items():
        avg = data["sum"] / data["count"] if data["count"] > 0 else 0
        averages.append((candidate, avg))

    # Sort by average score (descending)
    averages.sort(key=itemgetter(1), reverse=True)

    return {
        "method": "Simple Score",
        "winner": averages[0][0] if averages else None,
        "details": {candidate: avg for candidate, avg in averages},
    }


def get_star_voting_winner(all_scores: Any) -> Dict[str, Any]:
    """
    Determine the winner using STAR (Score Then Automatic Runoff) voting.
    """
    # First round: calculate average scores
    candidate_scores: "defaultdict[Any, dict[str, Any]]" = defaultdict(
        lambda: {"sum": 0, "count": 0}
    )

    for vote in all_scores:
        for candidate, score in vote.items():
            candidate_scores[candidate]["sum"] += score
            candidate_scores[candidate]["count"] += 1

    averages = []
    for candidate, data in candidate_scores.items():
        avg = data["sum"] / data["count"] if data["count"] > 0 else 0
        averages.append((candidate, avg))

    # Sort by average score (descending)
    averages.sort(key=itemgetter(1), reverse=True)

    # Take top two candidates for runoff
    if len(averages) < 2:
        return {
            "method": "STAR Voting",
            "winner": averages[0][0] if averages else None,
            "details": {
                "first_round": {candidate: avg for candidate, avg in averages},
                "runoff": None,
            },
        }

    top_two = averages[:2]
    candidate1, candidate2 = top_two[0][0], top_two[1][0]

    # Runoff: compare head-to-head
    votes1 = 0
    votes2 = 0
    tied = 0

    for vote in all_scores:
        score1 = vote.get(candidate1, 0)
        score2 = vote.get(candidate2, 0)

        if score1 > score2:
            votes1 += 1
        elif score2 > score1:
            votes2 += 1
        else:
            tied += 1

    # On a tied runoff, STAR breaks it by score — candidate1 is the higher-scored
    # finalist, so it must win the tie (>=, not >).
    runoff_winner = candidate1 if votes1 >= votes2 else candidate2

    return {
        "method": "STAR Voting",
        "winner": runoff_winner,
        "details": {
            "first_round": {candidate: avg for candidate, avg in averages},
            "runoff": {
                "candidate1": candidate1,
                "candidate2": candidate2,
                "votes1": votes1,
                "votes2": votes2,
                "tied": tied,
                "total_voters": len(all_scores),
            },
        },
    }


def _score_candidates(all_scores: Any) -> List[Any]:
    """Candidates in first-encountered order (deterministic tie-break, matching
    the client's argmax-over-index convention)."""
    candidates: List[Any] = []
    seen: set = set()
    for vote in all_scores:
        for c in vote:
            if c not in seen:
                seen.add(c)
                candidates.append(c)
    return candidates


def get_cumulative_winner(all_scores: Any) -> Optional[str]:
    """
    Cumulative voting: each voter splits ONE point across candidates in
    proportion to their scores (favourites get more, but the budget is
    shared). Most points wins.
    """
    candidates = _score_candidates(all_scores)
    if not candidates:
        return None
    tally: "defaultdict[Any, float]" = defaultdict(float)
    for vote in all_scores:
        total = sum(vote.values())
        if total > 0:
            for c, s in vote.items():
                tally[c] += s / total
    return str(max(candidates, key=lambda c: tally[c]))


def get_maximin_score_winner(all_scores: Any) -> Optional[str]:
    """
    Maximin (Rawlsian): elect the candidate whose WORST rating across voters
    is highest — the least-bad option for the most disadvantaged voter.
    """
    candidates = _score_candidates(all_scores)
    if not candidates:
        return None
    worst = {c: math.inf for c in candidates}
    for vote in all_scores:
        for c, s in vote.items():
            worst[c] = min(worst[c], s)
    return str(max(candidates, key=lambda c: worst[c]))


def get_nash_winner(all_scores: Any) -> Optional[str]:
    """
    Nash (proportional welfare): maximise the PRODUCT of voter utilities —
    summed in log-space to stay numerically stable. Rating a candidate 0
    crushes it, so Nash sits between the utilitarian sum (score) and the
    Rawlsian min (maximin).
    """
    candidates = _score_candidates(all_scores)
    if not candidates:
        return None
    eps = 1e-6
    acc: "defaultdict[Any, float]" = defaultdict(float)
    for vote in all_scores:
        for c, s in vote.items():
            acc[c] += math.log(max(s, eps))
    return str(max(candidates, key=lambda c: acc[c]))


def get_median_voting_winner(all_scores: Any) -> Dict[str, Any]:
    candidate_scores: "defaultdict[Any, list[Any]]" = defaultdict(list)

    for vote in all_scores:
        for candidate, score in vote.items():
            candidate_scores[candidate].append(score)

    medians = []
    for candidate, scores in candidate_scores.items():
        median = statistics.median(scores) if scores else 0
        medians.append((candidate, median))

    # Sort by median score (descending)
    medians.sort(key=itemgetter(1), reverse=True)

    return {
        "method": "Median Voting",
        "winner": medians[0][0] if medians else None,
        "details": {candidate: median for candidate, median in medians},
    }


def get_mean_median_hybrid_winner(all_scores: Any) -> Dict[str, Any]:
    candidate_stats: "defaultdict[Any, dict[str, Any]]" = defaultdict(
        lambda: {"sum": 0, "count": 0, "scores": []}
    )

    for vote in all_scores:
        for candidate, score in vote.items():
            candidate_stats[candidate]["sum"] += score
            candidate_stats[candidate]["count"] += 1
            candidate_stats[candidate]["scores"].append(score)

    results = []
    for candidate, stats in candidate_stats.items():
        mean = stats["sum"] / stats["count"] if stats["count"] > 0 else 0
        median = statistics.median(stats["scores"]) if stats["scores"] else 0

        # Combined score (50% mean, 50% median)
        combined = 0.5 * mean + 0.5 * median

        results.append(
            {
                "candidate": candidate,
                "mean": mean,
                "median": median,
                "combined": combined,
            }
        )

    results.sort(key=itemgetter("combined"), reverse=True)

    return {
        "method": "Mean-Median Hybrid",
        "winner": results[0]["candidate"] if results else None,
        "details": results,
    }


def get_variance_based_winner(all_scores: Any) -> Dict[str, Any]:
    candidate_stats: "defaultdict[Any, dict[str, Any]]" = defaultdict(
        lambda: {"sum": 0, "sum_sq": 0, "count": 0}
    )

    for vote in all_scores:
        for candidate, score in vote.items():
            candidate_stats[candidate]["sum"] += score
            candidate_stats[candidate]["sum_sq"] += score * score
            candidate_stats[candidate]["count"] += 1

    results = []
    for candidate, stats in candidate_stats.items():
        count = stats["count"]
        if count == 0:
            mean = 0
            variance = 0
        else:
            mean = stats["sum"] / count
            variance = (stats["sum_sq"] / count) - (mean * mean)
        std_dev = math.sqrt(max(variance, 0.0))

        # Weighted score that balances mean and consistency (lower variance is better)
        weighted_score = mean - 0.5 * std_dev

        results.append(
            {
                "candidate": candidate,
                "mean": mean,
                "variance": variance,
                "std_dev": std_dev,
                "weighted_score": weighted_score,
            }
        )

    results.sort(key=itemgetter("weighted_score"), reverse=True)

    return {
        "method": "Variance-Based",
        "winner": results[0]["candidate"] if results else None,
        "details": results,
    }


# ── Majority Judgment ─────────────────────────────────────────────────────────

DEFAULT_MJ_GRADES: List[str] = [
    "À Rejeter",    # 0 — worst
    "Passable",     # 1
    "Assez Bien",   # 2
    "Bien",         # 3
    "Très Bien",    # 4
    "Excellent",    # 5 — best
]

# Utility thresholds (lower bound inclusive) for each grade (ascending)
_MJ_THRESHOLDS: List[float] = [0.0, 0.17, 0.33, 0.50, 0.67, 0.83]


def _utility_to_grade(utility: float) -> int:
    """Convert a utility score in [0, 1] to a grade index in [0, 5]."""
    for i in range(len(_MJ_THRESHOLDS) - 1, -1, -1):
        if utility >= _MJ_THRESHOLDS[i]:
            return i
    return 0


def _mj_lower_median_index(n: int) -> int:
    """
    Majority Judgment median index: ceil(n/2) - 1 into a SORTED list of n
    grades. For odd n: the exact middle. For even n: the lower of the two
    middles (conservative choice) — a median must stay a real grade, never
    an interpolated average of two.
    """
    return (n - 1) // 2


def _mj_lower_median(grades: List[int]) -> int:
    # -1 (not 0 / "À Rejeter") for an empty list: a candidate that has run
    # out of grades to strip must never look tied with one still holding a
    # real grade of 0, only with another equally exhausted candidate. Real
    # candidates never hit this branch (see `_mj_winner`'s `true_medians`) —
    # only a candidate the tie-break has stripped down to nothing can.
    return grades[_mj_lower_median_index(len(grades))] if grades else -1


def _mj_strip_to_winner(pool: List[str], work: Dict[str, List[int]]) -> str:
    """
    The actual Balinski-Laraki (2010) tie-break: repeatedly strip one
    occurrence of the tied top median grade from every candidate still tied
    for first, and recompare, until one candidate stands alone or there is
    no more data to strip. `work` is mutated in place (each candidate's
    private, already-sorted copy — see `_mj_winner`).

    This used to be approximated by a majority-gauge shortcut (compare p -
    q, the fraction of grades above vs. below the median) with a single
    extra strip step if that didn't decide it either. Both were wrong: on
    fixture scenarios where the top two shared a median, p - q picked a
    different winner than the real procedure on several profiles (the gauge
    is not equivalent to repeated stripping in general), it only ever
    compared the top TWO candidates even when three or more were tied, and
    it compared p and q as floats, so an exact tie between two candidates'
    gauges could be decided by rounding noise. This is a direct port of
    winMajorityJudgment (playgroundVoting.ts), the client's implementation,
    which the parity harness (gen_engine_parity.py) checks this against —
    not an attempt to derive an equivalent closed-form comparator.
    """
    # Any pool member still holding a grade, not just the first — candidates
    # can have unequal grade-list lengths (a voter who didn't rate everyone),
    # and checking only pool[0] let an exhausted-but-first-encountered
    # candidate win by default over a rival who still had a real, better
    # grade left to compare (found by /code-review max on this branch: same
    # votes, only the candidates' dict-insertion order differed, and the
    # winner changed with it — see
    # test_majority_judgment_tie_survives_a_shorter_grade_list's repro).
    while len(pool) > 1 and any(work[c] for c in pool):
        best_median = max(_mj_lower_median(work[c]) for c in pool)
        top = [c for c in pool if _mj_lower_median(work[c]) == best_median]
        if len(top) == 1:
            return top[0]
        for c in top:
            work[c].pop(_mj_lower_median_index(len(work[c])))
        pool = top
    return pool[0]


def _mj_winner(
    candidate_names: List[str], all_grades: Dict[str, List[int]]
) -> tuple[Optional[str], Dict[str, int]]:
    """
    The Majority Judgment winner (see `_mj_strip_to_winner` for the actual
    tie-break), plus each candidate's TRUE (un-stripped) median — computed
    here, once, from the same sorted copy the tie-break itself needs, so the
    caller never has to re-sort `all_grades` just to report it.

    Operates on a private copy of each candidate's grades. Never mutates
    `all_grades`: the returned medians, and everything the caller reports
    from `all_grades` afterwards (distribution, score), stay the TRUE
    values, so a tie-break that had to look past the headline median never
    changes what gets reported for the candidates it compared.
    """
    if not candidate_names:
        return None, {}

    work: Dict[str, List[int]] = {c: sorted(all_grades[c]) for c in candidate_names}
    # Every real candidate has at least one grade (a candidate only enters
    # `candidate_names` by being rated by some voter — see the caller's
    # `_score_candidates` union), so this is always a real grade, never -1.
    true_medians: Dict[str, int] = {c: _mj_lower_median(work[c]) for c in candidate_names}

    winner = _mj_strip_to_winner(list(candidate_names), work)
    return winner, true_medians


def get_majority_judgment_winner(
    utility_scores: List[Dict[str, float]],
    grade_labels:   List[str] = DEFAULT_MJ_GRADES,
) -> Dict[str, object]:
    """
    Majority Judgment (Balinski & Laraki, 2010).

    Each voter grades each candidate on a 6-level ordinal scale derived
    from their utility score in [0, 1]. The winner is the candidate with
    the highest median grade; ties are broken by repeatedly stripping one
    occurrence of the tied median grade from every candidate still tied for
    first and recomparing (see `_mj_winner`), not by a majority-gauge
    shortcut.

    Parameters
    ----------
    utility_scores : List[Dict[str, float]]
        One dict per voter, mapping candidate name → utility in [0, 1].
    grade_labels : List[str]
        Ordered label list, index 0 = worst, index N-1 = best.

    Returns
    -------
    {
        "winner":  str | None,
        "grades":  {candidate: {grade_label: count}},
        "medians": {candidate: str},
        "scores":  {candidate: float},   # continuous score for comparison
        "grade_distributions": {candidate: [count_grade0, …, count_gradeN]}
    }
    """
    if not utility_scores:
        return {"winner": None, "grades": {}, "medians": {}, "scores": {},
                "grade_distributions": {}}

    # Union of every voter's candidates, not just voter 0's: a later voter
    # rating a candidate voter 0 didn't (e.g. a candidate who entered the
    # race after voter 0's ballot was cast) used to KeyError on
    # `all_grades[c]` below, since that dict was only ever pre-seeded with
    # voter 0's own keys. `_score_candidates` already implements this same
    # "first-encountered order across every voter" union for the other
    # cardinal rules in this file. Found fuzzing this function with atheris
    # (Lot 9, PLAN_SOLIDITE_TECHNIQUE.md).
    candidate_names: List[str] = _score_candidates(utility_scores)

    # 1. Build grade lists per candidate. This is the canonical, NEVER
    # mutated source for every field reported below (distributions, scores)
    # as well as for winner determination — `_mj_winner` works on its own
    # private copy.
    all_grades: Dict[str, List[int]] = {c: [] for c in candidate_names}
    for voter_utils in utility_scores:
        for c, u in voter_utils.items():
            all_grades[c].append(_utility_to_grade(u))

    # 2. Determine the winner. `medians` here are the TRUE, un-stripped
    # medians `_mj_winner` computed as a side effect of running the
    # tie-break — not read from `all_grades` a second time, so ties don't
    # cost an extra sort per candidate. A real past bug lived here: the old
    # top-2-only tiebreak mutated `all_grades` in place while deciding a
    # tie, so a tied pair's own reported median/distribution came back one
    # ballot short (and, when both truly shared the same median, wrongly
    # reported as unequal) — see `_mj_winner`'s docstring.
    winner: Optional[str]
    medians: Dict[str, int]
    winner, medians = _mj_winner(candidate_names, all_grades)

    # 3. Build grade distribution and continuous-score dicts for the
    # frontend, read from the TRUE, un-stripped grades.
    n_grades = len(grade_labels)
    grade_distributions: Dict[str, List[int]] = {}
    grades_labeled:      Dict[str, Dict[str, int]] = {}
    scores_out:          Dict[str, float] = {}

    for c in candidate_names:
        dist = [0] * n_grades
        for grade in all_grades[c]:
            if 0 <= grade < n_grades:
                dist[grade] += 1
        grade_distributions[c] = dist
        grades_labeled[c]      = {grade_labels[i]: dist[i] for i in range(n_grades)}
        # Continuous score: weighted average of grade indices
        n = len(all_grades[c]) or 1
        scores_out[c] = round(sum(g * cnt for g, cnt in enumerate(dist)) / n, 4)

    return {
        "winner":             winner,
        "grades":             grades_labeled,
        "medians":            {c: grade_labels[medians[c]] for c in candidate_names},
        "scores":             scores_out,
        "grade_distributions": grade_distributions,
    }


def get_evaluative_winner(
    utility_scores: List[Dict[str, float]],
    threshold_approve: float = 0.67,
    threshold_reject:  float = 0.33,
) -> Dict[str, object]:
    """
    Evaluative voting (vote +1 / 0 / −1).

    Each voter expresses approval (+1), neutrality (0), or rejection (−1)
    for each candidate based on their utility:
      utility ≥ threshold_approve → +1
      utility ≤ threshold_reject  → −1
      otherwise                   → 0

    The winner is the candidate with the highest net score (Σ votes).
    Tie-break: alphabetical.

    Parameters
    ----------
    utility_scores     : list of {candidate: utility ∈ [0,1]} dicts
    threshold_approve  : minimum utility for +1 (default 0.67 ≈ "Très Bien" in MJ)
    threshold_reject   : maximum utility for −1 (default 0.33 ≈ "Passable" in MJ)

    Returns
    -------
    {
        "winner":       str | None,
        "scores":       {candidate: int},        # net score
        "distribution": {candidate: {"+1": int, "0": int, "-1": int}}
    }
    """
    if not utility_scores:
        return {"winner": None, "scores": {}, "distribution": {}}

    # Union of every voter's candidates, not just voter 0's -- same fix and
    # same reason as get_majority_judgment_winner just above: deriving this
    # from voter 0 alone doesn't crash here (the loop below already reads
    # `voter_utils.get(c, 0.0)`), but it silently drops any candidate a
    # LATER voter rated and voter 0 didn't from every result entirely.
    # Found alongside the majority-judgment KeyError while fuzzing this
    # file with atheris (Lot 9, PLAN_SOLIDITE_TECHNIQUE.md).
    candidates = _score_candidates(utility_scores)
    if not candidates:
        return {"winner": None, "scores": {}, "distribution": {}}

    net:  dict[str, int] = {c: 0 for c in candidates}
    dist: dict[str, dict[str, int]] = {c: {"+1": 0, "0": 0, "-1": 0} for c in candidates}

    for voter_utils in utility_scores:
        for c in candidates:
            u = voter_utils.get(c, 0.0)
            if u >= threshold_approve:
                net[c]  += 1
                dist[c]["+1"] += 1
            elif u <= threshold_reject:
                net[c]  -= 1
                dist[c]["-1"] += 1
            else:
                dist[c]["0"] += 1

    if not any(net.values()):
        # All zeros — no approvals
        return {"winner": None, "scores": net, "distribution": dist}

    winner = min(candidates, key=lambda c: (-net[c], c))  # alpha tie-break
    return {"winner": winner, "scores": net, "distribution": dist}
