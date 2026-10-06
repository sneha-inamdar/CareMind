import json
import pandas as pd
import numpy as np

with open('experiments/phase5a_baseline/results/metrics_summary.json') as f:
    results = json.load(f)

print("=== VERIFYING METRICS DIRECTLY FROM METRICS_SUMMARY.JSON ===")
for exp_name, res in results.items():
    print(f"\nExperiment: {exp_name}")
    print(f"  Model Type: {res['model_type']}")
    print(f"  Feature Set: {res['feature_set']}")
    print(f"  Feature Count: {res['feature_count']}")
    
    val_m = res['validation']
    print(f"  Validation Metrics:")
    print(f"    Threshold: {val_m['threshold']}")
    print(f"    PR-AUC:    {val_m['pr_auc']}")
    print(f"    ROC-AUC:   {val_m['roc_auc']}")
    print(f"    F1:        {val_m['f1_score']}")
    print(f"    Precision: {val_m['precision']}")
    print(f"    Recall:    {val_m['recall']}")
    print(f"    Samples:   Total={val_m['total_samples']}, Pos={val_m['positive_samples']}, Neg={val_m['negative_samples']}")
    
    test_m = res['test']
    print(f"  Test Metrics (Holdout):")
    print(f"    Threshold: {test_m['threshold']} (Frozen from Validation)")
    print(f"    PR-AUC:    {test_m['pr_auc']}")
    print(f"    ROC-AUC:   {test_m['roc_auc']}")
    print(f"    F1:        {test_m['f1_score']}")
    print(f"    Precision: {test_m['precision']}")
    print(f"    Recall:    {test_m['recall']}")
    print(f"    Specificity: {test_m['specificity']}")
    print(f"    Samples:   Total={test_m['total_samples']}, Pos={test_m['positive_samples']}, Neg={test_m['negative_samples']}")
    print(f"    Confusion Matrix: TN={test_m['confusion_matrix']['TN']}, FP={test_m['confusion_matrix']['FP']}, FN={test_m['confusion_matrix']['FN']}, TP={test_m['confusion_matrix']['TP']}")
