"""
Unit tests for MIMIC-IV Waveform Subsystem (Phase 6 Waveform Milestone).

Validates MIMICWaveformLinker, MIMICWaveformProcessor, and MIMICWaveformFeatureExtractor.
"""

import pytest
import numpy as np
import pandas as pd
from src.mimic.config import MIMICConfig
from src.mimic.waveform_linker import MIMICWaveformLinker
from src.mimic.waveform_processor import MIMICWaveformProcessor
from src.mimic.waveform_features import MIMICWaveformFeatureExtractor


def test_waveform_linker_metadata_parsing():
    """Verify MIMICWaveformLinker header parsing, timestamp parsing, and Tier assignment."""
    linker = MIMICWaveformLinker()

    sample_hea = """#wfdb 10.7
81739927/21 4 125 6661120 09:00:17.566 16/8/2148
81739927_0001e.dat 516x4 200/mV 14 8192 0 512 0 II
81739927_0001e.dat 516x4 200/mV 14 8192 0 512 0 ABP
81739927_0001e.dat 516x4 200/mV 14 8192 0 512 0 PLETH
"""
    meta = linker.parse_header_metadata(sample_hea, "waves/p100/p10014354/", "81739927")

    assert meta["subject_id"] == 10014354
    assert meta["fs"] == 125.0
    assert meta["has_ecg"] is True
    assert meta["has_abp"] is True
    assert meta["has_ppg"] is True
    assert meta["tier"] == "Tier 1 (ECG+ABP+PPG)"
    assert meta["start_timestamp"] == "2148-08-16 09:00:17.566"


def test_waveform_linker_cohort_linkage():
    """Verify patient-level stay linkage to waveform records."""
    config = MIMICConfig()
    linker = MIMICWaveformLinker(config=config)

    cohort_df = pd.DataFrame({
        "subject_id": [10014354, 99999999],
        "stay_id": [30001, 30002],
        "intime": ["2148-08-16 08:00:00", "2150-01-01 00:00:00"]
    })

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
    assert len(linkage) == 2
    
    match1 = linkage[linkage["stay_id"] == 30001].iloc[0]
    assert match1["has_waveform_link"] == True
    assert match1["overlap_with_24h_window"] == True
    assert match1["tier"] == "Tier 2 (ECG+PPG)"

    match2 = linkage[linkage["stay_id"] == 30002].iloc[0]
    assert match2["has_waveform_link"] == False
    assert match2["overlap_with_24h_window"] == False


def test_waveform_processor_zero_leakage_firewall():
    """Verify MIMICWaveformProcessor rejects future samples (> 24h) and preserves observation window."""
    processor = MIMICWaveformProcessor(target_fs=125.0)
    intime = pd.Timestamp("2150-01-01 00:00:00")

    # Generate 36 hours of timestamps at 1 Hz
    ts = pd.date_range(start="2150-01-01 00:00:00", periods=36*3600, freq="1s")
    signal = np.sin(np.linspace(0, 100, len(ts)))

    filtered_sig, filtered_ts, audit = processor.extract_observation_window(
        signal_array=signal,
        signal_timestamps=ts,
        intime=intime,
        obs_hours=24.0
    )

    assert audit["leakage_violations"] == 0
    assert audit["kept_observation_samples"] == 24 * 3600 + 1
    assert audit["rejected_future_samples"] > 0
    assert filtered_ts.max() <= intime + pd.Timedelta(hours=24)


def test_waveform_processor_cleaning_and_resampling():
    """Verify signal artifact clipping, Z-score normalization, and linear resampling."""
    processor = MIMICWaveformProcessor(target_fs=100.0)

    # Synthetic noisy ECG with spike outliers
    raw_ecg = np.array([0.1, 0.2, 50.0, -20.0, 0.5, 0.3, np.nan, 0.4])
    cleaned = processor.clean_and_normalize_signal(raw_ecg, channel_name="II")

    assert not np.isnan(cleaned).any()
    assert abs(np.mean(cleaned)) < 1e-4
    assert abs(np.std(cleaned) - 1.0) < 1e-4

    # Resample 125 Hz signal to 100 Hz
    sig_125 = np.sin(np.linspace(0, 10, 125))
    resampled, new_fs = processor.resample_signal(sig_125, current_fs=125.0)

    assert new_fs == 100.0
    assert len(resampled) == 100


def test_waveform_feature_extractor():
    """Verify MIMICWaveformFeatureExtractor extracts baseline features for ECG, ABP, and PPG."""
    extractor = MIMICWaveformFeatureExtractor()

    ecg = np.array([0.1, 0.5, -0.2, 0.8, -0.4, 0.3, 0.0])
    abp = np.array([120.0, 118.0, 75.0, 80.0, 125.0, 70.0])
    ppg = np.array([50.0, 80.0, 40.0, 85.0, 35.0])

    feats = extractor.extract_stay_waveform_features(ecg_sig=ecg, abp_sig=abp, ppg_sig=ppg)

    assert feats["ECG_is_missing"] == 0.0
    assert feats["ABP_is_missing"] == 0.0
    assert feats["PPG_is_missing"] == 0.0
    assert feats["ABP_sys_max"] == 125.0
    assert feats["ABP_dia_min"] == 70.0
    assert feats["ABP_pulse_pressure"] == 55.0

    # Missing ABP test
    feats_missing_abp = extractor.extract_stay_waveform_features(ecg_sig=ecg, abp_sig=None, ppg_sig=ppg)
    assert feats_missing_abp["ABP_is_missing"] == 1.0
    assert feats_missing_abp["ABP_mean"] == 0.0
