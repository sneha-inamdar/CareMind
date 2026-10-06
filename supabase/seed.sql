-- CareMind ICU Clinical Decision Support System - Supabase Seed Data
-- Application-level operational data for the 3 REAL MIMIC-IV demo patient records.

-- 1. Insert Patient Identity Records
INSERT INTO patients (subject_id, gender, anchor_age) VALUES
(10014354, 'F', 68),
(10020306, 'M', 74),
(10126957, 'M', 59)
ON CONFLICT (subject_id) DO NOTHING;

-- 2. Insert ICU Stays Records
INSERT INTO icu_stays (stay_id, subject_id, bed_id, careunit, intime, status) VALUES
(39880770, 10014354, 'Bed ICU-01', 'Medical Intensive Care Unit (MICU)', '2148-08-16 08:00:00+00', 'ACTIVE'),
(38418938, 10020306, 'Bed ICU-02', 'Medical Intensive Care Unit (MICU)', '2135-01-21 16:00:00+00', 'ACTIVE'),
(39149479, 10126957, 'Bed ICU-03', 'Coronary Care Unit (CCU)', '2155-10-07 18:00:00+00', 'ACTIVE')
ON CONFLICT (stay_id) DO NOTHING;

-- 3. Insert Waveform Metadata Records
INSERT INTO waveform_records (record_id, subject_id, stay_id, fs, duration_hrs, tier, available_modalities) VALUES
('81739927', 10014354, 39880770, 62.50, 24.00, 'Tier 2 (ECG+PPG)', ARRAY['ECG', 'PPG', 'Resp', 'Clinical Vitals']),
('83404654', 10020306, 38418938, 62.50, 24.00, 'Tier 2 (ECG+PPG)', ARRAY['ECG', 'PPG', 'Resp', 'Clinical Vitals']),
('82924339', 10126957, 39149479, 125.00, 24.00, 'Tier 1 (ECG+ABP+PPG)', ARRAY['ECG', 'PPG', 'ABP', 'Resp', 'Clinical Vitals'])
ON CONFLICT (record_id) DO NOTHING;
