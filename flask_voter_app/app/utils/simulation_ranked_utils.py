from collections import defaultdict, Counter
from itertools import combinations, permutations
from typing import Optional


def _is_dict_format(votes: list) -> bool:
    """Return True when votes are dicts with a 'ranking' key, False for plain lists."""
    return bool(votes) and isinstance(votes[0], dict)


def _get_ranking(vote, is_dict: bool) -> list:
    """Extract the ranking list from a vote regardless of format."""
    return vote["ranking"] if is_dict else vote


def get_condorcet_winner(votes: list) -> Optional[str]:
    """
    Determine the Condorcet winner from a set of rankings.
    :param votes: A list of rankings, where each ranking is either:
                  1. A dictionary with 'ranking' (list of candidate names) and
                  'voter_id', or
                  2. A list of candidate names (ranking)
    :return: The name of the Condorcet winner, or None if there is no
                  Condorcet winner.
    """
    if not votes:
        return None
    is_dict = _is_dict_format(votes)
    candidates = set()
    for vote in votes:
        candidates.update(_get_ranking(vote, is_dict))

    wins = defaultdict(int)
    for candidate_1, candidate_2 in combinations(candidates, 2):
        for vote in votes:
            ranking = _get_ranking(vote, is_dict)
            rank_1 = ranking.index(candidate_1) if candidate_1 in ranking else float("inf")
            rank_2 = ranking.index(candidate_2) if candidate_2 in ranking else float("inf")
            if rank_1 < rank_2:
                wins[(candidate_1, candidate_2)] += 1
            elif rank_2 < rank_1:
                wins[(candidate_2, candidate_1)] += 1

    for candidate in candidates:
        if all(
            wins.get((candidate, other), 0) > wins.get((other, candidate), 0)
            for other in candidates
            if other != candidate
        ):
            return candidate
    return None


def get_two_round_winner(votes: list) -> Optional[str]:
    """
    Determine the winner of a two-round system from a set of rankings.
    :param votes: A list of rankings (see get_condorcet_winner for format)
    :return: The name of the winner.
    """
    if not votes:
        return None
    is_dict = _is_dict_format(votes)

    first_choice_votes = Counter()
    for vote in votes:
        ranking = _get_ranking(vote, is_dict)
        if ranking:
            first_choice_votes[ranking[0]] += 1

    majority = len(votes) // 2
    for candidate, count in first_choice_votes.items():
        if count > majority:
            return candidate

    top_two_candidates = [c for c, _ in first_choice_votes.most_common(2)]

    second_round_votes = Counter()
    for vote in votes:
        ranking = _get_ranking(vote, is_dict)
        for candidate in ranking:
            if candidate in top_two_candidates:
                second_round_votes[candidate] += 1
                break

    if not second_round_votes:
        return None
    return max(second_round_votes, key=second_round_votes.get)


def get_borda_winner(votes: list) -> Optional[str]:
    """
    Determine the Borda count winner from a set of rankings.
    :param votes: A list of rankings (see get_condorcet_winner for format)
    :return: The name of the Borda winner
    """
    if not votes:
        return None
    is_dict = _is_dict_format(votes)
    scores = defaultdict(int)
    for vote in votes:
        ranking = _get_ranking(vote, is_dict)
        num_candidates = len(ranking)
        for position, candidate in enumerate(ranking):
            scores[candidate] += num_candidates - 1 - position
    if not scores:
        return None
    return max(scores.items(), key=lambda x: x[1])[0]


def get_plurality_winner(votes: list) -> Optional[str]:
    """
    Determine the plurality winner from a set of rankings.
    :param votes: A list of rankings (see get_condorcet_winner for format)
    :return: The name of the plurality winner
    """
    if not votes:
        return None
    is_dict = _is_dict_format(votes)
    first_choice_votes = Counter()
    for vote in votes:
        ranking = _get_ranking(vote, is_dict)
        if ranking:
            first_choice_votes[ranking[0]] += 1
    if not first_choice_votes:
        return None
    return max(first_choice_votes.items(), key=lambda x: x[1])[0]


