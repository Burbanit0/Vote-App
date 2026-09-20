import random
import numpy as np
from typing import Any, Dict, List, Optional, Tuple, Union

from api.engine.constants import DEFAULT_ISSUES

from .demographic_data import (
    sample_age,
    sample_gender,
    sample_region,
    sample_income,
    sample_education,
    sample_employment_status,
    sample_family_status,
    sample_religion,
    sample_ethnicity_immigration,
    sample_likelihood_to_vote,
    _seeded_rng_pair,
)

# --- Define types for clarity ---
# Dict[str, Any] is used because voter and candidate dicts are assembled
# from many sources (demographics, ideology model, etc.) with heterogeneous values.
Voter = Dict[str, Any]
Candidate = Dict[str, Any]

def assign_issue_priorities(
    age: int,
    gender: str,
    region: str,
    education: str,
    income: str,
    employment_status: str,
    family_status: str,
    ethnicity_immigration: str,
    religion: str,
    *,
    rng: random.Random,
) -> Tuple[Dict[str, float], float, Dict[str, float]]:
    issue_priorities = {
        "economy": 0.5,
        "environment": 0.5,
        "healthcare": 0.5,
        "education": 0.5,
        "taxes": 0.5,
        "social_welfare": 0.5,
        "agriculture": 0.5,
        "public_transport": 0.5,
        "defense": 0.5,
        "gender_equality": 0.5,
        "pensions": 0.5,
        "climate_change": 0.5,
        "housing": 0.5,
        "immigration": 0.5,
        "crime_safety": 0.5,
        "technology_innovation": 0.5,
        "minimum_wage": 0.5,
        "business_regulation": 0.5,
        "infrastructure": 0.5,
    }

    political_lean = (
        1.0  # Neutral by default (1.0), >1.0 is conservative, <1.0 is progressive
    )

    # Age influence
    if age < 30:
        issue_priorities["environment"] = rng.uniform(0.7, 1.0)
        issue_priorities["education"] = rng.uniform(0.6, 0.9)
        issue_priorities["climate_change"] = rng.uniform(0.6, 0.9)
        issue_priorities["gender_equality"] = rng.uniform(0.6, 0.9)
        issue_priorities["public_transport"] = rng.uniform(0.5, 0.8)
        political_lean *= rng.uniform(
            0.8, 0.9
        )  # Younger voters tend to be more progressive
    elif age > 60:
        issue_priorities["healthcare"] = rng.uniform(0.7, 1.0)
        issue_priorities["pensions"] = rng.uniform(0.6, 0.9)
        political_lean *= rng.uniform(
            1.1, 1.2
        )  # Older voters tend to be more conservative
    else:
        issue_priorities["economy"] = rng.uniform(0.6, 0.9)
        issue_priorities["jobs"] = rng.uniform(0.5, 0.8)

    # Gender influence
    if gender == "female":
        issue_priorities["healthcare"] *= rng.uniform(1.1, 1.3)
        issue_priorities["education"] *= rng.uniform(1.1, 1.2)
        issue_priorities["gender_equality"] *= rng.uniform(1.1, 1.3)
        issue_priorities["social_welfare"] *= rng.uniform(1.0, 1.2)
        issue_priorities["crime_safety"] *= rng.uniform(1.0, 1.2)
        political_lean *= rng.uniform(
            0.8, 0.95
        )  # Females may lean slightly more progressive
    else:
        issue_priorities["economy"] *= rng.uniform(1.1, 1.3)
        issue_priorities["defense"] *= rng.uniform(1.1, 1.3)
        political_lean *= rng.uniform(
            1.05, 1.15
        )  # Males may lean slightly more conservative

    # Region influence
    if region == "urban":
        issue_priorities["public_transport"] = rng.uniform(0.7, 1.0)
        issue_priorities["environment"] = rng.uniform(0.6, 0.9)
        issue_priorities["housing"] = rng.uniform(0.6, 0.9)
        issue_priorities["climate_change"] = rng.uniform(0.6, 0.9)
    elif region == "rural":
        issue_priorities["agriculture"] = rng.uniform(0.7, 1.0)
        issue_priorities["infrastructure"] = rng.uniform(0.6, 0.9)
        issue_priorities["defense"] = rng.uniform(0.6, 0.9)
    else:  # suburban
        issue_priorities["education"] = rng.uniform(0.7, 1.0)
        issue_priorities["taxes"] = rng.uniform(0.5, 0.8)
        issue_priorities["housing"] = rng.uniform(0.6, 0.9)

    # Education influence
    if education in ("none", "high_school"):
        issue_priorities["social_welfare"] *= rng.uniform(1.1, 1.4)
        issue_priorities["economy"] *= rng.uniform(1.1, 1.3)
        if age > 50:
            political_lean *= rng.uniform(
                1.05, 1.2
            )  # Less educated older voters tend to be more conservative
    elif education in ("master", "phd"):
        issue_priorities["environment"] *= rng.uniform(1.1, 1.4)
        issue_priorities["education"] *= rng.uniform(1.2, 1.5)
        issue_priorities["technology_innovation"] = rng.uniform(0.7, 1.0)
        issue_priorities["climate_change"] *= rng.uniform(1.1, 1.4)
        political_lean *= rng.uniform(
            0.8, 0.95
        )  # More educated voters tend to be more progressive

    # Income influence
    if income == "low":
        issue_priorities["social_welfare"] = rng.uniform(0.8, 1.0)
        issue_priorities["minimum_wage"] = rng.uniform(0.7, 0.9)
        issue_priorities["healthcare"] *= rng.uniform(1.1, 1.3)
        issue_priorities["housing"] = rng.uniform(0.7, 1.0)
        political_lean *= rng.uniform(
            0.8, 0.95
        )  # Lower income voters tend to be more progressive
    elif income == "high":
        issue_priorities["taxes"] = rng.uniform(0.7, 1.0)
        issue_priorities["business_regulation"] = rng.uniform(0.5, 0.8)
        issue_priorities["economy"] *= rng.uniform(1.1, 1.3)
        political_lean *= rng.uniform(
            1.05, 1.2
        )  # Higher income voters tend to be more conservative

    # Employment status influence
    if employment_status == "unemployed":
        issue_priorities["social_welfare"] *= rng.uniform(1.2, 1.5)
        issue_priorities["jobs"] = rng.uniform(0.8, 1.0)
        issue_priorities["minimum_wage"] = rng.uniform(0.8, 1.0)
        political_lean *= rng.uniform(
            0.8, 0.95
        )  # Unemployed voters tend to be more progressive
    elif employment_status == "employed":
        issue_priorities["economy"] *= rng.uniform(1.1, 1.3)
        issue_priorities["taxes"] *= rng.uniform(1.0, 1.2)

    # Family status influence
    if family_status == "with_children":
        issue_priorities["education"] *= rng.uniform(1.2, 1.5)
        issue_priorities["healthcare"] *= rng.uniform(1.1, 1.3)
        issue_priorities["housing"] *= rng.uniform(1.1, 1.3)
    elif family_status == "single":
        issue_priorities["social_welfare"] *= rng.uniform(1.0, 1.2)
        issue_priorities["taxes"] *= rng.uniform(1.0, 1.2)

    # Ethnicity/Immigration influence
    if ethnicity_immigration == "immigrant":
        issue_priorities["immigration"] = rng.uniform(0.8, 1.0)
        issue_priorities["social_welfare"] *= rng.uniform(1.1, 1.3)
        issue_priorities["gender_equality"] *= rng.uniform(1.1, 1.3)
        political_lean *= rng.uniform(
            0.8, 0.95
        )  # Immigrants may lean more progressive
    else:
        issue_priorities["defense"] *= rng.uniform(1.0, 1.2)
        issue_priorities["immigration"] *= rng.uniform(0.8, 1.0)

    # Religion influence
    if religion == "religious":
        issue_priorities["gender_equality"] *= rng.uniform(0.8, 1.0)
        issue_priorities["social_welfare"] *= rng.uniform(1.0, 1.2)
        issue_priorities["education"] *= rng.uniform(0.9, 1.1)
        political_lean *= rng.uniform(
            1.1, 1.2
        )  # Religious voters tend to be more conservative
    else:
        issue_priorities["gender_equality"] *= rng.uniform(1.1, 1.3)
        issue_priorities["climate_change"] *= rng.uniform(1.0, 1.2)
        political_lean *= rng.uniform(
            0.8, 0.95
        )  # Non-religious voters tend to be more progressive

    # Derive voter's ideological position on each issue from political_lean.
    # political_lean is a multiplicative factor (~1.0 = neutral, <1 = progressive,
    # >1 = conservative). Convert to [0,1] so it aligns with candidate policy scale.
    political_lean_normalized = max(0.0, min(1.0, (political_lean - 0.5) / 1.5))
    issue_positions = {
        issue: max(0.0, min(1.0, political_lean_normalized + rng.uniform(-0.15, 0.15)))
        for issue in issue_priorities
    }

    return issue_priorities, political_lean, issue_positions


