"""
Check exact overlap between all 198 MIMIC-IV Waveform subject directories
and the 100 MIMIC-IV Clinical Demo patients.
"""

import os
import re
import urllib.request
import pandas as pd

DEMO_DIR = r"C:\Users\Sneha\Desktop\College sem 5\project\CareMind\data\MIMIC_Demo\mimic-iv-clinical-database-demo-2.2"
HOSP_DIR = os.path.join(DEMO_DIR, "hosp")
patients = pd.read_csv(os.path.join(HOSP_DIR, "patients.csv.gz"))
demo_subject_ids = set(patients["subject_id"])

BASE_URL = "https://physionet.org/files/mimic4wdb/0.1.0/"

req = urllib.request.Request(BASE_URL + "RECORDS", headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req) as resp:
    lines = [l.strip() for l in resp.read().decode("utf-8").strip().split("\n") if l.strip()]

wave_subject_ids = set()
for l in lines:
    m = re.search(r"p(\d{8})", l)
    if m:
        wave_subject_ids.add(int(m.group(1)))

common_subjects = demo_subject_ids.intersection(wave_subject_ids)

print("=== COHORT LINKAGE ANALYSIS ===")
print(f"Total Demo Patients: {len(demo_subject_ids)}")
print(f"Total Waveform Subjects in mimic4wdb/0.1.0: {len(wave_subject_ids)}")
print(f"Common Subjects between Demo Clinical & Waveform Database: {len(common_subjects)}")
print(f"Common Subject IDs: {sorted(list(common_subjects))}")
