-- CareMind ICU Clinical Decision Support System - Supabase Migration 001
-- PostgreSQL DDL for operational application data (Patients, ICU Stays, Vitals, Waveform Metadata, Risk Assessments, Alerts)

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Patients Table
CREATE TABLE IF NOT EXISTS patients (
    subject_id INTEGER PRIMARY KEY,
    gender VARCHAR(10) NOT NULL DEFAULT 'M',
    anchor_age INTEGER NOT NULL DEFAULT 65,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. ICU Stays Table
CREATE TABLE IF NOT EXISTS icu_stays (
    stay_id INTEGER PRIMARY KEY,
    subject_id INTEGER NOT NULL REFERENCES patients(subject_id) ON DELETE CASCADE,
    bed_id VARCHAR(50) NOT NULL,
    careunit VARCHAR(100) DEFAULT 'Medical Intensive Care Unit (MICU)',
    intime TIMESTAMPTZ NOT NULL,
    outtime TIMESTAMPTZ,
    status VARCHAR(50) DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Waveform Records Metadata Table
CREATE TABLE IF NOT EXISTS waveform_records (
    record_id VARCHAR(50) PRIMARY KEY,
    subject_id INTEGER NOT NULL REFERENCES patients(subject_id) ON DELETE CASCADE,
    stay_id INTEGER NOT NULL REFERENCES icu_stays(stay_id) ON DELETE CASCADE,
    fs NUMERIC(6, 2) NOT NULL DEFAULT 62.50,
    duration_hrs NUMERIC(6, 2) NOT NULL DEFAULT 24.00,
    tier VARCHAR(50) NOT NULL DEFAULT 'Tier 2 (ECG+PPG)',
    available_modalities TEXT[] NOT NULL DEFAULT ARRAY['ECG', 'PPG', 'Resp', 'Clinical Vitals'],
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Observation Windows Table
CREATE TABLE IF NOT EXISTS observation_windows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    record_id VARCHAR(50) NOT NULL REFERENCES waveform_records(record_id) ON DELETE CASCADE,
    window_index INTEGER NOT NULL CHECK (window_index >= 0),
    timestamp_label VARCHAR(100) NOT NULL,
    obs_timestamp TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_record_window UNIQUE (record_id, window_index)
);

-- 5. Vital Observations Table
CREATE TABLE IF NOT EXISTS vital_observations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    window_id UUID NOT NULL REFERENCES observation_windows(id) ON DELETE CASCADE,
    stay_id INTEGER NOT NULL REFERENCES icu_stays(stay_id) ON DELETE CASCADE,
    hr NUMERIC(5, 2) NOT NULL CHECK (hr > 0),
    spo2 NUMERIC(5, 2) NOT NULL CHECK (spo2 >= 0 AND spo2 <= 100),
    resp NUMERIC(5, 2) NOT NULL CHECK (resp >= 0),
    sys_bp NUMERIC(5, 2) NOT NULL,
    dia_bp NUMERIC(5, 2) NOT NULL,
    map_bp NUMERIC(5, 2) NOT NULL,
    temp NUMERIC(4, 2) DEFAULT 37.00,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. CareMind Risk Assessments Table
CREATE TABLE IF NOT EXISTS risk_assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    window_id UUID NOT NULL REFERENCES observation_windows(id) ON DELETE CASCADE,
    stay_id INTEGER NOT NULL REFERENCES icu_stays(stay_id) ON DELETE CASCADE,
    record_id VARCHAR(50) NOT NULL REFERENCES waveform_records(record_id) ON DELETE CASCADE,
    risk_score NUMERIC(5, 2) NOT NULL CHECK (risk_score >= 0.0 AND risk_score <= 100.0),
    risk_category VARCHAR(20) NOT NULL CHECK (risk_category IN ('LOW', 'MEDIUM', 'HIGH')),
    clinical_score NUMERIC(5, 2) NOT NULL DEFAULT 0.00,
    waveform_score NUMERIC(5, 2) NOT NULL DEFAULT 0.00,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7. Physiological Alerts Table
CREATE TABLE IF NOT EXISTS physiological_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id UUID NOT NULL REFERENCES risk_assessments(id) ON DELETE CASCADE,
    stay_id INTEGER NOT NULL REFERENCES icu_stays(stay_id) ON DELETE CASCADE,
    factor_name VARCHAR(100) NOT NULL,
    impact_level VARCHAR(20) NOT NULL CHECK (impact_level IN ('HIGH', 'MEDIUM', 'LOW')),
    description TEXT NOT NULL,
    contribution_score NUMERIC(5, 2) DEFAULT 0.00,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- INDEXES FOR FAST ICU DASHBOARD PRIORITIZATION
CREATE INDEX IF NOT EXISTS idx_icu_stays_subject ON icu_stays(subject_id);
CREATE INDEX IF NOT EXISTS idx_waveform_records_stay ON waveform_records(stay_id);
CREATE INDEX IF NOT EXISTS idx_obs_windows_rec_win ON observation_windows(record_id, window_index);
CREATE INDEX IF NOT EXISTS idx_vitals_window ON vital_observations(window_id);
CREATE INDEX IF NOT EXISTS idx_risk_assessments_prioritization ON risk_assessments(window_id, risk_score DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_assessment ON physiological_alerts(assessment_id);
