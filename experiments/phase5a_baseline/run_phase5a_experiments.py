"""
CareMind Phase 5A: Full Baseline Experiment Matrix Execution Script.

Runs combined and individual signal baselines for PhysioNet 2019 temporal sepsis prediction.
Saves model artifacts, feature configurations, evaluation results, and confusion matrices.
"""

import os
import json
import joblib
import pandas as pd
import numpy as np

from src.physionet2019.baseline import (
    BaselineTrainer,
    INDIVIDUAL_SIGNAL_SETS,
    EXCLUDED_COLUMNS,
    COMBINED_FEATURE_SET
)

def run_all_experiments():
    # 1. Paths & Directories
    processed_dir = "data/physionet2019/processed"
    results_dir = "experiments/phase5a_baseline/results"
    models_dir = "models/physionet2019"
    
    os.makedirs(results_dir, exist_ok=True)
    os.makedirs(models_dir, exist_ok=True)

    # 2. Load Data
    train_df = pd.read_parquet(os.path.join(processed_dir, "train.parquet"))
    val_df = pd.read_parquet(os.path.join(processed_dir, "val.parquet"))
    test_df = pd.read_parquet(os.path.join(processed_dir, "test.parquet"))

    print(f"Loaded Datasets:")
    print(f"  Train: {train_df.shape} ({train_df['patient_id'].nunique()} patients)")
    print(f"  Val:   {val_df.shape} ({val_df['patient_id'].nunique()} patients)")
    print(f"  Test:  {test_df.shape} ({test_df['patient_id'].nunique()} patients)")

    trainer = BaselineTrainer(random_state=42)

    # 3. Define Experiment Matrix
    # Combined models
    models_to_run = ["logistic_regression", "random_forest", "hist_gradient_boosting"]
    feature_sets_to_run = ["COMBINED", "HR_ONLY", "BP_ONLY", "SPO2_ONLY", "RESP_ONLY", "TEMP_ONLY"]

    all_results = []
    results_dict = {}

    print("\n=======================================================")
    print("RUNNING PHASE 5A BASELINE EXPERIMENT MATRIX")
    print("=======================================================\n")

    for m_type in models_to_run:
        for f_set in feature_sets_to_run:
            # Skip running individual signals for HistGradientBoosting to keep output clean & focused
            if m_type == "hist_gradient_boosting" and f_set != "COMBINED":
                continue

            exp_name = f"{m_type}__{f_set}"
            print(f"Running Experiment: {exp_name:35s} ...", end=" ")

            res = trainer.train_and_evaluate(
                train_df=train_df,
                val_df=val_df,
                test_df=test_df,
                model_type=m_type,
                feature_set_name=f_set
            )

            val_m = res["validation_metrics"]
            test_m = res["test_metrics"]

            exp_record = {
                "experiment_name": exp_name,
                "model_type": m_type,
                "feature_set": f_set,
                "feature_count": res["feature_count"],
                "features_used": res["features_used"],
                "validation": val_m,
                "test": test_m
            }

            all_results.append(exp_record)
            results_dict[exp_name] = exp_record

            # Save model object
            model_path = os.path.join(models_dir, f"{exp_name}.joblib")
            joblib.dump(res["model_object"], model_path)

            print(f"DONE | Val PR-AUC: {val_m['pr_auc']:.4f} | Test PR-AUC: {test_m['pr_auc']:.4f} | Test ROC-AUC: {test_m['roc_auc']:.4f}")

    # 4. Save Results JSON
    summary_json_path = os.path.join(results_dir, "metrics_summary.json")
    with open(summary_json_path, "w") as f:
        json.dump(results_dict, f, indent=2)

    # 5. Save Experiment Config & Metadata
    config_metadata = {
        "experiment_phase": "Phase 5A",
        "task_name": "PhysioNet 2019 Baseline Temporal Sepsis Model",
        "random_seed": 42,
        "target_column": "SepsisLabel",
        "excluded_columns": EXCLUDED_COLUMNS,
        "combined_feature_count": len(COMBINED_FEATURE_SET),
        "dataset_splits": {
            "train": {"patients": int(train_df['patient_id'].nunique()), "rows": len(train_df), "positive_rows": int((train_df['SepsisLabel']==1).sum())},
            "val": {"patients": int(val_df['patient_id'].nunique()), "rows": len(val_df), "positive_rows": int((val_df['SepsisLabel']==1).sum())},
            "test": {"patients": int(test_df['patient_id'].nunique()), "rows": len(test_df), "positive_rows": int((test_df['SepsisLabel']==1).sum())}
        }
    }

    config_path = os.path.join(results_dir, "config.json")
    with open(config_path, "w") as f:
        json.dump(config_metadata, f, indent=2)

    # 6. Generate Markdown Summary Table
    print("\n=======================================================")
    print("PHASE 5A RESULTS SUMMARY TABLE")
    print("=======================================================")
    
    summary_df = pd.DataFrame([
        {
            "Model": r["model_type"],
            "Feature Set": r["feature_set"],
            "Features": r["feature_count"],
            "Val Thresh": r["validation"]["threshold"],
            "Val PR-AUC": r["validation"]["pr_auc"],
            "Test PR-AUC": r["test"]["pr_auc"],
            "Test ROC-AUC": r["test"]["roc_auc"],
            "Test Precision": r["test"]["precision"],
            "Test Recall": r["test"]["recall"],
            "Test F1": r["test"]["f1_score"]
        }
        for r in all_results
    ])

    print(summary_df.to_string(index=False))

    summary_csv_path = os.path.join(results_dir, "metrics_summary.csv")
    summary_df.to_csv(summary_csv_path, index=False)
    print(f"\nSaved summary artifacts to {results_dir}")

if __name__ == "__main__":
    run_all_experiments()
