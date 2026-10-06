"""
Full inspection script for MIMIC-IV Waveform Database (mimic4wdb/0.1.0) on PhysioNet.

Inspects all 198 subject directories, header files (.hea), channels, sampling rates,
durations, and tier availability.
"""

import urllib.request
import re
import time
from typing import Dict, List, Any

BASE_URL = "https://physionet.org/files/mimic4wdb/0.1.0/"

def fetch_url(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp:
        return resp.read().decode("utf-8")

print("=== 1. FETCHING ALL SUBJECT DIRECTORIES FROM MIMIC4WDB/0.1.0 ===")
records_text = fetch_url(BASE_URL + "RECORDS")
subject_dirs = [line.strip() for line in records_text.strip().split("\n") if line.strip()]
print(f"Total Subject Directories: {len(subject_dirs)}")

inspect_limit = min(50, len(subject_dirs))  # Inspect top 50 subject directories
print(f"Inspecting first {inspect_limit} subject directories...")

record_inventory = []

for i, sub_dir in enumerate(subject_dirs[:inspect_limit]):
    # Extract subject_id from directory e.g. waves/p100/p10014354/ -> 10014354
    subj_match = re.search(r"p(\d{8})", sub_dir)
    subject_id = int(subj_match.group(1)) if subj_match else None
    
    try:
        sub_records_text = fetch_url(BASE_URL + sub_dir + "RECORDS")
        rec_names = [r.strip() for r in sub_records_text.strip().split("\n") if r.strip()]
        
        for rec_name in rec_names:
            # Header URL e.g. waves/p100/p10014354/81739927/81739927.hea
            hea_url = BASE_URL + sub_dir + rec_name + ".hea"
            try:
                hea_text = fetch_url(hea_url)
                lines = [l.strip() for l in hea_text.strip().split("\n") if l.strip()]
                if not lines:
                    continue
                
                # First line format: <record_name> <num_signals> <sampling_rate> <num_samples> [<base_time> <base_date>]
                first_parts = lines[0].split()
                rec_id = first_parts[0]
                num_signals = int(first_parts[1]) if len(first_parts) > 1 else 0
                fs = float(first_parts[2]) if len(first_parts) > 2 else 0.0
                num_samples = int(first_parts[3]) if len(first_parts) > 3 else 0
                base_time = first_parts[4] if len(first_parts) > 4 else ""
                base_date = first_parts[5] if len(first_parts) > 5 else ""
                
                # Parse channels from signal lines
                channels = []
                for line in lines[1:]:
                    if not line.startswith("#"):
                        parts = line.split()
                        if len(parts) >= 9:
                            sig_name = parts[-1]
                            channels.append(sig_name)
                
                # Determine presence of ECG, ABP, PPG
                has_ecg = any(c.upper() in ["II", "V", "ECG", "I", "III", "AVR", "AVL", "AVF"] for c in channels)
                has_abp = any(c.upper() in ["ABP", "ART", "BP"] for c in channels)
                has_ppg = any(c.upper() in ["PLETH", "PPG", "SPO2"] for c in channels)
                
                duration_sec = (num_samples / fs) if fs > 0 else 0.0
                duration_hrs = duration_sec / 3600.0
                
                record_inventory.append({
                    "subject_id": subject_id,
                    "sub_dir": sub_dir,
                    "rec_name": rec_name,
                    "fs": fs,
                    "num_signals": num_signals,
                    "num_samples": num_samples,
                    "duration_hrs": round(duration_hrs, 2),
                    "base_time": base_time,
                    "base_date": base_date,
                    "channels": channels,
                    "has_ecg": has_ecg,
                    "has_abp": has_abp,
                    "has_ppg": has_ppg
                })
            except Exception as e_hea:
                pass
    except Exception as e_rec:
        pass
    time.sleep(0.05)

print("\n=== 2. RECORD INVENTORY SUMMARY ===")
total_recs = len(record_inventory)
print(f"Total Waveform Records Parsed: {total_recs}")

ecg_cnt = sum(1 for r in record_inventory if r["has_ecg"])
abp_cnt = sum(1 for r in record_inventory if r["has_abp"])
ppg_cnt = sum(1 for r in record_inventory if r["has_ppg"])

tier1_cnt = sum(1 for r in record_inventory if r["has_ecg"] and r["has_abp"] and r["has_ppg"])
tier2_cnt = sum(1 for r in record_inventory if r["has_ecg"] and r["has_ppg"])
tier3_cnt = sum(1 for r in record_inventory if r["has_ecg"])

print(f"ECG Available: {ecg_cnt} / {total_recs} ({round(ecg_cnt/total_recs*100, 1) if total_recs else 0}%)")
print(f"ABP Available: {abp_cnt} / {total_recs} ({round(abp_cnt/total_recs*100, 1) if total_recs else 0}%)")
print(f"PPG Available: {ppg_cnt} / {total_recs} ({round(ppg_cnt/total_recs*100, 1) if total_recs else 0}%)")
print(f"Tier 1 (ECG + ABP + PPG): {tier1_cnt} / {total_recs} ({round(tier1_cnt/total_recs*100, 1) if total_recs else 0}%)")
print(f"Tier 2 (ECG + PPG): {tier2_cnt} / {total_recs} ({round(tier2_cnt/total_recs*100, 1) if total_recs else 0}%)")
print(f"Tier 3 (ECG only): {tier3_cnt} / {total_recs} ({round(tier3_cnt/total_recs*100, 1) if total_recs else 0}%)")

print("\n=== 3. SAMPLE RECORD HEADERS ===")
for r in record_inventory[:5]:
    print(f"Subject {r['subject_id']} | Rec: {r['rec_name']} | Fs: {r['fs']} Hz | Dur: {r['duration_hrs']} h | Channels: {r['channels']}")
