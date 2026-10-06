"""
Unit tests for CareMind Multimodal AI Evaluator, Temporal Risk Tracking, & Patient Prioritization.
"""

import pytest
import numpy as np
from src.mimic.evaluator import CareMindEvaluator
from src.mimic.multimodal_prototype import CareMindMultimodalPrototype


@pytest.fixture
def evaluator():
    return CareMindEvaluator(random_state=42)


@pytest.fixture
def prototype():
    return CareMindMultimodalPrototype()


def test_evaluator_patient_level_split(evaluator):
    """Verify zero-leakage patient-level split (no subject_id overlaps between train and test)."""
    X = np.random.randn(100, 5)
    y = np.random.randint(0, 2, 100)
    groups = np.repeat(np.arange(10, 30), 5)  # 20 unique subjects

    X_tr, X_te, y_tr, y_te, g_tr, g_te = evaluator.patient_level_split(X, y, groups, test_size=0.3)

    train_subjects = set(g_tr)
    test_subjects = set(g_te)

    # Zero leakage check
    overlap = train_subjects.intersection(test_subjects)
    assert len(overlap) == 0, f"Patient leakage detected! Overlapping subjects: {overlap}"
    assert len(train_subjects) > 0
    assert len(test_subjects) > 0


def test_evaluator_metrics_calculation(evaluator):
    """Verify evaluation metric calculations (Precision, Recall, F1, ROC-AUC, PR-AUC)."""
    y_true = np.array([0, 0, 1, 1, 0, 1, 0, 1])
    y_probs = np.array([0.1, 0.2, 0.8, 0.9, 0.3, 0.7, 0.4, 0.85])

    metrics = evaluator.calculate_metrics(y_true, y_probs)

    assert "precision" in metrics
    assert "recall" in metrics
    assert "f1" in metrics
    assert "roc_auc" in metrics
    assert "pr_auc" in metrics
    assert 0.0 <= metrics["precision"] <= 1.0
    assert 0.0 <= metrics["roc_auc"] <= 1.0


def test_unimodal_vs_multimodal_evaluation(evaluator):
    """Verify evaluation comparison between unimodal baselines and multimodal fusion."""
    res = evaluator.evaluate_unimodal_vs_multimodal(n_samples=100)

    assert "cohort_summary" in res
    assert "unimodal_clinical_metrics" in res
    assert "unimodal_waveform_metrics" in res
    assert "multimodal_fusion_metrics" in res
    assert res["cohort_summary"]["leakage_violations"] == 0


def test_adaptive_modality_fusion_missing_clinical(prototype):
    """Verify missing clinical vitals do not force default clinical score dilution in fusion."""
    vitals_missing = {"HR": None, "SpO2": None, "Resp": None, "SysBP": None, "DiaBP": None, "MAP": None, "Temp": None}
    ecg_sig = np.array([0.1, 0.8, -0.4, 0.3])
    
    analysis = prototype.analyze_multimodal_window(
        record_id="test_missing_mod",
        subject_id=999,
        window_index=0,
        vitals_dict=vitals_missing,
        ecg_signal=ecg_sig
    )

    assert "Clinical Vitals" not in analysis["available_modalities"]
    assert "ECG" in analysis["available_modalities"]
    assert 0.0 <= analysis["risk_score"] <= 100.0


def test_temporal_risk_trend_tracking(prototype):
    """Verify temporal trend calculation (STABLE, ESCALATING, IMPROVING)."""
    vitals = {"HR": 85.0, "SpO2": 97.0}
    
    # Window 0
    w0 = prototype.analyze_multimodal_window(
        record_id="rec_temp", subject_id=101, window_index=0, vitals_dict=vitals, previous_risk_score=None
    )
    assert w0["risk_trend_status"] == "STABLE"
    assert w0["risk_trend_delta"] == 0.0

    # Window 1 (Escalating risk: previous=20.0, current > 25.0)
    w1 = prototype.analyze_multimodal_window(
        record_id="rec_temp", subject_id=101, window_index=1, vitals_dict=vitals, previous_risk_score=20.0
    )
    assert "risk_trend_delta" in w1
    assert "risk_trend_status" in w1

    # Window 2 (Improving risk: previous=80.0)
    w2 = prototype.analyze_multimodal_window(
        record_id="rec_temp", subject_id=101, window_index=2, vitals_dict=vitals, previous_risk_score=80.0
    )
    assert w2["risk_trend_status"] == "IMPROVING"


def test_patient_prioritization_status(prototype):
    """Verify priority_status allocation (CRITICAL_PRIORITY, HIGH_PRIORITY, ROUTINE_MONITORING)."""
    # Low risk -> ROUTINE_MONITORING
    v_low = {"HR": 72.0, "SpO2": 98.0, "MAP": 90.0}
    w_low = prototype.analyze_multimodal_window(
        record_id="rec_low", subject_id=102, window_index=0, vitals_dict=v_low
    )
    assert w_low["priority_status"] in ["ROUTINE_MONITORING", "HIGH_PRIORITY", "CRITICAL_PRIORITY"]

    # High risk -> CRITICAL_PRIORITY
    v_high = {"HR": 130.0, "SpO2": 88.0, "MAP": 55.0}
    w_high = prototype.analyze_multimodal_window(
        record_id="rec_high", subject_id=103, window_index=0, vitals_dict=v_high
    )
    assert w_high["priority_status"] == "CRITICAL_PRIORITY"


def test_research_audit_summary(evaluator):
    """Verify research audit report contains demo limitations and architecture specs."""
    audit = evaluator.generate_research_audit_summary()
    assert audit["status"] == "success"
    assert "demo_cohort_limitations" in audit
    assert len(audit["demo_cohort_limitations"]) >= 3
