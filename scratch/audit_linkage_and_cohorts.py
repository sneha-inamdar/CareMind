"""
Rigorous Methodological Audit Script for MIMIC Clinical & Waveform Cohort Linkage.
"""

import os
import re
import urllib.request
import pandas as pd
import numpy as np

DEMO_DIR = r"C:\Users\Sneha\Desktop\College sem 5\project\CareMind\data\MIMIC_Demo\mimic-iv-clinical-database-demo-2.2"
HOSP_DIR = os.path.join(DEMO_DIR, "hosp")
ICU_DIR = os.path.join(DEMO_DIR, "icu")
BASE_URL = "https://physionet.org/files/mimic4wdb/0.1.0/"

# Load clinical demo tables
patients = pd.read_csv(os.path.join(HOSP_DIR, "patients.csv.gz"))
admissions = pd.read_csv(os.path.join(HOSP_DIR, "admissions.csv.gz"))
icustays = pd.read_csv(os.path.join(ICU_DIR, "icustays.csv.gz"))

# Build Clinical Cohort
icustays["intime"] = pd.to_datetime(icustays["intime"])
icustays["outtime"] = pd.to_datetime(icustays["outtime"])

df_cohort = icustays.merge(patients[["subject_id", "gender", "anchor_age", "dod"]], on="subject_id", how="left")
df_cohort = df_cohort.merge(admissions[["hadm_id", "admittime", "dischtime", "deathtime", "hospital_expire_flag"]], on="hadm_id", how="left")
df_cohort["deathtime"] = pd.to_datetime(df_cohort["deathtime"])
df_cohort["dod"] = pd.to_datetime(df_cohort["dod"])

# Adult first ICU stays >= 24h surviving initial 24h
df_adult = df_cohort[df_cohort["anchor_age"] >= 18]
first_idx = df_adult.groupby("subject_id")["intime"].idxmin()
df_first = df_adult.loc[first_idx].copy()
df_los24 = df_first[df_first["los"] >= 1.0].copy()
obs_end = df_los24["intime"] + pd.Timedelta(hours=24)

final_clinical_cohort = df_los24[
    (df_los24["outtime"] > obs_end) & 
    (df_los24["deathtime"].isna() | (df_los24["deathtime"] > obs_end)) &
    (df_los24["dod"].isna() | (df_los24["dod"] > obs_end))
].copy()

# Target construction: Mortality24h (24h-48h window)
pred_end = final_clinical_cohort["intime"] + pd.Timedelta(hours=48)
cond_death = (final_clinical_cohort["deathtime"] > obs_end) & (final_clinical_cohort["deathtime"] <= pred_end)
cond_dod = (final_clinical_cohort["dod"] > obs_end) & (final_clinical_cohort["dod"] <= pred_end)
cond_exp = (final_clinical_cohort["hospital_expire_flag"] == 1) & (final_clinical_cohort["deathtime"] > obs_end) & (final_clinical_cohort["deathtime"] <= pred_end)

final_clinical_cohort["Mortality24h"] = np.where(cond_death | cond_dod | cond_exp, 1, 0)
final_clinical_cohort["InHospMortalityPost24h"] = np.where(
    (final_clinical_cohort["hospital_expire_flag"] == 1) & (final_clinical_cohort["deathtime"] > obs_end), 1, 0
)

print("=== 1. CLINICAL DEMO COHORT STATS ===")
print(f"Total Adult First ICU Stays >= 24h (Clinical Cohort): {len(final_clinical_cohort)}")
print(f"Primary Target Mortality24h Positives (24h-48h window): {final_clinical_cohort['Mortality24h'].sum()}")
print(f"Substitute Target InHospMortalityPost24h Positives: {final_clinical_cohort['InHospMortalityPost24h'].sum()}")

# Fetch waveform records list from PhysioNet
req = urllib.request.Request(BASE_URL + "RECORDS", headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req) as resp:
    lines = [l.strip() for l in resp.read().decode("utf-8").strip().split("\n") if l.strip()]

wave_subjects = set()
for l in lines:
    m = re.search(r"p(\d{8})", l)
    if m:
        wave_subjects.add(int(m.group(1)))

clinical_subjects = set(final_clinical_cohort["subject_id"])
matched_subjects = clinical_subjects.intersection(wave_subjects)

print("\n=== 2. LINKAGE AUDIT FINDINGS ===")
print(f"Unique Clinical Demo Cohort Subjects: {len(clinical_subjects)}")
print(f"Unique MIMIC Waveform Database Subjects (mimic4wdb/0.1.0): {len(wave_subjects)}")
print(f"ACTUAL Common Overlapping Subjects: {len(matched_subjects)}")

common_cohort = final_clinical_cohort[final_clinical_cohort["subject_id"].isin(matched_subjects)].copy()
print(f"ACTUAL Common Cohort Size (Stays): {len(common_cohort)}")

print("\n=== 3. LINKAGE TABLE FOR ACTUAL COMMON COHORT STAYS ===")
cols_to_print = ["subject_id", "stay_id", "hadm_id", "intime", "outtime", "los", "Mortality24h", "InHospMortalityPost24h"]
print(common_cohort[cols_to_print].to_string())

print("\n=== 4. AUDIT DISCREPANCY CAUSE ===")
print("Cause of discrepancy: The previous run script generated synthetic mock waveform features")
print("for all 85 clinical stays (using np.random.normal) rather than restricting the Waveform Only")
print("and Multimodal models strictly to patients with verified waveform records.")
