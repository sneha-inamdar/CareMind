# CareMind: AI-Based Multimodal ICU Clinical Decision-Support System

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.0+-61DAFB?style=flat&logo=react&logoColor=black)](https://reactjs.org/)
[![Status](https://img.shields.io/badge/Phase-5A%20Baseline%20Sepsis%20Model%20Completed-brightgreen)](#project-status)

> **Clinical Disclaimer**: CareMind is an academic research software project and a clinical decision-support system (CDSS) prototype. Model outputs, alert scores, and patient prioritization rankings are decision-support insights intended to assist clinicians. CareMind is strictly a decision-support system, **NOT** a substitute for clinical judgment, medical diagnosis, direct patient evaluation, or primary ICU monitoring equipment.

---

## Overview

**CareMind** is an AI-based multimodal Intensive Care Unit (ICU) clinical decision-support platform designed for early patient risk prediction, multi-vital signal monitoring, dynamic patient triage, and explainable decision support.

By analyzing physiological telemetry (ECG, blood pressure, oxygen saturation, respiratory rate, and body temperature) alongside clinical data, CareMind helps clinical teams detect early signs of instability, reduce alarm fatigue, and prioritize attention toward high-risk patients.

---

## Completed Milestones

### 1. Baseline ECG Prototype Foundation
- **Dataset Standard**: Processed 48 records from the PhysioNet MIT-BIH Arrhythmia Database (360 Hz) using the de Chazal et al. (2004) DS1/DS2 inter-patient partition (51,002 train beats, 49,692 test beats).
- **Preprocessing & Windowing**: 0.5–40 Hz 2nd-order Butterworth bandpass filter with 250-sample R-peak windowing.
- **11D Tabular Feature Extraction**: Statistical, morphological, and temporal RR interval features per beat.
- **SVM Model Inference**: Production baseline using `StandardScaler` + `SVC` mapped to 5 standard AAMI beat categories (`N`, `S`, `V`, `F`, `Q`).
- **Deep Learning & Explainability**: Evaluated 1D CNN / 1D ResNet models, gradient saliency maps, and Monte Carlo Dropout uncertainty bounds.
- **Streaming Replay & UI**: 5-patient simulated real-time replay engine over WebSockets with a React visual testing dashboard.

### 2. PhysioNet 2019 Data Acquisition & Leakage-Free ETL (Phase 4A Milestone)
- **Official Data Source**: PhysioNet/CinC Challenge 2019 Sepsis Dataset.
- **Reproducible Acquisition**: Direct multi-threaded server fetch script (`src/physionet2019/downloader.py`).
- **Data Profiling & Validation**: Checked row/file counts, temporal monotonicity, missingness, and physiological range bounds (`src/physionet2019/validator.py`).
- **ETL Cleaning & Train-Only Imputation**: Outlier clipping and train-only fitted LOCF + cohort median imputation (`src/physionet2019/cleaner.py`).
- **Feature Transformation**: Missingness indicators, 1h/3h temporal deltas, and 3h rolling window statistics (`src/physionet2019/transformer.py`).
- **Leakage-Safe Patient Splitting**: 70/15/15 stratified patient-level partitioning with 0% patient overlap (`src/physionet2019/splitter.py`).
- **Parquet Outputs**: Saved `train.parquet`, `val.parquet`, `test.parquet`, and `dataset_metadata.json` under `data/physionet2019/processed/`.

### 3. PhysioNet 2019 Dataset-Wide EDA & Characterization (Phase 4B Milestone)
- **Structure & Demographics**: Analyzed 500 patients (19,278 hourly rows; median stay 39.0h; 62.6% male, mean age 61.5).
- **Sepsis Target Isolation**: Evaluated 9.00% patient prevalence (45 positive patients) and 2.25% hourly prevalence (433 positive hours). Target strictly designated for temporal sepsis experiment.
- **Missingness Taxonomy**: Classified vitals (<16% missing: HR, MAP, SBP, Resp, O2Sat), intermittent vitals (30-70%: DBP, Temp), and sparse labs (>85%: Lactate, WBC, etc.).
- **Exploration Notebook Review**: Integrated Sneha's manual exploration (`CareMind_PhysioNet2019_Exploration.ipynb`), confirming high lab missingness and tachycardia trends at dataset scale while isolating single-patient specificities.
- **Candidate Feature Taxonomy**: Defined Group A (Core Vitals), Group B (Intermittent Vitals), Group C (Engineered Deltas + Rolling Stats + Missingness Indicators), and Group D (Excluded Sparse Labs).

### 4. PhysioNet 2019 Baseline Temporal Sepsis Model (Phase 5A Milestone)
- **Reproducible Experiment Pipeline**: Built `src/physionet2019/baseline.py` and `experiments/phase5a_baseline/run_phase5a_experiments.py`.
- **Feature Exclusions & Safety**: Excluded target (`SepsisLabel`), identifiers (`patient_id`), operational metrics (`ICULOS`), and sparse labs (>85% missingness).
- **Leakage-Free Validation**: Fitted models strictly on Train split (350 patients), tuned decision threshold ($\tau=0.5148$) on Validation split (75 patients), evaluated once on holdout Test set (75 patients).
- **Best Model Results (Random Forest COMBINED)**: Holdout Test **PR-AUC = 0.0970** (4.75x random baseline 0.0204), **ROC-AUC = 0.7090**, Precision = 0.1176, Recall = 0.2373, F1 = 0.1573.
- **Single-Vital Ablation**: Demonstrated that combined vitals (PR-AUC 0.0970) significantly outperform individual signal models (`HR_ONLY` 0.0357, `TEMP_ONLY` 0.0388, `BP_ONLY` 0.0288).

---

## Technical Documentation Roadmap

Comprehensive planning documents are located in the [`docs/`](file:///c:/Users/Sneha/Desktop/College%20sem%205/project/CareMind/docs) directory:

- 📄 [**`MIMIC_MULTIMODAL_EXPERIMENT_REPORT.md`**](file:///c:/Users/Sneha/Desktop/College%20sem%205/project/CareMind/docs/MIMIC_MULTIMODAL_EXPERIMENT_REPORT.md): **[NEW Multimodal Experiment Report]** Clinical vs Waveform vs Multimodal baseline evaluation report, patient-level split metrics, decision thresholds, and feature attributions.
- 📄 [**`MIMIC_WAVEFORM_EXPERIMENT_REPORT.md`**](file:///c:/Users/Sneha/Desktop/College%20sem%205/project/CareMind/docs/MIMIC_WAVEFORM_EXPERIMENT_REPORT.md): MIMIC-IV Waveform Database (v0.1.0) inspection report, channel availability, linkage mechanism, sampling rates, 24h zero-leakage firewall, and baseline feature extraction.
- 📄 [**`MIMIC_RESEARCH_AND_DATA_PLAN.md`**](file:///c:/Users/Sneha/Desktop/College%20sem%205/project/CareMind/docs/MIMIC_RESEARCH_AND_DATA_PLAN.md): Comprehensive MIMIC-IV Clinical & Waveform research plan, target outcome definition, feature taxonomy, subset specifications, and PhysioNet access instructions.
- 📄 [**`PHASE_5A_BASELINE_REPORT.md`**](file:///c:/Users/Sneha/Desktop/College%20sem%205/project/CareMind/docs/PHASE_5A_BASELINE_REPORT.md): Baseline temporal sepsis model report (Research question, feature taxonomy, leakage checks, validation/test results, ablation matrix, limitations, next steps).
- 📄 [**`PHASE_4B_PHYSIONET_EDA_REPORT.md`**](file:///c:/Users/Sneha/Desktop/College%20sem%205/project/CareMind/docs/PHASE_4B_PHYSIONET_EDA_REPORT.md): Dataset-wide EDA and characterization of PhysioNet 2019 (Structure, SepsisLabel behavior, missingness taxonomy, physiological distributions, correlations, notebook findings integration, feature taxonomy).
- 📄 [**`PHASE_4A_ETL_REPORT.md`**](file:///c:/Users/Sneha/Desktop/College%20sem%205/project/CareMind/docs/PHASE_4A_ETL_REPORT.md): Master documentation for PhysioNet 2019 zero-leakage ETL pipeline, fitted train-only cleaning decisions, observed statistics, parquet schema, and reproduction guide.
- 📄 [**`PHASE_3_PHYSIOLOGICAL_DATA_REPORT.md`**](file:///c:/Users/Sneha/Desktop/College%20sem%205/project/CareMind/docs/PHASE_3_PHYSIOLOGICAL_DATA_REPORT.md): In-depth investigation of PhysioNet 2019 & MIMIC-IV Waveform, Two-Level Analysis Framework, Patient-Level Data Integrity Rules, and Detailed ETL Pipeline Designs.
- 📄 [**`PROJECT_DESIGN.md`**](file:///c:/Users/Sneha/Desktop/College%20sem%205/project/CareMind/docs/PROJECT_DESIGN.md): Detailed problem statement, objectives, completed ECG work, research questions, experimental strategy, and roadmap.
- 📄 [**`DATASET_PLAN.md`**](file:///c:/Users/Sneha/Desktop/College%20sem%205/project/CareMind/docs/DATASET_PLAN.md): Comparative analysis of candidate multimodal datasets (MIMIC-IV, MIMIC-IV Waveform, PhysioNet 2019, VitalDB), cross-dataset alignment challenges, and selection criteria.
- 📄 [**`ARCHITECTURE.md`**](file:///c:/Users/Sneha/Desktop/College%20sem%205/project/CareMind/docs/ARCHITECTURE.md): End-to-end data flow, layer responsibilities, FastAPI ML API layer, Supabase/PostgreSQL storage layer, and UI specifications.
- 📄 [**`ECG_INTEGRATION_PLAN.md`**](file:///c:/Users/Sneha/Desktop/College%20sem%205/project/CareMind/docs/ECG_INTEGRATION_PLAN.md): Detailed migration guide for integrating the standalone ECG baseline prototype into CareMind.

---

## Quickstart & Reproduction Commands

### Run PhysioNet 2019 Data Acquisition & ETL Pipeline
```bash
# Execute ETL pipeline on 500 patient cohort
python run_physionet2019_etl.py --max-patients 500 --seed 42

# Execute automated ETL test suite
python -m pytest tests/test_physionet2019_etl.py
```

---


## Target Project Structure

```text
CareMind/
├── backend/                          # FastAPI application & ML inference microservice
├── ml/                               # Machine learning modules (ecg, bp, spo2, resp, temp)
├── models/                           # Saved model artifacts (.joblib, .pt)
├── data/                             # Dataset storage directory (.gitignore)
├── notebooks/                        # Research Jupyter notebooks
├── tests/                            # Pytest automated test suite
├── docs/                             # Project planning & architectural documentation
└── frontend/                         # React web dashboard application
```

---

## License & Citation

CareMind is developed for academic research purposes. Datasets utilized (e.g., MIT-BIH Arrhythmia Database) are subject to PhysioNet Open Data / Health Data licenses.
