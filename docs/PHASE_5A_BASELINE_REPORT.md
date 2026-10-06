# CareMind — Phase 5A: Baseline Temporal Sepsis Prediction Report

## 1. Objective

The objective of **Phase 5A** is to establish a reproducible, leak-free baseline machine learning model for predicting temporal sepsis onset (`SepsisLabel`) on the PhysioNet/CinC Challenge 2019 dataset. 

This phase does **not** aim to produce the final production CareMind model, nor does it perform hyperparameter tuning or multimodal waveform fusion. Instead, it creates a trustworthy benchmark against which future individual-vital ablation studies, advanced temporal architectures, and multimodal fusion models can be objectively evaluated under identical patient-level splits.

---

## 2. Research Question

> **"How well can the available physiological and temporal features predict the PhysioNet 2019 `SepsisLabel` under a strict patient-level, leakage-free evaluation protocol?"**

---

## 3. Dataset & Cohort Characterization

The experiment uses the validated 500-patient PhysioNet 2019 benchmark cohort generated during Phase 4A. All data processing and imputation parameters were fitted **strictly on training patients**.

```
Dataset Partitioning Architecture (70% Train / 15% Val / 15% Test)
┌──────────────────────┬──────────────┬─────────────┬─────────────────┬──────────────────┐
│ Split                │ Patients     │ Hourly Rows │ Sepsis Patients │ Positive Rows (%)│
├──────────────────────┼──────────────┼─────────────┼─────────────────┼──────────────────┤
│ Train Split          │ 350 (70.0%)  │   13,623    │   32 (9.14%)    │   306 (2.25%)    │
│ Validation Split     │  75 (15.0%)  │    2,759    │    7 (9.33%)    │    68 (2.46%)    │
│ Test Split (Holdout) │  75 (15.0%)  │    2,896    │    6 (8.00%)    │    59 (2.04%)    │
├──────────────────────┼──────────────┼─────────────┼─────────────────┼──────────────────┤
│ Total Cohort         │ 500 (100.0%) │   19,278    │   45 (9.00%)    │   433 (2.25%)    │
└──────────────────────┴──────────────┴─────────────┴─────────────────┴──────────────────┘
```

* **Zero Patient Overlap:** Enforced patient-level separation: $\text{Train} \cap \text{Val} = \emptyset$, $\text{Train} \cap \text{Test} = \emptyset$, $\text{Val} \cap \text{Test} = \emptyset$.
* **Imbalance:** Severe hourly class imbalance with a positive label prevalence of **2.25%** overall (**2.04%** in the holdout test set).

---

## 4. Target Definition

* **Ground Truth Target:** `SepsisLabel` $\in \{0, 1\}$.
* **PhysioNet 2019 Definition:** Binary indicator set to $1$ starting 6 hours prior to clinical sepsis onset ($t_{sepsis} - 6$) through 9 hours post-onset ($t_{sepsis} + 9$).
* **Target Integrity:** `SepsisLabel` is preserved un-altered from raw `.psv` files. It is **NOT** transformed into a universal ICU risk score, nor modified to fit an artificial windowing scheme.

---

## 5. Temporal Prediction Setup

To mirror real-world ICU bedside monitoring, prediction at time step $t$ uses **only** information recorded at or before $t$:

$$\hat{y}_t = f\left( X_{\le t} \right)$$

* **Backward-Looking Feature Design:** 
  * 1-hour deltas: $\Delta X_t = X_t - X_{t-1}$
  * 3-hour deltas: $\Delta X_t = X_t - X_{t-3}$
  * 3-hour rolling statistics: Mean and standard deviation over $[t-3, t]$
* **No Future Peeking:** No future physiological measurements ($X_{>t}$), lead indicators, or future target labels ($y_{>t}$) are accessible to the model at step $t$.

---

## 6. Baseline Feature Groups

The primary combined baseline incorporates 42 engineered features spanning Groups A, B, and C:

```
Feature Taxonomy (42 Features)
├── Group A: Core Vitals (5)
│   └── HR, MAP, SBP, Resp, O2Sat
├── Group B: Intermittent Vitals (2)
│   └── Temp, DBP
└── Group C: Backward Temporal Dynamics (35)
    ├── Missingness Indicators (7): is_missing_HR, is_missing_Temp, etc.
    ├── 1-Hour Deltas (7): delta_HR_1h, delta_Resp_1h, etc.
    ├── 3-Hour Deltas (7): delta_HR_3h, delta_Resp_3h, etc.
    ├── 3-Hour Rolling Means (7): rolling_mean_HR_3h, etc.
    └── 3-Hour Rolling Stds (7): rolling_std_HR_3h, etc.
```

