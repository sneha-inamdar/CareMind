-- CareMind Supabase Migration 002: Least-Privilege Backend Permissions
-- Restricts write permissions exclusively to the server-side service_role used by FastAPI backend.

-- 1. Ensure Unique Constraints for Idempotent Cohort Synchronization
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'unique_vital_obs_window') THEN
        ALTER TABLE vital_observations ADD CONSTRAINT unique_vital_obs_window UNIQUE (window_id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'unique_risk_assessment_window') THEN
        ALTER TABLE risk_assessments ADD CONSTRAINT unique_risk_assessment_window UNIQUE (window_id);
    END IF;
END $$;

-- 2. Schema Usage Grant for Backend Server-Side Role
GRANT USAGE ON SCHEMA public TO service_role;

-- 3. Full Operational Table Privileges (SELECT, INSERT, UPDATE, DELETE) STRICTLY to service_role
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE patients TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE icu_stays TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE waveform_records TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE observation_windows TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE vital_observations TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE risk_assessments TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE physiological_alerts TO service_role;

-- 4. Sequence Privileges for ID Generators
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO service_role;

-- 5. Read-Only (SELECT) Privileges for Client Roles (anon & authenticated)
GRANT USAGE ON SCHEMA public TO anon, authenticated;
GRANT SELECT ON TABLE patients TO anon, authenticated;
GRANT SELECT ON TABLE icu_stays TO anon, authenticated;
GRANT SELECT ON TABLE waveform_records TO anon, authenticated;
GRANT SELECT ON TABLE observation_windows TO anon, authenticated;
GRANT SELECT ON TABLE vital_observations TO anon, authenticated;
GRANT SELECT ON TABLE risk_assessments TO anon, authenticated;
GRANT SELECT ON TABLE physiological_alerts TO anon, authenticated;
