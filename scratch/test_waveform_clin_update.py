import os, sys, json
import numpy as np
sys.path.insert(0, os.path.abspath("."))
from src.mimic.multimodal_prototype import CareMindMultimodalPrototype

prototype = CareMindMultimodalPrototype()
data = json.load(open('data/demo_waveforms/83404654.json'))
vitals_series = [
    {'HR': 92.0, 'SpO2': 96.0, 'Resp': 14.0, 'SysBP': 122.0, 'DiaBP': 77.0, 'MAP': 91.0, 'Temp': 36.6},
    {'HR': 98.0, 'SpO2': 96.0, 'Resp': 19.0, 'SysBP': 85.0, 'DiaBP': 73.0, 'MAP': 78.0, 'Temp': 36.6},
    {'HR': 88.0, 'SpO2': 96.0, 'Resp': 23.0, 'SysBP': 79.0, 'DiaBP': 67.0, 'MAP': 73.0, 'Temp': 36.6},
    {'HR': 105.0, 'SpO2': 98.0, 'Resp': 10.0, 'SysBP': 87.0, 'DiaBP': 64.0, 'MAP': 73.0, 'Temp': 36.1}
]

prev_risk = None
for i, w in enumerate(data['windows']):
    v = vitals_series[i]
    wave_feats = w['waveform_features']
    wave_score = w['waveform_score']
    
    # 1. Clinical score
    X_clin, clin_vitals = prototype.extract_clinical_feature_vector(v)
    clin_score_arr, _ = prototype.clinical_encoder.predict_risk_score(X_clin)
    clinical_score = float(clin_score_arr[0])
    
    # 2. Available modalities
    available_modalities = w.get('available_modalities', [])
    has_clinical = any(val is not None for val in clin_vitals.values())
    if has_clinical and 'Clinical Vitals' not in available_modalities:
        available_modalities.append('Clinical Vitals')
        
    # 3. Fusion
    if not has_clinical and len(available_modalities) > 0:
        raw_fused = wave_score
    elif has_clinical and len(available_modalities) == 1:
        raw_fused = clinical_score
    else:
        X_fusion = np.column_stack([clinical_score, wave_score, (clinical_score * wave_score) / 100.0])
        X_fusion_scaled = prototype.fusion_scaler.transform(X_fusion)
        fusion_logits = prototype.fusion_model.decision_function(X_fusion_scaled)
        fusion_prob = float(1.0 / (1.0 + np.exp(-fusion_logits[0] / 1.75)))
        raw_fused = 0.5 * clinical_score + 0.5 * wave_score + (fusion_prob - 0.5) * 10.0
    
    risk_score = round(float(np.clip(raw_fused, 0.0, 100.0)), 1)
    risk_category = prototype.calculate_risk_category(risk_score)
    
    delta = 0.0
    trend_status = 'STABLE'
    if prev_risk is not None:
        delta = round(risk_score - prev_risk, 1)
        if delta >= 5.0: trend_status = 'ESCALATING'
        elif delta <= -5.0: trend_status = 'IMPROVING'
    prev_risk = risk_score
    
    priority = 'ROUTINE_MONITORING'
    if risk_score >= 75.0 or (risk_score >= 60.0 and trend_status == 'ESCALATING'):
        priority = 'CRITICAL_PRIORITY'
    elif risk_score >= 50.0 or (risk_score >= 40.0 and trend_status == 'ESCALATING'):
        priority = 'HIGH_PRIORITY'
        
    factors = prototype.derive_contributing_factors(
        clin_vitals, wave_feats, clinical_score, wave_score, risk_trend_delta=delta
    )
    
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
    
    hr = clin_vitals['HR']
    sys = clin_vitals['SysBP']
    dia = clin_vitals['DiaBP']
    map_val = clin_vitals['MAP']
    c_score = round(clinical_score, 1)
    w_score = round(wave_score, 1)
    print(f"Win {i}: HR={hr}, BP={sys}/{dia}, MAP={map_val} | clin_score={c_score}, wave_score={w_score}, risk={risk_score}, delta={delta}, prio={priority}")
    print(f"   Clin indiv pred: {indiv['clinical']['prediction']} ({indiv['clinical']['score']})")
    print(f"   ECG indiv pred: {indiv['ecg']['prediction']} ({indiv['ecg']['score']})")
