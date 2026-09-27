"""
PhysioNet 2019 Dataset Validator and Profiler.

Validates and profiles raw and processed patient DataFrames:
  - Patient record counts & file integrity
  - Column schema verification
  - Patient length distribution (min, max, mean, median hours)
  - Variable-level missingness profiling
  - Physiological value range checking
  - Duplicate timestamp & sequence monotonicity verification
  - SepsisLabel distribution (row-level and patient-level prevalence)
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List

REQUIRED_VITALS = ["HR", "O2Sat", "Temp", "SBP", "MAP", "DBP", "Resp", "EtCO2"]
REQUIRED_METADATA = ["patient_id", "SepsisLabel"]


class PhysioNet2019Validator:
    """Validation and Data Profiling engine for PhysioNet 2019 dataset."""

    def __init__(self, expected_vitals: List[str] = REQUIRED_VITALS):
        self.expected_vitals = expected_vitals

    def profile_dataset(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Perform comprehensive statistical profiling and validation on a patient DataFrame.

        Args:
            df: DataFrame containing patient records concatenated together.

        Returns:
            Dictionary containing dataset statistics, missingness, ranges, and validation status.
        """
        if df.empty:
            raise ValueError("Cannot profile an empty DataFrame.")

        # 1. Basic schema validation
        columns = list(df.columns)
        missing_required = [col for col in REQUIRED_METADATA if col not in columns]
        if missing_required:
            raise ValueError(f"Missing required columns: {missing_required}")

        missing_vitals = [v for v in self.expected_vitals if v not in columns]

        # 2. Patient-level statistics
        total_rows = len(df)
        patient_ids = df["patient_id"].unique()
        num_patients = len(patient_ids)

        patient_lengths = df.groupby("patient_id").size()
        length_stats = {
            "min_stay_hours": int(patient_lengths.min()),
            "max_stay_hours": int(patient_lengths.max()),
            "mean_stay_hours": float(patient_lengths.mean()),
            "median_stay_hours": float(patient_lengths.median())
        }

        # 3. Temporal ordering & duplicate timestamps check
        temporal_violations = 0
        duplicate_timestamps = 0
        
        # Determine time column (ICULOS or time_step)
        time_col = "ICULOS" if "ICULOS" in df.columns else ("time_step" if "time_step" in df.columns else None)
        
        if time_col:
            for p_id, group in df.groupby("patient_id"):
                times = group[time_col].values
                # Check duplicates
                if len(times) != len(np.unique(times)):
                    duplicate_timestamps += 1
                # Check monotonic non-decreasing
                if not np.all(np.diff(times) >= 0):
                    temporal_violations += 1

        # 4. Label distribution (SepsisLabel)
        label_stats = {}
        if "SepsisLabel" in df.columns:
            total_pos_rows = int((df["SepsisLabel"] == 1).sum())
            pct_pos_rows = float((df["SepsisLabel"] == 1).mean() * 100)
            
            patient_sepsis = df.groupby("patient_id")["SepsisLabel"].max()
            pos_patients = int((patient_sepsis == 1).sum())
            pct_pos_patients = float((patient_sepsis == 1).mean() * 100)
            
            label_stats = {
                "total_positive_rows": total_pos_rows,
                "percentage_positive_rows": round(pct_pos_rows, 3),
                "total_positive_patients": pos_patients,
                "total_negative_patients": num_patients - pos_patients,
                "percentage_positive_patients": round(pct_pos_patients, 3)
            }

        # 5. Missingness profiling
        missingness = {}
        for col in columns:
            missing_count = int(df[col].isna().sum())
            missing_pct = float((missing_count / total_rows) * 100)
            missingness[col] = {
                "missing_count": missing_count,
                "missing_percentage": round(missing_pct, 2)
            }

        # 6. Physiological value range statistics
        value_ranges = {}
        vitals_to_check = [v for v in self.expected_vitals if v in df.columns]
        for v in vitals_to_check:
            s = df[v].dropna()
            if not s.empty:
                value_ranges[v] = {
                    "min": float(s.min()),
                    "max": float(s.max()),
                    "mean": float(round(s.mean(), 2)),
                    "std": float(round(s.std(), 2)),
                    "median": float(round(s.median(), 2)),
                    "p25": float(round(s.quantile(0.25), 2)),
                    "p75": float(round(s.quantile(0.75), 2))
                }
            else:
                value_ranges[v] = {"min": None, "max": None, "mean": None, "std": None, "median": None}

        report = {
            "num_patient_files": num_patients,
            "total_rows": total_rows,
            "patient_length_stats": length_stats,
            "missing_vitals": missing_vitals,
            "duplicate_timestamps_patients": duplicate_timestamps,
            "temporal_ordering_violations": temporal_violations,
            "label_stats": label_stats,
            "missingness": missingness,
            "physiological_value_ranges": value_ranges,
            "validation_passed": (len(missing_vitals) == 0 and temporal_violations == 0)
        }

        return report
