"""
Exploratory inspection script for MIMIC-IV Clinical Database Demo v2.2.
"""

import os
import gzip
import pandas as pd
import numpy as np

DEMO_DIR = r"C:\Users\Sneha\Desktop\College sem 5\project\CareMind\data\MIMIC_Demo\mimic-iv-clinical-database-demo-2.2"
HOSP_DIR = os.path.join(DEMO_DIR, "hosp")
ICU_DIR = os.path.join(DEMO_DIR, "icu")

print("=== 1. Inspecting File Headers and Columns ===")
for folder_name, folder_path in [("hosp", HOSP_DIR), ("icu", ICU_DIR)]:
    print(f"\n--- Folder: {folder_name} ---")
    for fname in os.listdir(folder_path):
        if fname.endswith(".csv.gz"):
            fpath = os.path.join(folder_path, fname)
            df_head = pd.read_csv(fpath, nrows=2)
            print(f"{fname}: {list(df_head.columns)}")

print("\n=== 2. Inspecting Item IDs in d_items (ICU) ===")
d_items = pd.read_csv(os.path.join(ICU_DIR, "d_items.csv.gz"))
print(f"d_items shape: {d_items.shape}")
print(d_items.head())

vitals_search = ["heart rate", "blood pressure", "spo2", "respiratory rate", "temperature", "o2 saturation"]
for term in vitals_search:
    matches = d_items[d_items["label"].str.contains(term, case=False, na=False)]
    print(f"\nMatches for '{term}':")
    print(matches[["itemid", "label", "abbreviation", "param_type", "unitname"]].to_string())

print("\n=== 3. Inspecting Item IDs in d_labitems (HOSP) ===")
d_labitems = pd.read_csv(os.path.join(HOSP_DIR, "d_labitems.csv.gz"))
print(f"d_labitems shape: {d_labitems.shape}")
print(d_labitems.head())

labs_search = ["lactate", "white blood", "wbc", "creatinine", "ph"]
for term in labs_search:
    matches = d_labitems[d_labitems["label"].str.contains(term, case=False, na=False)]
    print(f"\nMatches for '{term}':")
    print(matches[["itemid", "label", "fluid", "category"]].to_string())
