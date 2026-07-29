from collections import defaultdict, Counter
from itertools import combinations, permutations
from typing import Any, Optional


def _is_dict_format(votes: list[Any]) -> bool:
    """Return True when votes are dicts with a 'ranking' key, False for plain lists."""
    return bool(votes) and isinstance(votes[0], dict)


def _get_ranking(vote: Any, is_dict: bool) -> Any:
    """Extract the ranking list from a vote regardless of format."""
    return vote["ranking"] if is_dict else vote


def get_condorcet_winner(votes: list[Any], blank_candidate_name: str = "") -> Optional[str]:
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

    wins: "defaultdict[Any, int]" = defaultdict(int)
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
            return str(candidate)
    return None


def get_two_round_winner(votes: list[Any], blank_candidate_name: str = "") -> Optional[str]:
    """
    Determine the winner of a two-round system from a set of rankings.
    :param votes: A list of rankings (see get_condorcet_winner for format)
    :return: The name of the winner.
    """
    if not votes:
        return None
    is_dict = _is_dict_format(votes)

    first_choice_votes: "Counter[Any]" = Counter()
    for vote in votes:
        ranking = _get_ranking(vote, is_dict)
        if ranking:
            first_choice_votes[ranking[0]] += 1

    majority = len(votes) // 2
    for candidate, count in first_choice_votes.items():
        if count > majority:
            return str(candidate)

    top_two_candidates = [c for c, _ in first_choice_votes.most_common(2)]

    second_round_votes: "Counter[Any]" = Counter()
    for vote in votes:
        ranking = _get_ranking(vote, is_dict)
        for candidate in ranking:
            if candidate in top_two_candidates:
                second_round_votes[candidate] += 1
                break

    if not second_round_votes:
        return None
    return str(max(second_round_votes, key=lambda c: second_round_votes[c]))


def get_borda_winner(votes: list[Any], blank_candidate_name: str = "") -> Optional[str]:
    """
    Determine the Borda count winner from a set of rankings.
    :param votes: A list of rankings (see get_condorcet_winner for format)
    :return: The name of the Borda winner
    """
    if not votes:
        return None
    is_dict = _is_dict_format(votes)
    scores: "defaultdict[Any, int]" = defaultdict(int)
    for vote in votes:
        ranking = _get_ranking(vote, is_dict)
        num_candidates = len(ranking)
        for position, candidate in enumerate(ranking):
            scores[candidate] += num_candidates - 1 - position
    if not scores:
        return None
    return str(max(scores.items(), key=lambda x: x[1])[0])


def get_black_winner(votes: list[Any], blank_candidate_name: str = "") -> Optional[str]:
    """
    Determine the winner under Black's method (Duncan Black, 1958): elect the
    Condorcet winner if one exists, otherwise fall back to the Borda winner.

    :param votes: A list of rankings (see get_condorcet_winner for format)
    :return: The name of the Black winner
    """
    condorcet = get_condorcet_winner(votes, blank_candidate_name)
    return condorcet if condorcet is not None else get_borda_winner(votes, blank_candidate_name)


def get_plurality_winner(votes: list[Any], blank_candidate_name: str = "") -> Optional[str]:
    """
    Determine the plurality winner from a set of rankings.
    :param votes: A list of rankings (see get_condorcet_winner for format)
    :return: The name of the plurality winner
    """
    if not votes:
        return None
    is_dict = _is_dict_format(votes)
    first_choice_votes: "Counter[Any]" = Counter()
    for vote in votes:
        ranking = _get_ranking(vote, is_dict)
        if ranking:
            first_choice_votes[ranking[0]] += 1
    if not first_choice_votes:
        return None
    return str(max(first_choice_votes.items(), key=lambda x: x[1])[0])


