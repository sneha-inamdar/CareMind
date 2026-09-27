# CareMind — Phase 4B: PhysioNet 2019 EDA & Dataset Characterization Report

## 1. Objective

The primary objective of **Phase 4B** is to perform a rigorous, dataset-wide Exploratory Data Analysis (EDA) and characterization of the **PhysioNet/CinC Challenge 2019** dataset. Following the successful completion and verification of the zero-leakage ETL pipeline in **Phase 4A**, this phase establishes empirical understanding of ICU physiological dynamics, measurement availability, temporal label behaviors, and cross-variable interactions.

### Strict Scope Boundaries & Governance Rules
* **No Model Training:** No machine learning, deep learning, or heuristic classifier training is conducted in this phase.
* **No Multimodal Fusion Yet:** Integration between discrete ICU vitals and high-frequency ECG continuous waveforms is deferred to designated downstream phases.
* **Target Isolation:** PhysioNet 2019's `SepsisLabel` is used **exclusively** for a dedicated temporal sepsis-risk prediction experiment. It is **NOT** interpreted as a universal CareMind ICU risk label, nor does it define general critical deterioration across all disease etiologies.
* **Dataset Separation:** PhysioNet 2019 and MIMIC-IV remain completely separate datasets. Unrelated patient records across datasets are never merged.

---

## 2. Dataset Structure

PhysioNet 2019 comprises clinical records from ICU patients across two distinct hospital databases (Set A and Set B). Each patient record is stored as a pipe-separated value (`.psv`) file, where each row represents a 1-hour temporal observation window during the patient's ICU stay.

### Physical Column Composition (40 Variables)
1. **Vital Signs (8):** Heart Rate (`HR`), Pulse Oximetry (`O2Sat`), Temperature (`Temp`), Systolic Blood Pressure (`SBP`), Mean Arterial Pressure (`MAP`), Diastolic Blood Pressure (`DBP`), Respiration Rate (`Resp`), End-tidal Carbon Dioxide (`EtCO2`).
2. **Laboratory Values (26):** `BaseExcess`, `HCO3`, `FiO2`, `pH`, `PaCO2`, `SaO2`, `AST`, `BUN`, `Alkalinephos`, `Calcium`, `Chloride`, `Creatinine`, `Bilirubin_direct`, `Glucose`, `Lactate`, `Magnesium`, `Phosphate`, `Potassium`, `Bilirubin_total`, `TroponinI`, `Hct`, `Hgb`, `PTT`, `WBC`, `Fibrinogen`, `Platelets`.
3. **Demographics & Operational Metadata (6):** `Age`, `Gender`, `Unit1` (MICU indicator), `Unit2` (SICU indicator), `HospAdmTime` (hours prior to ICU admission), `ICULOS` (ICU length of stay in hours).
4. **Target (1):** `SepsisLabel` (binary indicator for clinical sepsis onset).

### Validated Benchmark Cohort (500 Patients)
For rigorous exploratory analysis and pipeline verification, the Phase 4A leak-free ETL pipeline processed a benchmark cohort of 500 patients:
* **Total Hourly Observations:** 19,278 rows.
* **Data Splits (70 / 15 / 15 Patient-Level Split):**
  * **Train Set:** 350 patients (13,623 hourly rows).
  * **Validation Set:** 75 patients (2,759 hourly rows).
  * **Test Set:** 75 patients (2,896 hourly rows).

---

## 3. Patient-Level Statistics

Characterization of patient stay lengths and demographics across the 500-patient cohort reveals significant temporal variability:

| Parameter | Min | 25th Percentile | Median | Mean | 75th Percentile | Max |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **ICU Stay Length (`ICULOS`, Hours)** | 8.0 | 24.0 | 39.0 | 38.56 | 48.0 | 258.0 |
| **Patient Age (Years)** | 18.85 | 51.20 | 63.71 | 61.50 | 73.40 | 100.0 |
| **Hospital Pre-ICU Time (`HospAdmTime`, Hours)** | -0.02 | -48.20 | -4.80 | -54.12 | -0.05 | -0.01 |

