def validate_vote_weights(votes):
    """
    Validate that the sum of weights for weighted votes equals 100.

    Args:
        votes (list of dict): A list of vote dictionaries containing 'weight'.

    Returns:
        bool: True if the sum of weights is 100, False otherwise.
    """
    total_weight = sum(vote['weight'] for vote in votes if vote['vote_type'] == 'weighted')
    return total_weight == 100

def validate_vote_rating(vote):
    """
    Validate that the rating for a rated vote is between 0 and 5.

    Args:
        vote (dict): A vote dictionary containing 'rating'.

    Returns:
        bool: True if the rating is between 0 and 5, False otherwise.
    """
    return 0 <= vote.get('rating', 0) <= 5

def get_candidate_names(candidates):
    """
    Get a formatted string of candidate names from a list of candidate dictionaries.

    Args:
        candidates (list of dict): A list of candidate dictionaries containing 'first_name' and 'last_name'.

    Returns:
        str: A formatted string of candidate names.
    """
    return ', '.join(f"{candidate['first_name']} {candidate['last_name']}" for candidate in candidates)
