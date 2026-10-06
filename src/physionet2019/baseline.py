"""
CareMind Phase 5A: Baseline Temporal Sepsis Model Module.

Provides reproducible baseline modeling, feature group definitions, threshold selection
on validation set, leak-free training, and evaluation metrics for PhysioNet 2019.
"""

import os
import json
import joblib
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional

from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    average_precision_score,
    roc_auc_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix
)

# --- FEATURE TAXONOMY DEFINITIONS ---
GROUP_A_VITALS = ["HR", "MAP", "SBP", "Resp", "O2Sat"]
GROUP_B_VITALS = ["Temp", "DBP"]
ALL_VITALS = GROUP_A_VITALS + GROUP_B_VITALS

MISSINGNESS_INDICATORS = [f"is_missing_{v}" for v in ALL_VITALS]
DELTAS_1H = [f"delta_{v}_1h" for v in ALL_VITALS]
DELTAS_3H = [f"delta_{v}_3h" for v in ALL_VITALS]
ROLLING_MEANS_3H = [f"rolling_mean_{v}_3h" for v in ALL_VITALS]
ROLLING_STDS_3H = [f"rolling_std_{v}_3h" for v in ALL_VITALS]

GROUP_C_TEMPORAL = (
    MISSINGNESS_INDICATORS + DELTAS_1H + DELTAS_3H + ROLLING_MEANS_3H + ROLLING_STDS_3H
)

COMBINED_FEATURE_SET = ALL_VITALS + GROUP_C_TEMPORAL

# Individual signal feature sets
INDIVIDUAL_SIGNAL_SETS: Dict[str, List[str]] = {
    "HR_ONLY": [
        "HR", "is_missing_HR", "delta_HR_1h", "delta_HR_3h",
        "rolling_mean_HR_3h", "rolling_std_HR_3h"
    ],
    "BP_ONLY": [
        "SBP", "MAP", "DBP", "is_missing_SBP", "is_missing_MAP", "is_missing_DBP",
        "delta_SBP_1h", "delta_SBP_3h", "delta_MAP_1h", "delta_MAP_3h", "delta_DBP_1h", "delta_DBP_3h",
        "rolling_mean_SBP_3h", "rolling_std_SBP_3h", "rolling_mean_MAP_3h", "rolling_std_MAP_3h",
        "rolling_mean_DBP_3h", "rolling_std_DBP_3h"
    ],
    "SPO2_ONLY": [
        "O2Sat", "is_missing_O2Sat", "delta_O2Sat_1h", "delta_O2Sat_3h",
        "rolling_mean_O2Sat_3h", "rolling_std_O2Sat_3h"
    ],
    "RESP_ONLY": [
        "Resp", "is_missing_Resp", "delta_Resp_1h", "delta_Resp_3h",
        "rolling_mean_Resp_3h", "rolling_std_Resp_3h"
    ],
    "TEMP_ONLY": [
        "Temp", "is_missing_Temp", "delta_Temp_1h", "delta_Temp_3h",
        "rolling_mean_Temp_3h", "rolling_std_Temp_3h"
    ],
    "COMBINED": COMBINED_FEATURE_SET
}

EXCLUDED_COLUMNS = [
    "patient_id", "time_step", "ICULOS", "Age", "Gender", "Unit1", "Unit2",
    "HospAdmTime", "SepsisLabel",
    "EtCO2", "BaseExcess", "HCO3", "FiO2", "pH", "PaCO2", "SaO2", "AST", "BUN",
    "Alkalinephos", "Calcium", "Chloride", "Creatinine", "Bilirubin_direct",
    "Glucose", "Lactate", "Magnesium", "Phosphate", "Potassium", "Bilirubin_total",
    "TroponinI", "Hct", "Hgb", "PTT", "WBC", "Fibrinogen", "Platelets"
]


def find_optimal_threshold(
    y_true: np.ndarray,
    y_probs: np.ndarray,
    metric: str = "f1",
    num_steps: int = 100
) -> Tuple[float, float]:
    """
    Find optimal classification threshold on validation probabilities.
    
    Args:
        y_true: True binary labels
        y_probs: Predicted positive class probabilities
        metric: Optimization metric ('f1' or 'pr_auc_point')
        num_steps: Grid resolution
        
    Returns:
        (best_threshold, best_score)
    """
    thresholds = np.linspace(0.01, 0.99, num_steps)
    best_thresh = 0.5
    best_score = -1.0

    for t in thresholds:
        preds = (y_probs >= t).astype(int)
        if metric == "f1":
            score = f1_score(y_true, preds, zero_division=0)
        else:
            score = precision_score(y_true, preds, zero_division=0)
        
        if score > best_score:
            best_score = score
            best_thresh = t

    return best_thresh, best_score


