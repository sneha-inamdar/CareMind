"""
Cohort selection, Mortality24h target construction, missingness analysis,
and zero-leakage audit on MIMIC-IV Clinical Database Demo v2.2.
"""

import os
import pandas as pd
import numpy as np

DEMO_DIR = r"C:\Users\Sneha\Desktop\College sem 5\project\CareMind\data\MIMIC_Demo\mimic-iv-clinical-database-demo-2.2"
HOSP_DIR = os.path.join(DEMO_DIR, "hosp")
ICU_DIR = os.path.join(DEMO_DIR, "icu")

# Load tables
patients = pd.read_csv(os.path.join(HOSP_DIR, "patients.csv.gz"))
admissions = pd.read_csv(os.path.join(HOSP_DIR, "admissions.csv.gz"))
icustays = pd.read_csv(os.path.join(ICU_DIR, "icustays.csv.gz"))
chartevents = pd.read_csv(os.path.join(ICU_DIR, "chartevents.csv.gz"))
labevents = pd.read_csv(os.path.join(HOSP_DIR, "labevents.csv.gz"))

print("=== 1. DEMO DATASET OVERVIEW ===")
num_demo_patients = patients["subject_id"].nunique()
num_admissions = admissions["hadm_id"].nunique()
num_icu_stays = icustays["stay_id"].nunique()
print(f"Total Demo Patients: {num_demo_patients}")
print(f"Total Admissions: {num_admissions}")
print(f"Total ICU Stays: {num_icu_stays}")

# Merge cohort information
icustays["intime"] = pd.to_datetime(icustays["intime"])
icustays["outtime"] = pd.to_datetime(icustays["outtime"])

# Merge patients age and death date
df_cohort = icustays.merge(patients[["subject_id", "gender", "anchor_age", "dod"]], on="subject_id", how="left")
# Merge admissions death time and expire flag
df_cohort = df_cohort.merge(
    admissions[["hadm_id", "admittime", "dischtime", "deathtime", "hospital_expire_flag"]],
    on="hadm_id",
    how="left"
)

df_cohort["admittime"] = pd.to_datetime(df_cohort["admittime"])
df_cohort["dischtime"] = pd.to_datetime(df_cohort["dischtime"])
df_cohort["deathtime"] = pd.to_datetime(df_cohort["deathtime"])
df_cohort["dod"] = pd.to_datetime(df_cohort["dod"])

print("\n=== 2. STEP-BY-STEP COHORT SELECTION FILTERING ===")
print(f"Initial ICU stays: {len(df_cohort)}")

# Step A: Adult stays (anchor_age >= 18)
df_adult = df_cohort[df_cohort["anchor_age"] >= 18]
print(f"Step A: Adult stays (anchor_age >= 18): {len(df_adult)}")

# Step B: First ICU stay per patient
first_stays = df_adult.groupby("subject_id")["intime"].idxmin()
df_first = df_adult.loc[first_stays].copy()
print(f"Step B: First ICU stay per patient: {len(df_first)}")

# Step C: ICU LOS >= 24h (los >= 1.0 day)
df_los24 = df_first[df_first["los"] >= 1.0].copy()
print(f"Step C: ICU LOS >= 24 hours (los >= 1.0 day): {len(df_los24)}")

# Step D: Survived initial 24 hours of ICU stay
# Patient must not have deathtime <= intime + 24h OR outtime <= intime + 24h
obs_end = df_los24["intime"] + pd.Timedelta(hours=24)
df_surv24 = df_los24[
    (df_los24["outtime"] > obs_end) & 
    (df_los24["deathtime"].isna() | (df_los24["deathtime"] > obs_end)) &
    (df_los24["dod"].isna() | (df_los24["dod"] > obs_end))
].copy()
print(f"Step D: Survived complete initial 24h observation period: {len(df_surv24)}")

final_cohort = df_surv24.copy()
print(f"\nFinal Preliminary Cohort Count: {len(final_cohort)}")

print("\n=== 3. MORTALITY24H TARGET CONSTRUCTION ===")
# Prediction window: (intime + 24h, intime + 48h]
pred_end = final_cohort["intime"] + pd.Timedelta(hours=48)
obs_end = final_cohort["intime"] + pd.Timedelta(hours=24)

