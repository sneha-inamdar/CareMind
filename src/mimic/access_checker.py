"""
MIMIC Access Checker and Environment Verification Tool.

Checks local directory readiness, environment credentialing status,
and provides structured guidance for PhysioNet access requirements.
"""

import os
from typing import Dict, Any
from src.mimic.config import MIMICConfig


class MIMICAccessChecker:
    """Validator for checking PhysioNet access setup, local storage, and credential readiness."""

    def __init__(self, config: MIMICConfig = None):
        self.config = config or MIMICConfig()

    def verify_environment(self) -> Dict[str, Any]:
        """
        Verify the local workspace directories and environment variables for MIMIC access.

        Returns:
            Dictionary containing verification status, directory existence, and checklist items.
        """
        data_dir_exists = os.path.exists(self.config.data_dir)
        clinical_dir_exists = os.path.exists(self.config.clinical_dir)
        waveform_dir_exists = os.path.exists(self.config.waveform_dir)
        processed_dir_exists = os.path.exists(self.config.processed_dir)

        # Check for PhysioNet credentials environment variables
        physionet_user = os.getenv("PHYSIONET_USERNAME", "")
        physionet_pass = os.getenv("PHYSIONET_PASSWORD", "")
        physionet_key = os.getenv("PHYSIONET_API_KEY", "")

        has_env_credentials = bool(physionet_key or (physionet_user and physionet_pass))

        checklist = {
            "citi_training_completed": False,  # User manual action item
            "physionet_account_linked": False, # User manual action item
            "dua_signed": False,               # User manual action item
            "env_credentials_detected": has_env_credentials,
            "data_directories_prepared": (
                data_dir_exists and clinical_dir_exists and processed_dir_exists
            )
        }

        guidance_steps = [
            f"1. Complete CITI Course: '{self.config.required_citi_course}'.",
            f"2. Link CITI Completion Record to your PhysioNet Account at {self.config.physionet_signup_url}.",
            f"3. Sign the '{self.config.required_dua}' on PhysioNet for MIMIC-IV.",
            "4. Await credentialing approval from PhysioNet (1-3 business days).",
            "5. After approval, export credentials to environment variables: PHYSIONET_USERNAME & PHYSIONET_PASSWORD.",
            "6. Execute `python -m src.mimic.prepare` to run cohort extraction."
        ]

        status = {
            "ready_for_download": (has_env_credentials and checklist["data_directories_prepared"]),
            "data_directories": {
                "root": self.config.data_dir,
                "clinical": self.config.clinical_dir,
                "waveform": self.config.waveform_dir,
                "processed": self.config.processed_dir,
                "status": "prepared" if checklist["data_directories_prepared"] else "missing"
            },
            "environment_credentials": {
                "detected": has_env_credentials,
                "username_set": bool(physionet_user),
                "api_key_set": bool(physionet_key)
            },
            "checklist": checklist,
            "user_action_guidance": guidance_steps
        }

        return status

    def initialize_directories(self) -> Dict[str, str]:
        """
        Create empty directory structure for local MIMIC data without downloading files.

        Returns:
            Dictionary of created directory paths.
        """
        paths = [
            self.config.data_dir,
            self.config.clinical_dir,
            self.config.waveform_dir,
            self.config.processed_dir
        ]

        created = {}
        for p in paths:
            os.makedirs(p, exist_ok=True)
            created[p] = "initialized"

        return created
