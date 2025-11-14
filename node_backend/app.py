from flask import Flask, json, request, jsonify
import configparser
import socket
import argparse
import psycopg2
import re
import uuid
from psycopg2.extras import Json
import time
from fetchall import FetchAll

app = Flask(__name__)
REGIONMAP= {
    "central": 5000,
    "east": 5001,
    "west": 5002
}

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
    status = pingDB()
    return jsonify({"status": status, "region": region}), 200

@app.post("/addData")
def addData():
    data = request.json
    try:
        # Expect a JSON object representing a single patient row
        insert_patient(dbConnection, data)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

def insert_patient_new(conn, row, upsert=True):
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

    tup = row_to_tuple(normalized_row)

    cols_sql = ", ".join(f'"{c}"' for c in COLS)
    placeholders = ", ".join(["%s"] * len(COLS))

    if upsert:
        update_assignments = ", ".join(
            f'"{c}" = EXCLUDED."{c}"' for c in COLS if c != "id"
        )
        sql = f"""
            INSERT INTO patients ({cols_sql})
            VALUES ({placeholders})
            ON CONFLICT ("id") DO UPDATE SET
            {update_assignments};
        """
    else:
        sql = f'INSERT INTO patients ({cols_sql}) VALUES ({placeholders});'

    with conn.cursor() as cur:
        cur.execute(sql, tup)
    conn.commit()
    with conn.cursor() as curr:
        curr.execute("""
            INSERT INTO outbox_events (event_id, table_name, op,payload)
                     VALUES (%s, %s, %s, %s);
        """, (str(uuid.uuid4()), "patients", "upsert", Json(normalized_row)))
    conn.commit()
    replicate_outbox_events()


def pingDB():
    try:
        cursor = dbConnection.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        if result and result[0] == 1:
            return True
        else:
            return False
    except Exception as e:
        print(f"Database ping failed: {e}")
        return False
    
def createTable():
    try:
        cursor = dbConnection.cursor()
        create_table_query = """
            CREATE TABLE IF NOT EXISTS patients (
  "id" STRING PRIMARY KEY,
  "first_name" STRING,
  "last_name" STRING,
  "email" STRING,
  "Phone number" STRING,
  "weight" STRING,
  "age" STRING,
  "gender" STRING,
  "Prefix" STRING,
  "Martial Status" STRING,
  "Address" STRING,
  "City" STRING,
  "State" STRING,
  "Hospital Name" STRING,
  "Hostipal Address" STRING,
  "Region" STRING,
  "Visit Date" DATE,
  "Treatement" STRING,
  "Doctor Appointed" STRING,
  "Number of Doctors Appointed" STRING,
  "Doctor's Contact" STRING,
  "Allergies" STRING,
  "Height" STRING
);
        """
        cursor.execute(create_table_query)
        dbConnection.commit()
    except Exception as e:
        print(f"Table creation failed: {e}")

import csv
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_batch
from datetime import datetime
from decimal import Decimal

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
            return datetime.strptime(x, f).date()
        except ValueError:
            continue
    # fall back: let DB try STRING → DATE cast, or raise
    return x

def to_str(x):
    return (x or "").strip() or None

# --- order of columns as in the table ---
COLS = [
    "id",
    "first_name",
    "last_name",
    "email",
    "Phone number",
    "weight",
    "age",
    "gender",
    "Prefix",
    "Martial Status",
    "Address",
    "City",
    "State",
    "Hospital Name",
    "Hostipal Address",
    "Region",
    "Visit Date",
    "Treatement",
    "Doctor Appointed",
    "Number of Doctors Appointed",
    "Doctor's Contact",
    "Allergies",
    "Height",
]

def row_to_tuple(r):
    """Map a CSV dict row to a positional tuple matching COLS (with type coercion)."""
    return (
        to_str(r.get("id")),
        to_str(r.get("first_name")),
        to_str(r.get("last_name")),
        to_str(r.get("email")),
        to_str(r.get("Phone number")),
        to_str(r.get("weight")),
        to_int(r.get("age")),
        to_str(r.get("gender")),
        to_str(r.get("Prefix")),
        to_str(r.get("Martial Status")),
        to_str(r.get("Address")),
        to_str(r.get("City")),
        to_str(r.get("State")),
        to_str(r.get("Hospital Name")),
        to_str(r.get("Hostipal Address")),
        to_str(r.get("Region")),
        to_date(r.get("Visit Date")),  # expects YYYY-MM-DD by default; see to_date()
        to_str(r.get("Treatement")),
        to_str(r.get("Doctor Appointed")),
        to_str(r.get("Number of Doctors Appointed")),
        to_str(r.get("Doctor's Contact")),
        to_str(r.get("Allergies")),
        to_str(r.get("Height")),
    )

def bulk_insert_patients(conn, rows, batch_size=1000, upsert=True):
    """
    Insert or upsert into patients.
    - conn: psycopg2 connection
    - rows: list[dict] from load_csv_rows()
    - upsert=True will do INSERT ... ON CONFLICT(id) DO UPDATE
    """
    tuples = [row_to_tuple(r) for r in rows]

    cols_sql = ", ".join(f'"{c}"' for c in COLS)
    placeholders = ", ".join(["%s"] * len(COLS))

    if upsert:
        # Update all mutable columns on conflict; leave id intact
        update_assignments = ", ".join(
            f'"{c}" = EXCLUDED."{c}"' for c in COLS if c != "id"
        )
        sql = f"""
            INSERT INTO patients ({cols_sql})
            VALUES ({placeholders})
            ON CONFLICT ("id") DO UPDATE SET
            {update_assignments};
        """
    else:
        sql = f'INSERT INTO patients ({cols_sql}) VALUES ({placeholders});'

    with conn.cursor() as cur:
        execute_batch(cur, sql, tuples, page_size=batch_size)
    conn.commit()


