import os, gzip
import pandas as pd

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
    match = chunk[chunk["subject_id"].isin([10000032, 10003400, 10019003, 10039708]) & chunk["itemid"].isin(item_map.keys())]
    if len(match) > 0:
        chunks.append(match)

df = pd.concat(chunks, ignore_index=True)
df["vital"] = df["itemid"].map(item_map)

# Pivot by charttime
for s in [10000032, 10003400, 10019003, 10039708]:
    s_df = df[df["subject_id"] == s].sort_values("charttime")
    piv = s_df.pivot_table(index="charttime", columns="vital", values="valuenum", aggfunc="last")
    # forward fill within patient
    piv = piv.ffill()
    print(f"\n=== Subject {s} (rows: {len(piv)}) ===")
    print(piv.head(10))