### Demographic Breakdown
* **Gender Distribution:** 313 Male patients (62.60%), 187 Female patients (37.40%).
* **ICU Unit Type:** Unit1 (MICU) = 45.16% non-null observations; Unit2 (SICU) = 45.16% non-null observations.

---

## 4. SepsisLabel Analysis

`SepsisLabel` in PhysioNet 2019 follows a specific clinical annotation rule: when clinical sepsis criteria (SIRS + organ dysfunction evidenced by SOFA drop) are met at hour $t$, `SepsisLabel` is set to $1$ starting 6 hours prior to $t$ ($t - 6$) and remains $1$ until 9 hours after $t$ ($t + 9$) or ICU discharge.

### Prevalence Statistics (500-Patient Cohort)
* **Patient-Level Prevalence:** 45 positive patients out of 500 (**9.00%**).
* **Hourly Observation Prevalence:** 433 positive hourly rows out of 19,278 (**2.25%**).
* **Non-Sepsis Cohort:** 455 patients (**91.00%**) and 18,845 hourly rows (**97.75%**).

```
Sepsis Imbalance (500 Patients)
───────────────────────────────────────────────────────────
Patients:     [████ 9.0% Positive ] [████████████████████████████ 91.0% Negative]
Hourly Rows:  [█ 2.25% Positive  ] [████████████████████████████ 97.75% Negative]
```

### Onset Timing and Label Duration
* **Hour of First Sepsis Onset (`ICULOS`):** Min = 1h, Median = 35.0h, Mean = 51.89h, Max = 249.0h.
* **Positive Label Window Duration per Patient:** Min = 8h, Median = 10.0h, Mean = 9.62h, Max = 10h.
* **Transition Pattern:** Sharp $0 \rightarrow 1$ step transition. Once set to $1$, the label remains $1$ for the duration of the window (up to 10 consecutive hours in our cohort).

> [!IMPORTANT]
> **Research Interpretation:** `SepsisLabel` is a dedicated target for early temporal sepsis detection under PhysioNet 2019 challenge rules. It cannot be generalized to mean generic ICU deterioration, cardiac arrest, respiratory failure, or a universal patient risk score.

---

## 5. Missingness Analysis

ICU data is recorded asynchronously based on clinical necessity. Vitals monitored via continuous bedside units are recorded hourly, whereas intermittent measurements (e.g., core temperature) and blood lab tests are drawn sporadically.

### Raw Missingness Taxonomy (Before Imputation)

```
Missingness Spectrum (% Missing across 19,278 hourly rows)
┌──────────────────────────────┬────────────────────────┬───────────┐
│ Feature Category             │ Variables              │ Missing % │
├──────────────────────────────┼────────────────────────┼───────────┤
│ Common Vitals (< 16%)        │ HR                     │   8.33%   │
│                              │ MAP                    │  10.74%   │
│                              │ Resp                   │  12.09%   │
│                              │ O2Sat                  │  12.64%   │
│                              │ SBP                    │  15.47%   │
├──────────────────────────────┼────────────────────────┼───────────┤
│ Intermittent Vitals (30-70%) │ DBP                    │  46.00%   │
│                              │ Temp                   │  64.69%   │
├──────────────────────────────┼────────────────────────┼───────────┤
│ Sparse Labs (> 85%)          │ FiO2                   │  86.16%   │
│                              │ Glucose                │  86.99%   │
│                              │ pH                     │  87.57%   │
│                              │ WBC                    │  92.08%   │
│                              │ Platelets              │  93.31%   │
│                              │ Creatinine             │  93.39%   │
│                              │ Lactate                │  95.95%   │
│                              │ TroponinI              │  99.75%   │
│                              │ EtCO2                  │  99.59%   │
└──────────────────────────────┴────────────────────────┴───────────┘
```

