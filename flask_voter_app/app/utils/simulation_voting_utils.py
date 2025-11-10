import random
import numpy as np
from typing import List, Dict, Optional, Union

# --- Define types for clarity ---
Voter = Dict[str, Union[float, str, Dict[str, float]]]
Candidate = Dict[str, Union[str, float, Dict[str, float]]]

# Define issues
issues = [
    "economy", "environment", "healthcare", "education", "taxes",
    "social_welfare", "agriculture", "public_transport",
    "defense", "gender_equality", "pensions", "climate_change",
    "housing", "immigration", "crime_safety", "technology_innovation",
    "minimum_wage", "business_regulation", "jobs", "infrastructure"
]


age_data = {
    18: 416343 + 433377 + 395666 + 412560,
    19: 395309 + 410714 + 375286 + 390002,
    20: 385065 + 398993 + 370927 + 384532,
    21: 372131 + 384384 + 357581 + 370258,
    22: 370146 + 381869 + 362301 + 374177,
    23: 360901 + 371731 + 356005 + 367951,
    24: 347002 + 357849 + 346277 + 358614,
    25: 345674 + 356195 + 345575 + 357966,
    26: 362321 + 373660 + 363459 + 376224,
    27: 366486 + 377772 + 372324 + 385366,
    28: 373290 + 384835 + 383355 + 397080,
    29: 374197 + 385034 + 391141 + 405038,
    30: 379875 + 390899 + 395872 + 409842,
    31: 381893 + 392786 + 399849 + 413955,
    32: 387094 + 397979 + 407992 + 422167,
    33: 387604 + 398786 + 406130 + 420790,
    34: 385394 + 396435 + 403783 + 417815,
    35: 380127 + 391214 + 400179 + 414133,
    36: 405212 + 416777 + 423799 + 438390,
    37: 409918 + 421707 + 427819 + 442482,
    38: 415493 + 427643 + 433421 + 448307,
    39: 393900 + 405581 + 409982 + 424441,
    40: 387855 + 399149 + 400285 + 414208,
    41: 392747 + 404816 + 399454 + 413671,
    42: 378560 + 390441 + 389825 + 404350,
    43: 391896 + 404346 + 398442 + 413722,
    44: 413159 + 426173 + 419802 + 435157,
    45: 435027 + 448213 + 444733 + 460384,
    46: 445836 + 459886 + 453714 + 469527,
    47: 443926 + 457822 + 450509 + 466462,
    48: 435014 + 448697 + 442478 + 457896,
    49: 427528 + 441572 + 437448 + 452879,
    50: 420403 + 434971 + 434367 + 450472,
    51: 418677 + 432749 + 431582 + 447421,
    52: 427611 + 441979 + 441391 + 457665,
    53: 428356 + 442828 + 443353 + 459310,
    54: 430748 + 444960 + 448656 + 464153,
    55: 424098 + 438142 + 444809 + 460412,
    56: 408160 + 422099 + 429696 + 445047,
    57: 408160 + 421161 + 430734 + 444896,
    58: 403439 + 416331 + 430410 + 444709,
    59: 398034 + 410415 + 429394 + 442263,
    60: 388186 + 400042 + 420715 + 433635,
    61: 384480 + 395817 + 418514 + 430912,
    62: 379050 + 390345 + 415501 + 427893,
    63: 371791 + 382395 + 412354 + 424094,
    64: 370846 + 381146 + 410242 + 421875,
    65: 361301 + 371165 + 402421 + 413428,
    66: 365439 + 374781 + 407626 + 418007,
    67: 356096 + 364694 + 398247 + 408050,
    68: 366582 + 374817 + 412349 + 422019,
    69: 356693 + 364312 + 404851 + 413673,
    70: 354324 + 361485 + 400690 + 409072,
    71: 343241 + 350179 + 393058 + 400876,
    72: 320586 + 327085 + 371293 + 378561,
    73: 236900 + 242793 + 279240 + 286325,
    74: 228830 + 234112 + 272775 + 279055,
    75: 219772 + 224687 + 263648 + 269401,
    76: 199977 + 204674 + 242996 + 249057,
    77: 173672 + 177799 + 216640 + 221914,
    78: 175051 + 179151 + 225878 + 231318,
    79: 178422 + 182015 + 234807 + 239598,
    80: 168374 + 171854 + 227972 + 232663,
    81: 157797 + 160969 + 221619 + 226088,
    82: 150275 + 153145 + 218414 + 222853,
    83: 136476 + 139041 + 209883 + 213902,
    84: 129598 + 131872 + 207254 + 210980,
    85: 114789 + 116712 + 192418 + 195596
}

