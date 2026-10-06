# CareMind Supabase Integration & Database Architecture

## 1. Overview & Architecture

CareMind utilizes Supabase (PostgreSQL) as its operational application database for patient management, ICU bed tracking, vital observations, CareMind risk assessment history, and physiological alerts.

```
Raw MIMIC / WFDB Signals (Disk / Local Cache)
                  │
                  ↓
           FastAPI Backend ──(Independence Firewall)──> CareMind ML Risk Engine
                  │                                               │
                  ↓                                               ↓
       Supabase PostgreSQL DB <───────────────────── Operational Risk & Vitals Data
                  │
                  ├──> React Web Dashboard (Clinician UI)
                  └──> Android Application (Future Phase)
```

> **IMPORTANT RULE:** Raw MIMIC datasets (waveform `.dat` files and full raw CSVs) are kept outside Supabase to protect patient privacy and optimize database performance. Supabase stores strictly operational application metadata and derived physiological assessments.

---

## 2. Relational Schema & Tables

- `patients`: `subject_id` (PK), `gender`, `anchor_age`, `created_at`
- `icu_stays`: `stay_id` (PK), `subject_id` (FK), `bed_id`, `careunit`, `intime`, `outtime`, `status`
- `waveform_records`: `record_id` (PK), `subject_id` (FK), `stay_id` (FK), `fs`, `duration_hrs`, `tier`, `available_modalities`
- `observation_windows`: `id` (PK), `record_id` (FK), `window_index`, `timestamp_label`, `obs_timestamp`
- `vital_observations`: `id` (PK), `window_id` (FK), `stay_id` (FK), `hr`, `spo2`, `resp`, `sys_bp`, `dia_bp`, `map_bp`, `temp`
- `risk_assessments`: `id` (PK), `window_id` (FK), `stay_id` (FK), `record_id` (FK), `risk_score`, `risk_category`, `clinical_score`, `waveform_score`
- `physiological_alerts`: `id` (PK), `assessment_id` (FK), `stay_id` (FK), `factor_name`, `impact_level`, `description`, `contribution_score`

---

## 3. Security & Row Level Security (RLS) Approach

For production deployments, Row Level Security (RLS) will be enabled on all tables:

```sql
-- Enable RLS on operational tables
ALTER TABLE patients ENABLE ROW LEVEL SECURITY;
ALTER TABLE icu_stays ENABLE ROW LEVEL SECURITY;
ALTER TABLE vital_observations ENABLE ROW LEVEL SECURITY;
ALTER TABLE risk_assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE physiological_alerts ENABLE ROW LEVEL SECURITY;

-- Read policy for authenticated healthcare clinicians & service role
CREATE POLICY "Allow read access for authenticated clinicians" ON patients
    FOR SELECT TO authenticated USING (true);

CREATE POLICY "Allow read access for authenticated clinicians" ON icu_stays
    FOR SELECT TO authenticated USING (true);

CREATE POLICY "Allow read access for authenticated clinicians" ON risk_assessments
    FOR SELECT TO authenticated USING (true);
```

During development/demonstration mode, read access is exposed to the FastAPI backend using the Supabase `anon` / `service_role` key configured via environment variables.

---

## 4. How to Apply Migrations & Seed Data

1. **Option A: Via Supabase Web Dashboard SQL Editor**
   - Copy contents of `supabase/migrations/001_initial_schema.sql` and run in the SQL Editor.
   - Copy contents of `supabase/seed.sql` and run in the SQL Editor.

2. **Option B: Via Supabase CLI**
   ```bash
   supabase db push
   ```

---

## 5. Environment Configuration

Copy `.env.example` to `.env` and fill in your Supabase project credentials:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```