### Missingness Stratified by Sepsis Outcome
Comparing raw missingness rates between patients who developed sepsis vs. non-septic patients reveals informative clinical monitoring bias:

| Variable | Sepsis Patients Missing % | Non-Sepsis Patients Missing % | Clinical Interpretation |
| :--- | :---: | :---: | :--- |
| **DBP** | **33.70%** | **48.00%** | More frequent invasively monitored blood pressure in septic patients. |
| **HR** | **7.87%** | **8.40%** | Consistently high charting for both groups. |
| **O2Sat** | **10.24%** | **13.02%** | Slightly higher monitoring frequency in septic patients. |
| **Resp** | **18.34%** | **11.07%** | Slightly higher missingness due to unrecorded manual breaths. |
| **SBP** | **19.67%** | **14.79%** | Non-invasive blood pressure cuff cycle differences. |
| **Temp** | **67.22%** | **64.27%** | Intermittent manual probe measurements in both groups. |

---

## 6. Physiological Distributions

The physiological variables were evaluated after outlier cleaning (clipping to physiologically plausible bounds: HR [30-220], O2Sat [40-100], Temp [26-45], SBP [40-260], MAP [20-220], DBP [20-180], Resp [4-60]) and Forward Fill / Training-Median Imputation.

### Summary Statistics (All Hours vs. Sepsis Hours vs. Non-Sepsis Hours)

| Variable | Cohort Mean ± Std | Cohort Median [IQR] | Sepsis Hours Mean (Median) | Non-Sepsis Hours Mean (Median) |
| :--- | :---: | :---: | :---: | :---: |
| **HR (bpm)** | 85.60 ± 16.93 | 84.00 [73.0, 97.0] | **93.14 (91.00)** | **85.42 (84.00)** |
| **O2Sat (%)** | 97.07 ± 3.24 | 98.00 [96.0, 99.0] | **96.97 (98.00)** | **97.07 (98.00)** |
| **Temp (°C)** | 36.95 ± 0.71 | 37.00 [36.5, 37.39] | **37.21 (37.28)** | **36.94 (37.00)** |
| **SBP (mmHg)** | 121.01 ± 20.89 | 119.00 [106.0, 133.0] | **119.85 (119.00)** | **121.04 (119.00)** |
| **MAP (mmHg)** | 79.26 ± 14.65 | 77.00 [69.0, 88.0] | **78.71 (77.00)** | **79.27 (77.00)** |
| **DBP (mmHg)** | 60.18 ± 10.72 | 59.00 [56.0, 62.0] | **62.05 (59.00)** | **60.14 (59.00)** |
| **Resp (breaths/min)** | 18.87 ± 5.30 | 18.00 [15.0, 22.0] | **20.03 (19.00)** | **18.84 (18.00)** |

### Physiological Insights
1. **Tachycardia Signal:** Sepsis hours exhibit a mean Heart Rate elevation of **+7.72 bpm** (93.14 vs 85.42 bpm), reflecting systemic inflammatory response compensating for vasodilation.
2. **Tachypnea Signal:** Respiration rate is elevated by **+1.19 breaths/min** in sepsis hours (20.03 vs 18.84 breaths/min).
3. **Hyperthermia Signal:** Core body temperature shows an upward shift during sepsis hours (37.21°C vs 36.94°C).

---

## 7. Temporal Behavior

Analyzing individual patient time series demonstrates distinct trajectory profiles:

```
Representative Sepsis Patient Trajectory (Conceptual Timeline)
ICULOS (h) ───►  0      10     20     30     35 (Onset)  40     45
HR (bpm)   ───► 75 ──── 78 ──── 84 ──── 92 ───► 108 ──────► 112 ─── 105
Resp (rpm) ───► 16 ──── 16 ──── 18 ──── 22 ───►  26 ──────►  28 ───  24
SepsisLabel───►  0      0      0      0      1       1      1
```

