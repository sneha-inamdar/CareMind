# Phase 3 — Remaining Physiological Data Report

> **Clinical & Architectural Disclaimer**: CareMind is an academic research project and a clinical decision-support system (CDSS) prototype. CareMind is designed to assist healthcare professionals by displaying individual vital parameter statuses alongside multimodal risk predictions. CareMind is strictly a decision-support tool and is **NOT** a replacement for clinical judgment, medical diagnosis, direct patient evaluation, or primary ICU hardware monitors.

---

## 1. Executive Summary & Scope

Phase 3 of the CareMind project focuses on investigating, understanding, inspecting, and planning the Extraction, Transformation, and Loading (ETL) pipeline for the remaining physiological data needed for multimodal ICU risk monitoring.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        CareMind Multimodal Pipeline                    │
│                                                                        │
│   Physiological Data ──► Data Ingestion / Replay ──► Preprocessing     │
│                                                            │           │
│                                                            ▼           │
│   Multimodal Fusion ◄── Individual Signal Models ◄── Signal Analysis   │
│           │                                                            │
│           ▼                                                            │
│   Patient Risk Engine ──► Explainability/Uncertainty ──► Alerts ──► Dashboard│
└────────────────────────────────────────────────────────────────────────┘
```

### Core Goals of Phase 3
1. **Preserve Completed ECG Foundation**: Maintain the completed MIT-BIH ECG baseline prototype as CareMind's single-modality ECG anchor.
2. **Investigate Remaining Candidate Datasets**: Conduct a detailed inspection of two primary target datasets: **PhysioNet/CinC Challenge 2019** (discrete hourly ICU time-series) and **MIMIC-IV Waveform Database** (high-frequency continuous ICU waveforms).
3. **Establish Two-Level Analysis Framework**: Differentiate between **Level 1 (Individual Signal Analysis)** and **Level 2 (Multimodal / Fusion Analysis)**.
4. **Define Patient-Level Data Integrity Rules**: Enforce strict boundary rules to prevent combining unrelated patients across different datasets.
5. **Design Detailed ETL Pipelines**: Specify `INPUT → PROCESS → OUTPUT` transformations for cleaning, resampling, handling missing values, and preparing data for simulated replay.

> **Phase 3 Boundary Notice**: In accordance with project phase guidelines, Phase 3 **does not** include training final ML models, constructing final multimodal training matrices, merging patient cohorts across datasets, downloading multi-terabyte datasets blindly, or implementing final UI dashboards.

---

## 2. Core Architectural Concept: Two-Level Analysis Framework

CareMind is structured around a **two-level analysis paradigm** to ensure clinicians receive both granular single-vital diagnostics and holistic multi-signal risk assessments.

```
                  ┌─────────────────────────────────────────┐
                  │          Physiological Inputs           │
                  └────────────────────┬────────────────────┘
                                       │
      ┌────────────────────────────────┼────────────────────────────────┐
      ▼                                ▼                                ▼
┌───────────┐                    ┌───────────┐                    ┌───────────┐
│ ECG Signal│                    │ Blood Press│                    │ SpO₂      │
└─────┬─────┘                    └─────┬─────┘                    └─────┬─────┘
      │                                │                                │
      ▼                                ▼                                ▼
┌───────────┐                    ┌───────────┐                    ┌───────────┐
│  Level 1  │                    │  Level 1  │                    │  Level 1  │
│ Individual│                    │ Individual│                    │ Individual│
│ Status: N │                    │ Status: H │                    │ Status: N │
└─────┬─────┘                    └─────┬─────┘                    └─────┬─────┘
      │                                │                                │
      └────────────────────────────────┼────────────────────────────────┘
                                       │
                                       ▼
                         ┌───────────────────────────┐
                         │          Level 2          │
                         │     Multimodal Fusion     │
                         └─────────────┬─────────────┘
                                       │
                                       ▼
                         ┌───────────────────────────┐
                         │   Overall Patient Risk    │
                         │    Score: 78% (Critical)  │
                         └───────────────────────────┘
