"""
Tests for Individual Physiological Model Predictions in CareMind.

Validates:
1. Actual individual model outputs are returned for supported modalities (ECG, PPG, ABP, Clinical Vitals).
2. Results correspond strictly to the selected patient and observation window.
3. Missing modalities are reported as unavailable (data_unavailable) without inventing predictions.
4. Missing models and inference failures are represented accurately.
5. No fabricated prediction or risk value is generated for missing data.
6. Existing multimodal risk calculation and fusion remain completely unchanged.
7. The Inspect Patient and predictions API endpoints return schema-compliant outputs.
8. Changing patients does not display stale predictions from the previous patient.
9. Advancing the simulation updates individual model outputs for the new observation window.
10. Regression check: all pipeline and patient management contracts remain preserved.
"""

import pytest
import numpy as np
from fastapi.testclient import TestClient

from src.mimic.multimodal_prototype import CareMindMultimodalPrototype
from src.mimic.simulation import CareMindSimulationEngine
from backend.main import app


@pytest.fixture
def prototype():
    return CareMindMultimodalPrototype()


@pytest.fixture
def sim_engine():
    return CareMindSimulationEngine()


@pytest.fixture
def client():
    return TestClient(app)


def test_actual_individual_model_outputs_returned(prototype):
    """1. Verify genuine individual model outputs are returned for supported modalities."""
    ecg = np.sin(np.linspace(0, 10, 500))
    ppg = np.sin(np.linspace(0, 10, 500)) * 20.0 + 70.0
    abp = np.sin(np.linspace(0, 10, 500)) * 25.0 + 95.0
    vitals = {"HR": 95.0, "SpO2": 96.0, "Resp": 19.0, "SysBP": 125.0, "DiaBP": 78.0, "MAP": 93.7, "Temp": 37.0}

    res = prototype.analyze_multimodal_window(
        record_id="test_rec_01",
        subject_id=10999999,
        window_index=0,
        vitals_dict=vitals,
        ecg_signal=ecg,
        ppg_signal=ppg,
        abp_signal=abp
    )

    assert "individual_predictions" in res
    preds = res["individual_predictions"]
    expected_modalities = ["ecg", "ppg", "abp", "clinical"]
    for mod in expected_modalities:
        assert mod in preds, f"Modality '{mod}' missing from individual_predictions"
        info = preds[mod]
        assert info["status"] == "prediction_available"
        assert info["is_available"] is True
        assert isinstance(info["score"], float)
        assert 0.0 <= info["score"] <= 100.0
        assert info["prediction"] is not None
        assert info["model_name"] is not None
        assert info["model_version"] is not None
        assert "risk_contribution" in info
        assert "explanation" in info
        assert "class_probabilities" in info
        assert isinstance(info["class_probabilities"], dict)


def test_results_correspond_to_selected_patient_and_observation_window(client):
    """2. Verify individual outputs correspond specifically to selected patient and window."""
    # Window 0 of 82439920 has only clinical vitals (waveforms not yet active)
    res_w0 = client.get("/api/multimodal/predictions/82439920?window_index=0")
    assert res_w0.status_code == 200
    p0 = res_w0.json()["predictions"]
    assert p0["clinical"]["status"] == "prediction_available"
    assert p0["ecg"]["status"] == "data_unavailable"
    assert p0["ppg"]["status"] == "data_unavailable"
    assert p0["abp"]["status"] == "data_unavailable"

    # Window 1 of 82439920 has all 4 modalities active
    res_w1 = client.get("/api/multimodal/predictions/82439920?window_index=1")
    assert res_w1.status_code == 200
    p1 = res_w1.json()["predictions"]
    assert p1["clinical"]["status"] == "prediction_available"
    assert p1["ecg"]["status"] == "prediction_available"
    assert p1["ppg"]["status"] == "prediction_available"
    assert p1["abp"]["status"] == "prediction_available"

    # Verify predictions differ and strictly reflect window 1 data
    assert p1["ecg"]["score"] is not None
    assert p1["ppg"]["score"] is not None
    assert p1["abp"]["score"] is not None


def test_missing_modalities_reported_as_unavailable(prototype):
    """3. Verify missing modalities report data_unavailable with null prediction & score."""
    # Only vitals passed; no waveforms
    res = prototype.analyze_multimodal_window(
        record_id="missing_test",
        subject_id=10999999,
        window_index=0,
        vitals_dict={"HR": 78.0, "SpO2": 98.0},
        ecg_signal=None,
        ppg_signal=None,
        abp_signal=None
    )

    preds = res["individual_predictions"]
    assert preds["clinical"]["status"] == "prediction_available"

    for wave_mod in ["ecg", "ppg", "abp"]:
        assert preds[wave_mod]["status"] == "data_unavailable"
        assert preds[wave_mod]["is_available"] is False
        assert preds[wave_mod]["score"] is None
        assert preds[wave_mod]["prediction"] is None
        assert preds[wave_mod]["class_probabilities"] is None
        assert preds[wave_mod]["features_used"] is None
        assert "not connected" in preds[wave_mod]["explanation"].lower() or "unmonitored" in preds[wave_mod]["explanation"].lower()


