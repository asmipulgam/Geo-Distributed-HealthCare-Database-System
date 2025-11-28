from typing import Optional, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor
import time


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


# Created a specialized clazz for Paginated Read functionality of CRUD. CockroachDB supports Paginated query results by default on large record size
# utilizing it fetch data in increments of 20. 
class FetchAll:
    #Python consutuctor
    def __init__(self, dsn: Optional[str] = None):
        self.dsn = dsn 
        self.conn = None
        self.table_name = 'patients_central'

    # Create new connection to the DB
    def _connect(self):
        if self.conn is None or self.conn.closed:
            self.conn = psycopg2.connect(self.dsn)

    # Close the DB cursor connection
    def close(self):
        if self.conn:
            try:
                self.conn.close()
            finally:
                self.conn = None

    # So this is the main function which fetches paginated results. cursor represents the current offset, dir is next/prev whether to see last/previous 20 records from the current display subset
    # next indicates next page/next 20. page_size is the number of records to fetch in each page. Can modify here for different limit
    def fetch(self, cursor: Optional[int] = 0, dir: str = "next", page_size: int = 20) -> Dict[str, Any]:
        self._connect()
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            # total count to determine next existence
            cur.execute(f"SELECT COUNT(*) AS cnt FROM {self.table_name};")
            total = cur.fetchone()["cnt"] or 0
            print("1")

            try:
                offset = int(cursor or 0)
            except Exception:
                offset = 0

            offset = max(0, offset)

            if offset >= total and total > 0:
                last_page = max(0, (total - 1) // page_size * page_size)
                offset = last_page
            select_sql = f"SELECT {', '.join('\"' + c + '\"' for c in COLS)} FROM {self.table_name} ORDER BY \"Patient_ID\" LIMIT %s OFFSET %s;"
            
            t0 = time.time()
            cur.execute(select_sql, (page_size, offset))
            rows = cur.fetchall()
            select_time_ms = int((time.time() - t0) * 1000)
            next_offset = offset + page_size
            nextIndex = next_offset if next_offset < total else None
            prevIndex = offset - page_size if offset - page_size >= 0 else (0 if offset > 0 else None)
            records = []
            for r in rows:
                rec = {k: r.get(k) for k in COLS}
                records.append(rec)

            # Metrics can be integrated here. Have madte it currently, but future scope enables to provide efficient calculations
            metrics = {
                "select_time_ms": select_time_ms,
                "rows": len(rows),
                "explain_time_ms": 0,
                "explain": 0,
            }

        return {
            "records": records,
            "nextIndex": nextIndex,
            "prevIndex": prevIndex,
            "count": total,
            "offset": offset,
            "metrics": metrics,
        }


if __name__ == "__main__":
    f = FetchAll()
    print(f.fetch(0, "next", 5))
    f.close()
