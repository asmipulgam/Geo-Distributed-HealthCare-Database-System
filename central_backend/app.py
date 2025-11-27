import configparser
import os
from flask import Flask, request, jsonify
from Replicator import Replicator
from client import DBClient
from fetchall import FetchAll
import time
import signal
import atexit
import threading
import os
import multiprocessing
import warnings
from CloudClient import CloudClient
from datetime import datetime
import math

# This is the entry point of the flask server. We are using flask to create the backend due to simple architecture and logic
app = Flask(__name__)

RECENT_METRICS = []

#As mentioned in report, we will replicate data to from west and central to east and (vice versa if there is a downtime), Storing global variables for instance reference
REPLICATORS = []


# We are running backend and frontend on same machine even for demo right, So avoiding any potentials CORS issues which can block communication
# Should be avoided in production hostong as can cause abuse of systems.
@app.before_request
def _handle_options():
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


#The below are three are default flask generated endpoints from builder template. Kept it as ease. No use in our project.
@app.get("/ping")
def ping():
    return jsonify({"status": "ok", "message": "pong"}), 200


@app.get("/greet")
def greet():
    name = request.args.get("name", "world")
    return jsonify({"greeting": f"Hello, {name}!"}), 200


@app.post("/echo")
def echo():
    if request.is_json:
        data = request.get_json(silent=True) or {}
    else:
        data = request.form.to_dict(flat=True)
    return jsonify({"received": data}), 200

