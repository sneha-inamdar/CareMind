"""
CareMind Multimodal Physiological Risk Engine Prototype.

Implements end-to-end multimodal physiological risk estimation using REAL observed
MIMIC-IV Waveform Database (mimic4wdb/0.1.0) signal streams and MIMIC-IV Clinical Demo vitals.

Architecture:
  1. Clinical Encoder (Vitals / Numerics -> Clinical Risk Representation)
  2. Waveform Encoder (ECG, PPG, ABP -> Waveform Instability Representation)
  3. Feature Fusion (Concatenate modality representations)
  4. Fusion Model -> Composite Prototype Risk Score (0 - 100) -> Category (LOW, MEDIUM, HIGH)
"""

import os
import re
import math
import json
import urllib.request
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple

from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier

from src.mimic.config import MIMICConfig
from src.mimic.waveform_linker import MIMICWaveformLinker
from src.mimic.waveform_processor import MIMICWaveformProcessor
from src.mimic.waveform_features import MIMICWaveformFeatureExtractor


class ModalityEncoder:
    """Modality-specific feature encoder using StandardScaler + Logistic Regression/Tree Model."""

    def __init__(self, modality_name: str):
        self.modality_name = modality_name
        self.scaler = StandardScaler()
        self.model = LogisticRegression(C=1.0, max_iter=200, random_state=42)
        self.feature_names: List[str] = []
        self.is_fitted = False

    def fit(self, X: np.ndarray, y: np.ndarray, feature_names: List[str]):
        """Fit scaler and classifier on training modality data."""
        self.feature_names = feature_names
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled, y)
        self.is_fitted = True

    def predict_risk_score(self, X: np.ndarray, temperature: float = 1.75) -> Tuple[np.ndarray, np.ndarray]:
        """
        Return temperature-calibrated continuous modality risk score (0-100) and scaled feature values.
        Uses logit decision function scaling with temperature dispersion T=1.75 to expand the dynamic range
        and prevent artificial score saturation at 100.0 for severe observations.
        """
        if not self.is_fitted:
            X_scaled = (X - np.mean(X, axis=0, keepdims=True)) / (np.std(X, axis=0, keepdims=True) + 1e-6)
            logits = np.mean(X_scaled, axis=1)
            calibrated_prob = 1.0 / (1.0 + np.exp(-logits / temperature))
            return np.clip(calibrated_prob * 100.0, 0.0, 100.0), X_scaled

        X_scaled = self.scaler.transform(X)
        logits = self.model.decision_function(X_scaled)
        calibrated_prob = 1.0 / (1.0 + np.exp(-logits / temperature))
        scores = np.clip(calibrated_prob * 100.0, 0.0, 100.0)
        return scores, X_scaled


