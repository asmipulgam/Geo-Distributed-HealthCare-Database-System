#!/usr/bin/env python3
"""Load CSV data files from central_backend/data into the databases using DBClient.

This script looks for:
 - central_backend/data/Doctors.csv
 - central_backend/data/Patients_US-WEST.csv
 - central_backend/data/Patients_US-CENTRAL.csv
 - central_backend/data/Patients_US-EAST.csv

It will use the `DBClient` helper methods `bulk_insert_doctors` and
`bulk_insert_patients`. If a connection is available in `db.connections`
for the target region it will be used; otherwise the DBClient will attempt
to open a connection (and fall back to configured backups if enabled).

Usage:
    python3 load_data.py

"""
from pathlib import Path
import csv
import sys
import time
import json
import os
from client import DBClient


def read_csv_rows(path: Path):
    rows = []
    if not path.exists():
        return rows
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            # strip whitespace from keys and values
            cleaned = {k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in r.items()}
            rows.append(cleaned)
    return rows


def load_doctors(db: DBClient, data_dir: Path, region_key: str):
    p = data_dir / "Doctors.csv"
    rows = read_csv_rows(p)
    if not rows:
        print(f"No doctors file found at {p}; skipping doctors load.")
        return
    print(f"Loading {len(rows)} doctors from {p}...")
    start = time.perf_counter()
    success = False
    err = None
    try:
        # let the client pick an appropriate connection if None
        
        db.bulk_insert_doctors(None, rows, batch_size=1000, upsert=True, region=region_key)
        success = True
        print("Doctors loaded.")
    except Exception as e:
        err = str(e)
        print("Failed to load doctors:", e)
    finally:
        duration = time.perf_counter() - start
        return {"type": "doctors", "rows": len(rows), "success": success, "error": err, "seconds": duration}


def load_patients_for_region(db: DBClient, data_dir: Path, region_key: str):
    # region_key e.g. 'us-west' -> file Patients_US-WEST.csv
    fname = f"Patients_{region_key.upper()}.csv"
    p = data_dir / fname
    rows = read_csv_rows(p)
    if not rows:
        print(f"No patient file found for {region_key} at {p}; skipping.")
        return
    print(f"Loading {len(rows)} patients for region {region_key} from {p}...")
    start = time.perf_counter()
    success = False
    err = None
    try:
        
        db.bulk_insert_patients(None, rows, batch_size=500, upsert=True)
        success = True
        print(f"Patients for {region_key} loaded.")
    except Exception as e:
        err = str(e)
        print(f"Failed to load patients for {region_key}: {e}")
    finally:
        duration = time.perf_counter() - start
        # if prometheus labels available, record duration
        
        return {"type": "patients", "region": region_key, "rows": len(rows), "success": success, "error": err, "seconds": duration}


def main():
    repo_root = Path(__file__).resolve().parent
    data_dir = repo_root / 'data'
    if not data_dir.exists():
        print(f"Data directory not found: {data_dir}")
        sys.exit(1)

    db = DBClient()

    # Load doctors first and collect metrics
    metrics = []
    
    for rk in ('US-CENTRAL',):
        rk = rk.lower()
        res = load_doctors(db, data_dir, region_key=rk)
        if res is not None:
            metrics.append(res)

    # Load patients for regions we expect files for
    for rk in ( 'US-CENTRAL',):
        # convert file-style to region key used by DBClient
        region_key = rk.lower()
        r = load_patients_for_region(db, data_dir, region_key)
        if r is not None:
            metrics.append(r)

    # write a small JSON summary to data dir so CI / demo scripts can read durations
    summary = {
        'timestamp': time.time(),
        'metrics': metrics
    }
    out_file = data_dir / 'load_metrics.json'
    try:
        with out_file.open('w', encoding='utf-8') as fh:
            json.dump(summary, fh, indent=2)
        print(f"Wrote load metrics to {out_file}")
    except Exception as e:
        print("Failed to write metrics file:", e)

   

    # Attempt to generate local plots/report if the plotting utility is available
    try:
        from plot_load_metrics import main as _plot_main
        try:
            _plot_main()
            print("Generated local plots/report via plot_load_metrics.py")
        except Exception as e:
            print("plot_load_metrics failed:", e)
    except Exception:
        # plotting script not present or matplotlib not installed; ignore
        pass


if __name__ == '__main__':
    main()