# --- 1. Generate Voters and Candidates ---

_IDEOLOGY_DISTRIBUTIONS = {"random", "centrist", "polarized", "left_skewed", "right_skewed"}


def _sample_ideology_position(
    distribution: str,
    np_rng: np.random.RandomState,
) -> Optional[float]:
    """
    Return a political lean position in [0,1] drawn from the requested
    distribution, or None for "random" (keep the demographically-derived value).

      0 = fully progressive   1 = fully conservative
    """
    if distribution == "centrist":
        return float(np.clip(np_rng.normal(0.5, 0.1), 0.0, 1.0))
    if distribution == "polarized":
        if np_rng.random() < 0.5:
            return float(np.clip(np_rng.normal(0.2, 0.08), 0.0, 1.0))
        return float(np.clip(np_rng.normal(0.8, 0.08), 0.0, 1.0))
    if distribution == "left_skewed":
        return float(np_rng.beta(2, 5))
    if distribution == "right_skewed":
        return float(np_rng.beta(5, 2))
    return None  # "random" — keep the value derived from demographics


def create_voter(
    issues: List[str],
    voter_id: int,
    ideology_distribution: str = "random",
    *,
    rng: random.Random,
    np_rng: np.random.RandomState,
) -> Voter:
    """Build one voter.

    rng/np_rng: local RNG instances (random.Random / np.random.RandomState) to
    draw from instead of the shared random/np.random module-level singletons.
    Every caller passes its own call-scoped pair (see election_service.py for
    the canonical pattern) so output stays reproducible under concurrent
    access — see PLAN_SOLIDITE_TECHNIQUE.md's Lot 5 addendum.
    """
    age = sample_age(rng)
    gender = sample_gender(np_rng)
    region = sample_region(np_rng)
    income = sample_income(np_rng)
    education = sample_education(age, np_rng)
    employment_status = sample_employment_status(rng)
    family_status = sample_family_status(rng)
    religion = sample_religion(rng)
    ethnicity_immigration = sample_ethnicity_immigration(rng)

    issue_priorities, political_lean, issue_positions = assign_issue_priorities(
        age,
        gender,
        region,
        education,
        income,
        employment_status,
        family_status,
        ethnicity_immigration,
        religion,
        rng=rng,
    )

    # Normalize so priorities sum to ~1
    total = sum(issue_priorities.values())
    issue_priorities = {k: v / total for k, v in issue_priorities.items()}

    # Normalized political lean on [0,1]: 0 = progressive, 1 = conservative.
    # Stored alongside the original multiplicative value to avoid breaking existing code.
    political_lean_normalized = max(0.0, min(1.0, (political_lean - 0.5) / 1.5))

    # Override the demographic-derived lean with a controlled distribution when
    # requested, then recompute issue_positions from the new base value.
    overridden_lean = _sample_ideology_position(ideology_distribution, np_rng)
    if overridden_lean is not None:
        political_lean_normalized = overridden_lean
        issue_positions = {
            issue: max(0.0, min(1.0, political_lean_normalized + rng.uniform(-0.15, 0.15)))
            for issue in issue_positions
        }

    # L'éducation influence la probabilité de voter (effet plus marqué avec l'âge)
    education_vote_boost = {
        "none": 0.0,
        "high_school": 0.05,
        "bachelor": 0.1,
        "master": 0.15,
        "phd": 0.2,
    }[education]

    # Les personnes âgées éduquées votent encore plus
    if age > 60 and education in ("master", "phd"):
        education_vote_boost += 0.1

    party_loyalty = rng.uniform(0, 1)

    # Strategic propensity: educated, older, and party-loyal voters are more
    # likely to vote tactically rather than by pure conviction.
    strategic_propensity = 0.2
    if education in ("master", "phd"):
        strategic_propensity += 0.1
    if age > 45:
        strategic_propensity += 0.1
    strategic_propensity += 0.15 * party_loyalty
    strategic_propensity += rng.uniform(-0.05, 0.05)
    strategic_propensity = max(0.0, min(0.8, strategic_propensity))
    voting_style = "strategic" if rng.random() < strategic_propensity else "sincere"

    # Social conformity: susceptibility to bandwagon / poll-driven preference shift.
    # Beta(2,3) → peak near 0.25, most values between 0.1 and 0.6.
    social_conformity = float(np_rng.beta(2, 3))
    if age < 30:
        social_conformity += 0.1
    if education in ("none", "high_school"):
        social_conformity += 0.05
    social_conformity = max(0.0, min(0.8, social_conformity))

    # Blank-vote threshold: minimum utility a candidate must provide for the
    # voter to rank them above "none of the above".  Beta(3, 5) → mean ≈ 0.375,
    # most values in [0.15, 0.65] — the majority of voters only cast a blank
    # when genuinely unsatisfied with every real candidate.
    blank_threshold = float(np_rng.beta(3, 5))

    return {
        "id": voter_id,
        "age": age,
        "region": region,
        "income": income,
        "gender": gender,
        "education": education,
        "employment_status": employment_status,
        "family_status": family_status,
        "ethnicity_immigration": ethnicity_immigration,
        "religion": religion,
        "political_lean": political_lean,
        "political_lean_normalized": political_lean_normalized,
        "issue_positions": issue_positions,
        "issue_priorities": issue_priorities,
        "party_loyalty": party_loyalty,
        "preferred_party": rng.choice(
            ["Green", "Conservative", "Liberal", "Independent"]
        ),
        # Turnout likelihood: age- and income-driven base rate (sample_likelihood_to_vote)
        # plus the education boost computed above.
        "likelihood_to_vote": float(
            min(0.95, sample_likelihood_to_vote(age, np_rng) + education_vote_boost)
        ),
        "mood": rng.uniform(-1, 1),
        "strategic_propensity": round(strategic_propensity, 4),
        "voting_style": voting_style,
        "social_conformity": round(social_conformity, 4),
        "blank_threshold": round(blank_threshold, 4),
    }


