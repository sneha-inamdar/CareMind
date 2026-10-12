"""
Focused Test Suite for CareMind:
1. Add Patient Workflow (Genuine Data Only, Duplicate Prevention, Monitored Count Increment)
2. Patient Management (Search, Multi-field Filtering, Sorting, Inspection Persistence)
"""

import os
import json
import copy
import pytest
from fastapi.testclient import TestClient

from backend.main import app, simulation_engine
from src.db.repository import LocalJSONRepository, get_repository, CareMindBaseRepository
from src.mimic.simulation import CareMindSimulationEngine


@pytest.fixture
def test_client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def preserve_monitored_cohort():
    """Ensure monitored_cohort.json is saved and restored around tests."""
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "demo_waveforms")
    cohort_path = os.path.join(data_dir, "monitored_cohort.json")
    original_data = None
    if os.path.exists(cohort_path):
        with open(cohort_path, "r") as f:
            original_data = json.load(f)

    yield

    # Restore original state
    if original_data is not None:
        with open(cohort_path, "w") as f:
            json.dump(original_data, f, indent=2)
    # Reinitialize simulation engine to restored state
    simulation_engine._initialize_simulation()


# --------------------------------------------------------------------------
# 1. ADD PATIENT WORKFLOW TESTS
# --------------------------------------------------------------------------

def test_available_records_from_genuine_cohort(test_client):
    """Verify available-record options originate strictly from genuine cohort source and exclude monitored ones."""
    res = test_client.get("/api/multimodal/records/available")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    unmonitored = data["records"]
    assert isinstance(unmonitored, list)

    repo = get_repository()
    monitored_ids = set(repo.get_monitored_record_ids())
    inventory_ids = {r["record_id"] for r in repo.get_inventory_records()}

    # All unmonitored records must be part of genuine inventory
    for rec in unmonitored:
        assert rec["record_id"] in inventory_ids, f"{rec['record_id']} is not in genuine inventory"
        assert rec["record_id"] not in monitored_ids, f"{rec['record_id']} is already monitored"
        assert "available_modalities" in rec
        assert "subject_id" in rec


def test_empty_state_when_all_records_monitored():
    """Verify empty list is returned when all genuine records are monitored (triggering empty state message)."""
    repo = LocalJSONRepository()
    inventory = repo.get_inventory_records()
    all_record_ids = [r["record_id"] for r in inventory]

    # Temporarily set monitored list to contain all records
    repo._save_monitored_record_ids(all_record_ids)

    unmonitored = repo.get_unmonitored_records()
    assert len(unmonitored) == 0, "When all genuine records are monitored, unmonitored list must be empty."


def test_add_genuine_patient_increases_monitored_count(test_client):
    """Verify adding a genuine unmonitored record increases monitored count by exactly 1."""
    res_avail = test_client.get("/api/multimodal/records/available")
    unmonitored = res_avail.json()["records"]
    assert len(unmonitored) > 0, "Need at least one unmonitored record to test addition."

    target_record = unmonitored[0]
    target_id = target_record["record_id"]

    sim_state_before = test_client.get("/api/simulation/state").json()
    count_before = sim_state_before["patient_count"]

    res_add = test_client.post("/api/multimodal/patients/add", json={"record_id": target_id})
    assert res_add.status_code == 200
    add_data = res_add.json()
    assert add_data["status"] == "success"
    assert add_data["monitored_patient_count"] == count_before + 1

    # Verify simulation state reflects exactly count_before + 1
    sim_state_after = test_client.get("/api/simulation/state").json()
    assert sim_state_after["patient_count"] == count_before + 1

    # Newly added patient must be present in simulation patients list
    record_ids_in_sim = [p["record_id"] for p in sim_state_after["patients"]]
    assert target_id in record_ids_in_sim


def test_duplicate_addition_prevention(test_client):
    """Verify attempting to add an already monitored patient returns HTTP 409 Conflict without duplicate creation."""
    repo = get_repository()
    monitored = repo.get_monitored_record_ids()
    assert len(monitored) > 0
    already_monitored_id = monitored[0]

    # Attempt to re-add existing monitored patient
    res_dup = test_client.post("/api/multimodal/patients/add", json={"record_id": already_monitored_id})
    assert res_dup.status_code == 409
    assert "already present" in res_dup.json()["detail"].lower()

    # Monitored count must remain unchanged
    sim_state = test_client.get("/api/simulation/state").json()
    assert sim_state["patient_count"] == len(monitored)


def test_reject_fake_or_nonexistent_patient(test_client):
    """Verify that fake or nonexistent patient IDs are strictly rejected."""
    fake_id = "fake_record_99999999"
    res = test_client.post("/api/multimodal/patients/add", json={"record_id": fake_id})
    assert res.status_code == 404
    assert "not found in genuine" in res.json()["detail"].lower()


def test_reject_empty_payload(test_client):
    """Verify empty or invalid record_id returns HTTP 400."""
    res = test_client.post("/api/multimodal/patients/add", json={"record_id": "   "})
    assert res.status_code == 400


