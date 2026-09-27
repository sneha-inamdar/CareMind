"""
PhysioNet 2019 Feature Transformer.

Transforms clean patient time-series into enriched patient-level representations:
  - Preserves original raw physiological variables and SepsisLabel
  - Derives missingness indicators (binary flags before imputation)
  - Computes 1-hour and 3-hour temporal deltas (e.g. delta_HR_1h, delta_MAP_3h)
  - Computes rolling temporal statistics (3-hour rolling mean and std)
"""

import pandas as pd
import numpy as np
from typing import List, Optional


DERIVED_TARGET_VITALS = ["HR", "O2Sat", "Temp", "SBP", "MAP", "DBP", "Resp"]


class PhysioNet2019Transformer:
    """Transformer for deriving temporal features while preserving raw vitals."""

    def __init__(
        self,
        target_vitals: List[str] = DERIVED_TARGET_VITALS,
        add_deltas: bool = True,
        add_rolling: bool = True,
        add_missingness_flags: bool = True
    ):
        self.target_vitals = target_vitals
        self.add_deltas = add_deltas
        self.add_rolling = add_rolling
        self.add_missingness_flags = add_missingness_flags

    def transform(self, raw_df: pd.DataFrame, clean_df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform clean DataFrame by adding derived temporal features.

        Args:
            raw_df: Un-imputed raw DataFrame used to construct missingness flags.
            clean_df: Cleaned & imputed DataFrame.

        Returns:
            Transformed pd.DataFrame with enriched temporal features.
        """
        transformed = clean_df.copy()
        vitals_present = [v for v in self.target_vitals if v in transformed.columns]

        # 1. Missingness indicators from raw_df
        if self.add_missingness_flags and raw_df is not None:
            for v in vitals_present:
                if v in raw_df.columns:
                    flag_col = f"is_missing_{v}"
                    # Match by index alignment
                    transformed[flag_col] = raw_df[v].isna().astype(int)

        # 2. Temporal deltas (1-hour and 3-hour changes)
        if self.add_deltas:
            for v in vitals_present:
                # 1-hour delta
                transformed[f"delta_{v}_1h"] = transformed.groupby("patient_id")[v].diff(1).fillna(0.0)
                # 3-hour delta
                transformed[f"delta_{v}_3h"] = transformed.groupby("patient_id")[v].diff(3).fillna(0.0)

        # 3. Rolling window statistics (3-hour rolling mean and std)
        if self.add_rolling:
            for v in vitals_present:
                rolling_3h = transformed.groupby("patient_id")[v].rolling(window=3, min_periods=1)
                transformed[f"rolling_mean_{v}_3h"] = rolling_3h.mean().reset_index(level=0, drop=True)
                transformed[f"rolling_std_{v}_3h"] = rolling_3h.std().reset_index(level=0, drop=True).fillna(0.0)

        return transformed
