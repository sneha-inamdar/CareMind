import os
import json
import requests
from src.db.config import DatabaseConfig
from src.db.repository import get_repository, LocalJSONRepository, SupabaseRepository
from src.mimic.simulation import CareMindSimulationEngine

print("=== 1. Checking Data Config ===")
db_config = DatabaseConfig()
print(f"Supabase Configured: {db_config.is_supabase_configured}")
print(f"Supabase URL: {db_config.supabase_url}")

print("\n=== 2. Checking get_repository() Type ===")
repo = get_repository()
print(f"Active Repository Class: {repo.__class__.__name__}")

print("\n=== 3. Repository Overview Output (Window 0) ===")
overview = repo.get_patients_overview(window_index=0)
for p in overview:
    print(f"  Bed {p.get('bed_id')} (Record {p.get('record_id')}): Risk = {p.get('risk_score')}")

print("\n=== 4. CareMindSimulationEngine Initial State ===")
sim = CareMindSimulationEngine()
sim.reset()
sim_state = sim.get_simulation_state()
for p in sim_state.get("patients", []):
    print(f"  Bed {p.get('bed_id')} (Subject {p.get('subject_id')}): Risk = {p.get('risk_score')}")

print("\n=== 5. Local JSON File Direct Values ===")
for rec_id in ["83404654", "82924339", "81739927"]:
    path = os.path.join("data", "demo_waveforms", f"{rec_id}.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            d = json.load(f)
        w0 = d.get("windows", [])[0]
        print(f"  Local JSON {rec_id} Window 0: Risk = {w0.get('risk_score')}")

print("\n=== 6. Live Running FastAPI Server Responses (http://localhost:8000) ===")
try:
    res_state = requests.get("http://localhost:8000/api/simulation/state").json()
    print("  /api/simulation/state patients:")
    for p in res_state.get("patients", []):
        print(f"    Bed {p.get('bed_id')} (Subject {p.get('subject_id')}): Risk = {p.get('risk_score')}")
except Exception as e:
    print(f"  Error querying FastAPI server: {e}")
