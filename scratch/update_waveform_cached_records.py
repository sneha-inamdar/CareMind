"""
Update cached waveform records for subjects present in MIMIC-IV Clinical Demo chartevents:
- 83404654 (Bed ICU-10, Subject 10020306)
- 81739927 (Bed ICU-08, Subject 10014354)
- 83411188 (Bed ICU-11, Subject 10039708)

Using genuine sequential observations from chartevents.csv.gz, preserving all existing
waveform samples, waveform features, and modality configuration.
"""

import os
import sys
import json
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath("."))
from src.mimic.multimodal_prototype import CareMindMultimodalPrototype

DATA_DIR = os.path.join("data", "demo_waveforms")
ICU_DIR = os.path.join("data", "MIMIC_Demo", "mimic-iv-clinical-database-demo-2.2", "icu")
CHARTEVENTS_PATH = os.path.join(ICU_DIR, "chartevents.csv.gz")

ITEM_MAP = {
    220045: "HR",
    220277: "SpO2",
    220210: "Resp",
    220179: "SysBP",
    220050: "SysBP",
    220180: "DiaBP",
    220051: "DiaBP",
    220181: "MAP",
    220052: "MAP",
    223761: "TempF",
    223762: "TempC"
}

TARGET_RECORDS = {
    "83404654": 10020306,
    "81739927": 10014354,
    "83411188": 10039708
}

def extract_genuine_vitals():
    needed_subjs = set(TARGET_RECORDS.values())
    chunks = []
    print(f"Reading chartevents for subjects {needed_subjs}...")
    for chunk in pd.read_csv(CHARTEVENTS_PATH, chunksize=50000):
        m = chunk[chunk["subject_id"].isin(needed_subjs) & chunk["itemid"].isin(ITEM_MAP.keys())]
        if len(m) > 0:
            chunks.append(m[["subject_id", "charttime", "itemid", "valuenum"]])
            
    df = pd.concat(chunks, ignore_index=True)
    df["vital"] = df["itemid"].map(ITEM_MAP)
    
    # Convert TempF to TempC
    tempf_mask = df["vital"] == "TempF"
    df.loc[tempf_mask, "valuenum"] = (df.loc[tempf_mask, "valuenum"] - 32.0) * 5.0 / 9.0
    df.loc[tempf_mask, "vital"] = "Temp"
    tempc_mask = df["vital"] == "TempC"
    df.loc[tempc_mask, "vital"] = "Temp"
    
    subj_vitals = {}
    for s in needed_subjs:
        s_df = df[df["subject_id"] == s].sort_values("charttime")
        piv = s_df.pivot_table(index="charttime", columns="vital", values="valuenum", aggfunc="last")
        piv = piv.ffill().bfill()
        piv.index = pd.to_datetime(piv.index)
        
        selected = []
        last_t = None
        for t, row in piv.iterrows():
            if last_t is None or (t - last_t).total_seconds() >= 15 * 60:
                hr = row.get("HR")
                sys = row.get("SysBP")
                if pd.notna(hr) and pd.notna(sys):
                    v_dict = {
                        "HR": round(float(row.get("HR", 80.0)), 1),
                        "SpO2": round(float(row.get("SpO2", 98.0)), 1),
                        "Resp": round(float(row.get("Resp", 18.0)), 1),
                        "SysBP": round(float(row.get("SysBP", 120.0)), 1),
                        "DiaBP": round(float(row.get("DiaBP", 75.0)), 1),
                        "MAP": round(float(row.get("MAP", 90.0)), 1),
                        "Temp": round(float(row.get("Temp", 37.0)), 1)
                    }
                    selected.append((t.strftime("%Y-%m-%d %H:%M:%S"), v_dict))
                    last_t = t
                    if len(selected) == 4:
                        break
        subj_vitals[s] = selected
        print(f"Subject {s}: extracted {len(selected)} sequential observation windows.")
    return subj_vitals

