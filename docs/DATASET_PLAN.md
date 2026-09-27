# CareMind Dataset Evaluation & Selection Plan

> **Planning Document Notice**: This document presents a structured comparative analysis of candidate datasets for Phase 2 of the CareMind project. **No final dataset selection has been executed yet.** Further empirical data investigation and exploratory data analysis (EDA) must be completed before selecting datasets for multimodal model training.

---

## 1. Executive Summary & Strategy

CareMind is transitioning from a single-modality ECG baseline to a comprehensive multimodal clinical decision-support system. While the **MIT-BIH Arrhythmia Database** serves as the validated, completed single-modality ECG foundation, expanding to multi-vital risk prediction requires evaluating candidate datasets containing continuous physiological waveforms, discrete vital sign time-series, and clinical ICU outcomes.

---

## 2. Completed Dataset Foundation: MIT-BIH Arrhythmia Database

The MIT-BIH Arrhythmia Database is **already fully integrated** into the CareMind ECG baseline prototype and is not a new candidate dataset under investigation.

| Dataset Dimension | Specification / Status |
| :--- | :--- |
| **Status** | **Completed Foundation (Single-Modality ECG Baseline)** |
| **Purpose** | Benchmark evaluation of cardiac arrhythmia beat detection and AAMI classification. |
| **Physiological Signals** | 2-lead ECG (Modified Limb Lead II and Lead V1/V2/V4/V5). |
| **Patient/Record Structure** | 48 ambulatory ECG recordings (~30 minutes each) from 47 distinct subjects. |
| **Sampling Resolution** | 360 Hz per channel; 11-bit resolution over a 10 mV range. |
| **Labels / Outcomes** | ~110,000 beat annotations labeled into standard AAMI EC57 beat categories (`N`, `S`, `V`, `F`, `Q`). |
| **Signal Synchronization** | Both ECG leads are synchronously sampled. |
| **Access Requirements** | Public open access via PhysioNet (WFDB format). |
| **Dataset Size** | ~100 MB raw signal data. |
| **CareMind Role** | Foundation for single-lead and multi-lead ECG beat extraction, 11D tabular feature engineering, SVM baseline inference, 1D CNN/ResNet experiments, and streaming replay engine. |
| **Advantages** | Standardized benchmark, precise beat-level annotations, lightweight, data-leakage-free DS1/DS2 split defined by de Chazal et al. (2004). |
| **Limitations** | Single modality (ECG only), lacks clinical ICU outcomes (e.g., sepsis, mortality, shock), non-ICU ambulatory cohort. |
| **Multimodal Support** | **No** (Single-modality ECG only). |

---

## 3. Candidate Multimodal Datasets Evaluation

The following five datasets are candidate sources for Phase 2 multimodal expansion:

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                               Candidate Dataset Spectrum                                 │
│                                                                                          │
│  [MIT-BIH]             [PhysioNet 2019]            [VitalDB]            [MIMIC-IV / Waveform]│
│  Single ECG            Discrete Sepsis Vitals     High-Res Intraop      Comprehensive ICU   │
│  (Completed Base)      (Candidate)                (Candidate)           (Candidate)         │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

---

### Candidate 1: MIMIC-IV (Clinical Database)

- **Purpose**: Comprehensive, anonymized electronic health record (EHR) database covering hospital stays at Beth Israel Deaconess Medical Center.
- **Physiological Signals**: Discrete vital signs sampled hourly or as clinically recorded (Heart Rate, Invasive Blood Pressure, Non-invasive Blood Pressure, SpO2, Respiratory Rate, Body Temperature) alongside laboratory results, medications, and clinical notes.
- **Patient/Record Structure**: ~50,000 ICU admissions across thousands of unique patients. Relational database schema (`hosp` and `icu` modules).
- **Sampling/Time Resolution**: Discrete, non-uniform time-series (typically 1 hour sampling interval for ICU chart events).
- **Labels / Outcomes**: In-hospital mortality, ICU length of stay, ICD-9/ICD-10 diagnostic codes, organ failure scores (SOFA, SAPS II), sepsis onset.
- **Signal Synchronization**: Clinically time-stamped chart events; lack high-frequency raw waveform synchronization.
- **Access Requirements**: Restricted access via PhysioNet (requires CITI Training "Data or Specimens Only Research", signed Data Use Agreement).
- **Approximate Dataset Size**: ~20–30 GB compressed relational database.
- **Potential CareMind Use**: Benchmark dataset for discrete multi-vital risk prediction, clinical outcome prediction (e.g., mortality, sepsis), and baseline EHR fusion.
- **Advantages**: Massive sample size, real clinical ICU outcomes, comprehensive clinical context (vitals + labs + meds).
- **Limitations**: No high-frequency continuous waveforms, irregular sampling intervals, missing data gaps, restricted access compliance.
- **Multimodal Support**: **Yes** (fuses tabular vitals, lab values, and clinical outcome labels).

