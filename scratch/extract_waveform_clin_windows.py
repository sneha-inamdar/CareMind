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

subjs = [10020306, 10014354, 10039708]

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
    piv.index = pd.to_datetime(piv.index)
    
    # Pick 4 rows at least 15 min apart
    selected = []
    last_t = None
    for t, row in piv.iterrows():
        if last_t is None or (t - last_t).total_seconds() >= 15 * 60:
            hr = row.get("HR")
            sys = row.get("SysBP")
            if pd.notna(hr) and pd.notna(sys):
                v_dict = {
                    "HR": round(float(row.get("HR", 80.0)), 1),
                    "SpO2": round(float(row.get("SpO2", 98.0)), 1),
                    "Resp": round(float(row.get("Resp", 18.0)), 1),
                    "SysBP": round(float(row.get("SysBP", 120.0)), 1),
                    "DiaBP": round(float(row.get("DiaBP", 75.0)), 1),
                    "MAP": round(float(row.get("MAP", 90.0)), 1),
                    "Temp": round(float(row.get("Temp", 37.0)), 1)
                }
                selected.append((t.strftime("%Y-%m-%d %H:%M:%S"), v_dict))
                last_t = t
                if len(selected) == 4:
                    break
    print(f"\n=== Subject {s} (selected {len(selected)} windows) ===")
    for idx, (t_str, v) in enumerate(selected):
        print(f"  Win {idx} ({t_str}): HR={v['HR']}, SpO2={v['SpO2']}, Resp={v['Resp']}, BP={v['SysBP']}/{v['DiaBP']}, MAP={v['MAP']}, Temp={v['Temp']}")
