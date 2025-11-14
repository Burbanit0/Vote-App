from collections import defaultdict, Counter
from itertools import combinations, permutations


def get_condorcet_winner(votes: list) -> str:
    """
    Determine the Condorcet winner from a set of rankings.
    :param votes: A list of rankings, where each ranking is either:
                  1. A dictionary with 'ranking' (list of candidate names) and
                  'voter_id', or
                  2. A list of candidate names (ranking)
    :return: The name of the Condorcet winner, or None if there is no
                  Condorcet winner.
    """
    # Get all unique candidates
    candidates = set()

    # Determine if votes are dictionaries or lists
    is_dict_format = isinstance(votes[0], dict) if votes else False

    for vote in votes:
        if is_dict_format:
            candidates.update(vote["ranking"])
        else:
            candidates.update(vote)

    # Count pairwise wins
    wins = defaultdict(int)

    for candidate_1, candidate_2 in combinations(candidates, 2):
        for vote in votes:
            if is_dict_format:
                ranking = vote["ranking"]
            else:
                ranking = vote

            rank_1 = (
                ranking.index(candidate_1) if candidate_1 in ranking else float("inf")
            )
            rank_2 = (
                ranking.index(candidate_2) if candidate_2 in ranking else float("inf")
            )

            if rank_1 < rank_2:
                wins[(candidate_1, candidate_2)] += 1
            elif rank_2 < rank_1:
                wins[(candidate_2, candidate_1)] += 1

    # Check for a Condorcet winner
    for candidate in candidates:
        if all(
            wins.get((candidate, other), 0) > wins.get((other, candidate), 0)
            for other in candidates
            if other != candidate
        ):
            return candidate

    return None


def get_two_round_winner(votes: list) -> str:
    """
    Determine the winner of a two-round system from a set of rankings.
    :param votes: A list of rankings (see get_condorcet_winner for format)
    :return: The name of the winner.
    """
    # Determine format
    is_dict_format = isinstance(votes[0], dict) if votes else False

    # Count the first-choice votes for each candidate
    first_choice_votes = Counter()
    for vote in votes:
        if is_dict_format:
            ranking = vote["ranking"]
        else:
            ranking = vote

        if ranking:
            first_choice_votes[ranking[0]] += 1

    # Determine the total number of voters
    total_voters = len(votes)

    # Check if any candidate has a majority in the first round
    majority = total_voters // 2
    for candidate, count in first_choice_votes.items():
        if count > majority:
            return candidate

    # If no majority, proceed to the second round with the top two candidates
    top_two_candidates = [
        candidate for candidate, _ in first_choice_votes.most_common(2)
    ]

    # Count the votes for the top two candidates in the second round
    second_round_votes = Counter()
    for vote in votes:
        if is_dict_format:
            ranking = vote["ranking"]
        else:
            ranking = vote

        # Find the highest-ranked candidate among the top two
        for candidate in ranking:
            if candidate in top_two_candidates:
                second_round_votes[candidate] += 1
                break  # Only count the highest-ranked of the top two

    # Determine the winner of the second round
    winner = max(second_round_votes, key=second_round_votes.get)
    return winner


def get_borda_winner(votes: list) -> str:
    """
    Determine the Borda count winner from a set of rankings.
    :param votes: A list of rankings (see get_condorcet_winner for format)
    :return: The name of the Borda winner
    """
    # Determine format
    is_dict_format = isinstance(votes[0], dict) if votes else False

    candidates = set()
    for vote in votes:
        if is_dict_format:
            ranking = vote["ranking"]
        else:
            ranking = vote
        candidates.update(ranking)

    scores = defaultdict(int)

    for vote in votes:
        if is_dict_format:
            ranking = vote["ranking"]
        else:
            ranking = vote

        num_candidates = len(ranking)
        for position, candidate in enumerate(ranking):
            # Assign points: last place gets 0, second last gets 1, etc.
            scores[candidate] += num_candidates - 1 - position

    return max(scores.items(), key=lambda x: x[1])[0]


def get_plurality_winner(votes: list) -> str:
    """
    Determine the plurality winner from a set of rankings.
    :param votes: A list of rankings (see get_condorcet_winner for format)
    :return: The name of the plurality winner
    """
    # Determine format
    is_dict_format = isinstance(votes[0], dict) if votes else False

    first_choice_votes = Counter()
    for vote in votes:
        if is_dict_format:
            ranking = vote["ranking"]
        else:
            ranking = vote

        if ranking:
            first_choice_votes[ranking[0]] += 1

    return max(first_choice_votes.items(), key=lambda x: x[1])[0]


