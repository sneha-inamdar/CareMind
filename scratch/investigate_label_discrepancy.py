import os
import glob
import pandas as pd
import json

# 1. Read raw PSV files from data/physionet2019/raw/ (or wherever 500 benchmark PSV files are)
raw_dir = 'data/physionet2019/raw'
raw_psv_files = sorted(glob.glob(os.path.join(raw_dir, '**', '*.psv'), recursive=True))

print(f"Total raw PSV files found in {raw_dir}: {len(raw_psv_files)}")

# If raw PSVs are not in raw_dir, let's check how run_physionet2019_etl.py loads them
# Let's inspect run_physionet2019_etl.py or data directory structure
raw_dfs = []
raw_pos_patients = 0
raw_pos_hours = 0
raw_total_hours = 0
raw_patient_stats = []

for fpath in raw_psv_files[:500]:
    pid = os.path.basename(fpath).replace('.psv', '')
    df = pd.read_csv(fpath, sep='|')
    total_h = len(df)
    pos_h = (df['SepsisLabel'] == 1).sum()
    has_sepsis = pos_h > 0
    raw_pos_hours += pos_h
    raw_total_hours += total_h
    if has_sepsis:
        raw_pos_patients += 1
    raw_patient_stats.append({
        'patient_id': pid,
        'total_hours': total_h,
        'pos_hours': pos_h,
        'has_sepsis': has_sepsis
    })

raw_stats_df = pd.DataFrame(raw_patient_stats)

print("\n--- RAW DATASET STATISTICS (First 500 PSV files) ---")
print(f"Total Patients: {len(raw_stats_df)}")
print(f"Total Hourly Rows: {raw_total_hours}")
print(f"Positive Patients (SepsisLabel == 1 at least once): {raw_pos_patients} ({raw_pos_patients/len(raw_stats_df)*100:.2f}%)")
print(f"Positive Hourly Rows (SepsisLabel == 1): {raw_pos_hours} ({raw_pos_hours/raw_total_hours*100:.2f}%)")

# 2. Now check processed parquet files
train_df = pd.read_parquet('data/physionet2019/processed/train.parquet')
val_df = pd.read_parquet('data/physionet2019/processed/val.parquet')
test_df = pd.read_parquet('data/physionet2019/processed/test.parquet')

print("\n--- PROCESSED PARQUET SPLITS STATISTICS ---")
for split_name, sdf in [('Train', train_df), ('Val', val_df), ('Test', test_df)]:
    p_count = sdf['patient_id'].nunique()
    h_count = len(sdf)
    p_sepsis = sdf.groupby('patient_id')['SepsisLabel'].max()
    p_pos_count = (p_sepsis == 1).sum()
    h_pos_count = (sdf['SepsisLabel'] == 1).sum()
    print(f"\n[{split_name} Split]")
    print(f"  Patients: {p_count}")
    print(f"  Hourly Rows: {h_count}")
    print(f"  Positive Patients: {p_pos_count} ({p_pos_count/p_count*100:.2f}%)")
    print(f"  Positive Hourly Rows: {h_pos_count} ({h_pos_count/h_count*100:.2f}%)")

all_proc_df = pd.concat([train_df, val_df, test_df], ignore_index=True)
proc_p_count = all_proc_df['patient_id'].nunique()
proc_h_count = len(all_proc_df)
proc_p_sepsis = all_proc_df.groupby('patient_id')['SepsisLabel'].max()
proc_p_pos_count = (proc_p_sepsis == 1).sum()
proc_h_pos_count = (all_proc_df['SepsisLabel'] == 1).sum()

print("\n--- COMBINED PROCESSED PARQUET STATISTICS ---")
print(f"Total Patients: {proc_p_count}")
print(f"Total Hourly Rows: {proc_h_count}")
print(f"Positive Patients: {proc_p_pos_count} ({proc_p_pos_count/proc_p_count*100:.2f}%)")
print(f"Positive Hourly Rows: {proc_h_pos_count} ({proc_h_pos_count/proc_h_count*100:.2f}%)")

# 3. Check dataset_metadata.json
if os.path.exists('data/physionet2019/processed/dataset_metadata.json'):
    with open('data/physionet2019/processed/dataset_metadata.json') as f:
        meta = json.load(f)
    print("\n--- DATASET METADATA JSON ---")
    print(json.dumps(meta.get('cohort_summary', {}), indent=2))
    print("Split summary in metadata:")
    print(json.dumps(meta.get('split_summary', {}), indent=2))

# 4. Check if raw PSVs evaluated in Phase 4A script were a DIFFERENT set of 500 patients or if there was filtering!
if len(raw_stats_df) > 0 and len(all_proc_df) > 0:
    raw_pids = set(raw_stats_df['patient_id'])
    proc_pids = set(all_proc_df['patient_id'])
    print(f"\nOverlap between raw_psv_files[:500] patient_ids and processed patient_ids: {len(raw_pids.intersection(proc_pids))}")
    if raw_pids != proc_pids:
        print("Raw PSVs set and Processed PSVs set DIFFER!")
        print(f"PIDs in raw but not in processed: {len(raw_pids - proc_pids)}")
        print(f"PIDs in processed but not in raw: {len(proc_pids - raw_pids)}")
