"""
Robust Waveform Linkage & Inventory Script for MIMIC-IV Waveform Database (mimic4wdb/0.1.0).

Scans MIMIC-IV Waveform subject directories, parses segment headers,
extracts channels & start timestamps, and links with MIMIC Demo clinical cohort stays.
"""

import os
import re
import urllib.request
import concurrent.futures
import pandas as pd
import numpy as np
from typing import Dict, List, Any

BASE_URL = "https://physionet.org/files/mimic4wdb/0.1.0/"
DEMO_DIR = r"C:\Users\Sneha\Desktop\College sem 5\project\CareMind\data\MIMIC_Demo\mimic-iv-clinical-database-demo-2.2"

def fetch_url(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp:
        return resp.read().decode("utf-8")

def parse_header_date_time(date_str: str, time_str: str) -> str:
    """Parse WFDB date (dd/mm/yyyy) and time (hh:mm:ss.sss) into ISO string."""
    try:
        parts = date_str.split('/')
        if len(parts) == 3:
            day, month, year = parts[0], parts[1], parts[2]
            iso_date = f"{year}-{int(month):02d}-{int(day):02d}"
            return f"{iso_date} {time_str}"
    except Exception:
        pass
    return f"{date_str} {time_str}"

def inspect_subject_record(sub_dir: str) -> List[Dict[str, Any]]:
    subj_match = re.search(r"p(\d{8})", sub_dir)
    subject_id = int(subj_match.group(1)) if subj_match else None
    records_list = []
    
    try:
        sub_records_text = fetch_url(BASE_URL + sub_dir + "RECORDS")
        rec_paths = [r.strip() for r in sub_records_text.strip().split("\n") if r.strip()]
        
        for rec_path in rec_paths:
            master_hea_url = f"{BASE_URL}{sub_dir}{rec_path}.hea"
            rec_id = rec_path.split("/")[-1]
            rec_folder = rec_path.split("/")[0]
            
            try:
                hea_text = fetch_url(master_hea_url)
                # Filter out comment lines starting with #
                lines = [l.strip() for l in hea_text.strip().split("\n") if l.strip() and not l.strip().startswith("#")]
                if not lines:
                    continue
                
                header_tokens = lines[0].split()
                num_signals = int(header_tokens[1].split('/')[0]) if len(header_tokens) > 1 else 0
                fs = float(header_tokens[2].split('/')[0]) if len(header_tokens) > 2 else 0.0
                num_samples = int(header_tokens[3]) if len(header_tokens) > 3 else 0
                base_time = header_tokens[4] if len(header_tokens) > 4 else ""
                base_date = header_tokens[5] if len(header_tokens) > 5 else ""
                
                start_iso = parse_header_date_time(base_date, base_time)
                duration_sec = (num_samples / fs) if fs > 0 else 0.0
                
                # Check segment layout/first non-layout segment for signal channels
                first_seg_name = None
                for l in lines[1:]:
                    seg_tokens = l.split()
                    if len(seg_tokens) >= 1 and seg_tokens[0] != "~" and not seg_tokens[0].startswith("layout"):
                        first_seg_name = seg_tokens[0]
                        break
                
                channels = []
                if first_seg_name:
                    seg_hea_url = f"{BASE_URL}{sub_dir}{rec_folder}/{first_seg_name}.hea"
                    try:
                        seg_hea_text = fetch_url(seg_hea_url)
                        for seg_l in seg_hea_text.strip().split("\n"):
                            seg_l = seg_l.strip()
                            if seg_l and not seg_l.startswith("#") and not seg_l.startswith(first_seg_name):
                                parts = seg_l.split()
                                if len(parts) >= 9:
                                    channels.append(parts[-1])
                    except Exception:
                        pass
                
                has_ecg = any(c.upper() in ["II", "V", "ECG", "I", "III", "AVR", "AVL", "AVF"] for c in channels)
                has_abp = any(c.upper() in ["ABP", "ART", "BP"] for c in channels)
                has_ppg = any(c.upper() in ["PLETH", "PPG", "SPO2"] for c in channels)
                
                records_list.append({
                    "subject_id": subject_id,
                    "record_dir": sub_dir,
                    "record_name": rec_id,
                    "fs": fs,
                    "num_samples": num_samples,
                    "duration_hrs": round(duration_sec / 3600.0, 2),
                    "start_timestamp": start_iso,
                    "channels": channels,
                    "has_ecg": has_ecg,
                    "has_abp": has_abp,
                    "has_ppg": has_ppg
                })
            except Exception as err:
                pass
    except Exception as err:
        pass
    return records_list

def main():
    print("=== 1. FETCHING MIMIC-IV WAVEFORM RECORDS INDEX ===")
    records_text = fetch_url(BASE_URL + "RECORDS")
    subject_dirs = [line.strip() for line in records_text.strip().split("\n") if line.strip()]
    print(f"Total Waveform Subject Directories: {len(subject_dirs)}")
    
    # Inspect top 40 subject directories
    target_sub_dirs = subject_dirs[:40]
    print(f"Parsing headers for {len(target_sub_dirs)} subject directories...")
    
    waveform_records = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(inspect_subject_record, s): s for s in target_sub_dirs}
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            waveform_records.extend(res)

    df_waves = pd.DataFrame(waveform_records)
    print(f"\nTotal Parsed Waveform Records: {len(df_waves)}")
    if df_waves.empty:
        print("No waveform records parsed.")
        return

    print(f"Unique Subjects in Waveform Subset: {df_waves['subject_id'].nunique()}")

    # Channel metrics
    ecg_count = df_waves["has_ecg"].sum()
    abp_count = df_waves["has_abp"].sum()
    ppg_count = df_waves["has_ppg"].sum()
    
    t1_count = len(df_waves[df_waves["has_ecg"] & df_waves["has_abp"] & df_waves["has_ppg"]])
    t2_count = len(df_waves[df_waves["has_ecg"] & df_waves["has_ppg"]])
    t3_count = len(df_waves[df_waves["has_ecg"]])

    print("\n=== 2. WAVEFORM CHANNEL AVAILABILITY REPORT ===")
    print(f"  ECG Available: {ecg_count}/{len(df_waves)} ({round(ecg_count/len(df_waves)*100, 1)}%)")
    print(f"  ABP Available: {abp_count}/{len(df_waves)} ({round(abp_count/len(df_waves)*100, 1)}%)")
    print(f"  PPG Available: {ppg_count}/{len(df_waves)} ({round(ppg_count/len(df_waves)*100, 1)}%)")
    print(f"  TIER 1 (ECG + ABP + PPG): {t1_count}/{len(df_waves)} ({round(t1_count/len(df_waves)*100, 1)}%)")
    print(f"  TIER 2 (ECG + PPG): {t2_count}/{len(df_waves)} ({round(t2_count/len(df_waves)*100, 1)}%)")
    print(f"  TIER 3 (ECG only): {t3_count}/{len(df_waves)} ({round(t3_count/len(df_waves)*100, 1)}%)")

    # Load MIMIC Demo Clinical Cohort for Linkage Test
    hosp_dir = os.path.join(DEMO_DIR, "hosp")
    icu_dir = os.path.join(DEMO_DIR, "icu")
    patients = pd.read_csv(os.path.join(hosp_dir, "patients.csv.gz"))
    icustays = pd.read_csv(os.path.join(icu_dir, "icustays.csv.gz"))
    
    demo_subjects = set(patients["subject_id"])
    wave_subjects = set(df_waves["subject_id"])
    matched_subjects = demo_subjects.intersection(wave_subjects)
    
    print("\n=== 3. CLINICAL & WAVEFORM COHORT LINKAGE ===")
    print(f"Demo Clinical Subjects: {len(demo_subjects)}")
    print(f"Waveform Subjects Inspected: {len(wave_subjects)}")
    print(f"Matched Direct Patient Linkages: {len(matched_subjects)}")

    print("\n=== 4. SAMPLE LINKAGE RECORDS TABLE ===")
    sample_cols = ["subject_id", "record_name", "fs", "duration_hrs", "start_timestamp", "has_ecg", "has_abp", "has_ppg"]
    print(df_waves[sample_cols].head(10).to_string())

if __name__ == "__main__":
    main()