def create_candidate(
    issues: List[str],
    candidate_id: int,
    name: str,
    party: str,
    ideology_position: Optional[float] = None,
    position_variance: float = 0.1,
    *,
    rng: random.Random,
) -> Dict[str, Any]:
    """
    Create a candidate with policy positions.

    When ideology_position is provided (0 = progressive, 1 = conservative),
    it is used directly as the base position for every policy issue, with
    ± position_variance noise per issue.  This allows precise placement of
    candidates in ideological space.

    When ideology_position is None the position is derived from the party
    lean as before, using the wider default variance of 0.2.

    rng: local random.Random instance — see create_voter() for why this
    matters under concurrent/seeded callers.
    """
    party_leans = {
        "Green": -0.8,
        "Liberal": -0.3,
        "Conservative": 0.7,
        "Independent": 0.0,
    }

    if ideology_position is not None:
        # Explicit placement: use the provided position as base for all issues.
        base_position = float(max(0.0, min(1.0, ideology_position)))
        effective_variance = position_variance
        # Derive a party_lean consistent with the explicit position.
        effective_party_lean = (base_position * 2) - 1
    else:
        # Default: derive base position from party lean.
        raw_lean = party_leans.get(party, 0.0)
        base_position = (raw_lean + 1) / 2
        effective_variance = 0.2
        effective_party_lean = raw_lean

    policies = {
        issue: max(0.0, min(1.0, base_position + rng.uniform(-effective_variance, effective_variance)))
        for issue in issues
    }

    return {
        "id": candidate_id,
        "name": name,
        "party": party,
        "party_lean": effective_party_lean,
        "ideology_position": base_position,
        "policies": policies,
        "charisma": rng.uniform(0.5, 1.0),
        "scandals": rng.randint(0, 2),
        "campaign_funds": rng.uniform(100000, 1000000),
        "experience": rng.randint(1, 20),
        "popularity": rng.uniform(0.3, 0.9),
    }


