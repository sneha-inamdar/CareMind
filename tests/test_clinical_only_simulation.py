"""
Tests for Clinical-Only Patient Simulation Updates & Presentation in CareMind.

Validates:
1. Clinical-only patients step through multiple observation windows just like waveform patients.
2. Observed bedside vitals change across windows when source data contains different observations.
3. Clinical-vitals prediction refreshes dynamically after each simulation step.
4. Simulation controls (Play/Start, Step, Reset) behave consistently for clinical-only patients.
5. Unavailable waveforms remain unavailable without fabricating fake waveforms or synthetic signals.
6. Patients with waveforms continue to update and display continuous traces normally.
7. Switching between patients in the detail view returns patient-specific, non-stale predictions.
8. API endpoints (/api/simulation/step, /api/simulation/reset, /api/multimodal/analyze) are fully synchronized.
"""

import os
import json
import pytest
import numpy as np
from fastapi.testclient import TestClient

from src.mimic.simulation import CareMindSimulationEngine
from src.mimic.multimodal_prototype import CareMindMultimodalPrototype
from backend.main import app


@pytest.fixture
def sim_engine():
    engine = CareMindSimulationEngine()
    engine.reset()
    return engine


@pytest.fixture
def client():
    return TestClient(app)


CLINICAL_ONLY_RECORD_IDS = [
    "84992147", "80628315", "83820235", "80338760",
    "89669614", "82136005", "80407156", "80299691", "88206263"
]

WAVEFORM_RECORD_IDS = [
    "81739927", "83404654", "83411188", "82439920", "82800131"
]


def test_clinical_only_records_have_four_observation_windows():
    """Verify all clinical-only records have 4 sequential observation windows in cache."""
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "demo_waveforms")
    for rec_id in CLINICAL_ONLY_RECORD_IDS:
        file_path = os.path.join(data_dir, f"{rec_id}.json")
        assert os.path.exists(file_path), f"File {file_path} missing!"
        with open(file_path, "r") as f:
            data = json.load(f)
        assert "windows" in data
        assert len(data["windows"]) == 4, f"Record {rec_id} has {len(data['windows'])} windows, expected 4"
        assert data.get("windows_count") == 4


def test_simulation_advances_clinical_only_patients(sim_engine):
    """Verify simulation step advances window_index and updates vitals for clinical-only patients."""
    # Step 0
    state_0 = sim_engine.get_simulation_state()
    assert state_0["current_step"] == 0
    p0_map = {p["record_id"]: p for p in state_0["patients"]}

    # Advance to Step 1
    state_1 = sim_engine.step()
    assert state_1["current_step"] == 1
    p1_map = {p["record_id"]: p for p in state_1["patients"]}

    for rec_id in CLINICAL_ONLY_RECORD_IDS:
        if rec_id in p0_map and rec_id in p1_map:
            p0 = p0_map[rec_id]
            p1 = p1_map[rec_id]
            assert p0["window_index"] == 0
            assert p1["window_index"] == 1
            # Timestamp must advance
            assert p0["timestamp"] != p1["timestamp"], f"Record {rec_id} timestamp did not advance"


def test_bedside_vitals_change_across_simulation_steps(sim_engine):
    """Verify bedside vitals values change between steps for clinical-only patients with changing observations."""
    step0_state = sim_engine.get_simulation_state()
    p_step0 = {p["record_id"]: p for p in step0_state["patients"]}

    sim_engine.step()
    step1_state = sim_engine.get_simulation_state()
    p_step1 = {p["record_id"]: p for p in step1_state["patients"]}

    sim_engine.step()
    step2_state = sim_engine.get_simulation_state()
    p_step2 = {p["record_id"]: p for p in step2_state["patients"]}

    sim_engine.step()
    step3_state = sim_engine.get_simulation_state()
    p_step3 = {p["record_id"]: p for p in step3_state["patients"]}

    # Check that for 84992147 (Bed ICU-01), HR evolves across windows
    rec_id = "84992147"
    hrs = [
        p_step0[rec_id]["vitals"]["HR"],
        p_step1[rec_id]["vitals"]["HR"],
        p_step2[rec_id]["vitals"]["HR"],
        p_step3[rec_id]["vitals"]["HR"]
    ]
    # Verify not all vitals are identical
    assert len(set(hrs)) > 1, f"Expected changing HR across windows for {rec_id}, got: {hrs}"


def test_clinical_vitals_prediction_refreshes_each_step(sim_engine):
    """Verify individual clinical model prediction refreshes and computes dynamic scores on each step."""
    rec_id = "84992147"
    scores = []
    predictions = []

    for expected_step in range(4):
        state = sim_engine.get_simulation_state()
        p = next(x for x in state["patients"] if x["record_id"] == rec_id)
        indiv = p.get("individual_predictions", {})
        assert "clinical" in indiv
        clin_pred = indiv["clinical"]
        assert clin_pred["is_available"] is True
        assert clin_pred["status"] == "prediction_available"
        assert clin_pred["score"] is not None
        scores.append(clin_pred["score"])
        predictions.append(clin_pred["prediction"])

        if expected_step < 3:
            sim_engine.step()

    # Scores should reflect different window observations
    assert len(scores) == 4
    assert len(set(scores)) > 1, f"Expected dynamic clinical instability scores, got: {scores}"


