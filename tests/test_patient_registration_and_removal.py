import os
import json
import pytest
from fastapi.testclient import TestClient
from backend.main import app, db_repository, simulation_engine


@pytest.fixture
def client():
    return TestClient(app)


def test_html_contains_two_option_entry_and_confirmation_dialog():
    """Verify frontend HTML contains Option A, Option B, and Removal confirmation dialog."""
    dist_html_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist", "index.html")
    assert os.path.exists(dist_html_path), "frontend/dist/index.html must exist"
    with open(dist_html_path, "r", encoding="utf-8") as f:
        html = f.read()

    # Check 2 options in modal
    assert 'id="tabOptionManual"' in html
    assert 'id="tabOptionCohort"' in html
    assert 'id="bodyOptionManual"' in html
    assert 'id="bodyOptionCohort"' in html
    assert 'id="btnSubmitManualRegister"' in html

    # Check manual registration fields
    assert 'id="regPatientName"' in html
    assert 'id="regPatientId"' in html
    assert 'id="regPatientAge"' in html
    assert 'id="regPatientSex"' in html
    assert 'id="regPatientBed"' in html
    assert 'id="regPatientNotes"' in html

    # Check confirmation dialog
    assert 'id="removePatientModal"' in html
    assert "Remove patient from monitoring?" in html
    assert 'id="btnConfirmRemovePatient"' in html
    assert 'id="btnCancelRemovePatient"' in html
    assert "leaves the active monitored roster" in html or "leave the active monitored roster" in html


def test_manual_registration_validation(client):
    """Verify manual registration validates required fields."""
    # Missing name
    res1 = client.post("/api/patients/register", json={"name": "", "patient_id": "PT-9999"})
    assert res1.status_code == 400
    assert "name is required" in res1.json()["detail"].lower()

    # Missing patient_id
    res2 = client.post("/api/patients/register", json={"name": "Alice Smith", "patient_id": ""})
    assert res2.status_code == 400
    assert "id is required" in res2.json()["detail"].lower()


def test_manual_registration_persistence_and_no_fake_data(client):
    """Verify manual registration persists correctly, assigns proper status, and does not invent fake vitals or risk score."""
    test_pid = "TEST-REG-101"
    # Clean up if previously registered
    db_repository.remove_registered_patient(test_pid)

    payload = {
        "name": "Evelyn Reed",
        "patient_id": test_pid,
        "age": 62,
        "sex": "Female",
        "bed_id": "Bed ICU-09",
        "notes": "Post-op observation"
    }

    res = client.post("/api/patients/register", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "Physiological data is not connected, so AI risk monitoring is currently unavailable." in data["message"]

    patient = data["patient"]
    assert patient["name"] == "Evelyn Reed"
    assert patient["patient_id"] == test_pid
    assert patient["monitoring_status"] == "Registered — No Data Source Connected"
    assert patient["is_monitored"] is False
    assert patient["risk_score"] is None
    assert patient["vitals"] is None
    assert patient["available_modalities"] == []

    # Verify query registered patients
    get_res = client.get("/api/patients/registered")
    assert get_res.status_code == 200
    registered_list = get_res.json()["patients"]
    matched = [p for p in registered_list if p["patient_id"] == test_pid]
    assert len(matched) == 1

    # Cleanup
    db_repository.remove_registered_patient(test_pid)


def test_manual_registration_duplicate_rejection(client):
    """Verify duplicate patient IDs are rejected with HTTP 409."""
    test_pid = "TEST-DUP-202"
    db_repository.remove_registered_patient(test_pid)

    payload = {
        "name": "Marcus Vance",
        "patient_id": test_pid,
        "bed_id": "Bed ICU-12"
    }

    res1 = client.post("/api/patients/register", json=payload)
    assert res1.status_code == 200

    # Try registering again with same ID
    res2 = client.post("/api/patients/register", json=payload)
    assert res2.status_code == 409
    assert "already registered" in res2.json()["detail"].lower()

    # Cleanup
    db_repository.remove_registered_patient(test_pid)


def test_simulation_state_includes_registered_patients(client):
    """Verify /api/simulation/state includes registered patients without altering monitored counts."""
    test_pid = "TEST-SIM-303"
    db_repository.remove_registered_patient(test_pid)

    client.post("/api/patients/register", json={"name": "George Clark", "patient_id": test_pid})

    res = client.get("/api/simulation/state")
    assert res.status_code == 200
    state = res.json()

    assert "registered_patients" in state
    assert any(p["patient_id"] == test_pid for p in state["registered_patients"])
    assert state["registered_patient_count"] >= 1

    # Monitored patients must all have is_monitored = True
    for p in state["patients"]:
        assert p.get("is_monitored") is True
        assert p.get("monitoring_status") == "Dataset Replay Active"

    # Cleanup
    db_repository.remove_registered_patient(test_pid)


def test_add_and_remove_patient_lifecycle(client):
    """
    Verify complete lifecycle:
    1. Check available records
    2. Add record to monitored cohort
    3. Monitored count increases
    4. Duplicate addition is rejected (409)
    5. Remove patient from monitored cohort
    6. Monitored count decreases
    7. Record returns to available inventory
    8. Raw dataset record and inventory are preserved
    """
    avail_res = client.get("/api/multimodal/records/available")
    assert avail_res.status_code == 200
    records = avail_res.json().get("records", [])

    if not records:
        # If all monitored, remove one to test
        current_monitored = db_repository.get_monitored_record_ids()
        assert len(current_monitored) > 0
        target_rec_id = current_monitored[-1]
        client.post("/api/multimodal/patients/remove", json={"record_id": target_rec_id})
        avail_res = client.get("/api/multimodal/records/available")
        records = avail_res.json().get("records", [])

    assert len(records) > 0
    candidate = records[0]
    candidate_id = str(candidate["record_id"])

    # Initial state count
    sim_before = client.get("/api/simulation/state").json()
    monitored_count_before = sim_before["patient_count"]

    # 1. Add patient
    add_res = client.post("/api/multimodal/patients/add", json={"record_id": candidate_id})
    assert add_res.status_code == 200
    add_data = add_res.json()
    assert add_data["status"] == "success"
    assert add_data["monitored_patient_count"] == monitored_count_before + 1

    # 2. Duplicate rejection
    dup_res = client.post("/api/multimodal/patients/add", json={"record_id": candidate_id})
    assert dup_res.status_code == 409

    # 3. Verify in simulation states
    assert candidate_id in simulation_engine.patient_states

    # 4. Remove patient
    remove_res = client.post("/api/multimodal/patients/remove", json={"record_id": candidate_id})
    assert remove_res.status_code == 200
    rem_data = remove_res.json()
    assert rem_data["status"] == "success"
    assert rem_data["monitored_patient_count"] == monitored_count_before

    # 5. Verify removed from simulation states and alerts
    assert candidate_id not in simulation_engine.patient_states
    alerts_for_patient = simulation_engine.alert_engine.get_patient_active_alerts(candidate_id)
    assert len(alerts_for_patient) == 0

    # 6. Verify record is back in available records and inventory preserved
    avail_after = client.get("/api/multimodal/records/available")
    avail_records_after = [str(r["record_id"]) for r in avail_after.json().get("records", [])]
    assert candidate_id in avail_records_after

    inventory = db_repository.get_inventory_records()
    assert any(str(r["record_id"]) == candidate_id for r in inventory)


def test_remove_nonexistent_patient_returns_404(client):
    """Verify removing a patient not present in cohort returns 404."""
    res = client.post("/api/multimodal/patients/remove", json={"record_id": "NONEXISTENT_99999"})
    assert res.status_code == 404
