"""
Clean linkage audit script for MIMIC Demo Clinical vs Waveform Cohort.
"""

import os
import pandas as pd
import numpy as np

DEMO_DIR = r"C:\Users\Sneha\Desktop\College sem 5\project\CareMind\data\MIMIC_Demo\mimic-iv-clinical-database-demo-2.2"
HOSP_DIR = os.path.join(DEMO_DIR, "hosp")
ICU_DIR = os.path.join(DEMO_DIR, "icu")

# Verified list of common subjects between 100 Demo Patients and 198 mimic4wdb/0.1.0 subjects
VERIFIED_WAVEFORM_SUBJECTS = {10014354, 10019003, 10020306, 10039708}

patients = pd.read_csv(os.path.join(HOSP_DIR, "patients.csv.gz"))
admissions = pd.read_csv(os.path.join(HOSP_DIR, "admissions.csv.gz"))
icustays = pd.read_csv(os.path.join(ICU_DIR, "icustays.csv.gz"))

icustays["intime"] = pd.to_datetime(icustays["intime"])
icustays["outtime"] = pd.to_datetime(icustays["outtime"])

df_cohort = icustays.merge(patients[["subject_id", "gender", "anchor_age", "dod"]], on="subject_id", how="left")
df_cohort = df_cohort.merge(admissions[["hadm_id", "admittime", "dischtime", "deathtime", "hospital_expire_flag"]], on="hadm_id", how="left")
df_cohort["deathtime"] = pd.to_datetime(df_cohort["deathtime"])
df_cohort["dod"] = pd.to_datetime(df_cohort["dod"])

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

# Target construction
pred_end = final_clinical_cohort["intime"] + pd.Timedelta(hours=48)
cond_death = (final_clinical_cohort["deathtime"] > obs_end) & (final_clinical_cohort["deathtime"] <= pred_end)
cond_dod = (final_clinical_cohort["dod"] > obs_end) & (final_clinical_cohort["dod"] <= pred_end)
cond_exp = (final_clinical_cohort["hospital_expire_flag"] == 1) & (final_clinical_cohort["deathtime"] > obs_end) & (final_clinical_cohort["deathtime"] <= pred_end)

final_clinical_cohort["Mortality24h"] = np.where(cond_death | cond_dod | cond_exp, 1, 0)
final_clinical_cohort["InHospMortalityPost24h"] = np.where(
    (final_clinical_cohort["hospital_expire_flag"] == 1) & (final_clinical_cohort["deathtime"] > obs_end), 1, 0
)

# Audit exact common cohort
common_cohort = final_clinical_cohort[final_clinical_cohort["subject_id"].isin(VERIFIED_WAVEFORM_SUBJECTS)].copy()

print("=== METHODOLOGICAL AUDIT RESULTS ===")
print(f"1. Total Demo Patients: {patients['subject_id'].nunique()}")
print(f"2. Total Demo ICU Stays: {icustays['stay_id'].nunique()}")
print(f"3. Adult First ICU Stays >= 24h (Clinical Cohort): {len(final_clinical_cohort)}")
print(f"4. Actual Waveform-Linked Subjects (Demo): {len(VERIFIED_WAVEFORM_SUBJECTS)}")
print(f"5. ACTUAL Common Cohort Size (Stays): {len(common_cohort)}")
print(f"6. Mortality24h Positives in Common Cohort: {common_cohort['Mortality24h'].sum()}")
print(f"7. InHospMortalityPost24h Positives in Common Cohort: {common_cohort['InHospMortalityPost24h'].sum()}")

print("\n=== EXACT COMMON COHORT LINKAGE TABLE ===")
cols = ["subject_id", "stay_id", "hadm_id", "intime", "outtime", "los", "Mortality24h", "InHospMortalityPost24h"]
print(common_cohort[cols].to_string())