# Calculate the total population
total_population = sum(age_data.values())

# Calculate the probability for each age
age_probabilities = [count / total_population for count in age_data.values()]
ages = list(age_data.keys())


def sample_age():
    return int(random.choices(ages, weights=age_probabilities, k=1)[0])


def sample_region():
    return np.random.choice(
        ["urban", "suburban", "rural"],
        p=[0.8, 0.15, 0.05]
    )


def sample_income():
    # Use a gamma distribution which is better for right-skewed data like income
    income_score = np.random.gamma(shape=2, scale=0.2)

    if income_score < 0.3:
        return "low"
    elif income_score < 0.7:
        return "middle"
    else:
        return "high"


def sample_likelihood_to_vote(age):
    # Base turnout: 50% + age effect + income effect
    base = 0.5
    age_effect = min(age / 100, 0.4)  # Older = more likely
    income_effect = 0.1 if sample_income() == "high" else 0
    return base + age_effect + income_effect


def sample_political_lean():
    # Mix of two normal distributions (left and right)
    if np.random.random() < 0.5:
        return np.random.normal(-0.5, 0.3)  # Left-leaning
    else:
        return np.random.normal(0.5, 0.3)   # Right-leaning


def sample_employment_status():
    # Probabilities based on typical employment distributions
    probabilities = {
        "employed": 0.6,       # 60% chance
        "unemployed": 0.1,     # 10% chance
        "self_employed": 0.1,  # 10% chance
        "retired": 0.2         # 20% chance
    }
    return random.choices(
        population=list(probabilities.keys()),
        weights=list(probabilities.values()),
        k=1
    )[0]


def sample_family_status():
    # Probabilities based on typical family structures
    probabilities = {
        "single": 0.3,         # 30% chance
        "with_children": 0.4,  # 40% chance
        "retired": 0.3         # 30% chance (includes empty-nesters and elderly)
    }
    return random.choices(
        population=list(probabilities.keys()),
        weights=list(probabilities.values()),
        k=1
    )[0]


def sample_ethnicity_immigration():
    # Probabilities based on typical immigration rates in many Western countries
    probabilities = {
        "native": 0.8,        # 80% chance
        "immigrant": 0.2      # 20% chance
    }
    return random.choices(
        population=list(probabilities.keys()),
        weights=list(probabilities.values()),
        k=1
    )[0]


def sample_religion():
    # Probabilities based on global religious affiliation trends
    probabilities = {
        "religious": 0.6,     # 60% chance
        "non_religious": 0.4  # 40% chance
    }
    return random.choices(
        population=list(probabilities.keys()),
        weights=list(probabilities.values()),
        k=1
    )[0]


def sample_gender():
    return np.random.choice(
        ["male", "female"],
        p=[0.49, 0.51]  # Slightly more females in many populations
    )


