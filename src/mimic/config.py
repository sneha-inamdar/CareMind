"""
MIMIC Dataset Configuration and Metadata Definitions (Audited).

Contains schema constants, PhysioNet itemid mappings for chartevents and labevents,
subset specifications, audited outcome targets (Mortality24h), waveform fallback tiers,
and credentialing guidelines for CareMind.
"""

import os
from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass(frozen=True)
class MIMICItemIDs:
    """PhysioNet itemid mappings for MIMIC-IV clinical chart and lab events."""
    # Vitals (icu/chartevents)
    HEART_RATE: List[int] = field(default_factory=lambda: [220045])
    SYS_BP: List[int] = field(default_factory=lambda: [220050, 220179])  # Arterial + NIBP
    DIA_BP: List[int] = field(default_factory=lambda: [220051, 220180])  # Arterial + NIBP
    MAP_BP: List[int] = field(default_factory=lambda: [220052, 220181])  # Arterial + NIBP
    SPO2: List[int] = field(default_factory=lambda: [220277])
    RESP_RATE: List[int] = field(default_factory=lambda: [220210])
    TEMPERATURE: List[int] = field(default_factory=lambda: [223761, 223762])  # Fahrenheit & Celsius

    # Core Labs (hosp/labevents)
    LACTATE: List[int] = field(default_factory=lambda: [50813])
    WBC: List[int] = field(default_factory=lambda: [51301])
    CREATININE: List[int] = field(default_factory=lambda: [50912])
    PH: List[int] = field(default_factory=lambda: [50820])


@dataclass
class MIMICConfig:
    """Central configuration for MIMIC-IV research integration in CareMind."""
    # Repository & local paths
    data_dir: str = os.path.join("data", "mimic")
    clinical_dir: str = os.path.join("data", "mimic", "clinical")
    waveform_dir: str = os.path.join("data", "mimic", "waveform")
    processed_dir: str = os.path.join("data", "mimic", "processed")

    # PhysioNet Dataset Handles
    physionet_clinical_handle: str = "mimiciv/2.2"
    physionet_waveform_handle: str = "mimic4wdb/0.1.0"
    physionet_url: str = "https://physionet.org/content/mimiciv/2.2/"
    physionet_waveform_url: str = "https://physionet.org/content/mimic4wdb/0.1.0/"

    # Benchmark Subsets (Computational Efficiency)
    clinical_subset_size: int = 1000  # Prototyping subset of adult ICU stays
    waveform_subset_size: int = 100   # Matched waveform ICU stays
    min_stay_duration_hours: float = 24.0

    # Observation and Prediction Windows (Hours)
    observation_window_hours: float = 24.0
    prediction_window_hours: float = 24.0
    primary_target_column: str = "Mortality24h"
    secondary_target_column: str = "AcuteDeterioration24h"

    # Core Vital Features
    core_vitals: List[str] = field(
        default_factory=lambda: ["HR", "SBP", "DBP", "MAP", "SpO2", "Resp", "Temp"]
    )
    core_labs: List[str] = field(
        default_factory=lambda: ["Lactate", "WBC", "Creatinine", "pH"]
    )

    # Waveform Signal Hierarchy
    tier1_waveforms: List[str] = field(default_factory=lambda: ["II", "ABP", "PLETH"])
    tier2_waveforms: List[str] = field(default_factory=lambda: ["II", "PLETH"])
    tier3_waveforms: List[str] = field(default_factory=lambda: ["II"])

    # PhysioNet Credentialing Guidelines
    required_citi_course: str = "Data or Specimens Only Research"
    required_dua: str = "PhysioNet Restricted Health Data Use Agreement"
    physionet_signup_url: str = "https://physionet.org/register/"

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration settings into a dictionary representation."""
        return {
            "data_dir": self.data_dir,
            "clinical_dir": self.clinical_dir,
            "waveform_dir": self.waveform_dir,
            "processed_dir": self.processed_dir,
            "clinical_subset_size": self.clinical_subset_size,
            "waveform_subset_size": self.waveform_subset_size,
            "observation_window_hours": self.observation_window_hours,
            "prediction_window_hours": self.prediction_window_hours,
            "primary_target_column": self.primary_target_column,
            "secondary_target_column": self.secondary_target_column,
            "core_vitals": self.core_vitals,
            "core_labs": self.core_labs,
            "tier1_waveforms": self.tier1_waveforms,
            "tier2_waveforms": self.tier2_waveforms,
            "tier3_waveforms": self.tier3_waveforms,
            "required_citi_course": self.required_citi_course,
            "required_dua": self.required_dua,
        }
