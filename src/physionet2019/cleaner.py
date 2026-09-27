"""
PhysioNet 2019 ETL Cleaner.

Implements data cleaning operations:
  - Outlier rejection using standard physiological bounds
  - Temporal sorting & deduplication per patient
  - Configurable imputation (Forward Fill / LOCF + Population Median Fallback)
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional

# Standard clinical physiological plausibility bounds
# Values strictly outside these ranges are sensor artifacts / recording errors and are replaced with NaN
PHYSIOLOGICAL_BOUNDS = {
    "HR": (20.0, 250.0),      # Heart Rate (bpm)
    "O2Sat": (0.0, 100.0),    # SpO2 (%)
    "Temp": (25.0, 45.0),     # Temperature (°C)
    "SBP": (30.0, 300.0),     # Systolic BP (mmHg)
    "DBP": (10.0, 200.0),     # Diastolic BP (mmHg)
    "MAP": (20.0, 250.0),     # Mean Arterial Pressure (mmHg)
    "Resp": (4.0, 100.0),     # Respiratory Rate (breaths/min)
    "EtCO2": (0.0, 150.0)     # End-Tidal CO2 (mmHg)
}


class PhysioNet2019Cleaner:
    """Cleaner module for PhysioNet 2019 patient physiological time-series."""

    def __init__(
        self,
        bounds: Optional[Dict[str, tuple]] = None,
        impute_vitals: bool = True,
        max_locf_hours: Optional[int] = 12,
        use_cohort_median: bool = True
    ):
        """
        Args:
            bounds: Dictionary mapping vital sign name to (min_val, max_val) physiological range.
            impute_vitals: Whether to apply imputation to missing vital signs.
            max_locf_hours: Max hours to forward-fill (LOCF). None for unlimited LOCF.
            use_cohort_median: Whether to fallback to cohort median for remaining initial NaNs.
        """
        self.bounds = bounds if bounds is not None else PHYSIOLOGICAL_BOUNDS
        self.impute_vitals = impute_vitals
        self.max_locf_hours = max_locf_hours
        self.use_cohort_median = use_cohort_median
        self.cohort_medians_: Dict[str, float] = {}

    def fit_cohort_medians(self, df: pd.DataFrame) -> Dict[str, float]:
        """Compute cohort medians for physiological vitals ONLY across training patients."""
        medians = {}
        for var in PHYSIOLOGICAL_BOUNDS.keys():
            if var in df.columns:
                s = df[var].dropna()
                medians[var] = float(s.median()) if not s.empty else 70.0
        self.cohort_medians_ = medians
        return medians

    def clean(self, df: pd.DataFrame, is_training: bool = True) -> pd.DataFrame:
        """
        Clean raw patient DataFrame.

        Steps:
          1. Sort by patient_id and time_step/ICULOS
          2. Deduplicate duplicate timestamps per patient
          3. Outlier rejection: set out-of-bounds values to NaN
          4. Configurable Imputation: LOCF forward-fill + training cohort median fallback
        
        Returns:
            Cleaned pd.DataFrame
        """
        cleaned_df = df.copy()

        # Step 1: Temporal ordering & deduplication
        time_col = "ICULOS" if "ICULOS" in cleaned_df.columns else "time_step"
        cleaned_df = cleaned_df.sort_values(by=["patient_id", time_col]).reset_index(drop=True)
        cleaned_df = cleaned_df.drop_duplicates(subset=["patient_id", time_col], keep="first")

        # Step 2: Outlier rejection using physiological bounds
        for var, (min_val, max_val) in self.bounds.items():
            if var in cleaned_df.columns:
                mask = (cleaned_df[var] < min_val) | (cleaned_df[var] > max_val)
                cleaned_df.loc[mask, var] = np.nan

        # Step 3: Compute cohort medians if training
        if is_training:
            self.fit_cohort_medians(cleaned_df)
        elif not self.cohort_medians_:
            raise RuntimeError(
                "Cleaner has not been fitted on training data yet. Call fit_cohort_medians(train_df) or clean(train_df, is_training=True) first."
            )

        # Step 4: Imputation if enabled
        if self.impute_vitals:
            vitals_to_impute = [v for v in self.bounds.keys() if v in cleaned_df.columns]
            
            # Forward fill per patient
            cleaned_df[vitals_to_impute] = cleaned_df.groupby("patient_id")[vitals_to_impute].ffill(
                limit=self.max_locf_hours
            )
            
            # Fallback to cohort median for remaining NaNs (initial hours) using fitted training medians
            if self.use_cohort_median:
                for v in vitals_to_impute:
                    med_val = self.cohort_medians_.get(v, np.nan)
                    if not np.isnan(med_val):
                        cleaned_df[v] = cleaned_df[v].fillna(med_val)

        return cleaned_df
