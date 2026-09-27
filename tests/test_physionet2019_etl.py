"""
Automated Pytest Suite for CareMind PhysioNet 2019 Data Acquisition & ETL Pipeline.
"""

import os
import shutil
import pytest
import pandas as pd
import numpy as np

from src.physionet2019.downloader import generate_synthetic_physionet2019
from src.physionet2019.loader import PhysioNet2019Loader, REQUIRED_VITAL_COLUMNS
from src.physionet2019.validator import PhysioNet2019Validator
from src.physionet2019.cleaner import PhysioNet2019Cleaner
from src.physionet2019.transformer import PhysioNet2019Transformer
from src.physionet2019.splitter import PhysioNet2019Splitter
from src.physionet2019.pipeline import run_physionet2019_pipeline


@pytest.fixture(scope="session")
def test_raw_dir(tmp_path_factory):
    """Fixture to generate temporary raw dataset for testing."""
    tmp_dir = str(tmp_path_factory.mktemp("raw_physionet2019"))
    generate_synthetic_physionet2019(raw_dir=tmp_dir, num_patients_per_set=20, seed=123)
    return tmp_dir


def test_dataset_loader(test_raw_dir):
    """Test loader discovers files, loads DataFrames, and preserves patient ID & time steps."""
    loader = PhysioNet2019Loader(raw_dir=test_raw_dir)
    files = loader.discover_patient_files()
    assert len(files) == 40, f"Expected 40 patient files, found {len(files)}."

    p_id, p_path = files[0]
    df_single = loader.load_single_patient(p_path, patient_id=p_id)
    
    assert "patient_id" in df_single.columns
    assert (df_single["patient_id"] == p_id).all()
    assert "time_step" in df_single.columns
    assert "SepsisLabel" in df_single.columns

    for vital in REQUIRED_VITAL_COLUMNS:
        assert vital in df_single.columns, f"Missing vital: {vital}"

    df_all = loader.load_all_patients()
    assert len(df_all["patient_id"].unique()) == 40
    assert len(df_all) > 0


def test_validator_and_profiler(test_raw_dir):
    """Test validator computes missingness, patient length stats, and checks temporal ordering."""
    loader = PhysioNet2019Loader(raw_dir=test_raw_dir)
    df = loader.load_all_patients()

    validator = PhysioNet2019Validator()
    report = validator.profile_dataset(df)

    assert report["num_patient_files"] == 40
    assert report["patient_length_stats"]["min_stay_hours"] > 0
    assert "HR" in report["missingness"]
    assert "SepsisLabel" in df.columns
    assert report["temporal_ordering_violations"] == 0


def test_cleaner_outlier_clipping_and_imputation(test_raw_dir):
    """Test cleaner clips impossible outliers and performs LOCF imputation."""
    loader = PhysioNet2019Loader(raw_dir=test_raw_dir)
    raw_df = loader.load_all_patients()

    # Introduce synthetic outliers into raw_df to verify clipping
    dirty_df = raw_df.copy()
    dirty_df.loc[0, "HR"] = 999.0   # Impossible HR
    dirty_df.loc[1, "O2Sat"] = -5.0  # Impossible SpO2

    cleaner = PhysioNet2019Cleaner(impute_vitals=True)
    cleaned_df = cleaner.clean(dirty_df, is_training=True)

    # Check outliers were sanitized
    assert cleaned_df.loc[0, "HR"] != 999.0
    assert cleaned_df.loc[1, "O2Sat"] != -5.0
    # Imputation should reduce NaNs in vitals
    assert cleaned_df["HR"].isna().sum() == 0
    assert cleaned_df["O2Sat"].isna().sum() == 0


