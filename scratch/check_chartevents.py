import os, gzip
import pandas as pd

icu_dir = r"data\MIMIC_Demo\mimic-iv-clinical-database-demo-2.2\icu"
chartevents_path = os.path.join(icu_dir, "chartevents.csv.gz")
subjects = [10000032, 10001884, 10002013, 10003004, 10003400, 10004555, 10005667, 10019003, 10039708]

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
    match = chunk[chunk["subject_id"].isin(subjects) & chunk["itemid"].isin(item_map.keys())]
    if len(match) > 0:
        chunks.append(match)

if chunks:
    df = pd.concat(chunks, ignore_index=True)
    df["vital"] = df["itemid"].map(item_map)
    print("Found total vital rows in chartevents:", len(df))
    for s in subjects:
        s_df = df[df["subject_id"] == s]
        n_times = s_df["charttime"].nunique()
        print(f"Subject {s}: {len(s_df)} rows, {n_times} unique timestamps")
        if len(s_df) > 0:
            times = s_df["charttime"].drop_duplicates().sort_values().head(6).tolist()
            print(f"   first timestamps: {times}")
            for t in times[:4]:
                t_df = s_df[s_df["charttime"] == t]
                v_dict = dict(zip(t_df["vital"], t_df["valuenum"]))
                print(f"     at {t}: {v_dict}")
else:
    print("No vital rows found!")