def insert_patient(conn, row, upsert=True):
    """
    Insert a single patient row (dict) into patients table.
    - conn: psycopg2 connection
    - row: dict matching column names in COLS
    - upsert: if True, perform ON CONFLICT DO UPDATE for non-id columns
    """
    tup = row_to_tuple(row)

    cols_sql = ", ".join(f'"{c}"' for c in COLS)
    placeholders = ", ".join(["%s"] * len(COLS))

    if upsert:
        update_assignments = ", ".join(
            f'"{c}" = EXCLUDED."{c}"' for c in COLS if c != "id"
        )
        sql = f"""
            INSERT INTO patients ({cols_sql})
            VALUES ({placeholders})
            ON CONFLICT ("id") DO UPDATE SET
            {update_assignments};
        """
    else:
        sql = f'INSERT INTO patients ({cols_sql}) VALUES ({placeholders});'

    with conn.cursor() as cur:
        cur.execute(sql, tup)
    conn.commit()
    replicate_outbox_events()


def loadLocalData(conn):
    paths="./WEST.csv"
    if isinstance(paths, (str, Path)):
        paths = [paths]

    rows = []
    for p in map(Path, paths):
        with p.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows.append({k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in r.items()})
    print(rows)
    bulk_insert_patients(conn, rows, batch_size=1000, upsert=True)


def replicate_outbox_events():
    """
    Polls outbox_events, sends new rows to replica DB, and marks processed ones.
    """
    print(" Starting replication loop...")
    SOURCE_DSN = "postgresql://root@localhost:26257/west?sslmode=disable"
    REPLICA_DSN = "postgresql://root@localhost:26260/west?sslmode=disable"
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

                    # normalize patient mapping: prefer exact column keys, else try a normalized key match
                    def build_values_map(patient_obj):
                        if not isinstance(patient_obj, dict):
                            raise ValueError("payload is not a JSON object")
                        # build normalized lookup for incoming keys
                        incoming = {re.sub(r"[^0-9a-z]", "", str(k).lower()): v for k, v in patient_obj.items()}
                        values = []
                        for col in COLS:
                            if col in patient_obj:
                                values.append(patient_obj.get(col))
                                continue
                            col_norm = re.sub(r"[^0-9a-z]", "", col.lower())
                            values.append(incoming.get(col_norm))
                        return tuple(values)

                    if op == "upsert":
                        cols_sql = ", ".join(f'"{c}"' for c in COLS)
                        placeholders = ", ".join(["%s"] * len(COLS))
                        update_assignments = ",\n        ".join(
                            f'"{c}" = EXCLUDED."{c}"' for c in COLS if c != "id"
                        )

                        values = build_values_map(patient)

                        sql = f"""
                            INSERT INTO patients ({cols_sql})
                            VALUES ({placeholders})
                            ON CONFLICT ("id") DO UPDATE SET
                            {update_assignments};
                        """

                        repl_cur.execute(sql, values)
                    elif op == "delete":
                        # for delete we expect an id field
                        pid = patient.get("id") if isinstance(patient, dict) else None
                        repl_cur.execute("DELETE FROM patients WHERE id = %s;", (pid,))

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

    fetcher = FetchAll()
    try:
        page = fetcher.fetch(cursor=cursor, dir=dir, page_size=page_size)
        return jsonify(page), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        try:
            fetcher.close()
        except Exception:
            pass


if __name__ == "__main__":
    # Run the Flask development server
    parse = argparse.ArgumentParser(description="Choose Region")
    parse.add_argument("--region", choices=["east", "west", "central"], default="west")
    args = parse.parse_args()
    region = args.region
    confFile = f"node_backend/database.{region}.conf"
    dbConnection = psycopg2.connect(dsn="postgresql://root@localhost:26257/west?sslmode=disable",connect_timeout=10)
    print(dbConnection)
    #createTable()
    #loadLocalData(dbConnection)

#     data = {
#   "id": "99999",
#   "first_name": "Cinda",
#   "last_name": "Klimowicz",
#   "email": "cklimowicz0@ameblo.jp",
#   "Phone number": "427-676-7930",
#   "weight": "121",
#   "age": "86",
#   "gender": "Female",
#   "Prefix": "Miss",
#   "Martial Status": "Single",
#   "Address": "07 Marcy Point",
#   "City": "Portland",
#   "State": "California",
#   "Hospital Name": "Mountain View Medical Center",
#   "Hostipal Address": "26285 BERG RD APT 276",
#   "Region": "West",
#   "Visit Date": "2025-05-05",
#   "Treatement": "herbal remedies",
#   "Doctor Appointed": "Cinda Klimowicz",
#   "Number of Doctors Appointed": "1",
#   "Doctor's Contact": "175-244-2423",
#   "Allergies": "peanuts",
#   "Height": "8"
#     }
#     insert_patient_new(dbConnection, data)
    app.run(host="0.0.0.0", port=5001, debug=True)