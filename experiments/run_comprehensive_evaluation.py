"""
Comprehensive Research Evaluation Runner for CareMind.

Executes:
  1. Single-signal / Unimodal vs Multimodal experiments (ECG, PPG, ABP, Clinical, Waveform, Multimodal).
  2. 1D CNN baseline vs. SVM handcrafted baseline on ECG signals.
  3. Patient-level split metric computation (Precision, Recall, F1, ROC-AUC, PR-AUC, Confusion Matrices).
  4. Generates structured JSON summary and Markdown research report.
"""

import os
import sys
import json
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.mimic.evaluator import CareMindEvaluator


def main():
    print("=== CAREMIND COMPREHENSIVE RESEARCH EVALUATION ENGINE ===")
    evaluator = CareMindEvaluator(random_state=42)

    # 1. Unimodal vs Multimodal Evaluation
    print("\n1. Running Unimodal vs. Multimodal Fusion Experiments (Patient-level Split)...")
    unimodal_res = evaluator.evaluate_unimodal_vs_multimodal(n_samples=300)
    
    # 2. 1D CNN vs SVM Baseline Evaluation
    print("\n2. Running ECG 1D CNN vs. Classical SVM Baseline Experiments...")
    cnn_res = evaluator.evaluate_ecg_cnn_vs_svm(n_samples=300, signal_len=1000)

    # Compile Summary
    summary = {
        "status": "success",
        "cohort_summary": unimodal_res["cohort_summary"],
        "unimodal_and_multimodal_metrics": unimodal_res["unimodal_metrics"],
        "ecg_cnn_vs_svm": cnn_res,
        "disclaimer": "Preliminary research evaluation on MIMIC-IV dataset — not clinical validation."
    }

    # Save to experiments/mimic_multimodal/metrics_summary.json
    out_dir = os.path.join(os.path.dirname(__file__), "mimic_multimodal")
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, "metrics_summary.json")
    with open(json_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSaved metrics summary to {json_path}")

    # Build Markdown Comparison Table
    rows = []
    
    # CNN vs SVM rows
    svm_m = cnn_res["svm_handcrafted_baseline"]
    cnn_m = cnn_res["cnn_1d_raw_signal_baseline"]
    rows.append({
        "Approach": "ECG (Handcrafted Features)",
        "Model": "SVM (RBF Kernel)",
        "Precision": svm_m["precision"],
        "Recall": svm_m["recall"],
        "F1-Score": svm_m["f1"],
        "ROC-AUC": svm_m["roc_auc"],
        "PR-AUC": svm_m["pr_auc"]
    })
    rows.append({
        "Approach": "ECG (Raw 1D Signals)",
        "Model": "1D CNN Baseline",
        "Precision": cnn_m["precision"],
        "Recall": cnn_m["recall"],
        "F1-Score": cnn_m["f1"],
        "ROC-AUC": cnn_m["roc_auc"],
        "PR-AUC": cnn_m["pr_auc"]
    })

    # Unimodal & Multimodal rows
    um_map = unimodal_res["unimodal_metrics"]
    rows.append({
        "Approach": "PPG-Only",
        "Model": "Logistic Regression",
        "Precision": um_map["PPG_Only_LR"]["precision"],
        "Recall": um_map["PPG_Only_LR"]["recall"],
        "F1-Score": um_map["PPG_Only_LR"]["f1"],
        "ROC-AUC": um_map["PPG_Only_LR"]["roc_auc"],
        "PR-AUC": um_map["PPG_Only_LR"]["pr_auc"]
    })
    rows.append({
        "Approach": "ABP-Only",
        "Model": "Logistic Regression",
        "Precision": um_map["ABP_Only_LR"]["precision"],
        "Recall": um_map["ABP_Only_LR"]["recall"],
        "F1-Score": um_map["ABP_Only_LR"]["f1"],
        "ROC-AUC": um_map["ABP_Only_LR"]["roc_auc"],
        "PR-AUC": um_map["ABP_Only_LR"]["pr_auc"]
    })
    rows.append({
        "Approach": "Clinical-Vitals-Only",
        "Model": "Logistic Regression",
        "Precision": um_map["Clinical_Vitals_LR"]["precision"],
        "Recall": um_map["Clinical_Vitals_LR"]["recall"],
        "F1-Score": um_map["Clinical_Vitals_LR"]["f1"],
        "ROC-AUC": um_map["Clinical_Vitals_LR"]["roc_auc"],
        "PR-AUC": um_map["Clinical_Vitals_LR"]["pr_auc"]
    })
    rows.append({
        "Approach": "Waveform-Only (ECG+PPG+ABP)",
        "Model": "Random Forest",
        "Precision": um_map["Waveform_Only_RF"]["precision"],
        "Recall": um_map["Waveform_Only_RF"]["recall"],
        "F1-Score": um_map["Waveform_Only_RF"]["f1"],
        "ROC-AUC": um_map["Waveform_Only_RF"]["roc_auc"],
        "PR-AUC": um_map["Waveform_Only_RF"]["pr_auc"]
    })
    rows.append({
        "Approach": "Multimodal Fusion (CareMind Risk)",
        "Model": "Adaptive Late Fusion (LR)",
        "Precision": um_map["Multimodal_Fusion_LR"]["precision"],
        "Recall": um_map["Multimodal_Fusion_LR"]["recall"],
        "F1-Score": um_map["Multimodal_Fusion_LR"]["f1"],
        "ROC-AUC": um_map["Multimodal_Fusion_LR"]["roc_auc"],
        "PR-AUC": um_map["Multimodal_Fusion_LR"]["pr_auc"]
    })

    df_table = pd.DataFrame(rows)
    csv_path = os.path.join(out_dir, "metrics_summary.csv")
    df_table.to_csv(csv_path, index=False)
    print(f"Saved CSV comparison table to {csv_path}\n")

    print("=== MODEL COMPARISON MATRIX ===")
    print(df_table.to_string(index=False))

if __name__ == "__main__":
    main()
