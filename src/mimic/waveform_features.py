"""
MIMIC-IV Waveform Baseline Feature Extractor.

Computes defensible statistical, temporal, and morphological waveform features
from preprocessed 24-hour observation signal windows (ECG, ABP, PPG).
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List


class MIMICWaveformFeatureExtractor:
    """Baseline feature extraction engine for continuous waveform streams."""

    def extract_ecg_features(self, ecg_signal: np.ndarray, prefix: str = "ECG") -> Dict[str, float]:
        """Extract baseline statistical and temporal features from clean ECG window."""
        if len(ecg_signal) == 0:
            return {
                f"{prefix}_mean": 0.0, f"{prefix}_std": 0.0, f"{prefix}_rms": 0.0,
                f"{prefix}_ptp": 0.0, f"{prefix}_zero_crossings": 0.0, f"{prefix}_is_missing": 1.0
            }

        arr = np.nan_to_num(ecg_signal)
        mean_val = float(np.mean(arr))
        std_val = float(np.std(arr))
        rms_val = float(np.sqrt(np.mean(arr ** 2)))
        ptp_val = float(np.ptp(arr))
        zero_cross = float(np.sum(np.diff(arr > 0) != 0))

        return {
            f"{prefix}_mean": round(mean_val, 4),
            f"{prefix}_std": round(std_val, 4),
            f"{prefix}_rms": round(rms_val, 4),
            f"{prefix}_ptp": round(ptp_val, 4),
            f"{prefix}_zero_crossings": zero_cross,
            f"{prefix}_is_missing": 0.0
        }

    def extract_abp_features(self, abp_signal: np.ndarray, prefix: str = "ABP") -> Dict[str, float]:
        """Extract baseline blood pressure trend and variability features from ABP window."""
        if len(abp_signal) == 0:
            return {
                f"{prefix}_mean": 0.0, f"{prefix}_std": 0.0, f"{prefix}_sys_max": 0.0,
                f"{prefix}_dia_min": 0.0, f"{prefix}_pulse_pressure": 0.0, f"{prefix}_is_missing": 1.0
            }

        arr = np.nan_to_num(abp_signal)
        mean_val = float(np.mean(arr))
        std_val = float(np.std(arr))
        sys_max = float(np.max(arr))
        dia_min = float(np.min(arr))
        pulse_press = sys_max - dia_min

        return {
            f"{prefix}_mean": round(mean_val, 4),
            f"{prefix}_std": round(std_val, 4),
            f"{prefix}_sys_max": round(sys_max, 4),
            f"{prefix}_dia_min": round(dia_min, 4),
            f"{prefix}_pulse_pressure": round(pulse_press, 4),
            f"{prefix}_is_missing": 0.0
        }

    def extract_ppg_features(self, ppg_signal: np.ndarray, prefix: str = "PPG") -> Dict[str, float]:
        """Extract photoplethysmogram pulse amplitude and variability features from PPG window."""
        if len(ppg_signal) == 0:
            return {
                f"{prefix}_mean": 0.0, f"{prefix}_std": 0.0, f"{prefix}_peak_max": 0.0,
                f"{prefix}_trough_min": 0.0, f"{prefix}_amplitude_range": 0.0, f"{prefix}_is_missing": 1.0
            }

        arr = np.nan_to_num(ppg_signal)
        mean_val = float(np.mean(arr))
        std_val = float(np.std(arr))
        peak_max = float(np.max(arr))
        trough_min = float(np.min(arr))
        amp_range = peak_max - trough_min

        return {
            f"{prefix}_mean": round(mean_val, 4),
            f"{prefix}_std": round(std_val, 4),
            f"{prefix}_peak_max": round(peak_max, 4),
            f"{prefix}_trough_min": round(trough_min, 4),
            f"{prefix}_amplitude_range": round(amp_range, 4),
            f"{prefix}_is_missing": 0.0
        }

    def extract_stay_waveform_features(
        self,
        ecg_sig: np.ndarray = None,
        abp_sig: np.ndarray = None,
        ppg_sig: np.ndarray = None
    ) -> Dict[str, float]:
        """
        Combine waveform features across available modalities into a single feature dictionary.
        """
        feats = {}
        feats.update(self.extract_ecg_features(ecg_sig if ecg_sig is not None else np.array([])))
        feats.update(self.extract_abp_features(abp_sig if abp_sig is not None else np.array([])))
        feats.update(self.extract_ppg_features(ppg_sig if ppg_sig is not None else np.array([])))
        return feats
