"""
Targeted verification of Item IDs and exact table schemas for MIMIC-IV demo.
"""

import os
import pandas as pd

DEMO_DIR = r"C:\Users\Sneha\Desktop\College sem 5\project\CareMind\data\MIMIC_Demo\mimic-iv-clinical-database-demo-2.2"
HOSP_DIR = os.path.join(DEMO_DIR, "hosp")
ICU_DIR = os.path.join(DEMO_DIR, "icu")

d_items = pd.read_csv(os.path.join(ICU_DIR, "d_items.csv.gz"))
d_labitems = pd.read_csv(os.path.join(HOSP_DIR, "d_labitems.csv.gz"))

vitals_map = {
    "HR": [220045],
    "SBP": [220050, 220179],
    "DBP": [220051, 220180],
    "MAP": [220052, 220181],
    "SpO2": [220277],
    "Resp": [220210],
    "Temp": [223761, 223762]
}

print("=== VERIFYING VITALS ITEM IDS IN D_ITEMS ===")
for name, ids in vitals_map.items():
    matched = d_items[d_items["itemid"].isin(ids)]
    print(f"\n{name} (ItemIDs {ids}):")
    print(matched[["itemid", "label", "abbreviation", "unitname"]].to_string())

labs_map = {
    "Lactate": [50813, 52442],
    "WBC": [51301, 52257],
    "Creatinine": [50912],
    "Arterial pH": [50820]
}

print("\n=== VERIFYING LABS ITEM IDS IN D_LABITEMS ===")
for name, ids in labs_map.items():
    matched = d_labitems[d_labitems["itemid"].isin(ids)]
    print(f"\n{name} (ItemIDs {ids}):")
    print(matched[["itemid", "label", "fluid", "category"]].to_string())
