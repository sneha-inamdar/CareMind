"""
CareMind PhysioNet 2019 Data Acquisition & ETL Pipeline Runner.

Usage:
  python run_physionet2019_etl.py [--max-patients 500] [--seed 42]
"""

import sys
import argparse
from src.physionet2019.pipeline import run_physionet2019_pipeline


def main():
    parser = argparse.ArgumentParser(description="CareMind PhysioNet 2019 Data Acquisition & ETL Pipeline")
    parser.add_argument("--raw-dir", type=str, default="data/physionet2019/raw", help="Directory for raw .psv dataset")
    parser.add_argument("--processed-dir", type=str, default="data/physionet2019/processed", help="Output directory for processed parquet files")
    parser.add_argument("--max-patients", type=int, default=500, help="Max patients to process (set 0 or None for all)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for patient-level splitting")
    parser.add_argument("--no-impute", action="store_true", help="Disable LOCF and median imputation")

    args = parser.parse_args()
    max_p = args.max_patients if args.max_patients > 0 else None

    run_physionet2019_pipeline(
        raw_dir=args.raw_dir,
        processed_dir=args.processed_dir,
        max_patients=max_p,
        impute_vitals=not args.no_impute,
        seed=args.seed
    )


if __name__ == "__main__":
    main()