```

---

### 2.1 Level 1 — Individual Signal Analysis

Each physiological parameter undergoes dedicated, signal-specific processing. The analytical approach for each signal is chosen based on what is scientifically and clinically appropriate:

1. **Electrocardiogram (ECG)**:
   - **Method**: 250-sample R-peak centered beat extraction, 11-dimensional feature vector extraction, and Support Vector Machine (SVM) classification (using the pre-validated MIT-BIH prototype baseline).
   - **Output Status**: 5-Class AAMI Category (`N` Normal, `S` Supraventricular Ectopic, `V` Ventricular Ectopic, `F` Fusion, `Q` Unclassifiable).
2. **Blood Pressure (BP — Systolic, Diastolic, MAP)**:
   - **Method**: Clinical thresholding combined with rolling trend statistics (Mean Arterial Pressure $MAP = DBP + \frac{1}{3}(SBP - DBP)$).
   - **Output Status**: `Normal` ($MAP \ge 70 \text{ mmHg}$), `Warning` ($60 \le MAP < 70$), `Critical Hypotension` ($MAP < 60 \text{ mmHg}$), or `Hypertensive Crisis` ($SBP > 180 \text{ mmHg}$).
3. **Oxygen Saturation ($SpO_2$)**:
   - **Method**: Direct physiological thresholding and desaturation event duration tracking. Machine learning is **not forced** here because established clinical thresholds are highly effective.
   - **Output Status**: `Normal` ($SpO_2 \ge 95\%$), `Mild Hypoxia` ($90\% \le SpO_2 < 95\%$), `Severe Hypoxia` ($SpO_2 < 90\%$).
4. **Respiratory Rate (RR)**:
   - **Method**: Clinical thresholding for tachypnea/bradycardia detection and respiratory instability scoring.
   - **Output Status**: `Normal` ($12 \le RR \le 20 \text{ bpm}$), `Bradypnea` ($RR < 12 \text{ bpm}$), `Tachypnea` ($RR > 24 \text{ bpm}$).
5. **Body Temperature**:
   - **Method**: Clinical thermal boundary thresholding.
   - **Output Status**: `Normal` ($36.5^\circ\text{C} \le Temp \le 37.5^\circ\text{C}$), `Hypothermia` ($Temp < 35.0^\circ\text{C}$), `Fever / Pyrexia` ($Temp > 38.3^\circ\text{C}$).

> **Clinical Rationale for Rule-Based Thresholds**: For parameters like $SpO_2$ and Body Temperature, established medical guidelines (such as NEWS2 - National Early Warning Score) provide gold-standard deterministic risk boundaries. Forcing complex black-box machine learning models onto single parameters where clear physiological thresholds exist adds unnecessary complexity and reduces interpretability. Machine learning is reserved for complex pattern discovery (e.g., ECG beat morphology and multimodal temporal interactions).

---

### 2.2 Level 2 — Multimodal / Fusion Analysis

Once individual signal statuses are computed, signals belonging strictly to the **same patient** are passed into the multimodal fusion engine:

- **Input**: Synchronized representations of ECG, BP, $SpO_2$, Resp Rate, and Temperature.
- **Process**: Joint temporal modeling (e.g., late probability fusion or recurrent temporal embedding) to assess multi-organ stability.
- **Output**: Composite Patient Risk Score $S_i \in [0, 100]$, Risk Category (`Normal`, `Warning`, `Critical`), and top contributing clinical factors (SHAP / feature attribution).

---

### 2.3 Interface Dual-Presentation Concept

The CareMind system delivers both levels of information on a single view:

```text
================================================================================
PATIENT P01 | ICU BED 04 | RISK SCORE: 78% (CRITICAL ALERT)
================================================================================
INDIVIDUAL PARAMETER STATUS:
  ├── ECG          : Normal Sinus Rhythm (N)          [Status: OK]
  ├── Blood Press  : MAP 54 mmHg (Hypotension)        [Status: CRITICAL]
  ├── SpO₂         : 91% (Mild Hypoxia)               [Status: WARNING]
  ├── Resp Rate    : 28 bpm (Tachypnea)               [Status: CRITICAL]
  └── Temperature  : 38.8 °C (Fever)                  [Status: WARNING]
--------------------------------------------------------------------------------
MULTIMODAL FUSION RISK ASSESSMENT:
  ├── Primary Finding: High Risk of Hemodynamic Collapse / Early Sepsis Onset
  └── Key Drivers    : Concurrent MAP drop + Elevated Resp Rate + Fever
