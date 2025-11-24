import configparser
import os
import requests
from flask import Flask, request, jsonify
from Replicator import Replicator
from client import DBClient
from fetchall import FetchAll
import csv
from pathlib import Path
import re
import time
import uuid
import signal
import atexit
import threading
import os
import multiprocessing
import warnings

import psycopg2

from datetime import datetime
from decimal import Decimal
import math

# URL of the node backend to forward paginated queries to
NODE_BACKEND_URL = os.environ.get("NODE_BACKEND_URL", "http://localhost:5001")

app = Flask(__name__)

# In-memory ring of recent query metrics (kept small for demo purposes)
RECENT_METRICS = []

# Keep references to running Replicator instances so we can stop them on shutdown
REPLICATORS = []


# Simple CORS handling so frontend (vite) can call this API during development.
# For production, use flask-cors or restrict origins appropriately.
@app.before_request
def _handle_options():
    # Respond to preflight OPTIONS requests
    if request.method == "OPTIONS":
        resp = app.make_response(("", 200))
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
        resp.headers[
            "Access-Control-Allow-Headers"
        ] = request.headers.get("Access-Control-Request-Headers", "*")
        return resp


@app.after_request
def _add_cors_headers(response):
    response.headers.setdefault("Access-Control-Allow-Origin", "*")
    response.headers.setdefault("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
    response.headers.setdefault(
        "Access-Control-Allow-Headers", "Content-Type,Authorization,Accept,Origin"
    )
    return response




@app.get("/ping")
def ping():
    return jsonify({"status": "ok", "message": "pong"}), 200


@app.get("/greet")
def greet():
    name = request.args.get("name", "world")
    return jsonify({"greeting": f"Hello, {name}!"}), 200


@app.post("/echo")
def echo():
    # Echo back JSON body or form fields
    if request.is_json:
        data = request.get_json(silent=True) or {}
    else:
        data = request.form.to_dict(flat=True)
    return jsonify({"received": data}), 200

@app.post("/api/getcustomer")
def getCustomer():
    data = request.json
    try:
        # Expect a JSON object with an 'id' field
        customer_id = data.get("id")
        state = data.get("state")
        print(f"Fetching customer with ID: {customer_id} and state: {state}")
        customer_data = db.fetchUserData(customer_id, state)
        status = 200
        print("CD",customer_data)
        # db.fetchUserData may return (dict, status) for not-found
        if isinstance(customer_data, tuple) and len(customer_data) == 2:
            payload, status = customer_data
        else:
            payload = customer_data

        # Record metrics if present
        try:
            if isinstance(payload, dict) and payload.get("metrics"):
                m = payload.get("metrics")
                entry = {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "endpoint": "getcustomer",
                    "region": state,
                    "customer_id": customer_id,
                    "metrics": m,
                }
                RECENT_METRICS.insert(0, entry)
                if len(RECENT_METRICS) > 50:
                    RECENT_METRICS.pop()
        except Exception:
            pass

        return jsonify(payload), status
    except Exception as e:
        print(e)
        return jsonify({"status": "error", "message": str(e)}), 500



@app.post("/api/admin/create")
def addData():
    data = request.json
    try:
        # Expect a JSON object representing a single patient row
        print(data)
        res = db.insert_patient_new(data)
        # If insert returned metrics, record them
        try:
            if isinstance(res, dict) and res.get("metrics"):
                m = res.get("metrics")
                entry = {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "endpoint": "insert_patient",
                    "payload_region": data.get("Region") or data.get("State") or data.get("region"),
                    "metrics": m,
                }
                RECENT_METRICS.insert(0, entry)
                if len(RECENT_METRICS) > 50:
                    RECENT_METRICS.pop()
        except Exception:
            pass

        # Forward the DB client's response to caller
        return jsonify(res), 200
    except Exception as e:
        print(e)
        return jsonify({"status": "error", "message": str(e)}), 500


@app.post('/admin/reload-connections')
def admin_reload_connections():
    """Admin endpoint to close and re-open DB connections based on current
    `LOCAL_URLS` and `/etc/hosts` changes. Returns a JSON report indicating
    which regions are reachable.
    """
    global db
    try:
        if 'db' not in globals() or db is None:
            db = DBClient()
        statuses = db.reload_connections()
        return jsonify({"status": "ok", "connections": statuses}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500





@app.get("/api/all")
def api_all():
    """Return paginated patients rows.

    Query params:
      - region: one of 'west','east','central' (affects DSN)
      - cursor: integer offset (default 0)
      - dir: 'next' or 'prev' (default 'next')
      - page_size: optional page size (default 20)
    """
    if FetchAll is None:
        return jsonify({"error": "fetchall helper not available"}), 500

    region = request.args.get("region", "west")
    try:
        cursor = int(request.args.get("cursor", 0))
    except Exception:
        cursor = 0
    dir = request.args.get("dir", "next")
    try:
        page_size = int(request.args.get("page_size", 20))
    except Exception:
        page_size = 20

    # Map region to DSN; adjust ports if your local setup differs
    dsn = db.getURL({"region": region})
    # map short region to table name: use patients_west for west, patients_central for others
    table_name = ('patients_west' if 'west' in str(region) else 'patients_central')
    fetcher = FetchAll(dsn=dsn)
    fetcher.table_name = table_name
    try:
        page = fetcher.fetch(cursor=cursor, dir=dir, page_size=page_size)
        # If the fetcher returned metrics, record them for admin UI
        try:
            m = page.get("metrics")
            if m:
                entry = {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "region": region,
                    "cursor": cursor,
                    "page_size": page_size,
                    "metrics": m,
                }
                RECENT_METRICS.insert(0, entry)
                # keep recent history bounded
                if len(RECENT_METRICS) > 50:
                    RECENT_METRICS.pop()
        except Exception:
            pass
        return jsonify(page), 200
    except Exception as e:
        print(f"Error fetching data: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        try:
            fetcher.close()
        except Exception:
            pass


@app.get("/api/metrics")
def api_metrics():
    """Return recent query metrics collected from /api/all.

    This is a lightweight in-memory store for demonstration only.
    """
    return jsonify({"metrics": RECENT_METRICS}), 200


@app.post('/api/search')
def api_search():
    """Accepts JSON body: { region: 'us-west', filters: [{col,op,val}, ...], limit: 1000 }
    Returns { records: [...] }
    """
    try:
        body = request.get_json(silent=True) or {}
        # Accept either a single `region` or multiple `regions` (list)
        region = body.get('region')
        regions = body.get('regions') or ([] if region is None else [region])
        filters = body.get('filters') or []
        limit = int(body.get('limit', 10))

        t0 = time.time()
        rows = []
        # Determine per-region fetch size. We distribute the requested `limit` across selected
        # regions to avoid over-fetching. Each physical DB has a hard cap of 90000 records.
        req_limit = int(limit)
        num_regions = max(1, len(regions))
        per_region_limit = max(1, math.ceil(req_limit / num_regions))
        # Cap per-region fetch size to physical DB limit
        per_region_limit = min(90000, per_region_limit)

        # Query each requested region and aggregate results. We will truncate the combined
        # results to the requested overall `limit` before returning.
        for r in regions:
            try:
                part = db.search_patients(filters=filters, region=r, limit=per_region_limit)
                # ensure we tag origin region so the UI can show provenance
                if isinstance(part, (list, tuple)):
                    for pr in part:
                        if isinstance(pr, dict):
                            # If the row already has Region/region, leave it; otherwise set `__source_region`
                            if not (pr.get('Region') or pr.get('region')):
                                pr['__source_region'] = r
                            rows.append(pr)
                        else:
                            rows.append(pr)
            except Exception as e:
                # ignore region errors but continue with others
                print(f"Warning: search failed for region {r}: {e}")

        elapsed_ms = int((time.time() - t0) * 1000)

        # Truncate combined results to requested overall limit for stable UI
        if isinstance(rows, list) and len(rows) > req_limit:
            rows = rows[:req_limit]

        # record a lightweight metric entry
        try:
            entry = {
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'endpoint': 'search',
                'region': region,
                'filters_count': len(filters),
                'rows': len(rows) if isinstance(rows, (list, tuple)) else 0,
                'elapsed_ms': elapsed_ms,
            }
            RECENT_METRICS.insert(0, entry)
            if len(RECENT_METRICS) > 50:
                RECENT_METRICS.pop()
        except Exception:
            pass

        return jsonify({'records': rows}), 200
    except Exception as e:
        print('Search error:', e)
        return jsonify({'error': str(e)}), 500


@app.post('/api/organ_search')
def api_organ_search():
    """Endpoint to find potential donors near a hospital.

    Expected body: { hospital: { id,name,address,lat,lng,region,state }, organ: str, age_min?, age_max? }
    The handler will query the appropriate region DB (using hospital.region) and filter by State
    and optional age range. Returns top 5 matching patient rows.
    """
    try:
        body = request.get_json(silent=True) or {}
        hospital = body.get('hospital') or {}
        # donor-only search uses boolean field `is_organ_donor` in patients
        donor_only = body.get('donor_only', True)
        age_min = body.get('age_min')
        age_max = body.get('age_max')

        region = hospital.get('region') or 'us-west'
        state = hospital.get('state')

        filters = []
        if state:
            filters.append({'col': 'State', 'op': '=', 'val': state})
        if donor_only:
            # boolean match
            filters.append({'col': 'is_organ_donor', 'op': '=', 'val': True})
        if age_min is not None:
            filters.append({'col': 'Age', 'op': '>=', 'val': age_min})
        if age_max is not None:
            filters.append({'col': 'Age', 'op': '<=', 'val': age_max})
        # perform search on region DB, limit to 5; if hospital coords present, pass them for proximity search
        try:
            center_lat = hospital.get('lat')
            center_lon = hospital.get('lng') or hospital.get('lon')
            if center_lat is not None and center_lon is not None:
                rows = db.search_patients(filters=filters, region=region, limit=5, center_lat=center_lat, center_lon=center_lon, donor_only=donor_only)
            else:
                rows = db.search_patients(filters=filters, region=region, limit=5, donor_only=donor_only)
        except Exception as e:
            print('organ_search db error:', e)
            return jsonify({'error': str(e)}), 500

        # record metric
        try:
            entry = {
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'endpoint': 'organ_search',
                'hospital_id': hospital.get('id'),
                'region': region,
                'rows': len(rows) if isinstance(rows, (list, tuple)) else 0,
            }
            RECENT_METRICS.insert(0, entry)
            if len(RECENT_METRICS) > 50:
                RECENT_METRICS.pop()
        except Exception:
            pass

        return jsonify({'records': rows}), 200
    except Exception as e:
        print('organ_search error:', e)
        return jsonify({'error': str(e)}), 500


@app.get('/api/analytics/summary')
def api_analytics_summary():
    """Run simple distributed queries across west and central and return merged stats.

    Query params:
      - per_region_limit: max rows to fetch per region for aggregation/sample (default 500)
    """
    try:
        per_region_limit = int(request.args.get('per_region_limit', 500))
    except Exception:
        per_region_limit = 500

    regions = ['us-west', 'us-central']
    totals = { 'rows': 0 }
    by_state = {}
    gender = {}
    ages = []
    sample_rows = []

    for r in regions:
        try:
            rows = db.search_patients(filters=[], region=r, limit=per_region_limit)
        except Exception as e:
            rows = []
        if not rows:
            continue
        for row in rows:
            totals['rows'] += 1
            st = row.get('State') or row.get('state') or 'Unknown'
            by_state[st] = by_state.get(st, 0) + 1
            g = row.get('Gender') or row.get('gender') or 'Unknown'
            gender[g] = gender.get(g, 0) + 1
            try:
                age_val = row.get('Age') or row.get('age')
                if age_val is not None:
                    ages.append(int(age_val))
            except Exception:
                pass
            if len(sample_rows) < 200:
                sample_rows.append({
                    'Patient_ID': row.get('Patient_ID') or row.get('patient_id'),
                    'Patient_Name': row.get('Patient_Name') or row.get('patient_name'),
                    'State': st,
                    'Age': row.get('Age') or row.get('age'),
                    'Gender': g,
                })

    ages_sorted = sorted(ages)

    return jsonify({
        'total_rows': totals['rows'],
        'by_state': by_state,
        'gender': gender,
        'ages': ages_sorted,
        'sample_rows': sample_rows,
    }), 200

def initReplicators():
    # Create Replicator instances that run their internal replication logic
    # by providing the DB client and source/target regions. The Replicator
    # will forward the regions to its internal routine and use the client's
    # URL mapping to connect to source and target DBs.
    # replicator_east = Replicator(
    #     lambda: None,
    #     db_client=db,
    #     source_region="us-east",
    #     target_regions=["us-central", "us-west"],
    #     interval=1.5,
    #     run_on_start=True,
    # )
    replicator_west = Replicator(
        lambda: None,
        db_client=db,
        source_region="us-west",
        target_regions=["us-east"],
        interval=1.5,
        run_on_start=True,
    )
    # replicator_central = Replicator(
    #     lambda: None,
    #     db_client=db,
    #     source_region="us-central",
    #     target_regions=["us-east"],
    #     interval=1.5,
    #     run_on_start=True,
    # )
    #replicator_east.start()
    replicator_west.start()
    # remember the replicator so we can stop it on process exit
    try:
        REPLICATORS.append(replicator_west)
    except Exception:
        pass
    #replicator_central.start()
    print("Replicators initialized and started.")


def shutdown_replicators(signum=None, frame=None):
    """Stop any running Replicator instances. Safe to call multiple times.

    Registered as a signal handler for SIGINT/SIGTERM and with `atexit`.
    Accepts optional (signum, frame) so it can be used as a handler.
    """
    # Prevent re-entrancy
    if getattr(shutdown_replicators, 'in_progress', False):
        print("Shutdown already in progress; ignoring additional signal")
        return
    shutdown_replicators.in_progress = True

    print(f"Shutting down replicators (signal={signum})...")

    # Start a watchdog that will forcibly kill the process after a timeout
    def _force_kill_after(timeout_sec=30):
        try:
            time.sleep(timeout_sec)
            print(f"Shutdown timeout ({timeout_sec}s) reached, forcing exit...")
        except Exception:
            pass
        # Attempt to terminate any active child processes first
        try:
            for p in multiprocessing.active_children():
                try:
                    p.terminate()
                    p.join(1)
                except Exception:
                    pass
        except Exception:
            pass

        # Suppress noisy resource_tracker warning if leftover semaphores exist
        try:
            warnings.filterwarnings("ignore", message=r"resource_tracker: There appear to be .* leaked semaphore objects to clean up at shutdown")
        except Exception:
            pass

        # Use os._exit to avoid any stuck cleanup hooks; this is last-resort
        os._exit(1)

    watcher = threading.Thread(target=_force_kill_after, args=(30,), daemon=True)
    watcher.start()

    # Attempt graceful stop of known replicators
    for rep in list(REPLICATORS):
        try:
            # If the Replicator exposes a stop(timeout) API, use it; otherwise call stop()
            try:
                rep.stop(timeout=5)
            except TypeError:
                # fallback if stop() doesn't accept timeout
                rep.stop()
        except Exception as e:
            print("Error stopping replicator:", e)

    # Allow a short grace period for threads to finish
    try:
        time.sleep(1)
    except Exception:
        pass

    REPLICATORS.clear()

    print("Shutdown actions complete — exiting process.")
    # Exit immediately; watcher will force-exit if this fails
    try:
        os._exit(0)
    except Exception:
        # If os._exit fails for any reason, raise SystemExit as fallback
        raise SystemExit(0)

if __name__ == "__main__":
    # Run the Flask development server
    db = DBClient()
    # Register signal handlers and atexit to ensure replicators are stopped
    try:
        signal.signal(signal.SIGINT, shutdown_replicators)
        signal.signal(signal.SIGTERM, shutdown_replicators)
    except Exception:
        pass
    try:
        if REPLICATORS == [] or REPLICATORS is None:
            pass
        print("Exiting")
        #atexit.register(shutdown_replicators)
    except Exception:
        pass

    initReplicators()
    print("Client initialized")
    #These are for direct loading of data at initial point
    #db.loadDoctorData(db.connections["us-west"])
    #db.loadLocalData(db.connections["us-east"])
    app.run(host="0.0.0.0", port=5010, debug=True)
    
    
