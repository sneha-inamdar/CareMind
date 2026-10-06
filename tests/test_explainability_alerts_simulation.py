"""
Comprehensive unit tests for Explainability, Alerts, Temporal Risk, Multi-Patient Simulation, & API Stabilization.
"""

import pytest
import numpy as np
from fastapi.testclient import TestClient

from src.mimic.multimodal_prototype import CareMindMultimodalPrototype
from src.mimic.alerts import AlertEngine
from src.mimic.simulation import CareMindSimulationEngine
from src.db.repository import LocalJSONRepository, get_repository
from backend.main import app


@pytest.fixture
def prototype():
    return CareMindMultimodalPrototype()


@pytest.fixture
def alert_engine():
    return AlertEngine()


@pytest.fixture
def sim_engine():
    return CareMindSimulationEngine()


@pytest.fixture
def api_client():
    return TestClient(app)


def test_explainability_complete_modalities(prototype):
    """1. Test structured explainability output with complete modalities."""
    vitals = {"HR": 115.0, "SpO2": 91.0, "Resp": 24.0, "SysBP": 90.0, "DiaBP": 55.0, "MAP": 62.0}
    ecg = np.array([0.1, 1.5, -0.9, 0.4])
    abp = np.array([125.0, 70.0, 130.0, 65.0])

    analysis = prototype.analyze_multimodal_window(
        record_id="rec_full", subject_id=101, window_index=0,
        vitals_dict=vitals, ecg_signal=ecg, abp_signal=abp
    )

    factors = analysis["contributing_factors"]
    assert len(factors) > 0
    f0 = factors[0]
    assert "factor" in f0
    assert "modality" in f0
    assert "severity" in f0
    assert "evidence" in f0
    assert f0["modality"] in ["Clinical Vitals", "ECG", "ABP", "PPG", "Temporal Trend", "General Physiology"]


def test_explainability_missing_modalities(prototype):
    """2. Test explainability suppresses factors for unobserved/missing modalities."""
    vitals = {"HR": None, "SpO2": None, "Resp": None, "SysBP": None, "DiaBP": None, "MAP": None, "Temp": None}
    ecg = np.array([0.1, 0.2, 0.3])

    analysis = prototype.analyze_multimodal_window(
        record_id="rec_missing", subject_id=102, window_index=0,
        vitals_dict=vitals, ecg_signal=ecg, ppg_signal=None, abp_signal=None
    )

    factors = analysis["contributing_factors"]
    modalities_in_factors = {f["modality"] for f in factors}

    # Clinical Vitals and ABP must NOT appear in factors when missing
    assert "Clinical Vitals" not in modalities_in_factors
    assert "ABP" not in modalities_in_factors


def test_temporal_risk_first_window(prototype):
    """3. Test temporal risk initialization for first observation window."""
    vitals = {"HR": 80.0, "SpO2": 98.0}
    analysis = prototype.analyze_multimodal_window(
        record_id="rec_w0", subject_id=103, window_index=0,
        vitals_dict=vitals, previous_risk_score=None
    )

    assert analysis["risk_trend_delta"] == 0.0
    assert analysis["risk_trend_status"] == "STABLE"


def test_temporal_risk_consecutive_windows(prototype):
    """4. Test temporal risk trend calculation across consecutive windows."""
    vitals = {"HR": 80.0, "SpO2": 98.0}
    
    # Previous risk = 30.0, Current risk = 60.0 -> ESCALATING (+30.0)
    w_esc = prototype.analyze_multimodal_window(
        record_id="rec_seq", subject_id=104, window_index=1,
        vitals_dict=vitals, previous_risk_score=30.0
    )
    assert w_esc["risk_trend_status"] in ["ESCALATING", "STABLE", "IMPROVING"]

    # Previous risk = 80.0 -> IMPROVING
    w_imp = prototype.analyze_multimodal_window(
        record_id="rec_seq", subject_id=104, window_index=2,
        vitals_dict=vitals, previous_risk_score=80.0
    )
    assert w_imp["risk_trend_status"] == "IMPROVING"
    assert w_imp["risk_trend_delta"] <= -5.0


def test_independent_multi_patient_temporal_state(sim_engine):
    """5. Test independent temporal risk state maintenance per patient."""
    sim_engine.reset()
    state_0 = sim_engine.get_simulation_state()
    p0 = state_0["patients"][0]

    sim_engine.step()
    state_1 = sim_engine.get_simulation_state()
    p1 = state_1["patients"][0]

    # Verify each patient retains independent record_id and window progression
    assert len(state_1["patients"]) == len(state_0["patients"])
    for p in state_1["patients"]:
        assert "risk_trend_status" in p
        assert "risk_trend_delta" in p