def get_approval_winner(votes: list, approval_threshold: int = 2) -> str:
    """
    Determine the approval voting winner from a set of rankings.
    :param votes: A list of rankings (see get_condorcet_winner for format)
    :param approval_threshold: Number of top candidates to approve (default: 2)
    :return: The name of the approval voting winner
    """
    # Determine format
    is_dict_format = isinstance(votes[0], dict) if votes else False

    approval_votes = Counter()

    for vote in votes:
        if is_dict_format:
            ranking = vote["ranking"]
        else:
            ranking = vote

        # Approve top N candidates
        approved = ranking[:approval_threshold]
        for candidate in approved:
            approval_votes[candidate] += 1

    return max(approval_votes.items(), key=lambda x: x[1])[0]


def get_irv_winner(votes: list) -> str:
    """
    Determine the Instant Runoff Voting winner from a set of rankings.
    :param votes: A list of rankings (see get_condorcet_winner for format)
    :return: The name of the IRV winner
    """
    # Determine format
    is_dict_format = isinstance(votes[0], dict) if votes else False

    candidates = set()
    for vote in votes:
        if is_dict_format:
            ranking = vote["ranking"]
        else:
            ranking = vote
        candidates.update(ranking)

    while len(candidates) > 1:
        # Count first-choice votes
        votes_count = Counter()
        for vote in votes:
            if is_dict_format:
                ranking = vote["ranking"]
            else:
                ranking = vote

            for candidate in ranking:
                if candidate in candidates:
                    votes_count[candidate] += 1
                    break  # Only count first valid choice

        # Check for majority winner
        total_votes = sum(votes_count.values())
        majority = total_votes / 2

        for candidate, count in votes_count.items():
            if count > majority:
                return candidate

        # Eliminate candidate(s) with fewest votes
        min_votes = min(votes_count.values())
        eliminated = [c for c, v in votes_count.items() if v == min_votes]

        # If tie for elimination, eliminate all tied candidates
        for candidate in eliminated:
            candidates.remove(candidate)

    return candidates.pop()  # Return the last remaining candidate


def get_coombs_winner(votes: list) -> str:
    """
    Determine the Coombs' method winner from a set of rankings.
    :param votes: A list of rankings (see get_condorcet_winner for format)
    :return: The name of the Coombs' winner
    """
    # Determine format
    is_dict_format = isinstance(votes[0], dict) if votes else False

    candidates = set()
    for vote in votes:
        if is_dict_format:
            ranking = vote["ranking"]
        else:
            ranking = vote
        candidates.update(ranking)

    while len(candidates) > 1:
        # Count last-choice votes
        last_choices = Counter()
        for vote in votes:
            if is_dict_format:
                ranking = vote["ranking"]
            else:
                ranking = vote

            # Find the lowest-ranked remaining candidate
            for candidate in reversed(ranking):
                if candidate in candidates:
                    last_choices[candidate] += 1
                    break

        # Eliminate candidate(s) with most last-place votes
        max_last_choices = max(last_choices.values())
        eliminated = [c for c, v in last_choices.items() if v == max_last_choices]

        # If tie for elimination, eliminate all tied candidates
        for candidate in eliminated:
            candidates.remove(candidate)

    return candidates.pop()  # Return the last remaining candidate


def get_score_winner(votes: list) -> str:
    """
    Determine the score voting winner from a set of rankings.
    :param votes: A list of rankings (see get_condorcet_winner for format)
    :return: The name of the score voting winner
    """
    # Determine format
    is_dict_format = isinstance(votes[0], dict) if votes else False

    scores = defaultdict(float)

    for vote in votes:
        if is_dict_format:
            ranking = vote["ranking"]
        else:
            ranking = vote

        num_candidates = len(ranking)
        for position, candidate in enumerate(ranking):
            # Assign scores from 0 (worst) to 1 (best)
            score = 1 - (position / (num_candidates - 1)) if num_candidates > 1 else 1
            scores[candidate] += score

    return max(scores.items(), key=lambda x: x[1])[0]


def get_kemeny_young_winner(votes: list) -> str:
    """
    Determine the Kemeny-Young winner from a set of rankings.
    :param votes: A list of rankings (see get_condorcet_winner for format)
    :return: The name of the Kemeny-Young winner
    """
    # Determine format
    is_dict_format = isinstance(votes[0], dict) if votes else False

    candidates = set()
    for vote in votes:
        if is_dict_format:
            ranking = vote["ranking"]
        else:
            ranking = vote
        candidates.update(ranking)
    candidates = list(candidates)

    # Generate all possible complete rankings
    all_rankings = list(permutations(candidates))

    def ranking_distance(r1, r2):
        """Calculate the Kendall tau distance between two rankings"""
        # Convert to dictionaries for position lookup
        pos1 = {c: i for i, c in enumerate(r1)}
        pos2 = {c: i for i, c in enumerate(r2)}

        # Count the number of pairs in different order
        distance = 0
        for i, j in combinations(range(len(r1)), 2):
            if (pos1[r1[i]] < pos1[r1[j]]) != (pos2[r1[i]] < pos2[r1[j]]):
                distance += 1
        return distance

    # Calculate the total distance for each possible ranking
    min_distance = float("inf")
    best_ranking = None

    for candidate_ranking in all_rankings:
        total_distance = 0
        for vote in votes:
            if is_dict_format:
                ranking = vote["ranking"]
            else:
                ranking = vote
            total_distance += ranking_distance(candidate_ranking, ranking)

        if total_distance < min_distance:
            min_distance = total_distance
            best_ranking = candidate_ranking

    return best_ranking[0]  # Return the top candidate in the best ranking