================================================================================
```

---

## 3. Completed MIT-BIH ECG Foundation Summary

The completed standalone ECG prototype serves as the baseline foundation for CareMind's ECG modality:

| Dimension | Specification |
| :--- | :--- |
| **Dataset** | PhysioNet MIT-BIH Arrhythmia Database (48 records, 2-lead, 360 Hz). |
| **Data Partition** | de Chazal et al. (2004) DS1/DS2 inter-patient split (DS1: 51,002 train beats; DS2: 49,692 test beats). |
| **Preprocessing** | 0.5–40 Hz 2nd-order zero-phase Butterworth bandpass filter. |
| **Segmentation** | 250-sample window centered at R-peak (90 samples pre-R, 160 samples post-R). |
| **Features** | 11-dimensional feature vector ($RR_{prev}$, $RR_{next}$, $RR_{ratio}$, statistical moments). |
| **Model** | Trained `StandardScaler` + `SVC` classifier mapped to 5 AAMI categories (`N`, `S`, `V`, `F`, `Q`). |
| **Replay & UI** | 5-patient simulated real-time stream replay engine over WebSockets with HTML5 Canvas dashboard. |
| **Integration** | Preserved intact; will be migrated to `ml/ecg/` according to `ECG_INTEGRATION_PLAN.md`. |

---

## 4. Dataset Investigation 1: PhysioNet/CinC Challenge 2019 (Sepsis)

### 4.1 Overview & Purpose
The PhysioNet/Computing in Cardiology Challenge 2019 dataset was developed for the early prediction of sepsis in ICU patients using clinical time-series data. It represents a realistic ICU cohort with hourly discrete vitals and laboratory measurements.

### 4.2 Detailed Specifications Table

| Question / Parameter | Detailed Dataset Finding |
| :--- | :--- |
| **1. What is the dataset?** | Retrospective ICU clinical time-series database collected from two separate hospital systems for early sepsis prediction. |
| **2. Patient Count** | **40,336 ICU patients** (Hospital A: 20,336 patients; Hospital B: 20,000 patients). |
| **3. Available Signals / Vitals** | 8 physiological vital signs (Heart Rate, $O_2Sat$, Temp, SBP, MAP, DBP, Resp, EtCO2), 26 laboratory values, and 6 demographic features. |
| **4. Patient Boundary** | Each pipe-delimited file (`.psv`) represents **one unique patient**. Signals inside a file belong exclusively to that patient. |
| **5. Patient Identifiers** | File-based IDs (e.g., `p000001.psv`, `p012345.psv`). |
| **6. Timestamps** | Hourly discrete time steps ($t = 0, 1, 2, \dots, N$ hours from ICU admission). |
| **7. Sampling Frequency** | Discrete 1-hour interval chart recordings (1 sample per hour). |
| **8. Continuity** | **Intermittent discrete time-series**. Vitals recorded hourly; labs recorded sporadically. |
| **9. Clinical Labels** | Binary hourly `SepsisLabel` (1 if sepsis onset occurs within the next 6 hours according to Sepsis-3 criteria; 0 otherwise). |
| **10. Missing Data** | **High missingness**: Lab values are missing in 85–98% of time steps; vital signs missing in 10–30% of hours. |
| **11. Data-Quality Issues** | Sensor disconnect artifacts, unrecorded hours, out-of-range clinical entry errors. |
| **12. Data Format** | ASCII Pipe-Separated Values (`.psv` files with header row). |
| **13. Storage Size** | Lightweight: **~250 MB** total uncompressed text. |
| **14. Access Requirements** | **Open Public Access** via PhysioNet (no credentialing required). |
| **15. CareMind Utility** | Excellent source for discrete 5-vital time-series modeling, early sepsis alert prediction, and multi-vital risk scoring. |
| **16. Individual Analysis Use** | BP (SBP/DBP/MAP), $SpO_2$, Resp Rate, Temp, and HR can each be evaluated independently at every hourly time step. |
| **17. Multimodal Fusion Use** | Fusing all 5 vitals + lab trends per patient to predict hourly sepsis risk scores. |
| **18. Stream Replay Feasibility** | **High**: Hourly patient rows can easily be replayed sequentially to simulate hourly ICU monitor updates. |

---

## 5. Dataset Investigation 2: MIMIC-IV Waveform Database

### 5.1 Overview & Purpose
The MIMIC-IV Waveform Database Matched Subset contains thousands of high-resolution physiological waveform recordings paired with clinical telemetry monitors in Beth Israel Deaconess Medical Center (BIDMC) ICUs.

### 5.2 Detailed Specifications Table

| Question / Parameter | Detailed Dataset Finding |
| :--- | :--- |
| **1. What is the dataset?** | Public collection of high-frequency continuous physiological waveforms co-registered with ICU bed monitors. |
| **2. Patient Count** | Tens of thousands of waveform record sets matching a subset of MIMIC-IV clinical ICU admissions. |
| **3. Available Signals / Vitals** | Continuous multi-lead ECG (Leads I, II, III, V), Arterial Blood Pressure (ABP), Photoplethysmogram (PPG/$SpO_2$), Respiration (RESP), alongside 1 Hz numeric trend metrics. |
| **4. Patient Boundary** | Waveform record folders are indexed by `subject_id` (e.g., `p10000032`). All channels in a record set belong exclusively to that patient. |
| **5. Patient Identifiers** | `subject_id` and `stay_id` linked directly to MIMIC-IV relational clinical database tables. |
| **6. Timestamps** | Absolute start timestamp co-registered with high-frequency sample indexes. |
| **7. Sampling Frequency** | High-frequency continuous: ECG sampled at **125 Hz or 250 Hz**; ABP/PPG waveforms at **125 Hz**; numerics at **1 Hz**. |
| **8. Continuity** | **Continuous raw physiological waveforms**. |
| **9. Clinical Labels** | Linked via `stay_id` to MIMIC-IV clinical database providing in-hospital mortality, ICU length of stay, SOFA scores, and ICD-10 diagnoses. |
| **10. Missing Data** | Channels missing if specific sensors (e.g., arterial line) were not placed; signal dropouts during patient transport. |
| **11. Data-Quality Issues** | Severe baseline wander, motion artifacts, electrode disconnects, signal clipping. |
| **12. Data Format** | Binary WFDB format (`.dat` signal files + `.hea` ASCII header files). |
| **13. Storage Size** | **Multi-terabyte** (~1–5 TB total). Small representative subsets (10–50 patients) are ~5–20 GB. |
| **14. Access Requirements** | **Restricted Access**: Requires CITI training ("Data or Specimens Only Research"), PhysioNet credentialing, and signed DUA. |
| **15. CareMind Utility** | Primary source for high-frequency continuous waveform fusion (ECG + ABP + PPG) for acute hemodynamic collapse research. |
| **16. Individual Analysis Use** | Continuous ECG beat analysis, continuous ABP waveform pulse contour analysis, PPG pulse oxygenation analysis. |
| **17. Multimodal Fusion Use** | Co-registered high-frequency waveform fusion (ECG + ABP + PPG) to detect early hemodynamic instability. |
| **18. Stream Replay Feasibility** | **High**: Binary waveform frames can be streamed frame-by-frame over WebSockets to simulate high-fidelity ICU telemetry. |

---

## 6. Dataset Comparison & Signal Availability Matrix

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                               Comparative Dataset Matrix                                    │
├──────────────────────────┬──────────────────────────┬──────────────────────────┬────────────┤
│ Dimension                │ MIT-BIH (Completed Base) │ PhysioNet 2019 (Sepsis)  │ MIMIC-IV WF│
├──────────────────────────┼──────────────────────────┼──────────────────────────┼────────────┤
│ Primary Data Type        │ Continuous Waveform      │ Discrete Time-Series     │ Waveform   │
│ Sampling Resolution      │ 360 Hz                   │ 1 Sample / Hour          │ 125/250 Hz │
│ Access Level             │ Open Public              │ Open Public              │ Credential │
│ Total Size               │ ~100 MB                  │ ~250 MB                  │ 1-5 TB     │
│ Patient Linkage          │ 47 Subjects              │ 40,336 Patients          │ Tens of K  │
│ ECG Signal               │ Yes (2 Leads)            │ Indirect (HR only)       │ Yes (Multi)│
│ Blood Pressure (BP)      │ No                       │ SBP, DBP, MAP (Hourly)   │ Wave + 1Hz │
│ Oxygen Saturation (SpO₂) │ No                       │ O₂Sat (Hourly)           │ Wave + 1Hz │
│ Respiratory Rate (RR)    │ No                       │ Resp (Hourly)            │ Wave + 1Hz │
│ Body Temperature         │ No                       │ Temp (Hourly)            │ Discrete   │
│ Clinical Outcome Labels  │ Beat Annotations         │ Hourly Sepsis-3 Label    │ EHR Outcomes│
└──────────────────────────┴──────────────────────────┴──────────────────────────┴────────────┘
```

