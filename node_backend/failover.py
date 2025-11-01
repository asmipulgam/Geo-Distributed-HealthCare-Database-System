# ft_mechanism.py
import threading
import time
import subprocess
from typing import Callable, Optional
import psycopg2

from health_checker import HealthChecker


# ------------------ helpers: schema & copy ------------------

DDL = """
CREATE TABLE IF NOT EXISTS kv_store (
  key TEXT PRIMARY KEY,
  value TEXT,
  updated_at TIMESTAMP DEFAULT now()
);
"""

def ensure_schema(dsn: str):
    conn = psycopg2.connect(dsn)
    conn.autocommit = True
    with conn, conn.cursor() as cur:
        cur.execute(DDL)
    conn.close()

def logical_copy(src_dsn: str, dst_dsn: str):
    """Very simple logical copy: kv_store only (demo)."""
    src = psycopg2.connect(src_dsn); src.autocommit = True
    dst = psycopg2.connect(dst_dsn); dst.autocommit = True
    ensure_schema(dst_dsn)
    with src.cursor() as rs, dst.cursor() as ws:
        rs.execute("SELECT key, value FROM kv_store")
        rows = rs.fetchmany(1000)
        while rows:
            for (k, v) in rows:
                ws.execute("""
                    INSERT INTO kv_store(key, value, updated_at)
                    VALUES (%s, %s, now())
                    ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now();
                """, (k, v))
            rows = rs.fetchmany(1000)
    src.close(); dst.close()


# ------------------ docker helpers (demo only) ------------------

def docker_run_single(name: str, sql_port: int, http_port: int, data_dir: str):
    """Start a single-node Cockroach (demo, --insecure)."""
    subprocess.call(["docker","rm","-f",name])  # clean old
    subprocess.call(["mkdir","-p", data_dir])
    cmd = [
        "docker","run","-d","--name",name,
        "-p", f"{sql_port}:26257","-p", f"{http_port}:8080",
        "-v", f"{data_dir}:/cockroach/cockroach-data",
        "cockroachdb/cockroach:v24.2.0",
        "start-single-node","--insecure","--accept-sql-without-tls"
    ]
    subprocess.check_call(cmd)


# ------------------ main FT Coordinator ------------------