def test_train_only_imputation_fitting(test_raw_dir):
    """Test that cleaner enforces train-only median fitting and prevents validation data leakage."""
    loader = PhysioNet2019Loader(raw_dir=test_raw_dir)
    raw_df = loader.load_all_patients()

    splitter = PhysioNet2019Splitter(seed=42)
    train_raw, val_raw, _, _ = splitter.split_dataframe(raw_df)

    cleaner = PhysioNet2019Cleaner(impute_vitals=True)

    # 1. Calling clean(val_raw, is_training=False) before fitting on train MUST raise RuntimeError
    with pytest.raises(RuntimeError):
        cleaner.clean(val_raw, is_training=False)

    # 2. Fit cleaner on train_raw
    clean_train = cleaner.clean(train_raw, is_training=True)
    fitted_train_medians = cleaner.cohort_medians_.copy()
    assert len(fitted_train_medians) > 0

    # 3. Clean val_raw using fitted train medians
    clean_val = cleaner.clean(val_raw, is_training=False)
    assert cleaner.cohort_medians_ == fitted_train_medians


def test_feature_transformer(test_raw_dir):
    """Test transformer creates deltas, rolling stats, and missingness flags."""
    loader = PhysioNet2019Loader(raw_dir=test_raw_dir)
    raw_df = loader.load_all_patients()

    cleaner = PhysioNet2019Cleaner(impute_vitals=True)
    clean_df = cleaner.clean(raw_df, is_training=True)

    transformer = PhysioNet2019Transformer()
    transformed_df = transformer.transform(raw_df=raw_df, clean_df=clean_df)

    # Check derived columns
    assert "is_missing_HR" in transformed_df.columns
    assert "delta_HR_1h" in transformed_df.columns
    assert "rolling_mean_HR_3h" in transformed_df.columns
    assert "rolling_std_HR_3h" in transformed_df.columns
    # Check original variables preserved
    assert "HR" in transformed_df.columns
    assert "SepsisLabel" in transformed_df.columns


def test_leakage_safe_patient_splitter(test_raw_dir):
    """Test patient-level splitter enforces 0% patient leakage and reproducibility."""
    loader = PhysioNet2019Loader(raw_dir=test_raw_dir)
    df = loader.load_all_patients()

    splitter = PhysioNet2019Splitter(seed=42)
    train_df, val_df, test_df, meta = splitter.split_dataframe(df)

    train_pts = set(train_df["patient_id"].unique())
    val_pts = set(val_df["patient_id"].unique())
    test_pts = set(test_df["patient_id"].unique())

    # Assert mutual exclusivity (0% leakage)
    assert len(train_pts & val_pts) == 0
    assert len(train_pts & test_pts) == 0
    assert len(val_pts & test_pts) == 0
    assert len(train_pts) + len(val_pts) + len(test_pts) == 40

    # Test reproducibility
    train_df2, val_df2, test_df2, _ = splitter.split_dataframe(df)
    assert set(train_df2["patient_id"].unique()) == train_pts
    assert set(val_df2["patient_id"].unique()) == val_pts


def test_full_pipeline_execution(tmp_path):
    """Test full end-to-end pipeline execution from raw to processed parquet outputs."""
    raw_dir = str(tmp_path / "raw")
    processed_dir = str(tmp_path / "processed")
    generate_synthetic_physionet2019(raw_dir=raw_dir, num_patients_per_set=15, seed=99)

    meta = run_physionet2019_pipeline(
        raw_dir=raw_dir,
        processed_dir=processed_dir,
        max_patients=30,
        download_if_missing=False,
        seed=100
    )

    assert meta["leakage_free_architecture"] == "Train-Only Fitted Preprocessing (Patient Split First)"
    assert os.path.exists(meta["output_files"]["train"])
    assert os.path.exists(meta["output_files"]["val"])
    assert os.path.exists(meta["output_files"]["test"])
    assert os.path.exists(meta["output_files"]["metadata"])

    df_train = pd.read_parquet(meta["output_files"]["train"])
    assert not df_train.empty
    assert "patient_id" in df_train.columns
    assert "SepsisLabel" in df_train.columns
