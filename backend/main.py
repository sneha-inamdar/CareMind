"""
CareMind Multimodal Physiological Risk Engine - FastAPI Backend.

Provides REST and Web API endpoints for multimodal ICU physiological risk scoring,
multi-patient ICU prioritization, timeline replay, and database persistence integration.
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
from src.mimic.simulation import CareMindSimulationEngine
from src.db.repository import get_repository

app = FastAPI(
    title="CareMind Multimodal Risk Engine API",
    description="API for real continuous waveform and bedside vital multimodal risk scoring and ICU patient prioritization.",
    version="1.0.0"
)

# Enable CORS for frontend web and mobile client integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1|10\.0\.2\.2|192\.168\.\d+\.\d+)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core prototype engine instance
prototype_engine = CareMindMultimodalPrototype()
simulation_engine = CareMindSimulationEngine()

# Database Repository Abstraction (Supabase if configured, or Local JSON fallback)
db_repository = get_repository()

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
    records = db_repository.get_available_records()
    return {"status": "success", "count": len(records), "records": records}


@app.post("/api/multimodal/sync_cohort")
def sync_cohort():
    """
    POST /api/multimodal/sync_cohort
    
    Synchronizes CareMind operational metadata cohort with Supabase database.
    """
    from src.db.cohort_sync import sync_cohort_to_supabase
    res = sync_cohort_to_supabase()
    return res



@app.get("/api/multimodal/patients")
def get_icu_patients_overview(window_index: int = Query(0, ge=0, le=3)):
    """
    GET /api/multimodal/patients?window_index=0
    
    Returns all monitored ICU patients at the specified observation window,
    AUTOMATICALLY SORTED BY HIGHEST CAREMIND RISK SCORE FIRST.
    """
    if simulation_engine.is_running and window_index == simulation_engine.current_step:
        state = simulation_engine.get_simulation_state()
        return {
            "status": "success",
            "window_index": simulation_engine.current_step,
            "patient_count": state["patient_count"],
            "patients": state["patients"]
        }

    patients = db_repository.get_patients_overview(window_index=window_index)
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
    detail = db_repository.get_record_detail(record_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Record '{record_id}' not found.")
    return detail


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
                timestamp_str=res.get("timestamp", "Window 1 • T+00:00")
            )

        if "available_modalities" in cached:
            res["record_available_modalities"] = cached["available_modalities"]

        return res

    raise HTTPException(status_code=404, detail=f"No data available for record '{req.record_id}'.")


@app.get("/api/multimodal/replay/{record_id}")
def replay_record(record_id: str):
    """
    GET /api/multimodal/replay/{record_id}
    
    Returns full array of sequential window analysis objects across the time timeline.
    """
    timeline = db_repository.get_replay_timeline(record_id)
    if not timeline:
        raise HTTPException(status_code=404, detail=f"No replay timeline found for record '{record_id}'.")

    return {
        "status": "success",
        "record_id": record_id,
        "total_windows": len(timeline),
        "timeline": timeline
    }


# Alert & Real-Time Simulation API Endpoints
@app.get("/api/alerts")
def get_active_alerts():
    """GET /api/alerts - Returns all currently active alerts across ICU patients."""
    alerts = simulation_engine.alert_engine.get_all_active_alerts()
    return {"status": "success", "count": len(alerts), "alerts": alerts}


@app.get("/api/alerts/{patient_id}")
def get_patient_alerts(patient_id: str):
    """GET /api/alerts/{patient_id} - Returns active alerts for a specific patient/record."""
    alerts = simulation_engine.alert_engine.get_patient_active_alerts(patient_id)
    return {"status": "success", "record_id": patient_id, "count": len(alerts), "alerts": alerts}


@app.get("/api/simulation/state")
def get_simulation_state():
    """GET /api/simulation/state - Returns current state of multi-patient simulation."""
    return simulation_engine.get_simulation_state()


@app.post("/api/simulation/start")
def start_simulation():
    """POST /api/simulation/start - Starts/resets multi-patient simulation."""
    return simulation_engine.start()


@app.post("/api/simulation/step")
def step_simulation():
    """POST /api/simulation/step - Advances simulation across all ICU patients by 1 step."""
    return simulation_engine.step()


@app.get("/api/research/metrics")
def get_research_metrics():
    """
    GET /api/research/metrics
    
    Returns empirical research evaluation metrics (unimodal vs. multimodal, 1D CNN vs SVM baselines,
    modality availability breakdown, and scientific limitations disclaimer).
    """
    metrics_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "experiments", "mimic_multimodal", "metrics_summary.json")
    if os.path.exists(metrics_path):
        with open(metrics_path, "r") as f:
            return json.load(f)
            
    # Fallback to evaluator if file not generated yet
    from src.mimic.evaluator import CareMindEvaluator
    evaluator = CareMindEvaluator(random_state=42)
    return evaluator.generate_research_audit_summary()


# Mount frontend static dashboard if available
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

