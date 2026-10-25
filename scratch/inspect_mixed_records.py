import json

for rec_id in ['83404654', '81739927', '83411188', '84992147', '82924339']:
    with open(f'data/demo_waveforms/{rec_id}.json') as f:
        d = json.load(f)
    print(f"=== Record {rec_id} ({d.get('bed_id')}) ===")
    for i, w in enumerate(d.get('windows', [])):
        cf = w.get('clinical_features', {})
        ecg_len = len(w.get('waveform_samples', {}).get('ecg', []))
        ppg_len = len(w.get('waveform_samples', {}).get('ppg', []))
        abp_len = len(w.get('waveform_samples', {}).get('abp', []))
        print(f"  Win {i}: HR={cf.get('HR')}, SpO2={cf.get('SpO2')}, Resp={cf.get('Resp')}, SysBP={cf.get('SysBP')}, DiaBP={cf.get('DiaBP')}, MAP={cf.get('MAP')} | ecg_len={ecg_len}, ppg_len={ppg_len}, abp_len={abp_len}, risk={w.get('risk_score')}")
