"""
PhysioNet 2019 Leakage-Safe Patient Splitter.

Performs patient-level train/validation/test splitting:
  - Ensures 0% patient leakage across splits
  - Stratified by patient-level sepsis outcome (if class count >= 2)
  - 100% reproducible with fixed random seed
"""

import numpy as np
import pandas as pd
from typing import Tuple, Dict, Set, Any
from sklearn.model_selection import train_test_split


class PhysioNet2019Splitter:
    """Leakage-safe patient-level dataset splitter."""

    def __init__(
        self,
        train_ratio: float = 0.70,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        seed: int = 42
    ):
        """
        Args:
            train_ratio: Proportion of patients for training set.
            val_ratio: Proportion of patients for validation set.
            test_ratio: Proportion of patients for test set.
            seed: Fixed random seed for reproducibility.
        """
        assert abs((train_ratio + val_ratio + test_ratio) - 1.0) < 1e-5, "Splits must sum to 1.0."
        self.train_ratio = train_ratio
        self.val_ratio = val_ratio
        self.test_ratio = test_ratio
        self.seed = seed

    def split_patients(self, df: pd.DataFrame) -> Tuple[Set[str], Set[str], Set[str]]:
        """
        Compute mutually exclusive patient IDs for train, val, and test splits.

        Args:
            df: Patient DataFrame with patient_id and SepsisLabel.

        Returns:
            Tuple of (train_patient_ids, val_patient_ids, test_patient_ids).
        """
        # Determine patient-level sepsis status for stratification
        patient_sepsis = df.groupby("patient_id")["SepsisLabel"].max().reset_index()
        patient_ids = np.asarray(patient_sepsis["patient_id"].values, dtype=str)
        sepsis_labels = np.asarray(patient_sepsis["SepsisLabel"].values, dtype=int)

        # Check if stratification is possible (need at least 2 samples per class)
        unique_classes, class_counts = np.unique(sepsis_labels, return_counts=True)
        can_stratify = len(unique_classes) > 1 and np.min(class_counts) >= 2
        stratify_param = sepsis_labels if can_stratify else None

        # First split: Train vs (Val + Test)
        test_val_ratio = self.val_ratio + self.test_ratio
        train_ids, temp_ids, y_train, y_temp = train_test_split(
            patient_ids,
            sepsis_labels,
            test_size=test_val_ratio,
            random_state=self.seed,
            stratify=stratify_param
        )

        # Second split: Val vs Test
        val_prop = self.val_ratio / test_val_ratio
        temp_classes, temp_counts = np.unique(y_temp, return_counts=True)
        can_stratify_temp = len(temp_classes) > 1 and np.min(temp_counts) >= 2
        stratify_temp = y_temp if can_stratify_temp else None

        val_ids, test_ids, _, _ = train_test_split(
            temp_ids,
            y_temp,
            test_size=(1.0 - val_prop),
            random_state=self.seed,
            stratify=stratify_temp
        )

        train_set = set(train_ids)
        val_set = set(val_ids)
        test_set = set(test_ids)

        # Verify zero patient leakage
        assert len(train_set & val_set) == 0, "Patient overlap detected between Train and Val!"
        assert len(train_set & test_set) == 0, "Patient overlap detected between Train and Test!"
        assert len(val_set & test_set) == 0, "Patient overlap detected between Val and Test!"

        return train_set, val_set, test_set

    def split_dataframe(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
        """
        Partition full DataFrame into Train, Val, and Test DataFrames.

        Returns:
            Tuple of (train_df, val_df, test_df, metadata_dict).
        """
        train_ids, val_ids, test_ids = self.split_patients(df)

        train_df = df[df["patient_id"].isin(train_ids)].reset_index(drop=True)
        val_df = df[df["patient_id"].isin(val_ids)].reset_index(drop=True)
        test_df = df[df["patient_id"].isin(test_ids)].reset_index(drop=True)

        metadata = {
            "split_seed": self.seed,
            "train_patients": len(train_ids),
            "val_patients": len(val_ids),
            "test_patients": len(test_ids),
            "total_patients": len(train_ids) + len(val_ids) + len(test_ids),
            "train_rows": len(train_df),
            "val_rows": len(val_df),
            "test_rows": len(test_df),
            "train_sepsis_patients": int(train_df.groupby("patient_id")["SepsisLabel"].max().sum()),
            "val_sepsis_patients": int(val_df.groupby("patient_id")["SepsisLabel"].max().sum()),
            "test_sepsis_patients": int(test_df.groupby("patient_id")["SepsisLabel"].max().sum())
        }

        return train_df, val_df, test_df, metadata
