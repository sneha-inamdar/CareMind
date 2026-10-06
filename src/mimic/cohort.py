"""
MIMIC Cohort Selection and Target Construction Subsystem.

Processes patients, admissions, and icustays to construct:
  - Adult cohort (anchor_age >= 18)
  - First ICU stay per patient
  - Stay duration >= 24h (los >= 1.0 day)
  - Survived initial 24h observation window
  - Target labels: Mortality24h (24h-48h window) & InHospMortalityPost24h
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple
from src.mimic.config import MIMICConfig


class MIMICCohortSelector:
    """Cohort selection and target construction pipeline for MIMIC datasets."""

    def __init__(self, config: MIMICConfig = None):
        self.config = config or MIMICConfig()

    def build_cohort(
        self,
        patients: pd.DataFrame,
        admissions: pd.DataFrame,
        icustays: pd.DataFrame
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Process patients, admissions, and icustays to generate the filtered cohort and targets.

        Returns:
            Tuple of (Cohort DataFrame, Summary Pipeline Audit Stats Dict)
        """
        initial_stays = len(icustays)

        df = icustays.copy()
        df["intime"] = pd.to_datetime(df["intime"])
        df["outtime"] = pd.to_datetime(df["outtime"])

        # Merge patient metadata
        df = df.merge(
            patients[["subject_id", "gender", "anchor_age", "dod"]],
            on="subject_id",
            how="left"
        )
        df["dod"] = pd.to_datetime(df["dod"])

        # Merge admissions metadata
        df = df.merge(
            admissions[["hadm_id", "admittime", "dischtime", "deathtime", "hospital_expire_flag"]],
            on="hadm_id",
            how="left"
        )
        df["admittime"] = pd.to_datetime(df["admittime"])
        df["dischtime"] = pd.to_datetime(df["dischtime"])
        df["deathtime"] = pd.to_datetime(df["deathtime"])

        # 1. Filter Adult Stays (anchor_age >= 18)
        df_adult = df[df["anchor_age"] >= 18].copy()
        adult_stays = len(df_adult)

        # 2. Filter First ICU Stay per Patient
        first_idx = df_adult.groupby("subject_id")["intime"].idxmin()
        df_first = df_adult.loc[first_idx].copy()
        first_stays_count = len(df_first)

        # 3. Filter ICU Length of Stay >= 24 Hours
        df_los24 = df_first[df_first["los"] >= 1.0].copy()
        los24_count = len(df_los24)

        # 4. Survived Initial 24-Hour Observation Window
        obs_end = df_los24["intime"] + pd.Timedelta(hours=self.config.observation_window_hours)
        df_survived24 = df_los24[
            (df_los24["outtime"] > obs_end) &
            (df_los24["deathtime"].isna() | (df_los24["deathtime"] > obs_end)) &
            (df_los24["dod"].isna() | (df_los24["dod"] > obs_end))
        ].copy()
        survived24_count = len(df_survived24)

        cohort = df_survived24.copy()

        # 5. Target Construction
        pred_end = cohort["intime"] + pd.Timedelta(hours=self.config.observation_window_hours + self.config.prediction_window_hours)
        obs_end_cohort = cohort["intime"] + pd.Timedelta(hours=self.config.observation_window_hours)

        # Mortality24h (24h to 48h prediction window)
        cond_deathtime_win = (cohort["deathtime"] > obs_end_cohort) & (cohort["deathtime"] <= pred_end)
        cond_dod_win = (cohort["dod"] > obs_end_cohort) & (cohort["dod"] <= pred_end)
        cond_expire_win = (cohort["hospital_expire_flag"] == 1) & (cohort["deathtime"] > obs_end_cohort) & (cohort["deathtime"] <= pred_end)

        cohort["Mortality24h"] = np.where(cond_deathtime_win | cond_dod_win | cond_expire_win, 1, 0)

        # Overall In-Hospital Mortality Post 24h
        cohort["InHospMortalityPost24h"] = np.where(
            (cohort["hospital_expire_flag"] == 1) & (cohort["deathtime"] > obs_end_cohort), 1, 0
        )

        audit_stats = {
            "initial_icu_stays": initial_stays,
            "adult_stays": adult_stays,
            "first_icu_stays": first_stays_count,
            "los_ge_24h_stays": los24_count,
            "survived_initial_24h_stays": survived24_count,
            "final_cohort_size": len(cohort),
            "mortality24h_positives": int((cohort["Mortality24h"] == 1).sum()),
            "mortality24h_negatives": int((cohort["Mortality24h"] == 0).sum()),
            "inhosp_mortality_post24h_positives": int((cohort["InHospMortalityPost24h"] == 1).sum())
        }

        return cohort, audit_stats