---

### Candidate 2: MIMIC-IV Waveform Database

- **Purpose**: High-frequency physiological waveform database paired with clinical telemetry monitors in BIDMC ICUs.
- **Physiological Signals**: High-resolution continuous waveforms including ECG (Leads I, II, III, V), Arterial Blood Pressure (ABP), Photoplethysmogram (PPG/SpO2), Respiratory Waveform (RESP), alongside matching numeric trend metrics (1 Hz).
- **Patient/Record Structure**: Tens of thousands of record sets matching a subset of MIMIC-IV clinical ICU stays.
- **Sampling/Time Resolution**: High frequency: ECG sampled at 125 Hz or 250 Hz; ABP/PPG at 125 Hz; Numerics at 1 Hz.
- **Labels / Outcomes**: Linked directly to MIMIC-IV clinical records via `stay_id` / `subject_id`, providing rich clinical outcome labels.
- **Signal Synchronization**: Multi-lead ECG, ABP, and PPG waveforms within a single record are synchronously sampled from the same patient bed monitor.
- **Access Requirements**: Restricted access via PhysioNet (CITI training + credentialing required).
- **Approximate Dataset Size**: Multi-terabyte (~1–5 TB depending on subset).
- **Potential CareMind Use**: Primary candidate for end-to-end continuous multimodal waveform fusion (ECG + ABP + PPG) for ICU shock and deterioration prediction.
- **Advantages**: Synchronized raw high-frequency multi-vital waveforms linked to real ICU clinical outcomes.
- **Limitations**: Massive storage and computational requirements, variable channel availability per patient, complex alignment between waveform records and clinical databases.
- **Multimodal Support**: **Yes** (High-frequency synchronized waveforms + clinical outcome linkage).

---

### Candidate 3: PhysioNet/CinC Challenge 2019 Sepsis Dataset

- **Purpose**: Early prediction of sepsis in ICU patients using clinical hourly time-series data.
- **Physiological Signals**: Discrete vital signs (HR, O2Sat, Temp, SBP, MAP, DBP, Resp, EtCO2) recorded hourly, alongside 26 laboratory metrics and demographics.
- **Patient/Record Structure**: 40,336 ICU patient records from two distinct hospital systems (ICU A: 20,336 patients; ICU B: 20,000 patients).
- **Sampling/Time Resolution**: Regular 1-hour interval discrete time-series grid up to 168 hours per patient.
- **Labels / Outcomes**: Binary hourly `SepsisLabel` (1 if sepsis onset occurs within the next 6 hours, 0 otherwise) defined by Sepsis-3 criteria.
- **Signal Synchronization**: Discrete hourly aligned time-series grid.
- **Access Requirements**: Open access public dataset on PhysioNet (no credentialing required).
- **Approximate Dataset Size**: ~250 MB CSV text files.
- **Potential CareMind Use**: Benchmark for discrete multi-vital time-series modeling, early sepsis alert prediction, and dynamic risk scoring evaluation.
- **Advantages**: Pre-formatted standardized benchmark, explicit 6-hour early prediction clinical label, open access, lightweight.
- **Limitations**: Lacks raw high-frequency waveforms (no raw ECG/PPG waveforms), high proportion of missing laboratory values.
- **Multimodal Support**: **Partial** (Multimodal across discrete vitals and lab tests; lacks continuous waveforms).

---

### Candidate 4: VitalDB (Intraoperative & ICU Dataset)

- **Purpose**: High-resolution intraoperative and intensive care surgical recording database from Seoul National University Hospital.
- **Physiological Signals**: High-density multi-channel waveforms (ECG, Arterial Line BP, PPG, EEG, Bispectral Index) sampled up to 500 Hz, alongside synchronized 1 Hz numerical trend vitals, lab results, and surgical parameters.
- **Patient/Record Structure**: 6,388 surgical patients with detailed perioperative tracking.
- **Sampling/Time Resolution**: Waveforms at 100–500 Hz; numerics at 1 Hz; clinical data tabular.
- **Labels / Outcomes**: Postoperative mortality, acute kidney injury (AKI), hypothetical intraoperative hypotension (IOH), length of stay.
- **Signal Synchronization**: Fully synchronized across all recorded waveforms via hardware time-stamps.
- **Access Requirements**: Open research access via Python `vitaldb` library or direct download.
- **Approximate Dataset Size**: ~300 GB compressed.
- **Potential CareMind Use**: High-resolution continuous multi-vital signal fusion experiments (ECG + ABP + SpO2) and real-time streaming replay simulation.
- **Advantages**: High-resolution synchronized multi-signal waveforms, open access API, minimal missing data during surgical cases.
- **Limitations**: Intraoperative/surgical population differs from general medical ICU cohorts; clinical outcome events differ from medical ICU sepsis/shock.
- **Multimodal Support**: **Yes** (Synchronized high-frequency multi-vital waveforms + trend numerics).

