"""Tests for demographic data sampling functions."""

import pytest
from app.utils.demographic_data import (
    sample_age,
    sample_region,
    sample_income,
    sample_likelihood_to_vote,
    sample_political_lean,
    sample_employment_status,
    sample_family_status,
    sample_ethnicity_immigration,
    sample_religion,
    sample_gender,
    sample_education,
)


VALID_REGIONS = {"urban", "suburban", "rural"}
VALID_INCOMES = {"low", "middle", "high"}
VALID_EMPLOYMENTS = {"employed", "unemployed", "self_employed", "retired"}
VALID_FAMILY_STATUSES = {"single", "with_children", "retired"}
VALID_ETHNICITIES = {"native", "immigrant"}
VALID_RELIGIONS = {"religious", "non_religious"}
VALID_GENDERS = {"male", "female"}
VALID_EDUCATIONS = {"none", "high_school", "bachelor", "master", "phd"}


class TestSampleAge:

    def test_age_in_valid_range(self):
        for _ in range(500):
            age = sample_age()
            assert 18 <= age <= 85

    def test_age_is_int(self):
        age = sample_age()
        assert isinstance(age, int)


class TestSampleRegion:

    def test_returns_valid_region(self):
        for _ in range(100):
            assert sample_region() in VALID_REGIONS

    def test_urban_is_most_common(self):
        regions = [sample_region() for _ in range(2000)]
        urban_pct = regions.count("urban") / len(regions)
        assert urban_pct > 0.6


class TestSampleIncome:

    def test_returns_valid_income(self):
        for _ in range(100):
            assert sample_income() in VALID_INCOMES

    def test_low_and_middle_dominate(self):
        incomes = [sample_income() for _ in range(2000)]
        low_pct = incomes.count("low") / len(incomes)
        middle_pct = incomes.count("middle") / len(incomes)
        high_pct = incomes.count("high") / len(incomes)
        assert low_pct + middle_pct > high_pct
        assert all(0.1 < pct < 0.7 for pct in (low_pct, middle_pct, high_pct))


class TestSampleLikelihoodToVote:

    def test_returns_float_between_0_and_1(self):
        for age in [18, 30, 45, 60, 85]:
            val = sample_likelihood_to_vote(age)
            assert 0.0 <= val <= 1.0

    def test_increases_with_age(self):
        young = sample_likelihood_to_vote(20)
        old = sample_likelihood_to_vote(80)
        assert old >= young


class TestSamplePoliticalLean:

    def test_returns_float(self):
        val = sample_political_lean()
        assert isinstance(val, float)

    def test_bimodal_distribution(self):
        values = [sample_political_lean() for _ in range(500)]
        neg = sum(1 for v in values if v < -0.2)
        pos = sum(1 for v in values if v > 0.2)
        assert neg > 50
        assert pos > 50


class TestSampleEmploymentStatus:

    def test_returns_valid_status(self):
        for _ in range(100):
            assert sample_employment_status() in VALID_EMPLOYMENTS

    def test_employed_is_most_common(self):
        statuses = [sample_employment_status() for _ in range(2000)]
        employed_pct = statuses.count("employed") / len(statuses)
        assert employed_pct > 0.4


class TestSampleFamilyStatus:

    def test_returns_valid_status(self):
        for _ in range(100):
            assert sample_family_status() in VALID_FAMILY_STATUSES


class TestSampleEthnicityImmigration:

    def test_returns_valid_value(self):
        for _ in range(100):
            assert sample_ethnicity_immigration() in VALID_ETHNICITIES

    def test_native_is_more_common(self):
        values = [sample_ethnicity_immigration() for _ in range(2000)]
        native_pct = values.count("native") / len(values)
        assert native_pct > 0.6


class TestSampleReligion:

    def test_returns_valid_value(self):
        for _ in range(100):
            assert sample_religion() in VALID_RELIGIONS


class TestSampleGender:

    def test_returns_valid_gender(self):
        for _ in range(100):
            assert sample_gender() in VALID_GENDERS


class TestSampleEducation:

    def test_returns_valid_education(self):
        for age in [18, 21, 25, 35, 50, 70]:
            for _ in range(50):
                assert sample_education(age) in VALID_EDUCATIONS

    def test_young_never_phd(self):
        for _ in range(200):
            edu = sample_education(18)
            assert edu != "phd"

    def test_older_has_more_none(self):
        young = [sample_education(25) for _ in range(500)]
        old = [sample_education(70) for _ in range(500)]
        young_none = young.count("none") / len(young)
        old_none = old.count("none") / len(old)
        assert old_none > young_none

    def test_mid_career_has_more_advanced_degrees(self):
        mid = [sample_education(35) for _ in range(500)]
        old = [sample_education(70) for _ in range(500)]
        mid_advanced = mid.count("master") + mid.count("phd")
        old_advanced = old.count("master") + old.count("phd")
        assert mid_advanced >= old_advanced
