"""
CareMind Multimodal Physiological Risk Engine - FastAPI Backend.

Provides REST and Web API endpoints for multimodal ICU physiological risk scoring,
multi-patient ICU prioritization, timeline replay, and clinician dashboard integration.
"""

import os
import json
import numpy as np
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel

from src.mimic.multimodal_prototype import CareMindMultimodalPrototype

app = FastAPI(
    title="CareMind Multimodal Risk Engine API",
    description="API for real continuous waveform and bedside vital multimodal risk scoring and ICU patient prioritization.",
    version="1.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core prototype engine instance
prototype_engine = CareMindMultimodalPrototype()

# Cache directory for real waveform demo records
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "demo_waveforms")


class AnalyzeRequest(BaseModel):
    record_id: str
    window_index: Optional[int] = 0
    vitals_override: Optional[Dict[str, float]] = None


def load_cached_record(record_id: str) -> Dict[str, Any]:
    """Helper to load pre-analyzed real record data from local cache if present."""
    cache_path = os.path.join(DATA_DIR, f"{record_id}.json")
    if os.path.exists(cache_path):
        with open(cache_path, "r") as f:
            return json.load(f)
    return {}


@app.get("/api/health")
def health_check():
    return {
        "status": "online",
        "system": "CareMind Multimodal Physiological Risk Engine",
        "version": "1.0.0"
    }


@app.get("/api/multimodal/records")
def get_available_records():
    """
    GET /api/multimodal/records
    
    Returns list of REAL available demo waveform records with subject IDs and modalities.
    """
    records = [
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
    return {"status": "success", "count": len(records), "records": records}


@app.get("/api/multimodal/patients")
def get_icu_patients_overview(window_index: int = Query(0, ge=0, le=3)):
    """
    GET /api/multimodal/patients?window_index=0
    
    Returns all monitored ICU patients at the specified observation window,
    AUTOMATICALLY SORTED BY HIGHEST CAREMIND RISK SCORE FIRST.
    """
    records_meta = [
        {"record_id": "81739927", "subject_id": 10014354, "stay_id": 39880770, "bed_id": "Bed ICU-01"},
        {"record_id": "83404654", "subject_id": 10020306, "stay_id": 38418938, "bed_id": "Bed ICU-02"},
        {"record_id": "82924339", "subject_id": 10126957, "stay_id": 39149479, "bed_id": "Bed ICU-03"}
    ]

    patients = []
    for meta in records_meta:
        cached = load_cached_record(meta["record_id"])
        if cached and "windows" in cached and len(cached["windows"]) > 0:
            w_idx = min(window_index, len(cached["windows"]) - 1)
            w_data = cached["windows"][w_idx]
            
            # Primary clinical alert derived from top contributing factor
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
                "vitals": w_data.get("clinical_features", {}),
                "primary_alert": primary_alert,
                "available_modalities": w_data.get("available_modalities", []),
                "contributing_factors": factors
            })

    # SORT PATIENTS BY HIGHEST RISK SCORE FIRST
    patients.sort(key=lambda p: p["risk_score"], reverse=True)

    return {
        "status": "success",
        "window_index": window_index,
        "patient_count": len(patients),
        "patients": patients
    }


@app.get("/api/multimodal/records/{record_id}")
def get_record_detail(record_id: str):
    """
    GET /api/multimodal/records/{record_id}
    
    Returns details for a specific record including available channels and vitals.
    """
    cached = load_cached_record(record_id)
    if not cached:
        records_map = {
            "81739927": {"subject_id": 10014354, "tier": "Tier 2 (ECG+PPG)"},
            "83404654": {"subject_id": 10020306, "tier": "Tier 2 (ECG+PPG)"},
            "82924339": {"subject_id": 10126957, "tier": "Tier 1 (ECG+ABP+PPG)"}
        }
        if record_id not in records_map:
            raise HTTPException(status_code=404, detail=f"Record '{record_id}' not found.")
        meta = records_map[record_id]
        return {
            "record_id": record_id,
            "subject_id": meta["subject_id"],
            "tier": meta["tier"],
            "windows_count": 4,
            "cached": False
        }

    return {
        "record_id": record_id,
        "subject_id": cached.get("subject_id"),
        "windows_count": len(cached.get("windows", [])),
        "cached": True,
        "first_window": cached["windows"][0] if cached.get("windows") else None
    }


@app.post("/api/multimodal/analyze")
def analyze_window(req: AnalyzeRequest):
    """
    POST /api/multimodal/analyze
    
    Analyzes a specific observation window for a patient record and calculates dynamic
    multimodal risk score (0-100), risk category, modality scores, and contributing factors.
    """
    cached = load_cached_record(req.record_id)
    if cached and "windows" in cached and len(cached["windows"]) > 0:
        win_idx = min(req.window_index or 0, len(cached["windows"]) - 1)
        res = cached["windows"][win_idx].copy()
        
        # Apply vitals override if provided
        if req.vitals_override:
            rec_id = req.record_id
            subj_id = cached.get("subject_id", 10014354)
            ecg_samples = np.array(res.get("waveform_samples", {}).get("ecg", []))
            ppg_samples = np.array(res.get("waveform_samples", {}).get("ppg", []))
            abp_samples = np.array(res.get("waveform_samples", {}).get("abp", []))
            
            res = prototype_engine.analyze_multimodal_window(
                record_id=rec_id,
                subject_id=subj_id,
                window_index=win_idx,
                vitals_dict=req.vitals_override,
                ecg_signal=ecg_samples,
                ppg_signal=ppg_samples,
                abp_signal=abp_samples,
                timestamp_str=res.get("timestamp", "2148-08-16 09:00:00")
            )

        return res

    raise HTTPException(status_code=404, detail=f"No data available for record '{req.record_id}'.")


@app.get("/api/multimodal/replay/{record_id}")
def replay_record(record_id: str):
    """
    GET /api/multimodal/replay/{record_id}
    
    Returns full array of sequential window analysis objects across the time timeline.
    """
    cached = load_cached_record(record_id)
    if not cached or "windows" not in cached:
        raise HTTPException(status_code=404, detail=f"No replay timeline found for record '{record_id}'.")

    return {
        "status": "success",
        "record_id": record_id,
        "subject_id": cached.get("subject_id"),
        "total_windows": len(cached["windows"]),
        "timeline": cached["windows"]
    }


# Mount frontend static dashboard if available
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
