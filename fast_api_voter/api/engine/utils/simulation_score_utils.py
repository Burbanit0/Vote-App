from collections import defaultdict
from typing import Any, Dict, List, Optional
import math
import statistics


def get_simple_score_winner(all_scores: Any) -> Dict[str, Any]:
    """
    Determine the winner using simple score sum/average method.
    """
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
    averages.sort(key=lambda x: x[1], reverse=True)

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
    averages.sort(key=lambda x: x[1], reverse=True)

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
    """
    Determine the winner using median score method.
    """
    candidate_scores: "defaultdict[Any, list[Any]]" = defaultdict(list)

    for vote in all_scores:
        for candidate, score in vote.items():
            candidate_scores[candidate].append(score)

    medians = []
    for candidate, scores in candidate_scores.items():
        median = statistics.median(scores) if scores else 0
        medians.append((candidate, median))

    # Sort by median score (descending)
    medians.sort(key=lambda x: x[1], reverse=True)

    return {
        "method": "Median Voting",
        "winner": medians[0][0] if medians else None,
        "details": {candidate: median for candidate, median in medians},
    }


def get_mean_median_hybrid_winner(all_scores: Any) -> Dict[str, Any]:
    """
    Determine the winner using a combination of mean and median scores.
    """
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

    # Sort by combined score (descending)
    results.sort(key=lambda x: x["combined"], reverse=True)

    return {
        "method": "Mean-Median Hybrid",
        "winner": results[0]["candidate"] if results else None,
        "details": results,
    }


def get_variance_based_winner(all_scores: Any) -> Dict[str, Any]:
    """
    Determine the winner considering both average score and variance.
    """
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

    # Sort by weighted score (descending)
    results.sort(key=lambda x: x["weighted_score"], reverse=True)

    return {
        "method": "Variance-Based",
        "winner": results[0]["candidate"] if results else None,
        "details": results,
    }


def get_score_distribution_analysis(all_scores: Any) -> Dict[str, Any]:
    """
    Analyze the distribution of scores for each candidate.
    """
    # Define score bins (0-0.5, 0.5-1, ..., 4.5-5)
    bins = [i * 0.5 for i in range(0, 11)]  # 0, 0.5, 1, ..., 5
    candidate_distributions: "defaultdict[Any, list[int]]" = defaultdict(
        lambda: [0] * (len(bins) - 1)
    )

    for vote in all_scores:
        for candidate, score in vote.items():
            # Find the appropriate bin
            for i in range(len(bins) - 1):
                if bins[i] <= score < bins[i + 1]:
                    candidate_distributions[candidate][i] += 1
                    break

    results = []
    for candidate, distribution in candidate_distributions.items():
        total = sum(distribution)
        percentages = [count / total if total > 0 else 0 for count in distribution]

        # Find mode (most common score range)
        max_index = max(range(len(distribution)), key=lambda i: distribution[i])
        mode_range = f"{bins[max_index]}-{bins[max_index + 1]}"

        results.append(
            {
                "candidate": candidate,
                "distribution": distribution,
                "percentages": percentages,
                "total": total,
                "mode_range": mode_range,
            }
        )

    # Sort by total votes (descending)
    results.sort(key=lambda x: x["total"], reverse=True)

    return {"method": "Score Distribution Analysis", "details": results}


