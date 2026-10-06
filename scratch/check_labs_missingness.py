"""
Inspect lab events missingness in initial 24h for demo cohort.
"""

import os
import pandas as pd

DEMO_DIR = r"C:\Users\Sneha\Desktop\College sem 5\project\CareMind\data\MIMIC_Demo\mimic-iv-clinical-database-demo-2.2"
HOSP_DIR = os.path.join(DEMO_DIR, "hosp")
ICU_DIR = os.path.join(DEMO_DIR, "icu")

patients = pd.read_csv(os.path.join(HOSP_DIR, "patients.csv.gz"))
admissions = pd.read_csv(os.path.join(HOSP_DIR, "admissions.csv.gz"))
icustays = pd.read_csv(os.path.join(ICU_DIR, "icustays.csv.gz"))
labevents = pd.read_csv(os.path.join(HOSP_DIR, "labevents.csv.gz"))

icustays["intime"] = pd.to_datetime(icustays["intime"])
icustays["outtime"] = pd.to_datetime(icustays["outtime"])

df_cohort = icustays.merge(patients[["subject_id", "anchor_age", "dod"]], on="subject_id", how="left")
df_cohort = df_cohort.merge(admissions[["hadm_id", "deathtime"]], on="hadm_id", how="left")
df_cohort["deathtime"] = pd.to_datetime(df_cohort["deathtime"])
df_cohort["dod"] = pd.to_datetime(df_cohort["dod"])

df_adult = df_cohort[df_cohort["anchor_age"] >= 18]
first_stays = df_adult.groupby("subject_id")["intime"].idxmin()
df_first = df_adult.loc[first_stays].copy()
df_los24 = df_first[df_first["los"] >= 1.0].copy()
obs_end = df_los24["intime"] + pd.Timedelta(hours=24)

final_cohort = df_los24[
    (df_los24["outtime"] > obs_end) & 
    (df_los24["deathtime"].isna() | (df_los24["deathtime"] > obs_end)) &
    (df_los24["dod"].isna() | (df_los24["dod"] > obs_end))
].copy()

labevents["charttime"] = pd.to_datetime(labevents["charttime"])
cohort_hadms = set(final_cohort["hadm_id"])

lab_cohort = labevents[labevents["hadm_id"].isin(cohort_hadms)].merge(
    final_cohort[["hadm_id", "intime"]], on="hadm_id"
)
lab_cohort["obs_end"] = lab_cohort["intime"] + pd.Timedelta(hours=24)

lab_obs = lab_cohort[(lab_cohort["charttime"] >= lab_cohort["intime"]) & (lab_cohort["charttime"] <= lab_cohort["obs_end"])]

item_to_lab = {
    50813: "Lactate", 52442: "Lactate",
    51301: "WBC",
    50912: "Creatinine",
    50820: "Arterial_pH"
}

lab_obs["lab_name"] = lab_obs["itemid"].map(item_to_lab)
present_labs = lab_obs.dropna(subset=["lab_name"]).groupby("hadm_id")["lab_name"].unique()

print("=== LAB MISSINGNESS IN DEMO COHORT (INITIAL 24H) ===")
for lab in ["Lactate", "WBC", "Creatinine", "Arterial_pH"]:
    count_present = sum(lab in labs for labs in present_labs)
    missing_pct = ((len(final_cohort) - count_present) / len(final_cohort)) * 100
    print(f"  {lab}: {count_present}/{len(final_cohort)} stays present ({round(missing_pct, 2)}% missing)")
