"""
Fast concurrent inspection script for MIMIC-IV Waveform Database (mimic4wdb/0.1.0).
"""

import urllib.request
import re
import concurrent.futures
from typing import Dict, List, Any

BASE_URL = "https://physionet.org/files/mimic4wdb/0.1.0/"

def fetch_url(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp:
        return resp.read().decode("utf-8")

def process_subject(sub_dir: str) -> List[Dict[str, Any]]:
    subj_match = re.search(r"p(\d{8})", sub_dir)
    subject_id = int(subj_match.group(1)) if subj_match else None
    
    results = []
    try:
        sub_records_text = fetch_url(BASE_URL + sub_dir + "RECORDS")
        rec_names = [r.strip() for r in sub_records_text.strip().split("\n") if r.strip()]
        
        for rec_name in rec_names:
            # Main segment header vs layout header
            hea_url = BASE_URL + sub_dir + rec_name + ".hea"
            try:
                hea_text = fetch_url(hea_url)
                lines = [l.strip() for l in hea_text.strip().split("\n") if l.strip()]
                if not lines:
                    continue
                
                first_parts = lines[0].split()
                rec_id = first_parts[0]
                num_signals = int(first_parts[1]) if len(first_parts) > 1 else 0
                fs = float(first_parts[2]) if len(first_parts) > 2 else 0.0
                num_samples = int(first_parts[3]) if len(first_parts) > 3 else 0
                base_time = first_parts[4] if len(first_parts) > 4 else ""
                base_date = first_parts[5] if len(first_parts) > 5 else ""
                
                channels = []
                for line in lines[1:]:
                    if not line.startswith("#"):
                        parts = line.split()
                        if len(parts) >= 9:
                            sig_name = parts[-1]
                            channels.append(sig_name)
                
                has_ecg = any(c.upper() in ["II", "V", "ECG", "I", "III", "AVR", "AVL", "AVF"] for c in channels)
                has_abp = any(c.upper() in ["ABP", "ART", "BP"] for c in channels)
                has_ppg = any(c.upper() in ["PLETH", "PPG", "SPO2"] for c in channels)
                
                duration_sec = (num_samples / fs) if fs > 0 else 0.0
                duration_hrs = duration_sec / 3600.0
                
                results.append({
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
            except Exception:
                pass
    except Exception:
        pass
    return results

def main():
    print("=== 1. FETCHING SUBJECT DIRECTORIES ===")
    records_text = fetch_url(BASE_URL + "RECORDS")
    subject_dirs = [line.strip() for line in records_text.strip().split("\n") if line.strip()]
    print(f"Total Subject Directories in mimic4wdb/0.1.0: {len(subject_dirs)}")

    # Process first 50 subject directories concurrently
    subset_dirs = subject_dirs[:50]
    print(f"Inspecting first {len(subset_dirs)} subject directories with 10 threads...")
    
    all_results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(process_subject, s): s for s in subset_dirs}
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            all_results.extend(res)

    print("\n=== 2. RECORD INVENTORY SUMMARY ===")
    total_recs = len(all_results)
    print(f"Total Waveform Records Parsed: {total_recs}")

    ecg_cnt = sum(1 for r in all_results if r["has_ecg"])
    abp_cnt = sum(1 for r in all_results if r["has_abp"])
    ppg_cnt = sum(1 for r in all_results if r["has_ppg"])

    tier1_cnt = sum(1 for r in all_results if r["has_ecg"] and r["has_abp"] and r["has_ppg"])
    tier2_cnt = sum(1 for r in all_results if r["has_ecg"] and r["has_ppg"])
    tier3_cnt = sum(1 for r in all_results if r["has_ecg"])

    print(f"ECG Available: {ecg_cnt} / {total_recs} ({round(ecg_cnt/total_recs*100, 1) if total_recs else 0}%)")
    print(f"ABP Available: {abp_cnt} / {total_recs} ({round(abp_cnt/total_recs*100, 1) if total_recs else 0}%)")
    print(f"PPG Available: {ppg_cnt} / {total_recs} ({round(ppg_cnt/total_recs*100, 1) if total_recs else 0}%)")
    print(f"Tier 1 (ECG + ABP + PPG): {tier1_cnt} / {total_recs} ({round(tier1_cnt/total_recs*100, 1) if total_recs else 0}%)")
    print(f"Tier 2 (ECG + PPG): {tier2_cnt} / {total_recs} ({round(tier2_cnt/total_recs*100, 1) if total_recs else 0}%)")
    print(f"Tier 3 (ECG only): {tier3_cnt} / {total_recs} ({round(tier3_cnt/total_recs*100, 1) if total_recs else 0}%)")

    print("\n=== 3. SAMPLE RECORD HEADERS ===")
    for r in all_results[:5]:
        print(f"Subject {r['subject_id']} | Rec: {r['rec_name']} | Fs: {r['fs']} Hz | Dur: {r['duration_hrs']} h | Channels: {r['channels']}")

if __name__ == "__main__":
    main()