def test_simulation_step_reset_cycle(sim_engine):
    """Verify stepping cycles through 0 -> 1 -> 2 -> 3 -> 0 and reset returns to step 0."""
    assert sim_engine.current_step == 0
    sim_engine.step()
    assert sim_engine.current_step == 1
    sim_engine.step()
    assert sim_engine.current_step == 2
    sim_engine.step()
    assert sim_engine.current_step == 3
    # Step after 3 should cycle back to 0
    sim_engine.step()
    assert sim_engine.current_step == 0

    # Step to 2 then reset
    sim_engine.step()
    sim_engine.step()
    assert sim_engine.current_step == 2
    reset_state = sim_engine.reset()
    assert reset_state["current_step"] == 0
    assert sim_engine.current_step == 0
    assert sim_engine.is_running is False


def test_unavailable_waveforms_remain_unavailable_without_fabricated_data(sim_engine):
    """Verify clinical-only patients report waveform channels as unavailable with zero fabricated signals."""
    for rec_id in CLINICAL_ONLY_RECORD_IDS:
        p_state = sim_engine.patient_states.get(rec_id)
        if not p_state:
            continue
        indiv = p_state.get("individual_predictions", {})

        # ECG, PPG, ABP must be unavailable
        for mod in ["ecg", "ppg", "abp"]:
            assert mod in indiv, f"Modality {mod} missing in individual predictions for {rec_id}"
            assert indiv[mod]["is_available"] is False
            assert indiv[mod]["status"] == "data_unavailable"
            assert indiv[mod]["score"] is None
            assert indiv[mod]["prediction"] is None
            assert "unavailable" in indiv[mod]["explanation"].lower() or "not connected" in indiv[mod]["explanation"].lower()

        # Waveform samples in cached windows must be empty arrays, never fabricated
        for w in p_state.get("cached_windows", []):
            samples = w.get("waveform_samples", {})
            assert len(samples.get("ecg", [])) == 0
            assert len(samples.get("ppg", [])) == 0
            assert len(samples.get("abp", [])) == 0


def test_waveform_patients_continue_to_update_normally(sim_engine):
    """Verify patients with waveforms update and have active waveform predictions on step advance."""
    wf_rec_id = "82439920"  # Tier 1 (ECG+ABP+PPG)
    p_state = sim_engine.patient_states.get(wf_rec_id)
    assert p_state is not None

    w0 = p_state["cached_windows"][0]

    # Advance to step 1 where continuous waveform monitoring is active
    sim_engine.step()
    p_state_step1 = sim_engine.patient_states[wf_rec_id]
    assert p_state_step1["window_index"] == 1
    assert p_state_step1["timestamp"] != w0["timestamp"]

    indiv1 = p_state_step1["individual_predictions"]
    assert indiv1["ecg"]["is_available"] is True
    assert indiv1["ppg"]["is_available"] is True
    assert indiv1["abp"]["is_available"] is True
    assert indiv1["clinical"]["is_available"] is True


def test_api_multimodal_analyze_synchronizes_with_simulation_step(client):
    """Verify POST /api/multimodal/analyze reflects the requested window_index and live simulation state."""
    # Reset simulation
    client.post("/api/simulation/reset")

    # Step to window 1
    step_resp = client.post("/api/simulation/step")
    assert step_resp.status_code == 200
    step_data = step_resp.json()
    assert step_data["current_step"] == 1

    # Request detail for clinical-only record at current step
    detail_resp = client.post("/api/multimodal/analyze", json={"record_id": "84992147", "window_index": 1})
    assert detail_resp.status_code == 200
    detail = detail_resp.json()

    assert detail["window_index"] == 1
    assert detail["clinical_features"]["HR"] == 93.0
    assert detail["individual_predictions"]["clinical"]["is_available"] is True
    assert detail["individual_predictions"]["ecg"]["is_available"] is False


def test_switching_patients_detail_returns_patient_specific_predictions(client):
    """Verify switching between clinical-only and waveform patients returns respective correct predictions."""
    # Clinical patient at window 1
    resp_clin = client.post("/api/multimodal/analyze", json={"record_id": "84992147", "window_index": 1})
    assert resp_clin.status_code == 200
    clin_data = resp_clin.json()
    assert clin_data["individual_predictions"]["ecg"]["is_available"] is False
    assert clin_data["individual_predictions"]["clinical"]["is_available"] is True

    # Waveform patient at window 1
    resp_wf = client.post("/api/multimodal/analyze", json={"record_id": "82439920", "window_index": 1})
    assert resp_wf.status_code == 200
    wf_data = resp_wf.json()
    assert wf_data["individual_predictions"]["ecg"]["is_available"] is True
    assert wf_data["individual_predictions"]["clinical"]["is_available"] is True

    # Ensure patient data is strictly distinct
    assert clin_data["record_id"] != wf_data["record_id"]
    assert clin_data["subject_id"] != wf_data["subject_id"]
    assert clin_data["individual_predictions"]["ecg"]["is_available"] != wf_data["individual_predictions"]["ecg"]["is_available"]


def test_records_index_consistency():
    """Verify data/demo_waveforms/records_index.json has windows_count: 4 for all records."""
    index_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "demo_waveforms", "records_index.json")
    with open(index_path, "r") as f:
        records = json.load(f)

    for r in records:
        assert r.get("windows_count") == 4, f"Record {r.get('record_id')} has windows_count: {r.get('windows_count')}, expected 4"