def get_bucklin_winner(votes: list) -> str:
    """
    Determine the Bucklin voting winner from a set of rankings.
    :param votes: A list of rankings (see get_condorcet_winner for format)
    :return: The name of the Bucklin winner
    """
    # Determine format
    is_dict_format = isinstance(votes[0], dict) if votes else False

    candidates = set()
    for vote in votes:
        if is_dict_format:
            ranking = vote["ranking"]
        else:
            ranking = vote
        candidates.update(ranking)

    max_rank = max(len(vote["ranking"] if is_dict_format else vote) for vote in votes)

    for rank in range(1, max_rank + 1):
        votes_count = Counter()
        for vote in votes:
            if is_dict_format:
                ranking = vote["ranking"]
            else:
                ranking = vote

            if len(ranking) >= rank:
                votes_count[ranking[rank - 1]] += 1

        majority = len(votes) / 2
        winners = [c for c, v in votes_count.items() if v > majority]

        if winners:
            return winners[0]  # Return the first winner if there's a tie

    # If no majority found at any rank, return the candidate with most votes
    # at the last rank
    return max(votes_count.items(), key=lambda x: x[1])[0]


def get_minimax_winner(votes: list) -> str:
    """
    Determine the Minimax winner from a set of rankings.
    :param votes: A list of rankings (see get_condorcet_winner for format)
    :return: The name of the Minimax winner
    """
    # Determine format
    is_dict_format = isinstance(votes[0], dict) if votes else False

    candidates = set()
    for vote in votes:
        if is_dict_format:
            ranking = vote["ranking"]
        else:
            ranking = vote
        candidates.update(ranking)

    # Calculate pairwise opposition
    opposition = defaultdict(int)
    for c1, c2 in combinations(candidates, 2):
        for vote in votes:
            if is_dict_format:
                ranking = vote["ranking"]
            else:
                ranking = vote

            pos1 = ranking.index(c1) if c1 in ranking else float("inf")
            pos2 = ranking.index(c2) if c2 in ranking else float("inf")
            if pos2 < pos1:  # c2 is preferred over c1
                opposition[(c1, c2)] += 1

    # Find the maximum opposition for each candidate
    max_opposition = {}
    for candidate in candidates:
        max_opposition[candidate] = max(
            opposition.get((candidate, other), 0)
            for other in candidates
            if other != candidate
        )

    # Return the candidate with the smallest maximum opposition
    return min(max_opposition.items(), key=lambda x: x[1])[0]


def get_schulze_winner(votes: list) -> str:
    """
    Determine the Schulze method winner from a set of rankings.
    :param votes: A list of rankings (see get_condorcet_winner for format)
    :return: The name of the Schulze winner
    """
    # Determine format
    is_dict_format = isinstance(votes[0], dict) if votes else False

    candidates = set()
    for vote in votes:
        if is_dict_format:
            ranking = vote["ranking"]
        else:
            ranking = vote
        candidates.update(ranking)

    # Initialize pairwise preference matrix
    pref = defaultdict(lambda: defaultdict(int))
    for c1, c2 in combinations(candidates, 2):
        for vote in votes:
            if is_dict_format:
                ranking = vote["ranking"]
            else:
                ranking = vote

            pos1 = ranking.index(c1) if c1 in ranking else float("inf")
            pos2 = ranking.index(c2) if c2 in ranking else float("inf")
            if pos1 < pos2:
                pref[c1][c2] += 1

    # Calculate the strength of the strongest paths
    strength = defaultdict(lambda: defaultdict(int))
    for c1, c2 in combinations(candidates, 2):
        if c1 != c2:
            strength[c1][c2] = pref[c1][c2]

    for c1, c2, c3 in permutations(candidates, 3):
        strength[c1][c2] = max(
            strength[c1][c2], min(strength[c1][c3], strength[c3][c2])
        )

    # Find the Schulze winner
    wins = defaultdict(int)
    for c1, c2 in combinations(candidates, 2):
        if strength[c1][c2] > strength[c2][c1]:
            wins[c1] += 1

    return max(wins.items(), key=lambda x: x[1])[0]
