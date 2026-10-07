"""
Inspect scratch/all_discovered_mimic_waveforms.csv to pick 15 verified MIMIC waveform records
with valid first segments across Tier 1, Tier 2, and Tier 3.
"""
import pandas as pd

df = pd.read_csv("scratch/all_discovered_mimic_waveforms.csv")
print("Total records:", len(df))

# Pick top records per Tier with non-null first_seg
df_valid = df[df["first_seg"].notna() & (df["first_seg"] != "")].copy()
print("Valid segment records:", len(df_valid))

t1 = df_valid[df_valid["tier"] == "Tier 1 (ECG+ABP+PPG)"].head(6)
t2 = df_valid[df_valid["tier"] == "Tier 2 (ECG+PPG)"].head(6)
t3 = df_valid[df_valid["tier"] == "Tier 3 (ECG only)"].head(3)

selected = pd.concat([t1, t2, t3])
print("\nSelected 15 Verified Records:")
cols = ["subject_id", "record_name", "first_seg", "rel_pn_dir", "fs", "duration_hrs", "tier"]
print(selected[cols].to_string())

selected.to_csv("scratch/selected_15_mimic_records.csv", index=False)
