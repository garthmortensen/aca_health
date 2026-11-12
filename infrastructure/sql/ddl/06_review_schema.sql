-- ---------------------------------------------------------------------------
-- review schema: the paper trail for prior authorization decisions.
--
-- Operational writes live here, apart from the dbt-managed warehouse (dw,
-- summary), which stays read-only for the application.
--
-- One row per decision EVENT. The system's decision is the first row for a
-- request; when a nurse practitioner acts, another row is appended. Rows are
-- never updated or deleted, so the full history of a request is the sequence
-- of its rows ordered by decided_at.
--
-- Runs automatically on first container start. For an existing container:
--   podman exec -i aca_health_postgres psql -U etl -d aca_health \
--       < infrastructure/sql/ddl/06_review_schema.sql
-- ---------------------------------------------------------------------------

CREATE SCHEMA IF NOT EXISTS review;

CREATE TABLE IF NOT EXISTS review.prior_authorization_decision (
    decision_id                     BIGSERIAL PRIMARY KEY,
    prior_authorization_request_id  TEXT        NOT NULL,
    decided_at                      TIMESTAMPTZ NOT NULL DEFAULT now(),
    decided_by                      TEXT        NOT NULL,   -- 'system' or the reviewer's name
    outcome                         TEXT        NOT NULL
        CHECK (outcome IN ('approve', 'deny', 'unclear', 'request_more_info')),
    reason                          TEXT,                   -- one line, human readable
    confidence                      NUMERIC(4,3),           -- AI confidence 0-1 (system rows)
    policy_id                       TEXT,
    policy_version                  TEXT,
    model                           TEXT,                   -- AI model id (system rows)
    checks                          JSONB,                  -- per criterion: status, value, quote
    np_rationale                    TEXT                    -- free text from the reviewer (NP rows)
);

CREATE INDEX IF NOT EXISTS prior_authorization_decision_request_idx
    ON review.prior_authorization_decision (prior_authorization_request_id, decided_at);

COMMENT ON TABLE review.prior_authorization_decision IS
    'Append-only log of prior authorization decisions by the system and by human reviewers';
COMMENT ON COLUMN review.prior_authorization_decision.checks IS
    'List of {id, question, status (pass/fail/unknown), value, quote, near} for each policy criterion';

-- Latest row per request: what the request's status is right now.
CREATE OR REPLACE VIEW review.prior_authorization_status AS
SELECT DISTINCT ON (prior_authorization_request_id)
    prior_authorization_request_id,
    decided_at   AS last_decided_at,
    decided_by   AS last_decided_by,
    outcome      AS current_outcome,
    reason,
    confidence,
    policy_id,
    policy_version
FROM review.prior_authorization_decision
ORDER BY prior_authorization_request_id, decided_at DESC, decision_id DESC;

-- Same read-only access as the warehouse schemas, when that role exists
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_readonly') THEN
    GRANT USAGE ON SCHEMA review TO app_readonly;
    GRANT SELECT ON ALL TABLES IN SCHEMA review TO app_readonly;
    ALTER DEFAULT PRIVILEGES FOR USER etl IN SCHEMA review GRANT SELECT ON TABLES TO app_readonly;
  END IF;
END$$;