class CareMindMultimodalPrototype:
    """
    CareMind Multimodal Risk Scoring Prototype Engine.
    
    Processes real continuous waveform streams (ECG, PPG, ABP) and real clinical bedside vitals.
    Calculates dynamic modality risk scores, composite fused risk score (0-100),
    risk categories (LOW, MEDIUM, HIGH), and derived physiological factor explanations.
    """

    def __init__(self, config: Optional[MIMICConfig] = None):
        self.config = config or MIMICConfig()
        self.linker = MIMICWaveformLinker(config=self.config)
        self.processor = MIMICWaveformProcessor(target_fs=125.0)
        self.feature_extractor = MIMICWaveformFeatureExtractor()

        self.clinical_encoder = ModalityEncoder("Clinical")
        self.waveform_encoder = ModalityEncoder("Waveform")

        self.fusion_scaler = StandardScaler()
        self.fusion_model = LogisticRegression(C=1.0, max_iter=200, random_state=42)
        self.is_fitted = False

        # Seed initial deterministic prototype weights for demonstration
        self._initialize_prototype_models()

    def _initialize_prototype_models(self):
        """
        Initialize prototype modality and fusion models using standard clinical thresholds
        to ensure deterministic, interpretable execution on real physiological data.
        """
        np.random.seed(42)
        # Synthetic calibration cohort representing standard physiological ranges
        n_samples = 200
        
        # Clinical features: [HR, SpO2, Resp, SysBP, DiaBP, MAP, Temp]
        hr = np.random.normal(80, 20, n_samples)
        spo2 = np.random.normal(97, 4, n_samples)
        resp = np.random.normal(18, 5, n_samples)
        sys_bp = np.random.normal(120, 20, n_samples)
        dia_bp = np.random.normal(75, 12, n_samples)
        map_bp = (sys_bp + 2 * dia_bp) / 3.0
        temp = np.random.normal(37.0, 1.0, n_samples)
        
        X_clin = np.column_stack([hr, spo2, resp, sys_bp, dia_bp, map_bp, temp])
        y_clin = ((hr > 110) | (spo2 < 92) | (map_bp < 65) | (resp > 24)).astype(int)

        clin_names = ["HR", "SpO2", "Resp", "SysBP", "DiaBP", "MAP", "Temp"]
        self.clinical_encoder.fit(X_clin, y_clin, clin_names)

        # Waveform features: [ECG_mean, ECG_std, ECG_rms, ECG_ptp, ECG_zero_crossings,
        #                     PPG_mean, PPG_std, PPG_peak_max, PPG_trough_min, PPG_amplitude_range,
        #                     ABP_mean, ABP_std, ABP_pulse_pressure]
        ecg_std = np.random.normal(0.8, 0.4, n_samples)
        ecg_rms = np.random.normal(0.9, 0.3, n_samples)
        ppg_std = np.random.normal(1.2, 0.5, n_samples)
        ppg_amp = np.random.normal(2.5, 1.0, n_samples)
        abp_std = np.random.normal(15.0, 5.0, n_samples)
        abp_pp = np.random.normal(45.0, 15.0, n_samples)

        X_wave = np.column_stack([
            np.random.normal(0, 0.1, n_samples), ecg_std, ecg_rms, np.random.normal(2.0, 0.5, n_samples), np.random.normal(20, 5, n_samples),
            np.random.normal(50, 10, n_samples), ppg_std, np.random.normal(90, 5, n_samples), np.random.normal(10, 5, n_samples), ppg_amp,
            np.random.normal(90, 15, n_samples), abp_std, abp_pp
        ])
        y_wave = ((ecg_std > 1.2) | (ppg_std < 0.5) | (abp_pp < 25) | (abp_std > 22)).astype(int)

        wave_names = [
            "ECG_mean", "ECG_std", "ECG_rms", "ECG_ptp", "ECG_zero_crossings",
            "PPG_mean", "PPG_std", "PPG_peak_max", "PPG_trough_min", "PPG_amplitude_range",
            "ABP_mean", "ABP_std", "ABP_pulse_pressure"
        ]
        self.waveform_encoder.fit(X_wave, y_wave, wave_names)

        # Stage 2 & 3: Fusion Model
        s_clin, _ = self.clinical_encoder.predict_risk_score(X_clin)
        s_wave, _ = self.waveform_encoder.predict_risk_score(X_wave)
        
        X_fusion = np.column_stack([s_clin, s_wave, (s_clin * s_wave) / 100.0])
        y_fusion = ((s_clin + s_wave) / 2.0 > 45).astype(int)

        X_fusion_scaled = self.fusion_scaler.fit_transform(X_fusion)
        self.fusion_model.fit(X_fusion_scaled, y_fusion)
        self.is_fitted = True

    def calculate_risk_category(self, score: float) -> str:
        """Map numeric score in [0, 100] to LOW, MEDIUM, or HIGH risk category."""
        if score < 50.0:
            return "LOW"
        elif score < 75.0:
            return "MEDIUM"
        else:
            return "HIGH"

    def extract_clinical_feature_vector(self, vitals_dict: Dict[str, float]) -> Tuple[np.ndarray, Dict[str, float]]:
        """
        Construct clean clinical feature vector from observed bedside vitals.
        Uses physiological defaults for unobserved fields to ensure robustness during model inference.
        Missing observations remain None in the output feat_dict.
        """
        defaults = {
            "HR": 75.0,
            "SpO2": 98.0,
            "Resp": 16.0,
            "SysBP": 120.0,
            "DiaBP": 75.0,
            "MAP": 88.0,
            "Temp": 37.0
        }
        
        feat_dict = {}
        vec = []
        for k in ["HR", "SpO2", "Resp", "SysBP", "DiaBP", "MAP", "Temp"]:
            val = vitals_dict.get(k)
            if val is None or (isinstance(val, (int, float)) and (np.isnan(val) or val <= 0)):
                vec_val = defaults[k]
                feat_dict[k] = None
            else:
                vec_val = float(val)
                feat_dict[k] = round(vec_val, 2)
            vec.append(vec_val)
            
        return np.array(vec).reshape(1, -1), feat_dict

    def derive_contributing_factors(
        self,
        clin_vitals: Dict[str, float],
        wave_feats: Dict[str, float],
        clin_score: float,
        wave_score: float,
        risk_trend_delta: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Derive top contributing physiological factors grounded strictly in observed input features.
        Each factor provides structured metadata: factor, modality, severity, evidence, contribution_score.
        """
        factors = []
        
        # Clinical vital deviations
        hr = clin_vitals.get("HR")
        spo2 = clin_vitals.get("SpO2")
        resp = clin_vitals.get("Resp")
        map_bp = clin_vitals.get("MAP")
        temp = clin_vitals.get("Temp")

        if hr is not None:
            if hr > 100.0:
                score = round(float(min(30.0, (hr - 100.0) * 0.8)), 1)
                evid = f"HR of {hr:.1f} bpm exceeds tachycardia threshold (100 bpm)"
                factors.append({
                    "factor": "Elevated Heart Rate",
                    "modality": "Clinical Vitals",
                    "severity": "HIGH",
                    "impact": "HIGH",
                    "evidence": evid,
                    "description": evid,
                    "contribution_score": score
                })
            elif hr < 50.0:
                score = round(float(min(25.0, (50.0 - hr) * 0.9)), 1)
                evid = f"HR of {hr:.1f} bpm below lower threshold (50 bpm)"
                factors.append({
                    "factor": "Bradycardia",
                    "modality": "Clinical Vitals",
                    "severity": "MEDIUM",
                    "impact": "MEDIUM",
                    "evidence": evid,
                    "description": evid,
                    "contribution_score": score
                })

        if spo2 is not None and spo2 < 94.0:
            score = round(float(min(35.0, (95.0 - spo2) * 2.5)), 1)
            evid = f"SpO2 saturation level at {spo2:.1f}% (normal >= 95%)"
            factors.append({
                "factor": "Hypoxia / Reduced SpO2",
                "modality": "Clinical Vitals",
                "severity": "HIGH",
                "impact": "HIGH",
                "evidence": evid,
                "description": evid,
                "contribution_score": score
            })

        if map_bp is not None and map_bp < 65.0:
            score = round(float(min(35.0, (65.0 - map_bp) * 1.5)), 1)
            evid = f"Mean Arterial Pressure at {map_bp:.1f} mmHg (target >= 65 mmHg)"
            factors.append({
                "factor": "Hypotension / Low MAP",
                "modality": "Clinical Vitals",
                "severity": "HIGH",
                "impact": "HIGH",
                "evidence": evid,
                "description": evid,
                "contribution_score": score
            })

        if resp is not None and resp > 22.0:
            score = round(float(min(20.0, (resp - 22.0) * 1.2)), 1)
            evid = f"Respiratory rate of {resp:.1f} breaths/min elevated"
            factors.append({
                "factor": "Tachypnea",
                "modality": "Clinical Vitals",
                "severity": "MEDIUM",
                "impact": "MEDIUM",
                "evidence": evid,
                "description": evid,
                "contribution_score": score
            })

        # Waveform stream deviations (only if modality signal is present)
        ecg_missing = wave_feats.get("ECG_is_missing", 1.0)
        abp_missing = wave_feats.get("ABP_is_missing", 1.0)
        ppg_missing = wave_feats.get("PPG_is_missing", 1.0)

        if ecg_missing == 0.0:
            ecg_std = wave_feats.get("ECG_std", 0.0)
            if ecg_std > 1.2:
                score = round(float(min(20.0, ecg_std * 10.0)), 1)
                evid = f"ECG waveform standard deviation elevated ({ecg_std:.2f})"
                factors.append({
                    "factor": "High ECG Waveform Variability",
                    "modality": "ECG",
                    "severity": "MEDIUM",
                    "impact": "MEDIUM",
                    "evidence": evid,
                    "description": evid,
                    "contribution_score": score
                })

        if abp_missing == 0.0:
            abp_std = wave_feats.get("ABP_std", 0.0)
            if abp_std > 18.0:
                score = round(float(min(25.0, abp_std * 0.8)), 1)
                evid = f"ABP waveform variability high (std={abp_std:.1f} mmHg)"
                factors.append({
                    "factor": "Arterial Pressure Instability",
                    "modality": "ABP",
                    "severity": "HIGH",
                    "impact": "HIGH",
                    "evidence": evid,
                    "description": evid,
                    "contribution_score": score
                })

        if ppg_missing == 0.0:
            ppg_amp = wave_feats.get("PPG_amplitude_range", 0.0)
            if ppg_amp > 0 and ppg_amp < 0.2:
                score = round(float(min(20.0, (0.2 - ppg_amp) * 100.0)), 1)
                evid = f"PPG pulse wave attenuation (amplitude range={ppg_amp:.3f})"
                factors.append({
                    "factor": "Attenuated Peripheral Pulse Wave",
                    "modality": "PPG",
                    "severity": "MEDIUM",
                    "impact": "MEDIUM",
                    "evidence": evid,
                    "description": evid,
                    "contribution_score": score
                })

        # Temporal trend factor
        if risk_trend_delta is not None and risk_trend_delta >= 5.0:
            score = round(float(min(30.0, risk_trend_delta * 1.5)), 1)
            evid = f"CareMind risk score escalated by +{risk_trend_delta:.1f} points in recent observation window"
            factors.append({
                "factor": "Rapid Risk Escalation",
                "modality": "Temporal Trend",
                "severity": "HIGH",
                "impact": "HIGH",
                "evidence": evid,
                "description": evid,
                "contribution_score": score
            })

        if not factors:
            evid = "Vitals and continuous waveform dynamics are within expected ranges"
            factors.append({
                "factor": "Normal Physiological Parameters",
                "modality": "General Physiology",
                "severity": "LOW",
                "impact": "LOW",
                "evidence": evid,
                "description": evid,
                "contribution_score": 0.0
            })

        # Sort factors by contribution score
        factors.sort(key=lambda x: x["contribution_score"], reverse=True)
        return factors

    def analyze_multimodal_window(
        self,
        record_id: str,
        subject_id: int,
        window_index: int,
        vitals_dict: Dict[str, float],
        ecg_signal: Optional[np.ndarray] = None,
        ppg_signal: Optional[np.ndarray] = None,
        abp_signal: Optional[np.ndarray] = None,
        timestamp_str: str = "2148-08-16 09:00:00",
        previous_risk_score: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Execute end-to-end multimodal risk score pipeline for a specific window.
        Uses adaptive modality fusion and temporal trend evaluation.
        
        Returns full schema-compliant JSON dictionary.
        """
        # 1. Extract Clinical Features & Score
        X_clin, clin_vitals = self.extract_clinical_feature_vector(vitals_dict)
        clin_score_arr, _ = self.clinical_encoder.predict_risk_score(X_clin)
        clinical_score = float(clin_score_arr[0])

        # 2. Extract Waveform Features & Score
        ecg_arr = ecg_signal if ecg_signal is not None else np.array([])
        ppg_arr = ppg_signal if ppg_signal is not None else np.array([])
        abp_arr = abp_signal if abp_signal is not None else np.array([])

        wave_feats = self.feature_extractor.extract_stay_waveform_features(
            ecg_sig=ecg_arr,
            abp_sig=abp_arr,
            ppg_sig=ppg_arr
        )

        wave_vec = np.array([
            wave_feats.get("ECG_mean", 0.0), wave_feats.get("ECG_std", 0.0), wave_feats.get("ECG_rms", 0.0),
            wave_feats.get("ECG_ptp", 0.0), wave_feats.get("ECG_zero_crossings", 0.0),
            wave_feats.get("PPG_mean", 0.0), wave_feats.get("PPG_std", 0.0), wave_feats.get("PPG_peak_max", 0.0),
            wave_feats.get("PPG_trough_min", 0.0), wave_feats.get("PPG_amplitude_range", 0.0),
            wave_feats.get("ABP_mean", 0.0), wave_feats.get("ABP_std", 0.0), wave_feats.get("ABP_pulse_pressure", 0.0)
        ]).reshape(1, -1)

        wave_score_arr, _ = self.waveform_encoder.predict_risk_score(wave_vec)
        waveform_score = float(wave_score_arr[0])

        # Available modalities check
        available_modalities = []
        if len(ecg_arr) > 0: available_modalities.append("ECG")
        if len(ppg_arr) > 0: available_modalities.append("PPG")
        if len(abp_arr) > 0: available_modalities.append("ABP")
        has_clinical = any(v is not None for v in clin_vitals.values())
        if has_clinical: available_modalities.append("Clinical Vitals")

        # 3. Adaptive Modality Fusion Strategy
        # If clinical vitals are completely missing, base risk strictly on continuous waveform features.
        # Otherwise, fuse clinical and waveform scores with adaptive weights.
        if not has_clinical and len(available_modalities) > 0:
            raw_fused_score = waveform_score
        elif has_clinical and len(available_modalities) == 1:
            raw_fused_score = clinical_score
        else:
            X_fusion = np.column_stack([clinical_score, waveform_score, (clinical_score * waveform_score) / 100.0])
            X_fusion_scaled = self.fusion_scaler.transform(X_fusion)
            fusion_logits = self.fusion_model.decision_function(X_fusion_scaled)
            fusion_prob = float(1.0 / (1.0 + np.exp(-fusion_logits[0] / 1.75)))
            raw_fused_score = 0.5 * clinical_score + 0.5 * waveform_score + (fusion_prob - 0.5) * 10.0

        risk_score = float(np.clip(raw_fused_score, 0.0, 100.0))
        risk_category = self.calculate_risk_category(risk_score)

        # 4. Temporal Trend & Prioritization Logic
        risk_trend_delta = 0.0
        risk_trend_status = "STABLE"
        if previous_risk_score is not None:
            risk_trend_delta = round(float(risk_score - previous_risk_score), 1)
            if risk_trend_delta >= 5.0:
                risk_trend_status = "ESCALATING"
            elif risk_trend_delta <= -5.0:
                risk_trend_status = "IMPROVING"

        priority_status = "ROUTINE_MONITORING"
        if risk_score >= 75.0 or (risk_score >= 60.0 and risk_trend_status == "ESCALATING"):
            priority_status = "CRITICAL_PRIORITY"
        elif risk_score >= 50.0 or (risk_score >= 40.0 and risk_trend_status == "ESCALATING"):
            priority_status = "HIGH_PRIORITY"

        # 5. Derive Explainability Factors (with temporal trend context)
        factors = self.derive_contributing_factors(
            clin_vitals, wave_feats, clinical_score, waveform_score, risk_trend_delta=risk_trend_delta
        )

        # Format waveform samples for UI visualization (downsample if needed)
        def sample_signal_for_ui(arr: np.ndarray, max_len: int = 500) -> List[float]:
            if len(arr) == 0:
                return []
            if len(arr) <= max_len:
                return [round(float(x), 4) for x in arr]
            idx = np.linspace(0, len(arr) - 1, max_len, dtype=int)
            return [round(float(arr[i]), 4) for i in idx]

        return {
            "record_id": record_id,
            "subject_id": subject_id,
            "window_index": window_index,
            "timestamp": timestamp_str,
            "clinical_features": clin_vitals,
            "waveform_features": wave_feats,
            "clinical_score": round(clinical_score, 1),
            "waveform_score": round(waveform_score, 1),
            "fusion_score": round(risk_score, 1),
            "risk_score": round(risk_score, 1),
            "risk_category": risk_category,
            "risk_trend_delta": risk_trend_delta,
            "risk_trend_status": risk_trend_status,
            "priority_status": priority_status,
            "available_modalities": available_modalities,
            "contributing_factors": factors,
            "waveform_samples": {
                "ecg": sample_signal_for_ui(ecg_arr),
                "ppg": sample_signal_for_ui(ppg_arr),
                "abp": sample_signal_for_ui(abp_arr)
            },
            "disclaimer": "CareMind Physiological Risk Score (0-100) is an engineering prototype decision-support metric for physiological instability, not a diagnostic or mortality prediction model."
        }