def sample_education(age: int) -> str:
    """
    Génère un niveau d'éducation en fonction de l'âge du voter.
    Les personnes âgées ont généralement un niveau d'éducation plus bas,
    et les jeunes n'ont pas encore eu le temps d'obtenir des diplômes avancés.
    """
    # Probabilités de base par niveau d'éducation (France, données approximatives)
    base_probs = {
        "none": 0.1,
        "high_school": 0.4,
        "bachelor": 0.3,
        "master": 0.15,
        "phd": 0.05
    }

    # Ajustement des probabilités en fonction de l'âge
    if age < 22:  # 18-21 ans (étudiants ou jeunes actifs)
        # Les très jeunes n'ont pas encore eu le temps de faire des études longues
        return np.random.choice(
            ["high_school", "bachelor"],
            p=[0.7, 0.3]  # 70% ont seulement le bac, 30% ont commencé un bachelor
        )
    elif age < 25:  # 22-24 ans
        # Certains ont terminé un bachelor, peu ont un master
        return np.random.choice(
            ["high_school", "bachelor", "master"],
            p=[0.3, 0.6, 0.1]
        )
    elif age < 30:  # 25-29 ans
        # Âge où beaucoup terminent leurs études supérieures
        return np.random.choice(
            ["high_school", "bachelor", "master", "phd"],
            p=[0.2, 0.4, 0.35, 0.05]
        )
    elif age < 40:  # 30-39 ans
        # Âge où les gens ont généralement terminé leurs études
        return np.random.choice(
            ["high_school", "bachelor", "master", "phd"],
            p=[0.2, 0.4, 0.3, 0.1]
        )
    elif age < 60:  # 40-59 ans
        # Génération avec un niveau d'éducation généralement plus élevé
        adjusted_probs = {
            "none": base_probs["none"] * 0.7,
            "high_school": base_probs["high_school"] * 0.9,
            "bachelor": base_probs["bachelor"] * 1.1,
            "master": base_probs["master"] * 1.2,
            "phd": base_probs["phd"] * 1.3
        }
    else:  # 60+ ans
        # Générations plus âgées avec un niveau d'éducation généralement plus bas
        adjusted_probs = {
            "none": base_probs["none"] * 2.0,
            "high_school": base_probs["high_school"] * 1.3,
            "bachelor": base_probs["bachelor"] * 0.7,
            "master": base_probs["master"] * 0.5,
            "phd": base_probs["phd"] * 0.3
        }

    # Normaliser les probabilités pour qu'elles sommement à 1
    if age >= 40:
        total = sum(adjusted_probs.values())
        normalized_probs = [v/total for v in adjusted_probs.values()]
        return np.random.choice(
            list(adjusted_probs.keys()),
            p=normalized_probs
        )

    # Pour les 30-39 ans, utiliser les probabilités de base
    return np.random.choice(
        list(base_probs.keys()),
        p=list(base_probs.values())
    )


