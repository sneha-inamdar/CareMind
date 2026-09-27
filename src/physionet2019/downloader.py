"""
PhysioNet 2019 Dataset Downloader & Data Acquisition.
"""

import os
import sys
import random
import numpy as np
import pandas as pd
import concurrent.futures
import urllib.request
from typing import List, Optional

BASE_URL_SET_A = "https://physionet.org/files/challenge-2019/1.0.0/training/training_setA/"
BASE_URL_SET_B = "https://physionet.org/files/challenge-2019/1.0.0/training/training_setB/"

DEFAULT_RAW_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "physionet2019", "raw")
)

PSV_COLUMNS = [
    "HR", "O2Sat", "Temp", "SBP", "MAP", "DBP", "Resp", "EtCO2",
    "BaseExcess", "HCO3", "FiO2", "pH", "PaCO2", "SaO2", "AST", "BUN",
    "Alkalinephos", "Calcium", "Chloride", "Creatinine", "Bilirubin_direct",
    "Glucose", "Lactate", "Magnesium", "Phosphate", "Potassium", "Bilirubin_total",
    "TroponinI", "Hct", "Hgb", "PTT", "WBC", "Fibrinogen", "Platelets",
    "Age", "Gender", "Unit1", "Unit2", "HospAdmTime", "ICULOS", "SepsisLabel"
]


def generate_patient_filenames(set_name: str, count: int) -> List[str]:
    """Generate official PhysioNet 2019 patient filenames."""
    if set_name == "training_setA":
        return [f"p{i:06d}.psv" for i in range(1, min(count, 20336) + 1)]
    elif set_name == "training_setB":
        return [f"p{i:06d}.psv" for i in range(100001, 100001 + min(count, 20000))]
    else:
        raise ValueError(f"Unknown set name: {set_name}")


def _download_single_psv(url: str, dest_path: str) -> bool:
    """Download a single .psv file. Cleans up partial/empty files on failure."""
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
        return True
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "CareMind-ETL/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read()
            if len(content) > 0:
                with open(dest_path, "wb") as f:
                    f.write(content)
                return True
    except Exception:
        pass

    # Cleanup empty file if created
    if os.path.exists(dest_path) and os.path.getsize(dest_path) == 0:
        try:
            os.remove(dest_path)
        except OSError:
            pass
    return False


