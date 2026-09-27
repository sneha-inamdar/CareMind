"""
PhysioNet 2019 Dataset Loader.

Discovers and loads patient .psv files into Pandas DataFrames while preserving:
  - Patient ID (derived from filename, e.g. 'p000001')
  - Hourly time step & ICULOS index
  - Original physiological parameters & laboratory values
  - SepsisLabel
"""

import os
import glob
import pandas as pd
from typing import List, Dict, Tuple, Optional


REQUIRED_VITAL_COLUMNS = ["HR", "O2Sat", "Temp", "SBP", "MAP", "DBP", "Resp", "EtCO2"]
LABEL_COLUMN = "SepsisLabel"


class PhysioNet2019Loader:
    """Loader for PhysioNet 2019 patient ASCII pipe-separated (.psv) files."""

    def __init__(self, raw_dir: str):
        self.raw_dir = os.path.abspath(raw_dir)

    def discover_patient_files(self) -> List[Tuple[str, str]]:
        """
        Discover all valid non-empty .psv files under raw_dir.
        
        Returns:
            List of tuples (patient_id, file_path) sorted by patient_id.
        """
        psv_paths = glob.glob(os.path.join(self.raw_dir, "**", "*.psv"), recursive=True)
        file_list = []
        for path in psv_paths:
            if os.path.getsize(path) == 0:
                continue
            filename = os.path.basename(path)
            patient_id = os.path.splitext(filename)[0]
            file_list.append((patient_id, path))
        
        file_list.sort(key=lambda x: x[0])
        return file_list

    def load_single_patient(self, file_path: str, patient_id: Optional[str] = None) -> pd.DataFrame:
        """
        Load a single patient .psv file.

        Args:
            file_path: Absolute or relative path to .psv file.
            patient_id: Optional patient identifier string.

        Returns:
            pd.DataFrame with patient_id column, time_step index, original vitals and SepsisLabel.
        """
        if patient_id is None:
            patient_id = os.path.splitext(os.path.basename(file_path))[0]

        df = pd.read_csv(file_path, sep="|")
        
        # Insert metadata columns without mutating raw physiological values
        df.insert(0, "patient_id", patient_id)
        if "time_step" not in df.columns:
            df.insert(1, "time_step", range(len(df)))

        return df

    def load_all_patients(self, max_patients: Optional[int] = None) -> pd.DataFrame:
        """
        Load multiple patient records into a single concatenated DataFrame.

        Args:
            max_patients: Optional limit on number of patient files to load.

        Returns:
            Concatenated pd.DataFrame preserving patient_id, temporal ordering, and raw values.
        """
        patient_files = self.discover_patient_files()
        if max_patients is not None and max_patients > 0:
            patient_files = patient_files[:max_patients]

        if not patient_files:
            raise FileNotFoundError(f"No valid non-empty .psv files found in raw directory '{self.raw_dir}'.")

        dfs = []
        for p_id, path in patient_files:
            try:
                df_p = self.load_single_patient(path, patient_id=p_id)
                dfs.append(df_p)
            except Exception as e:
                print(f"Warning: Skipped corrupted file {path}: {e}")

        combined_df = pd.concat(dfs, ignore_index=True)
        return combined_df