def assign_issue_priorities(age, gender, region, education, income,
                            employment_status, family_status,
                            ethnicity_immigration, religion):
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

    political_lean = 1.0  # Neutral by default (1.0), >1.0 is conservative, <1.0 is progressive

    # Age influence
    if age < 30:
        issue_priorities["environment"] = random.uniform(0.7, 1.0)
        issue_priorities["education"] = random.uniform(0.6, 0.9)
        issue_priorities["climate_change"] = random.uniform(0.6, 0.9)
        issue_priorities["gender_equality"] = random.uniform(0.6, 0.9)
        issue_priorities["public_transport"] = random.uniform(0.5, 0.8)
        political_lean *= random.uniform(0.8, 0.9)  # Younger voters tend to be more progressive
    elif age > 60:
        issue_priorities["healthcare"] = random.uniform(0.7, 1.0)
        issue_priorities["pensions"] = random.uniform(0.6, 0.9)
        political_lean *= random.uniform(1.1, 1.2)  # Older voters tend to be more conservative
    else:
        issue_priorities["economy"] = random.uniform(0.6, 0.9)
        issue_priorities["jobs"] = random.uniform(0.5, 0.8)

    # Gender influence
    if gender == "female":
        issue_priorities["healthcare"] *= random.uniform(1.1, 1.3)
        issue_priorities["education"] *= random.uniform(1.1, 1.2)
        issue_priorities["gender_equality"] *= random.uniform(1.1, 1.3)
        issue_priorities["social_welfare"] *= random.uniform(1.0, 1.2)
        issue_priorities["crime_safety"] *= random.uniform(1.0, 1.2)
        political_lean *= random.uniform(0.8, 0.95)  # Females may lean slightly more progressive
    else:
        issue_priorities["economy"] *= random.uniform(1.1, 1.3)
        issue_priorities["defense"] *= random.uniform(1.1, 1.3)
        political_lean *= random.uniform(1.05, 1.15)  # Males may lean slightly more conservative

    # Region influence
    if region == "urban":
        issue_priorities["public_transport"] = random.uniform(0.7, 1.0)
        issue_priorities["environment"] = random.uniform(0.6, 0.9)
        issue_priorities["housing"] = random.uniform(0.6, 0.9)
        issue_priorities["climate_change"] = random.uniform(0.6, 0.9)
    elif region == "rural":
        issue_priorities["agriculture"] = random.uniform(0.7, 1.0)
        issue_priorities["infrastructure"] = random.uniform(0.6, 0.9)
        issue_priorities["defense"] = random.uniform(0.6, 0.9)
    else:  # suburban
        issue_priorities["education"] = random.uniform(0.7, 1.0)
        issue_priorities["taxes"] = random.uniform(0.5, 0.8)
        issue_priorities["housing"] = random.uniform(0.6, 0.9)

    # Education influence
    if education in ["none", "high_school"]:
        issue_priorities["social_welfare"] *= random.uniform(1.1, 1.4)
        issue_priorities["economy"] *= random.uniform(1.1, 1.3)
        if age > 50:
            political_lean *= random.uniform(1.05, 1.2)  # Less educated older voters tend to be more conservative
    elif education in ["master", "phd"]:
        issue_priorities["environment"] *= random.uniform(1.1, 1.4)
        issue_priorities["education"] *= random.uniform(1.2, 1.5)
        issue_priorities["technology_innovation"] = random.uniform(0.7, 1.0)
        issue_priorities["climate_change"] *= random.uniform(1.1, 1.4)
        political_lean *= random.uniform(0.8, 0.95)  # More educated voters tend to be more progressive

    # Income influence
    if income == "low":
        issue_priorities["social_welfare"] = random.uniform(0.8, 1.0)
        issue_priorities["minimum_wage"] = random.uniform(0.7, 0.9)
        issue_priorities["healthcare"] *= random.uniform(1.1, 1.3)
        issue_priorities["housing"] = random.uniform(0.7, 1.0)
        political_lean *= random.uniform(0.8, 0.95)  # Lower income voters tend to be more progressive
    elif income == "high":
        issue_priorities["taxes"] = random.uniform(0.7, 1.0)
        issue_priorities["business_regulation"] = random.uniform(0.5, 0.8)
        issue_priorities["economy"] *= random.uniform(1.1, 1.3)
        political_lean *= random.uniform(1.05, 1.2)  # Higher income voters tend to be more conservative

    # Employment status influence
    if employment_status == "unemployed":
        issue_priorities["social_welfare"] *= random.uniform(1.2, 1.5)
        issue_priorities["jobs"] = random.uniform(0.8, 1.0)
        issue_priorities["minimum_wage"] = random.uniform(0.8, 1.0)
        political_lean *= random.uniform(0.8, 0.95)  # Unemployed voters tend to be more progressive
    elif employment_status == "employed":
        issue_priorities["economy"] *= random.uniform(1.1, 1.3)
        issue_priorities["taxes"] *= random.uniform(1.0, 1.2)

    # Family status influence
    if family_status == "with_children":
        issue_priorities["education"] *= random.uniform(1.2, 1.5)
        issue_priorities["healthcare"] *= random.uniform(1.1, 1.3)
        issue_priorities["housing"] *= random.uniform(1.1, 1.3)
    elif family_status == "single":
        issue_priorities["social_welfare"] *= random.uniform(1.0, 1.2)
        issue_priorities["taxes"] *= random.uniform(1.0, 1.2)

    # Ethnicity/Immigration influence
    if ethnicity_immigration == "immigrant":
        issue_priorities["immigration"] = random.uniform(0.8, 1.0)
        issue_priorities["social_welfare"] *= random.uniform(1.1, 1.3)
        issue_priorities["gender_equality"] *= random.uniform(1.1, 1.3)
        political_lean *= random.uniform(0.8, 0.95)  # Immigrants may lean more progressive
    else:
        issue_priorities["defense"] *= random.uniform(1.0, 1.2)
        issue_priorities["immigration"] *= random.uniform(0.8, 1.0)

    # Religion influence
    if religion == "religious":
        issue_priorities["gender_equality"] *= random.uniform(0.8, 1.0)
        issue_priorities["social_welfare"] *= random.uniform(1.0, 1.2)
        issue_priorities["education"] *= random.uniform(0.9, 1.1)
        political_lean *= random.uniform(1.1, 1.2)  # Religious voters tend to be more conservative
    else:
        issue_priorities["gender_equality"] *= random.uniform(1.1, 1.3)
        issue_priorities["climate_change"] *= random.uniform(1.0, 1.2)
        political_lean *= random.uniform(0.8, 0.95)  # Non-religious voters tend to be more progressive

    return issue_priorities, political_lean