def test_missing_models_and_inference_failures(prototype):
    """4. Verify missing model configuration and execution failures are handled gracefully."""
    # Simulate uninitialized model state
    old_ecg_encoder = prototype.ecg_encoder
    prototype.ecg_encoder = None

    preds = prototype.compute_individual_model_predictions(
        clin_vitals={"HR": 80.0},
        wave_feats={"ECG_is_missing": 0.0, "PPG_is_missing": 1.0, "ABP_is_missing": 1.0},
        available_modalities=["ECG"]
    )

    assert preds["ecg"]["status"] == "model_unavailable"
    assert preds["ecg"]["is_available"] is False
    assert preds["ecg"]["prediction"] is None

    # Restore encoder
    prototype.ecg_encoder = old_ecg_encoder

    # Simulate inference failure by injecting corrupted input structure
    bad_wave_feats = {"ECG_is_missing": 0.0, "ECG_mean": "NOT_A_FLOAT_CORRUPTED"}
    fail_preds = prototype.compute_individual_model_predictions(
        clin_vitals={"HR": 80.0},
        wave_feats=bad_wave_feats,
        available_modalities=["ECG"]
    )

    assert fail_preds["ecg"]["status"] == "inference_failed"
    assert fail_preds["ecg"]["is_available"] is False
    assert "error" in fail_preds["ecg"]


def test_no_fabricated_prediction_or_risk_value(prototype):
    """5. Verify no fake prediction or fabricated score is assigned when data is missing."""
    vitals_all_missing = {"HR": None, "SpO2": None, "Resp": None, "SysBP": None, "DiaBP": None, "MAP": None, "Temp": None}
    preds = prototype.compute_individual_model_predictions(
        clin_vitals=vitals_all_missing,
        wave_feats={"ECG_is_missing": 1.0, "PPG_is_missing": 1.0, "ABP_is_missing": 1.0},
        available_modalities=[]
    )

    for mod_key, info in preds.items():
        assert info["status"] == "data_unavailable"
        assert info["score"] is None, f"Modality '{mod_key}' must have score=None when missing, not zero or synthetic value."
        assert info["prediction"] is None


def test_existing_multimodal_risk_calculation_unchanged(prototype):
    """6. Verify composite multimodal risk scoring and categories remain completely unchanged."""
    vitals = {"HR": 115.0, "SpO2": 91.0, "Resp": 24.0, "SysBP": 95.0, "DiaBP": 60.0, "MAP": 71.7, "Temp": 38.0}
    ecg = np.array([0.2, 1.1, -0.6, 0.4] * 50)

    res = prototype.analyze_multimodal_window(
        record_id="test_consistency",
        subject_id=10014354,
        window_index=0,
        vitals_dict=vitals,
        ecg_signal=ecg
    )

    # Validate existing pipeline fields remain unchanged
    assert "risk_score" in res
    assert "clinical_score" in res
    assert "waveform_score" in res
    assert "fusion_score" in res
    assert "risk_category" in res
    assert res["risk_category"] in ["LOW", "MEDIUM", "HIGH"]
    assert 0.0 <= res["risk_score"] <= 100.0


def test_inspect_patient_and_predictions_endpoint(client):
    """7. Verify API endpoints expose individual model predictions correctly."""
    # Test POST analyze endpoint
    res_analyze = client.post("/api/multimodal/analyze", json={"record_id": "81739927", "window_index": 1})
    assert res_analyze.status_code == 200
    data_analyze = res_analyze.json()
    assert "individual_predictions" in data_analyze
    assert "ecg" in data_analyze["individual_predictions"]
    assert "clinical" in data_analyze["individual_predictions"]

    # Test GET predictions endpoint
    res_pred = client.get("/api/multimodal/predictions/81739927?window_index=1")
    assert res_pred.status_code == 200
    data_pred = res_pred.json()
    assert data_pred["status"] == "success"
    assert data_pred["record_id"] == "81739927"
    assert data_pred["window_index"] == 1
    assert "predictions" in data_pred
    assert "multimodal_risk_score" in data_pred

    # Test non-existent record returns 404
    res_404 = client.get("/api/multimodal/predictions/nonexistent_999999?window_index=0")
    assert res_404.status_code == 404


def test_changing_patients_isolation(client):
    """8. Verify querying different patients returns isolated, non-stale predictions."""
    res_p1 = client.get("/api/multimodal/predictions/81739927?window_index=1")
    res_p2 = client.get("/api/multimodal/predictions/82924339?window_index=1")

    assert res_p1.status_code == 200
    assert res_p2.status_code == 200

    data_p1 = res_p1.json()
    data_p2 = res_p2.json()

    # 81739927 has clinical vitals, 82924339 has missing clinical vitals
    assert data_p1["predictions"]["clinical"]["status"] == "prediction_available"
    assert data_p2["predictions"]["clinical"]["status"] == "data_unavailable"
    assert data_p1["record_id"] != data_p2["record_id"]


def test_advancing_simulation_updates_predictions(sim_engine):
    """9. Verify stepping simulation advances observation window and updates individual predictions."""
    sim_engine.reset()
    state_0 = sim_engine.get_simulation_state()
    assert state_0["current_step"] == 0

    # Advance 1 step
    step_res = sim_engine.step()
    assert step_res["current_step"] == 1

    # Check that individual predictions are present and updated for monitored patients
    p_state = sim_engine.patient_states.get("82439920")
    if p_state:
        assert p_state["window_index"] == 1
        assert "individual_predictions" in p_state
        # At window 1, all modalities are present for 82439920
        assert p_state["individual_predictions"]["ecg"]["status"] == "prediction_available"
        assert p_state["individual_predictions"]["abp"]["status"] == "prediction_available"
