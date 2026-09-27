# CareMind Phase 4A — PhysioNet 2019 Data Acquisition & ETL Pipeline Report

> **Clinical & Architectural Disclaimer**: CareMind is an academic research project and clinical decision-support system (CDSS) prototype. It is designed to assist healthcare professionals with multimodal risk estimation and patient prioritization. CareMind is strictly a decision-support tool and is **NOT** a replacement for clinical judgment, medical diagnosis, direct patient evaluation, or primary bedside monitoring equipment.

---

## 1. Milestone Overview & Objectives

Phase 4A establishes a reproducible, validated, patient-level **Data Acquisition & ETL Pipeline** for the **PhysioNet/CinC Challenge 2019 Sepsis Dataset**.

This milestone bridges raw physiological text records into a structured, validated, leakage-free time-series dataset ready for Level 1 individual vital analysis and Level 2 multimodal fusion modeling.

```
RAW PHYSIONET DATA (.psv)
       │
       ▼
┌──────────────┐
│  ACQUISITION │  ► Download / verify patient files into data/physionet2019/raw/
└──────┬───────┘
       │
       ▼
┌──────────────┐
│DATASET LOADER│  ► Parse pipe-delimited text into DataFrames preserving patient_id
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ VALIDATE RAW │  ► Profile raw un-cleaned data (record counts, missingness, raw ranges)
└──────┬───────┘
       │
       ▼
┌──────────────┐
│PATIENT SPLIT │  ► PATIENT SPLIT FIRST (Train 70% / Val 15% / Test 15% on raw data)
└──────┬───────┘
       │
       ▼
┌──────────────┐
│FIT ON TRAIN  │  ► Fit cleaner parameters (cohort medians) ONLY on Training Patients
└──────┬───────┘
       │
       ▼
┌──────────────┐
│CLEAN & IMPUTE│  ► Apply fitted Train medians to clean Train, Val, and Test DataFrames
└──────┬───────┘
       │
       ▼
┌──────────────┐
│TRANSFORMATION│  ► Compute missingness flags, 1h/3h deltas, and 3h rolling stats
└──────┬───────┘
       │
       ▼
┌──────────────┐
│    OUTPUT    │  ► Export train.parquet, val.parquet, test.parquet & metadata.json
└──────────────┘
```

---

## 2. Leakage-Free Architecture & Pipeline Re-ordering

Following code inspection, the pipeline architecture was explicitly refactored to eliminate **Preprocessing Data Leakage**:

1. **Patient Split First**: `PhysioNet2019Splitter` partitions raw patient DataFrames into Train, Validation, and Test sets *before* any imputation statistics are computed.
2. **Train-Only Parameter Fitting**: `PhysioNet2019Cleaner.fit_cohort_medians()` calculates population medians **strictly using training patients**.
3. **Imputation Application**: Validation and Test sets are cleaned and imputed using the pre-fitted Training cohort medians (`is_training=False`), preventing data snooping or validation set leakage.

### Fitted Training Cohort Medians (v1.1.0 Pipeline)
- `HR`: **84.0 bpm**
- `O2Sat`: **98.0 %**
- `Temp`: **37.06 °C**
- `SBP`: **119.0 mmHg**
- `DBP`: **59.0 mmHg**
- `MAP`: **77.0 mmHg**
- `Resp`: **18.0 bpm**
- `EtCO2`: **28.0 mmHg**

---

## 3. Observed Dataset Statistics

The pipeline was executed and validated on the 500-patient PhysioNet 2019 benchmark cohort:

### 3.1 Patient & Row Distributions

- **Total Processed Patients**: `500` unique ICU patients
- **Total Hourly Observations**: `19,278` hourly time steps
- **Mean ICU Stay Duration**: `38.6` hours
- **Median ICU Stay Duration**: `35.0` hours
- **Minimum ICU Stay Duration**: `8` hours
- **Maximum ICU Stay Duration**: `168` hours (7 days)

### 3.2 Sepsis Label Prevalence

- **Overall Patient Sepsis Rate**: `9.00%` (45 positive patients out of 500)
- **Overall Hourly Sepsis Rate**: `2.25%` (433 positive hourly rows out of 19,278)
- **Train Split**: 32 positive sepsis patients (`9.14%`) | 306 positive hourly rows (`2.25%`)
- **Validation Split**: 7 positive sepsis patients (`9.33%`) | 68 positive hourly rows (`2.46%`)
- **Test Split**: 6 positive sepsis patients (`8.00%`) | 59 positive hourly rows (`2.04%`)

### 3.3 Raw Missingness Summary

| Parameter | Missing Count | Missing % | Clinical Note |
| :--- | :---: | :---: | :--- |
| **HR** | 1,605 | 8.33% | Continuous vital telemetry |
| **O2Sat** | 2,436 | 12.64% | Continuous pulse oximetry |
| **Resp** | 2,330 | 12.09% | Continuous respiratory rate |
| **SBP** | 2,982 | 15.47% | Non-invasive / invasive arterial pressure |
| **MAP** | 2,070 | 10.74% | Calculated Mean Arterial Pressure |
| **DBP** | 8,868 | 46.00% | Diastolic Blood Pressure |
| **Temp** | 12,470 | 64.69% | Intermittent nursing temperature checks |
| **EtCO2** | 19,198 | 99.59% | End-tidal CO2 (ventilated sub-population only) |
| **Glucose** | 16,770 | 86.99% | Sporadic lab measurement |
| **WBC** | 17,752 | 92.08% | Daily lab CBC panel |

### 3.4 Raw vs. Cleaned (Post-Clipping) Physiological Parameter Ranges