# --- 1. Generate Voters and Candidates ---
def create_voter(issues: List[str], voter_id: int) -> Voter:
    age = sample_age()
    gender = sample_gender()
    region = sample_region()
    income = sample_income()
    education = sample_education(age)
    employment_status = sample_employment_status()
    family_status = sample_family_status()
    religion = sample_religion()
    ethnicity_immigration = sample_ethnicity_immigration()

    issue_priorities, political_lean = assign_issue_priorities(
        age, gender, region, education, income, employment_status,
        family_status, ethnicity_immigration, religion
    )

    # Normalize so priorities sum to ~1
    total = sum(issue_priorities.values())
    issue_priorities = {k: v / total for k, v in issue_priorities.items()}

    # L'éducation influence la probabilité de voter (effet plus marqué avec l'âge)
    education_vote_boost = {
        "none": 0.0,
        "high_school": 0.05,
        "bachelor": 0.1,
        "master": 0.15,
        "phd": 0.2
    }[education]

    # Les personnes âgées éduquées votent encore plus
    if age > 60 and education in ["master", "phd"]:
        education_vote_boost += 0.1

    return {
        "id": voter_id,  # Ajouter l'ID ici
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
        "issue_priorities": issue_priorities,
        "party_loyalty": random.uniform(0, 1),
        "preferred_party": random.choice(["Green", "Conservative", "Liberal",
                                          "Independent"]),
        # More extreme = more likely to vote
        "likelihood_to_vote": float(min(0.95, sample_likelihood_to_vote(age) + education_vote_boost)),
        "mood": random.uniform(-1, 1),
    }


def create_candidate(issues: List[str], candidate_id: int, name: str, party: str) -> Dict:
    """Create a candidate with random policies."""
    # Map party to a political lean (-1 to 1)
    party_leans = {"Green": -0.8, "Liberal": -0.3, "Conservative": 0.7, "Independent": 0.0}

    # Create policies that align with party lean
    policies = {}
    for issue in issues:
        # Base policy position influenced by party lean
        base_position = (party_leans.get(party, 0) + 1) / 2  # Convert to 0-1 range
        # Add some variation but keep it close to party line
        variation = random.uniform(-0.2, 0.2)
        policies[issue] = max(0, min(1, base_position + variation))

    return {
        "id": candidate_id,
        "name": name,
        "party": party,
        "party_lean": party_leans.get(party, 0),
        "policies": policies,
        "charisma": random.uniform(0.5, 1.0),  # Candidates generally have some charisma
        "scandals": random.randint(0, 2),
        "campaign_funds": random.uniform(100000, 1000000),  # Adding campaign funds
        "experience": random.randint(1, 20),  # Years of political experience
        "popularity": random.uniform(0.3, 0.9)  # Base popularity
    }


