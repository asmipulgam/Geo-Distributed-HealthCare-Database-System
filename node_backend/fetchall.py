"""
Simple pagination helper for node backend.
Provides FetchAll class which connects to CockroachDB (Postgres-compatible) and
returns page results from `patients` table as JSON-friendly dicts.

Usage:
    fetcher = FetchAll(dsn="postgresql://root@localhost:26257/west?sslmode=disable")
    page = fetcher.fetch(cursor=0, dir='next', page_size=20)
    # page -> {'records': [...], 'nextIndex': 20 or None, 'prevIndex': 0 or None, 'count': total}

This is intentionally simple (offset-based pagination) for demonstration purposes.
For production/useful systems consider keyset-pagination for large tables.
"""

from typing import Optional, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor

# Column order used in app.py; returned dicts will include these keys
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

DEFAULT_DSN = "postgresql://root@localhost:26257/west?sslmode=disable"


class FetchAll:
    def __init__(self, dsn: Optional[str] = None):
        self.dsn = dsn or DEFAULT_DSN
        self.conn = None

    def _connect(self):
        if self.conn is None or self.conn.closed:
            self.conn = psycopg2.connect(self.dsn)

    def close(self):
        if self.conn:
            try:
                self.conn.close()
            finally:
                self.conn = None

    def fetch(self, cursor: Optional[int] = 0, dir: str = "next", page_size: int = 20) -> Dict[str, Any]:
        """
        Fetch a page of rows from patients.
        - cursor: offset index (int). If None or 0, starts at beginning.
        - dir: 'next' or 'prev'. For 'prev' the returned prevIndex will be max(0, cursor-page_size).
        - page_size: number of rows to return.

        Returns dict with keys: records (list of dicts), nextIndex (int or None), prevIndex (int or None), count (total rows)
        """
        self._connect()
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            # total count to determine next existence
            cur.execute("SELECT COUNT(*) AS cnt FROM patients;")
            total = cur.fetchone()["cnt"] or 0

            try:
                offset = int(cursor or 0)
            except Exception:
                offset = 0

            # Treat `cursor` as the explicit offset to fetch. Caller should pass the
            # prevIndex/nextIndex returned by earlier responses. The `dir` parameter
            # is ignored to avoid double-adjusting the offset.
            offset = max(0, offset)

            # Defensive: don't request beyond total
            if offset >= total and total > 0:
                # clamp to last full page
                last_page = max(0, (total - 1) // page_size * page_size)
                offset = last_page

            cur.execute(
                f"SELECT {', '.join('"' + c + '"' for c in COLS)} FROM patients ORDER BY id LIMIT %s OFFSET %s;",
                (page_size, offset),
            )
            rows = cur.fetchall()

            # compute next/prev indices
            next_offset = offset + page_size
            nextIndex = next_offset if next_offset < total else None
            prevIndex = offset - page_size if offset - page_size >= 0 else (0 if offset > 0 else None)

            # Convert RealDictRows to normal dicts and ensure keys present
            records = []
            for r in rows:
                rec = {k: r.get(k) for k in COLS}
                records.append(rec)

        return {
            "records": records,
            "nextIndex": nextIndex,
            "prevIndex": prevIndex,
            "count": total,
            "offset": offset,
        }


if __name__ == "__main__":
    f = FetchAll()
    print(f.fetch(0, "next", 5))
    f.close()
