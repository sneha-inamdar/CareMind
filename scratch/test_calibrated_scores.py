import os
import json
import numpy as np
from src.mimic.multimodal_prototype import CareMindMultimodalPrototype

prototype = CareMindMultimodalPrototype()
data_dir = "data/demo_waveforms"

record_ids = ["83404654", "82924339", "81739927"]

for rec_id in record_ids:
    path = os.path.join(data_dir, f"{rec_id}.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            data = json.load(f)
        
        print(f"=== Record {rec_id} (Subject {data.get('subject_id')}) ===")
        for w in data.get("windows", []):
            print(f"  Window {w['window_index']}: Risk={w['risk_score']} | Category={w['risk_category']} | Priority={w['priority_status']} | ClinScore={w.get('clinical_score')} | WaveScore={w.get('waveform_score')}")