def generate_synthetic_physionet2019(
    raw_dir: str = DEFAULT_RAW_DIR,
    num_patients_per_set: int = 100,
    seed: int = 42
) -> List[str]:
    """
    Generate synthetic valid PhysioNet 2019 patient files for offline testing / fallback mode.
    """
    np.random.seed(seed)
    random.seed(seed)
    
    extracted_dirs = []
    for set_name in ["training_setA", "training_setB"]:
        set_dir = os.path.join(raw_dir, set_name)
        os.makedirs(set_dir, exist_ok=True)
        extracted_dirs.append(set_dir)
        
        filenames = generate_patient_filenames(set_name, num_patients_per_set)
        for fn in filenames:
            file_path = os.path.join(set_dir, fn)
            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                continue
                
            length = random.randint(12, 72)
            has_sepsis = random.random() < 0.10
            sepsis_onset = random.randint(length // 2, length - 2) if has_sepsis else -1
            
            age = float(random.randint(18, 90))
            gender = float(random.choice([0, 1]))
            unit1 = float(random.choice([0, 1]))
            unit2 = 1.0 - unit1
            hosp_adm_time = -float(random.randint(1, 100))
            
            base_hr = random.uniform(60, 100)
            base_spo2 = random.uniform(94, 99)
            base_temp = random.uniform(36.2, 37.5)
            base_sbp = random.uniform(100, 140)
            base_dbp = random.uniform(60, 90)
            base_resp = random.uniform(12, 20)
            
            hr_series, spo2_series, temp_series = [], [], []
            sbp_series, map_series, dbp_series = [], [], []
            resp_series, sepsis_label = [], []
            
            for t in range(1, length + 1):
                hr = base_hr + np.random.normal(0, 3)
                spo2 = base_spo2 + np.random.normal(0, 1)
                temp = base_temp + np.random.normal(0, 0.2)
                sbp = base_sbp + np.random.normal(0, 5)
                dbp = base_dbp + np.random.normal(0, 4)
                resp = base_resp + np.random.normal(0, 2)
                
                if has_sepsis and t >= sepsis_onset:
                    hr += (t - sepsis_onset) * 1.5
                    temp += (t - sepsis_onset) * 0.1
                    sbp -= (t - sepsis_onset) * 1.2
                    is_sepsis = 1
                else:
                    is_sepsis = 0
                
                hr_val = np.nan if random.random() < 0.15 else max(30.0, min(220.0, round(hr, 1)))
                spo2_val = np.nan if random.random() < 0.15 else max(50.0, min(100.0, round(spo2, 1)))
                temp_val = np.nan if random.random() < 0.30 else max(30.0, min(43.0, round(temp, 2)))
                sbp_val = np.nan if random.random() < 0.20 else max(40.0, min(250.0, round(sbp, 1)))
                dbp_val = np.nan if random.random() < 0.20 else max(20.0, min(150.0, round(dbp, 1)))
                
                if not np.isnan(sbp_val) and not np.isnan(dbp_val):
                    map_val = round(dbp_val + (sbp_val - dbp_val) / 3.0, 1)
                else:
                    map_val = np.nan
                    
                resp_val = np.nan if random.random() < 0.20 else max(5.0, min(60.0, round(resp, 1)))
                
                hr_series.append(hr_val)
                spo2_series.append(spo2_val)
                temp_series.append(temp_val)
                sbp_series.append(sbp_val)
                map_series.append(map_val)
                dbp_series.append(dbp_val)
                resp_series.append(resp_val)
                sepsis_label.append(is_sepsis)

            df_p = pd.DataFrame({
                "HR": hr_series,
                "O2Sat": spo2_series,
                "Temp": temp_series,
                "SBP": sbp_series,
                "MAP": map_series,
                "DBP": dbp_series,
                "Resp": resp_series,
                "EtCO2": [np.nan] * length,
                "BaseExcess": [np.nan] * length,
                "HCO3": [np.nan] * length,
                "FiO2": [np.nan] * length,
                "pH": [np.nan] * length,
                "PaCO2": [np.nan] * length,
                "SaO2": [np.nan] * length,
                "AST": [np.nan] * length,
                "BUN": [np.nan] * length,
                "Alkalinephos": [np.nan] * length,
                "Calcium": [np.nan] * length,
                "Chloride": [np.nan] * length,
                "Creatinine": [np.nan] * length,
                "Bilirubin_direct": [np.nan] * length,
                "Glucose": [np.nan if random.random() < 0.7 else round(random.uniform(70, 180), 1) for _ in range(length)],
                "Lactate": [np.nan] * length,
                "Magnesium": [np.nan] * length,
                "Phosphate": [np.nan] * length,
                "Potassium": [np.nan] * length,
                "Bilirubin_total": [np.nan] * length,
                "TroponinI": [np.nan] * length,
                "Hct": [np.nan] * length,
                "Hgb": [np.nan] * length,
                "PTT": [np.nan] * length,
                "WBC": [np.nan] * length,
                "Fibrinogen": [np.nan] * length,
                "Platelets": [np.nan] * length,
                "Age": [age] * length,
                "Gender": [gender] * length,
                "Unit1": [unit1] * length,
                "Unit2": [unit2] * length,
                "HospAdmTime": [hosp_adm_time] * length,
                "ICULOS": list(range(1, length + 1)),
                "SepsisLabel": sepsis_label
            })
            
            df_p.to_csv(file_path, sep="|", index=False)
            
    print(f"Generated synthetic PhysioNet 2019 dataset ({num_patients_per_set} patients/set) under {raw_dir}.")
    return extracted_dirs


def download_physionet2019(
    raw_dir: str = DEFAULT_RAW_DIR,
    include_set_b: bool = True,
    max_patients_per_set: int = 500,
    num_threads: int = 15,
    force_redownload: bool = False,
    allow_synthetic_fallback: bool = True
) -> List[str]:
    """
    Download PhysioNet 2019 dataset .psv files.
    """
    os.makedirs(raw_dir, exist_ok=True)
    target_sets = [("training_setA", BASE_URL_SET_A, 20336)]
    if include_set_b:
        target_sets.append(("training_setB", BASE_URL_SET_B, 20000))

    extracted_dirs = []

    for set_name, base_url, total_avail in target_sets:
        set_dir = os.path.join(raw_dir, set_name)
        os.makedirs(set_dir, exist_ok=True)
        extracted_dirs.append(set_dir)

        existing_files = [f for f in os.listdir(set_dir) if f.endswith(".psv") and os.path.getsize(os.path.join(set_dir, f)) > 0]
        target_count = min(max_patients_per_set, total_avail)
        if len(existing_files) >= target_count and not force_redownload:
            print(f"Set '{set_name}' already contains {len(existing_files)} valid patient records. Ready.")
            continue

        filenames = generate_patient_filenames(set_name, target_count)
        print(f"Downloading {len(filenames)} patient records for '{set_name}' using {num_threads} workers...")

        success_count = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            future_to_file = {
                executor.submit(_download_single_psv, base_url + fn, os.path.join(set_dir, fn)): fn
                for fn in filenames
            }
            for future in concurrent.futures.as_completed(future_to_file):
                if future.result():
                    success_count += 1

        print(f"Downloaded {success_count}/{len(filenames)} files for {set_name}.")

    return extracted_dirs


if __name__ == "__main__":
    download_physionet2019(max_patients_per_set=500)
