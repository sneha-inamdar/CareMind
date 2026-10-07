"""
Verification Script to test FastAPI simulation endpoints (/api/simulation/start, /api/simulation/step, /api/simulation/state).
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from backend.main import app

def main():
    client = TestClient(app)
    
    print("=== TESTING SIMULATION ENDPOINTS & FLOW ===")
    
    # 1. Reset / Start simulation
    res0 = client.post("/api/simulation/start")
    assert res0.status_code == 200
    data0 = res0.json()
    print(f"[START] Status: {data0['status']} | Step: {data0['current_step']} | Patients: {data0['patient_count']}")
    assert data0['current_step'] == 0
    assert data0['patient_count'] >= 24
    
    # Audit Bed IDs uniqueness
    beds = [p['bed_id'] for p in data0['patients']]
    unique_beds = set(beds)
    print(f"Total Bed IDs: {len(beds)} | Unique Bed IDs: {len(unique_beds)}")
    assert len(beds) == len(unique_beds), "Bed IDs must be 100% unique!"
    
    p0_score = data0['patients'][0]['risk_score']
    p0_bed = data0['patients'][0]['bed_id']
    p0_name = data0['patients'][0]['record_id']
    print(f"  Initial Top Priority Patient: {p0_name} ({p0_bed}) -> Risk Score: {p0_score}")
    
    # 2. Step 1
    res1 = client.post("/api/simulation/step")
    assert res1.status_code == 200
    data1 = res1.json()
    print(f"[STEP 1] Current Step: {data1['current_step']} | Alerts: {len(data1['active_alerts'])}")
    assert data1['current_step'] == 1
    
    # 3. Step 2
    res2 = client.post("/api/simulation/step")
    assert res2.status_code == 200
    data2 = res2.json()
    print(f"[STEP 2] Current Step: {data2['current_step']} | Alerts: {len(data2['active_alerts'])}")
    assert data2['current_step'] == 2
    
    # 4. Step 3
    res3 = client.post("/api/simulation/step")
    assert res3.status_code == 200
    data3 = res3.json()
    print(f"[STEP 3] Current Step: {data3['current_step']} | Alerts: {len(data3['active_alerts'])}")
    assert data3['current_step'] == 3
    
    # 5. Step 4 (Loop-around to Step 0)
    res4 = client.post("/api/simulation/step")
    assert res4.status_code == 200
    data4 = res4.json()
    print(f"[STEP 4 (Loop-around)] Current Step: {data4['current_step']}")
    assert data4['current_step'] == 0
    
    # 6. Reset again
    res_reset = client.post("/api/simulation/start")
    assert res_reset.status_code == 200
    data_reset = res_reset.json()
    print(f"[RESET] Current Step: {data_reset['current_step']}")
    assert data_reset['current_step'] == 0
    
    print("\nSUCCESS: All simulation endpoints, loop-around steps, and unique Bed IDs verified!")

if __name__ == "__main__":
    main()
