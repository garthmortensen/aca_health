#!/usr/bin/env python3
"""Staging CSV loader.

Idempotent design:
- One load_batches row per source file (file_pattern = basename).
- Unique partial index (status='completed') prevents duplicates.
- Skips file if a completed load_batches row exists for that filename.

Adds file metadata (size, sha256, source_row_count) for change detection.
"""
from __future__ import annotations

import os
import re
import glob
import sys
import hashlib
from dataclasses import dataclass
from typing import List

import psycopg
from psycopg import sql

SEED_DIR = "data/seeds"
ENTITIES = [
    ("plans", "plans_raw", [
        "plan_id","name","metal_tier","monthly_premium","deductible","oop_max","coinsurance_rate","pcp_copay","effective_year"
    ]),
    ("providers", "providers_raw", [
        "provider_id","npi","name","specialty","street","city","state","zip","phone"
    ]),
    ("members", "members_raw", [
        "member_id","first_name","last_name","dob","gender","email","phone","street","city","state","zip","fpl_ratio","hios_id","plan_network_access_type","plan_metal","age_group","region","enrollment_length_continuous","clinical_segment","general_agency_name","broker_name","sa_contracting_entity_name","new_member_in_period","member_used_app","member_had_web_login","member_visited_new_provider_ind","high_cost_member","mutually_exclusive_hcc_condition","geographic_reporting","year"
    ]),
    ("enrollments", "enrollments_raw", [
        "enrollment_id","member_id","plan_id","start_date","end_date","premium_paid","csr_variant"
    ]),
    ("claims", "claims_raw", [
        "claim_id","member_id","provider_id","plan_id","service_date","claim_amount","allowed_amount","paid_amount","status","diagnosis_code","procedure_code"
    ]),
]

TIMESTAMP_PATTERN = re.compile(r"_(\d{12})\.csv$")

@dataclass
class FileInfo:
    entity: str
    table: str
    path: str
    timestamp: str
    columns: List[str]


def find_latest_files() -> List[FileInfo]:
    out: List[FileInfo] = []
    for entity, table, cols in ENTITIES:
        matches = glob.glob(os.path.join(SEED_DIR, f"{entity}_*.csv"))
        if not matches:
            continue
        latest = max(matches, key=os.path.getmtime)
        m = TIMESTAMP_PATTERN.search(latest)
        ts = m.group(1) if m else ""
        out.append(FileInfo(entity, table, latest, ts, cols))
    return out


def copy_file(cur: psycopg.Cursor, info: FileInfo, load_id: int) -> int:
    # Build COPY statement
    copy_stmt = sql.SQL("COPY staging.{tbl} ({cols}, load_id) FROM STDIN WITH (FORMAT csv, HEADER true)").format(
        tbl=sql.Identifier(info.table),
        cols=sql.SQL(", ").join(sql.Identifier(c) for c in info.columns),
    )
    data_rows = 0
    with open(info.path, "r", encoding="utf-8") as fh, cur.copy(copy_stmt) as cp:
        first_col = info.columns[0]
        for raw in fh:
            if not raw.strip():
                continue
            if raw.startswith(first_col):  # header
                continue
            cp.write(raw.rstrip("\n") + f",{load_id}\n")
            data_rows += 1
    return data_rows


def file_completed(cur: psycopg.Cursor, filename: str) -> bool:
    cur.execute(
        "SELECT 1 FROM staging.load_batches WHERE file_pattern=%s AND status='completed' LIMIT 1",
        (filename,),
    )
    return cur.fetchone() is not None


def file_stats(path: str) -> tuple[int, str, int]:
    size = os.path.getsize(path)
    h = hashlib.sha256()
    rows = 0
    with open(path, 'rb') as f:
        header_skipped = False
        for line in f:
            h.update(line)
            if not header_skipped:
                header_skipped = True
                continue
            rows += 1
    return size, h.hexdigest(), rows


def load_file(conn: psycopg.Connection, info: FileInfo) -> int:
    filename = os.path.basename(info.path)
    size_bytes, sha256, src_rows = file_stats(info.path)
    with conn.cursor() as cur:
        if file_completed(cur, filename):
            print(f"Skip (already completed): {filename}")
            return 0
        cur.execute(
            "INSERT INTO staging.load_batches (source_name, description, file_pattern, file_size_bytes, file_sha256, source_row_count) VALUES (%s,%s,%s,%s,%s,%s) RETURNING load_id",
            (info.entity, f"Load {filename}", filename, size_bytes, sha256, src_rows),
        )
        load_id = cur.fetchone()[0]
        try:
            rows = copy_file(cur, info, load_id)
            if rows != src_rows:
                print(f"WARNING: row count mismatch file={filename} expected={src_rows} loaded={rows}")
            cur.execute(
                "UPDATE staging.load_batches SET row_count=%s, completed_at=now(), status='completed' WHERE load_id=%s",
                (rows, load_id),
            )
            print(f"Loaded {filename} -> {info.table} rows={rows} load_id={load_id}")
            return rows
        except Exception as e:  # noqa: BLE001
            cur.execute(
                "UPDATE staging.load_batches SET status='failed', completed_at=now() WHERE load_id=%s",
                (load_id,),
            )
            print(f"Failed {filename}: {e}", file=sys.stderr)
            raise


def stage_files(conn_str: str) -> int:
    files = find_latest_files()
    if not files:
        print("No seed files found.")
        return 0
    total = 0
    with psycopg.connect(conn_str) as conn:
        conn.autocommit = False
        for info in files:
            try:
                total += load_file(conn, info)
                conn.commit()
            except Exception:
                conn.rollback()
                # continue other files, or break? choose continue
        print(f"Total new rows inserted: {total}")
    return total


def main():
    conn_str = os.environ.get("DB_URL", "postgresql://etl:etl@localhost:5432/dw")
    stage_files(conn_str)

if __name__ == "__main__":
    main()
