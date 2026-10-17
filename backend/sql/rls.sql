-- DB-086: PostgreSQL row-level security. NOT executed by the test-suite (tests use SQLite) - run it on your Postgres and test it there.
-- The API sets `app.user_id` per request (see security.current_user). Connect the API as the non-owner role docbuddy_app so RLS applies.
-- RLS is a SECOND lock behind the application's consent checks, not a replacement for them.
CREATE ROLE docbuddy_app LOGIN PASSWORD 'change-me' NOSUPERUSER NOBYPASSRLS;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO docbuddy_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO docbuddy_app;

CREATE OR REPLACE FUNCTION docbuddy_uid() RETURNS int LANGUAGE sql STABLE AS
$$ SELECT NULLIF(current_setting('app.user_id', true), '')::int $$;

-- may the current user read this elder's data of this type?
CREATE OR REPLACE FUNCTION docbuddy_can_read(elder int, dtype text) RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER AS
$$ SELECT elder = docbuddy_uid() OR EXISTS (
     SELECT 1 FROM consents c WHERE c.elder_id = elder AND c.grantee_id = docbuddy_uid() AND c.data_type = dtype
       AND c.scope IN ('view','write') AND c.revoked_at IS NULL AND (c.expires_at IS NULL OR c.expires_at > now() at time zone 'utc')) $$;

DO $$
DECLARE r record;
BEGIN
  FOR r IN SELECT * FROM (VALUES
      ('checkins','checkin'), ('vitals','vitals'), ('medicines','medicines'), ('dose_log','medicines'), ('appointments','appointments'),
      ('emergency_cards','emergency_card'), ('symptom_notes','symptoms'), ('documents','documents'), ('life_stories','life_story'),
      ('activity_log','activity'), ('cognitive_results','cognitive')) AS t(tbl, dtype)
  LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', r.tbl);
    EXECUTE format('DROP POLICY IF EXISTS docbuddy_read ON %I', r.tbl);
    EXECUTE format('CREATE POLICY docbuddy_read ON %I FOR SELECT USING (docbuddy_can_read(%s, %L))',
                   r.tbl, CASE WHEN r.tbl = 'emergency_cards' THEN 'elder_id' ELSE 'elder_id' END, r.dtype);
    EXECUTE format('DROP POLICY IF EXISTS docbuddy_write ON %I', r.tbl);
    EXECUTE format('CREATE POLICY docbuddy_write ON %I FOR ALL USING (elder_id = docbuddy_uid()) WITH CHECK (elder_id = docbuddy_uid())', r.tbl);
  END LOOP;
END $$;
-- Writes by a consented CHW (scope 'write') and system jobs use a separate privileged role; keep that role's use minimal and audited.
