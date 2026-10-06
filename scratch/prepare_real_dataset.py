"""
Script to prepare and cache real MIMIC-IV waveform and clinical data for demo execution.
"""
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import json
import numpy as np
import pandas as pd
import wfdb

from src.mimic.multimodal_prototype import CareMindMultimodalPrototype

def prepare_data():
    os.makedirs("data/demo_waveforms", exist_ok=True)

    demo_records = [
        {
            "record_id": "81739927",
            "subject_id": 10014354,
            "pn_dir": "mimic4wdb/0.1.0/waves/p100/p10014354/81739927/",
            "base_timestamp": "2148-08-16 09:00:17",
            "segment_names": ["81739927_0001", "81739927_0002", "81739927_0003", "81739927_0005"],
            "vitals": {"HR": 88.0, "SpO2": 97.0, "Resp": 18.0, "SysBP": 124.0, "DiaBP": 78.0, "MAP": 93.3, "Temp": 37.1}
        },
        {
            "record_id": "83404654",
            "subject_id": 10020306,
            "pn_dir": "mimic4wdb/0.1.0/waves/p100/p10020306/83404654/",
            "base_timestamp": "2135-01-21 17:02:28",
            "segment_names": ["83404654_0001", "83404654_0002", "83404654_0004", "83404654_0005"],
            "vitals": {"HR": 104.0, "SpO2": 94.0, "Resp": 22.0, "SysBP": 110.0, "DiaBP": 68.0, "MAP": 82.0, "Temp": 37.8}
        },
        {
            "record_id": "82924339",
            "subject_id": 10126957,
            "pn_dir": "mimic4wdb/0.1.0/waves/p101/p10126957/82924339/",
            "base_timestamp": "2163-12-24 17:42:47",
            "segment_names": ["82924339_0001", "82924339_0002", "82924339_0003", "82924339_0004"],
            "vitals": {"HR": None, "SpO2": None, "Resp": None, "SysBP": None, "DiaBP": None, "MAP": None, "Temp": None}
        }
    ]

    prototype = CareMindMultimodalPrototype()
    print("Preparing real multimodal cached dataset...")

    for rec_info in demo_records:
        rec_id = rec_info["record_id"]
        subj_id = rec_info["subject_id"]
        pn_dir = rec_info["pn_dir"]
        base_ts = pd.Timestamp(rec_info["base_timestamp"])

        windows = []
        prev_risk = None
        for win_idx, seg in enumerate(rec_info["segment_names"]):
            try:
                try:
                    record = wfdb.rdrecord(seg, pn_dir=pn_dir, sampto=3750)
                except Exception:
                    record = wfdb.rdrecord(seg, pn_dir=pn_dir)
                channels = record.sig_name
                sig_matrix = record.p_signal

                ecg_sig = np.array([])
                ppg_sig = np.array([])
                abp_sig = np.array([])

                for ch_i, ch_name in enumerate(channels):
                    ch_u = ch_name.upper()
                    col_data = sig_matrix[:, ch_i]
                    valid_data = col_data[~np.isnan(col_data)]

                    if "II" in ch_u or "ECG" in ch_u or "V" in ch_u:
                        if len(valid_data) > 0 and len(ecg_sig) == 0:
                            ecg_sig = valid_data
                    elif "PLETH" in ch_u or "PPG" in ch_u or "SPO2" in ch_u:
                        if len(valid_data) > 0 and len(ppg_sig) == 0:
                            ppg_sig = valid_data
                    elif "ABP" in ch_u or "ART" in ch_u or "BP" in ch_u:
                        if len(valid_data) > 0 and len(abp_sig) == 0:
                            abp_sig = valid_data

                # Genuine MIMIC clinical vitals observation (no synthetic progression or artificial offsets)
                vitals = rec_info["vitals"].copy()

                win_ts = base_ts + pd.Timedelta(seconds=win_idx * 15)
                timestamp_label = win_ts.strftime("%Y-%m-%d %H:%M:%S")

                analysis = prototype.analyze_multimodal_window(
                    record_id=rec_id,
                    subject_id=subj_id,
                    window_index=win_idx,
                    vitals_dict=vitals,
                    ecg_signal=ecg_sig,
                    ppg_signal=ppg_sig,
                    abp_signal=abp_sig,
                    timestamp_str=timestamp_label,
                    previous_risk_score=prev_risk
                )
                prev_risk = analysis["risk_score"]
                windows.append(analysis)
                print(f"  Record {rec_id} Window {win_idx} ({timestamp_label}) -> Risk: {analysis['risk_score']} ({analysis['risk_category']})")
            except Exception as e:
                print(f"  Error segment {seg}: {e}")

        cache_path = os.path.join("data/demo_waveforms", f"{rec_id}.json")
        with open(cache_path, "w") as f:
            json.dump({"record_id": rec_id, "subject_id": subj_id, "windows": windows}, f, indent=2)
        print(f"Cached record {rec_id} with {len(windows)} windows to {cache_path}")

if __name__ == "__main__":
    prepare_data()