# --- 2. Utility Calculation ---
def calculate_utility(voter: Dict[str, Any], candidate: Dict[str, Any], issues: List[str]) -> Dict[str, Any]:
    """
    Calculate the utility score for a voter-candidate pair.
    Returns a dictionary with the utility score and its breakdown.
    """
    # Issue alignment: weighted sum of (1 - distance) between voter and candidate positions.
    # voter["issue_positions"] is in [0,1]; candidate["policies"] is in [0,1].
    issue_score = sum(
        voter["issue_priorities"].get(issue, 0)
        * (1 - abs(voter["issue_positions"].get(issue, 0.5) - candidate["policies"].get(issue, 0.5)))
        for issue in issues
        if issue in voter["issue_priorities"]
    )

    # Gender-specific bonus
    gender_bonus = 0
    if voter["gender"] == "female" and "gender_equality" in candidate["policies"]:
        gender_bonus = 0.1 * candidate["policies"]["gender_equality"]
        issue_score += gender_bonus

    # Party loyalty — both values normalised to [0,1] so the distance is meaningful.
    # candidate["party_lean"] is in [-1,1]; convert to [0,1] to match political_lean_normalized.
    candidate_lean_normalized = (candidate.get("party_lean", 0) + 1) / 2
    party_match = 1 - abs(voter["political_lean_normalized"] - candidate_lean_normalized)
    loyalty_bonus = voter["party_loyalty"] * party_match

    # Charisma and scandals (non-linear effect)
    charisma_effect = candidate["charisma"]
    scandal_penalty = -0.3 * candidate["scandals"]
    if candidate["charisma"] < 0.5:  # Bigger penalty if low charisma
        scandal_penalty *= 1.5

    # Mood effect
    mood_effect = voter["mood"] * 0.1 * (1 - candidate["scandals"])

    # Combine into utility
    utility = (
        0.6 * issue_score
        + 0.2 * loyalty_bonus
        + 0.15 * charisma_effect
        + scandal_penalty
        + mood_effect
    )

    return {
        "voter_id": voter["id"],
        "candidate_id": candidate["id"],
        "utility": round(utility, 4),
        "breakdown": {
            "issue_score": round(issue_score, 4),
            "loyalty_bonus": round(loyalty_bonus, 4),
            "charisma_effect": round(charisma_effect, 4),
            "scandal_penalty": round(scandal_penalty, 4),
            "mood_effect": round(mood_effect, 4),
            "gender_bonus": round(gender_bonus, 4) if gender_bonus else 0,
        },
    }


