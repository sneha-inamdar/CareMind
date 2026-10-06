# CareMind — MIMIC-IV Clinical vs Waveform vs Multimodal Experiment Report

> **Document Status**: Methodological Audit & Pipeline Verification Report  
> **Experiment Script**: `experiments/mimic_multimodal/run_mimic_multimodal_experiment.py`  
> **Saved Metrics**: `experiments/mimic_multimodal/metrics_summary.json` & `.csv`  

---

## 1. Audit of Initial Demo Multimodal Experiment

> ⚠️ **METHODOLOGICAL AUDIT NOTICE**: A rigorous data audit discovered that previous model comparisons generated synthetic/mock waveform features for unmatched patients, incorrectly presenting 85 stays as a "common cohort". In reality, exact linkage between the 100-patient MIMIC Clinical Demo and MIMIC-IV Waveform Database (`mimic4wdb/0.1.0`) yields **only 4 matching patients (3 valid stays)**. The initial comparative model metrics are therefore **INVALID for research conclusions** and serve strictly as code pipeline validation.

### 1.1 Summary of Audit Findings

| Component | Status | Details & Audit Findings |
| :--- | :---: | :--- |
| **Clinical ETL & Item IDs** | **VALID** | Verified schemas and canonical Item IDs for 7 vitals and 4 core labs. |
| **85-Stay Clinical Cohort** | **VALID** | Correctly filters adult first ICU stays with LOS $\ge 24\text{h}$ surviving initial 24h. |
| **Zero-Leakage Firewall** | **VALID** | Strictly enforces $X_{\le 24\text{h}}$ feature windowing; rejects $X_{>24\text{h}}$ events. |
| **`Mortality24h` Target Logic** | **VALID** | Correctly defines mortality during $(t_{\text{intime}}+24\text{h}, t_{\text{intime}}+48\text{h}]$. |
| **Waveform Linker & Processor** | **VALID** | WFDB header parsing, channel extraction, clipping, and Z-score standardization. |
| **Common Cohort Size** | **CORRECTED** | Corrected from 85 stays to **3 valid stays** (4 overlapping subjects). |
| **Pseudo-Waveform Generation** | **INVALID** | Previous script generated mock waveform features for 82 unmatched stays. |
| **Substitute Target Evaluation** | **CORRECTED** | Previous script evaluated `InHospMortalityPost24h` without explicit validation disclaimer. |

### 1.2 Cause of Discrepancy
In the initial demo experiment runner, a placeholder loop generated random Gaussian signal statistics for all 85 clinical stays rather than dropping unmatched patients from the Common Cohort. This artificially populated waveform features for 82 patients who had no actual waveform records in `mimic4wdb/0.1.0`.

### 1.3 Corrected Cohort & Linkage Counts

```
Corrected Demo Cohort Linkage Breakdown
├── Total MIMIC Clinical Demo Patients: 100
├── Total Adult First ICU Stays >= 24h (Clinical Cohort): 85 stays
├── MIMIC Waveform Database Subjects Inspected (mimic4wdb/0.1.0): 198 subjects
├── Actual Common Overlapping Subjects in Demo: 4 subjects
└── ACTUAL Common Cohort (Meeting Clinical + Waveform Inclusion): 3 stays
```

### 1.4 Exact Linkage Table for Actual Common Cohort (3 Stays)

| subject_id | stay_id | hadm_id | intime | outtime | los (days) | Mortality24h | InHospMortalityPost24h |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **10019003** | 34107647 | 29279905 | 2153-03-28 02:21:00 | 2153-03-31 16:59:04 | 3.61 | 0 | 0 |
| **10020306** | 38540883 | 23052851 | 2135-01-21 17:01:57 | 2135-01-24 21:47:45 | 3.20 | 0 | 0 |
| **10039708** | 33281088 | 28258130 | 2140-01-23 18:08:00 | 2140-02-08 22:28:20 | 16.18 | 0 | 0 |

---

## 2. Primary Research Question

> *"Does combining discrete clinical physiological information with continuous waveform representations over the initial 24 hours of ICU admission provide superior early 24-hour mortality risk prediction compared to either modality alone under strict zero-leakage patient-level evaluation?"*

---

## 3. Dataset & Version Specifications

- **Clinical Database**: MIMIC-IV Clinical Database Demo v2.2 (100 patients)
- **Waveform Database**: MIMIC-IV Waveform Database v0.1.0 (`mimic4wdb/0.1.0` - 198 subject directories)
- **Linkage Source**: `subject_id` folder alignment + header `base_date`/`base_time` timestamp co-registration.

---

## 4. Target Outcome & Class Imbalance

- **Primary Research Target**: `Mortality24h` (In-hospital mortality during the 24h–48h window post-admission). *Note: In the 100-patient demo dataset, 0 deaths occurred in this exact 24h-48h window due to small sample size limits.*
- **Substitute Pipeline Target**: `InHospMortalityPost24h` (Overall in-hospital mortality post 24h observation window — 7 positives in 85 clinical stays).

---

## 5. Methodological Safeguards & Code Enforcements

To prevent future pseudo-data artifacts or target dilution:
1. **Strict Linkage Firewall**: Unmatched stays are strictly dropped from Waveform and Multimodal feature matrices (`has_waveform_link == True` enforced).
2. **Identity Verification**: Multimodal rows require identical `subject_id` and `stay_id` across clinical and waveform modalities.
3. **No Target Substitution**: Primary `Mortality24h` logic is preserved without silent mutation.
4. **Sample Size Halt**: Machine learning model training on the 3-stay demo common cohort is halted until full credentialed MIMIC-IV database access is approved.

---

## 6. Automated Test Suite Verification

```bash
python -m pytest tests/
```

### Pytest Results:
```text
============================= 29 passed in 7.97s ==============================
tests\test_mimic_demo.py ...                                             [ 10%]
tests\test_mimic_multimodal.py ...                                       [ 20%]
tests\test_mimic_plan.py .....                                           [ 37%]
tests\test_mimic_waveform.py .....                                       [ 55%]
tests\test_physionet2019_baseline.py ......                              [ 75%]
tests\test_physionet2019_etl.py .......                                  [100%]
```

---

## 7. Next Implementation Steps (Post-Credentialing)

Upon approval of full credentialed MIMIC-IV access:
1. Extract full ~30,000 stay clinical cohort and ~200 matched waveform stays.
2. Evaluate Clinical Only, Waveform Only, and Multimodal models on the true ~200-stay Common Cohort.
3. Perform SHAP feature attributions and modality ablation studies.
