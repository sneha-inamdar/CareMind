# CareMind — MIMIC Research & Data Plan (Feasibility Audited)

> **Document Status**: Active Planning & Feasibility Audited Specification  
> **Target Dataset**: MIMIC-IV Clinical Database (v2.2) & MIMIC-IV Waveform Database (Matched Subset v1.0)  
> **Project Scope**: Multimodal ICU Risk Prediction & Physiological Feature Importance Evaluation  

---

## 1. Executive Summary & Strategic Rationale

CareMind is an AI-powered multimodal ICU clinical decision-support system. To establish robust, scientifically rigorous evidence for multimodal physiological fusion, the project requires evaluation on standard critical care datasets. 

While the **MIT-BIH Arrhythmia Database** serves as CareMind's validated single-modality ECG foundation, and **PhysioNet 2019** provides a discrete, sepsis-specific temporal benchmark, **MIMIC-IV** provides the essential clinical breadth and high-frequency waveform co-registration required for CareMind's core research objectives.

MIMIC-IV will **NOT** be concatenated or merged with PhysioNet 2019 or MIT-BIH patients. Instead, it serves as an independent, multi-hospital evaluation benchmark to:
1. Investigate broader ICU physiological deterioration patterns beyond sepsis.
2. Evaluate continuous waveform telemetry (ECG, ABP, PPG) linked to discrete clinical outcomes.
3. Quantify the relative importance of individual vital signs using multi-pillar feature attribution (single-vital baselines, modality ablation, permutation importance, and SHAP) rather than arbitrary clinical heuristics.

---

## 2. MIMIC Dataset Variant Selection & Architecture

CareMind will utilize **both MIMIC-IV variants in a linked multi-tiered design**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   Audited Tiered MIMIC Data Architecture                    │
│                                                                             │
│  ┌─────────────────────────────────┐   ┌─────────────────────────────────┐  │
│  │   MIMIC-IV Clinical (Relational)│   │  MIMIC-IV Waveform (Matched)    │  │
│  │   - ~30,000 adult first-ICU     │   │  - Tier 1: ECG + ABP + PPG      │  │
│  │   - Discrete vitals & labs      │   │  - Tier 2: ECG + PPG (Fallback) │  │
│  │   - 24h In-Hospital Mortality   │   │  - Tier 3: ECG + Trend Vitals   │  │
│  └────────────────┬────────────────┘   └────────────────┬────────────────┘  │
│                   │                                     │                   │
│                   └──────────────────┬──────────────────┘                   │
│                                      ▼                                      │
│                  Linked via `subject_id` & `stay_id`                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.1 MIMIC-IV (Clinical Relational Database v2.2)
- **Role**: Primary source for clinical cohort selection, demographic normalization, discrete vital sign trends (`icu/chartevents`), laboratory measurements (`hosp/labevents`), and ground-truth clinical outcomes (`hosp/patients`, `hosp/admissions`, `icu/icustays`).
- **Why Required**: Provides statistically powerful clinical outcome labels (e.g., 24-hour future in-hospital ICU mortality) and multi-vital discrete time-series across thousands of patients.

### 2.2 MIMIC-IV Waveform Database (Matched Subset v1.0)
- **Role**: Source for high-frequency continuous physiological signals (Lead II ECG, Invasive Arterial Blood Pressure [ABP], Photoplethysmogram [PPG]).
- **Feasibility Fallback Tiering**:
  - **Tier 1 (Triple-Vital Cohort)**: Lead II ECG + Invasive ABP + PPG (Ideal continuous signal set; present in ~25–35% of waveform records with arterial lines).
  - **Tier 2 (Dual-Vital Fallback)**: Lead II ECG + PPG + 1 Hz trend numerics for BP (Broad availability; present in >70% of waveform records).
  - **Tier 3 (Single-Vital Fallback)**: Lead II ECG + 1 Hz trend numerics for all vitals.

---

## 3. Primary Research Questions (Audited & Refined)

The MIMIC experiment is structured to answer two primary research questions:

1. **Multimodal Predictive Value**:  
   *Does late or hybrid fusion of continuous waveform representations (ECG, ABP, PPG) with discrete vital sign dynamics (HR, SBP/DBP/MAP, SpO2, Resp, Temp) extracted over the initial 24 hours of ICU stay significantly improve 24-hour future in-hospital mortality prediction compared to single-vital baseline models in a general ICU cohort?*

2. **Multi-Pillar Feature Importance**:  
   *What is the empirical predictive contribution of each physiological parameter (HR vs. BP vs. SpO2 vs. RR vs. Temp) for general ICU deterioration risk, and how can single-vital baselines, modality ablation, and SHAP attribution scores replace arbitrary heuristic risk weighting in CareMind's Patient Risk Engine ($S_i \in [0, 100]$)?*

