import random
from collections import defaultdict


def init(population_size, demographics, turnout_rate):
    voters = []
    for voter_id in range(population_size):
        # Assign demographics
        age = random.choices(
            list(demographics["age"].keys()), weights=demographics["age"].values()
        )[0]
        gender = random.choices(
            list(demographics["gender"].keys()), weights=demographics["gender"].values()
        )[0]
        location = random.choices(
            list(demographics["location"].keys()),
            weights=demographics["location"].values(),
        )[0]
        education = random.choices(
            list(demographics["education"].keys()),
            weights=demographics["education"].values(),
        )[0]
        income = random.choices(
            list(demographics["income"].keys()), weights=demographics["income"].values()
        )[0]
        ideology = random.choices(
            list(demographics["ideology"].keys()),
            weights=demographics["ideology"].values(),
        )[0]

        # Determine if the voter turns out
        turnout = random.random() < turnout_rate

        voters.append(
            {
                "id": voter_id,
                "age": age,
                "gender": gender,
                "location": location,
                "education": education,
                "income": income,
                "ideology": ideology,
                "turnout": turnout,
            }
        )

    return voters


def simulate_voters(
    population_size, candidates, demographics, influence_weights, turnout_rate
):

    voters = init(population_size, demographics, turnout_rate)

    # Assign preferences, including "No Vote"
    for voter in voters:
        if not voter["turnout"]:
            voter["preference"] = "No Vote"
            continue

        scores = {candidate: 1.0 for candidate in candidates}
        scores["No Vote"] = 1.0  # Base score for abstention

        # Apply influence weights
        for param, value in voter.items():
            if param in influence_weights and value in influence_weights[param]:
                for candidate, weight in influence_weights[param][value].items():
                    if candidate in scores:
                        scores[candidate] *= weight

        # Normalize scores to probabilities
        total = sum(scores.values())
        probabilities = [scores[candidate] / total for candidate in scores.keys()]
        voter["preference"] = random.choices(
            list(scores.keys()), weights=probabilities, k=1
        )[0]

    # Collect votes (including "No Vote" for those who turned out but abstained)
    votes = [voter["preference"] for voter in voters]

    # Tally votes
    tally = defaultdict(int)
    for vote in votes:
        tally[vote] += 1

    return voters, votes, tally


def simulate_ranked_voters(
    population_size, candidates, demographics, influence_weights, turnout_rate
):
    voters = voters = init(population_size, demographics, turnout_rate)

    # Assign ranked preferences
    for voter in voters:
        if not voter["turnout"]:
            voter["ranking"] = []  # No ranking if they don't turn out
            continue

        scores = {candidate: 1.0 for candidate in candidates}

        # Apply influence weights
        for param, value in voter.items():
            if param in influence_weights and value in influence_weights[param]:
                for candidate, weight in influence_weights[param][value].items():
                    if candidate in scores:
                        scores[candidate] *= weight

        # Sort candidates by score to create ranking (highest score first)
        voter["ranking"] = sorted(scores.keys(), key=lambda x: -scores[x])

    # Collect rankings
    rankings = [voter["ranking"] for voter in voters if voter["turnout"]]

    # Tally first choices (for demonstration)
    first_choices = [ranking[0] for ranking in rankings if ranking]
    tally = defaultdict(int)
    for choice in first_choices:
        tally[choice] += 1

    return voters, rankings, tally


def simulate_score_voters(
    population_size, candidates, demographics, influence_weights, turnout_rate
):
    voters = []
    for voter_id in range(population_size):
        # Assign demographics
        age = random.choices(
            list(demographics["age"].keys()), weights=demographics["age"].values()
        )[0]
        gender = random.choices(
            list(demographics["gender"].keys()), weights=demographics["gender"].values()
        )[0]
        location = random.choices(
            list(demographics["location"].keys()),
            weights=demographics["location"].values(),
        )[0]
        education = random.choices(
            list(demographics["education"].keys()),
            weights=demographics["education"].values(),
        )[0]
        income = random.choices(
            list(demographics["income"].keys()), weights=demographics["income"].values()
        )[0]
        ideology = random.choices(
            list(demographics["ideology"].keys()),
            weights=demographics["ideology"].values(),
        )[0]

        # Determine if the voter turns out
        turnout = random.random() < turnout_rate

        voters.append(
            {
                "id": voter_id,
                "age": age,
                "gender": gender,
                "location": location,
                "education": education,
                "income": income,
                "ideology": ideology,
                "turnout": turnout,
            }
        )

    # Assign scores (0-5) to each candidate for each voter
    for voter in voters:
        if not voter["turnout"]:
            voter["scores"] = {
                candidate: 0 for candidate in candidates
            }  # No scores if they don't turn out
            continue

        # Calculate raw similarity scores
        raw_scores = {candidate: 1.0 for candidate in candidates}
        for param, value in voter.items():
            if param in influence_weights and value in influence_weights[param]:
                for candidate, weight in influence_weights[param][value].items():
                    if candidate in raw_scores:
                        raw_scores[candidate] *= weight

        # Normalize raw scores to 0-5 range
        max_raw = max(raw_scores.values())
        min_raw = min(raw_scores.values())
        # Avoid division by zero and ensure range
        if max_raw != min_raw:
            for candidate in raw_scores:
                # Scale to 0-5
                raw_scores[candidate] = (
                    5 * (raw_scores[candidate] - min_raw) / (max_raw - min_raw)
                )
        else:
            for candidate in raw_scores:
                raw_scores[candidate] = (
                    2.5  # Default to midpoint if all scores are equal
                )

        # Clamp to 0-5
        voter["scores"] = {
            candidate: min(5, max(0, raw_scores[candidate])) for candidate in candidates
        }

    # Collect scores
    all_scores = [voter["scores"] for voter in voters if voter["turnout"]]

    # Calculate average score per candidate
    avg_scores = defaultdict(float)
    for scores in all_scores:
        for candidate, score in scores.items():
            avg_scores[candidate] += score
    for candidate in avg_scores:
        avg_scores[candidate] /= len(all_scores)

    return voters, all_scores, avg_scores