---

## 7. Patient-Level Data Integrity Rules

> **MANDATORY DATA RULE**: Under no circumstances should unrelated patients across different datasets be merged to manufacture a synthetic patient.

```
VALID WITHIN-PATIENT COMBINATION (SAME DATASET SUBJECT):
  PhysioNet Patient p000001:
  [ HR (68) + SBP (112) + DBP (70) + SpO₂ (98%) + Temp (37.1°C) ]  ──► VALID MULTIMODAL PATIENT

INVALID CROSS-DATASET MERGE (PROHIBITED):
  MIT-BIH Record 101 (ECG)
        +
  PhysioNet Patient p000001 (BP / Temp)
        +
  MIMIC Subject 10000032 (SpO₂)
        ↓
  [ Synthetic CareMind Patient ]  ──► STRICTLY INVALID & SCIENTIFICALLY UNJUSTIFIED
```

### Data Integrity Rules
1. **Subject Identity Retention**: Every dataset subject retains its unique original record identifier (`MIT-BIH #101`, `PhysioNet p000001`, `MIMIC subject_10000032`).
2. **Same-Patient Multimodal Fusion**: Multimodal fusion is **only** performed across physiological signals co-registered from the **same patient record** within the same dataset.
3. **Application Replay Abstraction**: The dashboard simulation IDs (`P01`, `P02`, `P03`) are runtime application aliases mapping to specific pre-processed dataset patient records for streaming demonstration purposes.