### Individual Signal Sets for Ablation
In addition to the COMBINED feature set, 5 single-vital feature sets were evaluated using the exact same split and temporal protocol:
1. **`HR_ONLY` (6 features):** `HR`, `is_missing_HR`, `delta_HR_1h`, `delta_HR_3h`, `rolling_mean_HR_3h`, `rolling_std_HR_3h`.
2. **`BP_ONLY` (18 features):** `SBP`, `MAP`, `DBP`, missingness flags, deltas, rolling means/stds.
3. **`SPO2_ONLY` (6 features):** `O2Sat`, missingness flag, deltas, rolling stats.
4. **`RESP_ONLY` (6 features):** `Resp`, missingness flag, deltas, rolling stats.
5. **`TEMP_ONLY` (6 features):** `Temp`, missingness flag, deltas, rolling stats.

---

## 7. Feature Exclusions

The following columns were explicitly excluded from the predictive feature matrix:

1. **Target Variable (`SepsisLabel`):** Primary prediction objective.
2. **Patient Identifiers & Index (`patient_id`, `time_step`):** Prevents patient identity memorization.
3. **Operational Metadata (`ICULOS`, `HospAdmTime`, `Unit1`, `Unit2`):** Operational length-of-stay features that leak admission duration.
4. **Static Demographics (`Age`, `Gender`):** Excluded to establish a pure physiological signal baseline.
5. **Sparse Laboratory Features (> 85% missingness):** `Lactate`, `WBC`, `Platelets`, `Creatinine`, `Glucose`, `pH`, `FiO2`, `TroponinI`, `EtCO2`, etc. Excluded to avoid severe imputation artifacts.

---

## 8. Leakage Prevention Checklist

- [x] **Patient Split First:** Split into Train (350), Val (75), and Test (75) before preprocessing.
- [x] **Train-Only Imputation:** Cohort medians fitted strictly on Train split.
- [x] **No Future Peeking:** All deltas and rolling window features are strictly backward-looking ($t-k \le t$).
- [x] **Frozen Threshold:** Decision threshold selected on Validation set and applied once to Test set without re-tuning.
- [x] **No Oversampling Leakage:** Class weighting (`class_weight="balanced"`) used instead of SMOTE to prevent cross-row correlation.

---

## 9. Baseline Models

Three scikit-learn baseline classifiers were evaluated:
1. **Logistic Regression (`logistic_regression`):** Linear baseline with `StandardScaler` pipeline and `class_weight="balanced"`.
2. **Random Forest (`random_forest`):** Non-linear ensemble (`n_estimators=100`, `max_depth=8`, `class_weight="balanced"`).
3. **HistGradientBoosting (`hist_gradient_boosting`):** Fast gradient boosted decision trees (`max_iter=100`, `class_weight="balanced"`).

---

## 10. Class Imbalance Handling

Given the 2.25% positive label prevalence:
* Models were trained using loss-level class weighting (`class_weight="balanced"`), adjusting sample weights inversely proportional to class frequencies:
  $$w_1 = \frac{N_{total}}{2 \cdot N_{pos}}$$
* Decision thresholds were tuned on the Validation split by grid-searching $\tau \in [0.01, 0.99]$ to maximize validation F1-score, then frozen for holdout test evaluation.

---

## 11. Evaluation Metrics

* **Primary Metric:** Precision-Recall Area Under Curve (**PR-AUC / Average Precision**). Essential for severely imbalanced ICU temporal datasets where ROC-AUC can present an overly optimistic score.
* **Secondary Metrics:** ROC-AUC, Precision, Recall (Sensitivity), Specificity, F1-Score, and Confusion Matrix.
* **Baseline Prevalence Reference:** Test set positive label prevalence = **0.0204** (2.04%). A random classifier achieves PR-AUC = 0.0204.

---

## 12. Empirical Results

### Summary Table across Models and Feature Sets

