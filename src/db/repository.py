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
    def get_replay_timeline(self, record_id: str) -> List[Dict[str, Any]]:
        """Return complete timeline windows for a record."""
        pass


class LocalJSONRepository(CareMindBaseRepository):
    """Local JSON cache repository implementation for offline/demo execution."""

    def __init__(self, data_dir: str = DATA_DIR):
        self.data_dir = data_dir
        self.records_metadata = [
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

    def get_available_records(self) -> List[Dict[str, Any]]:
        return self.records_metadata

    def get_patients_overview(self, window_index: int = 0) -> List[Dict[str, Any]]:
        patients = []
        for meta in self.records_metadata:
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
                    "bed_id": meta["bed_id"],
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

    def __init__(self, db_config: Optional[DatabaseConfig] = None):
        self.config = db_config or DatabaseConfig()
        if not SUPABASE_SDK_AVAILABLE:
            raise ImportError("supabase python SDK is not installed.")
        if not self.config.is_supabase_configured:
            raise ValueError("Supabase environment variables (SUPABASE_URL, SUPABASE_KEY) are missing or invalid.")
        
        # Prefer service key if available for backend operations
        key = self.config.supabase_service_key or self.config.supabase_key
        self.client: Client = create_client(self.config.supabase_url, key)
        self.local_fallback = LocalJSONRepository()

    def get_available_records(self) -> List[Dict[str, Any]]:
        try:
            res = self.client.table("waveform_records").select("*").execute()
            if res.data and len(res.data) > 0:
                return res.data
        except Exception as err:
            print(f"[SupabaseRepository] get_available_records notice: {err}")
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
                return patients
        except Exception as err:
            print(f"[SupabaseRepository] get_patients_overview notice: {err}")
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
            print(f"[SupabaseRepository] get_record_detail notice: {err}")
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
            print(f"[SupabaseRepository] get_replay_timeline notice: {err}")
        return self.local_fallback.get_replay_timeline(record_id)


def get_repository() -> CareMindBaseRepository:
    """
    Factory function returning SupabaseRepository if configured,
    or LocalJSONRepository as robust fallback.
    """
    config = DatabaseConfig()
    if config.is_supabase_configured and SUPABASE_SDK_AVAILABLE:
        try:
            return SupabaseRepository(config)
        except Exception as err:
            print(f"[DatabaseFactory] Supabase initialization notice: {err}. Using LocalJSONRepository fallback.")
    return LocalJSONRepository()
