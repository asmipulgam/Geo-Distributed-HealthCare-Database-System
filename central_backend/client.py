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
    "us-central": "",
    "us-east": "",
}
BACKUP_URLS = {
    "us-west": "",
    "us-central": "",
     "us-east": "",
}

# Patient Table columns
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


#Couple of helper functions for data formatting for CRUD ops
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
    for f in (fmt, "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(x, f).date().isoformat()
        except ValueError:
            continue
    return x

def to_str(x):
    return (x or "").strip() or None

def getFormattedURL(raw_url, useSecure = True):
        if useSecure:
            return f"{raw_url}?sslmode=verify-full"
        else:
            return f"{raw_url}?sslmode=disable"

#Parse the URL's and secrets from the config file
def init():
    config = configparser.ConfigParser()
    config.read('database.conf')
    LOCAL_URLS["us-east"] = config.get('DEFAULT', 'eastURL')
    #BACKUP_URLS["us-east"] = config.get('DEFAULT', 'remoteUSEastBackupURL')
    LOCAL_URLS["us-west"] = getFormattedURL(config.get('DEFAULT', 'westURL'))
    BACKUP_URLS["us-west"] = "us-east"
    LOCAL_URLS["us-central"] = getFormattedURL(config.get('DEFAULT', 'centralURL'))
    BACKUP_URLS["us-central"] = "us-east"
    print("Read Backend URLS")


class DBClient:
    #Python constructor
    def __init__(self):
        self.url = None
        init()
        with open('./us_state_regions.json', 'r') as f:
            self.region_map = json.load(f)
        self.connections = {}
        self.initConnections()
        print("west:" ,LOCAL_URLS["us-west"])
        
    # Initialize DB connections for all regions
    def initConnections(self):
        for region, url in LOCAL_URLS.items():
            try:
                if not url:
                    print(f"No URL configured for region {region}; skipping connection")
                    continue
                print(f"Connecting to {region} DB at {url}")
                conn = psycopg2.connect(url)
                self.connections[region] = conn
            except Exception as e:
                print(f"Warning: failed to connect to {region} at {url}: {e}")
        print("Initialized DB Connections", self.connections)

    # Purge and reconnect to the Cockroach clusters
    def reload_connections(self):
        statuses = {}
        # Close any existing connections
        for r, c in list(self.connections.items()):
            try:
                c.close()
            except Exception:
                pass
        self.connections.clear()
        for region, url in LOCAL_URLS.items():
            if not url:
                statuses[region] = {"ok": False, "error": "no url configured"}
                continue
            try:
                conn = psycopg2.connect(url)
                self.connections[region] = conn
                statuses[region] = {"ok": True}
            except Exception as e:
                statuses[region] = {"ok": False, "error": str(e)}

        return statuses
    
    #get Cockroach DSN . If exception/unable to connect get URL for backup/replica cluster, in this case east
    def get_connection_for_region(self, region_key, allow_backup=True):
        if not region_key:
            region_key = 'us-west'


        existing = self.connections.get(region_key)
        try:
            if existing and getattr(existing, 'closed', 1) == 0:
                return existing, region_key, False
        except Exception:
            pass

        primary_dsn = None
        try:
            primary_dsn = self.getURL({'region': region_key})
        except Exception:
            primary_dsn = None

        if primary_dsn:
            try:
                conn = psycopg2.connect(primary_dsn)
                return conn, region_key, True
            except Exception as e:
                print(f"Primary connect failed for {region_key}: {e}")

        if allow_backup:
            try:
                backup_dsn = self.__getReplicaURL({'region': region_key})
            except Exception:
                backup_dsn = None
            if backup_dsn:
                backup_url = None
                if isinstance(backup_dsn, str) and backup_dsn in LOCAL_URLS:
                    backup_url = LOCAL_URLS.get(backup_dsn)
                else:
                    backup_url = LOCAL_URLS.get(backup_dsn) or backup_dsn

                if backup_url:
                    try:
                        conn = psycopg2.connect(backup_url)
                        backup_region = None
                        for k, v in LOCAL_URLS.items():
                            if v == backup_url:
                                backup_region = k
                                break
                        if not backup_region and isinstance(backup_dsn, str) and backup_dsn in LOCAL_URLS:
                            backup_region = backup_dsn
                        return conn, backup_region or region_key, True
                    except Exception as e:
                        print(f"Backup connect failed for {region_key}: {e}")

        return None, None, False
    
    # Helper function which tells which region the user from a STATE belongs to
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
        return LOCAL_URLS.get(state)
    
    def __getReplicaURL(self,data):
        state = data.get("region")
        return BACKUP_URLS.get(state)

    #For basic Read operation, Get all details of the user on logging in
    def fetchUserData(self, user_id,state):
        try:
            url = self.getURLFromState({"state":state})
            conn = psycopg2.connect(url)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                select_sql = 'SELECT p.*, d."Doctor_Name" AS doctor_name, d."Hospital" AS doctor_hospital, d."Region" AS doctor_region'
                region_for_state = self.region_map.get(state)
                table_name = ('patients_west' if (region_for_state and region_for_state.endswith('west')) else 'patients_central')
                select_sql += f' FROM {table_name} p LEFT JOIN doctors d ON p."Doctor_ID" = d."Doctor_ID"'
                select_sql += ' WHERE p."Patient_ID" = %s AND p."State" = %s LIMIT 1;'
                t0 = time.time()
                cur.execute(select_sql, (user_id, state))
                row = cur.fetchone()
                select_time_ms = int((time.time() - t0) * 1000)

                if row:
                    return dict(row)
                else:
                    return {"error": "User not found", "metrics": {"select_time_ms": select_time_ms, "rows": 0}}, 404
        except Exception as e:
            return {"error": str(e)}

    #Function to fetch patients table based on the filters provided
    def search_patients(self, filters=None, region='us-west', limit=1000, center_lat=None, center_lon=None, donor_only=False):
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
                continue
            if op not in allowed_ops:
                continue

            if op == 'IN':
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
        if donor_only:
            where_parts.append('"is_organ_donor" = %s')
            params.append(True)

        where_expr = ' AND '.join(where_parts) if where_parts else ''
        where_clause = (' WHERE ' + where_expr) if where_expr else ''
        def _patients_table_for_region(region_key):
            if not region_key:
                return 'patients_central'
            suffix = region_key.split('-')[-1]
            if suffix == 'west':
                return 'patients_west'
            return 'patients_central'

        table_name = _patients_table_for_region(region)
        print("2")
        use_distance = (center_lat is not None and center_lon is not None)
        if use_distance:
            cols_sql = ', '.join(f'"{c}"' for c in COLS)
            cols_sql = cols_sql + ", " + f"haversine_km(\"lat\", \"lon\", %s, %s) AS distance_km"
            if where_clause:
                sql = f'SELECT {cols_sql} FROM {table_name}{where_clause} AND "lat" IS NOT NULL AND "lon" IS NOT NULL ORDER BY distance_km ASC LIMIT %s;'
            else:
                sql = f'SELECT {cols_sql} FROM {table_name} WHERE "lat" IS NOT NULL AND "lon" IS NOT NULL ORDER BY distance_km ASC LIMIT %s;'
            params.insert(0, center_lon) 
            params.insert(0, center_lat)
            params.append(limit)
        else:
            cols_sql = ', '.join(f'"{c}"' for c in COLS)
            sql = f'SELECT {cols_sql} FROM {table_name}{where_clause} ORDER BY "Patient_ID" LIMIT %s;'
            params.append(limit)
        print("3")

        conn = self.connections.get(region)
        created_conn = False
        used_region = region
        try:
            if conn is None:
                conn, used_region, created_conn = self.get_connection_for_region(region, allow_backup=True)
            if conn is None:
                raise RuntimeError(f"No DB connection available for region {region}")

            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()
                print("7")
                return [dict(r) for r in rows]
        except Exception as e:
            print("8")
            try:
                print(f"Primary DB request for region '{region}' failed: {e}. Attempting fallback to 'us-east'.")
                try:
                    if created_conn and conn is not None:
                        conn.close()
                except Exception:
                    pass
                try:
                    fb_conn, fb_region, fb_created = self.get_connection_for_region('us-east', allow_backup=True)
                except Exception:
                    fb_conn = None
                    fb_created = False

                if not fb_conn:
                    raise

                try:
                    with fb_conn.cursor(cursor_factory=RealDictCursor) as cur2:
                        cur2.execute(sql, params)
                        rows = cur2.fetchall()
                        return [dict(r) for r in rows]
                finally:
                    try:
                        if fb_created and fb_conn is not None:
                            fb_conn.close()
                    except Exception:
                        pass
            except Exception:
                raise
        finally:
            try:
                if created_conn and conn is not None:
                    conn.close()
            except Exception:
                pass

    # This function is periodically run by the replicators so as to process any pending changes and propagate to the intended target clusters
    def replicate_outbox_events(self):
        print(" Starting replication loop...")
        primary_region = 'us-west'
        while True:
            try:
                primary_dsn = self.getURL({"region": primary_region})
                backup_dsn = self.__getReplicaURL({"region": primary_region})
                src_conn = None
                repl_dsn = None
                try:
                    if primary_dsn:
                        src_conn = psycopg2.connect(primary_dsn)
                        repl_dsn = backup_dsn
                    else:
                        raise Exception("no primary dsn")
                except Exception:
                    if backup_dsn:
                        try:
                            src_conn = psycopg2.connect(backup_dsn)
                            repl_dsn = primary_dsn
                        except Exception as e:
                            print("Neither primary nor backup reachable for replication pair:", e)
                            time.sleep(5)
                            continue
                    else:
                        time.sleep(5)
                        continue

                src_cur = src_conn.cursor()
                print("Connected to Source")
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
                    time.sleep(5)
                    continue
                if not repl_dsn:
                    print("No replica DSN configured for this replication pair; skipping until configured")
                    src_cur.close(); src_conn.close()
                    time.sleep(5)
                    continue
                repl_conn = psycopg2.connect(repl_dsn)
                repl_cur  = repl_conn.cursor()

                for event_id, table, op, payload in events:
                    print(f"Processing event {event_id} op={op} table={table}")
                    try:
                        if isinstance(payload, str):
                            try:
                                patient = json.loads(payload)
                            except Exception:
                                patient = payload
                        else:
                            patient = payload
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

                        if op == "upsert":
                            if table and str(table).startswith('patients'):
                                if str(table).startswith('patients_'):
                                    table_name = table
                                else:
                                    region_key = None
                                    if isinstance(patient, dict):
                                        region_key = patient.get('Region') or self.region_map.get(patient.get('State'))
                                    table_name = ('patients_west' if (region_key and str(region_key).endswith('west')) else 'patients_central')
                                cols_sql = ", ".join(f'"{c}"' for c in COLS)
                                placeholders = ", ".join(["%s"] * len(COLS))
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
                                print(f" Skipping unknown table in outbox: {table}")
                        elif op == "delete":
                            if table and str(table).startswith('patients'):
                                pid = None
                                state_val = None
                                if isinstance(patient, dict):
                                    pid = patient.get("Patient_ID") or patient.get("id")
                                    state_val = patient.get("State")
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

                        src_cur.execute("UPDATE outbox_events SET processed = true WHERE event_id = %s;", (event_id,))

                    except Exception as e:
                        print(f" Failed event {event_id}: {e}")

                repl_conn.commit()
                src_conn.commit()
                print(f" Replicated {len(events)} events.")

                src_cur.close(); repl_cur.close()
                src_conn.close(); repl_conn.close()

            except Exception as e:
                print(" Replication error:", e)
                time.sleep(5)

    # Data formatter
    def row_to_tuple(self,r):
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
    

    # Function to insery/update new record. C/U in CRUD
    def insert_patient_new(self, row, upsert=True):
        if isinstance(row, dict):
            incoming = {}
            for k, v in row.items():
                norm = re.sub(r"[^0-9a-z]", "", str(k).lower())
                incoming[norm] = v

            normalized_row = {}
            for col in COLS:
                col_norm = re.sub(r"[^0-9a-z]", "", col.lower())
                if col_norm in incoming:
                    normalized_row[col] = incoming[col_norm]
                else:
                    normalized_row[col] = row.get(col)
        else:
            normalized_row = row
        print("CP1")

        tup = self.row_to_tuple(normalized_row)

        cols_sql = ", ".join(f'"{c}"' for c in COLS)
        placeholders = ", ".join(["%s"] * len(COLS))

        print(f"CP2, {cols_sql},{tup}")
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

        preferred_region = normalized_row.get('Region') or self.region_map.get(normalized_row.get('State'))
        conn, used_region, created_conn = self.get_connection_for_region(preferred_region, allow_backup=True)
        print("CP5 ", conn, "used_region:", used_region, "created_conn:", created_conn)

        print(f"Executing SQL: {sql} with values {tup} into {conn}")

        metrics = {
            "insert_time_ms": None,
            "outbox_time_ms": None,
            "rows": None,
        }

        if conn is None:
            return {"status": "error", "message": "No available DB connection for region", "metrics": metrics}

        try:
            t0 = time.time()
            with conn.cursor() as cur:
                cur.execute(sql, tup)
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
            return {"status": "error", "message": str(e), "metrics": metrics}
        finally:
            try:
                if created_conn and conn is not None:
                    conn.close()
            except Exception:
                pass

    # Function to bulk upload data using psycopg2's execute_batch for better performance
    def bulk_insert_patients(self,conn, rows, batch_size=1000, upsert=True):
        tuples = [self.row_to_tuple(r) for r in rows]

        cols_sql = ", ".join(f'"{c}"' for c in COLS)
        placeholders = ", ".join(["%s"] * len(COLS))
        first_region = (rows[0].get('Region') if rows and isinstance(rows[0], dict) else None)
        table_name = ("patients_west" if (first_region and str(first_region).endswith('west')) else "patients_central")

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
        else:
            sql = f'INSERT INTO {table_name} ({cols_sql}) VALUES ({placeholders});'
        created_conn = False
        if conn is None:
            conn, used_region, created_conn = self.get_connection_for_region(first_region, allow_backup=True)
        if conn is None:
            raise RuntimeError("No available DB connection for bulk insert")
        
        print("Bulk insert SQL:", sql,"Into conn: ",conn)

        with conn.cursor() as cur:
            execute_batch(cur, sql, tuples, page_size=batch_size)
            try:
                outbox_rows = []
                for r in rows:
                    payload = r if isinstance(r, dict) else {}
                    outbox_rows.append((str(uuid.uuid4()), table_name, 'upsert', Json(payload)))
                if outbox_rows:
                    execute_batch(cur, "INSERT INTO outbox_events (event_id, table_name, op, payload) VALUES (%s, %s, %s, %s);", outbox_rows, page_size=batch_size)
            except Exception:
                pass
        conn.commit()
        try:
            if created_conn and conn is not None:
                conn.close()
        except Exception:
            pass
        print("Bulk insert complete")

    # Function to bulk insert/update doctors data
    def bulk_insert_doctors(self, conn, rows, batch_size=1000, upsert=True, region="us-west"):
        tuples = []
        for r in rows:
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

        created_conn = False
        if conn is None:
            conn, used_region, created_conn = self.get_connection_for_region(region, allow_backup=True)
        if conn is None:
            raise RuntimeError("No available DB connection for bulk insert doctors")

        with conn.cursor() as cur:
            execute_batch(cur, sql, tuples, page_size=batch_size)
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
        try:
            if created_conn and conn is not None:
                conn.close()
        except Exception:
            pass

    # Function to load doctors data from CSV file
    # Not used directly, just for quick initial load or in testing
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


    # Function to load doctors data from CSV file
    # Not used directly, just for quick initial load or in testing
    def loadLocalData(self,conn):
        paths="./data/Patients_US-CENTRAL.csv"
        if isinstance(paths, (str, Path)):
            paths = [paths]

        rows = []
        for p in map(Path, paths):
            with p.open(newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    rows.append({k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in r.items()})
        #print(rows)
        self.bulk_insert_patients(conn, rows, batch_size=1000, upsert=True)