def update_records():
    prototype = CareMindMultimodalPrototype()
    subj_vitals = extract_genuine_vitals()
    
    for rec_id, subj_id in TARGET_RECORDS.items():
        cache_path = os.path.join(DATA_DIR, f"{rec_id}.json")
        if not os.path.exists(cache_path):
            print(f"File {cache_path} not found!")
            continue
            
        with open(cache_path, "r") as f:
            data = json.load(f)
            
        series = subj_vitals.get(subj_id, [])
        if len(series) < 4:
            print(f"Error: Not enough windows for subject {subj_id} (found {len(series)})")
            continue
            
        new_windows = []
        prev_risk = None
        
        for win_idx, old_w in enumerate(data.get("windows", [])):
            if win_idx >= len(series):
                break
                
            chart_ts, v = series[win_idx]
            wave_samples = old_w.get("waveform_samples", {})
            wave_feats = old_w.get("waveform_features", {})
            wave_score = old_w.get("waveform_score", 50.0)
            
            ecg_sig = np.array(wave_samples.get("ecg", []))
            ppg_sig = np.array(wave_samples.get("ppg", []))
            abp_sig = np.array(wave_samples.get("abp", []))
            
            # Clinical score
            X_clin, clin_vitals = prototype.extract_clinical_feature_vector(v)
            clin_score_arr, _ = prototype.clinical_encoder.predict_risk_score(X_clin)
            clinical_score = float(clin_score_arr[0])
            
            # Available modalities
            avail_mods = []
            if len(ecg_sig) > 0 or wave_feats.get("ECG_is_missing", 1.0) == 0.0:
                avail_mods.append("ECG")
            if len(ppg_sig) > 0 or wave_feats.get("PPG_is_missing", 1.0) == 0.0:
                avail_mods.append("PPG")
            if len(abp_sig) > 0 or wave_feats.get("ABP_is_missing", 1.0) == 0.0:
                avail_mods.append("ABP")
            avail_mods.append("Clinical Vitals")
            
            # Adaptive modality fusion
            X_fusion = np.column_stack([clinical_score, wave_score, (clinical_score * wave_score) / 100.0])
            X_fusion_scaled = prototype.fusion_scaler.transform(X_fusion)
            fusion_logits = prototype.fusion_model.decision_function(X_fusion_scaled)
            fusion_prob = float(1.0 / (1.0 + np.exp(-fusion_logits[0] / 1.75)))
            raw_fused = 0.5 * clinical_score + 0.5 * wave_score + (fusion_prob - 0.5) * 10.0
            
            risk_score = round(float(np.clip(raw_fused, 0.0, 100.0)), 1)
            risk_category = prototype.calculate_risk_category(risk_score)
            
            # Temporal trend
            risk_trend_delta = 0.0
            risk_trend_status = "STABLE"
            if prev_risk is not None:
                risk_trend_delta = round(float(risk_score - prev_risk), 1)
                if risk_trend_delta >= 5.0:
                    risk_trend_status = "ESCALATING"
                elif risk_trend_delta <= -5.0:
                    risk_trend_status = "IMPROVING"
            prev_risk = risk_score
            
            # Priority status
            priority_status = "ROUTINE_MONITORING"
            if risk_score >= 75.0 or (risk_score >= 60.0 and risk_trend_status == "ESCALATING"):
                priority_status = "CRITICAL_PRIORITY"
            elif risk_score >= 50.0 or (risk_score >= 40.0 and risk_trend_status == "ESCALATING"):
                priority_status = "HIGH_PRIORITY"
                
            # Contributing factors
            factors = prototype.derive_contributing_factors(
                clin_vitals, wave_feats, clinical_score, wave_score, risk_trend_delta=risk_trend_delta
            )
            
            # Individual predictions
            indiv_preds = prototype.compute_individual_model_predictions(
                clin_vitals=clin_vitals,
                wave_feats=wave_feats,
                available_modalities=avail_mods,
                waveform_samples={"ecg": ecg_sig, "ppg": ppg_sig, "abp": abp_sig}
            )
            
            win_obj = {
                "record_id": rec_id,
                "subject_id": subj_id,
                "window_index": win_idx,
                "timestamp": old_w.get("timestamp", chart_ts),
                "clinical_features": clin_vitals,
                "waveform_features": wave_feats,
                "clinical_score": round(clinical_score, 1),
                "waveform_score": round(wave_score, 1),
                "fusion_score": risk_score,
                "risk_score": risk_score,
                "risk_category": risk_category,
                "risk_trend_delta": risk_trend_delta,
                "risk_trend_status": risk_trend_status,
                "priority_status": priority_status,
                "available_modalities": avail_mods,
                "contributing_factors": factors,
                "waveform_samples": wave_samples,
                "individual_predictions": indiv_preds,
                "disclaimer": old_w.get("disclaimer", "CareMind Physiological Risk Score is an engineering prototype decision-support metric.")
            }
            new_windows.append(win_obj)
            
        data["windows"] = new_windows
        if "Clinical Vitals" not in data.get("available_modalities", []):
            data["available_modalities"].append("Clinical Vitals")
            
        with open(cache_path, "w") as f:
            json.dump(data, f, indent=2)
            
        print(f"Updated {cache_path} with {len(new_windows)} sequential windows:")
        for idx, nw in enumerate(new_windows):
            cf = nw["clinical_features"]
            print(f"  Win {idx}: HR={cf['HR']}, BP={cf['SysBP']}/{cf['DiaBP']}, MAP={cf['MAP']}, clin_score={nw['clinical_score']}, wave_score={nw['waveform_score']}, risk={nw['risk_score']}")

if __name__ == "__main__":
    update_records()
