-- PURPOSE
--   Create a read-only login (reader) and a role (app_readonly) that can SELECT from
--   all your user schemas (public, staging, dw, summary, etc.). This is safe to run
--   multiple times (idempotent) and is designed for local Docker bootstrap.
--
-- CONTEXT
--   - Docker mounts this file into /docker-entrypoint-initdb.d on first boot of the
--     Postgres container and executes it if the data directory is empty.
--   - If you already have a running database and re-run this file manually, it will
--     still work and not duplicate objects.
--
-- WHAT IT DOES
--   1) Ensures an app_readonly role exists with read-only defaults
--   2) Ensures a reader user exists with a known password and read-only default
--   3) Grants the reader membership in app_readonly (so permissions flow through)
--   4) Ensures common schemas exist
--   5) Grants read access (USAGE + SELECT) across ALL non-system schemas
--   6) Sets default privileges so future dbt-created tables are readable
--   7) Denies CREATE in schemas to keep reader from writing
--   8) Grants CONNECT on the database to app_readonly
--

-- Create role if missing; then enforce desired properties always
DO $$  -- Block 1: Ensure the app_readonly role exists and is configured
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_roles WHERE rolname = 'app_readonly'
  ) THEN
    CREATE ROLE app_readonly INHERIT;
  END IF;
  -- Ensure the role inherits and defaults to read-only transactions
  PERFORM 1;
  EXECUTE 'ALTER ROLE app_readonly INHERIT';
  EXECUTE 'ALTER ROLE app_readonly SET default_transaction_read_only = on';
END$$;

-- Block 2: Ensure the reader login exists, has the expected password, and inherits permissions
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_roles WHERE rolname = 'reader'
  ) THEN
    CREATE USER reader WITH LOGIN PASSWORD 'pass';
  END IF;
  -- Always ensure password and read-only default are set
  EXECUTE 'ALTER ROLE reader WITH LOGIN PASSWORD ''pass''';
  EXECUTE 'ALTER ROLE reader SET default_transaction_read_only = on';
  -- Ensure membership (idempotent GRANT)
  EXECUTE 'GRANT app_readonly TO reader';
END$$;

-- Block 3: Ensure schemas exist so grants below don't fail (dbt also manages these)
CREATE SCHEMA IF NOT EXISTS public;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS dw;
CREATE SCHEMA IF NOT EXISTS summary;

-- Block 4: Apply read access and future defaults across ALL non-system schemas
DO $$  -- do is for anonymous code block
DECLARE  -- declare is for variables
  r RECORD;
BEGIN  -- begin is for start of code block
  -- Ensure role can connect to this database
  EXECUTE format('GRANT CONNECT ON DATABASE %I TO app_readonly', current_database());

  FOR r IN
    SELECT nspname AS schema_name
    FROM pg_namespace
    WHERE nspname NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
  LOOP
    -- USAGE lets the role access the namespace; REVOKE CREATE prevents creating objects
    EXECUTE format('GRANT USAGE ON SCHEMA %I TO app_readonly', r.schema_name);
    EXECUTE format('REVOKE CREATE ON SCHEMA %I FROM app_readonly', r.schema_name);
    -- SELECT on all current tables/sequences in the schema
    EXECUTE format('GRANT SELECT ON ALL TABLES IN SCHEMA %I TO app_readonly', r.schema_name);
    EXECUTE format('GRANT SELECT ON ALL SEQUENCES IN SCHEMA %I TO app_readonly', r.schema_name);
    -- Default privileges: any future tables/sequences created by dbt user (etl)
    -- will be auto-readable by app_readonly without re-running grants.
    EXECUTE format('ALTER DEFAULT PRIVILEGES FOR USER etl IN SCHEMA %I GRANT SELECT ON TABLES TO app_readonly', r.schema_name);
    EXECUTE format('ALTER DEFAULT PRIVILEGES FOR USER etl IN SCHEMA %I GRANT SELECT ON SEQUENCES TO app_readonly', r.schema_name);
  END LOOP;
END$$;
