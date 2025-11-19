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

import psycopg2

from datetime import datetime
from decimal import Decimal

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
        region = body.get('region', 'us-west')
        filters = body.get('filters') or []
        limit = int(body.get('limit', 1000))

        t0 = time.time()
        rows = db.search_patients(filters=filters, region=region, limit=limit)
        elapsed_ms = int((time.time() - t0) * 1000)

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
    print(f"Shutting down replicators (signal={signum})...")
    for rep in list(REPLICATORS):
        try:
            rep.stop(timeout=5)
        except Exception as e:
            print("Error stopping replicator:", e)
    REPLICATORS.clear()

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
        atexit.register(shutdown_replicators)
    except Exception:
        pass

    initReplicators()
    print("Client initialized")
    #db.loadDoctorData(db.connections["us-west"])
    #db.loadLocalData(db.connections["us-west"])
    app.run(host="0.0.0.0", port=5010, debug=True)
    
    