---

## 4. Prediction Objective & Target Construction Audit

### 4.1 Ground-Truth Target Construction
- **Target Flag**: `Mortality24h` $\in \{0, 1\}$ (Primary Target) & `AcuteDeterioration24h` (Secondary Exploratory Composite).
- **Observation Window**: $t \in [t_{\text{intime}}, t_{\text{intime}} + 24\text{ hours}]$ (Initial 24 hours of ICU admission).
- **Prediction Horizon**: $t \in (t_{\text{intime}} + 24\text{ hours}, t_{\text{intime}} + 48\text{ hours}]$ (Next 24-hour window).

```
Timeline Schema & Target Window
┌─────────────────────────────────────────┬─────────────────────────────────────────┐
│     Observation Window (Predictors X)   │     Prediction Window (Target Y)        │
│          0h ────────────► 24h           │          24h ────────────► 48h          │
└─────────────────────────────────────────┴─────────────────────────────────────────┘
  Extract HR, BP, SpO2, Temp, Labs           Mortality24h = 1 if death occurs
  Strictly backward-looking (<= 24h)         in (24h, 48h] or hospital expire
```

### 4.2 Relational Construction Logic (SQL / Pandas)
Target `Mortality24h` is constructed by joining `icu/icustays`, `hosp/admissions`, and `hosp/patients`:
1. `deathtime` from `hosp/admissions` or `dod` (date of death) from `hosp/patients`.
2. `Mortality24h = 1` if `deathtime` or `dod` falls within $(t_{\text{intime}} + 24\text{h}, t_{\text{intime}} + 48\text{h}]$ OR if `hospital_expire_flag = 1` with `deathtime > intime + 24h`.
3. `Mortality24h = 0` if patient survives past $t_{\text{intime}} + 48\text{h}$.

### 4.3 Exclusion & Leakage Prevention Criteria
- **Exclude Short Stays**: Exclude stays with `los < 1.0` day ($< 24$ hours).
- **Exclude Early Mortality/Discharge**: Exclude stays where `outtime <= intime + 24h` or `deathtime <= intime + 24h` (prevents immortal time bias and missing predictor data).
- **Strict Leakage Firewall**: Zero data from $t > 24\text{h}$ is accessible during feature extraction.

---

## 5. Audited Clinical & Waveform Variable Extraction Schema

### 5.1 Discrete Vitals & Labs (`chartevents` & `labevents`)

| Variable | Source Table | Item IDs (`itemid`) | Extraction Strategy & Unit |
| :--- | :--- | :--- | :--- |
| **Heart Rate (HR)** | `icu/chartevents` | `220045` | Hourly stats over [0, 24h] (bpm) |
| **Systolic BP (SBP)** | `icu/chartevents` | `220050` (Art), `220179` (NIBP) | Hourly stats over [0, 24h] (mmHg) |
| **Diastolic BP (DBP)** | `icu/chartevents` | `220051` (Art), `220180` (NIBP) | Hourly stats over [0, 24h] (mmHg) |
| **Mean Arterial BP (MAP)** | `icu/chartevents` | `220052` (Art), `220181` (NIBP) | Hourly stats over [0, 24h] (mmHg) |
| **SpO2** | `icu/chartevents` | `220277` | Hourly stats over [0, 24h] (%) |
| **Respiratory Rate** | `icu/chartevents` | `220210` | Hourly stats over [0, 24h] (insp/min) |
| **Temperature** | `icu/chartevents` | `223761` (°F), `223762` (°C) | Convert °F to °C; stats over [0, 24h] |
| **Serum Lactate** | `hosp/labevents` | `50813` | Max value & deltas over [0, 24h] (mmol/L) |
| **White Blood Cells (WBC)**| `hosp/labevents` | `51301` | Latest value over [0, 24h] (K/uL) |
| **Serum Creatinine** | `hosp/labevents` | `50912` | Max value over [0, 24h] (mg/dL) |
| **Arterial pH** | `hosp/labevents` | `50820` | Min value over [0, 24h] |

### 5.2 Waveform Variables (`mimic4wdb`)

| Waveform Signal | Target Sampling | Channel Availability | Role in CareMind |
| :--- | :--- | :--- | :--- |
| **Lead II ECG** | 125 / 250 Hz | High (>90%) | HRV, beat morphology, QRS width |
| **Invasive ABP** | 125 Hz | Moderate (~25–35%) | Systolic/diastolic peak, dP/dt max |
| **Photoplethysmogram (PPG)**| 125 Hz | High (~70–80%) | Pulse wave amplitude, O2 dynamics |

