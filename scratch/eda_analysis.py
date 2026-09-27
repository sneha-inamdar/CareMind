import os
import json
import pandas as pd
import numpy as np

# Load processed datasets
train_df = pd.read_parquet('data/physionet2019/processed/train.parquet')
val_df = pd.read_parquet('data/physionet2019/processed/val.parquet')
test_df = pd.read_parquet('data/physionet2019/processed/test.parquet')

all_df = pd.concat([train_df, val_df, test_df], ignore_index=True)

print("=== 1. PATIENT LEVEL STRUCTURE ===")
total_rows = len(all_df)
unique_patients = all_df['patient_id'].nunique()
print(f"Total Rows (Hourly Observations): {total_rows}")
print(f"Unique Patients: {unique_patients}")
print(f"Train patients: {train_df['patient_id'].nunique()}, Val patients: {val_df['patient_id'].nunique()}, Test patients: {test_df['patient_id'].nunique()}")

patient_lengths = all_df.groupby('patient_id')['ICULOS'].count()
print("Patient Record Length (Hours):")
print(f"  Min: {patient_lengths.min()}")
print(f"  Median: {patient_lengths.median()}")
print(f"  Mean: {patient_lengths.mean():.2f}")
print(f"  Max: {patient_lengths.max()}")
print(f"  25th percentile: {patient_lengths.quantile(0.25)}")
print(f"  75th percentile: {patient_lengths.quantile(0.75)}")

print("\n=== 2. SEPSISLABEL ANALYSIS ===")
patient_sepsis = all_df.groupby('patient_id')['SepsisLabel'].max()
pos_patients = (patient_sepsis == 1).sum()
neg_patients = (patient_sepsis == 0).sum()
patient_prevalence = pos_patients / unique_patients * 100

pos_hours = (all_df['SepsisLabel'] == 1).sum()
neg_hours = (all_df['SepsisLabel'] == 0).sum()
hourly_prevalence = pos_hours / total_rows * 100

print(f"Positive Patients: {pos_patients} ({patient_prevalence:.2f}%)")
print(f"Negative Patients: {neg_patients} ({100 - patient_prevalence:.2f}%)")
print(f"Positive Hourly Obs: {pos_hours} ({hourly_prevalence:.2f}%)")
print(f"Negative Hourly Obs: {neg_hours} ({100 - hourly_prevalence:.2f}%)")

# Sepsis onset timing and duration
pos_patient_ids = patient_sepsis[patient_sepsis == 1].index

onset_hours = []
durations = []

for pid in pos_patient_ids:
    pdf = all_df[all_df['patient_id'] == pid].sort_values('ICULOS')
    pos_sub = pdf[pdf['SepsisLabel'] == 1]
    first_pos = pos_sub['ICULOS'].iloc[0]
    duration = len(pos_sub)
    onset_hours.append(first_pos)
    durations.append(duration)

onset_hours = pd.Series(onset_hours)
durations = pd.Series(durations)

print("\nSepsis Onset ICULOS (Hour of first positive label):")
print(f"  Min: {onset_hours.min()}")
print(f"  Median: {onset_hours.median()}")
print(f"  Mean: {onset_hours.mean():.2f}")
print(f"  Max: {onset_hours.max()}")

print("\nPositive Label Duration (Hours per positive patient):")
print(f"  Min: {durations.min()}")
print(f"  Median: {durations.median()}")
print(f"  Mean: {durations.mean():.2f}")
print(f"  Max: {durations.max()}")

print("\n=== 3. MISSINGNESS ANALYSIS ===")
# Raw missingness indicators
missing_cols = [c for c in all_df.columns if c.startswith('is_missing_')]
print("Missingness Indicator Averages (% missing in raw data):")
for mc in sorted(missing_cols):
    var_name = mc.replace('is_missing_', '')
    pct = all_df[mc].mean() * 100
    print(f"  {var_name:12s}: {pct:.2f}%")

# Missingness by patient outcome (Positive vs Negative patients)
all_df['is_pos_patient'] = all_df['patient_id'].isin(pos_patient_ids)

print("\nRaw Missingness Comparison (Positive vs Negative Patients):")
for mc in sorted(missing_cols):
    var_name = mc.replace('is_missing_', '')
    pos_pct = all_df[all_df['is_pos_patient']][mc].mean() * 100
    neg_pct = all_df[~all_df['is_pos_patient']][mc].mean() * 100
    print(f"  {var_name:12s} - Positive Patients: {pos_pct:.2f}%, Negative Patients: {neg_pct:.2f}%")

# Check metadata for lab missingness
with open('data/physionet2019/processed/dataset_metadata.json') as f:
    meta = json.load(f)

print("\nMetadata Raw Missingness for Vitals and Labs:")
for var, mdata in meta['raw_missingness'].items():
    print(f"  {var:15s}: {mdata['missing_percentage']:.2f}%")

print("\n=== 4. PHYSIOLOGICAL DISTRIBUTIONS (Cleaned & Imputed) ===")
vitals = ['HR', 'O2Sat', 'Temp', 'SBP', 'MAP', 'DBP', 'Resp']
for v in vitals:
    s_all = all_df[v]
    s_pos = all_df[all_df['SepsisLabel'] == 1][v]
    s_neg = all_df[all_df['SepsisLabel'] == 0][v]
    print(f"\n{v}:")
    print(f"  All   - Mean: {s_all.mean():.2f}, Std: {s_all.std():.2f}, Median: {s_all.median():.2f}, IQR: [{s_all.quantile(0.25):.2f}, {s_all.quantile(0.75):.2f}]")
    print(f"  Pos   - Mean: {s_pos.mean():.2f}, Std: {s_pos.std():.2f}, Median: {s_pos.median():.2f}, IQR: [{s_pos.quantile(0.25):.2f}, {s_pos.quantile(0.75):.2f}]")
    print(f"  Neg   - Mean: {s_neg.mean():.2f}, Std: {s_neg.std():.2f}, Median: {s_neg.median():.2f}, IQR: [{s_neg.quantile(0.25):.2f}, {s_neg.quantile(0.75):.2f}]")

print("\n=== 5. VARIABLE CORRELATIONS ===")
corr_matrix = all_df[vitals].corr()
print("Correlation Matrix (Vitals):")
print(corr_matrix.round(3))

print("\n=== 6. DEMOGRAPHIC STATISTICS ===")
demo_df = all_df.groupby('patient_id').first()
print(f"Age - Mean: {demo_df['Age'].mean():.2f}, Median: {demo_df['Age'].median():.2f}, Min: {demo_df['Age'].min()}, Max: {demo_df['Age'].max()}")
print(f"Gender - Male (1): {(demo_df['Gender'] == 1).sum()} ({(demo_df['Gender'] == 1).mean()*100:.2f}%), Female (0): {(demo_df['Gender'] == 0).sum()} ({(demo_df['Gender'] == 0).mean()*100:.2f}%)")
