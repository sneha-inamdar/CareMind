import json
import numpy as np
from src.mimic.multimodal_prototype import CareMindMultimodalPrototype

prototype = CareMindMultimodalPrototype()
data = json.load(open("data/demo_waveforms/83404654.json"))

vitals_series = [
    {"HR": 92.0, "SpO2": 96.0, "Resp": 14.0, "SysBP": 122.0, "DiaBP": 77.0, "MAP": 91.0, "Temp": 36.6},
    {"HR": 98.0, "SpO2": 96.0, "Resp": 19.0, "SysBP": 85.0, "DiaBP": 73.0, "MAP": 78.0, "Temp": 36.6},
    {"HR": 88.0, "SpO2": 96.0, "Resp": 23.0, "SysBP": 79.0, "DiaBP": 67.0, "MAP": 73.0, "Temp": 36.6},
    {"HR": 105.0, "SpO2": 98.0, "Resp": 10.0, "SysBP": 87.0, "DiaBP": 64.0, "MAP": 73.0, "Temp": 36.1}
]

prev_risk = None
for i, w in enumerate(data["windows"]):
    ecg_s = np.array(w.get("waveform_samples", {}).get("ecg", []))
    ppg_s = np.array(w.get("waveform_samples", {}).get("ppg", []))
    abp_s = np.array(w.get("waveform_samples", {}).get("abp", []))
    v = vitals_series[i]
    
    res = prototype.analyze_multimodal_window(
        record_id="83404654",
        subject_id=10020306,
        window_index=i,
        vitals_dict=v,
        ecg_signal=ecg_s,
        ppg_signal=ppg_s,
        abp_signal=abp_s,
        timestamp_str=w.get("timestamp"),
        previous_risk_score=prev_risk
    )
    res["individual_predictions"] = prototype.get_individual_predictions_for_window(res)
    prev_risk = res["risk_score"]
    
    print(f"Win {i}: HR={res['clinical_features']['HR']}, BP={res['clinical_features']['SysBP']}/{res['clinical_features']['DiaBP']}, clin_score={res['clinical_score']}, wave_score={res['waveform_score']}, risk={res['risk_score']}")
    print(f"   Clin pred: {res['individual_predictions']['clinical']['prediction']} (score: {res['individual_predictions']['clinical']['score']})")
    print(f"   ECG pred: {res['individual_predictions']['ecg']['prediction']} (avail: {res['individual_predictions']['ecg']['is_available']})")