| Parameter | Raw Min | Raw Max | Cleaned Min | Cleaned Max | Cleaned Mean | Cleaned Std | Cleaned Median |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **HR (bpm)** | 36.0 | 180.0 | **36.0** | **180.0** | 85.60 | 16.93 | 84.0 |
| **O2Sat (%)** | 39.0 | 100.0 | **39.0** | **100.0** | 97.07 | 3.24 | 98.0 |
| **Temp (°C)** | 23.6 | 40.5 | **27.9** | **40.5** | 36.95 | 0.71 | 37.0 |
| **SBP (mmHg)** | 43.0 | 234.5 | **43.0** | **234.5** | 121.01 | 20.89 | 119.0 |
| **MAP (mmHg)** | 20.0 | 294.0 | **20.0** | **219.0** | 79.26 | 14.65 | 77.0 |
| **DBP (mmHg)** | 23.0 | 287.0 | **23.0** | **166.5** | 60.18 | 10.72 | 59.0 |
| **Resp (bpm)** | 3.0 | 55.5 | **4.0** | **55.5** | 18.87 | 5.30 | 18.0 |
| **EtCO2 (mmHg)**| 11.5 | 42.5 | **11.5** | **42.5** | 28.01 | 0.47 | 28.0 |

> **Clipping Audit Note**: Extreme raw recording errors (such as raw $MAP = 294.0\text{ mmHg}$, $DBP = 287.0\text{ mmHg}$, and $Resp = 3.0\text{ bpm}$) were clipped to physiological bounds ($MAP \le 250$, $DBP \le 200$, $Resp \ge 4$) during Stage 5 cleaning.

---

## 4. Key ETL Decisions & Architectural Rationale

1. **Patient Identity Preservation**:
   - `patient_id` is preserved as a top-level column derived directly from source filenames (`p000001`).
   - Unrelated patient records across different datasets are never combined.

2. **Physiological Outlier Clipping**:
   - Implemented via fixed clinical plausibility bounds (`PHYSIOLOGICAL_BOUNDS`). Out-of-bounds values are replaced with `NaN`.

3. **Leakage-Free Imputation Strategy**:
   - **LOCF (Forward Fill)**: Applied per patient up to 12 hours.
   - **Train-Only Cohort Median Fallback**: Applied for remaining initial `NaN` values using medians fitted **strictly from training patients**.
   - **Missingness Flags**: Derived from `raw_df` prior to imputation.

4. **Derived Temporal Feature Extraction**:
   - **Deltas**: 1-hour ($\Delta X_t = X_t - X_{t-1}$) and 3-hour ($\Delta X_t = X_t - X_{t-3}$) rate-of-change features.
   - **Rolling Window Statistics**: Backward-looking 3-hour rolling mean (`rolling_mean_X_3h`) and std (`rolling_std_X_3h`).
   - Original variables remain un-overwritten.

5. **Leakage-Safe Patient-Level Partitioning**:
   - Split ratio: `70% Train` / `15% Validation` / `15% Test`.
   - Stratified by patient-level sepsis outcome.
   - Enforced zero patient overlap (`set(train) & set(val) == ∅`, etc.).
   - Reproducible with fixed random seed (`seed=42`).

---

## 5. Output Data Structure

Processed dataset artifacts are saved under `data/physionet2019/processed/` in Parquet format:

```
data/physionet2019/processed/
├── train.parquet              # 13,623 hourly rows (350 patients)
├── val.parquet                #  2,759 hourly rows (75 patients)
├── test.parquet               #  2,896 hourly rows (75 patients)
└── dataset_metadata.json      # Pipeline metadata, fitted medians, schema & statistics
```

### Partitioning Summary Table

| Split | Patient Count | Row Count | Sepsis Patients (Prevalence) | Positive Hourly Rows (Prevalence) |
| :--- | :---: | :---: | :---: | :---: |
| **Train** | 350 | 13,623 | 32 (9.14%) | 306 (2.25%) |
| **Validation** | 75 | 2,759 | 7 (9.33%) | 68 (2.46%) |
| **Test** | 75 | 2,896 | 6 (8.00%) | 59 (2.04%) |
| **Total** | **500** | **19,278** | **45 (9.00%)** | **433 (2.25%)** |

---

## 6. Automated Test Suite Results

The automated test suite (`tests/test_physionet2019_etl.py`) was executed using `pytest`:

```bash
python -m pytest tests/test_physionet2019_etl.py
```

### Test Results

```text
============================= test session starts =============================
platform win32 -- Python 3.13.5, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\Sneha\Desktop\College sem 5\project\CareMind

tests\test_physionet2019_etl.py .......                                  [100%]

============================== 7 passed in 2.31s ==============================
```

- `test_dataset_loader`: PASSED
- `test_validator_and_profiler`: PASSED
- `test_cleaner_outlier_clipping_and_imputation`: PASSED
- `test_train_only_imputation_fitting`: PASSED (**Verifies Train-only median fitting & prevents validation leakage**)
- `test_feature_transformer`: PASSED
- `test_leakage_safe_patient_splitter`: PASSED
- `test_full_pipeline_execution`: PASSED

---

## 7. Exact Commands to Reproduce Pipeline

### Run Leakage-Free ETL Pipeline (Command Line)

```bash
# Run pipeline with 500 patient benchmark cohort
python run_physionet2019_etl.py --max-patients 500 --seed 42

# Run full dataset pipeline (all 40,336 patients)
python run_physionet2019_etl.py --max-patients 0 --seed 42
```

### Run Automated Test Suite

```bash
python -m pytest tests/test_physionet2019_etl.py
```
