import numpy as np
from scipy.stats import truncnorm

######################################################################
#
# Simulation d'une population sur une grille de repartition politique
#
######################################################################


def repartition_votants(age_moyen, nb_voters):
    # Paramètres pour la distribution tronquée
    age_min = 18
    age_max = 85

    # Calculer les paramètres a et b pour la distribution tronquée
    std_dev = 15  # Écart-type supposé
    a = (age_min - age_moyen) / std_dev
    b = (age_max - age_moyen) / std_dev

    # Générer des âges aléatoires selon une distribution normale tronquée
    ages = truncnorm.rvs(a, b, loc=age_moyen, scale=std_dev, size=nb_voters)

    return ages


def generate_coordinates(age):
    if age < 18 or age > 85:
        raise ValueError("L'âge doit être compris entre 18 et 85 ans.")

    # Normaliser l'âge pour qu'il soit compris entre 0 et 1
    normalized_age = (age - 18) / (85 - 18)

    mean = -4 + 8 * normalized_age

    # Générer des coordonnées x et y en fonction de l'âge normalisé
    # Plus l'âge est grand, plus les coordonnées sont positives
    x = np.random.normal(mean, 1)
    y = np.random.normal(mean, 1)

    # Ajouter un léger bruit aléatoire pour varier les coordonnées
    x += np.random.uniform(-0.5, 0.5)
    y += np.random.uniform(-0.5, 0.5)

    # S'assurer que les coordonnées restent dans la plage [-5, 5]
    x = max(-5, min(5, x))
    y = max(-5, min(5, y))

    return {"x": x, "y": y}


def simulate_population(nb_voters, avg_age):
    coord = []
    for age in repartition_votants(avg_age, nb_voters):
        coord += [generate_coordinates(age)]

    return coord


def generate_coord_candidates(nb_candidates):
    x_coords = np.random.uniform(-5, 5, nb_candidates)
    y_coords = np.random.uniform(-5, 5, nb_candidates)

    return list(zip(x_coords, y_coords))


def assign_voters_to_candidates(voters, candidates):
    assignements = []
    for voter in voters:
        distances = [
            np.linalg.norm(np.array(voter) - np.array(candidate))
            for candidate in candidates
        ]

        closest_candidate_index = np.argmin(distances)

        assignements.append(closest_candidate_index)

    return assignements