---

## 8. Detailed ETL Pipeline Designs

### 8.1 PhysioNet 2019 Sepsis Dataset ETL Pipeline

```
RAW DATA (.psv files)
       │
       ▼
┌──────────────┐
│   EXTRACT    │  ► Read pipe-delimited text files per patient (p000001.psv)
└──────┬───────┘
       │
       ▼
┌──────────────┐
│    CLEAN     │  ► Filter impossible vital values (e.g. SpO₂ > 100%, MAP < 20 mmHg)
└──────┬───────┘  ► Apply Forward Fill (LOCF) for missing vital values
       │          ► Impute remaining initial NaNs using overall population medians
       ▼
┌──────────────┐
│  TRANSFORM   │  ► Standardize units (Temp to Celsius, BP to mmHg)
└──────┬───────┘  ► Calculate derived features: MAP = DBP + (SBP - DBP)/3
       │          ► Compute rolling 3-hour mean and variance statistics
       ▼
┌──────────────┐
│PATIENT DATA  │  ► Output clean patient-level DataFrame (Patient_ID, TimeStep, Vitals, Label)
└──────┬───────┘
       │
       ├───────────────────────────────┐
       ▼                               ▼
┌──────────────┐                ┌──────────────┐
│ LEVEL 1 DATA │                │ LEVEL 2 DATA │
│ (Single-Vital│                │ (Multimodal  │
│ Thresholds)  │                │ Time-Series) │
└──────────────┘                └──────────────┘
```

#### Step-by-Step ETL Breakdown (PhysioNet 2019)

1. **EXTRACT Stage**:
   - **Input**: Raw `.psv` files from dataset folders (`/data/physionet2019/raw/`).
   - **Process**: Parse headers, load tabular time-series into Pandas DataFrames, index by patient file ID and hourly time step ($t$).
   - **Output**: Unfiltered raw time-series matrix per patient ($N \times 40$ features).
2. **CLEAN Stage**:
   - **Input**: Raw patient DataFrame.
   - **Process**: Outlier clipping based on physiological boundaries ($30 \le HR \le 220$, $50 \le SpO_2 \le 100$, $10 \le SBP \le 250$, $10 \le Temp \le 43$). Apply Forward Fill (Last Observation Carried Forward - LOCF) up to 6 hours for missing vitals. Impute remaining initial NaNs with cohort medians.
   - **Output**: Cleaned continuous time-series DataFrame with zero missing vital values.
