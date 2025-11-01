# health_checker.py
import threading
import time
import psycopg2
from psycopg2 import OperationalError, InterfaceError, DatabaseError
from typing import Dict, Optional


class HealthChecker:
    def __init__(self, dsn: str, interval: float = 2.0, connect_timeout: float = 2.0, name: str = "db"):
        self._dsn = dsn
        self._interval = interval
        self._connect_timeout = connect_timeout
        self._name = name

        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

        self._status: Dict[str, Optional[object]] = {
            "healthy": False,
            "timestamp": 0.0,
            "error": "not started",
            "name": self._name,
        }

        self._conn = None

    def _set_status(self, healthy: bool, err: Optional[str] = None):
        with self._lock:
            self._status = {
                "healthy": healthy,
                "timestamp": time.time(),
                "error": err,
                "name": self._name,
            }

    def get_status(self) -> Dict[str, Optional[object]]:
        with self._lock:
            return dict(self._status)

    def _ensure_connection(self):
        if self._conn is not None:
            try:
                with self._conn.cursor() as c:
                    c.execute("SELECT 1;")
                    c.fetchone()
                return
            except Exception:
                try:
                    self._conn.close()
                except Exception:
                    pass
                self._conn = None

        dsn = self._dsn
        if "connect_timeout" not in dsn:
            delim = "&" if "?" in dsn else "?"
            dsn = f"{dsn}{delim}connect_timeout={int(self._connect_timeout)}"

        self._conn = psycopg2.connect(dsn)
        self._conn.autocommit = True

    def _tick(self):
        try:
            self._ensure_connection()
            with self._conn.cursor() as c:
                c.execute("SELECT 1;")
                c.fetchone()
            self._set_status(True, None)
        except (OperationalError, InterfaceError, DatabaseError) as e:
            self._set_status(False, str(e))
        except Exception as e:
            self._set_status(False, f"unexpected: {e}")

    def _run(self):
        self._tick()
        while not self._stop.is_set():
            start = time.time()
            self._tick()
            self._stop.wait(max(0.0, self._interval - (time.time() - start)))

        try:
            if self._conn is not None:
                self._conn.close()
        except Exception:
            pass
        self._conn = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name=f"HealthChecker-{self._name}", daemon=True)
        self._thread.start()

    def stop(self, join: bool = True, timeout: Optional[float] = 2.0):
        self._stop.set()
        if join and self._thread:
            self._thread.join(timeout=timeout)