def get_approval_winner(
    votes: list[Any],
    approval_threshold: int = 2,
    utility_scores: Optional[dict[Any, Any]] = None,
    blank_candidate_name: str = "",
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

    approval_votes: "Counter[Any]" = Counter()

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
    return str(max(approval_votes.items(), key=lambda x: x[1])[0])


def get_approval_winner_sincere(utility_scores: dict[Any, Any]) -> Optional[str]:
    """
    Convenience wrapper that runs approval voting in sincere mode.
    Expects utility_scores as {voter_id: {candidate_name: float}}.
    Builds the votes list internally so callers do not need to maintain
    a parallel rankings list.
    """
    votes = [{"voter_id": voter_id} for voter_id in utility_scores]
    return get_approval_winner(votes, utility_scores=utility_scores)


def get_irv_winner(votes: list[Any], blank_candidate_name: str = "") -> Optional[str]:
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
        # Seed every surviving candidate at 0 so a candidate with no first-prefs
        # this round is still eliminable (not silently protected).
        votes_count: "Counter[Any]" = Counter({c: 0 for c in candidates})
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
                return str(candidate)

        # Eliminate ALL candidates tied for the fewest first-prefs (neutral,
        # candidate-order-independent). If that is everyone, it's a dead tie.
        min_votes = min(votes_count.values())
        eliminated = [c for c, v in votes_count.items() if v == min_votes]
        if len(eliminated) >= len(candidates):
            return None
        for candidate in eliminated:
            candidates.remove(candidate)

    return candidates.pop() if candidates else None


def get_coombs_winner(votes: list[Any], blank_candidate_name: str = "") -> Optional[str]:
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
        first_choices: "Counter[Any]" = Counter()
        last_choices: "Counter[Any]" = Counter()
        for vote in votes:
            ranking = _get_ranking(vote, is_dict)
            for candidate in ranking:
                if candidate in candidates:
                    first_choices[candidate] += 1
                    break
            for candidate in reversed(ranking):
                if candidate in candidates:
                    last_choices[candidate] += 1
                    break

        # Standard Coombs stops as soon as a candidate holds a first-pref majority.
        majority = sum(first_choices.values()) / 2
        for candidate, count in first_choices.items():
            if count > majority:
                return str(candidate)

        if not last_choices:
            break
        # Eliminate ALL candidates tied for the most last-place votes (neutral).
        max_last = max(last_choices.values())
        eliminated = [c for c, v in last_choices.items() if v == max_last]
        if len(eliminated) >= len(candidates):
            return None
        for candidate in eliminated:
            candidates.remove(candidate)

    return candidates.pop() if candidates else None


def get_positional_score_winner(votes: list[Any], **kwargs: Any) -> Optional[str]:
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
    scores: "defaultdict[Any, float]" = defaultdict(float)
    for vote in votes:
        ranking = _get_ranking(vote, is_dict)
        num_candidates = len(ranking)
        for position, candidate in enumerate(ranking):
            scores[candidate] += 1 - (position / (num_candidates - 1)) if num_candidates > 1 else 1
    if not scores:
        return None
    return str(max(scores.items(), key=lambda x: x[1])[0])


# Backward-compatible alias used by existing route code.
get_score_winner = get_positional_score_winner


def _kwik_sort(candidates: list[str], pairwise: dict[tuple[str, str], int]) -> list[str]:
    """
    KwikSort approximation of Kemeny-Young — O(n log n) expected time.
    Randomly picks a pivot; partitions candidates by majority pairwise preference.
    Returns a ranking whose first element is the approximate KY winner.
    """
    import random as _rnd
    if len(candidates) <= 1:
        return list(candidates)
    pivot = _rnd.choice(candidates)
    left: list[str] = []
    right: list[str] = []
    for c in candidates:
        if c == pivot:
            continue
        (left if pairwise.get((pivot, c), 0) >= pairwise.get((c, pivot), 0) else right).append(c)
    return _kwik_sort(left, pairwise) + [pivot] + _kwik_sort(right, pairwise)


def _build_pairwise(candidates: list[str], votes: list[Any], is_dict: bool) -> dict[tuple[str, str], int]:
    """Count pairwise wins: pairwise[(a, b)] = number of ballots where a is ranked above b."""
    pairwise: dict[tuple[str, str], int] = {}
    for vote in votes:
        ranking = _get_ranking(vote, is_dict)
        pos = {c: i for i, c in enumerate(ranking)}
        for a, b in combinations(candidates, 2):
            if pos.get(a, len(ranking)) < pos.get(b, len(ranking)):
                pairwise[(a, b)] = pairwise.get((a, b), 0) + 1
            else:
                pairwise[(b, a)] = pairwise.get((b, a), 0) + 1
    return pairwise


# Hard cap: Kemeny-Young exact is O(n!) — impractical beyond 6 candidates.
_KY_EXACT_CAP = 6


def get_kemeny_young_winner(votes: list[Any], **kwargs: Any) -> Optional[str]:
    """
    Determine the Kemeny-Young winner from a set of rankings.

    Exact algorithm for ≤ 6 candidates (O(n!)).
    KwikSort approximation for > 6 candidates (O(n log n)).
    The approximation flag is stored in a thread-local so callers
    that need to know can check ``get_kemeny_young_winner.was_approx``.
    """
    if not votes:
        return None
    is_dict  = _is_dict_format(votes)
    cand_set: set[str] = set()
    for vote in votes:
        cand_set.update(_get_ranking(vote, is_dict))
    candidates = list(cand_set)

    get_kemeny_young_winner.was_approx = len(candidates) > _KY_EXACT_CAP  # type: ignore[attr-defined]

    pairwise = _build_pairwise(candidates, votes, is_dict)

    if len(candidates) > _KY_EXACT_CAP:
        # Approximation path — KwikSort
        ranking = _kwik_sort(candidates, pairwise)
        return ranking[0] if ranking else None

    # Exact path — enumerate all permutations
    def _kemeny_score(ranking: tuple[str, ...]) -> int:
        pos = {c: i for i, c in enumerate(ranking)}
        return sum(
            pairwise.get((ranking[i], ranking[j]), 0)
            for i in range(len(ranking))
            for j in range(i + 1, len(ranking))
            if pos[ranking[i]] < pos[ranking[j]]
        )

    best = max(permutations(candidates), key=_kemeny_score)
    return best[0] if best else None


def get_bucklin_winner(votes: list[Any], blank_candidate_name: str = "") -> Optional[str]:
    """
    Determine the Bucklin voting winner from a set of rankings.

    Bucklin is CUMULATIVE: at round k, tally every candidate that appears in a
    voter's top-k choices (counts carry over between rounds). The first round in
    which a candidate exceeds a majority decides it — the highest tally among
    those over the threshold wins.
    :param votes: A list of rankings (see get_condorcet_winner for format)
    :return: The name of the Bucklin winner
    """
    if not votes:
        return None
    is_dict = _is_dict_format(votes)
    rankings = [_get_ranking(vote, is_dict) for vote in votes]
    max_rank = max(len(ranking) for ranking in rankings)
    majority = len(votes) / 2
    votes_count: "Counter[Any]" = Counter()

    for rank in range(1, max_rank + 1):
        for ranking in rankings:
            if len(ranking) >= rank:
                votes_count[ranking[rank - 1]] += 1

        over_majority = [(c, v) for c, v in votes_count.items() if v > majority]
        if over_majority:
            return str(max(over_majority, key=lambda cv: cv[1])[0])

    return str(max(votes_count.items(), key=lambda x: x[1])[0]) if votes_count else None


def get_minimax_winner(votes: list[Any], blank_candidate_name: str = "") -> Optional[str]:
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

    opposition: "defaultdict[Any, int]" = defaultdict(int)
    for c1, c2 in combinations(candidates, 2):
        for vote in votes:
            ranking = _get_ranking(vote, is_dict)
            pos1 = ranking.index(c1) if c1 in ranking else float("inf")
            pos2 = ranking.index(c2) if c2 in ranking else float("inf")
            if pos2 < pos1:
                opposition[(c1, c2)] += 1
            elif pos1 < pos2:
                opposition[(c2, c1)] += 1

    if not candidates:
        return None
    max_opposition = {
        candidate: max(
            (opposition.get((candidate, other), 0) for other in candidates if other != candidate),
            default=0,
        )
        for candidate in candidates
    }
    return str(min(max_opposition.items(), key=lambda x: x[1])[0])


def get_schulze_winner(votes: list[Any], blank_candidate_name: str = "") -> Optional[str]:
    """
    Determine the Schulze method winner from a set of rankings.
    :param votes: A list of rankings (see get_condorcet_winner for format)
    :return: The name of the Schulze winner
    """
    if not votes:
        return None
    is_dict = _is_dict_format(votes)
    candidates: list[Any] = []
    seen: set[Any] = set()
    for vote in votes:
        for c in _get_ranking(vote, is_dict):
            if c not in seen:
                seen.add(c)
                candidates.append(c)
    if not candidates:
        return None

    # Pairwise preference counts d[a][b] = # voters ranking a above b.
    d = {a: {b: 0 for b in candidates} for a in candidates}
    for c1, c2 in combinations(candidates, 2):
        for vote in votes:
            ranking = _get_ranking(vote, is_dict)
            pos1 = ranking.index(c1) if c1 in ranking else float("inf")
            pos2 = ranking.index(c2) if c2 in ranking else float("inf")
            if pos1 < pos2:
                d[c1][c2] += 1
            elif pos2 < pos1:
                d[c2][c1] += 1

    # Strongest paths: keep only the winning direction, then widest-path
    # Floyd–Warshall with the intermediate node `i` as the OUTERMOST loop.
    p = {a: {b: 0 for b in candidates} for a in candidates}
    for c1, c2 in combinations(candidates, 2):
        if d[c1][c2] > d[c2][c1]:
            p[c1][c2] = d[c1][c2]
        elif d[c2][c1] > d[c1][c2]:
            p[c2][c1] = d[c2][c1]

    for i in candidates:
        for j in candidates:
            if j == i:
                continue
            for k in candidates:
                if k != i and k != j:
                    p[j][k] = max(p[j][k], min(p[j][i], p[i][k]))

    # The Schulze winner's strongest path to every other candidate is at least as
    # strong as the reverse (at least one such candidate always exists).
    for cand in candidates:
        if all(p[cand][other] >= p[other][cand] for other in candidates if other != cand):
            return str(cand)
    return str(candidates[0])


# ── New methods ────────────────────────────────────────────────────────────────

def _pairwise_wins(votes: list[Any]) -> dict[str, dict[str, int]]:
    """
    Build a pairwise wins matrix from a list of rankings.
    pw[a][b] = number of ballots where a is ranked above b.
    """
    is_dict = _is_dict_format(votes)
    cand_set: set[str] = set()
    for v in votes:
        cand_set.update(_get_ranking(v, is_dict))

    pw: dict[str, dict[str, int]] = {c: {d: 0 for d in cand_set} for c in cand_set}
    for v in votes:
        ranking = _get_ranking(v, is_dict)
        pos = {c: i for i, c in enumerate(ranking)}
        for a, b in combinations(cand_set, 2):
            pa = pos.get(a, len(ranking))
            pb = pos.get(b, len(ranking))
            if pa < pb:
                pw[a][b] += 1
            elif pb < pa:
                pw[b][a] += 1
    return pw


def get_copeland_winner(votes: list[Any], blank_candidate_name: str = "") -> Optional[str]:
    """
    Copeland's method: score = pairwise wins − pairwise losses.
    Ties in Copeland score are broken by total wins (descending),
    then alphabetically.
    """
    if not votes:
        return None

    pw = _pairwise_wins(votes)
    candidates = list(pw.keys())
    if not candidates:
        return None

    n_voters = len(votes)
    half     = n_voters / 2  # strict majority threshold

    copeland: dict[str, int] = {}
    total_wins: dict[str, int] = {}
    for c in candidates:
        w = sum(1 for d in candidates if d != c and pw[c][d] > half)
        l = sum(1 for d in candidates if d != c and pw[d][c] > half)
        copeland[c]    = w - l
        total_wins[c]  = w

    # Primary sort: Copeland score desc; secondary: total wins desc; tertiary: alpha asc
    ranked = sorted(
        candidates,
        key=lambda c: (-copeland[c], -total_wins[c], c),
    )
    return ranked[0]


def get_nanson_winner(votes: list[Any], blank_candidate_name: str = "") -> Optional[str]:
    """
    Nanson's method: iteratively eliminate all candidates whose Borda score
    is strictly below the mean Borda score of the remaining candidates.
    Guaranteed to elect the Condorcet winner when one exists (Nanson, 1882).
    Tie-break (if multiple remain with no eliminations possible): alphabetical.
    """
    if not votes:
        return None

    is_dict  = _is_dict_format(votes)
    all_cands: list[str] = []
    for v in votes:
        for c in _get_ranking(v, is_dict):
            if c not in all_cands:
                all_cands.append(c)

    active = set(all_cands)

    while len(active) > 1:
        # Compute Borda scores restricted to active candidates
        scores: dict[str, float] = {c: 0.0 for c in active}
        for v in votes:
            ranking = [c for c in _get_ranking(v, is_dict) if c in active]
            n = len(ranking)
            for pos, c in enumerate(ranking):
                scores[c] += n - 1 - pos

        mean_score = sum(scores.values()) / len(active)
        to_eliminate = {c for c in active if scores[c] < mean_score}

        if not to_eliminate or to_eliminate == active:
            # No progress possible — break and return best remaining
            break

        active -= to_eliminate

    if not active:
        return min(all_cands)  # fallback
    if len(active) == 1:
        return next(iter(active))

    # Multiple survivors: return the one with highest final Borda score, then alpha
    scores_final: dict[str, float] = {c: 0.0 for c in active}
    for v in votes:
        ranking = [c for c in _get_ranking(v, is_dict) if c in active]
        n = len(ranking)
        for pos, c in enumerate(ranking):
            scores_final[c] += n - 1 - pos

    return min(active, key=lambda c: (-scores_final[c], c))


def get_baldwin_winner(votes: list[Any], blank_candidate_name: str = "") -> Optional[str]:
    """
    Baldwin's method: iteratively eliminate the single candidate with the
    lowest Borda score among the remaining candidates.
    Like Nanson, guaranteed to elect the Condorcet winner when one exists.
    Tie-break on elimination: alphabetical (eliminate the alphabetically first).
    """
    if not votes:
        return None

    is_dict   = _is_dict_format(votes)
    all_cands: list[str] = []
    for v in votes:
        for c in _get_ranking(v, is_dict):
            if c not in all_cands:
                all_cands.append(c)

    active = set(all_cands)

    while len(active) > 1:
        scores: dict[str, float] = {c: 0.0 for c in active}
        for v in votes:
            ranking = [c for c in _get_ranking(v, is_dict) if c in active]
            n = len(ranking)
            for pos, c in enumerate(ranking):
                scores[c] += n - 1 - pos

        min_score = min(scores.values())
        # All tied → no elimination possible
        if all(s == min_score for s in scores.values()):
            break

        # Eliminate the candidate with the lowest score (alpha tie-break)
        loser = min(
            (c for c in active if scores[c] == min_score),
            key=lambda c: c,
        )
        active.discard(loser)

    if not active:
        return min(all_cands)
    return min(active)  # alpha tie-break among survivors


def get_ranked_pairs_winner(votes: list[Any], blank_candidate_name: str = "") -> Optional[str]:
    """
    Tideman's Ranked Pairs (1987).

    Lock the strongest pairwise majorities first, skipping any that would create
    a cycle; the source of the resulting acyclic tournament is the winner.
    Elects the Condorcet winner whenever one exists, and is clone-independent.

    Tie-break for equal margins: stronger winner support first, then alphabetical
    on (winner, loser) so the lock order — and therefore the winner — is
    deterministic. A pairwise tie contributes no locked edge.
    """
    if not votes:
        return None

    pw = _pairwise_wins(votes)
    candidates = sorted(pw.keys())
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    # Majorities: (margin, winner_support, winner, loser), strongest first.
    majorities: list[tuple[int, int, str, str]] = []
    for a, b in combinations(candidates, 2):
        ab, ba = pw[a][b], pw[b][a]
        if ab > ba:
            majorities.append((ab - ba, ab, a, b))
        elif ba > ab:
            majorities.append((ba - ab, ba, b, a))
    majorities.sort(key=lambda m: (-m[0], -m[1], m[2], m[3]))

    locked: dict[str, set[str]] = {c: set() for c in candidates}

    def _reaches(src: str, dst: str) -> bool:
        """DFS: is dst already reachable from src in the locked graph?"""
        stack = [src]
        seen: set[str] = set()
        while stack:
            node = stack.pop()
            if node == dst:
                return True
            if node in seen:
                continue
            seen.add(node)
            stack.extend(locked[node])
        return False

    for _margin, _support, winner, loser in majorities:
        # winner → loser would form a cycle iff loser can already reach winner.
        if not _reaches(loser, winner):
            locked[winner].add(loser)

    # The winner is the source: no locked edge points into it.
    incoming: dict[str, int] = {c: 0 for c in candidates}
    for losers in locked.values():
        for loser in losers:
            incoming[loser] += 1
    sources = sorted(c for c in candidates if incoming[c] == 0)
    return sources[0] if sources else None


def random_ballot_probabilities(votes: list[Any]) -> dict[str, float]:
    """
    Win probabilities under the random-ballot rule (Gibbard, 1977).

    A single ballot is drawn uniformly at random and its top choice elected, so
    P(candidate wins) equals that candidate's first-preference share. Returns a
    {candidate: probability} map that sums to 1 over the ballots cast.
    """
    if not votes:
        return {}
    is_dict = _is_dict_format(votes)
    first_choice: "Counter[str]" = Counter()
    cast = 0
    for vote in votes:
        ranking = _get_ranking(vote, is_dict)
        if ranking:
            first_choice[ranking[0]] += 1
            cast += 1
    if cast == 0:
        return {}
    return {c: n / cast for c, n in first_choice.items()}


def get_random_ballot_winner(votes: list[Any], blank_candidate_name: str = "") -> Optional[str]:
    """
    Random ballot / random dictator (Gibbard, 1977) — the canonical strategyproof
    rule. The realised winner is a lottery (see :func:`random_ballot_probabilities`);
    this returns the *most probable* outcome — the candidate with the largest
    first-preference share, alphabetical tie-break — so the rule has a stable,
    comparable representative winner. Its strategyproofness and full distribution
    are surfaced separately (the comparison report weights metrics by probability).
    """
    probs = random_ballot_probabilities(votes)
    if not probs:
        return None
    return min(probs, key=lambda c: (-probs[c], c))