def get_approval_winner(
    votes: list,
    approval_threshold: int = 2,
    utility_scores: dict = None,
) -> Optional[str]:
    """
    Determine the approval voting winner from a set of rankings.
    :param votes: A list of rankings (see get_condorcet_winner for format)
    :param approval_threshold: Number of top candidates to approve when
        utility_scores is not provided (default: 2)
    :param utility_scores: Optional dict {voter_id: {candidate_name: float}}.
        When provided, each voter approves every candidate whose utility
        exceeds their personal mean utility (sincere threshold model).
        The votes list must then be in dict format with a 'voter_id' key.
    :return: The name of the approval voting winner
    """
    if not votes:
        return None

    approval_votes = Counter()

    if utility_scores is not None:
        # Sincere approval: approve candidates above the voter's mean utility.
        for vote in votes:
            voter_id = vote["voter_id"] if isinstance(vote, dict) else None
            if voter_id is None or voter_id not in utility_scores:
                continue
            u = utility_scores[voter_id]
            if not u:
                continue
            threshold = sum(u.values()) / len(u)
            for candidate, score in u.items():
                if score > threshold:
                    approval_votes[candidate] += 1
    else:
        # Backward-compatible path: approve the top N from the ranking.
        is_dict = _is_dict_format(votes)
        for vote in votes:
            ranking = _get_ranking(vote, is_dict)
            for candidate in ranking[:approval_threshold]:
                approval_votes[candidate] += 1

    if not approval_votes:
        return None
    return max(approval_votes.items(), key=lambda x: x[1])[0]


def get_approval_winner_sincere(utility_scores: dict) -> str:
    """
    Convenience wrapper that runs approval voting in sincere mode.
    Expects utility_scores as {voter_id: {candidate_name: float}}.
    Builds the votes list internally so callers do not need to maintain
    a parallel rankings list.
    """
    votes = [{"voter_id": voter_id} for voter_id in utility_scores]
    return get_approval_winner(votes, utility_scores=utility_scores)


def get_irv_winner(votes: list) -> Optional[str]:
    """
    Determine the Instant Runoff Voting winner from a set of rankings.
    :param votes: A list of rankings (see get_condorcet_winner for format)
    :return: The name of the IRV winner
    """
    if not votes:
        return None
    is_dict = _is_dict_format(votes)
    candidates = set()
    for vote in votes:
        candidates.update(_get_ranking(vote, is_dict))

    while len(candidates) > 1:
        votes_count = Counter()
        for vote in votes:
            ranking = _get_ranking(vote, is_dict)
            for candidate in ranking:
                if candidate in candidates:
                    votes_count[candidate] += 1
                    break

        total_votes = sum(votes_count.values())
        majority = total_votes / 2
        for candidate, count in votes_count.items():
            if count > majority:
                return candidate

        if not votes_count:
            break
        min_votes = min(votes_count.values())
        for candidate in [c for c, v in votes_count.items() if v == min_votes]:
            candidates.remove(candidate)

    return candidates.pop() if candidates else None


def get_coombs_winner(votes: list) -> Optional[str]:
    """
    Determine the Coombs' method winner from a set of rankings.
    :param votes: A list of rankings (see get_condorcet_winner for format)
    :return: The name of the Coombs' winner
    """
    if not votes:
        return None
    is_dict = _is_dict_format(votes)
    candidates = set()
    for vote in votes:
        candidates.update(_get_ranking(vote, is_dict))

    while len(candidates) > 1:
        last_choices = Counter()
        for vote in votes:
            ranking = _get_ranking(vote, is_dict)
            for candidate in reversed(ranking):
                if candidate in candidates:
                    last_choices[candidate] += 1
                    break

        if not last_choices:
            break
        max_last = max(last_choices.values())
        for candidate in [c for c, v in last_choices.items() if v == max_last]:
            candidates.remove(candidate)

    return candidates.pop() if candidates else None


def get_positional_score_winner(votes: list) -> Optional[str]:
    """
    Determine the winner using positional scoring derived from rankings.
    Each candidate receives a score proportional to their rank position
    (1 = best, 0 = worst), normalised across the number of candidates.
    :param votes: A list of rankings (see get_condorcet_winner for format)
    :return: The name of the winner
    """
    if not votes:
        return None
    is_dict = _is_dict_format(votes)
    scores = defaultdict(float)
    for vote in votes:
        ranking = _get_ranking(vote, is_dict)
        num_candidates = len(ranking)
        for position, candidate in enumerate(ranking):
            scores[candidate] += 1 - (position / (num_candidates - 1)) if num_candidates > 1 else 1
    if not scores:
        return None
    return max(scores.items(), key=lambda x: x[1])[0]


# Backward-compatible alias used by existing route code.
get_score_winner = get_positional_score_winner


