import os
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

subjs = [10014354, 10020306, 10039708]

chunks = []
for chunk in pd.read_csv(chartevents_path, chunksize=50000):
    match = chunk[chunk["subject_id"].isin(subjs) & chunk["itemid"].isin(item_map.keys())]
    if len(match) > 0:
        chunks.append(match[["subject_id", "charttime", "itemid", "valuenum"]])

df = pd.concat(chunks, ignore_index=True)
df["vital"] = df["itemid"].map(item_map)

# Convert TempF to TempC
tempf_mask = df["vital"] == "TempF"
df.loc[tempf_mask, "valuenum"] = (df.loc[tempf_mask, "valuenum"] - 32.0) * 5.0 / 9.0
df.loc[tempf_mask, "vital"] = "Temp"
tempc_mask = df["vital"] == "TempC"
df.loc[tempc_mask, "vital"] = "Temp"

for s in subjs:
    s_df = df[df["subject_id"] == s].sort_values("charttime")
    piv = s_df.pivot_table(index="charttime", columns="vital", values="valuenum", aggfunc="last")
    piv = piv.ffill().bfill()
    print(f"\n=== Subject {s} (total timestamps: {len(piv)}) ===")
    print(piv.head(10))