* **Pre-Onset Acceleration:** Heart rate and respiration rate exhibit progressive upward trajectories 4–8 hours prior to official `SepsisLabel` onset.
* **Non-Sepsis Controls:** Negative patients display stable baseline oscillations with occasional transient spikes that return quickly to normal physiological equilibrium.
* **No Causality Inference:** Temporal trends demonstrate clinical correlations with sepsis onset windows but do not prove individual causal mechanisms.

---

## 8. Variable Relationships

Pairwise Pearson correlation analysis across primary vital signs provides empirical evidence of physiological coupling:

### Correlation Matrix

```
        HR     O2Sat    Temp     SBP     MAP     DBP    Resp
HR     1.000  -0.082   0.242  -0.017   0.130   0.182   0.275
O2Sat -0.082   1.000   0.033   0.055   0.055   0.041  -0.120
Temp   0.242   0.033   1.000   0.035   0.015   0.047   0.107
SBP   -0.017   0.055   0.035   1.000   0.775   0.441   0.033
MAP    0.130   0.055   0.015   0.775   1.000   0.612   0.064
DBP    0.182   0.041   0.047   0.441   0.612   1.000   0.063
Resp   0.275  -0.120   0.107   0.033   0.064   0.063   1.000
```

### Key Observations
1. **Hemodynamic Coupling:** Strong positive correlations exist between blood pressure metrics: SBP & MAP ($r = 0.775$), MAP & DBP ($r = 0.612$), and SBP & DBP ($r = 0.441$).
2. **Cardiorespiratory Coupling:** Moderate correlation between Heart Rate and Respiration Rate ($r = 0.275$) and HR and Temperature ($r = 0.242$).
3. **Orthogonal Signals:** Pulse Oximetry (`O2Sat`) exhibits weak correlation with blood pressure ($r \approx 0.055$) and heart rate ($r = -0.082$), providing independent physiological information.

> [!IMPORTANT]
> **Methodological Note:** Correlation measures linear association across hourly snapshots, not direct physiological causation.

---

## 9. Review & Integration of Exploration Notebook

The user's hands-on notebook (`CareMind_PhysioNet2019_Exploration.ipynb`) was thoroughly reviewed as an active EDA artifact.

### Key Contributions of User Notebook
* Initial exploration of raw `.psv` file structures downloaded via AWS CLI.
* Detailed deep dive into single patient record `p002261` (ICULOS timeline, missingness breakdown, 0 → 1 label transition).
* Histogram analysis of record lengths on a 20-patient subset.
* Visual trajectory plotting of HR, Resp, and SpO2 for positive-label patients.

---

## 10. Confirmed vs. Sample-Specific Observations

Comparing notebook observations against dataset-wide 500-patient benchmark statistics yields clear classification:

| Notebook Finding | 500-Patient Benchmark Status | Classification | Context & Action |
| :--- | :--- | :--- | :--- |
| Extreme lab missingness (>85-99%) | Confirmed (Lactate 95.95%, WBC 92.08%, Glucose 86.99%) | **Confirmed at Scale** | Labs are unsuitable as dense hourly inputs; require missingness indicators if included. |
| High Temperature missingness (~64%) | Confirmed (64.69% raw missingness) | **Confirmed at Scale** | Requires LOCF + missingness indicator `is_missing_Temp`. |
| Sepsis prevalence ~9% | Confirmed (9.00% patient-level, 2.25% hourly-level) | **Confirmed at Scale** | Representative of severe class imbalance in real-world ICU sepsis cohorts. |
| Median ICU stay ~39 hours | Confirmed (Median = 39.0h, IQR [24.0, 48.0]) | **Confirmed at Scale** | Reflects short-to-medium ICU monitoring windows. |
| Single patient `p002261` onset at hour 14 | Sample-specific | **Do Not Generalize** | Onset varies widely across cohort (median 35h, mean 51.9h, range 1–249h). |
| Visual SpO2 drop in patient sample | Sample-specific | **Do Not Generalize** | Cohort-wide O2Sat mean in sepsis hours is 96.97% vs 97.07% non-sepsis (minimal overall shift). |

