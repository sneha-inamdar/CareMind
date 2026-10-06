"""
MIMIC Data Loader Module for MIMIC-IV Clinical & Demo Datasets.

Loads raw or compressed CSV tables (patients, admissions, icustays, chartevents, labevents)
from a specified directory path.
"""

import os
import pandas as pd
from typing import Dict, Any, Optional
from src.mimic.config import MIMICConfig


class MIMICDataLoader:
    """Data loader engine supporting both full MIMIC-IV and MIMIC-IV Demo datasets."""

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.hosp_dir = os.path.join(data_dir, "hosp") if os.path.exists(os.path.join(data_dir, "hosp")) else data_dir
        self.icu_dir = os.path.join(data_dir, "icu") if os.path.exists(os.path.join(data_dir, "icu")) else data_dir

    def _find_file(self, base_name: str, folder: str) -> str:
        """Find either .csv or .csv.gz file in the target folder."""
        path_gz = os.path.join(folder, f"{base_name}.csv.gz")
        path_csv = os.path.join(folder, f"{base_name}.csv")

        if os.path.exists(path_gz):
            return path_gz
        elif os.path.exists(path_csv):
            return path_csv
        else:
            raise FileNotFoundError(f"Neither {base_name}.csv nor {base_name}.csv.gz found in {folder}")

    def load_patients(self) -> pd.DataFrame:
        path = self._find_file("patients", self.hosp_dir)
        return pd.read_csv(path)

    def load_admissions(self) -> pd.DataFrame:
        path = self._find_file("admissions", self.hosp_dir)
        return pd.read_csv(path)

    def load_icustays(self) -> pd.DataFrame:
        path = self._find_file("icustays", self.icu_dir)
        return pd.read_csv(path)

    def load_chartevents(self, nrows: Optional[int] = None) -> pd.DataFrame:
        path = self._find_file("chartevents", self.icu_dir)
        return pd.read_csv(path, nrows=nrows)

    def load_labevents(self, nrows: Optional[int] = None) -> pd.DataFrame:
        path = self._find_file("labevents", self.hosp_dir)
        return pd.read_csv(path, nrows=nrows)

    def load_d_items(self) -> pd.DataFrame:
        path = self._find_file("d_items", self.icu_dir)
        return pd.read_csv(path)

    def load_d_labitems(self) -> pd.DataFrame:
        path = self._find_file("d_labitems", self.hosp_dir)
        return pd.read_csv(path)
