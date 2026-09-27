import os
import glob
import pandas as pd

raw_dir = 'data/physionet2019/raw'
all_files = sorted(glob.glob(os.path.join(raw_dir, '**', '*.psv'), recursive=True))

print(f"Total PSV files in raw dir: {len(all_files)}")

# Sort alphabetically vs sort numerically
alpha_files_500 = all_files[:500]

def analyze_files(files, name):
    total_hours = 0
    pos_hours = 0
    pos_patients = 0
    patient_stats = []
    for f in files:
        pid = os.path.basename(f).replace('.psv', '')
        df = pd.read_csv(f, sep='|')
        th = len(df)
        ph = (df['SepsisLabel'] == 1).sum()
        total_hours += th
        pos_hours += ph
        if ph > 0:
            pos_patients += 1
        patient_stats.append({'pid': pid, 'th': th, 'ph': ph})
    print(f"\n=== {name} ({len(files)} files) ===")
    print(f"Total Hours: {total_hours}")
    print(f"Positive Hours: {pos_hours} ({pos_hours/total_hours*100:.2f}%)")
    print(f"Positive Patients: {pos_patients} ({pos_patients/len(files)*100:.2f}%)")
    return pd.DataFrame(patient_stats)

df_alpha = analyze_files(alpha_files_500, "Alphabetical First 500 Files")

# Also check numeric sorting (p000001, p000002, etc.)
def get_num(fpath):
    base = os.path.basename(fpath).replace('.psv', '')
    digits = ''.join(c for c in base if c.isdigit())
    return int(digits) if digits else 0

num_files = sorted(all_files, key=get_num)
df_num = analyze_files(num_files[:500], "Numerical First 500 Files")

# Check all 954 files
df_all = analyze_files(all_files, "All 954 Files")
