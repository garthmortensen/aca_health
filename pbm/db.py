"""The app's database: one DuckDB file, pbm/data/pbm.duckdb.

It holds two schemas:
  dw       a read-only snapshot of the warehouse tables the policy checks need,
           copied from the Postgres warehouse by pbm/build_db.py
  review   the paper trail, review.prior_authorization_decision, appended to by
           record.py and the dashboard

DuckDB runs inside the Python process, so the dashboard can be hosted on
Streamlit Community Cloud with no database server. On Community Cloud the
filesystem resets on restart or redeploy, so reviewer decisions made there last
until the app restarts.

Set PBM_DUCKDB to use a different file.
"""
from __future__ import annotations

import os

import duckdb

HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("PBM_DUCKDB", os.path.join(HERE, "data", "pbm.duckdb"))

REVIEW_DDL = """
create schema if not exists review;
create sequence if not exists review.decision_id_seq;

-- One row per decision event, never updated or deleted
create table if not exists review.prior_authorization_decision (
    decision_id                     bigint primary key default nextval('review.decision_id_seq'),
    prior_authorization_request_id  varchar     not null,
    decided_at                      timestamptz not null default current_timestamp,
    decided_by                      varchar     not null,   -- 'system' or the reviewer's name
    outcome                         varchar     not null
        check (outcome in ('approve', 'deny', 'unclear', 'request_more_info')),
    reason                          varchar,
    confidence                      decimal(4,3),           -- AI confidence 0-1 (system rows)
    policy_id                       varchar,
    policy_version                  varchar,
    model                           varchar,                -- AI model id (system rows)
    checks                          json,                   -- per criterion: status, value and evidence from each source
    summary                         varchar,                -- AI briefing for the reviewer
    np_rationale                    varchar                 -- free text from the reviewer (NP rows)
);

-- Latest row per request: what the request's status is right now
create or replace view review.prior_authorization_status as
select prior_authorization_request_id,
       decided_at as last_decided_at,
       decided_by as last_decided_by,
       outcome    as current_outcome,
       reason, confidence, policy_id, policy_version
from review.prior_authorization_decision
qualify row_number() over (partition by prior_authorization_request_id
                           order by decided_at desc, decision_id desc) = 1;
"""


def connect(path: str = DB_PATH) -> duckdb.DuckDBPyConnection:
    """Open the database, creating the review schema if it is missing."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} not found. Build it with: python -m pbm.build_db")
    conn = duckdb.connect(path)
    conn.execute(REVIEW_DDL)
    return conn


def rows(conn: duckdb.DuckDBPyConnection, sql: str, params=None) -> list[dict]:
    """Run a query and return each row as a dict."""
    cur = conn.execute(sql, params)
    names = [d[0] for d in cur.description]
    return [dict(zip(names, r)) for r in cur.fetchall()]