3. **TRANSFORM Stage**:
   - **Input**: Cleaned vital DataFrame.
   - **Process**: Compute derived Mean Arterial Pressure ($MAP$). Compute rolling temporal trends ($\Delta HR/\Delta t$, $MAP$ slope over past 3 hours). Normalize features using `StandardScaler`.
   - **Output**: Transformed feature matrix ready for Level 1 evaluation and Level 2 multimodal model ingestion.

---

### 8.2 MIMIC-IV Waveform Dataset ETL Pipeline

```
RAW DATA (.hea + .dat binary files)
       │
       ▼
┌──────────────┐
│   EXTRACT    │  ► Read binary WFDB waveform headers and dat files using pywfdb
└──────┬───────┘  ► Extract matching channel signals (ECG, ABP, PPG)
       │
       ▼
┌──────────────┐
│    CLEAN     │  ► Zero-phase bandpass filtering (ECG: 0.5-40Hz; ABP/PPG: 0.5-15Hz)
└──────┬───────┘  ► Reject clipped or disconnected signal segments (flatlines)
       │
       ▼
┌──────────────┐
│  TRANSFORM   │  ► Downsample all waveform channels to a uniform 125 Hz frequency
└──────┬───────┘  ► Align multi-channel signal frames into synchronized 10-second windows
       │          ► Extract pulse peak locations and compute RR/PP intervals
       ▼
┌──────────────┐
│PATIENT DATA  │  ► Output synchronized multi-channel waveform array per subject
└──────────────┘
```

#### Step-by-Step ETL Breakdown (MIMIC-IV Waveform)

1. **EXTRACT Stage**:
   - **Input**: Binary WFDB signal files (`.dat`) and ASCII header files (`.hea`).
   - **Process**: Use `wfdb.rdrecord()` to parse signal headers, identify channel names (e.g., `II`, `ABP`, `PLETH`), and extract raw digital signal samples.
   - **Output**: Multi-channel raw waveform dictionary per patient stay.
2. **CLEAN Stage**:
   - **Input**: Raw waveform array.
   - **Process**: Apply signal-specific zero-phase Butterworth filters (0.5–40 Hz for ECG, 0.5–15 Hz for ABP and PPG). Reject flatline segments caused by lead disconnects.
   - **Output**: Noise-filtered continuous waveform signals.
3. **TRANSFORM Stage**:
   - **Input**: Cleaned multi-channel signals.
   - **Process**: Resample ECG signals to a uniform 125 Hz matching ABP and PPG channels. Segment signals into synchronized 10-second sliding windows. Calculate signal quality metrics (SQI).
   - **Output**: Clean, synchronized 10-second multimodal waveform tensor ($3 \times 1250$ samples) ready for representation encoding.

---

## 9. Data Quality & Missing Data Strategy