# --- 3. Strategic Voting Helpers ---

def compute_sincere_ranking(
    voter: Voter, candidates: List[Candidate], issues: List[str]
) -> List[Candidate]:
    """Return candidates sorted by true utility (descending)."""
    return sorted(
        candidates,
        key=lambda c: -calculate_utility(voter, c, issues)["utility"],
    )


def compute_strategic_plurality_vote(
    voter: Voter,
    candidates: List[Candidate],
    issues: List[str],
    poll_standings: Dict[str, float],
) -> Optional[str]:
    """
    Plurality tactical vote (Duverger): if the sincere first choice is not
    viable (not in top-2 of polls), switch to the best viable candidate.
    """
    utilities: Dict[str, float] = {
        str(c["name"]): float(calculate_utility(voter, c, issues)["utility"]) for c in candidates
    }
    top2 = sorted(poll_standings, key=lambda k: poll_standings[k], reverse=True)[:2]
    preferred: str = max(utilities, key=lambda k: utilities[k])

    if preferred in top2:
        return preferred

    viable_top2 = [name for name in top2 if name in utilities]
    if not viable_top2:
        return preferred
    return max(viable_top2, key=lambda name: utilities[name])


def compute_strategic_borda_vote(
    voter: Voter,
    candidates: List[Candidate],
    issues: List[str],
    poll_standings: Dict[str, float],
) -> List[str]:
    """
    Borda burial strategy: rank the main poll threat last to minimise their
    Borda points, while keeping the sincere order for all other candidates.
    Falls back to sincere ranking if the preferred candidate already leads polls.
    """
    utilities_b: Dict[str, float] = {
        str(c["name"]): float(calculate_utility(voter, c, issues)["utility"]) for c in candidates
    }
    preferred_b: str = max(utilities_b, key=lambda k: utilities_b[k])
    top_by_polls = sorted(poll_standings, key=lambda k: poll_standings[k], reverse=True)

    if top_by_polls and top_by_polls[0] == preferred_b:
        return [str(c["name"]) for c in compute_sincere_ranking(voter, candidates, issues)]

    threat = next((c for c in top_by_polls if c != preferred_b), None)
    sincere_order = [str(c["name"]) for c in compute_sincere_ranking(voter, candidates, issues)]
    others = [name for name in sincere_order if name != preferred_b and name != threat]

    ranking = [preferred_b] + others
    if threat:
        ranking.append(threat)
    return ranking


