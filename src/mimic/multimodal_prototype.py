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

        # Modality-specific signal encoders
        self.ecg_encoder = ModalityEncoder("ECG")
        self.ppg_encoder = ModalityEncoder("PPG")
        self.abp_encoder = ModalityEncoder("ABP")

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

        # Modality-specific baseline encoders for individual signal inference
        # 1. ECG Sub-Encoder: [ECG_mean, ECG_std, ECG_rms, ECG_ptp, ECG_zero_crossings]
        ecg_names = wave_names[0:5]
        X_ecg = X_wave[:, 0:5]
        y_ecg = (ecg_std > 1.2).astype(int)
        self.ecg_encoder.fit(X_ecg, y_ecg, ecg_names)

        # 2. PPG Sub-Encoder: [PPG_mean, PPG_std, PPG_peak_max, PPG_trough_min, PPG_amplitude_range]
        ppg_names = wave_names[5:10]
        X_ppg = X_wave[:, 5:10]
        y_ppg = ((ppg_std < 0.5) | (ppg_amp < 1.0)).astype(int)
        self.ppg_encoder.fit(X_ppg, y_ppg, ppg_names)

        # 3. ABP Sub-Encoder: [ABP_mean, ABP_std, ABP_pulse_pressure]
        abp_names = wave_names[10:13]
        X_abp = X_wave[:, 10:13]
        y_abp = ((abp_pp < 25) | (abp_std > 22)).astype(int)
        self.abp_encoder.fit(X_abp, y_abp, abp_names)

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

        # Compute genuine modality-specific individual model predictions
        individual_preds = self.compute_individual_model_predictions(
            clin_vitals=clin_vitals,
            wave_feats=wave_feats,
            available_modalities=available_modalities,
            waveform_samples={"ecg": ecg_arr, "ppg": ppg_arr, "abp": abp_arr}
        )

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
            "individual_predictions": individual_preds,
            "disclaimer": "CareMind Physiological Risk Score (0-100) is an engineering prototype decision-support metric for physiological instability, not a diagnostic or mortality prediction model."
        }

    def compute_individual_model_predictions(
        self,
        clin_vitals: Dict[str, Any],
        wave_feats: Dict[str, Any],
        available_modalities: Optional[List[str]] = None,
        waveform_samples: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Compute genuine, modality-specific inference predictions for:
          - ECG
          - PPG
          - ABP
          - Clinical Vitals

        Distinguishes:
          - prediction_available: usable input data present and model inference succeeded
          - data_unavailable: patient/record has no usable signal/vitals for this modality
          - model_unavailable: no compatible model is configured
          - inference_failed: model execution raised an error

        Returns dictionary keyed by modality ('ecg', 'ppg', 'abp', 'clinical').
        """
        available_mods = [str(m).upper() for m in (available_modalities or [])]
        samples = waveform_samples or {}
        predictions: Dict[str, Dict[str, Any]] = {}

        # -------------------------------------------------------------
        # 1. ECG Lead II
        # -------------------------------------------------------------
        try:
            has_ecg_sample = bool(samples.get("ecg") is not None and len(samples["ecg"]) > 0)
            has_ecg_meta = any("ECG" in m for m in available_mods)
            has_ecg_feature = (wave_feats.get("ECG_is_missing", 1.0) == 0.0)
            has_ecg_data = has_ecg_feature or has_ecg_sample or has_ecg_meta

            if not has_ecg_data:
                predictions["ecg"] = {
                    "modality": "ECG",
                    "modality_name": "ECG Lead II",
                    "model_name": "ECG Waveform Instability Model",
                    "model_version": "1.0.0",
                    "status": "data_unavailable",
                    "is_available": False,
                    "prediction": None,
                    "score": None,
                    "class_probabilities": None,
                    "risk_contribution": "0.0% (signal unmonitored)",
                    "fusion_weight": 0.0,
                    "features_used": None,
                    "explanation": "ECG Lead II signal is not connected or waveform data is unavailable for this observation window.",
                    "clinical_disclaimer": "Physiological instability indicator, not a definitive diagnostic arrhythmia classification."
                }
            elif not getattr(self, "ecg_encoder", None) or not self.ecg_encoder.is_fitted:
                predictions["ecg"] = {
                    "modality": "ECG",
                    "modality_name": "ECG Lead II",
                    "model_name": "ECG Waveform Instability Model",
                    "model_version": "1.0.0",
                    "status": "model_unavailable",
                    "is_available": False,
                    "prediction": None,
                    "score": None,
                    "class_probabilities": None,
                    "risk_contribution": None,
                    "fusion_weight": 0.0,
                    "features_used": None,
                    "explanation": "No compatible ECG physiological model is configured.",
                    "clinical_disclaimer": "Physiological instability indicator."
                }
            else:
                ecg_feat_names = ["ECG_mean", "ECG_std", "ECG_rms", "ECG_ptp", "ECG_zero_crossings"]
                ecg_vec = np.array([[float(wave_feats.get(k, 0.0)) for k in ecg_feat_names]])
                ecg_scores, _ = self.ecg_encoder.predict_risk_score(ecg_vec)
                ecg_score = round(float(ecg_scores[0]), 1)
                
                ecg_scaled = self.ecg_encoder.scaler.transform(ecg_vec)
                ecg_logits = float(self.ecg_encoder.model.decision_function(ecg_scaled)[0])
                p_instability = round(float(1.0 / (1.0 + np.exp(-ecg_logits / 1.75))), 4)
                p_normal = round(float(1.0 - p_instability), 4)

                ecg_pred_label = "Elevated Rhythm Variability" if ecg_score >= 50.0 else "Normal Sinus Dynamics"

                predictions["ecg"] = {
                    "modality": "ECG",
                    "modality_name": "ECG Lead II",
                    "model_name": "ECG Waveform Instability Model",
                    "model_version": "1.0.0",
                    "status": "prediction_available",
                    "is_available": True,
                    "prediction": ecg_pred_label,
                    "score": ecg_score,
                    "class_probabilities": {
                        "normal": p_normal,
                        "elevated_variability": p_instability
                    },
                    "risk_contribution": "Waveform stream component (fused at 50.0% late fusion weight)",
                    "fusion_weight": 0.5,
                    "features_used": {k: round(float(wave_feats.get(k, 0.0)), 3) for k in ecg_feat_names},
                    "explanation": "Evaluates continuous cardiac electrical rhythm stability, waveform amplitude standard deviation, and zero-crossing dispersion from continuous ECG Lead II.",
                    "clinical_disclaimer": "Physiological instability indicator, not a definitive diagnostic arrhythmia classification."
                }
        except Exception as e:
            predictions["ecg"] = {
                "modality": "ECG",
                "modality_name": "ECG Lead II",
                "model_name": "ECG Waveform Instability Model",
                "model_version": "1.0.0",
                "status": "inference_failed",
                "is_available": False,
                "error": str(e),
                "prediction": None,
                "score": None,
                "class_probabilities": None,
                "risk_contribution": None,
                "fusion_weight": 0.0,
                "features_used": None,
                "explanation": f"ECG model inference failed: {e}",
                "clinical_disclaimer": "Inference error occurred."
            }

        # -------------------------------------------------------------
        # 2. PPG / Plethysmogram
        # -------------------------------------------------------------
        try:
            has_ppg_sample = bool(samples.get("ppg") is not None and len(samples["ppg"]) > 0)
            has_ppg_meta = any("PPG" in m or "PLETH" in m for m in available_mods)
            has_ppg_feature = (wave_feats.get("PPG_is_missing", 1.0) == 0.0)
            has_ppg_data = has_ppg_feature or has_ppg_sample or has_ppg_meta

            if not has_ppg_data:
                predictions["ppg"] = {
                    "modality": "PPG",
                    "modality_name": "PLETH / PPG Pulse Wave",
                    "model_name": "PPG Peripheral Perfusion Model",
                    "model_version": "1.0.0",
                    "status": "data_unavailable",
                    "is_available": False,
                    "prediction": None,
                    "score": None,
                    "class_probabilities": None,
                    "risk_contribution": "0.0% (signal unmonitored)",
                    "fusion_weight": 0.0,
                    "features_used": None,
                    "explanation": "PPG / Plethysmograph pulse waveform is not connected or unavailable for this observation window.",
                    "clinical_disclaimer": "Physiological perfusion indicator, not a diagnostic peripheral vascular disease evaluation."
                }
            elif not getattr(self, "ppg_encoder", None) or not self.ppg_encoder.is_fitted:
                predictions["ppg"] = {
                    "modality": "PPG",
                    "modality_name": "PLETH / PPG Pulse Wave",
                    "model_name": "PPG Peripheral Perfusion Model",
                    "model_version": "1.0.0",
                    "status": "model_unavailable",
                    "is_available": False,
                    "prediction": None,
                    "score": None,
                    "class_probabilities": None,
                    "risk_contribution": None,
                    "fusion_weight": 0.0,
                    "features_used": None,
                    "explanation": "No compatible PPG physiological model is configured.",
                    "clinical_disclaimer": "Physiological perfusion indicator."
                }
            else:
                ppg_feat_names = ["PPG_mean", "PPG_std", "PPG_peak_max", "PPG_trough_min", "PPG_amplitude_range"]
                ppg_vec = np.array([[float(wave_feats.get(k, 0.0)) for k in ppg_feat_names]])
                ppg_scores, _ = self.ppg_encoder.predict_risk_score(ppg_vec)
                ppg_score = round(float(ppg_scores[0]), 1)

                ppg_scaled = self.ppg_encoder.scaler.transform(ppg_vec)
                ppg_logits = float(self.ppg_encoder.model.decision_function(ppg_scaled)[0])
                p_instability = round(float(1.0 / (1.0 + np.exp(-ppg_logits / 1.75))), 4)
                p_normal = round(float(1.0 - p_instability), 4)

                ppg_pred_label = "Attenuated Pulse / Perfusion Instability" if ppg_score >= 50.0 else "Normal Pulsatile Dynamics"

                predictions["ppg"] = {
                    "modality": "PPG",
                    "modality_name": "PLETH / PPG Pulse Wave",
                    "model_name": "PPG Peripheral Perfusion Model",
                    "model_version": "1.0.0",
                    "status": "prediction_available",
                    "is_available": True,
                    "prediction": ppg_pred_label,
                    "score": ppg_score,
                    "class_probabilities": {
                        "normal": p_normal,
                        "perfusion_attenuation": p_instability
                    },
                    "risk_contribution": "Waveform stream component (fused at 50.0% late fusion weight)",
                    "fusion_weight": 0.5,
                    "features_used": {k: round(float(wave_feats.get(k, 0.0)), 3) for k in ppg_feat_names},
                    "explanation": "Evaluates peripheral vascular pulsatility, pulse wave attenuation, and amplitude stability from continuous photoplethysmogram.",
                    "clinical_disclaimer": "Physiological perfusion indicator, not a diagnostic peripheral vascular disease evaluation."
                }
        except Exception as e:
            predictions["ppg"] = {
                "modality": "PPG",
                "modality_name": "PLETH / PPG Pulse Wave",
                "model_name": "PPG Peripheral Perfusion Model",
                "model_version": "1.0.0",
                "status": "inference_failed",
                "is_available": False,
                "error": str(e),
                "prediction": None,
                "score": None,
                "class_probabilities": None,
                "risk_contribution": None,
                "fusion_weight": 0.0,
                "features_used": None,
                "explanation": f"PPG model inference failed: {e}",
                "clinical_disclaimer": "Inference error occurred."
            }

        # -------------------------------------------------------------
        # 3. Arterial Blood Pressure (ABP)
        # -------------------------------------------------------------
        try:
            has_abp_sample = bool(samples.get("abp") is not None and len(samples["abp"]) > 0)
            has_abp_meta = any("ABP" in m or "ART" in m for m in available_mods)
            has_abp_feature = (wave_feats.get("ABP_is_missing", 1.0) == 0.0)
            has_abp_data = has_abp_feature or has_abp_sample or has_abp_meta

            if not has_abp_data:
                predictions["abp"] = {
                    "modality": "ABP",
                    "modality_name": "Arterial Line ABP",
                    "model_name": "ABP Hemodynamic Instability Model",
                    "model_version": "1.0.0",
                    "status": "data_unavailable",
                    "is_available": False,
                    "prediction": None,
                    "score": None,
                    "class_probabilities": None,
                    "risk_contribution": "0.0% (signal unmonitored)",
                    "fusion_weight": 0.0,
                    "features_used": None,
                    "explanation": "Invasive Arterial Line (ABP) is not connected or unmonitored for this patient.",
                    "clinical_disclaimer": "Hemodynamic instability indicator, not a definitive shock diagnosis."
                }
            elif not getattr(self, "abp_encoder", None) or not self.abp_encoder.is_fitted:
                predictions["abp"] = {
                    "modality": "ABP",
                    "modality_name": "Arterial Line ABP",
                    "model_name": "ABP Hemodynamic Instability Model",
                    "model_version": "1.0.0",
                    "status": "model_unavailable",
                    "is_available": False,
                    "prediction": None,
                    "score": None,
                    "class_probabilities": None,
                    "risk_contribution": None,
                    "fusion_weight": 0.0,
                    "features_used": None,
                    "explanation": "No compatible ABP physiological model is configured.",
                    "clinical_disclaimer": "Hemodynamic instability indicator."
                }
            else:
                abp_feat_names = ["ABP_mean", "ABP_std", "ABP_pulse_pressure"]
                abp_vec = np.array([[float(wave_feats.get(k, 0.0)) for k in abp_feat_names]])
                abp_scores, _ = self.abp_encoder.predict_risk_score(abp_vec)
                abp_score = round(float(abp_scores[0]), 1)

                abp_scaled = self.abp_encoder.scaler.transform(abp_vec)
                abp_logits = float(self.abp_encoder.model.decision_function(abp_scaled)[0])
                p_instability = round(float(1.0 / (1.0 + np.exp(-abp_logits / 1.75))), 4)
                p_normal = round(float(1.0 - p_instability), 4)

                abp_pred_label = "Hemodynamic Instability / Pulse Pressure Narrowing" if abp_score >= 50.0 else "Hemodynamically Stable"

                predictions["abp"] = {
                    "modality": "ABP",
                    "modality_name": "Arterial Line ABP",
                    "model_name": "ABP Hemodynamic Instability Model",
                    "model_version": "1.0.0",
                    "status": "prediction_available",
                    "is_available": True,
                    "prediction": abp_pred_label,
                    "score": abp_score,
                    "class_probabilities": {
                        "normal": p_normal,
                        "hemodynamic_instability": p_instability
                    },
                    "risk_contribution": "Waveform stream component (fused at 50.0% late fusion weight)",
                    "fusion_weight": 0.5,
                    "features_used": {k: round(float(wave_feats.get(k, 0.0)), 2) for k in abp_feat_names},
                    "explanation": "Evaluates continuous invasive arterial pressure variability, pulse pressure degradation, and acute hemodynamic derangements.",
                    "clinical_disclaimer": "Hemodynamic instability indicator, not a definitive shock diagnosis."
                }
        except Exception as e:
            predictions["abp"] = {
                "modality": "ABP",
                "modality_name": "Arterial Line ABP",
                "model_name": "ABP Hemodynamic Instability Model",
                "model_version": "1.0.0",
                "status": "inference_failed",
                "is_available": False,
                "error": str(e),
                "prediction": None,
                "score": None,
                "class_probabilities": None,
                "risk_contribution": None,
                "fusion_weight": 0.0,
                "features_used": None,
                "explanation": f"ABP model inference failed: {e}",
                "clinical_disclaimer": "Inference error occurred."
            }

        # -------------------------------------------------------------
        # 4. Clinical Bedside Vitals
        # -------------------------------------------------------------
        try:
            has_clinical_data = any(
                v is not None and (not isinstance(v, (int, float)) or (not np.isnan(v) and v > 0))
                for v in clin_vitals.values()
            )

            if not has_clinical_data:
                predictions["clinical"] = {
                    "modality": "Clinical Vitals",
                    "modality_name": "Observed Bedside Vitals",
                    "model_name": "Bedside Clinical Instability Model",
                    "model_version": "1.0.0",
                    "status": "data_unavailable",
                    "is_available": False,
                    "prediction": None,
                    "score": None,
                    "class_probabilities": None,
                    "risk_contribution": "0.0% (vitals unobserved; fallback to waveform stream)",
                    "fusion_weight": 0.0,
                    "features_used": None,
                    "explanation": "No bedside vital signs (HR, SpO2, BP, MAP, Resp, Temp) observed for this observation window.",
                    "clinical_disclaimer": "Physiological instability indicator, not a medical diagnostic model."
                }
            elif not getattr(self, "clinical_encoder", None) or not self.clinical_encoder.is_fitted:
                predictions["clinical"] = {
                    "modality": "Clinical Vitals",
                    "modality_name": "Observed Bedside Vitals",
                    "model_name": "Bedside Clinical Instability Model",
                    "model_version": "1.0.0",
                    "status": "model_unavailable",
                    "is_available": False,
                    "prediction": None,
                    "score": None,
                    "class_probabilities": None,
                    "risk_contribution": None,
                    "fusion_weight": 0.0,
                    "features_used": None,
                    "explanation": "No compatible Clinical Vitals physiological model is configured.",
                    "clinical_disclaimer": "Physiological instability indicator."
                }
            else:
                X_clin, _ = self.extract_clinical_feature_vector(clin_vitals)
                clin_score_arr, _ = self.clinical_encoder.predict_risk_score(X_clin)
                clin_score = round(float(clin_score_arr[0]), 1)

                clin_scaled = self.clinical_encoder.scaler.transform(X_clin)
                clin_logits = float(self.clinical_encoder.model.decision_function(clin_scaled)[0])
                p_instability = round(float(1.0 / (1.0 + np.exp(-clin_logits / 1.75))), 4)
                p_normal = round(float(1.0 - p_instability), 4)

                if clin_score >= 75.0:
                    clin_pred_label = "Critical Vital Derangement"
                elif clin_score >= 50.0:
                    clin_pred_label = "Moderate Vital Instability"
                else:
                    clin_pred_label = "Low Risk / Stable"

                # Check if waveforms are present to specify exact fusion contribution
                has_any_waveform = any(
                    m in available_mods for m in ["ECG", "PPG", "ABP", "PLETH"]
                ) or (predictions.get("ecg", {}).get("is_available") or predictions.get("ppg", {}).get("is_available") or predictions.get("abp", {}).get("is_available"))

                fusion_weight = 0.5 if has_any_waveform else 1.0
                fusion_desc = f"{fusion_weight * 100:.0f}% linear contribution to composite multimodal risk"
                if has_any_waveform:
                    fusion_desc += " (balanced with waveform stream)"
                else:
                    fusion_desc += " (waveform stream absent; 100% vital-dominant)"

                clin_feats_used = {k: clin_vitals.get(k) for k in ["HR", "SpO2", "Resp", "SysBP", "DiaBP", "MAP", "Temp"]}

                predictions["clinical"] = {
                    "modality": "Clinical Vitals",
                    "modality_name": "Observed Bedside Vitals",
                    "model_name": "Bedside Clinical Instability Model",
                    "model_version": "1.0.0",
                    "status": "prediction_available",
                    "is_available": True,
                    "prediction": clin_pred_label,
                    "score": clin_score,
                    "class_probabilities": {
                        "normal": p_normal,
                        "vital_instability": p_instability
                    },
                    "risk_contribution": fusion_desc,
                    "fusion_weight": fusion_weight,
                    "features_used": clin_feats_used,
                    "explanation": "Temperature-calibrated logistic regression evaluating acute multi-parameter bedside vital deviations against physiological thresholds.",
                    "clinical_disclaimer": "Physiological instability indicator, not a medical diagnostic model."
                }
        except Exception as e:
            predictions["clinical"] = {
                "modality": "Clinical Vitals",
                "modality_name": "Observed Bedside Vitals",
                "model_name": "Bedside Clinical Instability Model",
                "model_version": "1.0.0",
                "status": "inference_failed",
                "is_available": False,
                "error": str(e),
                "prediction": None,
                "score": None,
                "class_probabilities": None,
                "risk_contribution": None,
                "fusion_weight": 0.0,
                "features_used": None,
                "explanation": f"Clinical vitals model inference failed: {e}",
                "clinical_disclaimer": "Inference error occurred."
            }

        return predictions

    def get_individual_predictions_for_window(self, window_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        Helper to retrieve pre-computed individual predictions or evaluate them dynamically
        from window features if missing from cache.
        """
        if "individual_predictions" in window_data and isinstance(window_data["individual_predictions"], dict):
            return window_data["individual_predictions"]

        clin_vitals = window_data.get("clinical_features", {})
        wave_feats = window_data.get("waveform_features", {})
        samples = window_data.get("waveform_samples", {})
        available_mods = window_data.get("available_modalities", [])

        return self.compute_individual_model_predictions(
            clin_vitals=clin_vitals,
            wave_feats=wave_feats,
            available_modalities=available_mods,
            waveform_samples=samples
        )