def evaluate_predictions(
    y_true: np.ndarray,
    y_probs: np.ndarray,
    threshold: float = 0.5
) -> Dict[str, Any]:
    """
    Compute comprehensive evaluation metrics.
    
    Args:
        y_true: Ground truth binary labels
        y_probs: Predicted positive class probabilities
        threshold: Decision threshold
        
    Returns:
        Dictionary of evaluation metrics
    """
    y_pred = (y_probs >= threshold).astype(int)
    
    # Primary metrics
    pr_auc = float(average_precision_score(y_true, y_probs))
    roc_auc = float(roc_auc_score(y_true, y_probs))
    
    # Secondary threshold-dependent metrics
    prec = float(precision_score(y_true, y_pred, zero_division=0))
    rec = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))
    
    cm = confusion_matrix(y_true, y_pred)
    if cm.shape == (2, 2):
        tn, fp, fn, tp = cm.ravel()
        spec = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0
    else:
        tn, fp, fn, tp = int(cm[0, 0]), 0, 0, 0
        spec = 1.0

    pos_count = int(np.sum(y_true == 1))
    total_count = int(len(y_true))
    prevalence = float(pos_count / total_count) if total_count > 0 else 0.0

    return {
        "pr_auc": round(pr_auc, 4),
        "roc_auc": round(roc_auc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "specificity": round(spec, 4),
        "f1_score": round(f1, 4),
        "threshold": round(float(threshold), 4),
        "total_samples": total_count,
        "positive_samples": pos_count,
        "negative_samples": total_count - pos_count,
        "positive_prevalence": round(prevalence, 4),
        "confusion_matrix": {
            "TN": int(tn),
            "FP": int(fp),
            "FN": int(fn),
            "TP": int(tp)
        }
    }


class BaselineTrainer:
    """
    Trainer for CareMind Phase 5A baseline models.
    """

    def __init__(self, random_state: int = 42):
        self.random_state = random_state

    def get_model(self, model_type: str) -> Any:
        """Instantiate specified baseline classifier."""
        if model_type == "logistic_regression":
            return Pipeline([
                ("scaler", StandardScaler()),
                ("classifier", LogisticRegression(
                    class_weight="balanced",
                    random_state=self.random_state,
                    max_iter=1000
                ))
            ])
        elif model_type == "random_forest":
            return RandomForestClassifier(
                n_estimators=100,
                max_depth=8,
                class_weight="balanced",
                random_state=self.random_state,
                n_jobs=-1
            )
        elif model_type == "hist_gradient_boosting":
            return HistGradientBoostingClassifier(
                max_iter=100,
                class_weight="balanced",
                random_state=self.random_state
            )
        else:
            raise ValueError(f"Unknown model_type: {model_type}")

    def train_and_evaluate(
        self,
        train_df: pd.DataFrame,
        val_df: pd.DataFrame,
        test_df: pd.DataFrame,
        model_type: str = "logistic_regression",
        feature_set_name: str = "COMBINED"
    ) -> Dict[str, Any]:
        """
        Train baseline model on Train, optimize threshold on Val, evaluate on Test.
        
        Args:
            train_df: Training DataFrame
            val_df: Validation DataFrame
            test_df: Test DataFrame
            model_type: 'logistic_regression' or 'random_forest' or 'hist_gradient_boosting'
            feature_set_name: Key in INDIVIDUAL_SIGNAL_SETS
            
        Returns:
            Dictionary containing model results and metadata
        """
        features = INDIVIDUAL_SIGNAL_SETS[feature_set_name]

        # Verify no illegal columns in feature matrix
        assert "SepsisLabel" not in features, "Target SepsisLabel must NOT be in features!"
        assert "patient_id" not in features, "patient_id must NOT be in features!"
        
        X_train, y_train = train_df[features], train_df["SepsisLabel"].values
        X_val, y_val = val_df[features], val_df["SepsisLabel"].values
        X_test, y_test = test_df[features], test_df["SepsisLabel"].values

        # 1. Fit model on Train split ONLY
        model = self.get_model(model_type)
        model.fit(X_train, y_train)

        # 2. Validation predictions & threshold tuning
        val_probs = model.predict_proba(X_val)[:, 1]
        best_thresh, _ = find_optimal_threshold(y_val, val_probs, metric="f1")
        val_metrics = evaluate_predictions(y_val, val_probs, threshold=best_thresh)

        # 3. Test predictions using FROZEN validation threshold
        test_probs = model.predict_proba(X_test)[:, 1]
        test_metrics = evaluate_predictions(y_test, test_probs, threshold=best_thresh)

        return {
            "model_type": model_type,
            "feature_set_name": feature_set_name,
            "feature_count": len(features),
            "features_used": features,
            "validation_metrics": val_metrics,
            "test_metrics": test_metrics,
            "model_object": model
        }
