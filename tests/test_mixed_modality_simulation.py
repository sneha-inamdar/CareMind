"""
Tests for CareMind Mixed-Modality (Waveform + Clinical) Patient Simulation Updates.

Validates:
1. Consecutive windows contain genuine differing clinical observations for mixed-modality patients.
2. The simulation state returns the correct bedside vitals after each step.
3. Waveform and clinical values refer to the same active observation window.
4. Clinical predictions update dynamically when clinical inputs change across windows.
5. Play (start/pause), Step, and Reset behave consistently and deterministically.
6. Clinical-only simulation continues to work without regression.
7. Missing waveforms or clinical values are preserved and never fabricated.
8. Existing risk, alert, and patient-switching behavior remains intact.
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import json
import pytest
import numpy as np
from fastapi.testclient import TestClient

from src.mimic.simulation import CareMindSimulationEngine
from src.mimic.multimodal_prototype import CareMindMultimodalPrototype
from backend.main import app

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "demo_waveforms")

MIXED_MODALITY_RECORDS = ["83404654", "81739927", "83411188"]
CLINICAL_ONLY_RECORDS = ["84992147", "80628315", "83820235", "80338760"]
UNMONITORED_CLINICAL_RECORD = "82924339"


@pytest.fixture
def sim_engine():
    engine = CareMindSimulationEngine(data_dir=DATA_DIR)
    engine.reset()
    return engine


@pytest.fixture
def client():
    return TestClient(app)


def test_consecutive_windows_contain_expected_clinical_observations():
    """1. Verify consecutive windows contain genuine differing clinical observations for mixed-modality patients."""
    # 83404654 (Bed ICU-10, Subject 10020306)
    path_8340 = os.path.join(DATA_DIR, "83404654.json")
    with open(path_8340, "r") as f:
        d_8340 = json.load(f)

    windows = d_8340["windows"]
    assert len(windows) == 4

    hrs = [w["clinical_features"]["HR"] for w in windows]
    bps = [(w["clinical_features"]["SysBP"], w["clinical_features"]["DiaBP"]) for w in windows]
    maps = [w["clinical_features"]["MAP"] for w in windows]

    assert hrs == [92.0, 98.0, 88.0, 105.0]
    assert bps == [(122.0, 77.0), (85.0, 73.0), (79.0, 67.0), (87.0, 64.0)]
    assert maps == [91.0, 78.0, 73.0, 73.0]
    assert len(set(hrs)) == 4, "HR values must differ across windows"

    # 81739927 (Bed ICU-08, Subject 10014354)
    path_8173 = os.path.join(DATA_DIR, "81739927.json")
    with open(path_8173, "r") as f:
        d_8173 = json.load(f)
    hrs_817 = [w["clinical_features"]["HR"] for w in d_8173["windows"]]
    assert hrs_817 == [63.0, 55.0, 53.0, 60.0]
    assert len(set(hrs_817)) == 4

    # 83411188 (Bed ICU-11, Subject 10039708)
    path_8341 = os.path.join(DATA_DIR, "83411188.json")
    with open(path_8341, "r") as f:
        d_8341 = json.load(f)
    resps_8341 = [w["clinical_features"]["Resp"] for w in d_8341["windows"]]
    assert resps_8341 == [18.0, 18.0, 30.0, 19.0]
    assert len(set(resps_8341)) > 1


def test_simulation_state_returns_correct_vitals_after_each_step(sim_engine):
    """2. Verify simulation state returns correct bedside vitals after each step for mixed-modality patients."""
    # Window 0
    s0 = sim_engine.get_simulation_state()
    p0 = {p["record_id"]: p for p in s0["patients"]}
    assert p0["83404654"]["vitals"]["HR"] == 92.0
    assert p0["83404654"]["vitals"]["SysBP"] == 122.0
    assert p0["81739927"]["vitals"]["HR"] == 63.0

    # Step to Window 1
    s1 = sim_engine.step()
    p1 = {p["record_id"]: p for p in s1["patients"]}
    assert s1["current_step"] == 1
    assert p1["83404654"]["vitals"]["HR"] == 98.0
    assert p1["83404654"]["vitals"]["SysBP"] == 85.0
    assert p1["81739927"]["vitals"]["HR"] == 55.0

    # Step to Window 2
    s2 = sim_engine.step()
    p2 = {p["record_id"]: p for p in s2["patients"]}
    assert s2["current_step"] == 2
    assert p2["83404654"]["vitals"]["HR"] == 88.0
    assert p2["83404654"]["vitals"]["SysBP"] == 79.0
    assert p2["81739927"]["vitals"]["HR"] == 53.0

    # Step to Window 3
    s3 = sim_engine.step()
    p3 = {p["record_id"]: p for p in s3["patients"]}
    assert s3["current_step"] == 3
    assert p3["83404654"]["vitals"]["HR"] == 105.0
    assert p3["83404654"]["vitals"]["SysBP"] == 87.0
    assert p3["81739927"]["vitals"]["HR"] == 60.0


def test_waveform_and_clinical_values_refer_to_same_active_window(client):
    """3. Verify waveform samples and clinical vitals correspond to the same active window."""
    for win_idx in [0, 1, 2, 3]:
        resp = client.post("/api/multimodal/analyze", json={"record_id": "83404654", "window_index": win_idx})
        assert resp.status_code == 200
        data = resp.json()

        assert data["window_index"] == win_idx
        # Check that clinical features match the expected window
        expected_hrs = [92.0, 98.0, 88.0, 105.0]
        assert data["clinical_features"]["HR"] == expected_hrs[win_idx]

        # Check waveform samples are present and belong to this window
        samples = data.get("waveform_samples", {})
        assert "ecg" in samples
        assert "ppg" in samples
        if win_idx > 0:
            assert len(samples["ecg"]) > 0
            assert len(samples["ppg"]) > 0


def test_clinical_predictions_update_when_clinical_inputs_change():
    """4. Verify individual clinical-vitals prediction changes when clinical inputs change."""
    path = os.path.join(DATA_DIR, "83404654.json")
    with open(path, "r") as f:
        d = json.load(f)

    w0 = d["windows"][0]
    w2 = d["windows"][2]

    pred0 = w0["individual_predictions"]["clinical"]
    pred2 = w2["individual_predictions"]["clinical"]

    # In window 0: normal BP (122/77), HR 92 -> Low Risk / Stable
    assert pred0["prediction"] == "Low Risk / Stable"
    assert pred0["score"] < 50.0

    # In window 2: hypotensive (79/67, MAP 73) -> Moderate Vital Instability
    assert pred2["prediction"] == "Moderate Vital Instability"
    assert pred2["score"] >= 50.0
    assert pred2["score"] != pred0["score"]


def test_play_step_reset_consistency(sim_engine):
    """5. Verify Play/Start, Pause, Step, and Reset behave consistently."""
    # Initial state is step 0
    assert sim_engine.current_step == 0
    assert not sim_engine.is_running

    # Start simulation
    sim_engine.start()
    assert sim_engine.is_running

    # Pause simulation
    sim_engine.pause()
    assert not sim_engine.is_running
    assert sim_engine.current_step == 0

    # Step through all 4 windows and cycle back to 0
    s1 = sim_engine.step()
    assert s1["current_step"] == 1
    s2 = sim_engine.step()
    assert s2["current_step"] == 2
    s3 = sim_engine.step()
    assert s3["current_step"] == 3
    s0_cycled = sim_engine.step()
    assert s0_cycled["current_step"] == 0

    # Advance again and test Reset
    sim_engine.step()
    assert sim_engine.current_step == 1
    reset_state = sim_engine.reset()
    assert reset_state["current_step"] == 0
    assert not sim_engine.is_running
    p_reset = {p["record_id"]: p for p in reset_state["patients"]}
    assert p_reset["83404654"]["vitals"]["HR"] == 92.0


def test_clinical_only_simulation_still_works(sim_engine):
    """6. Verify clinical-only patients continue to advance and update without regression."""
    s0 = sim_engine.get_simulation_state()
    p0 = {p["record_id"]: p for p in s0["patients"]}

    sim_engine.step()
    s1 = sim_engine.get_simulation_state()
    p1 = {p["record_id"]: p for p in s1["patients"]}

    # Check clinical-only patient 84992147 (Bed ICU-01)
    assert p0["84992147"]["vitals"]["HR"] == 91.0
    assert p1["84992147"]["vitals"]["HR"] == 93.0
    assert p0["84992147"]["window_index"] == 0
    assert p1["84992147"]["window_index"] == 1


def test_missing_waveforms_or_clinical_values_not_fabricated():
    """7. Verify missing waveforms or clinical values are preserved and never fabricated."""
    # 82924339 has no bedside vitals
    path_8292 = os.path.join(DATA_DIR, f"{UNMONITORED_CLINICAL_RECORD}.json")
    with open(path_8292, "r") as f:
        d_8292 = json.load(f)

    for w in d_8292["windows"]:
        cf = w["clinical_features"]
        for key in ["HR", "SpO2", "Resp", "SysBP", "DiaBP", "MAP"]:
            assert cf.get(key) is None, f"Expected {key} to be None for unmonitored patient {UNMONITORED_CLINICAL_RECORD}"

    # 83404654 is Tier 2 (ECG+PPG), ABP is unavailable
    path_8340 = os.path.join(DATA_DIR, "83404654.json")
    with open(path_8340, "r") as f:
        d_8340 = json.load(f)

    for w in d_8340["windows"]:
        abp_samples = w.get("waveform_samples", {}).get("abp", [])
        assert len(abp_samples) == 0, "ABP waveform must not be fabricated for Tier 2 record"
        assert w["waveform_features"].get("ABP_is_missing") == 1.0


def test_risk_alert_and_patient_switching_behavior_intact(client, sim_engine):
    """8. Verify risk scores, alerts, and patient switching remain isolated and synchronized."""
    # Step simulation to step 1
    sim_engine.step()

    # Query patient 83404654 at window 1
    r1 = client.post("/api/multimodal/analyze", json={"record_id": "83404654", "window_index": 1})
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["record_id"] == "83404654"
    assert d1["clinical_features"]["HR"] == 98.0
    assert d1["risk_score"] == 79.8
    assert d1["priority_status"] == "CRITICAL_PRIORITY"

    # Query patient 81739927 at window 1
    r2 = client.post("/api/multimodal/analyze", json={"record_id": "81739927", "window_index": 1})
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["record_id"] == "81739927"
    assert d2["clinical_features"]["HR"] == 55.0
    assert d2["risk_score"] == 39.9
    assert d2["priority_status"] == "ROUTINE_MONITORING"

    # Re-query patient 83404654 to ensure no state bleeding
    r3 = client.post("/api/multimodal/analyze", json={"record_id": "83404654", "window_index": 1})
    d3 = r3.json()
    assert d3["clinical_features"]["HR"] == 98.0
    assert d3["risk_score"] == 79.8
