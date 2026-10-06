"""
CareMind Clinical Decision-Support Alert Engine & Deduplication System.

Generates evidence-grounded alerts (HIGH_RISK, RISK_ESCALATING, PHYSIOLOGICAL_ABNORMALITY,
MODALITY_SIGNAL_CHANGE), manages per-patient alert state, and prevents notification fatigue via state-based deduplication.
"""

import uuid
from typing import Dict, List, Any, Optional


class AlertEngine:
    """Alert generation and state-based deduplication system for CareMind ICU monitoring."""

    def __init__(self):
        # Keyed by f"{record_id}:{alert_type}"
        self.active_alerts: Dict[str, Dict[str, Any]] = {}
        # Historical log of generated alerts
        self.alert_history: List[Dict[str, Any]] = []

    def evaluate_patient_alerts(self, patient_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Evaluate current window analysis for a patient and generate/deduplicate alerts.
        
        Returns list of newly generated or active alerts for this evaluation window.
        """
        record_id = str(patient_analysis.get("record_id", "unknown"))
        subject_id = patient_analysis.get("subject_id")
        stay_id = patient_analysis.get("stay_id", 0)
        bed_id = patient_analysis.get("bed_id", "Bed ICU")
        win_idx = patient_analysis.get("window_index", 0)
        ts = patient_analysis.get("timestamp", "")
        risk_score = float(patient_analysis.get("risk_score", 0.0))
        risk_cat = patient_analysis.get("risk_category", "LOW")
        risk_trend = patient_analysis.get("risk_trend_status", "STABLE")
        risk_delta = float(patient_analysis.get("risk_trend_delta", 0.0))
        factors = patient_analysis.get("contributing_factors", [])
        modalities = patient_analysis.get("available_modalities", [])

        current_window_alerts: List[Dict[str, Any]] = []

        # 1. HIGH_RISK Alert
        high_risk_key = f"{record_id}:HIGH_RISK"
        if risk_cat == "HIGH" or risk_score >= 75.0:
            if high_risk_key not in self.active_alerts:
                alert = {
                    "alert_id": f"ALT-{record_id}-W{win_idx}-HIGH",
                    "record_id": record_id,
                    "subject_id": subject_id,
                    "stay_id": stay_id,
                    "bed_id": bed_id,
                    "window_index": win_idx,
                    "timestamp": ts,
                    "severity": "HIGH",
                    "alert_type": "HIGH_RISK",
                    "title": "High Physiological Risk",
                    "message": f"Patient #{subject_id} CareMind risk score elevated to {risk_score:.1f} ({risk_cat})",
                    "supporting_factors": [f for f in factors if f.get("severity") in ["HIGH", "MEDIUM"]],
                    "current_risk_score": risk_score,
                    "risk_trend": risk_trend,
                    "acknowledged": False
                }
                self.active_alerts[high_risk_key] = alert
                self.alert_history.append(alert)
                current_window_alerts.append(alert)
            else:
                # Update timestamp on existing active alert without creating duplicate
                self.active_alerts[high_risk_key]["current_risk_score"] = risk_score
                self.active_alerts[high_risk_key]["timestamp"] = ts
                current_window_alerts.append(self.active_alerts[high_risk_key])
        else:
            # Clear active high risk alert if patient risk has returned to lower levels
            self.active_alerts.pop(high_risk_key, None)

        # 2. RISK_ESCALATING Alert
        escalating_key = f"{record_id}:RISK_ESCALATING"
        if risk_trend == "ESCALATING" and risk_delta >= 5.0:
            if escalating_key not in self.active_alerts:
                alert = {
                    "alert_id": f"ALT-{record_id}-W{win_idx}-ESC",
                    "record_id": record_id,
                    "subject_id": subject_id,
                    "stay_id": stay_id,
                    "bed_id": bed_id,
                    "window_index": win_idx,
                    "timestamp": ts,
                    "severity": "HIGH" if risk_score >= 50.0 else "MEDIUM",
                    "alert_type": "RISK_ESCALATING",
                    "title": "Rapid Risk Escalation",
                    "message": f"Patient #{subject_id} risk score escalated by +{risk_delta:.1f} points (current score: {risk_score:.1f})",
                    "supporting_factors": [f for f in factors if f.get("modality") == "Temporal Trend" or f.get("severity") == "HIGH"],
                    "current_risk_score": risk_score,
                    "risk_trend": risk_trend,
                    "acknowledged": False
                }
                self.active_alerts[escalating_key] = alert
                self.alert_history.append(alert)
                current_window_alerts.append(alert)
            else:
                self.active_alerts[escalating_key]["current_risk_score"] = risk_score
                self.active_alerts[escalating_key]["timestamp"] = ts
                current_window_alerts.append(self.active_alerts[escalating_key])
        else:
            self.active_alerts.pop(escalating_key, None)

        # 3. PHYSIOLOGICAL_ABNORMALITY Alert
        abnorm_key = f"{record_id}:PHYSIOLOGICAL_ABNORMALITY"
        high_factors = [f for f in factors if f.get("severity") == "HIGH" and f.get("factor") != "Normal Physiological Parameters"]
        if high_factors:
            primary_fac = high_factors[0]
            if abnorm_key not in self.active_alerts:
                alert = {
                    "alert_id": f"ALT-{record_id}-W{win_idx}-ABN",
                    "record_id": record_id,
                    "subject_id": subject_id,
                    "stay_id": stay_id,
                    "bed_id": bed_id,
                    "window_index": win_idx,
                    "timestamp": ts,
                    "severity": "HIGH",
                    "alert_type": "PHYSIOLOGICAL_ABNORMALITY",
                    "title": f"Abnormality Detected: {primary_fac.get('factor')}",
                    "message": f"{primary_fac.get('evidence')} ({primary_fac.get('modality')})",
                    "supporting_factors": high_factors,
                    "current_risk_score": risk_score,
                    "risk_trend": risk_trend,
                    "acknowledged": False
                }
                self.active_alerts[abnorm_key] = alert
                self.alert_history.append(alert)
                current_window_alerts.append(alert)
            else:
                self.active_alerts[abnorm_key]["current_risk_score"] = risk_score
                self.active_alerts[abnorm_key]["timestamp"] = ts
                current_window_alerts.append(self.active_alerts[abnorm_key])
        else:
            self.active_alerts.pop(abnorm_key, None)

        # 4. MODALITY_SIGNAL_CHANGE Alert (e.g. waveform modality missing / disconnected)
        signal_key = f"{record_id}:MODALITY_SIGNAL_CHANGE"
        if "Clinical Vitals" not in modalities and len(modalities) > 0:
            if signal_key not in self.active_alerts:
                alert = {
                    "alert_id": f"ALT-{record_id}-W{win_idx}-SIG",
                    "record_id": record_id,
                    "subject_id": subject_id,
                    "stay_id": stay_id,
                    "bed_id": bed_id,
                    "window_index": win_idx,
                    "timestamp": ts,
                    "severity": "INFO",
                    "alert_type": "MODALITY_SIGNAL_CHANGE",
                    "title": "Clinical Modality Unobserved",
                    "message": f"Patient #{subject_id} operating on continuous waveform channels only ({', '.join(modalities)})",
                    "supporting_factors": [],
                    "current_risk_score": risk_score,
                    "risk_trend": risk_trend,
                    "acknowledged": False
                }
                self.active_alerts[signal_key] = alert
                self.alert_history.append(alert)
                current_window_alerts.append(alert)
            else:
                current_window_alerts.append(self.active_alerts[signal_key])
        else:
            self.active_alerts.pop(signal_key, None)

        return current_window_alerts

    def get_all_active_alerts(self) -> List[Dict[str, Any]]:
        """Return list of all currently active alerts across ICU patients."""
        return list(self.active_alerts.values())

    def get_patient_active_alerts(self, record_id: str) -> List[Dict[str, Any]]:
        """Return active alerts for a specific patient record."""
        return [a for k, a in self.active_alerts.items() if a.get("record_id") == str(record_id)]
