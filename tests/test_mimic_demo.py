"""
Unit tests for MIMIC Demo pipeline, cohort selection, target construction,
and zero-leakage feature extraction.
"""

import os
import pytest
import pandas as pd
from src.mimic.loader import MIMICDataLoader
from src.mimic.cohort import MIMICCohortSelector
from src.mimic.extractor import MIMICFeatureExtractor
from src.mimic.config import MIMICConfig

DEMO_DIR = r"C:\Users\Sneha\Desktop\College sem 5\project\CareMind\data\MIMIC_Demo\mimic-iv-clinical-database-demo-2.2"


@pytest.mark.skipif(not os.path.exists(DEMO_DIR), reason="MIMIC Demo dataset directory not found.")
def test_mimic_demo_data_loader():
    """Verify MIMICDataLoader loads demo tables without error."""
    loader = MIMICDataLoader(DEMO_DIR)
    patients = loader.load_patients()
    admissions = loader.load_admissions()
    icustays = loader.load_icustays()

    assert len(patients) == 100
    assert len(admissions) == 275
    assert len(icustays) == 140


@pytest.mark.skipif(not os.path.exists(DEMO_DIR), reason="MIMIC Demo dataset directory not found.")
def test_mimic_demo_cohort_selection():
    """Verify MIMICCohortSelector filters 85 valid cohort stays on demo data."""
    loader = MIMICDataLoader(DEMO_DIR)
    patients = loader.load_patients()
    admissions = loader.load_admissions()
    icustays = loader.load_icustays()

    selector = MIMICCohortSelector()
    cohort, stats = selector.build_cohort(patients, admissions, icustays)

    assert stats["initial_icu_stays"] == 140
    assert stats["adult_stays"] == 140
    assert stats["first_icu_stays"] == 100
    assert stats["los_ge_24h_stays"] == 85
    assert stats["survived_initial_24h_stays"] == 85
    assert len(cohort) == 85
    assert "Mortality24h" in cohort.columns
    assert "InHospMortalityPost24h" in cohort.columns


@pytest.mark.skipif(not os.path.exists(DEMO_DIR), reason="MIMIC Demo dataset directory not found.")
def test_mimic_demo_feature_extraction_zero_leakage():
    """Verify MIMICFeatureExtractor enforces 100% zero-leakage temporal firewall."""
    loader = MIMICDataLoader(DEMO_DIR)
    patients = loader.load_patients()
    admissions = loader.load_admissions()
    icustays = loader.load_icustays()
    chartevents = loader.load_chartevents()
    labevents = loader.load_labevents()

    selector = MIMICCohortSelector()
    cohort, _ = selector.build_cohort(patients, admissions, icustays)

    extractor = MIMICFeatureExtractor()
    features, audit = extractor.extract_features(cohort, chartevents, labevents)

    assert len(features) == 85
    assert audit["leakage_violations"] == 0
    assert audit["rejected_future_events"] > 0
    assert "HR_mean" in features.columns
    assert "is_missing_HR" in features.columns
