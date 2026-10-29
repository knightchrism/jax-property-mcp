-- Least-privilege roles for the jax_property database (run once as a superuser, e.g. postgres):
--   psql -h localhost -U postgres -d jax_property -v ON_ERROR_STOP=1 \
--        -v loader_password="$(openssl rand -hex 24)" -v reader_password="$(openssl rand -hex 24)" -f sql/roles.sql
-- Passwords are required psql variables (the script fails if either is missing) and are never stored in git.
--   jax_loader : owns and (re)builds tables; used only by the load_* / clean_* / home_types scripts
--   jax_reader : SELECT only; used by the MCP server, agents, notebooks and dashboards
SET jax.loader_pw = :'loader_password';
SET jax.reader_pw = :'reader_password';
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'jax_loader') THEN
    CREATE ROLE jax_loader LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'jax_reader') THEN
    CREATE ROLE jax_reader LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
  END IF;
  EXECUTE format('ALTER ROLE jax_loader PASSWORD %L', current_setting('jax.loader_pw'));
  EXECUTE format('ALTER ROLE jax_reader PASSWORD %L', current_setting('jax.reader_pw'));
  EXECUTE format('ALTER ROLE jax_reader SET default_transaction_read_only = on');
  EXECUTE format('ALTER ROLE jax_reader SET statement_timeout = %L', '30s');
END$$;
RESET jax.loader_pw;
RESET jax.reader_pw;

-- Nobody but the owners creates objects in public (PostgreSQL < 15 grants CREATE to PUBLIC by default).
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT CONNECT ON DATABASE jax_property TO jax_loader, jax_reader;
GRANT USAGE, CREATE ON SCHEMA public TO jax_loader;
GRANT USAGE ON SCHEMA public TO jax_reader;

-- Existing tables (e.g. created earlier as postgres): loader may rebuild them, reader may only read.
DO $$
DECLARE t record;
BEGIN
  FOR t IN SELECT schemaname, tablename FROM pg_tables WHERE schemaname = 'public'
                 AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.objid = format('%I.%I', schemaname, tablename)::regclass AND d.deptype = 'e') LOOP
    EXECUTE format('ALTER TABLE %I.%I OWNER TO jax_loader', t.schemaname, t.tablename);
  END LOOP;
  FOR t IN SELECT schemaname, viewname AS tablename FROM pg_views WHERE schemaname = 'public'
                 AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.objid = format('%I.%I', schemaname, viewname)::regclass AND d.deptype = 'e') LOOP
    EXECUTE format('ALTER VIEW %I.%I OWNER TO jax_loader', t.schemaname, t.tablename);
  END LOOP;
  FOR t IN SELECT schemaname, matviewname AS tablename FROM pg_matviews WHERE schemaname = 'public'
                 AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.objid = format('%I.%I', schemaname, matviewname)::regclass AND d.deptype = 'e') LOOP
    EXECUTE format('ALTER MATERIALIZED VIEW %I.%I OWNER TO jax_loader', t.schemaname, t.tablename);
  END LOOP;
END$$;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO jax_reader;
-- Tables the loader creates later are readable by jax_reader automatically.
ALTER DEFAULT PRIVILEGES FOR ROLE jax_loader IN SCHEMA public GRANT SELECT ON TABLES TO jax_reader;
