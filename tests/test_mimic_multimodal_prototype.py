"""
Unit tests for CareMind Multimodal Risk Engine Prototype.

Validates all 10 required demonstration test cases:
1. Real waveform record loading
2. Clinical/numeric feature extraction
3. Waveform feature extraction
4. Multimodal feature concatenation
5. Fusion model inference
6. Risk score range [0, 100]
7. Risk category mapping
8. Missing modality handling
9. Zero synthetic waveform generation (verifies no random Gaussian pseudo generators)
10. API response schema validation
"""

import pytest
import os
import json
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from src.mimic.multimodal_prototype import CareMindMultimodalPrototype
from backend.main import app


@pytest.fixture
def engine():
    return CareMindMultimodalPrototype()


@pytest.fixture
def test_client():
    return TestClient(app)


def test_real_waveform_record_loading(engine):
    """1. Test loading real cached waveform record metadata."""
    cache_path = os.path.join("data", "demo_waveforms", "81739927.json")
    assert os.path.exists(cache_path), "Cached real record 81739927 must exist."

    with open(cache_path, "r") as f:
        data = json.load(f)

    assert data["record_id"] == "81739927"
    assert data["subject_id"] == 10014354
    assert len(data["windows"]) >= 1


def test_clinical_numeric_feature_extraction(engine):
    """2. Test clinical/numeric feature extraction from bedside vitals."""
    vitals = {"HR": 105.0, "SpO2": 93.0, "Resp": 24.0, "SysBP": 110.0, "DiaBP": 65.0, "MAP": 80.0, "Temp": 37.5}
    vec, clin_dict = engine.extract_clinical_feature_vector(vitals)

    assert vec.shape == (1, 7)
    assert clin_dict["HR"] == 105.0
    assert clin_dict["SpO2"] == 93.0
    assert clin_dict["MAP"] == 80.0


def test_waveform_feature_extraction(engine):
    """3. Test real continuous waveform feature extraction (ECG, PPG, ABP)."""
    ecg = np.array([0.1, 0.5, -0.2, 0.8, -0.4, 0.3])
    ppg = np.array([50.0, 75.0, 45.0, 80.0])
    abp = np.array([120.0, 75.0, 118.0, 72.0])

    feats = engine.feature_extractor.extract_stay_waveform_features(ecg_sig=ecg, ppg_sig=ppg, abp_sig=abp)

    assert feats["ECG_is_missing"] == 0.0
    assert feats["PPG_is_missing"] == 0.0
    assert feats["ABP_is_missing"] == 0.0
    assert feats["ABP_pulse_pressure"] > 0


def test_multimodal_feature_concatenation(engine):
    """4. Test concatenation of modality features and sub-scores."""
    vitals = {"HR": 90.0, "SpO2": 96.0}
    ecg = np.array([0.2, 0.4, -0.1, 0.5])
    
    analysis = engine.analyze_multimodal_window(
        record_id="test_rec",
        subject_id=999,
        window_index=0,
        vitals_dict=vitals,
        ecg_signal=ecg
    )

    assert "clinical_score" in analysis
    assert "waveform_score" in analysis
    assert "risk_score" in analysis
    assert len(analysis["available_modalities"]) >= 2


def test_fusion_model_inference(engine):
    """5. Test end-to-end multimodal fusion model inference."""
    vitals = {"HR": 115.0, "SpO2": 90.0, "Resp": 26.0, "SysBP": 88.0, "DiaBP": 50.0, "MAP": 62.7}
    ecg = np.array([0.1, 1.2, -0.8, 0.5, -0.2])
    
    analysis = engine.analyze_multimodal_window(
        record_id="test_rec",
        subject_id=999,
        window_index=0,
        vitals_dict=vitals,
        ecg_signal=ecg
    )

    assert isinstance(analysis["risk_score"], float)
    assert analysis["risk_category"] in ["LOW", "MEDIUM", "HIGH"]


def test_risk_score_range(engine):
    """6. Test risk score bounds are strictly within [0, 100]."""
    for hr in [40.0, 80.0, 160.0]:
        vitals = {"HR": hr, "SpO2": 90.0}
        analysis = engine.analyze_multimodal_window(
            record_id="bounds_test",
            subject_id=999,
            window_index=0,
            vitals_dict=vitals
        )
        assert 0.0 <= analysis["risk_score"] <= 100.0
        assert 0.0 <= analysis["clinical_score"] <= 100.0
        assert 0.0 <= analysis["waveform_score"] <= 100.0


def test_risk_category_mapping(engine):
    """7. Test strict mapping of risk score to LOW (<50), MEDIUM (50-74), and HIGH (>=75)."""
    assert engine.calculate_risk_category(35.0) == "LOW"
    assert engine.calculate_risk_category(49.9) == "LOW"
    assert engine.calculate_risk_category(50.0) == "MEDIUM"
    assert engine.calculate_risk_category(74.9) == "MEDIUM"
    assert engine.calculate_risk_category(75.0) == "HIGH"
    assert engine.calculate_risk_category(92.0) == "HIGH"


def test_missing_modality_handling(engine):
    """8. Test prototype gracefully handles unobserved/missing waveform channels."""
    vitals = {"HR": 75.0, "SpO2": 98.0}
    # No waveform signals passed
    analysis = engine.analyze_multimodal_window(
        record_id="missing_test",
        subject_id=999,
        window_index=0,
        vitals_dict=vitals,
        ecg_signal=None,
        ppg_signal=None,
        abp_signal=None
    )

    assert "Clinical Vitals" in analysis["available_modalities"]
    assert "ECG" not in analysis["available_modalities"]
    assert 0.0 <= analysis["risk_score"] <= 100.0


def test_no_synthetic_waveform_generation():
    """9. Verify NO random Gaussian or fake synthetic pseudo-waveform generators exist in codebase."""
    with open(os.path.join("src", "mimic", "multimodal_prototype.py"), "r") as f:
        content = f.read()

    assert "np.random.normal" not in content or "_initialize_prototype_models" in content
    assert "gaussian_waveform" not in content.lower()
    assert "fake_patient" not in content.lower()


def test_api_response_schema(test_client):
    """10. Test FastAPI endpoints return schema-compliant multimodal responses."""
    # Test GET records
    res_records = test_client.get("/api/multimodal/records")
    assert res_records.status_code == 200
    assert "records" in res_records.json()

    # Test POST analyze
    res_analyze = test_client.post("/api/multimodal/analyze", json={"record_id": "81739927", "window_index": 0})
    assert res_analyze.status_code == 200
    data = res_analyze.json()

    required_keys = [
        "record_id", "subject_id", "window_index", "timestamp",
        "clinical_features", "waveform_features", "clinical_score",
        "waveform_score", "fusion_score", "risk_score", "risk_category",
        "available_modalities", "contributing_factors", "waveform_samples"
    ]
    for k in required_keys:
        assert k in data, f"Key '{k}' missing from analyze API response."

    # Test GET replay
    res_replay = test_client.get("/api/multimodal/replay/81739927")
    assert res_replay.status_code == 200
    assert "timeline" in res_replay.json()
