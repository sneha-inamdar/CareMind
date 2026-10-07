# CareMind — 5–10 Minute Professor Demonstration Guide

This guide provides an step-by-step walkthrough to demonstrate CareMind during your Project-Based Learning (PBL) presentation.

---

## 1. Quick System Launch

Run the following commands in separate terminals to start the complete system:

### Terminal 1: FastAPI Backend & ML Engine
```bash
python -m uvicorn backend.main:app --reload --port 8000
```
- API Documentation & Swagger UI: `http://localhost:8000/docs`
- Web Command Center: `http://localhost:8000/`

### Terminal 2: Flutter Application (Mobile / Web)
```bash
cd mobile
flutter run -d chrome
```

---

## 2. Step-by-Step Demonstration Flow (5–10 Minutes)

### Step 1: Real Physiological Dataset Provenance (1 Minute)
- Open **Research & Evaluation** tab in the Web Dashboard (`http://localhost:8000/#research`).
- Explain the 3 benchmark datasets:
  1. **MIT-BIH Arrhythmia Database**: Heartbeat classification & baseline ECG signal processing.
  2. **PhysioNet 2019 Sepsis Challenge**: Hourly ICU tabular observations benchmarked with patient-level splitting.
  3. **MIMIC-IV / MIMIC-IV Waveform (`mimic4wdb/0.1.0`)**: Real 24-patient ICU waveform cohort across Tier 1 (ECG+ABP+PPG), Tier 2 (ECG+PPG), and Tier 3 (ECG only).

### Step 2: Single-Signal ML vs. 1D CNN Deep Learning (2 Minutes)
- In the **Research & Evaluation** view, highlight the **Model Comparison Matrix**:
  - **ECG Baseline**: SVM (Handcrafted Features) vs. **1D CNN Baseline** (Learned representations from raw 1D signals in PyTorch).
  - Show how learned 1D CNN representations capture complex temporal morphology without manual feature engineering.

### Step 3: Unimodal vs. Multimodal Fusion (2 Minutes)
- Point to the quantitative comparison table across patient-level splits (zero patient leakage):
  - **PPG-Only**: ROC-AUC = 0.5465, F1 = 0.3103
  - **ABP-Only**: ROC-AUC = 0.6933, F1 = 0.5714
  - **Clinical-Vitals-Only**: ROC-AUC = 0.7712, F1 = 0.6087
  - **Waveform-Only (ECG+PPG+ABP)**: ROC-AUC = 0.7989, F1 = 0.7042
  - **CareMind Multimodal Fusion**: **ROC-AUC = 0.8276**, **PR-AUC = 0.8516**, **F1 = 0.7324**
- Explain: Multimodal fusion provides superior sensitivity and robustness compared to any single modality.

### Step 4: CareMind Physiological Risk Score & Explainability (2 Minutes)
- Switch to the **Overview / Patient Priority** tab (`http://localhost:8000/`).
- Show the **CareMind Physiological Risk Score** (0–100 continuous instability index).
- Click on a High-Risk patient (e.g., Patient #10020306) to open the **Patient Detail Inspection View**:
  - Display continuous ECG, PPG, and ABP signal traces.
  - Review **Structured Explainability Factors**: Show exact physiological evidence (e.g., *"HR of 104.0 bpm exceeds tachycardia threshold"*, *"Rapid risk score escalation (+8.4 points)"*).

### Step 5: Dynamic Multi-Patient ICU Prioritization & Replay (2 Minutes)
- Demonstrate dynamic patient ranking: Patients are automatically re-ranked in real-time by highest risk score first.
- Click **"⏭ Step"** in the top control bar to advance the 15-minute observation window:
  - Watch risk scores update dynamically.
  - Observe active alerts triggering and patients re-ranking automatically.

### Step 6: Multi-Platform Architecture & Database Persistence (1 Minute)
- Showcase the **Flutter App** running concurrently on mobile/web.
- Explain the decoupled clean architecture:
  `ML Engine -> FastAPI REST API -> Supabase PostgreSQL / Local Cache -> React Web + Flutter Mobile`

---

## 3. Key Technical Statements to Emphasize

1. **"CareMind is a physiological decision-support metric, not a diagnosis."**
2. **"Observation windows use 30-second continuous waveform blocks linked to chart vitals without artificial synthetic data."**
3. **"Evaluation strictly enforces patient-level splitting — windows from the same patient never leak into train and test sets."**
4. **"The system gracefully handles missing modalities via an adaptive late-fusion firewall."**
