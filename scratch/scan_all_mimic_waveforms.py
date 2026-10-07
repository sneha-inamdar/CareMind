"""
Scan all 198 MIMIC-IV Waveform subject directories to discover all available waveform records,
extract channel metadata, sampling rates, signal lengths, start timestamps, and categorize into Tiers.
"""

import os
import re
import urllib.request
import concurrent.futures
import pandas as pd
import numpy as np

BASE_URL = "https://physionet.org/files/mimic4wdb/0.1.0/"
DEMO_DIR = r"C:\Users\Sneha\Desktop\College sem 5\project\CareMind\data\MIMIC_Demo\mimic-iv-clinical-database-demo-2.2"

def fetch_url(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp:
        return resp.read().decode("utf-8")

def parse_header_date_time(date_str: str, time_str: str) -> str:
    try:
        parts = date_str.split('/')
        if len(parts) == 3:
            day, month, year = parts[0], parts[1], parts[2]
            iso_date = f"{year}-{int(month):02d}-{int(day):02d}"
            return f"{iso_date} {time_str}"
    except Exception:
        pass
    return f"{date_str} {time_str}"

def inspect_subject_record(sub_dir: str):
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
                lines = [l.strip() for l in hea_text.strip().split("\n") if l.strip() and not l.strip().startswith("#")]
                if not lines:
                    continue
                
                header_tokens = lines[0].split()
                fs = float(header_tokens[2].split('/')[0]) if len(header_tokens) > 2 else 0.0
                num_samples = int(header_tokens[3]) if len(header_tokens) > 3 else 0
                base_time = header_tokens[4] if len(header_tokens) > 4 else ""
                base_date = header_tokens[5] if len(header_tokens) > 5 else ""
                
                start_iso = parse_header_date_time(base_date, base_time)
                duration_sec = (num_samples / fs) if fs > 0 else 0.0
                
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
                
                if has_ecg and has_abp and has_ppg:
                    tier = "Tier 1 (ECG+ABP+PPG)"
                elif has_ecg and has_ppg:
                    tier = "Tier 2 (ECG+PPG)"
                elif has_ecg:
                    tier = "Tier 3 (ECG only)"
                else:
                    tier = "Tier 4 (Other)"

                records_list.append({
                    "subject_id": subject_id,
                    "pn_dir": f"{BASE_URL}{sub_dir}{rec_folder}/",
                    "rel_pn_dir": f"mimic4wdb/0.1.0/{sub_dir}{rec_folder}/",
                    "record_name": rec_id,
                    "first_seg": first_seg_name,
                    "fs": fs,
                    "num_samples": num_samples,
                    "duration_hrs": round(duration_sec / 3600.0, 2),
                    "start_timestamp": start_iso,
                    "channels": channels,
                    "has_ecg": has_ecg,
                    "has_abp": has_abp,
                    "has_ppg": has_ppg,
                    "tier": tier
                })
            except Exception:
                pass
    except Exception:
        pass
    return records_list

def main():
    print("Fetching RECORDS index from PhysioNet...")
    records_text = fetch_url(BASE_URL + "RECORDS")
    subject_dirs = [line.strip() for line in records_text.strip().split("\n") if line.strip()]
    print(f"Total Subject Directories: {len(subject_dirs)}")
    
    waveform_records = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        futures = {executor.submit(inspect_subject_record, s): s for s in subject_dirs}
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            waveform_records.extend(res)

    df_waves = pd.DataFrame(waveform_records)
    print(f"\nTotal Parsed Records: {len(df_waves)}")
    print(f"Unique Subjects: {df_waves['subject_id'].nunique()}")
    print("\nTier Breakdown:")
    print(df_waves["tier"].value_counts())
    
    # Save parsed records table
    os.makedirs("scratch", exist_ok=True)
    df_waves.to_csv("scratch/all_discovered_mimic_waveforms.csv", index=False)
    print("Saved metadata to scratch/all_discovered_mimic_waveforms.csv")

if __name__ == "__main__":
    main()
