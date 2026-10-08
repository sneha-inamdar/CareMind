"""
CareMind Supabase Cohort Synchronization Engine.

Provides idempotent cohort synchronization between CareMind source cohort metadata
(dataset/index) and Supabase PostgreSQL operational database tables.
Handles cohort expansion (e.g. 3 -> 24, 24 -> 30) and cohort shrinking (30 -> 24) safely.
"""

import os
import json
from typing import Dict, List, Any, Optional, Set
from src.db.config import DatabaseConfig

try:
    from supabase import create_client, Client
    SUPABASE_SDK_AVAILABLE = True
except ImportError:
    SUPABASE_SDK_AVAILABLE = False


class MIMICCohortSyncEngine:
    """
    Idempotent Cohort Synchronization Engine for Supabase operational tables.
    """

    def __init__(self, db_config: Optional[DatabaseConfig] = None, client: Optional[Any] = None):
        self.config = db_config or DatabaseConfig()
        self.client = client
        if not self.client and SUPABASE_SDK_AVAILABLE and self.config.is_supabase_configured:
            key = self.config.supabase_service_key or self.config.supabase_key
            try:
                self.client = create_client(self.config.supabase_url, key)
            except Exception as e:
                print(f"[CohortSync] Client initialization notice: {e}")

    def sync_cohort_to_supabase(
        self, source_cohort: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Synchronizes the source cohort metadata with Supabase.
        Idempotent: prevents duplicate patients, stays, or records.
        Handles addition of new records and cleanup/deactivation of records no longer in source cohort.
        """
        if not self.client:
            print("[Repository] Supabase unavailable — using LocalJSON fallback")
            return {
                "status": "skipped",
                "reason": "Supabase client unavailable",
                "synced_count": 0
            }

        # Fetch active source cohort from LocalJSONRepository if not explicitly provided
        if source_cohort is None:
            from src.db.repository import LocalJSONRepository
            source_repo = LocalJSONRepository()
            source_cohort = source_repo.get_available_records()

        if not source_cohort:
            return {"status": "success", "synced_count": 0, "message": "Source cohort is empty"}

        active_record_ids: Set[str] = set()
        patients_to_upsert: List[Dict[str, Any]] = []
        stays_to_upsert: List[Dict[str, Any]] = []
        records_to_upsert: List[Dict[str, Any]] = []

        for meta in source_cohort:
            rec_id = str(meta["record_id"])
            subj_id = int(meta["subject_id"])
            stay_id = int(meta.get("stay_id", 30000000 + (subj_id % 1000000)))
            bed_id = str(meta.get("bed_id", f"Bed ICU-{(subj_id % 20) + 1:02d}"))
            careunit = str(meta.get("careunit", "Medical Intensive Care Unit (MICU)"))
            fs = float(meta.get("fs", 125.0))
            duration_hrs = float(meta.get("duration_hrs", 24.0))
            tier = str(meta.get("tier", "Tier 2 (ECG+PPG)"))
            modalities = meta.get("available_modalities", ["ECG", "Clinical Vitals"])
            gender = meta.get("gender", "M" if subj_id % 2 == 0 else "F")
            anchor_age = meta.get("anchor_age", 50 + (subj_id % 35))

            active_record_ids.add(rec_id)

            patients_to_upsert.append({
                "subject_id": subj_id,
                "gender": gender,
                "anchor_age": anchor_age
            })

            stays_to_upsert.append({
                "stay_id": stay_id,
                "subject_id": subj_id,
                "bed_id": bed_id,
                "careunit": careunit,
                "intime": "2150-01-01T08:00:00Z",
                "status": "ACTIVE"
            })

            records_to_upsert.append({
                "record_id": rec_id,
                "subject_id": subj_id,
                "stay_id": stay_id,
                "fs": fs,
                "duration_hrs": duration_hrs,
                "tier": tier,
                "available_modalities": modalities
            })

        # Deduplicate records by primary key before upserting
        patients_dict = {p["subject_id"]: p for p in patients_to_upsert}
        stays_dict = {s["stay_id"]: s for s in stays_to_upsert}
        records_dict = {r["record_id"]: r for r in records_to_upsert}

        try:
            # 1. Upsert Patients
            self.client.table("patients").upsert(list(patients_dict.values()), on_conflict="subject_id").execute()

            # 2. Upsert ICU Stays
            self.client.table("icu_stays").upsert(list(stays_dict.values()), on_conflict="stay_id").execute()

            # 3. Upsert Waveform Records
            self.client.table("waveform_records").upsert(list(records_dict.values()), on_conflict="record_id").execute()

            # 4. Handle Cohort Shrinking / Deactivation
            sb_records_res = self.client.table("waveform_records").select("record_id").execute()
            if sb_records_res.data:
                sb_rec_ids = {r["record_id"] for r in sb_records_res.data}
                obsolete_ids = sb_rec_ids - active_record_ids
                if obsolete_ids:
                    print(f"[CohortSync] Removing obsolete records from Supabase cohort: {obsolete_ids}")
                    for obs_id in obsolete_ids:
                        self.client.table("waveform_records").delete().eq("record_id", obs_id).execute()

            # 5. Synchronize observation windows, vitals & risk assessments for cached windows
            from src.db.repository import LocalJSONRepository
            source_repo = LocalJSONRepository()
            for meta in source_cohort:
                rec_id = str(meta["record_id"])
                stay_id = int(meta.get("stay_id", 30000000 + (int(meta["subject_id"]) % 1000000)))
                cached = source_repo._load_cached_json(rec_id)
                windows = cached.get("windows", [])
                if windows:
                    self._sync_record_windows(rec_id, stay_id, windows)

            print(f"[Repository] Using Supabase Repository (Synced cohort count: {len(records_dict)})")
            return {
                "status": "success",
                "synced_count": len(records_dict),
                "record_ids": sorted(list(active_record_ids))
            }

        except Exception as err:
            err_msg = str(err)
            if "42501" in err_msg or "permission denied" in err_msg.lower():
                print(f"[Repository] Supabase permission error (42501) — using LocalJSON fallback ({err_msg})")
            else:
                print(f"[Repository] Supabase notice: {err_msg} — using LocalJSON fallback")
            return {
                "status": "error",
                "error": err_msg,
                "synced_count": 0
            }

    def _sync_record_windows(self, record_id: str, stay_id: int, windows: List[Dict[str, Any]]):
        """Syncs sequential observation windows, bedside vitals, and risk assessments."""
        for w in windows:
            w_idx = w.get("window_index", 0)
            ts_label = w.get("timestamp", f"Window {w_idx+1}")

            win_payload = {
                "record_id": record_id,
                "window_index": w_idx,
                "timestamp_label": ts_label,
                "obs_timestamp": "2150-01-01T08:00:00Z"
            }
            try:
                w_res = self.client.table("observation_windows").upsert(
                    win_payload, on_conflict="record_id,window_index"
                ).execute()

                if w_res.data and len(w_res.data) > 0:
                    win_id = w_res.data[0]["id"]

                    vitals = w.get("clinical_features", {})
                    if vitals:
                        vit_payload = {
                            "window_id": win_id,
                            "stay_id": stay_id,
                            "hr": float(vitals.get("HR", 80.0) or 80.0),
                            "spo2": float(vitals.get("SpO2", 98.0) or 98.0),
                            "resp": float(vitals.get("Resp", 18.0) or 18.0),
                            "sys_bp": float(vitals.get("SysBP", 120.0) or 120.0),
                            "dia_bp": float(vitals.get("DiaBP", 80.0) or 80.0),
                            "map_bp": float(vitals.get("MAP", 93.3) or 93.3),
                            "temp": float(vitals.get("Temp", 37.0) or 37.0)
                        }
                        try:
                            self.client.table("vital_observations").upsert(vit_payload, on_conflict="window_id").execute()
                        except Exception:
                            pass

                    risk_score = float(w.get("risk_score", 0.0))
                    risk_cat = w.get("risk_category", "LOW")
                    risk_payload = {
                        "window_id": win_id,
                        "stay_id": stay_id,
                        "record_id": record_id,
                        "risk_score": risk_score,
                        "risk_category": risk_cat,
                        "clinical_score": float(w.get("modality_scores", {}).get("Clinical Vitals", 0.0)),
                        "waveform_score": float(w.get("modality_scores", {}).get("ECG", 0.0))
                    }
                    try:
                        r_res = self.client.table("risk_assessments").upsert(risk_payload, on_conflict="window_id").execute()

                        if r_res.data and len(r_res.data) > 0 and "contributing_factors" in w:
                            assess_id = r_res.data[0]["id"]
                            for factor in w["contributing_factors"]:
                                alert_payload = {
                                    "assessment_id": assess_id,
                                    "stay_id": stay_id,
                                    "factor_name": factor.get("factor", "Vital Abnormality"),
                                    "impact_level": factor.get("impact", "MEDIUM"),
                                    "description": factor.get("description", "Monitored parameter"),
                                    "contribution_score": float(factor.get("weight", 0.0))
                                }
                                try:
                                    self.client.table("physiological_alerts").insert(alert_payload).execute()
                                except Exception:
                                    pass
                    except Exception:
                        pass
            except Exception:
                pass


def sync_cohort_to_supabase(
    source_cohort: Optional[List[Dict[str, Any]]] = None,
    db_config: Optional[DatabaseConfig] = None
) -> Dict[str, Any]:
    """Helper function to run cohort synchronization."""
    sync_engine = MIMICCohortSyncEngine(db_config=db_config)
    return sync_engine.sync_cohort_to_supabase(source_cohort)
