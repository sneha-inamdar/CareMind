"""
CareMind Multi-Patient Real-Time Simulation Engine.

Manages independent patient simulation states across continuous observation windows,
advances time steps, updates risk & temporal trends, generates deduplicated alerts,
and dynamically re-ranks ICU patients by physiological priority.
"""

import os
import json
from typing import Dict, List, Any, Optional

from src.mimic.multimodal_prototype import CareMindMultimodalPrototype
from src.mimic.alerts import AlertEngine
from src.db.repository import get_repository


class CareMindSimulationEngine:
    """Decoupled real-time multi-patient ICU simulation state manager."""

    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = data_dir or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "demo_waveforms")
        self.repository = get_repository()
        self.prototype = CareMindMultimodalPrototype()
        self.alert_engine = AlertEngine()

        self.is_running = False
        self.current_step = 0
        self.total_steps = 4

        # Per-patient state: keyed by record_id
        self.patient_states: Dict[str, Dict[str, Any]] = {}
        self._initialize_simulation()

    def _initialize_simulation(self):
        """Initialize simulation state from repository records and cached window files."""
        self.patient_states = {}
        self.alert_engine = AlertEngine()
        self.current_step = 0
        records_meta = self.repository.get_available_records()

        for meta in records_meta:
            rec_id = meta["record_id"]
            cache_path = os.path.join(self.data_dir, f"{rec_id}.json")
            cached_windows = []
            if os.path.exists(cache_path):
                try:
                    with open(cache_path, "r") as f:
                        cached_data = json.load(f)
                        cached_windows = cached_data.get("windows", [])
                except Exception as e:
                    print(f"[SimulationEngine] Warning reading {cache_path}: {e}")

            w0 = cached_windows[0] if cached_windows else {}
            w0_risk = float(w0.get("risk_score", 0.0))
            w0_prio = w0.get("priority_status")
            if not w0_prio:
                if w0_risk >= 75.0:
                    w0_prio = "CRITICAL_PRIORITY"
                elif w0_risk >= 50.0:
                    w0_prio = "HIGH_PRIORITY"
                else:
                    w0_prio = "ROUTINE_MONITORING"

            patient_state = {
                "record_id": rec_id,
                "subject_id": meta.get("subject_id"),
                "stay_id": meta.get("stay_id"),
                "bed_id": meta.get("bed_id", "Bed ICU"),
                "window_index": 0,
                "total_windows": len(cached_windows),
                "timestamp": w0.get("timestamp", "2148-08-16 09:00:17"),
                "risk_score": w0_risk,
                "risk_category": w0.get("risk_category", "LOW"),
                "risk_trend_delta": 0.0,
                "risk_trend_status": "STABLE",
                "priority_status": w0_prio,
                "clinical_features": w0.get("clinical_features", {}),
                "waveform_features": w0.get("waveform_features", {}),
                "available_modalities": w0.get("available_modalities", []),
                "contributing_factors": w0.get("contributing_factors", []),
                "cached_windows": cached_windows,
                "active_alerts": [],
                "disclaimer": w0.get("disclaimer", "CareMind Physiological Risk Score is an engineering prototype decision-support metric.")
            }

            # Evaluate initial alerts
            alerts = self.alert_engine.evaluate_patient_alerts(patient_state)
            patient_state["active_alerts"] = alerts
            self.patient_states[rec_id] = patient_state

    def reset(self):
        """Reset simulation to initial step (Window 0)."""
        self.is_running = False
        self._initialize_simulation()
        return self.get_simulation_state()

    def start(self):
        """Start or resume simulation execution."""
        self.is_running = True
        return self.get_simulation_state()

    def step(self) -> Dict[str, Any]:
        """
        Advance simulation across all patients by 1 step.
        Updates timestamps, temporal trends, priority ranks, and deduplicated alerts.
        """
        if self.current_step < self.total_steps - 1:
            self.current_step += 1
        else:
            self.current_step = 0

        for rec_id, p_state in self.patient_states.items():
            cached_windows = p_state.get("cached_windows", [])
            if not cached_windows:
                continue

            # Target window index for this simulation step
            w_idx = min(self.current_step, len(cached_windows) - 1)
            target_window = cached_windows[w_idx]

            # Preserve previous risk score for temporal trend calculation
            prev_risk = p_state["risk_score"]
            curr_risk = float(target_window.get("risk_score", 0.0))

            # Update patient state
            p_state["window_index"] = w_idx
            p_state["timestamp"] = target_window.get("timestamp")
            p_state["risk_score"] = curr_risk
            p_state["risk_category"] = target_window.get("risk_category", "LOW")
            p_state["clinical_features"] = target_window.get("clinical_features", {})
            p_state["waveform_features"] = target_window.get("waveform_features", {})
            p_state["available_modalities"] = target_window.get("available_modalities", [])

            # Temporal trend calculation
            delta = round(curr_risk - prev_risk, 1)
            p_state["risk_trend_delta"] = delta
            if delta >= 5.0:
                p_state["risk_trend_status"] = "ESCALATING"
            elif delta <= -5.0:
                p_state["risk_trend_status"] = "IMPROVING"
            else:
                p_state["risk_trend_status"] = "STABLE"

            # Priority status calculation
            if curr_risk >= 75.0 or (curr_risk >= 60.0 and p_state["risk_trend_status"] == "ESCALATING"):
                p_state["priority_status"] = "CRITICAL_PRIORITY"
            elif curr_risk >= 50.0 or (curr_risk >= 40.0 and p_state["risk_trend_status"] == "ESCALATING"):
                p_state["priority_status"] = "HIGH_PRIORITY"
            else:
                p_state["priority_status"] = "ROUTINE_MONITORING"

            # Re-derive contributing factors with temporal context
            p_state["contributing_factors"] = self.prototype.derive_contributing_factors(
                p_state["clinical_features"],
                p_state["waveform_features"],
                target_window.get("clinical_score", 0.0),
                target_window.get("waveform_score", 0.0),
                risk_trend_delta=delta
            )

            # Evaluate alerts via AlertEngine
            alerts = self.alert_engine.evaluate_patient_alerts(p_state)
            p_state["active_alerts"] = alerts

        return self.get_simulation_state()

    def get_simulation_state(self) -> Dict[str, Any]:
        """
        Return current snapshot of simulation state with patients sorted by highest CareMind risk score first.
        """
        patient_list = []
        for rec_id, p in self.patient_states.items():
            patient_list.append({
                "record_id": p["record_id"],
                "subject_id": p["subject_id"],
                "stay_id": p["stay_id"],
                "bed_id": p["bed_id"],
                "window_index": p["window_index"],
                "timestamp": p["timestamp"],
                "risk_score": p["risk_score"],
                "risk_category": p["risk_category"],
                "risk_trend_delta": p["risk_trend_delta"],
                "risk_trend_status": p["risk_trend_status"],
                "priority_status": p["priority_status"],
                "vitals": p["clinical_features"],
                "available_modalities": p["available_modalities"],
                "primary_alert": p["contributing_factors"][0]["factor"] if p["contributing_factors"] else "Normal Parameters",
                "contributing_factors": p["contributing_factors"],
                "active_alerts_count": len(p["active_alerts"]),
                "disclaimer": p["disclaimer"]
            })

        # Rank patients descending by CareMind risk score
        patient_list.sort(key=lambda x: x["risk_score"], reverse=True)

        return {
            "status": "success",
            "is_running": self.is_running,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "patient_count": len(patient_list),
            "patients": patient_list,
            "active_alerts": self.alert_engine.get_all_active_alerts()
        }

    def get_patient_detail(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Return detail and timeline history for a specific patient record."""
        p_state = self.patient_states.get(str(record_id))
        if not p_state:
            return None
        return {
            "record_id": p_state["record_id"],
            "subject_id": p_state["subject_id"],
            "stay_id": p_state["stay_id"],
            "bed_id": p_state["bed_id"],
            "current_window": p_state["window_index"],
            "current_risk_score": p_state["risk_score"],
            "risk_category": p_state["risk_category"],
            "risk_trend_status": p_state["risk_trend_status"],
            "priority_status": p_state["priority_status"],
            "active_alerts": p_state["active_alerts"],
            "timeline": p_state["cached_windows"]
        }
