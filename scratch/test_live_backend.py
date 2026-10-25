import urllib.request
import json

# 1. Reset simulation
req = urllib.request.Request('http://localhost:8000/api/simulation/reset', method='POST')
with urllib.request.urlopen(req) as resp:
    res = json.loads(resp.read().decode())
print("=== AFTER RESET ===")
print("current_step:", res.get("current_step"))
for p in res.get("patients", []):
    if p["record_id"] in ["83404654", "81739927", "83411188"]:
        print(f"  {p['record_id']} ({p['bed_id']}): HR={p['vitals'].get('HR')}, BP={p['vitals'].get('SysBP')}/{p['vitals'].get('DiaBP')}, risk={p['risk_score']}")

# 2. Step 1
req = urllib.request.Request('http://localhost:8000/api/simulation/step', method='POST')
with urllib.request.urlopen(req) as resp:
    res = json.loads(resp.read().decode())
print("\n=== AFTER STEP 1 ===")
print("current_step:", res.get("current_step"))
for p in res.get("patients", []):
    if p["record_id"] in ["83404654", "81739927", "83411188"]:
        print(f"  {p['record_id']} ({p['bed_id']}): HR={p['vitals'].get('HR')}, BP={p['vitals'].get('SysBP')}/{p['vitals'].get('DiaBP')}, risk={p['risk_score']}")

# 3. Test /api/multimodal/analyze for 83404654 for window 0 and window 1
print("\n=== /api/multimodal/analyze FOR 83404654 ===")
for w_idx in [0, 1, 2, 3]:
    payload = json.dumps({"record_id": "83404654", "window_index": w_idx}).encode()
    req = urllib.request.Request('http://localhost:8000/api/multimodal/analyze', data=payload, headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(req) as resp:
        an = json.loads(resp.read().decode())
    cf = an.get("clinical_features", {})
    clin_p = an.get("individual_predictions", {}).get("clinical", {})
    ecg_p = an.get("individual_predictions", {}).get("ecg", {})
    print(f"Window {w_idx}: HR={cf.get('HR')}, BP={cf.get('SysBP')}/{cf.get('DiaBP')}, MAP={cf.get('MAP')}, risk={an.get('risk_score')}")
    print(f"   Clin Pred: {clin_p.get('prediction')} (score: {clin_p.get('score')})")
    print(f"   ECG Pred: {ecg_p.get('prediction')} (score: {ecg_p.get('score')})")
