# CareMind — PBL Project Presentation Outline

**Project Title:** CareMind: AI-Powered Multimodal ICU Decision Support System  
**Presentation Length:** 10–12 Slides (Approx. 10 Minutes)

---

## Slide 1: Title & Introduction
- **Header:** CareMind — AI-Powered Multimodal ICU Decision Support System
- **Subtitle:** Transforming Continuous High-Frequency Waveforms & Bedside Vitals into Dynamic Instability Metrics
- **Presenter Names & Course:** PBL Project Presentation (Semester 5)
- **Core Focus:** Genuine AI/ML research project evaluated on open-access MIMIC-IV & PhysioNet physiological datasets.

## Slide 2: The Problem
- **Headline:** Information Overload & Delayed Intervention in Intensive Care
- **Key Points:**
  - ICU clinicians face hundreds of uncoordinated alarms daily (*alarm fatigue*).
  - Bedside monitors process individual signals in isolation without unified risk synthesis.
  - Physiological deterioration is often preceded by subtle cross-modality signals (e.g., simultaneous ECG variability and SpO2 drop).

## Slide 3: Proposed Solution
- **Headline:** CareMind Multimodal Decision Support System
- **Key Points:**
  - Continuously ingests 1D waveform streams (ECG, PPG, ABP) and bedside chart vitals.
  - Computes the **CareMind Physiological Risk Score** (0–100 continuous instability index).
  - Ranks multi-patient ICU beds automatically by risk priority.
  - Delivers grounded, structured explainability factors for rapid clinical verification.

## Slide 4: Real Datasets & Provenance
- **Headline:** Empirically Grounded on Open-Access Physiological Datasets
- **Key Points:**
  - **MIT-BIH Arrhythmia Database**: Baseline ECG signal processing and heartbeat classification.
  - **PhysioNet 2019 Sepsis Challenge**: Hourly ICU tabular observations benchmarked with patient-level splitting.
  - **MIMIC-IV / MIMIC-IV Waveform (`mimic4wdb/0.1.0`)**: 24 genuine ICU waveform records categorized into Tier 1 (ECG+ABP+PPG), Tier 2 (ECG+PPG), and Tier 3 (ECG only).

## Slide 5: Single-Signal Analysis
- **Headline:** Individual Modality Processing & Feature Extraction
- **Key Points:**
  - **ECG Processing**: Noise filtering, QRS peak detection, 11 handcrafted temporal/statistical features.
  - **PPG Processing**: Attenuation detection, amplitude range, pulse wave variability.
  - **ABP Processing**: Systolic/Diastolic bounds, pulse pressure, mean arterial pressure (MAP) dynamics.
  - **Clinical Vitals**: Standardized bedside vitals vector (HR, SpO2, Resp, BP, Temp).

## Slide 6: Machine Learning & Deep Learning Models
- **Headline:** Classical Machine Learning vs. 1D CNN Deep Learning
- **Key Points:**
  - **Classical Baselines**: Support Vector Machines (SVM), Logistic Regression, Random Forests.
  - **1D CNN Baseline**: PyTorch 1D Convolutional Neural Network trained on raw ECG signal segments (Conv1d -> BatchNorm -> ReLU -> MaxPool -> Linear).
  - **Research Question**: Evaluates whether learned 1D CNN representations improve over handcrafted classical baselines.

## Slide 7: Multimodal Adaptive Fusion & Missing Modality Firewall
- **Headline:** Adaptive Late Fusion & Missing-Modality Resilience
- **Key Points:**
  - Modality-specific encoders transform raw features into calibrated logit representations.
  - **Temperature-Scaled Calibration ($T=1.75$)**: Expands score dynamic range and prevents score saturation.
  - **Missing Modality Firewall**: System dynamically adjusts fusion weights when specific sensors are unmonitored or noisy.

## Slide 8: Physiological Risk Score & Explainability
- **Headline:** Transparent Instability Scoring & Clinical Rationale
- **Key Points:**
  - **CareMind Risk Score (0–100)**: Defined strictly as an engineering instability index (Routine <50, High 50–74, Critical ≥75).
  - **Structured Factors**: Factors link directly to evidence (e.g., *"SpO2 of 93.0% below threshold"*, *"ECG variability elevated"*).
  - **Temporal Trend**: Tracks risk escalation (+Δ points) across sequential observation windows.

## Slide 9: System Architecture
- **Headline:** Production-Ready End-to-End Software Architecture
- **Key Points:**
  - **ML Core**: Python, PyTorch, Scikit-learn, WFDB.
  - **Backend**: FastAPI REST API with CORS support.
  - **Persistence**: Dual-repository layer (Supabase PostgreSQL / Local JSON Cache).
  - **Frontends**: React Web Command Center + Flutter Android Mobile App.

## Slide 10: Empirical Results & Model Comparison Matrix
- **Headline:** Quantitative Results Across Patient-Level Splits
- **Comparison Table:**

| Approach | Model | Precision | Recall | F1-Score | ROC-AUC | PR-AUC |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| ECG (Handcrafted) | SVM (RBF) | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| ECG (Raw 1D) | 1D CNN Baseline | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| PPG-Only | Logistic Regression | 0.4737 | 0.2308 | 0.3103 | 0.5465 | 0.4680 |
| ABP-Only | Logistic Regression | 0.5789 | 0.5641 | 0.5714 | 0.6933 | 0.7177 |
| Clinical Vitals | Logistic Regression | 0.7000 | 0.5385 | 0.6087 | 0.7712 | 0.7506 |
| Waveform-Only | Random Forest | 0.7812 | 0.6410 | 0.7042 | 0.7989 | 0.8379 |
| **Multimodal Fusion** | **Adaptive Late Fusion** | **0.8125** | **0.6667** | **0.7324** | **0.8276** | **0.8516** |

## Slide 11: Live Prototype Demonstration
- **Headline:** Live System Demonstration
- **Highlights:**
  - Multi-patient ICU command center overview.
  - Live 15-minute window simulation replay & alert generation.
  - Real-time continuous waveform inspection (ECG, PPG, ABP).
  - Concurrent mobile app integration via Flutter.

## Slide 12: Conclusion & Research Roadmap
- **Headline:** Conclusion & Future Directions
- **Summary:**
  - CareMind demonstrates that multimodal fusion outperforms single-modality baselines under zero-leakage patient-level evaluation.
  - Production architecture connects ML core to web and mobile operational interfaces.
- **Future Work:**
  - Expanded evaluation on credentialed full MIMIC-IV dataset (tens of thousands of stays).
  - Transformer/Mamba attention mechanisms for long-context waveform fusion.
