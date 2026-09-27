# CareMind End-to-End System Architecture

> **Architectural Specification**: This document details the conceptual end-to-end architecture of the CareMind clinical decision-support system. It highlights the data ingestion flow, preprocessing pipelines, model representation, multimodal fusion layer, risk scoring, explainability modules, API microservices, storage infrastructure, and user applications.

---

## 1. System Conceptual Data Flow

The CareMind platform operates via a multi-stage pipeline processing continuous and discrete physiological data into actionable clinical insights.

```
┌────────────────────────────────────────────────────────────────────────┐
│                          Physiological Data                            │
│           (ECG, Blood Pressure, SpO2, Resp Rate, Temperature)          │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        Data Ingestion / Replay                         │
│            (WFDB Signal Streams, Multi-Bed Replay Engine)              │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      Signal-specific Preprocessing                     │
│      (ECG Butterworth Bandpass, BP Filtering, Outlier Rejection)       │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                 Signal-specific Representation / Models                │
│     (ECG 11D Tabular / 1D CNN, BP Statistics, SpO2 Dynamics)           │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                           Multimodal Fusion                            │
│           (Early Concatenation / Late Softmax / Hybrid Temporal)        │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                          Patient Risk Engine                           │
│              (Composite Risk Scoring, Patient Instability)             │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      Explainability + Uncertainty                      │
│         (SHAP Values, Saliency Mapping, MC Dropout Uncertainty)        │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        Alerts / Prioritization                         │
│          (Ward Triage Queue, Status: Critical / Warning / Normal)      │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                            FastAPI Backend                             │
│             (ML API Layer, WebSockets, REST Endpoints, CORS)           │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      Supabase / PostgreSQL Data                        │
│            (Persistence Layer: Auth, Patient DB, Audit Logs)           │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                       Presentation Application Layer                   │
│          ├── React Web Dashboard (Central ICU Bed Monitors)            │
│          └── Android App (Mobile Ward Rounds & Alerts)                 │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Layer Responsibilities & Component Breakdown

### 2.1 Ingestion & Preprocessing Layer
- **Data Ingestion / Replay**: Streams pre-recorded ICU waveform and vital sign time-series via an asynchronous replay service mimicking live bedside monitor telemetry.
- **Signal-Specific Preprocessing**: Each vital sign undergoes dedicated noise filtering (e.g., zero-phase Butterworth bandpass filtering for ECG, baseline wander removal, median filtering for BP artifacts, clipping range checks).

### 2.2 Feature Representation & ML Layer
- **Signal-Specific Representation / Models**:
  - **ECG**: Extracts 250-sample beat windows, calculates 11D statistical/temporal features, or generates deep embeddings via 1D CNN/ResNet.
  - **Blood Pressure (BP)**: Computes Systolic, Diastolic, Mean Arterial Pressure (MAP), and short-term variability statistics.
  - **SpO2 & Resp Rate**: Extracts desaturation frequencies, trend slopes, and respiration dynamics.
- **Multimodal Fusion Layer**: Combines representation vectors across modalities using late fusion probability ensembles or hybrid recurrent/attention fusion blocks.
- **Patient Risk Engine**: Aggregates composite multi-vital predictions into a unified patient risk score $S_i \in [0, 100]$.

### 2.3 Interpretability & Prioritization Layer
- **Explainability + Uncertainty**: Computes gradient saliency for waveforms, SHAP values for tabular vitals, and Monte Carlo Dropout variances to output confidence bounds alongside predictions.
- **Alerts / Prioritization Engine**: Manages ward-level triage logic, maintaining a real-time dynamic patient priority queue sorted by severity.

### 2.4 Application API & Infrastructure Layer
- **FastAPI Backend (Application & ML API Layer)**:
  - Serves as the central microservice orchestrator.
  - Executes real-time ML inference.
  - Exposes RESTful endpoints for patient data, predictions, and replay engine control.
  - Maintains WebSocket connections (`ws://.../ws/patients`) pushing sub-second updates to clients.
- **Supabase / PostgreSQL (Data, Auth & Storage Layer)**:
  - Serves as the persistent data storage and authentication provider.
  - Stores patient metadata, historical vital logs, model execution audit logs, user credentials, and alert history.
  - Operates independently from the stateless FastAPI ML inference engine to maintain low-latency streaming performance.

### 2.5 User Interface Layer
- **React Web Dashboard**: Central ICU monitoring interface featuring HTML5 Canvas waveform rendering, patient risk cards, trend plots, and explainability modals.
- **Android Mobile App**: Mobile application delivering push notification alerts, quick patient status summaries, and vital sign overview for mobile clinicians.

---

## 3. Baseline ECG Prototype Integration into CareMind Architecture

The completed `CareMind-ECG` prototype maps directly into this architectural framework as the first single-modality operational pipeline:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Baseline ECG Subsystem Flow                     │
├────────────────────────────────────────────────────────────────────────┤
│ MIT-BIH Waveforms ──► 0.5-40Hz Bandpass ──► Beat Windowing (250 Smp)    │
│                                                     │                  │
│                                                     ▼                  │
│ 5-Class AAMI Output ◄── SVM Model (.joblib) ◄── 11D Feature Extractor  │
│          │                                                             │
│          ▼                                                             │
│ Replay Engine (P01-P05) ──► FastAPI WebSockets ──► React ECG Canvas    │
└────────────────────────────────────────────────────────────────────────┘
```

- **Preprocessing & Features**: Implemented via `src/preprocessing.py`, `src/segmentation.py`, and `src/feature_extraction.py`.
- **Model Inference**: Implemented via `models/ecg/caremind_ecg_model/baseline_svm.joblib` and `backend/model/model_loader.py`.
- **Replay Engine**: Implemented via `backend/services/replay_engine.py`.
- **API & UI**: Implemented via `backend/main.py` and `frontend/src/App.jsx`.

---

## 4. Expansion Architecture for Phase 2 Multimodal Modules

In Phase 2, additional signal processing modules (`bp`, `spo2`, `respiratory_rate`, `temperature`) will be integrated alongside `ecg`:

```
                               ┌──► ECG Pipeline ──────┐
                               ├──► BP Pipeline ───────┤
Physiological Telemetry Streams ┼──► SpO2 Pipeline ─────┼──► Multimodal Fusion ──► Risk Engine
                               ├──► Resp Rate Pipeline ┤
                               └──► Temp Pipeline ─────┘
```

Each module will maintain a modular structure inside `ml/<modality>/` containing preprocessing, feature extraction, and model representation definitions.
