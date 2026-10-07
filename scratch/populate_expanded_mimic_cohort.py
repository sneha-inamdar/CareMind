"""
Script to populate an expanded cohort of 15 genuine MIMIC-IV waveform records
from PhysioNet (mimic4wdb/0.1.0) into CareMind's cache repository.
"""

import os
import sys
import pandas as pd
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.mimic.cohort_ingestion import MIMICCohortIngestionEngine

# Load selected 15 verified records from CSV
selected_df = pd.read_csv("scratch/selected_15_mimic_records.csv")

def main():
    print("=== POPULATING EXPANDED 15-PATIENT MIMIC-IV COHORT ===")
    engine = MIMICCohortIngestionEngine()
    
    for _, row in selected_df.iterrows():
        rec_id = str(row["record_name"])
        subj_id = int(row["subject_id"])
        pn_dir = str(row["rel_pn_dir"])
        first_seg_stem = str(row["first_seg"]).rsplit("_", 1)[0]
        
        # Build 4 sequential segment names (_0000, _0001, _0002, _0003)
        segment_names = [f"{first_seg_stem}_{i:04d}" for i in range(4)]
        
        engine.process_and_cache_record(
            record_id=rec_id,
            subject_id=subj_id,
            pn_dir=pn_dir,
            segment_names=segment_names,
            base_timestamp_str="2150-01-01 08:00:00",
            vitals_dict=None, # Will use subject-specific or standard baseline profile
            bed_id=f"Bed ICU-{(subj_id % 20) + 1:02d}"
        )

    index_meta = engine.update_records_index()
    print(f"\nSUCCESS: Ingested {len(index_meta)} genuine MIMIC-IV records into CareMind cache.")

if __name__ == "__main__":
    main()
