"""
MIMIC-IV Waveform Record Discovery & Linkage Subsystem.

Discovers MIMIC-IV Waveform (mimic4wdb/0.1.0) records, parses header timestamps
and signal channels, and establishes zero-leakage patient-level linkages
with MIMIC-IV ICU stays.
"""

import os
import re
import urllib.request
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from src.mimic.config import MIMICConfig


class MIMICWaveformLinker:
    """Linker engine connecting WFDB header metadata to MIMIC-IV clinical ICU stays."""

    def __init__(self, config: MIMICConfig = None, base_url: str = "https://physionet.org/files/mimic4wdb/0.1.0/"):
        self.config = config or MIMICConfig()
        self.base_url = base_url

    def parse_wfdb_date_time(self, date_str: str, time_str: str) -> str:
        """Convert WFDB header date (dd/mm/yyyy) and time into ISO timestamp string."""
        try:
            parts = date_str.split('/')
            if len(parts) == 3:
                day, month, year = parts[0], parts[1], parts[2]
                iso_date = f"{year}-{int(month):02d}-{int(day):02d}"
                return f"{iso_date} {time_str}"
        except Exception:
            pass
        return f"{date_str} {time_str}"

    def parse_header_metadata(self, header_text: str, sub_dir: str, rec_name: str) -> Dict[str, Any]:
        """
        Parse raw WFDB .hea text to extract sampling rate, duration, start timestamp, and channels.
        """
        lines = [l.strip() for l in header_text.strip().split("\n") if l.strip() and not l.strip().startswith("#")]
        if not lines:
            raise ValueError("Empty or header-only file.")

        header_tokens = lines[0].split()
        rec_id = header_tokens[0]
        fs = float(header_tokens[2].split('/')[0]) if len(header_tokens) > 2 else 0.0
        num_samples = int(header_tokens[3]) if len(header_tokens) > 3 else 0
        base_time = header_tokens[4] if len(header_tokens) > 4 else ""
        base_date = header_tokens[5] if len(header_tokens) > 5 else ""

        start_iso = self.parse_wfdb_date_time(base_date, base_time)
        duration_sec = (num_samples / fs) if fs > 0 else 0.0

        channels = []
        for l in lines[1:]:
            parts = l.split()
            if len(parts) >= 9 and not parts[0].startswith("~"):
                channels.append(parts[-1])

        has_ecg = any(c.upper() in ["II", "V", "ECG", "I", "III", "AVR", "AVL", "AVF"] for c in channels)
        has_abp = any(c.upper() in ["ABP", "ART", "BP"] for c in channels)
        has_ppg = any(c.upper() in ["PLETH", "PPG", "SPO2"] for c in channels)

        # Determine Tier
        if has_ecg and has_abp and has_ppg:
            tier = "Tier 1 (ECG+ABP+PPG)"
        elif has_ecg and has_ppg:
            tier = "Tier 2 (ECG+PPG)"
        elif has_ecg:
            tier = "Tier 3 (ECG only)"
        else:
            tier = "Tier 4 (Other)"

        subj_match = re.search(r"p(\d{8})", sub_dir)
        subject_id = int(subj_match.group(1)) if subj_match else None

        return {
            "subject_id": subject_id,
            "record_dir": sub_dir,
            "record_name": rec_name,
            "fs": fs,
            "num_samples": num_samples,
            "duration_hrs": round(duration_sec / 3600.0, 2),
            "start_timestamp": start_iso,
            "channels": channels,
            "has_ecg": has_ecg,
            "has_abp": has_abp,
            "has_ppg": has_ppg,
            "tier": tier
        }

    def link_cohort_waveforms(
        self,
        cohort: pd.DataFrame,
        waveform_metadata: List[Dict[str, Any]]
    ) -> pd.DataFrame:
        """
        Link clinical cohort ICU stays to waveform records matching subject_id
        and overlapping the initial 24h observation window [intime, intime + 24h].

        Returns:
            Reproducible Linkage DataFrame with waveform record details and 24h overlap status.
        """
        if not waveform_metadata:
            return pd.DataFrame()

        df_wave = pd.DataFrame(waveform_metadata)
        df_wave["start_timestamp"] = pd.to_datetime(df_wave["start_timestamp"], errors="coerce")
        df_wave["end_timestamp"] = df_wave["start_timestamp"] + pd.to_timedelta(df_wave["duration_hrs"], unit="h")

        cohort_links = []

        for _, row in cohort.iterrows():
            subj_id = row["subject_id"]
            stay_id = row["stay_id"]
            intime = pd.to_datetime(row["intime"])
            obs_end = intime + pd.Timedelta(hours=self.config.observation_window_hours)

            # Match subject_id
            subj_waves = df_wave[df_wave["subject_id"] == subj_id]

            if subj_waves.empty:
                cohort_links.append({
                    "subject_id": subj_id,
                    "stay_id": stay_id,
                    "intime": intime,
                    "obs_end": obs_end,
                    "waveform_record": None,
                    "has_waveform_link": False,
                    "overlap_with_24h_window": False,
                    "tier": "No Waveform"
                })
            else:
                for _, w in subj_waves.iterrows():
                    w_start = w["start_timestamp"]
                    w_end = w["end_timestamp"]

                    # Check temporal overlap with [intime, intime + 24h]
                    has_overlap = False
                    if pd.notna(w_start) and pd.notna(w_end):
                        has_overlap = (w_start < obs_end) and (w_end > intime)

                    cohort_links.append({
                        "subject_id": subj_id,
                        "stay_id": stay_id,
                        "intime": intime,
                        "obs_end": obs_end,
                        "waveform_record": w["record_name"],
                        "waveform_start": w_start,
                        "waveform_end": w_end,
                        "fs": w["fs"],
                        "duration_hrs": w["duration_hrs"],
                        "has_ecg": w["has_ecg"],
                        "has_abp": w["has_abp"],
                        "has_ppg": w["has_ppg"],
                        "has_waveform_link": True,
                        "overlap_with_24h_window": has_overlap,
                        "tier": w["tier"]
                    })

        return pd.DataFrame(cohort_links)