def calculate_bayesian_regret(all_scores: Any) -> Dict[str, Any]:
    """
    Calculate Bayesian regret for each candidate.
    """
    candidate_set: set[Any] = set()
    for vote in all_scores:
        candidate_set.update(vote.keys())
    candidates = list(candidate_set)

    # Calculate utilities (normalized scores)
    utilities: "defaultdict[Any, list[Any]]" = defaultdict(list)
    for vote in all_scores:
        for candidate, score in vote.items():
            # Normalize to 0-1 range
            utilities[candidate].append(score / 5)

    # Calculate expected regret for each candidate
    regrets = []
    for candidate in candidates:
        total_regret = 0

        for vote in all_scores:
            # Find the utility of the voter's most preferred candidate
            best_utility = max(vote.values()) / 5
            current_utility = vote.get(candidate, 0) / 5

            # Regret is the difference between best possible and current
            total_regret += best_utility - current_utility

        avg_regret = total_regret / len(all_scores)
        avg_utility = (
            sum(utilities[candidate]) / len(utilities[candidate])
            if utilities[candidate]
            else 0
        )

        regrets.append(
            {
                "candidate": candidate,
                "avg_utility": avg_utility,
                "avg_regret": avg_regret,
            }
        )

    # Sort by average regret (ascending - lower regret is better)
    regrets.sort(key=lambda x: x["avg_regret"])

    return {
        "method": "Bayesian Regret",
        "winner": regrets[0]["candidate"] if regrets else None,
        "details": regrets,
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


def _mj_median_grade(grade_list: List[int]) -> int:
    """
    Majority Judgment median: the grade at index ceil(n/2) - 1 when sorted.
    For odd n: exact middle.  For even n: lower median (conservative choice).
    """
    if not grade_list:
        return 0
    n = len(grade_list)
    sorted_grades = sorted(grade_list)
    return sorted_grades[(n - 1) // 2]


def _mj_majority_gauge(grade_list: List[int], median: int) -> tuple[float, float]:
    """
    Compute p (fraction strictly above median) and q (fraction strictly below).
    Used for tiebreaking: if p > q the candidate has a "superior majority".
    """
    n = len(grade_list) or 1
    p = sum(1 for g in grade_list if g > median) / n
    q = sum(1 for g in grade_list if g < median) / n
    return p, q


def get_majority_judgment_winner(
    utility_scores: List[Dict[str, float]],
    grade_labels:   List[str] = DEFAULT_MJ_GRADES,
) -> Dict[str, object]:
    """
    Majority Judgment (Balinski & Laraki, 2010).

    Each voter grades each candidate on a 6-level ordinal scale derived
    from their utility score in [0, 1].  The winner is the candidate with
    the highest median grade.  Ties are broken by the majority-gauge rule:
    the candidate whose "superior majority" (fraction above median) exceeds
    their "inferior majority" (fraction below median) wins.  If still tied,
    one median is removed from each tied candidate and the process repeats.

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

    candidate_names: List[str] = list(utility_scores[0].keys())

    # 1. Build grade lists per candidate
    all_grades: Dict[str, List[int]] = {c: [] for c in candidate_names}
    for voter_utils in utility_scores:
        for c, u in voter_utils.items():
            all_grades[c].append(_utility_to_grade(u))

    # 2. Compute median + gauge for each candidate
    medians: Dict[str, int]           = {}
    gauges:  Dict[str, tuple[float, float]] = {}
    for c in candidate_names:
        med         = _mj_median_grade(all_grades[c])
        medians[c]  = med
        gauges[c]   = _mj_majority_gauge(all_grades[c], med)

    # 3. Rank candidates: primary = median (desc), secondary = p-q (desc)
    def _sort_key(c: str) -> tuple[int, float]:
        p, q = gauges[c]
        return (medians[c], p - q)

    ranking = sorted(candidate_names, key=_sort_key, reverse=True)

    # 4. Iterative tiebreak if top-2 are still equal after gauge
    if len(ranking) >= 2:
        a, b = ranking[0], ranking[1]
        if _sort_key(a) == _sort_key(b):
            # Drop one median grade from each and retry (single step suffices
            # for almost all practical cases)
            for cand in (a, b):
                g = all_grades[cand]
                med = medians[cand]
                idx = next((i for i, x in enumerate(sorted(g)) if x == med), None)
                if idx is not None:
                    g_sorted = sorted(g)
                    g_sorted.pop(idx)
                    all_grades[cand] = g_sorted
            for c in (a, b):
                medians[c] = _mj_median_grade(all_grades[c])
                gauges[c]  = _mj_majority_gauge(all_grades[c], medians[c])
            if _sort_key(b) > _sort_key(a):
                ranking[0], ranking[1] = b, a

    winner: Optional[str] = ranking[0] if ranking else None

    # 5. Build grade distribution dicts for frontend visualisation
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

    candidates = list(utility_scores[0].keys())
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


def run_all_score_voting_methods(all_scores: Any) -> Dict[str, Any]:
    """
    Run all score voting methods and return the results.
    """
    results = {
        "simple_score": get_simple_score_winner(all_scores),
        "star_voting": get_star_voting_winner(all_scores),
        "median_voting": get_median_voting_winner(all_scores),
        "mean_median_hybrid": get_mean_median_hybrid_winner(all_scores),
        "variance_based": get_variance_based_winner(all_scores),
        "score_distribution": get_score_distribution_analysis(all_scores),
        "bayesian_regret": calculate_bayesian_regret(all_scores),
    }

    return results
