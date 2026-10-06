"""
MIMIC Data Schema and Data Profiling Engine (Audited).

Validates and profiles patient tables, chartevents, labevents, and waveform metadata
frames against CareMind MIMIC specifications.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List
from src.mimic.config import MIMICConfig


class MIMICSchemaValidator:
    """Validator and profiler for MIMIC-IV clinical and waveform metadata DataFrames."""

    def __init__(self, config: MIMICConfig = None):
        self.config = config or MIMICConfig()

    def validate_clinical_schema(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Validate and profile a MIMIC-IV clinical patient DataFrame.

        Args:
            df: DataFrame containing patient stay records.

        Returns:
            Dictionary containing profiling statistics, column presence, missingness, and label stats.
        """
        if df.empty:
            raise ValueError("Cannot profile an empty DataFrame.")

        # 1. Required identifier columns
        required_ids = ["subject_id", "stay_id"]
        missing_ids = [col for col in required_ids if col not in df.columns]
        if missing_ids:
            raise ValueError(f"Missing required identifier columns: {missing_ids}")

        # 2. Check presence of core vitals and target column
        present_vitals = [v for v in self.config.core_vitals if v in df.columns]
        missing_vitals = [v for v in self.config.core_vitals if v not in df.columns]
        
        target_col = (
            self.config.primary_target_column 
            if self.config.primary_target_column in df.columns 
            else self.config.secondary_target_column
        )
        has_target = target_col in df.columns

        # 3. Patient stay statistics
        total_rows = len(df)
        num_patients = df["subject_id"].nunique()
        num_stays = df["stay_id"].nunique()

        # 4. Target label statistics (if present)
        target_stats = {}
        if has_target:
            pos_rows = int((df[target_col] == 1).sum())
            pct_pos_rows = float((df[target_col] == 1).mean() * 100)
            target_stats = {
                "target_column": target_col,
                "positive_rows": pos_rows,
                "percentage_positive_rows": round(pct_pos_rows, 3)
            }

        # 5. Missingness summary
        missingness = {}
        for col in df.columns:
            m_count = int(df[col].isna().sum())
            m_pct = float((m_count / total_rows) * 100)
            missingness[col] = {
                "missing_count": m_count,
                "missing_percentage": round(m_pct, 2)
            }

        report = {
            "num_rows": total_rows,
            "unique_subjects": num_patients,
            "unique_stays": num_stays,
            "present_vitals": present_vitals,
            "missing_vitals": missing_vitals,
            "has_target_column": has_target,
            "target_stats": target_stats,
            "missingness": missingness,
            "is_valid_schema": (len(missing_ids) == 0 and has_target)
        }

        return report
