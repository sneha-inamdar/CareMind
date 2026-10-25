import os, gzip, json
import pandas as pd
import numpy as np

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

target_subjects = [10000032, 10003400, 10019003, 10039708, 10002428, 10005817, 10007818, 10020740, 10016742]

chunks = []
for chunk in pd.read_csv(chartevents_path, chunksize=50000):
    match = chunk[chunk["subject_id"].isin(target_subjects) & chunk["itemid"].isin(item_map.keys())]
    if len(match) > 0:
        chunks.append(match[["subject_id", "charttime", "itemid", "valuenum"]])

df = pd.concat(chunks, ignore_index=True)
df["vital"] = df["itemid"].map(item_map)

# For TempF convert to TempC
tempf_mask = df["vital"] == "TempF"
df.loc[tempf_mask, "valuenum"] = (df.loc[tempf_mask, "valuenum"] - 32.0) * 5.0 / 9.0
df.loc[tempf_mask, "vital"] = "Temp"
tempc_mask = df["vital"] == "TempC"
df.loc[tempc_mask, "vital"] = "Temp"

for s in target_subjects:
    s_df = df[df["subject_id"] == s].sort_values("charttime")
    piv = s_df.pivot_table(index="charttime", columns="vital", values="valuenum", aggfunc="last")
    piv = piv.ffill().bfill()
    # Filter rows that have at least HR, Resp, SysBP
    valid_rows = piv.dropna(subset=["HR", "Resp", "SysBP"])
    print(f"\nSubject {s}: {len(valid_rows)} valid observation rows")
    if len(valid_rows) >= 4:
        # Pick 4 sequential rows spaced nicely (or consecutive non-identical rows)
        distinct_rows = []
        last_hr = None
        for t, row in valid_rows.iterrows():
            if last_hr is None or abs(row["HR"] - last_hr) >= 1.0 or len(distinct_rows) < 4:
                distinct_rows.append((t, row.to_dict()))
                last_hr = row["HR"]
            if len(distinct_rows) == 4:
                break
        for idx, (t, r) in enumerate(distinct_rows):
            print(f"  Win {idx} ({t}): HR={r.get('HR'):.0f}, SpO2={r.get('SpO2', 98):.0f}, Resp={r.get('Resp'):.0f}, SysBP={r.get('SysBP'):.0f}, DiaBP={r.get('DiaBP', 70):.0f}, MAP={r.get('MAP', 80):.0f}, Temp={r.get('Temp', 37.0):.1f}")
