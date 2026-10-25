import os
import json
import pandas as pd

records_path = 'data/demo_waveforms/records_index.json'
with open(records_path) as f:
    records = json.load(f)

waveform_records = [r for r in records if any(m in r.get('available_modalities', []) for m in ['ECG', 'PPG', 'ABP'])]
waveform_subjs = set(r['subject_id'] for r in waveform_records)
print('Waveform subjects:', waveform_subjs)

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
    match = chunk[chunk["subject_id"].isin(waveform_subjs) & chunk["itemid"].isin(item_map.keys())]
    if len(match) > 0:
        chunks.append(match)

if chunks:
    df = pd.concat(chunks, ignore_index=True)
    df["vital"] = df["itemid"].map(item_map)
    print(f"Total matched rows in chartevents for waveform subjects: {len(df)}")
    for s in sorted(waveform_subjs):
        s_df = df[df["subject_id"] == s]
        n_times = s_df["charttime"].nunique() if len(s_df) else 0
        print(f"Subject {s}: {len(s_df)} rows, {n_times} unique timestamps")
else:
    print("No matches in chartevents")
