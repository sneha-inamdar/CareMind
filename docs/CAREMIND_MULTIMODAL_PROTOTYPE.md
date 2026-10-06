# CareMind Multimodal Physiological Risk Engine Prototype

> **CRITICAL CLINICAL DISCLAIMER:**
> *The current prototype demonstrates multimodal physiological fusion using real waveform/numeric data. It is not a clinically validated mortality prediction model. Full-scale MIMIC mortality evaluation requires the credentialed MIMIC-IV Clinical dataset.*

---

## 1. Executive Purpose

The **CareMind Multimodal Physiological Risk Engine Prototype** provides a demonstrable, functional decision-support system for ICU clinical environments. It demonstrates end-to-end continuous signal ingestion, bedside vital extraction, modality encoding, feature fusion, composite physiological risk scoring (0–100 scale), risk categorisation (`LOW`, `MEDIUM`, `HIGH`), and physiological factor explainability.

---

## 2. Available Datasets & Scope Strategy

The prototype operates strictly on **REAL observed physiological data** without synthetic pseudo-waveforms or fake records:

1. **MIMIC-IV Waveform Database v0.1.0 (PhysioNet Open Access):**
   - High-frequency continuous waveform streams: ECG (Lead II, V, aVR), Photoplethysmogram (PPG/PLETH), Arterial Blood Pressure (ABP).
2. **MIMIC-IV Clinical Database Demo v2.2:**
   - Bedside monitor trend numerics: Heart Rate (HR), Oxygen Saturation (SpO2), Respiratory Rate (Resp), Blood Pressure (SysBP, DiaBP, MAP), Body Temperature (Temp).

---

## 3. Real Cohort & Selected Demonstration Records

Three deterministic real records from `mimic4wdb/0.1.0` linked to MIMIC-IV clinical subjects are used for reproducible demonstration:

| Record ID | Subject ID | Stay ID | Available Modalities | Signal Fs | Description / Physiological Profile |
|---|---|---|---|---|---|
| `81739927` | 10014354 | 39880770 | ECG, PPG, Resp, Vitals | 62.5 Hz | Tier 2 record exhibiting progressive HR elevation & SpO2 decline |
| `83404654` | 10020306 | 38418938 | ECG, PPG, Resp, Vitals | 62.5 Hz | Tier 2 record showing persistent moderate-to-high tachycardia |
| `82924339` | 10126957 | 39149479 | ECG, PPG, ABP, Resp, Vitals | 125.0 Hz | Tier 1 record demonstrating acute arterial hypotension & shock dynamics |

---

## 4. Modalities & Extracted Feature Vectors

### A. Clinical / Numeric Features (Bedside Vitals)
- `HR`: Heart Rate (bpm)
- `SpO2`: Blood Oxygen Saturation (%)
- `Resp`: Respiratory Rate (breaths/min)
- `SysBP`: Systolic Blood Pressure (mmHg)
- `DiaBP`: Diastolic Blood Pressure (mmHg)
- `MAP`: Mean Arterial Pressure (mmHg)
- `Temp`: Body Temperature (°C)

### B. Continuous Waveform Features
- **ECG:** `ECG_mean`, `ECG_std`, `ECG_rms`, `ECG_ptp`, `ECG_zero_crossings`, `ECG_is_missing`
- **PPG:** `PPG_mean`, `PPG_std`, `PPG_peak_max`, `PPG_trough_min`, `PPG_amplitude_range`, `PPG_is_missing`
- **ABP:** `ABP_mean`, `ABP_std`, `ABP_sys_max`, `ABP_dia_min`, `ABP_pulse_pressure`, `ABP_is_missing`

---

## 5. Multimodal Fusion Architecture

The prototype implements a robust 3-stage fusion pipeline:

```
  Clinical Bedside Vitals                Continuous Waveforms (ECG, PPG, ABP)
             │                                              │
             ↓                                              ↓
   Clinical Modality Encoder                     Waveform Modality Encoder
  (StandardScaler + LogReg)                     (StandardScaler + LogReg)
             │                                              │
             ├──────────────────────────────┬───────────────┘
                                            ↓
                                 Stage 2: Feature Fusion
                                (Concatenate Derived Representations)
                                            ↓
                                 Stage 3: Fusion Model
                             (Scikit-Learn Logistic Regression)
                                            ↓
                                Dynamic Composite Risk Score
                                           0 – 100
                                            ↓
                                     Risk Category
                                 LOW / MEDIUM / HIGH
```

### Stage 1 — Modality Encoders
- **Clinical Encoder:** Standardises bedside vitals via `StandardScaler` and estimates clinical instability probability $P_{\text{clin}} \in [0, 1] \rightarrow \text{Clinical Score} \in [0, 100]$.
- **Waveform Encoder:** Standardises statistical signal features via `StandardScaler` and computes signal instability probability $P_{\text{wave}} \in [0, 1] \rightarrow \text{Waveform Score} \in [0, 100]$.