class FaultToleranceCoordinator:
    """
    Monitors a primary & replica DB using in-memory health dicts.

    - If replica down: create new replica and copy from primary.
    - If primary down: promote replica to primary, create a new instance to replace the lost one,
      copy from promoted primary to new instance, then switch primary to the new instance.
    """

    def __init__(
        self,
        primary_dsn: str,
        replica_dsn: str,
        # creators produce DSNs for the new instances (after docker run completes)
        create_new_replica_dsns: Callable[[], str],
        create_new_primary_dsns: Callable[[], str],
        # optional: your own promote / switch hooks
        on_promote_replica_to_primary: Optional[Callable[[], None]] = None,
        on_switch_primary_to_new: Optional[Callable[[str], None]] = None,
        name: str = "coordinator",
        poll_interval: float = 1.0,
        fail_window: float = 5.0,
        cooldown: float = 30.0,
    ):
        self.primary_dsn = primary_dsn
        self.replica_dsn = replica_dsn
        self._create_new_replica_dsns = create_new_replica_dsns
        self._create_new_primary_dsns = create_new_primary_dsns
        self._on_promote = on_promote_replica_to_primary or (lambda: None)
        self._on_switch_new_primary = on_switch_primary_to_new or (lambda dsn: None)

        # health checkers
        self.hc_primary = HealthChecker(primary_dsn, name="primary")
        self.hc_replica = HealthChecker(replica_dsn, name="replica")

        # watcher thread
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

        # timers
        self._primary_unhealthy_since: Optional[float] = None
        self._replica_unhealthy_since: Optional[float] = None
        self._last_action_at: float = 0.0

        # params
        self._interval = poll_interval
        self._fail_window = fail_window
        self._cooldown = cooldown

        # current role DSNs (we may switch them at runtime)
        self._current_primary_dsn = primary_dsn
        self._current_replica_dsn = replica_dsn

    # ---------------- life cycle ----------------

    def start(self):
        ensure_schema(self.primary_dsn)
        ensure_schema(self.replica_dsn)
        self.hc_primary.start()
        self.hc_replica.start()
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name=f"FT-{self.__class__.__name__}", daemon=True)
        self._thread.start()

    def stop(self, join=True, timeout=2.0):
        self._stop.set()
        self.hc_primary.stop(join=join, timeout=timeout)
        self.hc_replica.stop(join=join, timeout=timeout)
        if join and self._thread:
            self._thread.join(timeout=timeout)

    # ---------------- actions ----------------

    def _cooldown_ok(self) -> bool:
        return (time.time() - self._last_action_at) >= self._cooldown

    def _mark_action(self):
        self._last_action_at = time.time()

    def _replica_down_flow(self):
        """
        Replica is unhealthy:
        1) Create a NEW replica instance (docker run)
        2) Copy data FROM current primary → new replica
        3) Switch our replica DSN to the new instance
        """
        if not self._cooldown_ok(): return
        print("[FT] Detected REPLICA down → rebuilding replica")
        self._mark_action()

        # 1) create new replica instance (you can docker-run here)
        new_replica_dsn = self._create_new_replica_dsns()
        # 2) copy from primary
        logical_copy(self._current_primary_dsn, new_replica_dsn)
        # 3) switch the health checker & coordinator to track new replica
        self.hc_replica.stop()
        self.hc_replica = HealthChecker(new_replica_dsn, name="replica")
        self.hc_replica.start()
        self._current_replica_dsn = new_replica_dsn
        print("[FT] Replica rebuilt and synchronized")

    def _primary_down_flow(self):
        """
        Primary is unhealthy:
        1) PROMOTE replica to PRIMARY (app-level role flip)
        2) Create NEW instance to REPLACE the failed primary
        3) Copy data FROM promoted primary → new instance
        4) SWITCH primary to new instance (so replica returns to being replica of the new primary)
        """
        if not self._cooldown_ok(): return
        print("[FT] Detected PRIMARY down → promoting replica and rebuilding primary")
        self._mark_action()

        # 1) promote replica to primary
        self._on_promote()  # your hook (e.g., update leader/epoch)
        promoted_primary_dsn = self._current_replica_dsn
        self._current_primary_dsn = promoted_primary_dsn

        # 2) create new replacement instance
        new_primary_dsn = self._create_new_primary_dsns()

        # 3) copy from promoted primary -> new instance
        logical_copy(promoted_primary_dsn, new_primary_dsn)

        # 4) switch primary to the NEW instance (hand back leadership)
        self._on_switch_new_primary(new_primary_dsn)  # your hook if you track leader externally
        self._current_primary_dsn = new_primary_dsn

        # and re-assign replica to track the promoted node as replica again (optional)
        # here we choose to keep the promoted node as REPLICA now:
        self._current_replica_dsn = promoted_primary_dsn

        # restart health checkers on new DSNs
        self.hc_primary.stop(); self.hc_replica.stop()
        self.hc_primary = HealthChecker(self._current_primary_dsn, name="primary")
        self.hc_replica = HealthChecker(self._current_replica_dsn, name="replica")
        self.hc_primary.start(); self.hc_replica.start()

        print("[FT] Primary rebuilt, data copied, leadership handed to the new primary")

    # ---------------- main loop ----------------

    def _run(self):
        while not self._stop.is_set():
            now = time.time()

            # check primary
            p = self.hc_primary.get_status()["healthy"]
            if p:
                self._primary_unhealthy_since = None
            else:
                if self._primary_unhealthy_since is None:
                    self._primary_unhealthy_since = now
                if (now - self._primary_unhealthy_since) >= self._fail_window:
                    self._primary_down_flow()
                    self._primary_unhealthy_since = None  # reset window

            # check replica
            r = self.hc_replica.get_status()["healthy"]
            if r:
                self._replica_unhealthy_since = None
            else:
                if self._replica_unhealthy_since is None:
                    self._replica_unhealthy_since = now
                if (now - self._replica_unhealthy_since) >= self._fail_window:
                    self._replica_down_flow()
                    self._replica_unhealthy_since = None

            self._stop.wait(self._interval)