---

## 4. Cross-Dataset Comparison Matrix

| Dataset | Access | Modality Type | Primary Vitals | High-Res Waveforms? | Clinical Outcomes | Multimodal Fusion Potential |
| :--- | :---: | :--- | :--- | :---: | :---: | :---: |
| **MIT-BIH** *(Completed)* | Open | Waveform | ECG | Yes (360 Hz) | Arrhythmia Beats | Single Modality (Baseline) |
| **MIMIC-IV (Clinical)** | Credentialed | Discrete Tabular | HR, BP, SpO2, Temp, Resp | No | Mortality, ICU LOS, Sepsis | High (Tabular Vitals + Labs) |
| **MIMIC-IV Waveform** | Credentialed | Waveform + Trend | ECG, ABP, PPG, RESP | Yes (125/250 Hz) | Linked to MIMIC-IV | Highest (Raw Waveforms + EHR) |
| **PhysioNet 2019** | Open | Discrete Tabular | HR, BP, SpO2, Temp, Resp | No | Sepsis-3 (Hourly) | Moderate (Discrete Vitals) |
| **VitalDB** | Open | Waveform + Trend | ECG, ABP, PPG, EEG | Yes (100-500 Hz) | AKI, IOH, Mortality | High (Surgical Multi-vital) |

---

## 5. Critical Challenges in Dataset Alignment & Merging

> **Methodological Precaution**: Datasets from different hospital cohorts **cannot be naively concatenated or merged into a single training matrix**. The following technical challenges must be addressed during dataset evaluation:

1. **Lack of Cross-Dataset Patient Linkage**: Patients in MIT-BIH, PhysioNet 2019, VitalDB, and MIMIC-IV are completely distinct cohorts. Record `#101` in MIT-BIH has no relationship to Patient `10000032` in MIMIC-IV.
2. **Temporal & Frequency Mismatch**:
   - MIT-BIH ECG: 360 Hz
   - MIMIC-IV Waveforms: 125 Hz / 250 Hz
   - VitalDB Waveforms: 100–500 Hz
   - PhysioNet 2019 / MIMIC-IV Clinical Vitals: 1 hour discrete sampling
   - Merging requires signal resampling, anti-aliasing filtering, and temporal window synchronization.
3. **Cohort & Clinical Domain Shift**:
   - MIT-BIH: Ambulatory ECG subjects.
   - VitalDB: Surgical operative patients under anesthesia.
   - MIMIC-IV / PhysioNet 2019: Medical and surgical ICU patients.
4. **Missing Modality Gaps**: Not all patients in waveform databases have all sensors attached simultaneously (e.g., invasive arterial lines are only placed in critically unstable patients).

---

## 6. Dataset Selection Criteria

Before confirming dataset selection for Phase 2, candidate datasets will be evaluated against the following nine criteria:

```
┌───────────────────────────────────────────────────────────────────────────┐
│                       Dataset Selection Criteria Matrix                   │
├──────────────────────────┬────────────────────────────────────────────────┤
│ Criterion                │ Evaluation Objective                           │
├──────────────────────────┼────────────────────────────────────────────────┤
│ 1. Multimodal Availability│ Contains ECG, BP, SpO2, Resp Rate, and Temp.   │
│ 2. Patient-Level Linkage │ Synchronized vitals linked to single patients. │
│ 3. Temporal Alignment    │ Co-registered timestamp alignment across vitals│
│ 4. Clinical Labels       │ Clear deterioration outcomes (sepsis, shock).  │
│ 5. Sample Size           │ Sufficient statistical power & cohort size.    │
│ 6. Accessibility         │ Open access vs credentialed IRB requirements.  │
│ 7. Compute Requirements  │ Feasibility of storage, memory, and training.  │
│ 8. Reproducibility       │ Public benchmark transparency and standard.    │
│ 9. Research Suitability  │ Directly addresses the CareMind research Qs.   │
└──────────────────────────┴────────────────────────────────────────────────┘
```

---

## 7. Next Steps & Dataset Investigation Tasks

1. Conduct exploratory data analysis (EDA) on candidate datasets (PhysioNet 2019 and VitalDB open subsets first, followed by MIMIC-IV credentialing verification).
2. Determine whether CareMind will use a **discrete multi-vital time-series approach** (PhysioNet 2019 / MIMIC-IV Clinical) or a **raw continuous waveform fusion approach** (VitalDB / MIMIC-IV Waveform), or a **tiered multi-dataset evaluation strategy**.
3. Establish data preprocessing scripts, missing-value imputation protocols, and resampling pipelines for the chosen dataset cohort.