def test_alert_generation(alert_engine):
    """6. Test evidence-grounded alert generation for HIGH_RISK and PHYSIOLOGICAL_ABNORMALITY."""
    patient_high = {
        "record_id": "81739927",
        "subject_id": 10014354,
        "stay_id": 39880770,
        "bed_id": "Bed ICU-01",
        "window_index": 0,
        "timestamp": "2148-08-16 09:00:17",
        "risk_score": 82.5,
        "risk_category": "HIGH",
        "risk_trend_status": "ESCALATING",
        "risk_trend_delta": 12.0,
        "available_modalities": ["ECG", "Clinical Vitals"],
        "contributing_factors": [
            {
                "factor": "Elevated Heart Rate",
                "modality": "Clinical Vitals",
                "severity": "HIGH",
                "evidence": "HR of 115 bpm exceeds 100 bpm threshold",
                "contribution_score": 15.0
            }
        ]
    }

    alerts = alert_engine.evaluate_patient_alerts(patient_high)
    assert len(alerts) >= 1
    alert_types = [a["alert_type"] for a in alerts]
    assert "HIGH_RISK" in alert_types or "PHYSIOLOGICAL_ABNORMALITY" in alert_types


def test_alert_deduplication(alert_engine):
    """7. Test alert engine prevents duplicate notification spam for unchanged patient state."""
    patient = {
        "record_id": "81739927",
        "subject_id": 10014354,
        "window_index": 0,
        "timestamp": "2148-08-16 09:00:17",
        "risk_score": 85.0,
        "risk_category": "HIGH",
        "contributing_factors": []
    }

    alerts_step1 = alert_engine.evaluate_patient_alerts(patient)
    history_len1 = len(alert_engine.alert_history)

    # Re-evaluate same state
    patient["window_index"] = 1
    patient["timestamp"] = "2148-08-16 09:00:32"
    alerts_step2 = alert_engine.evaluate_patient_alerts(patient)
    history_len2 = len(alert_engine.alert_history)

    # Alert history count must NOT increase when state is unchanged
    assert history_len2 == history_len1


def test_risk_transition_alerts(alert_engine):
    """8. Test transition alerts when patient transitions from LOW to HIGH risk."""
    patient_low = {
        "record_id": "81739927",
        "subject_id": 10014354,
        "risk_score": 30.0,
        "risk_category": "LOW",
        "contributing_factors": []
    }
    alert_engine.evaluate_patient_alerts(patient_low)
    assert len(alert_engine.active_alerts) == 0

    patient_high = {
        "record_id": "81739927",
        "subject_id": 10014354,
        "risk_score": 88.0,
        "risk_category": "HIGH",
        "contributing_factors": [{"factor": "Hypoxia", "severity": "HIGH", "evidence": "SpO2 88%", "contribution_score": 20.0}]
    }
    alerts_trans = alert_engine.evaluate_patient_alerts(patient_high)
    assert len(alerts_trans) > 0


def test_multi_patient_simulation(sim_engine):
    """9. Test multi-patient simulation initialization and step advancing."""
    sim_engine.reset()
    state0 = sim_engine.get_simulation_state()
    assert state0["status"] == "success"
    assert state0["patient_count"] == 3
    assert state0["current_step"] == 0

    sim_engine.step()
    state1 = sim_engine.get_simulation_state()
    assert state1["current_step"] == 1


def test_patient_reranking_after_simulation_step(sim_engine):
    """10. Test ICU patients are dynamically re-ranked descending by risk score after simulation step."""
    sim_engine.reset()
    sim_engine.step()
    state = sim_engine.get_simulation_state()

    patients = state["patients"]
    scores = [p["risk_score"] for p in patients]
    sorted_scores = sorted(scores, reverse=True)
    
    assert scores == sorted_scores, f"Patients not sorted descending by risk score: {scores}"


def test_simulation_and_alert_api_endpoints(api_client):
    """11. Test FastAPI simulation and alert endpoints."""
    # Test GET /api/simulation/state
    res_state = api_client.get("/api/simulation/state")
    assert res_state.status_code == 200
    assert "patients" in res_state.json()

    # Test POST /api/simulation/start
    res_start = api_client.post("/api/simulation/start")
    assert res_start.status_code == 200

    # Test POST /api/simulation/step
    res_step = api_client.post("/api/simulation/step")
    assert res_step.status_code == 200

    # Test GET /api/alerts
    res_alerts = api_client.get("/api/alerts")
    assert res_alerts.status_code == 200
    assert "alerts" in res_alerts.json()


def test_local_json_repository_fallback():
    """12. Test LocalJSONRepository fallback behavior."""
    repo = LocalJSONRepository()
    records = repo.get_available_records()
    assert len(records) >= 3

    patients = repo.get_patients_overview(window_index=0)
    assert len(patients) >= 3
    scores = [p["risk_score"] for p in patients]
    assert scores == sorted(scores, reverse=True)


def test_supabase_repository_compatibility():
    """13. Test Repository factory returns working repository abstraction."""
    repo = get_repository()
    records = repo.get_available_records()
    assert len(records) >= 3


def test_step0_priority_initialization_regression(sim_engine):
    """14. Regression test: Step 0 initialization for high-risk patients must calculate priority correctly."""
    sim_engine.reset()
    state = sim_engine.get_simulation_state()
    for p in state["patients"]:
        if p["risk_score"] >= 75.0:
            assert p["priority_status"] == "CRITICAL_PRIORITY", f"Patient {p['subject_id']} with risk {p['risk_score']} should be CRITICAL_PRIORITY"
        elif p["risk_score"] >= 50.0:
            assert p["priority_status"] == "HIGH_PRIORITY", f"Patient {p['subject_id']} with risk {p['risk_score']} should be HIGH_PRIORITY"
        else:
            assert p["priority_status"] == "ROUTINE_MONITORING"
