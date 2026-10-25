from src.mimic.multimodal_prototype import CareMindMultimodalPrototype
import numpy as np

prototype = CareMindMultimodalPrototype()
v0 = {'HR': 91.0, 'SpO2': 98.0, 'Resp': 24.0, 'SysBP': 84.0, 'DiaBP': 48.0, 'MAP': 56.0, 'Temp': 37.1}
v1 = {'HR': 93.0, 'SpO2': 97.0, 'Resp': 21.0, 'SysBP': 95.0, 'DiaBP': 59.0, 'MAP': 67.0, 'Temp': 37.1}
v2 = {'HR': 94.0, 'SpO2': 97.0, 'Resp': 23.0, 'SysBP': 88.0, 'DiaBP': 56.0, 'MAP': 64.0, 'Temp': 37.1}
v3 = {'HR': 105.0, 'SpO2': 94.0, 'Resp': 21.0, 'SysBP': 88.0, 'DiaBP': 56.0, 'MAP': 64.0, 'Temp': 37.1}

prev = None
for i, (ts, v) in enumerate([('2180-07-23 14:00:00', v0), ('2180-07-23 14:30:00', v1), ('2180-07-23 15:00:00', v2), ('2180-07-23 16:00:00', v3)]):
    res = prototype.analyze_multimodal_window(
        record_id='84992147',
        subject_id=10000032,
        window_index=i,
        vitals_dict=v,
        ecg_signal=np.array([]),
        ppg_signal=np.array([]),
        abp_signal=np.array([]),
        timestamp_str=ts,
        previous_risk_score=prev
    )
    preds = prototype.get_individual_predictions_for_window(res)
    print(f"Window {i} ({ts}): risk={res['risk_score']}, clin_pred={preds['clinical']['prediction']}, clin_score={preds['clinical']['score']}, ecg_avail={preds['ecg']['is_available']}")
    prev = res['risk_score']
