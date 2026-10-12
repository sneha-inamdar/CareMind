
"""
CareMind Database Repository & Persistence Layer.

Provides clean repository interface decoupling the ML/Risk engine from database storage.
Supports both Supabase PostgreSQL and Local JSON fallback repository implementations.
"""

import os
import json
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

from src.db.config import DatabaseConfig

# Attempt to import Supabase SDK if installed
try:
    from supabase import create_client, Client
    SUPABASE_SDK_AVAILABLE = True
except ImportError:
    SUPABASE_SDK_AVAILABLE = False


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "demo_waveforms")


class CareMindBaseRepository(ABC):
    """Abstract base repository contract for CareMind data operations."""

    @abstractmethod
    def get_available_records(self) -> List[Dict[str, Any]]:
        """Return list of available demo records."""
        pass

    @abstractmethod
    def get_patients_overview(self, window_index: int = 0) -> List[Dict[str, Any]]:
        """Return list of active ICU patients sorted by highest risk score first."""
        pass

    @abstractmethod
    def get_record_detail(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Return details for a specific record."""
        pass

    @abstractmethod
    def get_unmonitored_records(self) -> List[Dict[str, Any]]:
        """Return genuine records from inventory not currently in monitored cohort."""
        pass

    @abstractmethod
    def get_monitored_record_ids(self) -> List[str]:
        """Return list of record IDs currently monitored."""
        pass

    @abstractmethod
    def get_inventory_records(self) -> List[Dict[str, Any]]:
        """Return all genuine records from cohort inventory."""
        pass

    @abstractmethod
    def add_patient_to_cohort(self, record_id: str) -> Dict[str, Any]:
        """Add a genuine record to the active monitored cohort."""
        pass

    @abstractmethod
    def remove_patient_from_cohort(self, record_id: str) -> Dict[str, Any]:
        """Remove a patient from the active monitored cohort while preserving raw data and inventory."""
        pass

    @abstractmethod
    def get_registered_patients(self) -> List[Dict[str, Any]]:
        """Return list of manually registered patients."""
        pass

    @abstractmethod
    def register_patient(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """Register a patient profile manually without attaching physiological dataset records."""
        pass

    @abstractmethod
    def remove_registered_patient(self, patient_id: str) -> bool:
        """Remove a manually registered patient."""
        pass

    @abstractmethod
    def is_record_monitored(self, record_id: str) -> bool:
        """Check if record_id is currently monitored."""
        pass


class LocalJSONRepository(CareMindBaseRepository):
    """Local JSON cache repository implementation for offline/demo execution."""

    def __init__(self, data_dir: str = DATA_DIR):
        self.data_dir = data_dir
        self.monitored_cohort_path = os.path.join(self.data_dir, "monitored_cohort.json")
        self.registered_patients_path = os.path.join(self.data_dir, "registered_patients.json")
        self.fallback_records_metadata = [
            {
                "record_id": "81739927",
                "subject_id": 10014354,
                "stay_id": 39880770,
                "bed_id": "Bed ICU-01",
                "duration_hrs": 24.0,
                "fs": 62.5,
                "available_modalities": ["ECG", "PPG", "Resp", "Clinical Vitals"],
                "tier": "Tier 2 (ECG+PPG)",
                "windows_count": 4,
                "description": "Patient #10014354 — Progressive tachycardia & oxygen saturation drop"
            },
            {
                "record_id": "83404654",
                "subject_id": 10020306,
                "stay_id": 38418938,
                "bed_id": "Bed ICU-02",
                "duration_hrs": 24.0,
                "fs": 62.5,
                "available_modalities": ["ECG", "PPG", "Resp", "Clinical Vitals"],
                "tier": "Tier 2 (ECG+PPG)",
                "windows_count": 4,
                "description": "Patient #10020306 — Persistent moderate tachycardia & tachypnea"
            },
            {
                "record_id": "82924339",
                "subject_id": 10126957,
                "stay_id": 39149479,
                "bed_id": "Bed ICU-03",
                "duration_hrs": 24.0,
                "fs": 125.0,
                "available_modalities": ["ECG", "PPG", "ABP", "Resp", "Clinical Vitals"],
                "tier": "Tier 1 (ECG+ABP+PPG)",
                "windows_count": 4,
                "description": "Patient #10126957 — Tier 1 record with acute hypotensive shock dynamics"
            }
        ]

    def _load_cached_json(self, record_id: str) -> Dict[str, Any]:
        cache_path = os.path.join(self.data_dir, f"{record_id}.json")
        if os.path.exists(cache_path):
            with open(cache_path, "r") as f:
                return json.load(f)
        return {}

    def get_inventory_records(self) -> List[Dict[str, Any]]:
        """Return all genuine records present in dataset index or local cache directory."""
        index_path = os.path.join(self.data_dir, "records_index.json")
        if os.path.exists(index_path):
            try:
                with open(index_path, "r") as f:
                    meta = json.load(f)
                    if meta and len(meta) > 0:
                        return meta
            except Exception:
                pass

        if os.path.exists(self.data_dir):
            files = [
                f for f in os.listdir(self.data_dir)
                if f.endswith(".json") and f not in ["records_index.json", "monitored_cohort.json"]
            ]
            if files:
                records = []
                for fn in files:
                    try:
                        with open(os.path.join(self.data_dir, fn), "r") as f:
                            data = json.load(f)
                            records.append({
                                "record_id": str(data.get("record_id", fn.replace(".json", ""))),
                                "subject_id": int(data.get("subject_id", 10000000)),
                                "stay_id": int(data.get("stay_id", 30000000)),
                                "bed_id": data.get("bed_id", "Bed ICU"),
                                "duration_hrs": data.get("duration_hrs", 24.0),
                                "fs": data.get("fs", 125.0),
                                "available_modalities": data.get("available_modalities", ["ECG", "Clinical Vitals"]),
                                "tier": data.get("tier", "Tier 2 (ECG+PPG)"),
                                "windows_count": len(data.get("windows", [])),
                                "description": data.get("description", f"Patient #{data.get('subject_id')}")
                            })
                    except Exception:
                        pass
                if records:
                    records.sort(key=lambda x: x["subject_id"])
                    return records

        return self.fallback_records_metadata

    def get_monitored_record_ids(self) -> List[str]:
        """Return list of record IDs currently active in the monitored operational cohort."""
        if os.path.exists(self.monitored_cohort_path):
            try:
                with open(self.monitored_cohort_path, "r") as f:
                    data = json.load(f)
                    if isinstance(data, list) and len(data) > 0:
                        ids = [str(item["record_id"]) if isinstance(item, dict) else str(item) for item in data]
                        return ids
            except Exception as e:
                print(f"[Repository] Warning reading monitored_cohort.json: {e}")

        # Default initial operational cohort: 20 genuine records, leaving 4 available genuine records
        inventory = self.get_inventory_records()
        if len(inventory) > 20:
            initial_ids = [str(r["record_id"]) for r in inventory[:20]]
        else:
            initial_ids = [str(r["record_id"]) for r in inventory]
        self._save_monitored_record_ids(initial_ids)
        return initial_ids

    def _save_monitored_record_ids(self, ids: List[str]):
        """Persist active monitored cohort record IDs to local JSON file."""
        try:
            with open(self.monitored_cohort_path, "w") as f:
                json.dump(ids, f, indent=2)
        except Exception as e:
            print(f"[Repository] Error saving monitored_cohort.json: {e}")

    def get_available_records(self) -> List[Dict[str, Any]]:
        """Return metadata for all active monitored records in operational cohort."""
        monitored_ids = set(self.get_monitored_record_ids())
        inventory = self.get_inventory_records()
        monitored_records = [r for r in inventory if str(r["record_id"]) in monitored_ids]
        if not monitored_records:
            return inventory
        return monitored_records

    def get_unmonitored_records(self) -> List[Dict[str, Any]]:
        """Return genuine records from inventory that are not currently monitored."""
        monitored_ids = set(self.get_monitored_record_ids())
        inventory = self.get_inventory_records()
        return [r for r in inventory if str(r["record_id"]) not in monitored_ids]

    def is_record_monitored(self, record_id: str) -> bool:
        """Check if record_id is already present in monitored cohort."""
        return str(record_id).strip() in set(self.get_monitored_record_ids())

    def add_patient_to_cohort(self, record_id: str) -> Dict[str, Any]:
        """Add a genuine record to the active monitored cohort."""
        rec_id = str(record_id).strip()
        inventory = self.get_inventory_records()
        found_meta = next((r for r in inventory if str(r["record_id"]) == rec_id), None)
        if not found_meta:
            raise ValueError(f"Record '{rec_id}' not found in genuine cohort inventory.")

        current_ids = self.get_monitored_record_ids()
        if rec_id in current_ids:
            raise ValueError(f"Record '{rec_id}' is already present in the active monitored cohort.")

        current_ids.append(rec_id)
        self._save_monitored_record_ids(current_ids)
        print(f"[Repository] Added record {rec_id} to active monitored cohort (Total: {len(current_ids)})")
        return found_meta

    def remove_patient_from_cohort(self, record_id: str) -> Dict[str, Any]:
        """Remove a patient from the active monitored cohort while preserving raw data and inventory."""
        rec_id = str(record_id).strip()
        current_ids = self.get_monitored_record_ids()

        if rec_id not in current_ids:
            # Check if it was a registered patient
            reg_removed = self.remove_registered_patient(rec_id)
            if reg_removed:
                return {
                    "record_id": rec_id,
                    "patient_id": rec_id,
                    "status": "removed_registered"
                }
            raise ValueError(f"Record '{rec_id}' is not in the active monitored cohort.")

        current_ids.remove(rec_id)
        self._save_monitored_record_ids(current_ids)

        inventory = self.get_inventory_records()
        meta = next((r for r in inventory if str(r["record_id"]) == rec_id), {"record_id": rec_id})
        print(f"[Repository] Removed record {rec_id} from active monitored cohort (Remaining: {len(current_ids)})")
        return meta

    def get_registered_patients(self) -> List[Dict[str, Any]]:
        """Return list of manually registered patients without attached physiological data."""
        if os.path.exists(self.registered_patients_path):
            try:
                with open(self.registered_patients_path, "r") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data
            except Exception as e:
                print(f"[Repository] Warning reading registered_patients.json: {e}")
        return []

    def _save_registered_patients(self, patients: List[Dict[str, Any]]):
        try:
            with open(self.registered_patients_path, "w") as f:
                json.dump(patients, f, indent=2)
        except Exception as e:
            print(f"[Repository] Error saving registered_patients.json: {e}")

    def register_patient(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """Register a patient profile manually without attaching physiological dataset records."""
        name = str(patient_data.get("name", "")).strip()
        patient_id = str(patient_data.get("patient_id", "")).strip()

        if not name:
            raise ValueError("Patient name is required.")
        if not patient_id:
            raise ValueError("Patient ID is required.")

        # Check uniqueness across registered patients
        registered = self.get_registered_patients()
        for p in registered:
            if str(p.get("patient_id", "")).strip().lower() == patient_id.lower():
                raise ValueError(f"Patient ID '{patient_id}' is already registered.")

        # Also check uniqueness against actively monitored patients
        monitored_records = self.get_available_records()
        for m in monitored_records:
            if str(m.get("subject_id", "")).strip().lower() == patient_id.lower() or str(m.get("record_id", "")).strip().lower() == patient_id.lower():
                raise ValueError(f"Patient ID '{patient_id}' conflicts with an existing monitored patient identifier.")

        age = patient_data.get("age")
        if age is not None and str(age).strip():
            try:
                age = int(age)
            except (ValueError, TypeError):
                age = None
        else:
            age = None

        new_patient = {
            "patient_id": patient_id,
            "subject_id": patient_id,
            "name": name,
            "age": age,
            "sex": str(patient_data.get("sex", "")).strip() or "Unspecified",
            "bed_id": str(patient_data.get("bed_id", "")).strip() or "Unassigned Bed",
            "notes": str(patient_data.get("notes", "")).strip(),
            "monitoring_status": "Registered — No Data Source Connected",
            "is_monitored": False,
            "record_id": None,
            "stay_id": None,
            "available_modalities": [],
            "risk_score": None,
            "priority_status": "UNMONITORED",
            "vitals": None,
            "created_at": "2026-10-12T19:00:00Z"
        }

        registered.append(new_patient)
        self._save_registered_patients(registered)
        print(f"[Repository] Registered patient {name} (ID: {patient_id}) without physiological data.")
        return new_patient

    def remove_registered_patient(self, patient_id: str) -> bool:
        pid = str(patient_id).strip().lower()
        registered = self.get_registered_patients()
        filtered = [p for p in registered if str(p.get("patient_id", "")).strip().lower() != pid]
        if len(filtered) < len(registered):
            self._save_registered_patients(filtered)
            return True
        return False

    def get_patients_overview(self, window_index: int = 0) -> List[Dict[str, Any]]:
        patients = []
        records = self.get_available_records()
        for meta in records:
            cached = self._load_cached_json(meta["record_id"])
            if cached and "windows" in cached and len(cached["windows"]) > 0:
                w_idx = min(window_index, len(cached["windows"]) - 1)
                w_data = cached["windows"][w_idx]

                factors = w_data.get("contributing_factors", [])
                primary_alert = factors[0]["factor"] if factors else "Normal Parameters"

                patients.append({
                    "record_id": meta["record_id"],
                    "subject_id": meta["subject_id"],
                    "stay_id": meta["stay_id"],
                    "bed_id": meta.get("bed_id", f"Bed ICU-{(meta['subject_id'] % 20) + 1:02d}"),
                    "window_index": w_idx,
                    "timestamp": w_data.get("timestamp"),
                    "risk_score": w_data.get("risk_score", 0.0),
                    "risk_category": w_data.get("risk_category", "LOW"),
                    "risk_trend_status": w_data.get("risk_trend_status", "STABLE"),
                    "risk_trend_delta": w_data.get("risk_trend_delta", 0.0),
                    "priority_status": w_data.get("priority_status", "ROUTINE_MONITORING"),
                    "vitals": w_data.get("clinical_features", {}),
                    "primary_alert": primary_alert,
                    "available_modalities": w_data.get("available_modalities", []),
                    "contributing_factors": factors,
                    "disclaimer": w_data.get("disclaimer", "CareMind Physiological Risk Score is an engineering prototype decision-support metric.")
                })

        # Sort patients descending by highest CareMind risk score first
        patients.sort(key=lambda p: p["risk_score"], reverse=True)
        return patients

    def get_record_detail(self, record_id: str) -> Optional[Dict[str, Any]]:
        cached = self._load_cached_json(record_id)
        if not cached:
            return None
        return {
            "record_id": record_id,
            "subject_id": cached.get("subject_id"),
            "windows_count": len(cached.get("windows", [])),
            "cached": True
        }

    def get_replay_timeline(self, record_id: str) -> List[Dict[str, Any]]:
        cached = self._load_cached_json(record_id)
        return cached.get("windows", [])


class SupabaseRepository(CareMindBaseRepository):
    """Supabase PostgreSQL repository implementation using Supabase Python Client SDK."""

    def __init__(self, db_config: Optional[DatabaseConfig] = None, auto_sync: bool = False):
        self.config = db_config or DatabaseConfig()
        if not SUPABASE_SDK_AVAILABLE:
            raise ImportError("supabase python SDK is not installed.")
        if not self.config.is_supabase_configured:
            raise ValueError("Supabase environment variables (SUPABASE_URL, SUPABASE_KEY) are missing or invalid.")
        
        # Prefer service key if available for backend operations
        key = self.config.supabase_service_key or self.config.supabase_key
        self.client: Client = create_client(self.config.supabase_url, key)
        self.local_fallback = LocalJSONRepository()
        
        if auto_sync:
            self.sync_cohort()

    def sync_cohort(self, source_cohort: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Synchronizes source cohort records into Supabase operational tables."""
        from src.db.cohort_sync import MIMICCohortSyncEngine
        sync_engine = MIMICCohortSyncEngine(db_config=self.config, client=self.client)
        return sync_engine.sync_cohort_to_supabase(source_cohort)

    def get_inventory_records(self) -> List[Dict[str, Any]]:
        """Return all genuine records from inventory."""
        return self.local_fallback.get_inventory_records()

    def get_monitored_record_ids(self) -> List[str]:
        """Return list of record IDs currently monitored."""
        return self.local_fallback.get_monitored_record_ids()

    def get_unmonitored_records(self) -> List[Dict[str, Any]]:
        """Return genuine records from inventory not currently in monitored cohort."""
        return self.local_fallback.get_unmonitored_records()

    def is_record_monitored(self, record_id: str) -> bool:
        """Check if record_id is currently monitored."""
        return self.local_fallback.is_record_monitored(record_id)

    def add_patient_to_cohort(self, record_id: str) -> Dict[str, Any]:
        """Add a genuine record to the active monitored cohort and synchronize with Supabase."""
        meta = self.local_fallback.add_patient_to_cohort(record_id)
        # Synchronize operational metadata with Supabase if client available (without shrinking)
        try:
            from src.db.cohort_sync import MIMICCohortSyncEngine
            sync_engine = MIMICCohortSyncEngine(db_config=self.config, client=self.client)
            sync_engine.sync_cohort_to_supabase([meta], deactivate_obsolete=False)
            print(f"[Repository] Synchronized added record {record_id} to Supabase")
        except Exception as err:
            err_msg = str(err)
            if "42501" in err_msg or "permission denied" in err_msg.lower():
                print(f"[Repository] Supabase permission error (42501) — using LocalJSON fallback ({err_msg})")
            else:
                print(f"[Repository] Supabase synchronization notice: {err_msg} — preserved LocalJSON fallback")
        return meta

    def remove_patient_from_cohort(self, record_id: str) -> Dict[str, Any]:
        """Remove a patient from the active monitored cohort and update Supabase."""
        meta = self.local_fallback.remove_patient_from_cohort(record_id)
        try:
            stay_id = meta.get("stay_id")
            if stay_id:
                self.client.table("icu_stays").update({"status": "INACTIVE"}).eq("stay_id", stay_id).execute()
        except Exception as err:
            print(f"[Repository] Supabase deactivation notice: {err} — preserved LocalJSON fallback")
        return meta

    def get_registered_patients(self) -> List[Dict[str, Any]]:
        return self.local_fallback.get_registered_patients()

    def register_patient(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        patient = self.local_fallback.register_patient(patient_data)
        try:
            pid = patient["patient_id"]
            if str(pid).isdigit():
                subj_id = int(pid)
                self.client.table("patients").upsert({
                    "subject_id": subj_id,
                    "gender": str(patient.get("sex", "M"))[0].upper() if patient.get("sex") else "M",
                    "anchor_age": patient.get("age") or 65
                }).execute()
        except Exception as err:
            err_msg = str(err)
            if "42501" in err_msg or "permission denied" in err_msg.lower():
                print(f"[Repository] Supabase permission notice (42501) — using LocalJSON fallback ({err_msg})")
            else:
                print(f"[Repository] Supabase registration notice: {err_msg} — preserved LocalJSON fallback")
        return patient

    def remove_registered_patient(self, patient_id: str) -> bool:
        return self.local_fallback.remove_registered_patient(patient_id)

    def get_available_records(self) -> List[Dict[str, Any]]:
        # Align with active operational cohort
        return self.local_fallback.get_available_records()

    def get_patients_overview(self, window_index: int = 0) -> List[Dict[str, Any]]:
        try:
            # Query risk assessments from Supabase joined with stays
            res = self.client.table("risk_assessments") \
                .select("*, icu_stays(bed_id, subject_id, careunit), vital_observations(*)") \
                .execute()
            if res.data and len(res.data) > 0:
                patients = []
                for row in res.data:
                    stay = row.get("icu_stays", {})
                    vitals = row.get("vital_observations", {})
                    patients.append({
                        "record_id": row.get("record_id"),
                        "subject_id": stay.get("subject_id"),
                        "stay_id": row.get("stay_id"),
                        "bed_id": stay.get("bed_id", "Bed ICU"),
                        "window_index": window_index,
                        "risk_score": float(row.get("risk_score", 0.0)),
                        "risk_category": row.get("risk_category", "LOW"),
                        "vitals": vitals,
                        "primary_alert": "Monitored via Supabase"
                    })
                patients.sort(key=lambda p: p["risk_score"], reverse=True)
                print(f"[Repository] Using Supabase ({len(patients)} ICU patients overview)")
                return patients
        except Exception as err:
            err_msg = str(err)
            if "42501" in err_msg or "permission denied" in err_msg.lower():
                print(f"[Repository] Supabase permission error (42501) — using LocalJSON fallback ({err_msg})")
            else:
                print(f"[Repository] Supabase notice: {err} — using LocalJSON fallback")
        return self.local_fallback.get_patients_overview(window_index)

    def get_record_detail(self, record_id: str) -> Optional[Dict[str, Any]]:
        try:
            res = self.client.table("waveform_records").select("*").eq("record_id", record_id).execute()
            if res.data and len(res.data) > 0:
                row = res.data[0]
                return {
                    "record_id": row.get("record_id"),
                    "subject_id": row.get("subject_id"),
                    "stay_id": row.get("stay_id"),
                    "tier": row.get("tier"),
                    "windows_count": 4,
                    "cached": True,
                    "source": "supabase"
                }
        except Exception as err:
            err_msg = str(err)
            if "42501" in err_msg or "permission denied" in err_msg.lower():
                print(f"[Repository] Supabase permission error (42501) — using LocalJSON fallback ({err_msg})")
            else:
                print(f"[Repository] Supabase notice: {err} — using LocalJSON fallback")
        return self.local_fallback.get_record_detail(record_id)

    def get_replay_timeline(self, record_id: str) -> List[Dict[str, Any]]:
        try:
            res = self.client.table("observation_windows") \
                .select("*, vital_observations(*), risk_assessments(*)") \
                .eq("record_id", record_id) \
                .order("window_index") \
                .execute()
            if res.data and len(res.data) > 0:
                timeline = []
                for row in res.data:
                    vitals = row.get("vital_observations", [{}])[0] if row.get("vital_observations") else {}
                    risk = row.get("risk_assessments", [{}])[0] if row.get("risk_assessments") else {}
                    timeline.append({
                        "window_index": row.get("window_index", 0),
                        "timestamp": row.get("timestamp_label"),
                        "clinical_features": vitals,
                        "risk_score": float(risk.get("risk_score", 0.0)),
                        "risk_category": risk.get("risk_category", "LOW")
                    })
                return timeline
        except Exception as err:
            err_msg = str(err)
            if "42501" in err_msg or "permission denied" in err_msg.lower():
                print(f"[Repository] Supabase permission error (42501) — using LocalJSON fallback ({err_msg})")
            else:
                print(f"[Repository] Supabase notice: {err} — using LocalJSON fallback")
        return self.local_fallback.get_replay_timeline(record_id)


def get_repository() -> CareMindBaseRepository:
    """
    Factory function returning SupabaseRepository if configured,
    or LocalJSONRepository as robust fallback.
    """
    config = DatabaseConfig()
    if config.is_supabase_configured and SUPABASE_SDK_AVAILABLE:
        try:
            return SupabaseRepository(config, auto_sync=False)
        except Exception as err:
            print(f"[Repository] Supabase initialization notice: {err} — using LocalJSON fallback")
    else:
        print("[Repository] Supabase unconfigured — using LocalJSON fallback")
    return LocalJSONRepository()

