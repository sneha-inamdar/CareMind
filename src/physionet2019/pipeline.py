"""
PhysioNet 2019 Reproducible Pipeline Orchestrator.

Executes the leakage-free PhysioNet 2019 ETL pipeline:
  RAW → LOAD → VALIDATE RAW → PATIENT SPLIT → FIT CLEANER ON TRAIN ONLY → TRANSFORM SPLITS → SAVE PARQUET
"""

import os
import json
import time
import datetime
import pandas as pd
from typing import Dict, Any, Optional

from src.physionet2019.downloader import download_physionet2019, DEFAULT_RAW_DIR
from src.physionet2019.loader import PhysioNet2019Loader
from src.physionet2019.validator import PhysioNet2019Validator
from src.physionet2019.cleaner import PhysioNet2019Cleaner
from src.physionet2019.transformer import PhysioNet2019Transformer
from src.physionet2019.splitter import PhysioNet2019Splitter

DEFAULT_PROCESSED_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "physionet2019", "processed")
)


def run_physionet2019_pipeline(
    raw_dir: str = DEFAULT_RAW_DIR,
    processed_dir: str = DEFAULT_PROCESSED_DIR,
    max_patients: Optional[int] = 500,
    download_if_missing: bool = True,
    impute_vitals: bool = True,
    seed: int = 42
) -> Dict[str, Any]:
    """
    Run the leakage-free PhysioNet 2019 ETL pipeline.

    Flow:
      1. Acquisition
      2. Load raw patient DataFrames
      3. Profile raw un-cleaned data
      4. Patient-level Train/Val/Test Split FIRST (Zero patient leakage)
      5. Fit cleaner parameters (cohort medians) ONLY on Train set; clean Val/Test using Train medians
      6. Transform features (missingness flags from raw, backward-looking deltas & rolling stats)
      7. Export Parquet files & comprehensive metadata JSON

    Returns:
        Pipeline execution metadata summary.
    """
    start_time = time.time()
    os.makedirs(processed_dir, exist_ok=True)

    print("=" * 70)
    print("CAREMIND PHYSIONET 2019 LEAKAGE-FREE ETL PIPELINE")
    print("=" * 70)

    # 1. ACQUISITION
    print("\n[STAGE 1/7] DATA ACQUISITION")
    if download_if_missing:
        download_physionet2019(raw_dir=raw_dir, max_patients_per_set=max_patients or 500)

    # 2. LOAD
    print("\n[STAGE 2/7] DATASET LOADER")
    loader = PhysioNet2019Loader(raw_dir=raw_dir)
    raw_df = loader.load_all_patients(max_patients=max_patients)
    print(f"Loaded {len(raw_df['patient_id'].unique())} patient files ({len(raw_df)} total hourly rows).")

    # 3. VALIDATE / PROFILE (RAW UN-CLEANED DATA)
    print("\n[STAGE 3/7] DATA VALIDATION & PROFILING (RAW UN-CLEANED DATA)")
    validator = PhysioNet2019Validator()
    raw_profile = validator.profile_dataset(raw_df)
    print(f"Raw Profiling Completed: {raw_profile['num_patient_files']} patients, "
          f"Sepsis Patients: {raw_profile['label_stats'].get('total_positive_patients')}.")

    # 4. PATIENT-LEVEL SPLITTING (SPLIT FIRST ON RAW DATA)
    print("\n[STAGE 4/7] PATIENT-LEVEL SPLITTING (RAW DATA FIRST)")
    splitter = PhysioNet2019Splitter(seed=seed)
    train_raw_df, val_raw_df, test_raw_df, split_meta = splitter.split_dataframe(raw_df)
    print(f"Split completed: Train={len(train_raw_df['patient_id'].unique())} patients ({len(train_raw_df)} rows), "
          f"Val={len(val_raw_df['patient_id'].unique())} patients ({len(val_raw_df)} rows), "
          f"Test={len(test_raw_df['patient_id'].unique())} patients ({len(test_raw_df)} rows).")

    # 5. ETL CLEANING (FIT ON TRAIN ONLY)
    print("\n[STAGE 5/7] ETL CLEANING (FIT PREPROCESSING PARAMETERS ON TRAIN ONLY)")
    cleaner = PhysioNet2019Cleaner(impute_vitals=impute_vitals)
    train_clean_df = cleaner.clean(train_raw_df, is_training=True)
    fitted_medians = cleaner.cohort_medians_
    print(f"Fitted Train Cohort Medians: {fitted_medians}")

    val_clean_df = cleaner.clean(val_raw_df, is_training=False)
    test_clean_df = cleaner.clean(test_raw_df, is_training=False)
    print("Cleaned Train, Val, and Test DataFrames using Train-only cohort medians.")

    # 6. FEATURE TRANSFORMATION
    print("\n[STAGE 6/7] FEATURE TRANSFORMATION")
    transformer = PhysioNet2019Transformer()
    train_transformed_df = transformer.transform(raw_df=train_raw_df, clean_df=train_clean_df)
    val_transformed_df = transformer.transform(raw_df=val_raw_df, clean_df=val_clean_df)
    test_transformed_df = transformer.transform(raw_df=test_raw_df, clean_df=test_clean_df)

    # 7. SAVE PROCESSED PARQUET & METADATA
    print("\n[STAGE 7/7] OUTPUT SAVING & METADATA GENERATION")
    train_path = os.path.join(processed_dir, "train.parquet")
    val_path = os.path.join(processed_dir, "val.parquet")
    test_path = os.path.join(processed_dir, "test.parquet")

    train_transformed_df.to_parquet(train_path, index=False)
    val_transformed_df.to_parquet(val_path, index=False)
    test_transformed_df.to_parquet(test_path, index=False)

    print(f"Saved: {train_path} ({len(train_transformed_df)} rows)")
    print(f"Saved: {val_path} ({len(val_transformed_df)} rows)")
    print(f"Saved: {test_path} ({len(test_transformed_df)} rows)")

    # Validate processed data profiles
    full_transformed_df = pd.concat([train_transformed_df, val_transformed_df, test_transformed_df], ignore_index=True)
    cleaned_profile = validator.profile_dataset(full_transformed_df)

    elapsed_sec = round(time.time() - start_time, 2)

    metadata = {
        "pipeline_name": "CareMind PhysioNet 2019 ETL Pipeline",
        "pipeline_version": "1.1.0",
        "leakage_free_architecture": "Train-Only Fitted Preprocessing (Patient Split First)",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "execution_time_seconds": elapsed_sec,
        "parameters": {
            "max_patients_requested": max_patients,
            "impute_vitals": impute_vitals,
            "random_seed": seed,
            "train_val_test_ratio": "70/15/15"
        },
        "fitted_train_cohort_medians": fitted_medians,
        "patient_counts": {
            "total_processed_patients": int(split_meta["total_patients"]),
            "train_patients": int(split_meta["train_patients"]),
            "val_patients": int(split_meta["val_patients"]),
            "test_patients": int(split_meta["test_patients"])
        },
        "row_counts": {
            "total_rows": int(len(full_transformed_df)),
            "train_rows": int(len(train_transformed_df)),
            "val_rows": int(len(val_transformed_df)),
            "test_rows": int(len(test_transformed_df))
        },
        "sepsis_prevalence": {
            "train_sepsis_patients": int(split_meta["train_sepsis_patients"]),
            "val_sepsis_patients": int(split_meta["val_sepsis_patients"]),
            "test_sepsis_patients": int(split_meta["test_sepsis_patients"]),
            "overall_sepsis_patient_percentage": raw_profile["label_stats"].get("percentage_positive_patients")
        },
        "columns": list(full_transformed_df.columns),
        "raw_missingness": raw_profile["missingness"],
        "processed_missingness": cleaned_profile["missingness"],
        "raw_physiological_ranges": raw_profile["physiological_value_ranges"],
        "cleaned_physiological_ranges": cleaned_profile["physiological_value_ranges"],
        "output_files": {
            "train": train_path,
            "val": val_path,
            "test": test_path,
            "metadata": os.path.join(processed_dir, "dataset_metadata.json")
        }
    }

    meta_path = os.path.join(processed_dir, "dataset_metadata.json")
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"Saved Metadata: {meta_path}")
    print("=" * 70)
    print(f"LEAKAGE-FREE ETL PIPELINE COMPLETED SUCCESSFULLY IN {elapsed_sec} SECONDS")
    print("=" * 70)

    return metadata


if __name__ == "__main__":
    run_physionet2019_pipeline()
