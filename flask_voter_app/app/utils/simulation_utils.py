from collections import defaultdict, Counter
from itertools import combinations
import random
from typing import List, Dict


def simulate_votes(num_voters: int, num_candidates: int) -> List[Dict[str,
                                                                      int]]:
    """
    Simulate random votes for a given number of voters and candidates.

    :param num_voters: The number of voters.
    :param num_candidates: The number of candidates.
    :return: A list of simulated votes.
    """
    votes = []

    for voter_id in range(1, num_voters + 1):
        preferences = list(range(1, num_candidates + 1))
        random.shuffle(preferences)

        for rank, candidate_id in enumerate(preferences, start=1):
            votes.append({
                'voter_id': voter_id,
                'candidate_id': candidate_id,
                'rank': rank
            })

    return votes


def get_condorcet_winner(votes: List[Dict[str, int]]) -> int:
    """
    Determine the Condorcet winner from a set of votes.

    :param votes: A list of votes, where each vote is a dictionary with keys
                  'candidate_id', 'voter_id', and 'rank'.
    :return: The ID of the Condorcet winner, or None if there is no
    Condorcet winner.
    """
    candidates = set(vote['candidate_id'] for vote in votes)
    voters = set(vote['voter_id'] for vote in votes)
    wins = defaultdict(int)

    for candidate_1, candidate_2 in combinations(candidates, 2):
        for voter in voters:
            rank_1 = next((v['rank'] for v in votes if v['candidate_id'] ==
                           candidate_1 and v['voter_id'] == voter), None)
            rank_2 = next((v['rank'] for v in votes if v['candidate_id'] ==
                           candidate_2 and v['voter_id'] == voter), None)

            if rank_1 is not None and rank_2 is not None:
                if rank_1 < rank_2:
                    wins[(candidate_1, candidate_2)] += 1
                elif rank_2 < rank_1:
                    wins[(candidate_2, candidate_1)] += 1

    for candidate in candidates:
        if all(wins[(candidate, other)] > wins[(other, candidate)] for other
               in candidates if candidate != other):
            return candidate

    return None


def get_two_round_winner(votes: List[Dict[str, int]]) -> int:
    """
    Determine the winner of a two-round system from a set of votes.

    :param votes: A list of votes, where each vote is a dictionary with keys
                  'candidate_id', 'voter_id', and 'rank'.
    :return: The ID of the winner.
    """
    # Count the first-choice votes for each candidate
    first_choice_votes = Counter()
    for vote in votes:
        if vote['rank'] == 1:
            first_choice_votes[vote['candidate_id']] += 1

    # Determine the total number of voters
    total_voters = len(set(vote['voter_id'] for vote in votes))

    # Check if any candidate has a majority in the first round
    majority = total_voters // 2
    for candidate, count in first_choice_votes.items():
        if count > majority:
            return candidate

    # If no majority, proceed to the second round with the top two candidates
    top_two_candidates = first_choice_votes.most_common(2)
    candidate_1, candidate_2 = top_two_candidates[0][0],
    top_two_candidates[1][0]

    # Count the votes for the top two candidates in the second round
    second_round_votes = Counter()
    for vote in votes:
        if vote['candidate_id'] in (candidate_1, candidate_2):
            second_round_votes[vote['candidate_id']] += 1

    # Determine the winner of the second round
    winner = max(second_round_votes, key=second_round_votes.get)
    return winner
