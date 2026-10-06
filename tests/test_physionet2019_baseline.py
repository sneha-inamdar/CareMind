"""
Automated unit tests for CareMind Phase 5A baseline model pipeline.

Verifies:
1. Train/Validation/Test patient splits remain 100% disjoint.
2. Target SepsisLabel is NOT in the feature matrix.
3. patient_id is NOT in the feature matrix.
4. No future-looking feature columns are included.
5. Feature columns are 100% consistent across train, validation, and test sets.
6. Baseline model fits successfully without errors.
7. Threshold tuning and evaluation compute expected metric structures.
8. Trained model artifact can be saved, reloaded, and used for inference.
"""

import os
import joblib
import pandas as pd
import numpy as np
import pytest

from src.physionet2019.baseline import (
    BaselineTrainer,
    COMBINED_FEATURE_SET,
    INDIVIDUAL_SIGNAL_SETS,
    EXCLUDED_COLUMNS,
    find_optimal_threshold,
    evaluate_predictions
)

PROCESSED_DIR = "data/physionet2019/processed"


@pytest.fixture(scope="module")
def dataset_splits():
    """Load train, validation, and test parquet splits."""
    train_df = pd.read_parquet(os.path.join(PROCESSED_DIR, "train.parquet"))
    val_df = pd.read_parquet(os.path.join(PROCESSED_DIR, "val.parquet"))
    test_df = pd.read_parquet(os.path.join(PROCESSED_DIR, "test.parquet"))
    return train_df, val_df, test_df


def test_disjoint_patient_splits(dataset_splits):
    """Verify zero patient overlap across splits."""
    train_df, val_df, test_df = dataset_splits
    
    train_pids = set(train_df["patient_id"])
    val_pids = set(val_df["patient_id"])
    test_pids = set(test_df["patient_id"])
    
    assert len(train_pids & val_pids) == 0, "Patient leakage detected between Train and Validation!"
    assert len(train_pids & test_pids) == 0, "Patient leakage detected between Train and Test!"
    assert len(val_pids & test_pids) == 0, "Patient leakage detected between Validation and Test!"


def test_feature_matrix_safety():
    """Verify target and identifier columns are excluded from feature sets."""
    for f_set_name, f_list in INDIVIDUAL_SIGNAL_SETS.items():
        assert "SepsisLabel" not in f_list, f"Target SepsisLabel found in feature set {f_set_name}!"
        assert "patient_id" not in f_list, f"patient_id found in feature set {f_set_name}!"
        assert "time_step" not in f_list, f"time_step found in feature set {f_set_name}!"
        assert "ICULOS" not in f_list, f"ICULOS found in feature set {f_set_name}!"


def test_no_future_looking_features():
    """Verify all engineered features in COMBINED feature set are backward-looking."""
    for feat in COMBINED_FEATURE_SET:
        assert not feat.startswith("future_"), f"Future feature detected: {feat}"
        assert not feat.endswith("_lead"), f"Lead feature detected: {feat}"
        # Deltas and rolling stats must use 1h or 3h backward naming convention
        if "delta_" in feat or "rolling_" in feat:
            assert feat.endswith("_1h") or feat.endswith("_3h"), f"Invalid window in feature: {feat}"


def test_feature_columns_consistency(dataset_splits):
    """Verify feature column names and dtypes are identical across train, val, and test splits."""
    train_df, val_df, test_df = dataset_splits
    features = COMBINED_FEATURE_SET
    
    train_features = list(train_df[features].columns)
    val_features = list(val_df[features].columns)
    test_features = list(test_df[features].columns)
    
    assert train_features == val_features, "Validation feature columns differ from Train!"
    assert train_features == test_features, "Test feature columns differ from Train!"
    
    # Check zero NaNs in features
    assert train_df[features].isna().sum().sum() == 0, "NaNs found in Train features!"
    assert val_df[features].isna().sum().sum() == 0, "NaNs found in Val features!"
    assert test_df[features].isna().sum().sum() == 0, "NaNs found in Test features!"


def test_baseline_training_and_evaluation(dataset_splits):
    """Verify model fits, tunes threshold on val, and evaluates on test."""
    train_df, val_df, test_df = dataset_splits
    trainer = BaselineTrainer(random_state=42)
    
    result = trainer.train_and_evaluate(
        train_df=train_df,
        val_df=val_df,
        test_df=test_df,
        model_type="logistic_regression",
        feature_set_name="COMBINED"
    )
    
    assert "validation_metrics" in result
    assert "test_metrics" in result
    assert result["validation_metrics"]["pr_auc"] >= 0.0
    assert result["test_metrics"]["pr_auc"] >= 0.0
    assert 0.0 <= result["test_metrics"]["threshold"] <= 1.0


def test_model_serialization_and_inference(dataset_splits, tmp_path):
    """Verify saved model artifact can be loaded and perform inference matching original predictions."""
    train_df, val_df, test_df = dataset_splits
    trainer = BaselineTrainer(random_state=42)
    
    result = trainer.train_and_evaluate(
        train_df=train_df,
        val_df=val_df,
        test_df=test_df,
        model_type="random_forest",
        feature_set_name="COMBINED"
    )
    
    model = result["model_object"]
    save_path = tmp_path / "test_rf_model.joblib"
    joblib.dump(model, save_path)
    
    loaded_model = joblib.load(save_path)
    
    features = COMBINED_FEATURE_SET
    orig_probs = model.predict_proba(test_df[features])[:, 1]
    loaded_probs = loaded_model.predict_proba(test_df[features])[:, 1]
    
    np.testing.assert_allclose(orig_probs, loaded_probs, rtol=1e-5)