def compute_strategic_irv_vote(
    voter: Voter,
    candidates: List[Candidate],
    issues: List[str],
    poll_standings: Dict[str, float],
) -> List[str]:
    """
    IRV compromise strategy: if the preferred candidate is not viable (not in
    top-2 of polls), promote the best top-2 candidate to first position while
    keeping the sincere order for the rest.
    """
    utilities_i: Dict[str, float] = {
        str(c["name"]): float(calculate_utility(voter, c, issues)["utility"]) for c in candidates
    }
    top2 = sorted(poll_standings, key=lambda k: poll_standings[k], reverse=True)[:2]
    preferred_i: str = max(utilities_i, key=lambda k: utilities_i[k])

    sincere = [str(c["name"]) for c in compute_sincere_ranking(voter, candidates, issues)]
    if preferred_i in top2:
        return sincere

    best_viable = max(
        (c for c in top2 if c in utilities_i),
        key=lambda c: utilities_i[c],
        default=None,
    )
    if best_viable and best_viable in sincere:
        sincere.remove(best_viable)
        return [best_viable] + sincere
    return sincere


def compute_strategic_approval_vote(
    voter: Voter,
    candidates: List[Candidate],
    issues: List[str],
) -> List[str]:
    """
    Approval bullet-vote strategy: approve only the top candidate to maximise
    concentration, unless the second candidate's utility is within 10 % of the
    first's (too close to sacrifice).
    Returns a list of approved candidate names (may be length 1 or 2).
    """
    utilities_a: Dict[str, float] = {
        str(c["name"]): float(calculate_utility(voter, c, issues)["utility"]) for c in candidates
    }
    ranked: List[str] = sorted(utilities_a, key=lambda k: utilities_a[k], reverse=True)
    if len(ranked) < 2:
        return ranked

    best, second = ranked[0], ranked[1]
    best_u, second_u = utilities_a[best], utilities_a[second]

    if best_u > 0 and second_u > 0 and second_u / best_u > 0.9:
        return [best, second]
    return [best]


def compute_strategic_score_vote(
    voter: Voter,
    candidates: List[Candidate],
    issues: List[str],
    poll_standings: Dict[str, float],
) -> Dict[str, int]:
    """
    Score exaggeration strategy: give the preferred candidate 5, the main poll
    threat 0, and proportionally scaled scores (1–4) to everyone else.
    """
    utilities_s: Dict[str, float] = {
        str(c["name"]): float(calculate_utility(voter, c, issues)["utility"]) for c in candidates
    }
    preferred_s: str = max(utilities_s, key=lambda k: utilities_s[k])
    top_by_polls = sorted(poll_standings, key=lambda k: poll_standings[k], reverse=True)
    threat = next((c for c in top_by_polls if c != preferred_s), None)

    others = {
        name: u
        for name, u in utilities_s.items()
        if name != preferred_s and name != threat
    }

    scores: Dict[str, int] = {preferred_s: 5}
    if threat:
        scores[threat] = 0

    if others:
        max_u = max(others.values())
        min_u = min(others.values())
        u_range = max_u - min_u
        for name, u in others.items():
            if u_range > 0:
                scores[name] = 1 + round(3 * (u - min_u) / u_range)
            else:
                scores[name] = 2
    return scores


# --- 4. Social Influence ---



# --- 4. Voting Methods ---

# Method groups used for strategic dispatch and sincere fallback.
_PLURALITY_METHODS: frozenset[str] = frozenset({"plurality"})
_BORDA_METHODS: frozenset[str] = frozenset({"borda"})
_RANKED_METHODS: frozenset[str] = frozenset({
    "ranked", "irv", "condorcet", "schulze", "minimax",
    "kemeny_young", "coombs", "bucklin", "two_round",
})
_APPROVAL_METHODS: frozenset[str] = frozenset({"approval"})
_SCORE_METHODS: frozenset[str] = frozenset({
    "score", "simple_score", "star_voting",
    "median_voting", "mean_median_hybrid", "variance_based",
})