#User login endpoint. When user enters his ID, State and DOB , he will come to a screen where his details are mentioned.
@app.post("/api/getcustomer")
def getCustomer():
    data = request.json
    try:
        customer_id = data.get("id")
        state = data.get("state")
        print(f"Fetching customer with ID: {customer_id} and state: {state}")
        customer_data = db.fetchUserData(customer_id, state)
        status = 200
        if isinstance(customer_data, tuple) and len(customer_data) == 2:
            payload, status = customer_data
        else:
            payload = customer_data

        try:
            if isinstance(payload, dict) and payload.get("metrics"):
                m = payload.get("metrics")
                entry = {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "endpoint": "getcustomer",
                    "region": state,
                    "customer_id": customer_id,
                    "metrics": m,
                    "rows": int(m.get('rows')) if isinstance(m.get('rows'), (int, float)) else (m.get('rows') or None),
                    "elapsed_ms": int(m.get('select_time_ms')) if m.get('select_time_ms') is not None else (m.get('elapsed_ms') if m.get('elapsed_ms') is not None else None),
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


#Simple Crate endpoint in CRUD REST API strategy.
@app.post("/api/admin/create")
def addData():
    data = request.json
    try:
        print(data)
        res = db.insert_patient_new(data)
        try:
            if isinstance(res, dict) and res.get("metrics"):
                m = res.get("metrics")
                entry = {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "endpoint": "insert_patient",
                    "payload_region": data.get("Region") or data.get("State") or data.get("region"),
                    "metrics": m,
                    "rows": int(m.get('rows')) if isinstance(m.get('rows'), (int, float)) else (m.get('rows') or None),
                    "elapsed_ms": int(m.get('select_time_ms')) if m.get('select_time_ms') is not None else (m.get('elapsed_ms') if m.get('elapsed_ms') is not None else None),
                }
                RECENT_METRICS.insert(0, entry)
                if len(RECENT_METRICS) > 50:
                    RECENT_METRICS.pop()
        except Exception:
            pass
        return jsonify(res), 200
    except Exception as e:
        print(e)
        return jsonify({"status": "error", "message": str(e)}), 500

# TODO(REMOVE)
# HealthCheck endpoint to reload DB connections based on current network changes
@app.post('/admin/reload-connections')
def admin_reload_connections():
    global db
    try:
        if 'db' not in globals() or db is None:
            db = DBClient()
        statuses = db.reload_connections()
        return jsonify({"status": "ok", "connections": statuses}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    

# This endpoint will fetch node details from CockroachDB Cloud API for the admin page.
# We tried making it similar to local cockroachDB cluster admin UI but due to limitations on the free tier (dedicated and standard paid tiers have more features)
# We can't show any more useful information than this. But in production environments, A paid tier will add more monitoring and metrics capabiltiies with custom 
# Backup Schedules, etc
@app.get("/api/nodes")
def api_nodes():
    """Fetch cluster and node status from NODE_BACKEND_URL and return to caller."""
    try:
        return jsonify(clusterDetails), 200
    except Exception as e:
        print("Error fetching nodes from backend:", e)
        return jsonify({"error": str(e)}), 500





@app.get("/api/all")
def api_all():
    """Return paginated patients rows.

    Query params:
      - region: one of 'west','east','central' get from where
      - cursor: integer offset (default 0) starting offset value , 0.20,40, etc
      - dir: 'next' or 'prev' (default 'next') Go back or next set of records
      - page_size: set to 20, Feel free to modify
    """
    if FetchAll is None:
        return jsonify({"error": "Some issue. Data not available"}), 500

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
    table_name = ('patients_west' if 'west' in str(region) else 'patients_central')
    used_region = region
    used_dsn = None
    try:
        conn_for_region, used_region_resolved, created_tmp = db.get_connection_for_region(region, allow_backup=True)
    except Exception:
        conn_for_region = None
        used_region_resolved = None
        created_tmp = False

    if used_region_resolved:
        used_region = used_region_resolved

    used_dsn = db.getURL({"region": used_region}) or db.getURL({"region": region})
    try:
        if created_tmp and conn_for_region is not None:
            conn_for_region.close()
    except Exception:
        pass

    fetcher = FetchAll(dsn=used_dsn)
    fetcher.table_name = table_name

    def _record_page_metrics(page_obj, used_region_val):
        try:
            m = page_obj.get("metrics")
            if m:
                entry = {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "region": region,
                    "used_region": used_region_val,
                    "cursor": cursor,
                    "page_size": page_size,
                    "metrics": m,
                    "rows": int(m.get('rows')) if isinstance(m.get('rows'), (int, float)) else (m.get('rows') or 0),
                    "elapsed_ms": int(m.get('select_time_ms')) if m.get('select_time_ms') is not None else None,
                }
                RECENT_METRICS.insert(0, entry)
                if len(RECENT_METRICS) > 50:
                    RECENT_METRICS.pop()
        except Exception:
            print(e)

    try:
        page = fetcher.fetch(cursor=cursor, dir=dir, page_size=page_size)
        try:
            if isinstance(page, dict):
                page['used_region'] = used_region
        except Exception:
            pass
        _record_page_metrics(page, used_region)
        return jsonify(page), 200
    except Exception as e:
        print(f"Primary fetch failed (dsn={used_dsn}): {e}")
        try:
            ft_replica_URL = db.__getReplicaURL({"region": region})
        except Exception:
            ft_replica_URL = None

        if ft_replica_URL:
            backup_dsn = db.getURL({"region": ft_replica_URL}) or ft_replica_URL
            try:
                alt_fetcher = FetchAll(dsn=backup_dsn)
                alt_fetcher.table_name = table_name
                try:
                    page2 = alt_fetcher.fetch(cursor=cursor, dir=dir, page_size=page_size)
                    try:
                        if isinstance(page2, dict):
                            page2['used_region'] = ft_replica_URL
                    except Exception:
                        pass
                    _record_page_metrics(page2, ft_replica_URL)
                    return jsonify(page2), 200
                finally:
                    try:
                        alt_fetcher.close()
                    except Exception as e:
                        print(f"Error closing cursor: {e}")
            except Exception as e2:
                print(f"Fallback Fault Tolerance Connection also failed (backup={ft_replica_URL}): {e2}")
        return jsonify({"error": str(e)}), 500
    finally:
        try:
            fetcher.close()
        except Exception:
            pass


# Get recorded metrics
@app.get("/api/metrics")
def api_metrics():
    return jsonify({"metrics": RECENT_METRICS}), 200

# This is an admin search query which performs distributed query with custom filters across cluster regions
@app.post('/api/search')
def api_search():
    """{ region: 'us-west', filters: [{col,op,val}, ...], limit: 1000 }
     { records: [...] }
    """
    try:
        body = request.get_json(silent=True) or {}
        region = body.get('region')
        regions = body.get('regions') or ([] if region is None else [region])
        filters = body.get('filters') or []
        limit = int(body.get('limit', 10))

        t0 = time.time()
        rows = []
        req_limit = int(limit)
        num_regions = max(1, len(regions))
        per_region_limit = max(1, math.ceil(req_limit / num_regions))
        per_region_limit = min(90000, per_region_limit)
        per_region_timings = []
        for r in regions:
            try:
                t_region = time.time()
                part = db.search_patients(filters=filters, region=r, limit=per_region_limit)
                region_elapsed_ms = int((time.time() - t_region) * 1000)
                part_count = len(part) if isinstance(part, (list, tuple)) else (1 if part is not None else 0)
                per_region_timings.append({
                    'region': r,
                    'elapsed_ms': region_elapsed_ms,
                    'rows': part_count,
                })
                if isinstance(part, (list, tuple)):
                    for pr in part:
                        if isinstance(pr, dict):
                            if not (pr.get('Region') or pr.get('region')):
                                pr['__source_region'] = r
                            rows.append(pr)
                        else:
                            rows.append(pr)
            except Exception as e:
                print(f"Warning: search failed for region {r}: {e}")
                per_region_timings.append({
                    'region': r,
                    'elapsed_ms': None,
                    'rows': 0,
                    'error': str(e),
                })

        elapsed_ms = int((time.time() - t0) * 1000)

        if isinstance(rows, list) and len(rows) > req_limit:
            rows = rows[:req_limit]
        try:
            entry = {
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'endpoint': 'search',
                'region': region,
                'filters_count': len(filters),
                'rows': len(rows) if isinstance(rows, (list, tuple)) else 0,
                'elapsed_ms': elapsed_ms,
                'per_region': per_region_timings,
            }
            RECENT_METRICS.insert(0, entry)
            if len(RECENT_METRICS) > 50:
                RECENT_METRICS.pop()
        except Exception:
            pass

        return jsonify({'records': rows, 'elapsed_ms': elapsed_ms, 'per_region': per_region_timings}), 200
    except Exception as e:
        print('Search error:', e)
        return jsonify({'error': str(e)}), 500


@app.post('/api/organ_search')
def api_organ_search():
    try:
        body = request.get_json(silent=True) or {}
        hospital = body.get('hospital') or {}
        donor_only = body.get('donor_only', True)
        age_min = body.get('age_min')
        age_max = body.get('age_max')

        region = hospital.get('region') or 'us-west'
        state = hospital.get('state')

        filters = []
        if state:
            filters.append({'col': 'State', 'op': '=', 'val': state})
        if donor_only:
            filters.append({'col': 'is_organ_donor', 'op': '=', 'val': True})
        if age_min is not None:
            filters.append({'col': 'Age', 'op': '>=', 'val': age_min})
        if age_max is not None:
            filters.append({'col': 'Age', 'op': '<=', 'val': age_max})
        try:
            center_lat = hospital.get('lat')
            center_lon = hospital.get('lng') or hospital.get('lon')
            t0 = time.time()
            if center_lat is not None and center_lon is not None:
                rows = db.search_patients(filters=filters, region=region, limit=5, center_lat=center_lat, center_lon=center_lon, donor_only=donor_only)
            else:
                rows = db.search_patients(filters=filters, region=region, limit=5, donor_only=donor_only)
            elapsed_ms = int((time.time() - t0) * 1000)
        except Exception as e:
            print('organ_search db error:', e)
            return jsonify({'error': str(e)}), 500
        try:
            entry = {
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'endpoint': 'organ_search',
                'hospital_id': hospital.get('id'),
                'region': region,
                'rows': len(rows) if isinstance(rows, (list, tuple)) else 0,
                'elapsed_ms': int(elapsed_ms) if elapsed_ms is not None else None,
            }
            RECENT_METRICS.insert(0, entry)
            if len(RECENT_METRICS) > 50:
                RECENT_METRICS.pop()
        except Exception:
            pass

        return jsonify({'records': rows, 'elapsed_ms': elapsed_ms}), 200
    except Exception as e:
        print('organ_search error:', e)
        return jsonify({'error': str(e)}), 500


# Created this to display an analytics dashboard with charts, etc so that some visualization on distributed qyery can be performed
@app.get('/api/analytics/summary')
def api_analytics_summary():
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
    #Our replicator logic as explained in report should be that all changes to central and west be replicated to backup/replica cluster
    # in east. But if due to fault west or central is down, then east will be primary cluster for that region and all data be forwarded to east. When west/central - the downed instance
    # comes backup, then get any changes during its downtime from east and apply to itself.
    global REPLICATOR_CENTRAL, REPLICATOR_MONITOR_THREAD

    replicator_east = Replicator(
        lambda: None,
        db_client=db,
        source_region="us-east",
        target_regions=["us-central", "us-west"],
        interval=1.5,
        run_on_start=True,
    )
    replicator_west = Replicator(
        lambda: None,
        db_client=db,
        source_region="us-west",
        target_regions=["us-east"],
        interval=1.5,
        run_on_start=True,
    )]
    replicator_central = Replicator(
        lambda: None,
        db_client=db,
        source_region="us-central",
        target_regions=["us-east"],
        interval=1.5,
        run_on_start=False,
    )

    replicator_east.start()
    replicator_west.start()
    REPLICATORS.append(replicator_east)
    REPLICATORS.append(replicator_west)

    REPLICATOR_CENTRAL = replicator_central

    def _central_monitor(poll_interval=5.0):
        print("Central replicator monitor started")
        while True:
            if getattr(shutdown_replicators, 'in_progress', False):
                break
            try:
                statuses = {}
                try:
                    statuses = db.reload_connections()
                except Exception as e:
                    print("Error checking connections for monitor:", e)

                west_ok = statuses.get('us-west', {}).get('ok', False)
                east_ok = statuses.get('us-east', {}).get('ok', False)

                central_running = getattr(REPLICATOR_CENTRAL, '_started', False)


                if not (west_ok and east_ok):
                    if not central_running:
                        try:
                            REPLICATOR_CENTRAL.start()
                            REPLICATOR_CENTRAL._started = True
                            REPLICATORS.append(REPLICATOR_CENTRAL)
                            print("Started central replicator due to region outage")
                        except Exception as e:
                            print("Failed to start central replicator:", e)
                else:

                    if central_running:
                        try:
                            REPLICATOR_CENTRAL.stop()
                        except Exception as e:
                            print("Failed to stop central replicator:", e)
                        try:
                            REPLICATORS.remove(REPLICATOR_CENTRAL)
                        except Exception:
                            pass
                        REPLICATOR_CENTRAL._started = False
                        print("Stopped central replicator: all regions healthy")
            except Exception as e:
                print("Central replicator monitor encountered error:", e)
            time.sleep(poll_interval)


    try:
        REPLICATOR_MONITOR_THREAD = threading.Thread(target=_central_monitor, args=(5.0,), daemon=True)
        REPLICATOR_MONITOR_THREAD.start()
    except Exception as e:
        print("Failed to start central monitor thread:", e)

    print("Replicators initialized (central managed by monitor).")


def shutdown_replicators(signum=None, frame=None):
    if getattr(shutdown_replicators, 'in_progress', False):
        print("Shutdown already in progress; ignoring additional signal")
        return
    shutdown_replicators.in_progress = True

    print(f"Shutting down replicators (signal={signum})...")

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
        #Force exit
        os._exit(1)

    watcher = threading.Thread(target=_force_kill_after, args=(30,), daemon=True)
    watcher.start()

    for rep in list(REPLICATORS):
        try:
            try:
                rep.stop(timeout=5)
            except TypeError:
                rep.stop()
        except Exception as e:
            print("Error stopping replicator:", e)
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

clusterDetails = None

def fetchClusterDetails():
    config = configparser.ConfigParser()
    config.read('database.conf')
    cc1 = CloudClient(api_key=config.get('DEFAULT','API_KEY_EC'))
    cc2 = CloudClient(api_key=config.get('DEFAULT','API_KEY_W'))
    cc1.run_details()
    cc2.run_details()
    global clusterDetails
    clusterDetails = cc1.getClusterDetails()
    clusterDetails.update(cc2.getClusterDetails())
    

if __name__ == "__main__":
    #Run the Flask development server
    db = DBClient()
    try:
        signal.signal(signal.SIGINT, shutdown_replicators)
        signal.signal(signal.SIGTERM, shutdown_replicators)
    except Exception:
        pass
    try:
        if REPLICATORS == [] or REPLICATORS is None:
            pass
        print("Exiting")
        atexit.register(shutdown_replicators)
    except Exception:
        pass

    initReplicators()
    print("Client initialized")
    #These are for direct loading of data at initial point
    #db.loadDoctorData(db.connections["us-west"])
    #db.loadLocalData(db.connections["us-east"])
    fetchClusterDetails()
    app.run(host="0.0.0.0", port=5010, debug=True)
    
    
    
