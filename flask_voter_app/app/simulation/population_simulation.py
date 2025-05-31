import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

# Step 1: Define Voter Profiles
np.random.seed(42)
num_voters = 100000
voter_profiles = pd.DataFrame({
    'age': np.random.normal(45, 15, num_voters).astype(int),
    'gender': np.random.choice(['Male', 'Female'], num_voters),
    'location': np.random.choice(['Urban', 'Rural'], num_voters),
    'historical_preference': np.random.choice(['Left', 'Right', 'Center'], num_voters)
})

# Step 2: Generate Synthetic Data
# For simplicity, we'll use the same dataset for training and simulation
synthetic_voters = voter_profiles.copy()

# Step 3: Train a Predictive Model
# Assume we have historical voting data
historical_votes = np.random.choice(['Candidate_A', 'Candidate_B', 'Candidate_C'], num_voters)
voter_profiles['historical_vote'] = historical_votes

# Split the data into training and test sets
X_train, X_test, y_train, y_test = train_test_split(voter_profiles.drop('historical_vote', axis=1), voter_profiles['historical_vote'], test_size=0.2, random_state=42)

# Train a RandomForestClassifier
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Step 4: Simulate Voting Process
synthetic_voters['predicted_vote'] = model.predict(synthetic_voters)

# Step 5: Analyze Results
vote_counts = synthetic_voters['predicted_vote'].value_counts()
print("Simulated Voting Results:")
print(vote_counts)

# Evaluate the model
y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)
print(f"Model Accuracy: {accuracy:.2f}")

"""
Comment veux-je simuler une election ? 

    il faut definir une liste de candidats
    qu'est ce qu'un candidat et comment se definit t'il par rapport aux autres 
    
    quel est le meilleur moyen de definir les candidats les un par rapports aux autres ? 
    pouvoir les mettre sur une echelle "droite/gauche" 
    voir comment faire des liens 
        est-il plus probable que je vote pour gars a droite ou a gauche selon ce qui reste ? 

    passage par une matrice qui definit les probas 
    comment definir les probas selon les profiles 

"""

def create_custom_dataset(population_size, age_mean, age_std, income_mean, income_std, education_distribution, political_distribution):
    """
    Create a custom dataset based on user-defined parameters.

    Parameters:
    - population_size: Total number of individuals in the population.
    - age_mean: Mean age of the population.
    - age_std: Standard deviation of the age distribution.
    - income_mean: Mean income of the population.
    - income_std: Standard deviation of the income distribution.
    - education_distribution: Dictionary with education levels as keys and their respective probabilities as values.
    - political_distribution: Dictionary with political affiliations as keys and their respective probabilities as values.

    Returns:
    - A pandas DataFrame representing the population.
    """

    # Generate demographic data based on user inputs
    data = {
        'age': np.random.normal(age_mean, age_std, population_size).astype(int),
        'gender': np.random.choice(['Male', 'Female'], population_size),
        'education_level': np.random.choice(list(education_distribution.keys()), population_size, p=list(education_distribution.values())),
        'income_level': np.random.normal(income_mean, income_std, population_size).astype(int),
        'location': np.random.choice(['Urban', 'Rural'], population_size),
        'political_affiliation': np.random.choice(list(political_distribution.keys()), population_size, p=list(political_distribution.values())),
        'voting_probability': np.random.uniform(0.5, 1.0, population_size)
    }

    # Create a DataFrame
    population_df = pd.DataFrame(data)

    return population_df

voter_data = {
    'age': 45,
    'gender': 'Female',
    'education_level': 'Bachelor',
    'occupation': 'Teacher',
    'income_level': 60000,
    'marital_status': 'Married',
    'number_of_children': 2,
    'location': 'Urban',
    'region': 'Northeast',
    'zip_code': '10001',
    'party_affiliation': 'Democrat',
    'voting_history': ['2020 Election', '2016 Election'],
    'political_ideology': 'Liberal',
    'policy_priorities': ['Education', 'Healthcare', 'Environment'],
    'candidate_preferences': {'Candidate A': 8, 'Candidate B': 5},
    'news_sources': ['CNN', 'New York Times'],
    'social_media_use': 'Daily',
    'media_consumption': 'Online',
    'voter_turnout': 'Likely',
    'community_involvement': 'Occasionally',
    'volunteer_work': 'Yes',
    'values_and_beliefs': 'Equality, Education',
    'lifestyle': 'Active, Environmentally-conscious'
}