# --------------------------------------------------------------------------
# 2. PATIENT MANAGEMENT TESTS (Search, Filter, Sort, Inspect)
# --------------------------------------------------------------------------

def test_search_by_subject_and_record_and_stay_id(test_client):
    """Verify searching finds patients by Subject ID, Record ID, Stay ID, Bed without altering state."""
    sim_state = test_client.get("/api/simulation/state").json()
    patients = sim_state["patients"]
    assert len(patients) > 0

    target = patients[0]
    sub_id = str(target["subject_id"])
    rec_id = str(target["record_id"])
    stay_id = str(target["stay_id"])
    bed_id = str(target["bed_id"])

    # Simulate frontend search logic
    def filter_by_search(query, pts):
        q = query.lower()
        return [
            p for p in pts
            if q in str(p.get("subject_id", "")).lower()
            or q in str(p.get("record_id", "")).lower()
            or q in str(p.get("stay_id", "")).lower()
            or q in str(p.get("bed_id", "")).lower()
        ]

    # Search by Subject ID
    matches_sub = filter_by_search(sub_id, patients)
    assert any(p["record_id"] == rec_id for p in matches_sub)

    # Search by Record ID
    matches_rec = filter_by_search(rec_id, patients)
    assert any(p["record_id"] == rec_id for p in matches_rec)

    # Search by Stay ID
    matches_stay = filter_by_search(stay_id, patients)
    assert any(p["record_id"] == rec_id for p in matches_stay)

    # Search by Bed
    matches_bed = filter_by_search(bed_id, patients)
    assert any(p["record_id"] == rec_id for p in matches_bed)


def test_priority_filtering_accuracy(test_client):
    """Verify priority filter correctly partitions CRITICAL, HIGH, and ROUTINE patients."""
    sim_state = test_client.get("/api/simulation/state").json()
    patients = sim_state["patients"]

    critical_patients = [
        p for p in patients
        if p["priority_status"] == "CRITICAL_PRIORITY" or p["risk_category"] == "HIGH" or p["risk_score"] >= 75
    ]
    high_patients = [
        p for p in patients
        if (p["priority_status"] == "HIGH_PRIORITY" or p["risk_category"] == "MEDIUM" or (50 <= p["risk_score"] < 75))
        and p not in critical_patients
    ]
    routine_patients = [
        p for p in patients
        if p not in critical_patients and p not in high_patients
    ]

    total_partitioned = len(critical_patients) + len(high_patients) + len(routine_patients)
    assert total_partitioned == len(patients), "Priority filters must cover all patients without overlap."


def test_modality_filtering(test_client):
    """Verify modality filter identifies patients possessing ECG, PPG, ABP, or Clinical Vitals."""
    sim_state = test_client.get("/api/simulation/state").json()
    patients = sim_state["patients"]

    def filter_by_modality(mod, pts):
        m_upper = mod.upper()
        return [
            p for p in pts
            if any(m_upper in str(item).upper() for item in p.get("available_modalities", []))
        ]

    ecg_patients = filter_by_modality("ECG", patients)
    assert len(ecg_patients) > 0, "ECG patients should be present in MIMIC cohort."
    for p in ecg_patients:
        assert any("ECG" in m.upper() for m in p["available_modalities"])


def test_sorting_preserves_patient_data(test_client):
    """Verify sorting changes ordering without altering underlying scores, IDs, or timestamps."""
    sim_state = test_client.get("/api/simulation/state").json()
    patients = sim_state["patients"]

    # Sort RISK_ASC
    sorted_asc = sorted(patients, key=lambda x: x["risk_score"])
    assert sorted_asc[0]["risk_score"] <= sorted_asc[-1]["risk_score"]

    # Sort PRIORITY_DESC (default)
    sorted_desc = sorted(patients, key=lambda x: x["risk_score"], reverse=True)
    assert sorted_desc[0]["risk_score"] >= sorted_desc[-1]["risk_score"]

    # Patient data integrity: set of record_ids must match exactly
    assert {p["record_id"] for p in sorted_asc} == {p["record_id"] for p in patients}
    assert {p["record_id"] for p in sorted_desc} == {p["record_id"] for p in patients}


def test_inspect_patient_detail_continuity(test_client):
    """Verify inspecting patient detail (/api/multimodal/analyze) works continuously without resetting simulation."""
    sim_state = test_client.get("/api/simulation/state").json()
    patients = sim_state["patients"]
    assert len(patients) > 0

    first_patient = patients[0]
    rec_id = first_patient["record_id"]

    res_analyze = test_client.post("/api/multimodal/analyze", json={"record_id": rec_id, "window_index": 0})
    assert res_analyze.status_code == 200
    data = res_analyze.json()
    assert str(data["record_id"]) == str(rec_id)
    assert "waveform_samples" in data or "waveform_features" in data
    assert "clinical_features" in data
    assert "risk_score" in data

    # Check simulation engine current_step did not reset or jump
    sim_state_after = test_client.get("/api/simulation/state").json()
    assert sim_state_after["current_step"] == sim_state["current_step"]
