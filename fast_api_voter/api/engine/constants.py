"""
api.engine.constants — shared issue taxonomy for the simulation engine.

Relocated from app/constants.py in Phase 4.5.b. `app/constants.py` re-exports
from here as a shim until the Flask `app/` package is deleted in 4.5.b.3.
"""

DEFAULT_ISSUES = [
    "economy", "environment", "healthcare", "education", "taxes",
    "social_welfare", "agriculture", "public_transport", "defense",
    "gender_equality", "pensions", "climate_change", "housing",
    "immigration", "crime_safety", "technology_innovation",
    "minimum_wage", "business_regulation", "jobs", "infrastructure",
]

ECONOMY_ISSUES = {"economy", "taxes", "business_regulation", "jobs", "minimum_wage", "infrastructure", "technology_innovation"}
ENV_ISSUES     = {"environment", "climate_change", "agriculture", "public_transport"}
SOCIAL_ISSUES  = {"social_welfare", "healthcare", "education", "gender_equality", "housing", "immigration", "crime_safety", "defense", "pensions"}
