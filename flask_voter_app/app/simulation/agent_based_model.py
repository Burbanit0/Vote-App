import random
import numpy as np

class Elector:
    def __init__(self, preference, num_choices, age):
        self.preference = preference  # Initial preference
        self.num_choices = num_choices  # Total number of choices
        self.age = age # Age of the elector
        
    def influence(self, other, influence_matrix):
        # Determine the probability of changing preference based on the influence matrix
        current_pref = self.preference
        other_pref = other.preference
        if random.random() < influence_matrix[current_pref, other_pref]:
            self.preference = other_pref

def simulate_election(num_electors, num_choices, influence_matrix, num_steps):
    # Initialize electors with random preferences
    electors = [Elector(random.randint(0, num_choices - 1), num_choices) for _ in range(num_electors)]

    for step in range(num_steps):
        # Each elector interacts with another random elector
        for elector in electors:
            other = random.choice(electors)
            elector.influence(other, influence_matrix)

    # Count the final preferences
    preferences = [elector.preference for elector in electors]
    preference_counts = [preferences.count(i) for i in range(num_choices)]
    return preference_counts

# Example usage
num_electors = 1000
num_choices = 3  # Number of choices (e.g., candidates)
influence_matrix = np.array([
    [0.1, 0.2, 0.3],  # Probability of changing from choice 0 to others
    [0.2, 0.1, 0.4],  # Probability of changing from choice 1 to others
    [0.3, 0.4, 0.1]   # Probability of changing from choice 2 to others
])
num_steps = 10

preference_counts = simulate_election(num_electors, num_choices, influence_matrix, num_steps)

print("Final preference counts:", preference_counts)