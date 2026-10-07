"""
Audit and assign 100% unique Bed IDs (Bed ICU-01 to Bed ICU-24) to all 24 genuine MIMIC waveform records.
"""
import os
import json

data_dir = "data/demo_waveforms"
index_path = os.path.join(data_dir, "records_index.json")

if os.path.exists(index_path):
    with open(index_path, "r") as f:
        records = json.load(f)
        
    print(f"Auditing {len(records)} records in records_index.json...")
    
    # Sort records by subject_id for deterministic assignment
    records.sort(key=lambda x: x["subject_id"])
    
    for idx, r in enumerate(records):
        unique_bed = f"Bed ICU-{idx + 1:02d}"
        old_bed = r.get("bed_id")
        r["bed_id"] = unique_bed
        rec_id = r["record_id"]
        
        # Also update the individual JSON file
        rf_path = os.path.join(data_dir, f"{rec_id}.json")
        if os.path.exists(rf_path):
            with open(rf_path, "r") as rf:
                rdata = json.load(rf)
            rdata["bed_id"] = unique_bed
            with open(rf_path, "w") as rf:
                json.dump(rdata, rf, indent=2)
                
        print(f"  Record {rec_id} (Subject #{r['subject_id']}) -> {old_bed} updated to {unique_bed}")

    with open(index_path, "w") as f:
        json.dump(records, f, indent=2)
        
    print("\nSUCCESS: All 24 records updated with unique Bed IDs (Bed ICU-01 through Bed ICU-24).")
