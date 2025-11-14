from collections import defaultdict
import math
import statistics


def get_simple_score_winner(all_scores):
    """
    Determine the winner using simple score sum/average method.
    """
    candidate_scores = defaultdict(lambda: {"sum": 0, "count": 0})

    for vote in all_scores:
        for candidate, score in vote["scores"].items():
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


def get_star_voting_winner(all_scores):
    """
    Determine the winner using STAR (Score Then Automatic Runoff) voting.
    """
    # First round: calculate average scores
    candidate_scores = defaultdict(lambda: {"sum": 0, "count": 0})

    for vote in all_scores:
        for candidate, score in vote["scores"].items():
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
        score1 = vote["scores"].get(candidate1, 0)
        score2 = vote["scores"].get(candidate2, 0)

        if score1 > score2:
            votes1 += 1
        elif score2 > score1:
            votes2 += 1
        else:
            tied += 1

    runoff_winner = candidate1 if votes1 > votes2 else candidate2

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


def get_median_voting_winner(all_scores):
    """
    Determine the winner using median score method.
    """
    candidate_scores = defaultdict(list)

    for vote in all_scores:
        for candidate, score in vote["scores"].items():
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


def get_mean_median_hybrid_winner(all_scores):
    """
    Determine the winner using a combination of mean and median scores.
    """
    candidate_stats = defaultdict(lambda: {"sum": 0, "count": 0, "scores": []})

    for vote in all_scores:
        for candidate, score in vote["scores"].items():
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


def get_variance_based_winner(all_scores):
    """
    Determine the winner considering both average score and variance.
    """
    candidate_stats = defaultdict(lambda: {"sum": 0, "sum_sq": 0, "count": 0})

    for vote in all_scores:
        for candidate, score in vote["scores"].items():
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
        std_dev = math.sqrt(variance) if variance >= 0 else 0

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


def get_score_distribution_analysis(all_scores):
    """
    Analyze the distribution of scores for each candidate.
    """
    # Define score bins (0-0.5, 0.5-1, ..., 4.5-5)
    bins = [i * 0.5 for i in range(0, 11)]  # 0, 0.5, 1, ..., 5
    candidate_distributions = defaultdict(lambda: [0] * (len(bins) - 1))

    for vote in all_scores:
        for candidate, score in vote["scores"].items():
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


def calculate_bayesian_regret(all_scores):
    """
    Calculate Bayesian regret for each candidate.
    """
    candidates = set()
    for vote in all_scores:
        candidates.update(vote["scores"].keys())
    candidates = list(candidates)

    # Calculate utilities (normalized scores)
    utilities = defaultdict(list)
    for vote in all_scores:
        for candidate, score in vote["scores"].items():
            # Normalize to 0-1 range
            utilities[candidate].append(score / 5)

    # Calculate expected regret for each candidate
    regrets = []
    for candidate in candidates:
        total_regret = 0

        for vote in all_scores:
            # Find the utility of the voter's most preferred candidate
            best_utility = max(vote["scores"].values()) / 5
            current_utility = vote["scores"].get(candidate, 0) / 5

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


def run_all_score_voting_methods(all_scores):
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
