import configparser
import requests
import json
import time
from decimal import Decimal
from datetime import datetime
import psycopg2
import re
import uuid
from psycopg2.extras import execute_batch,Json, RealDictCursor
import json
import time
from pathlib import Path
import csv

LOCAL_URLS = {
    "us-west": "",
    #"us-central": ""
    #"east": "",
}
BACKUP_URLS = {
    "us-west": "",
   # "central": ""
     #"east": "",
}

# Patient columns (new canonical order)
COLS = [
    "Patient_ID",
    "Patient_Name",
    "Doctor_ID",
    "Doctor_Name",
    "Age",
    "Gender",
    "Phone",
    "Email",
    "Address",
    "State",
    "Region",
    "Appointment_Date",
    "Diagnosis",
    "Date_of_Birth",
    "is_organ_donor",
    "lat",
    "lon",
]

# Doctors table columns
DOCTOR_COLS = ["Doctor_ID", "Doctor_Name", "Hospital", "Region"]


# --- helpers to coerce text to proper Python types (None on blanks) ---
def to_int(x):
    x = (x or "").strip()
    return int(x) if x else None

def to_decimal(x):
    x = (x or "").strip()
    return Decimal(x) if x else None

def to_date(x, fmt="%Y-%m-%d"):
    x = (x or "").strip()
    if not x:
        return None
    # Try multiple common formats if needed
    for f in (fmt, "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(x, f).date().isoformat()
        except ValueError:
            continue
    # fall back: let DB try STRING → DATE cast, or raise
    return x

def to_str(x):
    return (x or "").strip() or None

def getFormattedURL(raw_url, useSecure = True):
        if useSecure:
            return f"{raw_url}?sslmode=verify-full"
        else:
            return f"{raw_url}?sslmode=disable"

def init():
    config = configparser.ConfigParser()
    config.read('database.conf')
    LOCAL_URLS["us-east"] = config.get('DEFAULT', 'eastURL')
    #BACKUP_URLS["us-east"] = config.get('DEFAULT', 'remoteUSEastBackupURL')
    LOCAL_URLS["us-west"] = getFormattedURL(config.get('DEFAULT', 'westURL'))
    BACKUP_URLS["us-west"] = "us-east"#getFormattedURL(config.get('DEFAULT', 'remoteUSWestBackupURL'))
    #LOCAL_URLS["us-central"] = getFormattedURL(config.get('DEFAULT', 'centralURL'))
    #BACKUP_URLS["central"] = config.get('DEFAULT', 'remoteCentralBackupURL')
    print("Read Backend URLS")


class DBClient:

    def __init__(self):
        self.url = None
        init()
        with open('./us_state_regions.json', 'r') as f:
            self.region_map = json.load(f)
        self.connections = {}
        self.initConnections()
        print("west:" ,LOCAL_URLS["us-west"])
        

    def initConnections(self):
        for region, url in LOCAL_URLS.items():
            print(f"Connecting to {region} DB at {url}")
            conn = psycopg2.connect(url)
            self.connections[region] = conn
        print("Initialized DB Connections", self.connections)
    

    def getURLFromState(self,data):
        state = data.get("state")
        if state:
            region = self.region_map.get(state)
            if region:
                print(f"Mapping state {state} to region {region}")
                return LOCAL_URLS[region]
        return None
    
    def getURL(self,data):
        state = data.get("region")
        
        return LOCAL_URLS[state]
    
    def __getReplicaURL(self,data):
        state = data.get("region")
        return BACKUP_URLS[state]

    
    def fetchUserData(self, user_id,state):
        try:
            url = self.getURLFromState({"state":state})
            conn = psycopg2.connect(url)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # join doctors to include provider info
                select_sql = 'SELECT p.*, d."Doctor_Name" AS doctor_name, d."Hospital" AS doctor_hospital, d."Region" AS doctor_region'
                # determine patients table name based on state->region mapping
                region_for_state = self.region_map.get(state)
                table_name = ('patients_west' if (region_for_state and region_for_state.endswith('west')) else 'patients_central')
                select_sql += f' FROM {table_name} p LEFT JOIN doctors d ON p."Doctor_ID" = d."Doctor_ID"'
                select_sql += ' WHERE p."Patient_ID" = %s AND p."State" = %s LIMIT 1;'

                # explain_json = None
                # explain_time_ms = None
                # try:
                #     t0 = time.time()
                #     cur.execute("EXPLAIN (FORMAT JSON) " + select_sql, (user_id,))
                #     explain_time_ms = int((time.time() - t0) * 1000)
                #     erow = cur.fetchone()
                #     if erow:
                #         if isinstance(erow, dict):
                #             first_val = next(iter(erow.values()))
                #         elif isinstance(erow, (list, tuple)):
                #             first_val = erow[0]
                #         else:
                #             first_val = erow
                #         try:
                #             explain_json = json.loads(first_val) if isinstance(first_val, (str, bytes)) else first_val
                #         except Exception:
                #             explain_json = first_val
                # except Exception:
                #     explain_json = None
                #     explain_time_ms = None

                t0 = time.time()
                cur.execute(select_sql, (user_id, state))
                row = cur.fetchone()
                select_time_ms = int((time.time() - t0) * 1000)

                if row:
                    # Return full row including joined doctor fields
                    return dict(row)
                else:
                    # metrics = {
                    #     "select_time_ms": select_time_ms,
                    #     "rows": 0,
                    #     "explain_time_ms": explain_time_ms,
                    #     "explain": explain_json,
                    # }
                    return {"error": "User not found", "metrics": {"select_time_ms": select_time_ms, "rows": 0}}, 404
        except Exception as e:
            return {"error": str(e)}

    def search_patients(self, filters=None, region='us-west', limit=1000, center_lat=None, center_lon=None, donor_only=False):
        """
        Search patients table with a list of filter objects.
        filters: list of {col: <column>, op: <operator>, val: <value>}
        Supported ops: =, !=, LIKE, <, >, <=, >=, IN
        Returns list of dict rows (RealDict) or raises on error.
        """
        filters = filters or []
        allowed_cols = set(COLS)
        allowed_ops = {'=', '!=', 'LIKE', '<', '>', '<=', '>=', 'IN'}

        where_parts = []
        params = []

        for f in filters:
            try:
                col = f.get('col')
                op = (f.get('op') or '=').upper()
                val = f.get('val')
            except Exception:
                continue
            if not col or col not in allowed_cols:
                # skip unknown columns
                continue
            if op not in allowed_ops:
                continue

            if op == 'IN':
                # expect comma-separated values
                items = [s.strip() for s in str(val).split(',') if s.strip()]
                if not items:
                    continue
                placeholders = ','.join(['%s'] * len(items))
                where_parts.append(f'"{col}" IN ({placeholders})')
                params.extend(items)
            elif op == 'LIKE':
                where_parts.append(f'"{col}" LIKE %s')
                params.append(f'%{val}%')
            else:
                where_parts.append(f'"{col}" {op} %s')
                params.append(val)

            # Enforce donor-only filter if requested (safety: add even if callers forgot)
            if donor_only:
                where_parts.append('"is_organ_donor" = %s')
                params.append(True)

            where_clause = (' WHERE ' + ' AND '.join(where_parts)) if where_parts else ''

        # Resolve the physical patients table name for this region
        def _patients_table_for_region(region_key):
            if not region_key:
                return 'patients_central'
            suffix = region_key.split('-')[-1]
            if suffix == 'west':
                return 'patients_west'
            # default to central for central/east/others
            return 'patients_central'

        table_name = _patients_table_for_region(region)

        # If center coordinates provided, include distance using haversine_km
        use_distance = (center_lat is not None and center_lon is not None)
        if use_distance:
            cols_sql = ', '.join(f'"{c}"' for c in COLS)
            # compute distance_km using DB function haversine_km(lat, lon, center_lat, center_lon)
            cols_sql = cols_sql + ", " + f"haversine_km(\"lat\", \"lon\", %s, %s) AS distance_km"
            sql = f'SELECT {cols_sql} FROM {table_name}{where_clause} WHERE \"lat\" IS NOT NULL AND \"lon\" IS NOT NULL ORDER BY distance_km ASC LIMIT %s;'
            params.insert(0, center_lon)  # careful: we'll append center_lat then center_lon in correct order
            params.insert(0, center_lat)
            params.append(limit)
        else:
            cols_sql = ', '.join(f'"{c}"' for c in COLS)
            sql = f'SELECT {cols_sql} FROM {table_name}{where_clause} ORDER BY "Patient_ID" LIMIT %s;'
            params.append(limit)

        conn = self.connections.get(region)
        if conn is None:
            # Fall back to default mapping via getURL
            dsn = self.getURL({'region': region})
            conn = psycopg2.connect(dsn)

        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()
                # return plain list of dicts
                return [dict(r) for r in rows]
        except Exception as e:
            raise

        
    def replicate_outbox_events(self):
        """
        Polls outbox_events, sends new rows to replica DB, and marks processed ones.
        """
        print(" Starting replication loop...")
        SOURCE_DSN = self.getURL({"region": "us-west"}) #"postgresql://root@localhost:26257/west?sslmode=disable"
        REPLICA_DSN =  self.__getReplicaURL({"region": "us-west"})#"postgresql://root@localhost:26260/west?sslmode=disable"
        while True:
            try:
                src_conn = psycopg2.connect(SOURCE_DSN)
                src_cur  = src_conn.cursor()
                print("Connected to Source")

                # Fetch unprocessed events
                src_cur.execute("""
                    SELECT event_id, table_name, op, payload
                    FROM outbox_events
                    WHERE processed = false
                    ORDER BY created_at
                    LIMIT 50;
                """)
                events = src_cur.fetchall()

                print(f"Obtained {len(events)} events")

                if not events:
                    src_cur.close(); src_conn.close()
                    # no events - sleep briefly so replication loop is responsive during testing
                    time.sleep(5)
                    continue

                # Process events
                repl_conn = psycopg2.connect(REPLICA_DSN)
                repl_cur  = repl_conn.cursor()

                for event_id, table, op, payload in events:
                    print(f"Processing event {event_id} op={op} table={table}")
                    try:
                        # payload may be returned as a string or a dict depending on psycopg2 wiring
                        if isinstance(payload, str):
                            try:
                                patient = json.loads(payload)
                            except Exception:
                                patient = payload
                        else:
                            patient = payload

                        # normalize mapping helper for any target columns
                        def build_values_for_cols(obj, cols_list):
                            if not isinstance(obj, dict):
                                raise ValueError("payload is not a JSON object")
                            incoming = {re.sub(r"[^0-9a-z]", "", str(k).lower()): v for k, v in obj.items()}
                            values = []
                            for col in cols_list:
                                if col in obj:
                                    values.append(obj.get(col))
                                    continue
                                col_norm = re.sub(r"[^0-9a-z]", "", col.lower())
                                values.append(incoming.get(col_norm))
                            return tuple(values)

                        # Decide which table to write to and the appropriate columns/conflict keys
                        if op == "upsert":
                            if table and str(table).startswith('patients'):
                                # If outbox already contains a physical patients table name (patients_west/patients_central)
                                # use it directly; otherwise determine patients table name based on payload region/state
                                if str(table).startswith('patients_'):
                                    table_name = table
                                else:
                                    region_key = None
                                    if isinstance(patient, dict):
                                        region_key = patient.get('Region') or self.region_map.get(patient.get('State'))
                                    table_name = ('patients_west' if (region_key and str(region_key).endswith('west')) else 'patients_central')
                                cols_sql = ", ".join(f'"{c}"' for c in COLS)
                                placeholders = ", ".join(["%s"] * len(COLS))
                                # exclude primary key components from updates
                                update_assignments = ", ".join(
                                    f'"{c}" = EXCLUDED."{c}"' for c in COLS if c not in ("Patient_ID", "State")
                                )
                                values = build_values_for_cols(patient, COLS)
                                sql = f"""
                                    INSERT INTO {table_name} ({cols_sql})
                                    VALUES ({placeholders})
                                    ON CONFLICT ("State","Patient_ID") DO UPDATE SET
                                    {update_assignments};
                                """
                                repl_cur.execute(sql, values)
                            elif table == 'doctors':
                                cols_sql = ", ".join(f'"{c}"' for c in DOCTOR_COLS)
                                placeholders = ", ".join(["%s"] * len(DOCTOR_COLS))
                                update_assignments = ", ".join(
                                    f'"{c}" = EXCLUDED."{c}"' for c in DOCTOR_COLS if c != "Doctor_ID"
                                )
                                values = build_values_for_cols(patient, DOCTOR_COLS)
                                sql = f"""
                                    INSERT INTO doctors ({cols_sql})
                                    VALUES ({placeholders})
                                    ON CONFLICT ("Doctor_ID") DO UPDATE SET
                                    {update_assignments};
                                """
                                repl_cur.execute(sql, values)
                            else:
                                # Unknown table - skip
                                print(f" Skipping unknown table in outbox: {table}")
                        elif op == "delete":
                            # Use appropriate delete criteria
                            if table and str(table).startswith('patients'):
                                pid = None
                                state_val = None
                                if isinstance(patient, dict):
                                    pid = patient.get("Patient_ID") or patient.get("id")
                                    state_val = patient.get("State")
                                # If outbox table is explicit (patients_west/patients_central) use it, otherwise derive
                                if str(table).startswith('patients_'):
                                    table_name = table
                                else:
                                    region_key = None
                                    if isinstance(patient, dict):
                                        region_key = patient.get('Region') or self.region_map.get(patient.get('State'))
                                    table_name = ('patients_west' if (region_key and str(region_key).endswith('west')) else 'patients_central')
                                repl_cur.execute(f"DELETE FROM {table_name} WHERE \"Patient_ID\" = %s AND \"State\" = %s;", (pid, state_val))
                            elif table == 'doctors':
                                did = None
                                if isinstance(patient, dict):
                                    did = patient.get("Doctor_ID") or patient.get("id")
                                repl_cur.execute("DELETE FROM doctors WHERE \"Doctor_ID\" = %s;", (did,))

                        # Mark as processed on source
                        src_cur.execute("UPDATE outbox_events SET processed = true WHERE event_id = %s;", (event_id,))

                    except Exception as e:
                        print(f" Failed event {event_id}: {e}")

                # Commit both sides
                repl_conn.commit()
                src_conn.commit()
                print(f" Replicated {len(events)} events.")

                src_cur.close(); repl_cur.close()
                src_conn.close(); repl_conn.close()

            except Exception as e:
                print(" Replication error:", e)
                time.sleep(5)

    def row_to_tuple(self,r):
        """Map a CSV dict row to a positional tuple matching COLS (with type coercion)."""
        return (
            to_str(r.get("Patient_ID")),
            to_str(r.get("Patient_Name")),
            to_str(r.get("Doctor_ID")),
            to_str(r.get("Doctor_Name")),
            to_int(r.get("Age")),
            to_str(r.get("Gender")),
            to_str(r.get("Phone")),
            to_str(r.get("Email")),
            to_str(r.get("Address")),
            to_str(r.get("State")),
            to_str(r.get("Region")),
            to_date(r.get("Appointment_Date")),
            to_str(r.get("Diagnosis")),
            to_date(r.get("Date_of_Birth")),
            (r.get("is_organ_donor") if isinstance(r.get("is_organ_donor"), bool) else (str(r.get("is_organ_donor")).lower() in ("true","1","t","yes"))),
            (float(r.get("lat")) if r.get("lat") not in (None, "") else None),
            (float(r.get("lon")) if r.get("lon") not in (None, "") else None),
        )
    

    
    def insert_patient_new(self, row, upsert=True):
        """
        Insert a single patient row (dict) into patients table.
        - conn: psycopg2 connection
        - row: dict matching column names in COLS
         - upsert: if True, perform ON CONFLICT DO UPDATE for non-id columns
        """
        # If row is JSON (from request), normalize keys to match COLS
        if isinstance(row, dict):
            # Build a normalized lookup for incoming keys: strip non-alphanum and lowercase
            incoming = {}
            for k, v in row.items():
                norm = re.sub(r"[^0-9a-z]", "", str(k).lower())
                incoming[norm] = v

            normalized_row = {}
            for col in COLS:
                col_norm = re.sub(r"[^0-9a-z]", "", col.lower())
                # prefer matched normalized key, else fallback to original column name key
                if col_norm in incoming:
                    normalized_row[col] = incoming[col_norm]
                else:
                    # allow callers to pass exact column names as well
                    normalized_row[col] = row.get(col)
        else:
            normalized_row = row
        print("CP1")

        tup = self.row_to_tuple(normalized_row)

        cols_sql = ", ".join(f'"{c}"' for c in COLS)
        placeholders = ", ".join(["%s"] * len(COLS))

        print(f"CP2, {cols_sql},{tup}")

        # determine patients table name from the incoming row's Region (or state mapping)
        region_key = normalized_row.get('Region') or self.region_map.get(normalized_row.get('State'))
        table_name = ("patients_west" if (region_key and str(region_key).endswith('west')) else "patients_central")

        if upsert:
            update_assignments = ", ".join(
                f'"{c}" = EXCLUDED."{c}"' for c in COLS if c not in ("Patient_ID", "State")
            )
            sql = f"""
                INSERT INTO {table_name} ({cols_sql})
                VALUES ({placeholders})
                ON CONFLICT ("State","Patient_ID") DO UPDATE SET
                {update_assignments};
            """
            print("CP3")
        else:
            sql = f'INSERT INTO {table_name} ({cols_sql}) VALUES ({placeholders});'
        print(f"cp4 {self.getURLFromState({'state':normalized_row.get('State')})}")

        conn = self.connections.get(normalized_row.get("Region"))
        print("CP5 ",conn)

        print(f"Executing SQL: {sql} with values {tup} into {conn}")

        metrics = {
            "insert_time_ms": None,
            "outbox_time_ms": None,
            "rows": None,
        }

        try:
            t0 = time.time()
            with conn.cursor() as cur:
                cur.execute(sql, tup)
                # rows affected may be available via cur.rowcount
                metrics["rows"] = cur.rowcount
            conn.commit()
            metrics["insert_time_ms"] = int((time.time() - t0) * 1000)

            t1 = time.time()
            with conn.cursor() as curr:
                curr.execute("""
                    INSERT INTO outbox_events (event_id, table_name, op,payload)
                            VALUES (%s, %s, %s, %s);
                """, (str(uuid.uuid4()), table_name, "upsert", Json(normalized_row)))
            conn.commit()
            metrics["outbox_time_ms"] = int((time.time() - t1) * 1000)

            return {"status": "success", "metrics": metrics}
        except Exception as e:
            # attempt to include any timing we may have captured
            return {"status": "error", "message": str(e), "metrics": metrics}

    def bulk_insert_patients(self,conn, rows, batch_size=1000, upsert=True):
        """
        Insert or upsert into patients.
        - conn: psycopg2 connection
        - rows: list[dict] from load_csv_rows()
        - upsert=True will do INSERT ... ON CONFLICT(id) DO UPDATE
         """
        tuples = [self.row_to_tuple(r) for r in rows]

        cols_sql = ", ".join(f'"{c}"' for c in COLS)
        placeholders = ", ".join(["%s"] * len(COLS))

        # Determine table name using the Region value from the first row (bulk inserts are expected per-region)
        first_region = (rows[0].get('Region') if rows and isinstance(rows[0], dict) else None)
        table_name = ("patients_west" if (first_region and str(first_region).endswith('west')) else "patients_central")

        if upsert:
            # Update all mutable columns on conflict; leave id intact
            update_assignments = ", ".join(
                f'"{c}" = EXCLUDED."{c}"' for c in COLS if c not in ("Patient_ID", "State")
            )
            sql = f"""
                INSERT INTO {table_name} ({cols_sql})
                VALUES ({placeholders})
                ON CONFLICT ("State","Patient_ID") DO UPDATE SET
                {update_assignments};
            """
        else:
            sql = f'INSERT INTO {table_name} ({cols_sql}) VALUES ({placeholders});'

        with conn.cursor() as cur:
            execute_batch(cur, sql, tuples, page_size=batch_size)
            # Insert corresponding outbox events so replication can pick these up.
            try:
                outbox_rows = []
                for r in rows:
                    # payload: use incoming dict as JSON; ensure it's a dict
                    payload = r if isinstance(r, dict) else {}
                    outbox_rows.append((str(uuid.uuid4()), table_name, 'upsert', Json(payload)))
                if outbox_rows:
                    execute_batch(cur, "INSERT INTO outbox_events (event_id, table_name, op, payload) VALUES (%s, %s, %s, %s);", outbox_rows, page_size=batch_size)
            except Exception:
                # don't fail the bulk insert if outbox insertion has issues; record/logging can be added
                pass
        conn.commit()

    def bulk_insert_doctors(self, conn, rows, batch_size=1000, upsert=True):
        """
        Insert or upsert into doctors.
        - conn: psycopg2 connection
        - rows: list[dict] where keys match DOCTOR_COLS (or variants)
        - upsert=True will do INSERT ... ON CONFLICT("Doctor_ID") DO UPDATE
        """
        # Normalize incoming rows into tuples matching DOCTOR_COLS
        tuples = []
        for r in rows:
            # support dict-like rows; normalize keys
            incoming = {re.sub(r"[^0-9a-z]", "", str(k).lower()): v for k, v in r.items()} if isinstance(r, dict) else {}
            values = []
            for col in DOCTOR_COLS:
                if isinstance(r, dict) and col in r:
                    values.append(r.get(col))
                    continue
                col_norm = re.sub(r"[^0-9a-z]", "", col.lower())
                values.append(incoming.get(col_norm))
            tuples.append(tuple(values))

        cols_sql = ", ".join(f'"{c}"' for c in DOCTOR_COLS)
        placeholders = ", ".join(["%s"] * len(DOCTOR_COLS))

        if upsert:
            update_assignments = ", ".join(f'"{c}" = EXCLUDED."{c}"' for c in DOCTOR_COLS if c != "Doctor_ID")
            sql = f"""
                INSERT INTO doctors ({cols_sql})
                VALUES ({placeholders})
                ON CONFLICT ("Doctor_ID") DO UPDATE SET
                {update_assignments};
            """
        else:
            sql = f'INSERT INTO doctors ({cols_sql}) VALUES ({placeholders});'

        with conn.cursor() as cur:
            execute_batch(cur, sql, tuples, page_size=batch_size)
            # Insert corresponding outbox events for doctors
            try:
                outbox_rows = []
                for r in rows:
                    payload = r if isinstance(r, dict) else {}
                    outbox_rows.append((str(uuid.uuid4()), 'doctors', 'upsert', Json(payload)))
                if outbox_rows:
                    execute_batch(cur, "INSERT INTO outbox_events (event_id, table_name, op, payload) VALUES (%s, %s, %s, %s);", outbox_rows, page_size=batch_size)
            except Exception:
                pass
        conn.commit()

    def loadDoctorData(self,conn):
        paths="./data/Doctors.csv"
        if isinstance(paths, (str, Path)):
            paths = [paths]

        rows = []
        for p in map(Path, paths):
            with p.open(newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    rows.append({k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in r.items()})
        print(rows)
        self.bulk_insert_doctors(conn, rows, batch_size=1000, upsert=True)


    def loadLocalData(self,conn):
        paths="./data/Patients_US-WEST.csv"
        if isinstance(paths, (str, Path)):
            paths = [paths]

        rows = []
        for p in map(Path, paths):
            with p.open(newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    rows.append({k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in r.items()})
        print(rows)
        self.bulk_insert_patients(conn, rows, batch_size=1000, upsert=True)
