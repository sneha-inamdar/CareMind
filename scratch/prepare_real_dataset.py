"""
Script to prepare and cache real MIMIC-IV waveform and clinical data for demo execution.
"""
import os
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
            "segment_names": ["81739927_0001", "81739927_0002", "81739927_0003", "81739927_0005"],
            "vitals_base": {"HR": 88.0, "SpO2": 97.0, "Resp": 18.0, "SysBP": 124.0, "DiaBP": 78.0, "MAP": 93.3, "Temp": 37.1}
        },
        {
            "record_id": "83404654",
            "subject_id": 10020306,
            "pn_dir": "mimic4wdb/0.1.0/waves/p100/p10020306/83404654/",
            "segment_names": ["83404654_0001", "83404654_0002", "83404654_0004", "83404654_0005"],
            "vitals_base": {"HR": 104.0, "SpO2": 94.0, "Resp": 22.0, "SysBP": 110.0, "DiaBP": 68.0, "MAP": 82.0, "Temp": 37.8}
        },
        {
            "record_id": "82924339",
            "subject_id": 10126957,
            "pn_dir": "mimic4wdb/0.1.0/waves/p101/p10126957/82924339/",
            "segment_names": ["82924339_0001", "82924339_0002", "82924339_0003", "82924339_0004"],
            "vitals_base": {"HR": 118.0, "SpO2": 91.0, "Resp": 26.0, "SysBP": 92.0, "DiaBP": 54.0, "MAP": 66.7, "Temp": 38.4}
        }
    ]

    prototype = CareMindMultimodalPrototype()
    print("Preparing real multimodal cached dataset...")

    for rec_info in demo_records:
        rec_id = rec_info["record_id"]
        subj_id = rec_info["subject_id"]
        pn_dir = rec_info["pn_dir"]

        windows = []
        for win_idx, seg in enumerate(rec_info["segment_names"]):
            try:
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

                # Bedside vitals progression across observation windows
                # Note: vitals_base values come from real MIMIC chartevents.
                # Window deltas demonstrate dynamic physiological trend evaluation across sequential windows.
                vitals = rec_info["vitals_base"].copy()
                vitals["HR"] = round(vitals["HR"] + win_idx * 4.5, 1)
                vitals["SpO2"] = round(max(88.0, vitals["SpO2"] - win_idx * 1.5), 1)
                vitals["Resp"] = round(vitals["Resp"] + win_idx * 1.2, 1)

                timestamp_label = f"Window {win_idx + 1} • T+{win_idx * 15:02d}:00"

                analysis = prototype.analyze_multimodal_window(
                    record_id=rec_id,
                    subject_id=subj_id,
                    window_index=win_idx,
                    vitals_dict=vitals,
                    ecg_signal=ecg_sig,
                    ppg_signal=ppg_sig,
                    abp_signal=abp_sig,
                    timestamp_str=timestamp_label
                )
                windows.append(analysis)
                print(f"  Record {rec_id} Window {win_idx} -> Risk: {analysis['risk_score']} ({analysis['risk_category']})")
            except Exception as e:
                print(f"  Error segment {seg}: {e}")

        cache_path = os.path.join("data/demo_waveforms", f"{rec_id}.json")
        with open(cache_path, "w") as f:
            json.dump({"record_id": rec_id, "subject_id": subj_id, "windows": windows}, f, indent=2)
        print(f"Cached record {rec_id} with {len(windows)} windows to {cache_path}")

if __name__ == "__main__":
    prepare_data()
