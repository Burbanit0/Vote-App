from collections import defaultdict, Counter
from itertools import combinations
import numpy as np


# return the Condorcet winner
def get_condorcet_winner(votes):
    """
    Determine the Condorcet winner from a set of votes.

    :param votes: A list of votes, where each vote is a dictionary with keys
                  'candidate_id', 'voter_id', and 'rank'.
    :return: The ID of the Condorcet winner, or None if there is
    no Condorcet winner.
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
            # Find the ranks of candidate_1 and candidate_2
            # for the current voter
            rank_1 = next((v.rank for v in votes if v.candidate_id ==
                           candidate_1 and v.voter_id == voter), None)
            rank_2 = next((v.rank for v in votes if v.candidate_id ==
                           candidate_2 and v.voter_id == voter), None)

            if rank_1 is not None and rank_2 is not None:
                if rank_1 < rank_2:
                    wins[(candidate_1, candidate_2)] += 1
                elif rank_2 < rank_1:
                    wins[(candidate_2, candidate_1)] += 1

    # Check if there is a Condorcet winner
    for candidate in candidates:
        if all(wins[(candidate, other)] > wins[(other, candidate)]
                for other in candidates if candidate != other):
            return candidate

    # If no Condorcet winner is found
    return None


# return the winner
def get_two_round_winner(votes):
    """
    Determine the winner of a two-round system from a set of votes.

    :param votes: A list of votes, where each vote is a dictionary with keys
                  'candidate_id', 'voter_id', and 'rank'.
    :return: The ID of the winner.
    """
    # Count the first-choice votes for each candidate
    first_choice_votes = Counter()
    for vote in votes:
        if vote.rank == 1:
            first_choice_votes[vote.candidate_id] += 1

    # Determine the total number of voters
    total_voters = len(set(vote.voter_id for vote in votes))

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
        if vote.candidate_id in (candidate_1, candidate_2):
            second_round_votes[vote.candidate_id] += 1

    # Determine the winner of the second round
    winner = max(second_round_votes, key=second_round_votes.get)
    return winner


def bucklin_voting(votes):
    # Group votes by candidate_id and rank
    candidate_votes = defaultdict(lambda: defaultdict(int))
    for vote in votes:
        candidate_id = vote['candidate_id']
        rank = vote['rank']
        candidate_votes[candidate_id][rank] += 1

    # Determine the total number of voters
    total_voters = len(set(vote['voter_id'] for vote in votes))

    # Determine the majority threshold
    majority = total_voters // 2 + 1

    # Accumulate votes by rank
    accumulated_votes = defaultdict(int)
    for rank in sorted(set(vote['rank'] for vote in votes)):
        for candidate_id in candidate_votes:
            accumulated_votes[candidate_id] += \
                candidate_votes[candidate_id][rank]
            if accumulated_votes[candidate_id] >= majority:
                return candidate_id

    # If no candidate achieves a majority, return the candidate with
    # the most accumulated votes
    return max(accumulated_votes, key=accumulated_votes.get)


# Getting the intermediate candidates
def two_round_system(votes):
    # Group votes by candidate_id and count their first-choice votes
    first_choice_votes = defaultdict(int)
    for vote in votes:
        if vote['rank'] == 1:
            first_choice_votes[vote['candidate_id']] += 1

    # Determine the total number of voters
    total_voters = len(set(vote['voter_id'] for vote in votes))

    # Determine the majority threshold
    majority = total_voters // 2 + 1

    # Check if any candidate has a majority in the first round
    first_round_results = list(first_choice_votes.items())
    first_round_results.sort(key=lambda x: x[1], reverse=True)

    if first_round_results[0][1] >= majority:
        # A candidate has a majority in the first round
        return first_round_results[0][0], []

    # If no majority, proceed to the second round with the top two candidates
    top_two_candidates = [candidate_id for candidate_id, _
                          in first_round_results[:2]]

    # Count votes for the top two candidates in the second round
    second_round_votes = defaultdict(int)
    for vote in votes:
        if vote['candidate_id'] in top_two_candidates:
            second_round_votes[vote['candidate_id']] += 1

    # Determine the winner of the second round
    second_round_winner = max(second_round_votes, key=second_round_votes.get)

    return second_round_winner, top_two_candidates


def schulze_method(votes):
    # Group votes by voter_id
    voter_preferences = defaultdict(list)
    for vote in votes:
        voter_preferences[vote['voter_id']].append((vote['candidate_id'],
                                                    vote['rank']))

    # Sort preferences by rank for each voter
    for voter_id in voter_preferences:
        voter_preferences[voter_id].sort(key=lambda x: x[1])

    # Extract unique candidate IDs
    candidates = sorted(set(vote['candidate_id'] for vote in votes))
    candidate_indices = {candidate: index for index, candidate
                         in enumerate(candidates)}

    # Initialize the pairwise preference matrix
    num_candidates = len(candidates)
    preference_matrix = np.zeros((num_candidates, num_candidates), dtype=int)

    # Fill the preference matrix
    for voter_id, preferences in voter_preferences.items():
        for i in range(len(preferences)):
            for j in range(i + 1, len(preferences)):
                pref_candidate = preferences[i][0]
                less_pref_candidate = preferences[j][0]
                preference_matrix[candidate_indices[pref_candidate],
                                  candidate_indices[less_pref_candidate]] += 1

    # Calculate the strength of preferences
    strength_matrix = np.zeros((num_candidates, num_candidates), dtype=int)
    for i, j in combinations(range(num_candidates), 2):
        if preference_matrix[i, j] > preference_matrix[j, i]:
            strength_matrix[i, j] = preference_matrix[i, j]
        elif preference_matrix[i, j] < preference_matrix[j, i]:
            strength_matrix[j, i] = preference_matrix[j, i]

    # Floyd-Warshall algorithm to find the strongest paths
    for i, j in combinations(range(num_candidates), 2):
        if strength_matrix[i, j] == 0 and strength_matrix[j, i] == 0:
            strength_matrix[i, j] = strength_matrix[j, i] = max(
                preference_matrix[i, j], preference_matrix[j, i])

    for i, k, j in combinations(range(num_candidates), 3):
        if strength_matrix[i, j] < min(strength_matrix[i, k],
                                       strength_matrix[k, j]):
            strength_matrix[i, j] = min(strength_matrix[i, k],
                                        strength_matrix[k, j])

    # Determine the winner
    wins = np.sum(strength_matrix > strength_matrix.T, axis=1)
    winner_index = np.argmax(wins)

    return candidates[winner_index]


# Using the rating poart of the votes
def score_voting(votes):
    # Group votes by candidate_id and sum their ratings
    candidate_scores = defaultdict(float)
    candidate_counts = defaultdict(int)

    for vote in votes:
        candidate_id = vote['candidate_id']
        rating = vote['rating']
        candidate_scores[candidate_id] += rating
        candidate_counts[candidate_id] += 1

    # Calculate average scores
    average_scores = {candidate: total_score / candidate_counts[candidate]
                      for candidate, total_score in candidate_scores.items()}

    # Determine the winner
    winner = max(average_scores, key=average_scores.get)

    return winner
