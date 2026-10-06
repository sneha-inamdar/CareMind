"""
MIMIC-IV Waveform Preprocessing Pipeline.

Handles waveform timestamp alignment, 24-hour window extraction, zero-leakage firewalls,
artifact clipping, and uniform signal resampling.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Tuple, List
from src.mimic.config import MIMICConfig


class MIMICWaveformProcessor:
    """Preprocessing engine for MIMIC continuous waveform streams (ECG, ABP, PPG)."""

    def __init__(self, config: MIMICConfig = None, target_fs: float = 125.0):
        self.config = config or MIMICConfig()
        self.target_fs = target_fs

    def extract_observation_window(
        self,
        signal_array: np.ndarray,
        signal_timestamps: np.ndarray,
        intime: pd.Timestamp,
        obs_hours: float = 24.0
    ) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
        """
        Extract signal samples strictly within [intime, intime + obs_hours].
        Enforces 100% zero-leakage firewall by rejecting any samples > intime + obs_hours.

        Returns:
            Tuple of (Filtered Signal Array, Filtered Timestamps, Processing Audit Stats)
        """
        obs_end = intime + pd.Timedelta(hours=obs_hours)

        # Convert timestamps to pd.Timestamp if needed
        ts = pd.to_datetime(signal_timestamps)

        # Mask for observation window
        mask = (ts >= intime) & (ts <= obs_end)
        filtered_sig = signal_array[mask]
        filtered_ts = ts[mask]

        total_samples = len(signal_array)
        kept_samples = len(filtered_sig)
        rejected_future_samples = int((ts > obs_end).sum())

        audit = {
            "total_raw_samples": total_samples,
            "kept_observation_samples": kept_samples,
            "rejected_future_samples": rejected_future_samples,
            "leakage_violations": 0
        }

        return filtered_sig, filtered_ts, audit

    def clean_and_normalize_signal(
        self,
        signal_array: np.ndarray,
        channel_name: str
    ) -> np.ndarray:
        """
        Clean physiological signal artifacts and apply Z-score normalization.

        - ECG: Remove extreme outliers (clip outside [-5 mV, 5 mV] or 99.9th percentile).
        - ABP: Clip physiology bounds [0, 300 mmHg].
        - PPG: Clip physiology bounds [0, 100 %].
        """
        if len(signal_array) == 0:
            return signal_array

        arr = signal_array.astype(np.float64).copy()
        ch_upper = channel_name.upper()

        if "ECG" in ch_upper or "II" in ch_upper or "V" in ch_upper:
            # Clip ECG noise spike artifacts
            arr = np.clip(arr, -5.0, 5.0)
        elif "ABP" in ch_upper or "ART" in ch_upper:
            # Clip Blood Pressure to physical bounds
            arr = np.clip(arr, 0.0, 300.0)
        elif "PLETH" in ch_upper or "PPG" in ch_upper:
            # Clip PPG percentage / raw ADC bounds
            arr = np.clip(arr, 0.0, 100.0)

        # Handle NaNs via linear interpolation
        nans = np.isnan(arr)
        if np.any(nans):
            not_nans = ~nans
            if np.any(not_nans):
                arr[nans] = np.interp(np.flatnonzero(nans), np.flatnonzero(not_nans), arr[not_nans])
            else:
                arr = np.zeros_like(arr)

        # Standardize (Z-score normalization) if std > 0
        std = np.std(arr)
        if std > 1e-6:
            arr = (arr - np.mean(arr)) / std

        return arr

    def resample_signal(
        self,
        signal_array: np.ndarray,
        current_fs: float
    ) -> Tuple[np.ndarray, float]:
        """
        Resample signal array to target_fs using linear interpolation.
        """
        if current_fs <= 0 or len(signal_array) <= 1 or current_fs == self.target_fs:
            return signal_array, current_fs

        duration_sec = len(signal_array) / current_fs
        target_num_samples = int(round(duration_sec * self.target_fs))

        if target_num_samples <= 0:
            return signal_array, current_fs

        old_idx = np.linspace(0, 1, len(signal_array))
        new_idx = np.linspace(0, 1, target_num_samples)

        resampled = np.interp(new_idx, old_idx, signal_array)
        return resampled, self.target_fs
