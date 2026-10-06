"""
Test suite for MIMIC Research & Data Plan implementation (Audited Feasibility).

Validates MIMICConfig, MIMICItemIDs, MIMICAccessChecker, and MIMICSchemaValidator.
"""

import os
import pytest
import pandas as pd
from src.mimic.config import MIMICConfig, MIMICItemIDs
from src.mimic.access_checker import MIMICAccessChecker
from src.mimic.schema import MIMICSchemaValidator


def test_mimic_config_defaults():
    """Verify MIMICConfig default values, audited targets, and waveform tier definitions."""
    config = MIMICConfig()
    assert config.clinical_subset_size == 1000
    assert config.waveform_subset_size == 100
    assert config.observation_window_hours == 24.0
    assert config.prediction_window_hours == 24.0
    assert config.primary_target_column == "Mortality24h"
    assert config.secondary_target_column == "AcuteDeterioration24h"
    assert "HR" in config.core_vitals
    assert "SpO2" in config.core_vitals
    assert "II" in config.tier1_waveforms
    assert "ABP" in config.tier1_waveforms
    assert "PLETH" in config.tier1_waveforms


def test_mimic_item_ids():
    """Verify PhysioNet itemids mapped for chartevents and labevents."""
    itemids = MIMICItemIDs()
    assert 220045 in itemids.HEART_RATE
    assert 220050 in itemids.SYS_BP
    assert 220179 in itemids.SYS_BP
    assert 220277 in itemids.SPO2
    assert 50813 in itemids.LACTATE
    assert 51301 in itemids.WBC


def test_mimic_access_checker_initialization(tmp_path):
    """Verify directory creation and access guidance reporting."""
    test_data_dir = str(tmp_path / "mimic")
    test_clinical_dir = str(tmp_path / "mimic" / "clinical")
    test_waveform_dir = str(tmp_path / "mimic" / "waveform")
    test_processed_dir = str(tmp_path / "mimic" / "processed")

    config = MIMICConfig(
        data_dir=test_data_dir,
        clinical_dir=test_clinical_dir,
        waveform_dir=test_waveform_dir,
        processed_dir=test_processed_dir,
    )

    checker = MIMICAccessChecker(config=config)
    created = checker.initialize_directories()

    assert os.path.exists(test_data_dir)
    assert os.path.exists(test_clinical_dir)
    assert os.path.exists(test_waveform_dir)
    assert os.path.exists(test_processed_dir)

    status = checker.verify_environment()
    assert status["checklist"]["data_directories_prepared"] is True
    assert len(status["user_action_guidance"]) == 6


def test_mimic_schema_validator():
    """Verify MIMICSchemaValidator profiling on synthetic patient stay DataFrame."""
    config = MIMICConfig()
    validator = MIMICSchemaValidator(config=config)

    synthetic_df = pd.DataFrame({
        "subject_id": [10001, 10001, 10002],
        "stay_id": [30001, 30001, 30002],
        "HR": [80.0, 85.0, 90.0],
        "SBP": [120.0, 118.0, 115.0],
        "DBP": [75.0, 72.0, 70.0],
        "MAP": [90.0, 87.0, 85.0],
        "SpO2": [98.0, 97.0, 99.0],
        "Resp": [16.0, 18.0, 17.0],
        "Temp": [37.0, 37.2, 36.8],
        "Mortality24h": [0, 0, 1]
    })

    report = validator.validate_clinical_schema(synthetic_df)
    assert report["is_valid_schema"] is True
    assert report["unique_subjects"] == 2
    assert report["unique_stays"] == 2
    assert report["has_target_column"] is True
    assert report["target_stats"]["positive_rows"] == 1


def test_mimic_schema_validator_invalid():
    """Verify MIMICSchemaValidator raises ValueError when required identifier columns are missing."""
    validator = MIMICSchemaValidator()
    invalid_df = pd.DataFrame({"invalid_col": [1, 2, 3]})

    with pytest.raises(ValueError, match="Missing required identifier columns"):
        validator.validate_clinical_schema(invalid_df)