---

## 11. Candidate Physiological Feature Groups

Based on empirical missingness, clinical relevance, and temporal stability, candidate physiological features for downstream modeling are categorized into four distinct groups:

```
Feature Architecture Taxonomy
├── Group A: Core Vitals (Common, Missing < 16%)
│   ├── HR, MAP, SBP, Resp, O2Sat
├── Group B: Intermittent Vitals (Missing 30-70%)
│   ├── Temp, DBP
├── Group C: Engineered Temporal Dynamics (100% Complete post-ETL)
│   ├── Missingness Indicators: is_missing_HR, is_missing_Temp, etc.
│   ├── 1h & 3h Deltas: delta_HR_1h, delta_HR_3h, delta_Resp_1h, etc.
│   ├── 3h Rolling Stats: rolling_mean_HR_3h, rolling_std_HR_3h, etc.
└── Group D: Excluded Laboratory Features (Missing > 85%)
    └── Lactate, WBC, Platelets, Creatinine, TroponinI, EtCO2 (Excluded from primary continuous model)
```

1. **Group A (Primary Continuous Vitals):** `HR`, `MAP`, `SBP`, `Resp`, `O2Sat`. High charting frequency, minimal imputation required.
2. **Group B (Secondary Vitals):** `Temp`, `DBP`. Carries vital clinical signal but requires explicit missingness flags.
3. **Group C (Engineered Temporal Dynamics):** `is_missing_*` indicators, hourly deltas (`delta_*_1h`, `delta_*_3h`), and rolling statistics (`rolling_mean_*_3h`, `rolling_std_*_3h`).
4. **Group D (Excluded Sparse Labs):** Laboratory values with >85% missingness. Excluded from baseline temporal sequence models to avoid severe imputation bias.

---

## 12. Limitations

1. **Hourly Temporal Resolution:** Data is discretized into 1-hour windows; intra-hour high-frequency dynamics are unavailable in PhysioNet 2019.
2. **Clinical Charting Bias:** Vital sign recording frequency is influenced by nurse charting habits and patient severity.
3. **Sepsis Label Specificity:** `SepsisLabel` is constructed per PhysioNet 2019 rules (SIRS + SOFA drop within window) and may differ from alternative consensus definitions (e.g. Sepsis-3 explicit onset timestamps).

---

## 13. Implications for CareMind

* **Validated Discrete Pipeline:** Confirms that discrete ICU vitals combined with temporal feature engineering (deltas + rolling statistics + missingness flags) form a solid foundation for Level 1 temporal risk modeling.
* **Strict Task Boundary:** Prevents scope creep by maintaining `SepsisLabel` strictly as a dedicated sepsis target.
* **Separation of Concerns:** Confirms that high-frequency continuous waveform research belongs in MIMIC-IV and MIT-BIH, keeping PhysioNet 2019 focused on discrete hourly physiological trends.

---

## 14. Recommended Next Experiment (Phase 5 Transition)

With Phase 4A ETL and Phase 4B EDA fully complete and verified, the recommended next step is:

### Phase 5A: Baseline Multimodal Temporal Sepsis Model Development
1. **Model Scope:** Train initial baseline classifiers (e.g., LightGBM / XGBoost / Logistic Regression) on the zero-leakage preprocessed splits (`train.parquet`, `val.parquet`, `test.parquet`).
2. **Feature Set:** Utilize Group A + Group B vitals + Group C temporal dynamics (deltas, rolling stats, missingness indicators).
3. **Evaluation Metrics:** PR-AUC, ROC-AUC, F1-score, and PhysioNet Utility Score on the holdout test set (`test.parquet`).
4. **Approval Requirement:** Model training will commence **only after explicit user approval**.
