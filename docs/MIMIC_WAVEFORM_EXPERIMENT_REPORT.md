# CareMind — MIMIC-IV Waveform Database (v0.1.0) Integration & Linkage Report

> **Milestone Status**: Completed Waveform Data Preparation & Linkage Subsystem  
> **Official Source**: PhysioNet MIMIC-IV Waveform Database (`mimic4wdb/0.1.0`)  
> **Access Type**: Open Access (WFDB Header & Signal Records)  

---

## 1. Executive Summary

This report documents the design, verification, and implementation of the **MIMIC-IV Waveform Subsystem** for CareMind. 

The objective of this milestone is to establish a verified, leak-free linkage pipeline connecting continuous physiological waveforms (ECG, ABP, PPG) from the open-access **MIMIC-IV Waveform Database (`mimic4wdb/0.1.0`)** to discrete ICU patient stays from the **MIMIC-IV Clinical Database**.

---

## 2. Dataset & Version Specifications

- **Dataset Identifier**: MIMIC-IV Waveform Database v0.1.0 (`mimic4wdb/0.1.0`)
- **Host Platform**: PhysioNet (Open Access)
- **Record Directory Structure**: Organized into subject subfolders (`waves/p100/p10014354/`, `waves/p101/p10112163/`, etc.).
- **Segment Structure**: Multi-segment WFDB records composed of a master header (`81739927.hea`), layout header, and individual binary segment files (`81739927_0001e.dat`).

---

## 3. Empirical Waveform Inspection & Channel Availability Report

We performed a direct, empirical inspection of header files across 40 subject directories (42 waveform records) from `mimic4wdb/0.1.0`:

```
MIMIC-IV Waveform Channel Inventory (42 Records Inspected)
├── Total Waveform Records: 42
├── Unique Subjects Inspected: 40
├── Lead II / Multi-Lead ECG: 42 / 42 (100.0% Availability)
├── Photoplethysmogram (PPG/PLETH): 42 / 42 (100.0% Availability)
└── Invasive Arterial BP (ABP): 13 / 42 (31.0% Availability)
```

### Modality Tiering & Record Breakdown (Inspected Sample)
- **Total Waveform Records Inspected**: 42 records across 40 unique subject directories.
- **Tier 1 (ECG + ABP + PPG)**: **13 / 42 records (31.0%)** — Subset of records with invasive arterial lines.
- **Tier 2 (ECG + PPG)**: **42 / 42 records (100.0%)** — All 42 records contain both ECG and PPG (including the 13 Tier 1 records).
- **Tier 3 (ECG Only)**: **42 / 42 records (100.0%)** — Universal single-modality baseline.
- **Linkage to Clinical Demo**: Out of 40 inspected waveform subjects, **4 subjects (4 ICU stays)** directly matched the 100-patient MIMIC Clinical Demo cohort.

> [!NOTE]
> **Cohort Scope Distinction**: The 100% ECG/PPG availability and 31.0% ABP availability describe the *inspected sample of 42 records*. Tier 1 (13) is a proper subset of Tier 2 (42), NOT an additive total ($13 + 42 \ne 55$). Full MIMIC-IV Waveform Database (`mimic4wdb/0.1.0`) contains 198 subject directories across PhysioNet.

---

## 4. Sampling Frequencies & Recording Durations

- **Sampling Frequencies ($F_s$)**: Master header index rate is **62.4725 Hz**, with continuous raw waveform segments sampled at **125 Hz** and **250 Hz**.
- **Recording Durations**: Ranges from **1.58 hours to 137.14 hours** per ICU stay (median duration: ~28.5 hours).

---

## 5. Clinical & Waveform Linkage Mechanism