def get_kemeny_young_winner(votes: list) -> Optional[str]:
    """
    Determine the Kemeny-Young winner from a set of rankings.
    :param votes: A list of rankings (see get_condorcet_winner for format)
    :return: The name of the Kemeny-Young winner
    """
    if not votes:
        return None
    is_dict = _is_dict_format(votes)
    candidates = set()
    for vote in votes:
        candidates.update(_get_ranking(vote, is_dict))
    candidates = list(candidates)

    all_rankings = list(permutations(candidates))

    def ranking_distance(r1, r2):
        pos1 = {c: i for i, c in enumerate(r1)}
        pos2 = {c: i for i, c in enumerate(r2)}
        return sum(
            1
            for i, j in combinations(range(len(r1)), 2)
            if (pos1[r1[i]] < pos1[r1[j]]) != (pos2[r1[i]] < pos2[r1[j]])
        )

    min_distance = float("inf")
    best_ranking = None
    for candidate_ranking in all_rankings:
        total_distance = sum(
            ranking_distance(candidate_ranking, _get_ranking(vote, is_dict))
            for vote in votes
        )
        if total_distance < min_distance:
            min_distance = total_distance
            best_ranking = candidate_ranking

    return best_ranking[0] if best_ranking else None


def get_bucklin_winner(votes: list) -> Optional[str]:
    """
    Determine the Bucklin voting winner from a set of rankings.
    :param votes: A list of rankings (see get_condorcet_winner for format)
    :return: The name of the Bucklin winner
    """
    if not votes:
        return None
    is_dict = _is_dict_format(votes)
    max_rank = max(len(_get_ranking(vote, is_dict)) for vote in votes)
    majority = len(votes) / 2
    votes_count: Counter = Counter()

    for rank in range(1, max_rank + 1):
        votes_count = Counter()
        for vote in votes:
            ranking = _get_ranking(vote, is_dict)
            if len(ranking) >= rank:
                votes_count[ranking[rank - 1]] += 1

        winners = [c for c, v in votes_count.items() if v > majority]
        if winners:
            return winners[0]

    return max(votes_count.items(), key=lambda x: x[1])[0] if votes_count else None


def get_minimax_winner(votes: list) -> Optional[str]:
    """
    Determine the Minimax winner from a set of rankings.
    :param votes: A list of rankings (see get_condorcet_winner for format)
    :return: The name of the Minimax winner
    """
    if not votes:
        return None
    is_dict = _is_dict_format(votes)
    candidates = set()
    for vote in votes:
        candidates.update(_get_ranking(vote, is_dict))

    opposition = defaultdict(int)
    for c1, c2 in combinations(candidates, 2):
        for vote in votes:
            ranking = _get_ranking(vote, is_dict)
            pos1 = ranking.index(c1) if c1 in ranking else float("inf")
            pos2 = ranking.index(c2) if c2 in ranking else float("inf")
            if pos2 < pos1:
                opposition[(c1, c2)] += 1

    if not candidates:
        return None
    max_opposition = {
        candidate: max(
            (opposition.get((candidate, other), 0) for other in candidates if other != candidate),
            default=0,
        )
        for candidate in candidates
    }
    return min(max_opposition.items(), key=lambda x: x[1])[0]


def get_schulze_winner(votes: list) -> Optional[str]:
    """
    Determine the Schulze method winner from a set of rankings.
    :param votes: A list of rankings (see get_condorcet_winner for format)
    :return: The name of the Schulze winner
    """
    if not votes:
        return None
    is_dict = _is_dict_format(votes)
    candidates = set()
    for vote in votes:
        candidates.update(_get_ranking(vote, is_dict))

    pref = defaultdict(lambda: defaultdict(int))
    for c1, c2 in combinations(candidates, 2):
        for vote in votes:
            ranking = _get_ranking(vote, is_dict)
            pos1 = ranking.index(c1) if c1 in ranking else float("inf")
            pos2 = ranking.index(c2) if c2 in ranking else float("inf")
            if pos1 < pos2:
                pref[c1][c2] += 1

    strength = defaultdict(lambda: defaultdict(int))
    for c1, c2 in combinations(candidates, 2):
        strength[c1][c2] = pref[c1][c2]

    for c1, c2, c3 in permutations(candidates, 3):
        strength[c1][c2] = max(strength[c1][c2], min(strength[c1][c3], strength[c3][c2]))

    wins: defaultdict = defaultdict(int)
    for c1, c2 in combinations(candidates, 2):
        if strength[c1][c2] > strength[c2][c1]:
            wins[c1] += 1

    if not wins:
        return next(iter(candidates), None)
    return max(wins.items(), key=lambda x: x[1])[0]
