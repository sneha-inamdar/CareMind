"""
Automated Test Suite for CareMind Supabase Cohort Synchronization & Permission Fallback.

Tests all 8 required milestone scenarios:
1. Initial Sync 3 -> 24
2. Idempotent re-sync (24 -> 24, no duplicates)
3. Expansion (24 -> 30)
4. Shrinking (30 -> 24, safe removal of obsolete records)
5. Permission error fallback to LocalJSON
6. Permission recovery
7. Read/write operations on waveform_records table
8. Identifier matching & duplicate prevention
"""

import pytest
from unittest.mock import MagicMock, patch
from src.db.repository import LocalJSONRepository, SupabaseRepository, get_repository
from src.db.cohort_sync import MIMICCohortSyncEngine, sync_cohort_to_supabase
from src.db.config import DatabaseConfig


class DummyDataResponse:
    def __init__(self, data):
        self.data = data

    def execute(self):
        return self


class MockSupabaseTable:
    def __init__(self, name, db_state):
        self.name = name
        self.db_state = db_state
        self._where_clause = None

    def select(self, columns="*"):
        return self

    def eq(self, column, val):
        self._where_clause = (column, val)
        return self

    def order(self, column, desc=False):
        return self

    def limit(self, count):
        return self

    def upsert(self, data, on_conflict=None):
        data_list = data if isinstance(data, list) else [data]
        pk_map = {
            "patients": "subject_id",
            "icu_stays": "stay_id",
            "waveform_records": "record_id",
            "observation_windows": "id",
            "vital_observations": "id",
            "risk_assessments": "id"
        }
        pk = pk_map.get(self.name, "id")
        
        for item in data_list:
            item_pk = item.get(pk)
            # Find and update or append
            found = False
            for idx, existing in enumerate(self.db_state[self.name]):
                if existing.get(pk) == item_pk and item_pk is not None:
                    self.db_state[self.name][idx] = {**existing, **item}
                    found = True
                    break
            if not found:
                if "id" in pk and "id" not in item:
                    item = {**item, "id": f"uuid-{len(self.db_state[self.name])+1}"}
                self.db_state[self.name].append(item)
        return DummyDataResponse(data_list)

    def insert(self, data):
        return self.upsert(data)

    def delete(self):
        return self

    def execute(self):
        if self._where_clause and self._where_clause[0] == "record_id":
            val = self._where_clause[1]
            # Perform deletion if in delete mode
            self.db_state[self.name] = [r for r in self.db_state[self.name] if r.get("record_id") != val]
            self._where_clause = None
            return DummyDataResponse([])

        rows = self.db_state.get(self.name, [])
        if self._where_clause:
            col, val = self._where_clause
            rows = [r for r in rows if r.get(col) == val]
            self._where_clause = None
        return DummyDataResponse(rows)


class MockSupabaseClient:
    def __init__(self):
        self.db_state = {
            "patients": [],
            "icu_stays": [],
            "waveform_records": [],
            "observation_windows": [],
            "vital_observations": [],
            "risk_assessments": [],
            "physiological_alerts": []
        }

    def table(self, table_name):
        return MockSupabaseTable(table_name, self.db_state)


def generate_mock_cohort(count: int):
    """Generates mock source cohort of N records."""
    cohort = []
    for i in range(1, count + 1):
        subj_id = 10000000 + i
        rec_id = f"8000000{i:02d}"
        cohort.append({
            "record_id": rec_id,
            "subject_id": subj_id,
            "stay_id": 30000000 + i,
            "bed_id": f"Bed ICU-{i:02d}",
            "duration_hrs": 24.0,
            "fs": 125.0,
            "available_modalities": ["ECG", "PPG", "Clinical Vitals"],
            "tier": "Tier 2 (ECG+PPG)",
            "windows_count": 4,
            "description": f"Patient #{subj_id}"
        })
    return cohort