---

## 6. Audited Cohort Design & Feasibility Subsets

```
Cohort Selection Pipeline
┌─────────────────────────────────────────────────────────────────────────────┐
│ All MIMIC-IV ICU Admissions (~50,000 stays)                                 │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Filter: anchor_age >= 18
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Adult ICU Admissions (~45,000 stays)                                        │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Filter: First ICU Stay per subject_id
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ First Adult ICU Admissions (~30,000 stays)                                  │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Filter: los >= 1.0 day & intime+24h survived
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Primary Clinical Cohort (~20,000 stays)                                     │
│ ├── Prototyping Subset: 1,000 stays (Fast local development)                │
│ └── Matched Waveform Cohort: 100–200 stays (Tier 1/2 Waveforms)              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Multi-Pillar Feature Importance Framework

To ensure scientifically sound variable evaluation (beyond SHAP alone), CareMind uses a **4-Pillar Feature Importance Strategy**:

1. **Single-Vital Baseline Ablation**: Evaluate performance of models trained on single vital signs (`HR_ONLY`, `BP_ONLY`, `SPO2_ONLY`, `RESP_ONLY`, `TEMP_ONLY`).
2. **Modality Group Ablation Matrix**: Train models excluding entire signal groups (`NO_LABS`, `NO_WAVEFORMS`, `VITALS_ONLY`, `ALL_COMBINED`).
3. **Permutation Feature Importance**: Quantify the drop in Test PR-AUC when individual feature columns are randomly shuffled.
4. **Post-Hoc SHAP Attribution**: Calculate mean absolute SHAP values ($|\text{SHAP}|$) on the `ALL_COMBINED` model to inspect individual feature impact and directionality.

---

## 8. Comparative Analysis: MIMIC vs. PhysioNet 2019 vs. MIT-BIH

| Dimension | MIT-BIH Arrhythmia | PhysioNet 2019 Sepsis | MIMIC-IV Benchmark (CareMind) |
| :--- | :--- | :--- | :--- |
| **Clinical Focus** | Cardiac Arrhythmia Detection | Hourly Sepsis-3 Early Warning | General ICU 24h Mortality & Deterioration |
| **Modality** | 2-Lead Raw ECG | Hourly Discrete Tabular Vitals | Tiered: Discrete EHR Vitals + High-Res Waveforms |
| **Sampling Rate** | 360 Hz | 1-hour discrete intervals | 125/250 Hz waveforms + 1h chart events |
| **Outcome Label** | AAMI Beat Labels (N, S, V, F, Q) | 6h Lead SepsisLabel | 24h Future Mortality (`Mortality24h`) |
| **Patient Population** | Ambulatory Outpatients (47) | ICU Patients (ICU A & B) | General ICU Admissions (BIDMC) |
| **CareMind Role** | ECG single-modality baseline | Sepsis hourly baseline | Multimodal general risk & feature importance |

---

## 9. PhysioNet Access Requirements & Action Checklist

MIMIC-IV and MIMIC-IV Waveform are restricted access datasets hosted on PhysioNet under a strict Data Use Agreement (DUA).

### User Action Required (Step-by-Step):
1. **Complete CITI Training**:
   - Course: **"Data or Specimens Only Research"** or **"Human Subjects Research for Biomedical Researchers"**.
   - Obtain completion certificate PDF and report ID.
2. **Register PhysioNet Account**:
   - Register at [physionet.org](https://physionet.org/).
   - Complete personal and institutional profile.
3. **Link CITI Certificate**:
   - Submit CITI completion record on PhysioNet profile under "Training".
4. **Sign Data Use Agreement (DUA)**:
   - Navigate to MIMIC-IV (v2.2) and MIMIC-IV Waveform Database (v1.0) pages.
   - Read and electronically sign the Restricted Health Data Use Agreement.
5. **Submit Access Request**:
   - Await PhysioNet credentialing approval (typically 1–3 business days).
6. **Generate Credentials**:
   - Once approved, set environment variables (`PHYSIONET_USERNAME` & `PHYSIONET_PASSWORD`).

---

## 10. Next Implementation Steps (Post-Access)

Once PhysioNet credentialing is verified:
1. **Execute Cohort Selection**: Run `src/mimic/cohort_selector.py` to extract the 1,000-patient discrete subset and 100-patient waveform subset.
2. **Data Validation**: Run `src/mimic/validator.py` to check missingness, schema integrity, and physiological value bounds.
3. **Feature Engineering**: Generate 24-hour backward-looking statistics, deltas, and waveform morphological features.
4. **Ablation Baseline Experiments**: Evaluate `random_forest` and `hist_gradient_boosting` across `HR_ONLY`, `BP_ONLY`, `SPO2_ONLY`, `RESP_ONLY`, `TEMP_ONLY`, and `COMBINED` feature sets.
5. **Multi-Pillar Feature Importance**: Calculate SHAP attributions and permutation importance to parameterize the CareMind Patient Risk Engine ($S_i$).

---

## 11. Preliminary MIMIC-IV Clinical Demo v2.2 Verification Report (PRELIMINARY / DEMO ONLY)

> ⚠️ **Disclaimer**: The results in this section are generated strictly from the open **MIMIC-IV Clinical Database Demo v2.2** (100 patients) to test schema compatibility, item ID correctness, cohort filtering, and temporal zero-leakage firewalls. **These numbers do NOT represent final research results.** The final CareMind research evaluation will use the full credentialed MIMIC-IV dataset upon PhysioNet approval.

### 11.1 Demo Table Verification & Schema Mapping
- **`hosp/patients`**: Verified `subject_id`, `gender`, `anchor_age`, `dod`.
- **`hosp/admissions`**: Verified `subject_id`, `hadm_id`, `admittime`, `dischtime`, `deathtime`, `hospital_expire_flag`.
- **`icu/icustays`**: Verified `subject_id`, `hadm_id`, `stay_id`, `intime`, `outtime`, `los`.
- **`icu/chartevents` & `icu/d_items`**: Verified item IDs `220045` (HR), `220050`/`220179` (SBP), `220051`/`220180` (DBP), `220052`/`220181` (MAP), `220277` (SpO2), `220210` (Resp), `223761`/`223762` (Temp).
- **`hosp/labevents` & `hosp/d_labitems`**: Verified item IDs `50813`/`52442` (Lactate), `51301` (WBC), `50912` (Creatinine), `50820` (Arterial pH).

### 11.2 Preliminary Demo Cohort Statistics
```
MIMIC-IV Demo v2.2 Pipeline Filtering
├── Total Demo Patients: 100
├── Total Admissions: 275
├── Total ICU Stays: 140
├── Step A: Adult Stays (anchor_age >= 18): 140 (100.0%)
├── Step B: First ICU Stay per Patient: 100 stays
├── Step C: ICU Length of Stay >= 24h (los >= 1.0): 85 stays
└── Step D: Survived Complete Initial 24h Window: 85 stays (Final Demo Cohort)
```

### 11.3 Preliminary Demo Target Distribution
- **`Mortality24h` (24h–48h Prediction Window)**:
  - `Mortality24h = 0`: 85 stays (100.0%)
  - `Mortality24h = 1`: 0 stays (0.0% — due to 100-patient sample size limit)
- **`InHospMortalityPost24h` (Overall In-Hospital Mortality Post-24h)**:
  - Survived stay post 24h: 78 stays (91.76%)
  - In-Hospital Death post 24h: 7 stays (8.24%)

### 11.4 Initial 24-Hour Vital & Lab Missingness (Demo Cohort N = 85)

| Parameter | Source Table | Item IDs | Present Stays | Missing % |
| :--- | :--- | :--- | :---: | :---: |
| **Heart Rate** | `chartevents` | `220045` | 85 / 85 | **0.00%** |
| **Systolic BP** | `chartevents` | `220050`, `220179` | 85 / 85 | **0.00%** |
| **Diastolic BP** | `chartevents` | `220051`, `220180` | 85 / 85 | **0.00%** |
| **Mean Arterial BP**| `chartevents` | `220052`, `220181` | 85 / 85 | **0.00%** |
| **SpO2** | `chartevents` | `220277` | 85 / 85 | **0.00%** |
| **Respiratory Rate**| `chartevents` | `220210` | 85 / 85 | **0.00%** |
| **Temperature** | `chartevents` | `223761`, `223762` | 81 / 85 | **4.71%** |
| **White Blood Cells**| `labevents` | `51301` | 85 / 85 | **0.00%** |
| **Creatinine** | `labevents` | `50912` | 85 / 85 | **0.00%** |
| **Arterial pH** | `labevents` | `50820` | 59 / 85 | **30.59%** |
| **Lactate** | `labevents` | `50813`, `52442` | 56 / 85 | **34.12%** |

### 11.5 Leakage Audit Findings
- Out of 490,081 chart event rows for cohort stays, exactly **119,147 rows** occurred within $[t_{\text{intime}}, t_{\text{intime}} + 24\text{h}]$ and were extracted into predictor features $X_{\le 24\text{h}}$.
- Exactly **370,934 future rows** ($> 24\text{h}$) were successfully rejected by the temporal firewall.
- **Leakage Violations = 0**.