def vote_plurality(
    voter: Voter, candidates: List[Candidate], issues: List[str]
) -> Optional[str]:
    utilities_p: Dict[str, float] = {
        str(c["name"]): float(calculate_utility(voter, c, issues)["utility"]) for c in candidates
    }
    max_utility = max(utilities_p.values())
    return max(utilities_p, key=lambda k: utilities_p[k]) if max_utility > 0.3 else None


def vote_ranked(
    voter: Voter, candidates: List[Candidate], issues: List[str]
) -> List[Candidate]:
    return sorted(candidates, key=lambda c: -calculate_utility(voter, c, issues)["utility"])


def vote_score(
    voter: Voter, candidates: List[Candidate], issues: List[str]
) -> Dict[str, int]:
    return {c["name"]: int(5 * calculate_utility(voter, c, issues)["utility"]) for c in candidates}


def simulate_vote(
    voter: Voter,
    candidates: List[Candidate],
    issues: List[str],
    method: str = "plurality",
    poll_standings: Optional[Dict[str, float]] = None,
    *,
    rng: random.Random,
) -> Union[Optional[str], List[str], Dict[str, int]]:
    """rng: local random.Random instance — see create_voter() for why this
    matters under concurrent/seeded callers. Its only caller,
    run_simulation(), threads its own call-scoped rng through here so the
    turnout gate below stays reproducible under the same seed (see
    PLAN_SOLIDITE_TECHNIQUE.md's Lot 5 addendum: before this parameter
    existed, this draw came from the bare global singleton regardless of
    what run_simulation() itself did)."""
    if rng.random() > voter["likelihood_to_vote"]:
        return None

    is_strategic = voter.get("voting_style") == "strategic"

    # ── Strategic dispatch ──────────────────────────────────────────────
    if is_strategic:
        # Approval needs no poll_standings (threshold is utility-based).
        if method in _APPROVAL_METHODS:
            return compute_strategic_approval_vote(voter, candidates, issues)

        # All other strategic methods require poll_standings to identify threats.
        if poll_standings is not None:
            if method in _PLURALITY_METHODS:
                return compute_strategic_plurality_vote(
                    voter, candidates, issues, poll_standings
                )
            if method in _BORDA_METHODS:
                return compute_strategic_borda_vote(
                    voter, candidates, issues, poll_standings
                )
            if method in _RANKED_METHODS:
                return compute_strategic_irv_vote(
                    voter, candidates, issues, poll_standings
                )
            if method in _SCORE_METHODS:
                return compute_strategic_score_vote(
                    voter, candidates, issues, poll_standings
                )
        # No poll_standings available — fall through to sincere vote.

    # ── Sincere fallback ────────────────────────────────────────────────
    if method in _PLURALITY_METHODS:
        return vote_plurality(voter, candidates, issues)
    if method in _BORDA_METHODS | _RANKED_METHODS | _APPROVAL_METHODS:
        return [c["name"] for c in vote_ranked(voter, candidates, issues)]
    if method in _SCORE_METHODS:
        return vote_score(voter, candidates, issues)
    return None


# --- 4. Run Simulation ---
def run_simulation(
    num_voters: int = 1000,
    num_candidates: int = 3,
    method: str = "plurality",
    ideology_distribution: str = "random",
    *,
    seed: int,
) -> List[Dict[str, Any]]:
    # Local RNG pair, scoped to this call (and election_service.py) — see
    # _seeded_rng_pair() for why NOT `random.seed(seed)`/`np.random.seed(seed)`.
    rng, np_rng = _seeded_rng_pair(seed)
    voters = [
        create_voter(
            DEFAULT_ISSUES, voter_id=i, ideology_distribution=ideology_distribution,
            rng=rng, np_rng=np_rng,
        )
        for i in range(num_voters)
    ]
    _party_cycle = ("Green", "Conservative", "Liberal", "Independent")
    candidates = [
        create_candidate(
            DEFAULT_ISSUES,
            candidate_id=i,
            name=f"Candidate {i + 1}",
            party=_party_cycle[i % len(_party_cycle)],
            rng=rng,
        )
        for i in range(num_candidates)
    ]

    results = []
    for voter in voters:
        vote = simulate_vote(voter, candidates, DEFAULT_ISSUES, method, rng=rng)
        results.append(
            {
                "voter": voter,
                "vote": vote,
                "utilities": {
                    c["name"]: calculate_utility(voter, c, DEFAULT_ISSUES)["utility"] for c in candidates
                },
            }
        )
    return results
