"""
Unit and Integration Tests for Expanded MIMIC Cohort, 1D CNN Model, and Multimodal Evaluation Engine.
"""

import os
import json
import numpy as np
import pytest

from src.models.ecg_cnn import ECG1DCNN, ECGCNNClassifier
from src.mimic.evaluator import CareMindEvaluator
from src.mimic.cohort_ingestion import MIMICCohortIngestionEngine
from src.db.repository import LocalJSONRepository


def test_1d_cnn_model_forward_pass():
    """Verify PyTorch 1D CNN model input/output tensor shapes."""
    model = ECG1DCNN(input_channels=1, num_classes=2)
    x = torch_tensor = np.random.randn(8, 1, 1000).astype(np.float32)
    import torch
    out = model(torch.tensor(x))
    assert out.shape == (8, 2)


def test_ecg_cnn_classifier_fit_predict():
    """Verify scikit-learn API wrapper for 1D CNN classifier."""
    X = np.random.randn(20, 500)
    y = np.random.randint(0, 2, size=20)
    
    clf = ECGCNNClassifier(epochs=2, batch_size=10, random_state=42)
    clf.fit(X, y)
    
    assert clf.is_fitted is True
    probs = clf.predict_proba(X)
    assert probs.shape == (20, 2)
    assert np.allclose(np.sum(probs, axis=1), 1.0)
    
    preds = clf.predict(X)
    assert len(preds) == 20


def test_patient_level_split_zero_leakage():
    """Verify GroupShuffleSplit ensures zero patient leakage across train and test sets."""
    evaluator = CareMindEvaluator(random_state=42)
    X = np.random.randn(50, 10)
    y = np.random.randint(0, 2, size=50)
    groups = np.repeat(np.arange(10), 5) # 10 patients, 5 windows each
    
    X_tr, X_te, y_tr, y_te, g_tr, g_te = evaluator.patient_level_split(X, y, groups, test_size=0.3)
    
    train_patients = set(g_tr)
    test_patients = set(g_te)
    
    # Overlap must be empty
    assert len(train_patients.intersection(test_patients)) == 0


def test_unimodal_and_multimodal_evaluation():
    """Verify unimodal vs multimodal evaluation returns structured metrics and confusion matrices."""
    evaluator = CareMindEvaluator(random_state=42)
    res = evaluator.evaluate_unimodal_vs_multimodal(n_samples=50)
    
    assert "cohort_summary" in res
    assert "unimodal_metrics" in res
    
    metrics = res["unimodal_metrics"]
    assert "ECG_Only_SVM" in metrics
    assert "Multimodal_Fusion_LR" in metrics
    assert "precision" in metrics["Multimodal_Fusion_LR"]
    assert "confusion_matrix" in metrics["Multimodal_Fusion_LR"]


def test_dynamic_patient_count_repository():
    """Verify LocalJSONRepository dynamically returns all ingested records."""
    repo = LocalJSONRepository()
    records = repo.get_available_records()
    assert len(records) >= 12
    
    patients = repo.get_patients_overview(window_index=0)
    assert len(patients) == len(records)
    # Check that patients are sorted descending by risk score
    scores = [p["risk_score"] for p in patients]
    assert scores == sorted(scores, reverse=True)


def test_ingestion_engine_duplicate_safety(tmp_path):
    """Verify cohort ingestion engine safely updates records without corruption."""
    engine = MIMICCohortIngestionEngine(data_dir=str(tmp_path))
    
    # Ingest record twice
    meta1 = engine.process_and_cache_record(
        record_id="test_rec_01",
        subject_id=99900001,
        pn_dir="mimic4wdb/0.1.0/waves/p999/p99900001/test_rec_01/",
        segment_names=["test_rec_01"],
        base_timestamp_str="2150-01-01 08:00:00",
        vitals_dict={"HR": 80.0, "SpO2": 98.0},
        bed_id="Bed ICU-TEST"
    )
    
    meta2 = engine.process_and_cache_record(
        record_id="test_rec_01",
        subject_id=99900001,
        pn_dir="mimic4wdb/0.1.0/waves/p999/p99900001/test_rec_01/",
        segment_names=["test_rec_01"],
        base_timestamp_str="2150-01-01 08:00:00",
        vitals_dict={"HR": 80.0, "SpO2": 98.0},
        bed_id="Bed ICU-TEST"
    )
    
    index = engine.update_records_index()
    assert len(index) == 1
    assert index[0]["record_id"] == "test_rec_01"
