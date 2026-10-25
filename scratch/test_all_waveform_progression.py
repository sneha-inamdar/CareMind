import json
import numpy as np
from src.mimic.multimodal_prototype import CareMindMultimodalPrototype

prototype = CareMindMultimodalPrototype()

# 81739927
data_817 = json.load(open("data/demo_waveforms/81739927.json"))
vitals_817 = [
    {"HR": 63.0, "SpO2": 98.0, "Resp": 20.0, "SysBP": 153.0, "DiaBP": 60.0, "MAP": 85.0, "Temp": 36.6},
    {"HR": 55.0, "SpO2": 96.0, "Resp": 23.0, "SysBP": 153.0, "DiaBP": 60.0, "MAP": 85.0, "Temp": 36.6},
    {"HR": 53.0, "SpO2": 96.0, "Resp": 17.0, "SysBP": 153.0, "DiaBP": 60.0, "MAP": 85.0, "Temp": 36.6},
    {"HR": 60.0, "SpO2": 96.0, "Resp": 14.0, "SysBP": 146.0, "DiaBP": 56.0, "MAP": 80.0, "Temp": 36.6}
]

print("\n--- Testing 81739927 ---")
prev_risk = None
for i, w in enumerate(data_817["windows"]):
    ecg_s = np.array(w.get("waveform_samples", {}).get("ecg", []))
    ppg_s = np.array(w.get("waveform_samples", {}).get("ppg", []))
    abp_s = np.array(w.get("waveform_samples", {}).get("abp", []))
    v = vitals_817[i]
    res = prototype.analyze_multimodal_window(
        record_id="81739927",
        subject_id=10014354,
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
    print(f"   Clin pred: {res['individual_predictions']['clinical']['prediction']} ({res['individual_predictions']['clinical']['score']})")

# 83411188
data_834 = json.load(open("data/demo_waveforms/83411188.json"))
vitals_834 = [
    {"HR": 76.0, "SpO2": 99.0, "Resp": 18.0, "SysBP": 81.0, "DiaBP": 43.0, "MAP": 51.0, "Temp": 36.6},
    {"HR": 76.0, "SpO2": 99.0, "Resp": 18.0, "SysBP": 81.0, "DiaBP": 43.0, "MAP": 51.0, "Temp": 36.6},
    {"HR": 81.0, "SpO2": 100.0, "Resp": 30.0, "SysBP": 81.0, "DiaBP": 43.0, "MAP": 51.0, "Temp": 36.4},
    {"HR": 71.0, "SpO2": 100.0, "Resp": 19.0, "SysBP": 81.0, "DiaBP": 43.0, "MAP": 51.0, "Temp": 36.4}
]

print("\n--- Testing 83411188 ---")
prev_risk = None
for i, w in enumerate(data_834["windows"]):
    ecg_s = np.array(w.get("waveform_samples", {}).get("ecg", []))
    ppg_s = np.array(w.get("waveform_samples", {}).get("ppg", []))
    abp_s = np.array(w.get("waveform_samples", {}).get("abp", []))
    v = vitals_834[i]
    res = prototype.analyze_multimodal_window(
        record_id="83411188",
        subject_id=10039708,
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
    print(f"   Clin pred: {res['individual_predictions']['clinical']['prediction']} ({res['individual_predictions']['clinical']['score']})")
