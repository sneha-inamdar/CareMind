import json
import os
import pandas as pd

idx = json.load(open('data/demo_waveforms/records_index.json'))
clin_records = [r for r in idx if 'ECG' not in r.get('available_modalities', [])]
print('Clinical-only records count:', len(clin_records))
for r in clin_records:
    print(r['record_id'], r['subject_id'], r['bed_id'], r['available_modalities'], r.get('windows_count'))

subs = set(r['subject_id'] for r in clin_records)
print('Unique clinical-only subjects:', subs)

icu_dir = r"data\MIMIC_Demo\mimic-iv-clinical-database-demo-2.2\icu"
chartevents_path = os.path.join(icu_dir, "chartevents.csv.gz")

item_map = {
    220045: "HR",
    220277: "SpO2",
    220210: "Resp",
    220179: "SysBP",
    220050: "SysBP",
    220180: "DiaBP",
    220051: "DiaBP",
    220181: "MAP",
    220052: "MAP",
    223761: "TempF",
    223762: "TempC"
}

chunks = []
for chunk in pd.read_csv(chartevents_path, chunksize=50000):
    match = chunk[chunk["subject_id"].isin(subs) & chunk["itemid"].isin(item_map.keys())]
    if len(match) > 0:
        chunks.append(match)

if chunks:
    df = pd.concat(chunks, ignore_index=True)
    df["vital"] = df["itemid"].map(item_map)
    for s in sorted(subs):
        s_df = df[df["subject_id"] == s]
        n_times = s_df["charttime"].nunique() if len(s_df) else 0
        print(f"Subject {s}: {len(s_df)} rows, {n_times} timestamps")
else:
    print("No matches in chartevents")