ICU physiological telemetry suffers from frequent missing values, sensor artifacts, and noise. CareMind employs a structured data-quality handling strategy:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Missing Data Taxonomy                           │
├──────────────────────────┬─────────────────────────────────────────────┤
│ Category                 │ Handling Strategy                           │
├──────────────────────────┼─────────────────────────────────────────────┤
│ Vital Sign Gaps (< 6 hrs)│ Forward Fill (Last Observation Carried Forward)│
│ Lab Value Gaps           │ Sample-and-Hold Imputation + Missingness Flag│
│ Initial Unrecorded Vitals│ Population / Cohort Median Imputation       │
│ Out-of-Range Artifacts   │ Hard Boundary Clipping to Physiological Min/Max│
│ Sensor Disconnect        │ Quality Flag = 0 (Exclude Window from Fusion)│
└──────────────────────────┴─────────────────────────────────────────────┘
```

---

## 10. Replay Engine & Dashboard Simulation Concept

CareMind bridges offline research datasets and real-time clinical monitoring via an **Asynchronous Replay Simulation Engine**.

```
┌────────────────────────────────────────────────────────────────────────┐
│                  Replay Simulation & Streaming Flow                    │
│                                                                        │
│   Pre-processed Patient Data (PhysioNet / MIMIC / MIT-BIH)             │
│                                  │                                     │
│                                  ▼                                     │
│   Asynchronous Replay Engine (FastAPI Backend)                         │
│   - Reads sequential time steps or 10s waveform frames                 │
│   - Maps dataset records to simulated bed IDs (P01, P02, P03)          │
│   - Controls playback speed (1.0x real-time up to 5.0x fast-forward)   │
│                                  │                                     │
│                                  ▼                                     │
│   WebSocket Broadcast Server (ws://.../ws/patients)                    │
│                                  │                                     │
│                                  ▼                                     │
│   CareMind Frontend Applications                                       │
│   - Computes Level 1 Single-Vital Statuses                             │
│   - Computes Level 2 Multimodal Patient Risk Scores                    │
│   - Renders HTML5 Canvas waveforms & patient triage list               │
└────────────────────────────────────────────────────────────────────────┘
```

> **Key Rule on Application IDs**: Dashboard patient IDs such as `P01`, `P02`, `P03` are **runtime application aliases** for the simulation UI. They are mapped internally to specific pre-processed dataset records (e.g., `P01` maps to PhysioNet record `p000001` or MIT-BIH record `101`).

---

## 11. Phase 4 Preparation & Strategy Recommendations

### 11.1 Individual Signal Analysis Strategy for Phase 4

| Signal | Analytical Approach | Justification |
| :--- | :--- | :--- |
| **ECG** | **Machine Learning (SVM / 1D CNN)** | Complex waveform morphology requires trained ML models (MIT-BIH baseline). |
| **Blood Pressure** | **Clinical Thresholding + Trend Rules** | $MAP < 60 \text{ mmHg}$ or $SBP > 180 \text{ mmHg}$ are clear, gold-standard clinical indicators. |
| **SpO₂** | **Clinical Thresholding + Duration** | $SpO_2 < 90\%$ provides immediate, unambiguous hypoxemic alert boundaries. |
| **Resp Rate** | **Clinical Thresholding + Score** | $RR > 24 \text{ bpm}$ indicates tachypnea; standard component of NEWS2 scoring. |
| **Temperature** | **Clinical Thermal Boundaries** | $Temp > 38.3^\circ\text{C}$ (fever) or $< 35^\circ\text{C}$ (hypothermia) follow deterministic medical rules. |

---

### 11.2 Multimodal Fusion Strategy for Phase 4

For Level 2 Multimodal Risk Prediction, CareMind will evaluate two primary fusion strategies:

1. **Late Softmax Ensembling**:
   - Combine softmax class probabilities or risk estimates from independent signal models using weighted averaging or logistic regression stacking.
   - *Advantage*: Highly modular; easy to inspect individual model contributions.
2. **Hybrid Temporal Recurrent Fusion**:
   - Concatenate signal representations (ECG features + BP stats + SpO2 dynamics) per time step and pass through an LSTM/GRU or Transformer temporal layer.
   - *Advantage*: Captures complex cross-vital interactions across time.

---

### 11.3 Recommended Dataset Strategy for Phase 4 Development

- **Primary Dataset for Discrete Multimodal Fusion (5 Vitals + Sepsis Risk)**:
  - **PhysioNet/CinC Challenge 2019 Sepsis Dataset** (Open access, 40,336 patients, complete 5-vital time-series, explicit Sepsis-3 early prediction target).
- **Primary Dataset for Single-Modality ECG Baseline**:
  - **MIT-BIH Arrhythmia Database** (Completed ECG baseline foundation).
- **Secondary Dataset for Continuous Multi-Waveform Fusion**:
  - A targeted subset of **VitalDB** or **MIMIC-IV Waveform** (10–20 patients) for high-frequency continuous waveform streaming experiments.

---

### 11.4 Required Preprocessing Tasks Before Multimodal Model Construction

1. Implement `PhysioNet2019Loader` script in Python to parse `.psv` files into structured DataFrames.
2. Implement `ForwardFillImputer` and `OutlierClipper` modules in `ml/preprocessing/`.
3. Construct clean, patient-level evaluation matrices containing synchronized 5-vital time-series.
4. Verify data splits (train/validation/test) using strict patient-level partitioning to ensure zero data leakage across patients.