```
Patient-Level Waveform Linkage Logic
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. Extract `subject_id` from folder name: `waves/p100/p10014354/` -> 10014354│
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. Parse record start timestamp from WFDB header line 1:                     │
│    "09:00:17.566 16/8/2148" -> `2148-08-16 09:00:17.566`                    │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. Match `subject_id` against MIMIC-IV Clinical `icustays` cohort            │
├─────────────────────────────────────────────────────────────────────────────┤
│ 4. Compute temporal overlap with initial 24h observation window:             │
│    Overlap = (w_start < t_intime + 24h) and (w_end > t_intime)              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Preprocessing & Zero-Leakage Temporal Firewall

The reusable waveform processor (`src/mimic/waveform_processor.py`) enforces strict temporal rules:
- **Observation Window**: $[t_{\text{intime}}, t_{\text{intime}} + 24\text{ hours}]$.
- **Zero-Leakage Firewall**: Any waveform samples recorded after $t_{\text{intime}} + 24\text{ hours}$ are strictly rejected.
- **Signal Cleaning**:
  - ECG: Clip noise spikes to $[-5.0\text{ mV}, 5.0\text{ mV}]$.
  - ABP: Clip physical blood pressure bounds $[0, 300\text{ mmHg}]$.
  - PPG: Clip percentage / ADC bounds $[0, 100\%]$.
- **Normalization & Resampling**: Linear interpolation for missing values, Z-score standardization ($\mu=0, \sigma=1$), and linear resampling to uniform $125.0\text{ Hz}$.

---

## 7. Baseline Waveform Feature Representation

The initial waveform feature extractor (`src/mimic/waveform_features.py`) converts continuous 24-hour windows into defensible tabular features:

| Modality | Features Extracted |
| :--- | :--- |
| **ECG** | `ECG_mean`, `ECG_std`, `ECG_rms`, `ECG_ptp` (peak-to-peak), `ECG_zero_crossings`, `ECG_is_missing` |
| **ABP** | `ABP_mean`, `ABP_std`, `ABP_sys_max`, `ABP_dia_min`, `ABP_pulse_pressure` (sys - dia), `ABP_is_missing` |
| **PPG** | `PPG_mean`, `PPG_std`, `PPG_peak_max`, `PPG_trough_min`, `PPG_amplitude_range`, `PPG_is_missing` |

---

## 8. Derived Linkage Metadata Table Schema

```text
Linkage Metadata Output Table
├── subject_id (int64)
├── stay_id (int64)
├── intime (datetime64[ns])
├── obs_end (datetime64[ns])
├── waveform_record (str)
├── waveform_start (datetime64[ns])
├── waveform_end (datetime64[ns])
├── fs (float64)
├── duration_hrs (float64)
├── has_ecg (bool)
├── has_abp (bool)
├── has_ppg (bool)
├── overlap_with_24h_window (bool)
└── tier (str)
```

---

## 9. Test Suite Verification

The complete CareMind test suite was executed, verifying all components:

```bash
python -m pytest tests/
```

### Pytest Results:
```text
============================= 26 passed in 4.57s ==============================
tests\test_mimic_demo.py ...                                             [ 11%]
tests\test_mimic_plan.py .....                                           [ 30%]
tests\test_mimic_waveform.py .....                                       [ 50%]
tests\test_physionet2019_baseline.py ......                              [ 73%]
tests\test_physionet2019_etl.py .......                                  [100%]
```

---

## 10. Code Subsystem Architecture

The new waveform pipeline files are located under `src/mimic/`:
- 🐍 [`src/mimic/waveform_linker.py`](file:///c:/Users/Sneha/Desktop/College%20sem%205/project/CareMind/src/mimic/waveform_linker.py): `MIMICWaveformLinker`
- 🐍 [`src/mimic/waveform_processor.py`](file:///c:/Users/Sneha/Desktop/College%20sem%205/project/CareMind/src/mimic/waveform_processor.py): `MIMICWaveformProcessor`
- 🐍 [`src/mimic/waveform_features.py`](file:///c:/Users/Sneha/Desktop/College%20sem%205/project/CareMind/src/mimic/waveform_features.py): `MIMICWaveformFeatureExtractor`
- 🧪 [`tests/test_mimic_waveform.py`](file:///c:/Users/Sneha/Desktop/College%20sem%205/project/CareMind/tests/test_mimic_waveform.py): Unit test suite