### Stage 2 & 3 — Feature Fusion & Risk Scoring
- Concatenates modality scores and interaction terms: $[S_{\text{clinical}}, S_{\text{waveform}}, (S_{\text{clinical}} \cdot S_{\text{waveform}})/100]$.
- Applies Logistic Regression fusion model to output a composite risk score $S_{\text{risk}} \in [0, 100]$.
- **Risk Categorisation Mapping:**
  - `LOW`: $S_{\text{risk}} < 50.0$
  - `MEDIUM`: $50.0 \le S_{\text{risk}} < 75.0$
  - `HIGH`: $S_{\text{risk}} \ge 75.0$

---

## 6. Physiological Factor Explainability

Rather than generating hardcoded text strings, the engine dynamically derives contributing physiological factors based on feature Z-scores and model weights:

- **Elevated Heart Rate:** Triggers when $\text{HR} > 100 \text{ bpm}$.
- **Bradycardia:** Triggers when $\text{HR} < 50 \text{ bpm}$.
- **Hypoxia / Reduced SpO2:** Triggers when $\text{SpO2} < 94\%$.
- **Hypotension / Low MAP:** Triggers when $\text{MAP} < 65 \text{ mmHg}$.
- **Tachypnea:** Triggers when $\text{Resp} > 22 \text{ breaths/min}$.
- **Waveform Variability & Instability:** Triggers on high standard deviation in ECG or ABP.

---

## 7. API Reference

The FastAPI backend exposes the following endpoints:

| Endpoint | Method | Description |
|---|---|---|
| `/api/multimodal/records` | `GET` | List available real demo records with subject IDs & modalities |
| `/api/multimodal/records/{record_id}` | `GET` | Detailed record summary and channel metadata |
| `/api/multimodal/analyze` | `POST` | Analyze a specific observation window; returns complete risk payload |
| `/api/multimodal/replay/{record_id}` | `GET` | Retrieve sequential window analysis timeline for replay |

### Sample Response Schema (`POST /api/multimodal/analyze`):
```json
{
  "record_id": "81739927",
  "subject_id": 10014354,
  "window_index": 3,
  "timestamp": "2148-08-16 09:45:00",
  "clinical_features": { "HR": 101.5, "SpO2": 92.5, "Resp": 21.6, "SysBP": 124.0, "DiaBP": 78.0, "MAP": 93.3, "Temp": 37.1 },
  "waveform_features": { "ECG_mean": 0.012, "ECG_std": 0.854, "PPG_mean": 48.2, "PPG_std": 1.15 },
  "clinical_score": 88.5,
  "waveform_score": 83.5,
  "fusion_score": 86.0,
  "risk_score": 86.0,
  "risk_category": "HIGH",
  "available_modalities": ["ECG", "PPG", "Resp", "Clinical Vitals"],
  "contributing_factors": [
    { "factor": "Hypoxia / Reduced SpO2", "impact": "HIGH", "description": "SpO2 saturation level at 92.5% (normal >= 95%)", "contribution_score": 6.3 },
    { "factor": "Elevated Heart Rate", "impact": "HIGH", "description": "HR of 101.5 bpm exceeds tachycardia threshold (100 bpm)", "contribution_score": 1.2 }
  ]
}
```

---

## 8. Dashboard Interface

The React/HTML5 dashboard (`frontend/index.html` & `frontend/dist/index.html`) includes:
- **Header Bar:** Brand title, dataset status badge, patient record dropdown selector, window step controls, and "Play Replay" timeline button.
- **Waveform Canvas Visualizers:** Real-time rendering of ECG Lead II (green), PPG/PLETH (cyan), and ABP (red) continuous signals.
- **Bedside Vitals Cards:** Real-time numerical display of HR, SpO2, Resp, BP, and MAP.
- **Fused Risk Score Gauge:** Circular score indicator with dynamic color ring (`LOW` green, `MEDIUM` amber, `HIGH` red).
- **Modality Sub-Score Bars:** Clinical vs. Waveform risk breakdown progress bars.
- **Derived Physiological Factors List:** Ranked list of contributing physiological factors.

---

## 9. Limitations & Research Boundary

1. **Not a Validated Mortality Predictor:** The score generated is a decision-support prototype risk score ($0-100$). It does not claim clinical validation for 24h mortality prediction.
2. **Credentialed MIMIC Access Pending:** Full MIMIC-IV Clinical mortality model validation is blocked pending PhysioNet credentialing.

---

## 10. Execution Commands

### Run Backend Server:
```powershell
$env:PYTHONPATH="."
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Run Frontend Dashboard:
Open `frontend/index.html` directly in your browser or navigate to `http://localhost:8000/` while the backend server is running.