# --- 2. Utility Calculation ---
def calculate_utility(voter: Dict, candidate: Dict, issues: List[str]) -> Dict:
    """
    Calculate the utility score for a voter-candidate pair.
    Returns a dictionary with the utility score and its breakdown.
    """
    # Issue alignment
    issue_score = sum(
        voter["issue_priorities"].get(issue, 0) * candidate["policies"].get(issue, 0)
        for issue in issues
    )

    # Gender-specific bonus
    gender_bonus = 0
    if voter["gender"] == "female" and "gender_equality" in candidate["policies"]:
        gender_bonus = 0.1 * candidate["policies"]["gender_equality"]
        issue_score += gender_bonus

    # Party loyalty
    party_match = 1 - abs(voter["political_lean"] - candidate.get("party_lean", 0))
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
        0.6 * issue_score +
        0.2 * loyalty_bonus +
        0.15 * charisma_effect +
        scandal_penalty +
        mood_effect
    )

    # Determine if voter will vote for this candidate
    will_vote = random.random() < voter["likelihood_to_vote"] and utility > 0.3

    return {
        "voter_id": voter["id"],
        "candidate_id": candidate["id"],
        "utility": round(utility, 4),
        "will_vote": will_vote,
        "breakdown": {
            "issue_score": round(issue_score, 4),
            "loyalty_bonus": round(loyalty_bonus, 4),
            "charisma_effect": round(charisma_effect, 4),
            "scandal_penalty": round(scandal_penalty, 4),
            "mood_effect": round(mood_effect, 4),
            "gender_bonus": round(gender_bonus, 4) if gender_bonus else 0
        }
    }


# --- 3. Voting Methods ---
def vote_plurality(voter: Voter, candidates: List[Candidate], issues: List[str]) -> Optional[str]:
    utilities = {c["name"]: calculate_utility(voter, c, issues) for c in candidates}
    max_utility = max(utilities.values())
    return max(utilities, key=utilities.get) if max_utility > 0.3 else None


def vote_ranked(voter: Voter, candidates: List[Candidate], issues: List[str]) -> List[str]:
    return sorted(candidates, key=lambda c: -calculate_utility(voter, c, issues))


def vote_score(voter: Voter, candidates: List[Candidate], issues: List[str]) -> Dict[str, int]:
    return {c["name"]: int(5 * calculate_utility(voter, c, issues)) for c in candidates}


def simulate_vote(
    voter: Voter,
    candidates: List[Candidate],
    issues: List[str],
    method: str = "plurality"
) -> Union[Optional[str], List[str], Dict[str, int]]:
    if random.random() > voter["likelihood_to_vote"]:
        return None
    if method == "plurality":
        return vote_plurality(voter, candidates, issues)
    elif method == "ranked":
        return [c["name"] for c in vote_ranked(voter, candidates, issues)]
    elif method == "score":
        return vote_score(voter, candidates, issues)
    else:
        return None


# --- 4. Run Simulation ---
def run_simulation(num_voters: int = 1000, num_candidates: int = 3, method: str = "plurality"):
    issues = ["economy", "environment", "healthcare"]
    voters = [create_voter(issues) for _ in range(num_voters)]
    candidates = [
        create_candidate(issues, f"Candidate {i+1}", party)
        for i, party in enumerate(["Green", "Conservative", "Liberal"])
    ]

    results = []
    for voter in voters:
        vote = simulate_vote(voter, candidates, issues, method)
        results.append({
            "voter": voter,
            "vote": vote,
            "utilities": {c["name"]: calculate_utility(voter, c, issues) for c in candidates}
        })
    return results


# --- 5. Analyze Results ---
def analyze_results(results: List[Dict]):
    votes = [r["vote"] for r in results if r["vote"] is not None]
    print(f"Turnout: {len(votes) / len(results):.1%}")
    if isinstance(votes[0], str):  # Plurality
        from collections import Counter
        print("Plurality results:", Counter(votes))
    elif isinstance(votes[0], list):  # Ranked
        print("Ranked-choice first preferences:", Counter(v[0] for v in votes))
    elif isinstance(votes[0], dict):  # Score
        scores = {c: sum(v.get(c, 0) for v in votes) for c in votes[0].keys()}
        print("Score voting totals:", scores)


# --- 6. Example Usage ---
if __name__ == "__main__":
    results = run_simulation(num_voters=1000, method="plurality")
    analyze_results(results)
    # Save results for visualization
    import json
    with open("election_results.json", "w") as f:
        json.dump(results, f)
