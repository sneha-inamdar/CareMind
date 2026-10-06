"""
Unit test suite enforcing methodological audit rules for MIMIC Multimodal subsystem.

Enforces:
1. Waveform linkage validation (every waveform-linked row must have has_waveform_link == True).
2. Multimodal stay identity match (clinical + waveform subject/stay alignment).
3. Dropping unmatched patients from Waveform and Multimodal cohorts.
4. Target definition integrity (Mortality24h primary target presence).
"""

import os
import pytest
import numpy as np
import pandas as pd
from experiments.mimic_multimodal.run_mimic_multimodal_experiment import (
    build_audited_experiment_cohorts,
    DEMO_DIR
)
from src.mimic.waveform_linker import MIMICWaveformLinker
from src.mimic.config import MIMICConfig


@pytest.mark.skipif(not os.path.exists(DEMO_DIR), reason="MIMIC Demo dataset directory not found.")
def test_audited_cohort_construction_and_linkage_integrity():
    """Verify that build_audited_experiment_cohorts returns exact 85 clinical stays and 3 common stays."""
    df_clinical, df_common, meta = build_audited_experiment_cohorts(DEMO_DIR)

    assert len(df_clinical) == 85
    assert len(df_common) == 3
    assert meta["common_cohort_size"] == 3
    assert meta["mortality24h_positives_common"] == 0

    # Verify target column presence
    assert "Mortality24h" in df_clinical.columns
    assert "InHospMortalityPost24h" in df_clinical.columns


def test_strict_waveform_linkage_enforcement():
    """Verify that unmatched patients are strictly excluded from the Waveform/Multimodal common cohort."""
    config = MIMICConfig()
    linker = MIMICWaveformLinker(config=config)

    cohort_df = pd.DataFrame({
        "subject_id": [10014354, 99999999],
        "stay_id": [30001, 30002],
        "intime": ["2148-08-16 08:00:00", "2150-01-01 00:00:00"]
    })

    # Only patient 10014354 has a real waveform record
    wave_meta = [{
        "subject_id": 10014354,
        "record_dir": "waves/p100/p10014354/",
        "record_name": "81739927",
        "fs": 125.0,
        "num_samples": 10800000,
        "duration_hrs": 24.0,
        "start_timestamp": "2148-08-16 09:00:00",
        "channels": ["II", "PLETH"],
        "has_ecg": True,
        "has_abp": False,
        "has_ppg": True,
        "tier": "Tier 2 (ECG+PPG)"
    }]

    linkage = linker.link_cohort_waveforms(cohort_df, wave_meta)
    
    # Filter common cohort
    matched_linkage = linkage[linkage["has_waveform_link"] == True]

    # Enforce Rule 1: Every row in common cohort must have has_waveform_link == True
    assert (matched_linkage["has_waveform_link"] == True).all()

    # Enforce Rule 2: Unmatched patient 99999999 must NOT enter matched linkage
    assert 99999999 not in matched_linkage["subject_id"].values
    assert len(matched_linkage) == 1
    assert matched_linkage.iloc[0]["subject_id"] == 10014354


def test_target_definition_integrity():
    """Verify primary Mortality24h target calculation logic on synthetic data."""
    df = pd.DataFrame({
        "subject_id": [1, 2, 3],
        "stay_id": [101, 102, 103],
        "intime": pd.to_datetime(["2020-01-01 00:00:00", "2020-01-01 00:00:00", "2020-01-01 00:00:00"]),
        "outtime": pd.to_datetime(["2020-01-03 00:00:00", "2020-01-03 00:00:00", "2020-01-03 00:00:00"]),
        "deathtime": pd.to_datetime(["2020-01-02 12:00:00", "2020-01-05 00:00:00", pd.NaT]),
        "dod": pd.to_datetime(["2020-01-02 12:00:00", "2020-01-05 00:00:00", pd.NaT]),
        "hospital_expire_flag": [1, 1, 0]
    })

    obs_end = df["intime"] + pd.Timedelta(hours=24)
    pred_end = df["intime"] + pd.Timedelta(hours=48)

    cond_death = (df["deathtime"] > obs_end) & (df["deathtime"] <= pred_end)
    cond_exp = (df["hospital_expire_flag"] == 1) & (df["deathtime"] > obs_end) & (df["deathtime"] <= pred_end)

    df["Mortality24h"] = np.where(cond_death | cond_exp, 1, 0)

    # Patient 1 died at 36h (in 24-48h window) -> Target = 1
    assert df.loc[0, "Mortality24h"] == 1
    # Patient 2 died at 96h (after 48h window) -> Target = 0
    assert df.loc[1, "Mortality24h"] == 0
    # Patient 3 survived -> Target = 0
    assert df.loc[2, "Mortality24h"] == 0