# Death during (intime + 24h, intime + 48h] or hospital expire in that window
cond_death_deathtime = (final_cohort["deathtime"] > obs_end) & (final_cohort["deathtime"] <= pred_end)
cond_death_dod = (final_cohort["dod"] > obs_end) & (final_cohort["dod"] <= pred_end)
cond_expire_window = (final_cohort["hospital_expire_flag"] == 1) & (final_cohort["deathtime"] > obs_end) & (final_cohort["deathtime"] <= pred_end)

final_cohort["Mortality24h"] = np.where(cond_death_deathtime | cond_death_dod | cond_expire_window, 1, 0)

target_counts = final_cohort["Mortality24h"].value_counts().to_dict()
print(f"Mortality24h Target Distribution in Demo Cohort:")
print(f"  Mortality24h = 0 (Survived 24-48h window): {target_counts.get(0, 0)}")
print(f"  Mortality24h = 1 (Died in 24-48h window): {target_counts.get(1, 0)}")

# Also check total in-hospital mortality post 24h
final_cohort["InHospMortalityPost24h"] = np.where(
    (final_cohort["hospital_expire_flag"] == 1) & (final_cohort["deathtime"] > obs_end), 1, 0
)
print(f"Overall In-Hospital Mortality Post-24h: {final_cohort['InHospMortalityPost24h'].value_counts().to_dict()}")

print("\n=== 4. LEAKAGE AUDIT & FEATURE EXTRACTION TEST ===")
# Check chartevents and labevents for cohort stays restricted to <= intime + 24h
chartevents["charttime"] = pd.to_datetime(chartevents["charttime"])
labevents["charttime"] = pd.to_datetime(labevents["charttime"])

vitals_itemids = [220045, 220050, 220179, 220051, 220180, 220052, 220181, 220277, 220210, 223761, 223762]
labs_itemids = [50813, 52442, 51301, 50912, 50820]

cohort_stays = set(final_cohort["stay_id"])
cohort_hadms = set(final_cohort["hadm_id"])

chart_cohort = chartevents[chartevents["stay_id"].isin(cohort_stays)].copy()
lab_cohort = labevents[labevents["hadm_id"].isin(cohort_hadms)].copy()

# Join intime to filter charttime <= intime + 24h
chart_merged = chart_cohort.merge(final_cohort[["stay_id", "intime"]], on="stay_id")
chart_merged["obs_end"] = chart_merged["intime"] + pd.Timedelta(hours=24)

# Filter <= obs_end AND >= intime
chart_obs = chart_merged[(chart_merged["charttime"] >= chart_merged["intime"]) & (chart_merged["charttime"] <= chart_merged["obs_end"])]

print(f"Total Chart Events for Cohort Stays: {len(chart_cohort)}")
print(f"Chart Events in [intime, intime+24h] window: {len(chart_obs)}")
print(f"Filtered out future events (> intime+24h): {len(chart_cohort) - len(chart_obs)}")

# Check missingness across the 7 vitals in [intime, intime+24h]
item_to_vital = {
    220045: "HR",
    220050: "SBP", 220179: "SBP",
    220051: "DBP", 220180: "DBP",
    220052: "MAP", 220181: "MAP",
    220277: "SpO2",
    220210: "Resp",
    223761: "Temp", 223762: "Temp"
}

chart_obs["vital_name"] = chart_obs["itemid"].map(item_to_vital)
present_vitals = chart_obs.groupby("stay_id")["vital_name"].unique()

missingness = {}
for vital in ["HR", "SBP", "DBP", "MAP", "SpO2", "Resp", "Temp"]:
    count_present = sum(vital in vitals for vitals in present_vitals)
    missing_pct = ((len(final_cohort) - count_present) / len(final_cohort)) * 100
    missingness[vital] = {"present_stays": count_present, "missing_pct": round(missing_pct, 2)}

print("\n=== 5. VITAL MISSINGNESS IN DEMO COHORT (INITIAL 24H) ===")
for v, stats in missingness.items():
    print(f"  {v}: {stats['present_stays']}/{len(final_cohort)} stays present ({stats['missing_pct']}% missing)")

print("\n=== 6. REPRESENTATIVE SAMPLE EXTRACTED VITAL RECORDS ===")
print(chart_obs[["stay_id", "charttime", "vital_name", "valuenum", "valueuom"]].head(10).to_string())