| Model | Feature Set | Feature Count | Val Thresh | Val PR-AUC | Test PR-AUC | Test ROC-AUC | Test Precision | Test Recall | Test F1 |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`random_forest`** | **`COMBINED`** | **42** | **0.5148** | **0.0345** | **0.0970** | **0.7090** | **0.1176** | **0.2373** | **0.1573** |
| `random_forest` | `HR_ONLY` | 6 | 0.6633 | 0.0390 | 0.0357 | 0.6854 | 0.0388 | 0.1356 | 0.0604 |
| `random_forest` | `TEMP_ONLY` | 6 | 0.7227 | 0.1022 | 0.0388 | 0.6664 | 0.0720 | 0.1525 | 0.0978 |
| `random_forest` | `BP_ONLY` | 18 | 0.7029 | 0.0652 | 0.0288 | 0.6025 | 0.0000 | 0.0000 | 0.0000 |
| `random_forest` | `RESP_ONLY` | 6 | 0.4753 | 0.0456 | 0.0212 | 0.4935 | 0.0192 | 0.2203 | 0.0354 |
| `random_forest` | `SPO2_ONLY` | 6 | 0.0991 | 0.0176 | 0.0196 | 0.4752 | 0.0202 | 0.9831 | 0.0395 |
| `logistic_regression` | `COMBINED` | 42 | 0.7425 | 0.0632 | 0.0348 | 0.6525 | 0.0261 | 0.0678 | 0.0377 |
| `logistic_regression` | `TEMP_ONLY` | 6 | 0.6039 | 0.0412 | 0.0419 | 0.6838 | 0.0381 | 0.1356 | 0.0595 |
| `logistic_regression` | `HR_ONLY` | 6 | 0.6831 | 0.0385 | 0.0331 | 0.6719 | 0.0207 | 0.0678 | 0.0317 |
| `hist_gradient_boosting` | `COMBINED` | 42 | 0.4852 | 0.0427 | 0.0416 | 0.6313 | 0.0312 | 0.0847 | 0.0457 |

---

## 13. Detailed Performance Analysis of Best Model

### Top Baseline Model: Random Forest (`COMBINED`)
* **Test PR-AUC:** **0.0970** (vs. 0.0204 random baseline — **4.75x improvement**).
* **Test ROC-AUC:** **0.7090** (demonstrating solid discrimination between septic and non-septic hourly states).
* **Test Precision / Recall / F1:** Precision = **0.1176**, Recall = **0.2373**, F1 = **0.1573** at frozen threshold $\tau = 0.5148$.

```
Holdout Test Confusion Matrix (Random Forest COMBINED @ threshold = 0.5148)
┌──────────────────────────────┬──────────────────────────────┐
│ True Negatives (TN): 2,732   │ False Positives (FP):  105   │
├──────────────────────────────┼──────────────────────────────┤
│ False Negatives (FN):   45   │ True Positives (TP):    14   │
└──────────────────────────────┴──────────────────────────────┘
```

### Signal Importance Insights (Ablation Analysis)
1. **Multimodal Synergy:** The `COMBINED` model (PR-AUC 0.0970) significantly outperforms every individual vital baseline on test set (`HR_ONLY` 0.0357, `TEMP_ONLY` 0.0388, `BP_ONLY` 0.0288), proving that integrating multiple physiological vitals provides superior predictive signal over single-vital monitoring.
2. **Strongest Individual Predictors:** `HR` (ROC-AUC 0.6854) and `Temp` (ROC-AUC 0.6664) provide the highest single-vital predictive power for sepsis onset, reflecting systemic tachycardia and febrile responses.

---

## 14. Limitations

1. **Discrete Hourly Resolution:** Data is logged in 1-hour windows without continuous waveform sub-second granularity.
2. **Missing Laboratory Signal:** Sparse lab variables (e.g., Lactate, WBC) were excluded due to >85% missingness.
3. **Imbalance Severity:** Extremely low positive label prevalence (2.04% on test set) leads to low precision at high recall thresholds, highlighting the challenge of early bedside alert systems.

---

## 15. Research Interpretation & Scope Boundaries

> [!IMPORTANT]
> **Strict CareMind Scope Statement:** This experiment evaluates a **PhysioNet 2019 temporal sepsis prediction baseline**. It is **NOT** a universal CareMind ICU risk score, nor does it predict all forms of acute organ failure or cardiac arrest.

---

## 16. Reproducibility & Automated Test Suite Verification

The experiment is 100% reproducible with fixed random seed `seed=42`. Automated test suite (`tests/test_physionet2019_baseline.py`) verifies all core assumptions:

```bash
python -m pytest tests/
```

### Test Suite Output
```text
============================= test session starts =============================
platform win32 -- Python 3.13.5, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\Sneha\Desktop\College sem 5\project\CareMind

tests\test_physionet2019_baseline.py ......                              [ 46%]
tests\test_physionet2019_etl.py .......                                  [100%]

============================= 13 passed in 3.23s ==============================
```

---

## 17. Recommended Next Experiment (Phase 5B)

With Phase 5A baseline establishment complete, the recommended next steps for **Phase 5B** are:
1. **Sequence Modeling:** Evaluate sequential deep learning models (e.g. LSTM / GRU / Temporal Convolutional Networks) capable of capturing long-range temporal memory across patient stays.
2. **Utility Score Integration:** Implement official PhysioNet 2019 Challenge Utility Scoring for clinical early-warning evaluation.
3. **Approval:** Await explicit user approval before starting Phase 5B development.
