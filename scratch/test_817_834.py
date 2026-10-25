import os, sys, json
import numpy as np
sys.path.insert(0, os.path.abspath("."))
from src.mimic.multimodal_prototype import CareMindMultimodalPrototype

prototype = CareMindMultimodalPrototype()

# 81739927 (Subject 10014354)
data_817 = json.load(open('data/demo_waveforms/81739927.json'))
vitals_817 = [
    {"HR": 63.0, "SpO2": 98.0, "Resp": 20.0, "SysBP": 153.0, "DiaBP": 60.0, "MAP": 85.0, "Temp": 36.6},
    {"HR": 55.0, "SpO2": 96.0, "Resp": 23.0, "SysBP": 153.0, "DiaBP": 60.0, "MAP": 85.0, "Temp": 36.6},
    {"HR": 53.0, "SpO2": 96.0, "Resp": 17.0, "SysBP": 153.0, "DiaBP": 60.0, "MAP": 85.0, "Temp": 36.6},
    {"HR": 60.0, "SpO2": 96.0, "Resp": 14.0, "SysBP": 146.0, "DiaBP": 56.0, "MAP": 80.0, "Temp": 36.6}
]

print("\n--- 81739927 ---")
prev_risk = None
for i, w in enumerate(data_817['windows']):
    v = vitals_817[i]
    wave_feats = w['waveform_features']
    wave_score = w['waveform_score']
    X_clin, clin_vitals = prototype.extract_clinical_feature_vector(v)
    clin_score_arr, _ = prototype.clinical_encoder.predict_risk_score(X_clin)
    clinical_score = float(clin_score_arr[0])
    available_modalities = w.get('available_modalities', [])
    has_clinical = any(val is not None for val in clin_vitals.values())
    if has_clinical and 'Clinical Vitals' not in available_modalities:
        available_modalities.append('Clinical Vitals')
    X_fusion = np.column_stack([clinical_score, wave_score, (clinical_score * wave_score) / 100.0])
    X_fusion_scaled = prototype.fusion_scaler.transform(X_fusion)
    fusion_logits = prototype.fusion_model.decision_function(X_fusion_scaled)
    fusion_prob = float(1.0 / (1.0 + np.exp(-fusion_logits[0] / 1.75)))
    raw_fused = 0.5 * clinical_score + 0.5 * wave_score + (fusion_prob - 0.5) * 10.0
    risk_score = round(float(np.clip(raw_fused, 0.0, 100.0)), 1)
    delta = round(risk_score - prev_risk, 1) if prev_risk is not None else 0.0
    prev_risk = risk_score
    indiv = prototype.compute_individual_model_predictions(
        clin_vitals=clin_vitals,
        wave_feats=wave_feats,
        available_modalities=available_modalities,
        waveform_samples={
            'ecg': np.array(w.get('waveform_samples', {}).get('ecg', [])),
            'ppg': np.array(w.get('waveform_samples', {}).get('ppg', [])),
            'abp': np.array(w.get('waveform_samples', {}).get('abp', []))
        }
    )
    print(f"Win {i}: HR={clin_vitals['HR']}, BP={clin_vitals['SysBP']}/{clin_vitals['DiaBP']} | clin_score={round(clinical_score,1)}, wave_score={round(wave_score,1)}, risk={risk_score}, delta={delta}")
    print(f"   Clin indiv pred: {indiv['clinical']['prediction']} ({indiv['clinical']['score']})")

# 83411188 (Subject 10039708)
data_834 = json.load(open('data/demo_waveforms/83411188.json'))
vitals_834 = [
    {"HR": 76.0, "SpO2": 99.0, "Resp": 18.0, "SysBP": 81.0, "DiaBP": 43.0, "MAP": 51.0, "Temp": 36.6},
    {"HR": 76.0, "SpO2": 99.0, "Resp": 18.0, "SysBP": 81.0, "DiaBP": 43.0, "MAP": 51.0, "Temp": 36.6},
    {"HR": 81.0, "SpO2": 100.0, "Resp": 30.0, "SysBP": 81.0, "DiaBP": 43.0, "MAP": 51.0, "Temp": 36.4},
    {"HR": 71.0, "SpO2": 100.0, "Resp": 19.0, "SysBP": 81.0, "DiaBP": 43.0, "MAP": 51.0, "Temp": 36.4}
]

print("\n--- 83411188 ---")
prev_risk = None
for i, w in enumerate(data_834['windows']):
    v = vitals_834[i]
    wave_feats = w['waveform_features']
    wave_score = w['waveform_score']
    X_clin, clin_vitals = prototype.extract_clinical_feature_vector(v)
    clin_score_arr, _ = prototype.clinical_encoder.predict_risk_score(X_clin)
    clinical_score = float(clin_score_arr[0])
    available_modalities = w.get('available_modalities', [])
    has_clinical = any(val is not None for val in clin_vitals.values())
    if has_clinical and 'Clinical Vitals' not in available_modalities:
        available_modalities.append('Clinical Vitals')
    X_fusion = np.column_stack([clinical_score, wave_score, (clinical_score * wave_score) / 100.0])
    X_fusion_scaled = prototype.fusion_scaler.transform(X_fusion)
    fusion_logits = prototype.fusion_model.decision_function(X_fusion_scaled)
    fusion_prob = float(1.0 / (1.0 + np.exp(-fusion_logits[0] / 1.75)))
    raw_fused = 0.5 * clinical_score + 0.5 * wave_score + (fusion_prob - 0.5) * 10.0
    risk_score = round(float(np.clip(raw_fused, 0.0, 100.0)), 1)
    delta = round(risk_score - prev_risk, 1) if prev_risk is not None else 0.0
    prev_risk = risk_score
    indiv = prototype.compute_individual_model_predictions(
        clin_vitals=clin_vitals,
        wave_feats=wave_feats,
        available_modalities=available_modalities,
        waveform_samples={
            'ecg': np.array(w.get('waveform_samples', {}).get('ecg', [])),
            'ppg': np.array(w.get('waveform_samples', {}).get('ppg', [])),
            'abp': np.array(w.get('waveform_samples', {}).get('abp', []))
        }
    )
    print(f"Win {i}: HR={clin_vitals['HR']}, BP={clin_vitals['SysBP']}/{clin_vitals['DiaBP']} | clin_score={round(clinical_score,1)}, wave_score={round(wave_score,1)}, risk={risk_score}, delta={delta}")
    print(f"   Clin indiv pred: {indiv['clinical']['prediction']} ({indiv['clinical']['score']})")
