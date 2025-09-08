#!/usr/bin/env python3
"""Staging CSV loader.

Filename-based idempotent design:
- Maintains a .loaded_filenames file tracking which files have been processed
- Only loads files whose filenames aren't in the tracker
- Updates tracker file after successful loads
"""
from __future__ import annotations

import os
import re
import glob
import sys
import hashlib
from dataclasses import dataclass
from typing import List, Set
from datetime import datetime, timezone
from pathlib import Path

import psycopg
from psycopg import sql

SEED_DIR = "data/seeds"
TRACKER_FILE = ".loaded_filenames"
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

TIMESTAMP_PATTERN = re.compile(r"_(\d{12})\.csv$")  # e.g. _202401011230.csv

@dataclass
class FileInfo:
    entity: str
    table: str
    path: str
    timestamp: str
    columns: List[str]


def load_processed_filenames() -> Set[str]:
    """Load set of already processed filenames from tracker file."""
    if not os.path.exists(TRACKER_FILE):
        return set()
    
    with open(TRACKER_FILE, "r") as f:
        return {line.strip() for line in f if line.strip()}


def save_processed_filename(filename: str) -> None:
    """Append a filename to the tracker file."""
    with open(TRACKER_FILE, "a") as f:
        f.write(f"{filename}\n")


def find_new_files() -> List[FileInfo]:
    """Find all CSV files that haven't been processed yet, keeping only the latest timestamp per entity."""
    processed = load_processed_filenames()
    entity_files: dict[str, List[FileInfo]] = {}
    
    # Collect all files by entity
    for entity, table, cols in ENTITIES:
        matches = glob.glob(os.path.join(SEED_DIR, f"{entity}_*.csv"))
        entity_files[entity] = []
        
        for file_path in matches:
            filename = os.path.basename(file_path)
            if filename in processed:
                continue  # Skip already processed files
                
            m = TIMESTAMP_PATTERN.search(file_path)
            if not m:
                print(f"Warning: Could not extract timestamp from {file_path}, skipping")
                continue
            
            timestamp = m.group(1)
            entity_files[entity].append(FileInfo(entity, table, file_path, timestamp, cols))
    
    # For each entity, keep only the file with the latest timestamp
    out: List[FileInfo] = []
    for entity, files in entity_files.items():
        if not files:
            continue
            
        # Sort by timestamp descending and take the most recent
        latest_file = max(files, key=lambda x: x.timestamp)
        out.append(latest_file)
        
        # Log which files we're skipping
        skipped = [f for f in files if f != latest_file]
        if skipped:
            skipped_names = [os.path.basename(f.path) for f in skipped]
            print(f"  {entity}: Using latest {os.path.basename(latest_file.path)}, skipping older: {', '.join(skipped_names)}")
    
    return out


def copy_file(cur: psycopg.Cursor, info: FileInfo, load_id: int) -> int:
    """Copy CSV data into staging table. Watch out for headers/no headers"""
    copy_stmt = sql.SQL("COPY staging.{tbl} ({cols}, load_id) FROM STDIN WITH (FORMAT csv)").format(
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


def file_stats(path: str) -> tuple[int, str, int]:
    """Calculate file size, SHA256, and row count."""
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
    """Load a single CSV file into staging."""
    filename = os.path.basename(info.path)
    size_bytes, sha256, src_rows = file_stats(info.path)
    
    with conn.cursor() as cur:
        # Create load_batches entry
        cur.execute(
            "INSERT INTO staging.load_batches (source_name, description, file_pattern, file_size_bytes, file_sha256, source_row_count) VALUES (%s,%s,%s,%s,%s,%s) RETURNING load_id",
            (info.entity, f"Load {filename} (timestamp: {info.timestamp})", filename, size_bytes, sha256, src_rows),
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
            print(f"Loaded {filename} -> {info.table} rows={rows} load_id={load_id} timestamp={info.timestamp}")
            return rows
        except Exception as e:
            cur.execute(
                "UPDATE staging.load_batches SET status='failed', completed_at=now() WHERE load_id=%s",
                (load_id,),
            )
            print(f"Failed {filename}: {e}", file=sys.stderr)
            raise


def stage_files(conn_str: str) -> int:
    """Load all new CSV files into staging."""
    files = find_new_files()
    if not files:
        print("No new seed files to load.")
        return 0
    
    print(f"Found {len(files)} new files to load:")
    for f in files:
        print(f"  {f.entity}: {os.path.basename(f.path)} (timestamp: {f.timestamp})")
    
    total = 0
    with psycopg.connect(conn_str) as conn:
        conn.autocommit = False
        for info in files:
            try:
                rows = load_file(conn, info)
                total += rows
                # Mark filename as processed after successful load
                save_processed_filename(os.path.basename(info.path))
                conn.commit()
            except Exception as e:
                conn.rollback()
                print(f"Load failed for {info.path}, stopping: {e}", file=sys.stderr)
                break
    
    print(f"Total new rows inserted: {total}")
    return total


def main():  # user pass
    conn_str = os.environ.get("DB_URL", "postgresql://etl:etl@localhost:5432/dw")
    stage_files(conn_str)


if __name__ == "__main__":
    main()