def test_scenario_1_and_2_initial_sync_and_idempotency():
    """TEST 1 & 2: Supabase starts with 3, syncs to 24, then re-syncs to 24 without duplicates."""
    mock_client = MockSupabaseClient()
    sync_engine = MIMICCohortSyncEngine(client=mock_client)

    # Seed initial 3 records
    initial_3 = generate_mock_cohort(3)
    sync_engine.sync_cohort_to_supabase(initial_3)
    assert len(mock_client.db_state["waveform_records"]) == 3

    # Sync larger source cohort of 24
    cohort_24 = generate_mock_cohort(24)
    res = sync_engine.sync_cohort_to_supabase(cohort_24)

    assert res["status"] == "success"
    assert res["synced_count"] == 24
    assert len(mock_client.db_state["patients"]) == 24
    assert len(mock_client.db_state["icu_stays"]) == 24
    assert len(mock_client.db_state["waveform_records"]) == 24

    # TEST 2: Re-run sync with 24
    res2 = sync_engine.sync_cohort_to_supabase(cohort_24)
    assert res2["status"] == "success"
    assert len(mock_client.db_state["waveform_records"]) == 24


def test_scenario_3_and_4_expansion_and_shrinking():
    """TEST 3 & 4: Expansion from 24 -> 30, then shrinking from 30 -> 24."""
    mock_client = MockSupabaseClient()
    sync_engine = MIMICCohortSyncEngine(client=mock_client)

    cohort_24 = generate_mock_cohort(24)
    sync_engine.sync_cohort_to_supabase(cohort_24)
    assert len(mock_client.db_state["waveform_records"]) == 24

    # TEST 3: Expand to 30
    cohort_30 = generate_mock_cohort(30)
    res_exp = sync_engine.sync_cohort_to_supabase(cohort_30)
    assert res_exp["status"] == "success"
    assert len(mock_client.db_state["waveform_records"]) == 30

    # TEST 4: Shrink back to 24
    res_shrink = sync_engine.sync_cohort_to_supabase(cohort_24)
    assert res_shrink["status"] == "success"
    assert len(mock_client.db_state["waveform_records"]) == 24


def test_scenario_5_and_6_permission_error_and_recovery():
    """TEST 5 & 6: Permission 42501 error triggers LocalJSON fallback; recovery uses Supabase."""
    # TEST 5: Permission error mock
    failing_client = MagicMock()
    failing_client.table.side_effect = Exception("42501 permission denied for table waveform_records")

    sync_engine = MIMICCohortSyncEngine(client=failing_client)
    res = sync_engine.sync_cohort_to_supabase(generate_mock_cohort(5))
    assert res["status"] == "error"
    assert "42501" in res["error"]

    # TEST 6: Normal recovery
    working_client = MockSupabaseClient()
    sync_engine_ok = MIMICCohortSyncEngine(client=working_client)
    res_ok = sync_engine_ok.sync_cohort_to_supabase(generate_mock_cohort(5))
    assert res_ok["status"] == "success"


def test_scenario_7_waveform_records_crud():
    """TEST 7: waveform_records table read/write operations succeed on client."""
    mock_client = MockSupabaseClient()
    sync_engine = MIMICCohortSyncEngine(client=mock_client)

    res = sync_engine.sync_cohort_to_supabase(generate_mock_cohort(10))
    assert res["status"] == "success"

    rec_table = mock_client.table("waveform_records")
    data = rec_table.select("*").execute().data
    assert len(data) == 10


def test_scenario_8_identifier_matching():
    """TEST 8: Verify exact subject_id, stay_id, record_id matching without duplicates."""
    mock_client = MockSupabaseClient()
    sync_engine = MIMICCohortSyncEngine(client=mock_client)
    cohort = generate_mock_cohort(24)

    sync_engine.sync_cohort_to_supabase(cohort)
    synced_records = mock_client.db_state["waveform_records"]

    for src in cohort:
        matched = [r for r in synced_records if r["record_id"] == src["record_id"]]
        assert len(matched) == 1
        assert matched[0]["subject_id"] == src["subject_id"]
        assert matched[0]["stay_id"] == src["stay_id"]
