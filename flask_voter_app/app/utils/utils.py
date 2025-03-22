from collections import defaultdict
from itertools import combinations

def get_condorcet_winner(votes):
    """
    Determine the Condorcet winner from a set of votes.

    :param votes: A list of votes, where each vote is a dictionary with keys
                  'candidate_id', 'voter_id', and 'rank'.
    :return: The ID of the Condorcet winner, or None if there is no Condorcet winner.
    """
    # Extract unique candidates and voters
    candidates = set(vote.candidate_id for vote in votes)
    voters = set(vote.voter_id for vote in votes)

    # Initialize a dictionary to store the head-to-head wins
    wins = defaultdict(int)

    # Compare each pair of candidates
    for candidate_1, candidate_2 in combinations(candidates, 2):
        # Count the number of voters who prefer candidate_1 over candidate_2
        for voter in voters:
            # Find the ranks of candidate_1 and candidate_2 for the current voter
            rank_1 = next((v.rank for v in votes if v.candidate_id == candidate_1 and v.voter_id == voter), None)
            rank_2 = next((v.rank for v in votes if v.candidate_id == candidate_2 and v.voter_id == voter), None)

            if rank_1 is not None and rank_2 is not None:
                if rank_1 < rank_2:
                    wins[(candidate_1, candidate_2)] += 1
                elif rank_2 < rank_1:
                    wins[(candidate_2, candidate_1)] += 1

    # Check if there is a Condorcet winner
    for candidate in candidates:
        if all(wins[(candidate, other)] > wins[(other, candidate)] for other in candidates if candidate != other):
            return candidate

    # If no Condorcet winner is found
    return None