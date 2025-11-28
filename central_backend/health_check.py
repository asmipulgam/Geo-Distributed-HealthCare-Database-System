import threading
import time
import psycopg2
from psycopg2 import OperationalError, InterfaceError, DatabaseError
from typing import Dict, Optional, List
import json
from collections import deque
from pathlib import Path
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except Exception:
    MATPLOTLIB_AVAILABLE = False


# This code is responsible for checking periodically if all the cluster instances are active or not
# not rigidly integrated into the dashboard, but can be extended to build many useful monitoring features and metrics.
class HealthChecker:
    def __init__(self, dsn: str, interval: float = 2.0, connect_timeout: float = 2.0, name: str = "db"):
        self._dsn = dsn
        self._interval = interval
        self._connect_timeout = connect_timeout
        self._name = name
        self._ping_only = False

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
        if self._ping_only:
            # In ping-only mode we don't maintain a persistent connection
            return

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
            if self._ping_only:
                # Lightweight connect/close to probe availability
                dsn = self._dsn
                if "connect_timeout" not in dsn:
                    delim = "&" if "?" in dsn else "?"
                    dsn = f"{dsn}{delim}connect_timeout={int(self._connect_timeout)}"
                conn = None
                try:
                    conn = psycopg2.connect(dsn)
                    conn.close()
                    self._set_status(True, None)
                except (OperationalError, InterfaceError, DatabaseError) as e:
                    self._set_status(False, str(e))
                except Exception as e:
                    self._set_status(False, f"unexpected: {e}")
                finally:
                    try:
                        if conn is not None:
                            conn.close()
                    except Exception:
                        pass
            else:
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
        self._thread = None


class ClusterHealthMonitor:
    """Manage multiple HealthChecker instances, sample their statuses over
    time, persist metrics to disk and optionally render a PNG availability
    graph showing per-region uptime across the monitoring window.

    Usage:
      monitor = ClusterHealthMonitor({'us-west': dsn_west, 'us-central': dsn_central, 'us-east': dsn_east})
      monitor.start()
      ...
      metrics = monitor.get_metrics()
      monitor.generate_graph('availability.png')
    """

    def __init__(self, region_dsns: Dict[str, str], sample_interval: float = 5.0, retention_minutes: int = 60, storage_path: Optional[str] = None):
        self.region_dsns = dict(region_dsns)
        self.sample_interval = float(sample_interval)
        self.retention_seconds = int(retention_minutes * 60)
        self._checkers: Dict[str, HealthChecker] = {}
        self._lock = threading.Lock()
        # Use deque for efficient pops from left when trimming
        self._samples: deque = deque()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.storage_path = Path(storage_path) if storage_path else Path(__file__).with_name('health_metrics.json')
        # Pre-create checkers (use ping-only mode to avoid persistent connections)
        for name, dsn in self.region_dsns.items():
            chk = HealthChecker(dsn=dsn, interval=max(1.0, sample_interval / 2.0), name=name)
            # Enable ping-only probing to avoid keeping persistent DB connections
            chk._ping_only = True
            self._checkers[name] = chk

    def start(self):
        # start individual checkers
        for chk in self._checkers.values():
            try:
                chk.start()
            except Exception:
                pass

        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name='ClusterHealthMonitor', daemon=True)
        self._thread.start()

    def stop(self, join: bool = True, timeout: Optional[float] = 2.0):
        self._stop.set()
        if self._thread and join:
            self._thread.join(timeout=timeout)
        # stop inner checkers
        for chk in self._checkers.values():
            try:
                chk.stop(join=False)
            except Exception:
                pass

    def _sample(self):
        sample_time = time.time()
        status = {}
        for name, chk in self._checkers.items():
            try:
                s = chk.get_status()
                status[name] = bool(s.get('healthy'))
            except Exception:
                status[name] = False
        with self._lock:
            self._samples.append({'ts': sample_time, 'status': status})
            # prune old samples
            cutoff = sample_time - self.retention_seconds
            while self._samples and self._samples[0]['ts'] < cutoff:
                self._samples.popleft()

    def _run(self):
        # initial sample
        self._sample()
        while not self._stop.is_set():
            start = time.time()
            self._sample()
            # persist to disk periodically (every minute worth of samples)
            try:
                if len(self._samples) and (int(time.time()) % 60) < self.sample_interval:
                    self._persist()
            except Exception:
                pass
            self._stop.wait(max(0.0, self.sample_interval - (time.time() - start)))
        # final persist on stop
        try:
            self._persist()
        except Exception:
            pass

    def _persist(self):
        try:
            with self._lock:
                data = list(self._samples)
            tmp = self.storage_path.with_suffix('.tmp')
            tmp.write_text(json.dumps(data))
            tmp.replace(self.storage_path)
        except Exception:
            pass

    def get_metrics(self, since_seconds: Optional[int] = None) -> List[Dict]:
        with self._lock:
            data = list(self._samples)
        if since_seconds is None:
            return data
        cutoff = time.time() - since_seconds
        return [d for d in data if d['ts'] >= cutoff]

    def generate_graph(self, out_path: Optional[str] = None, width: int = 800, height: int = 300):
        """Render an availability graph to `out_path` (PNG). If matplotlib is
        not available this is a no-op.
        """
        if not MATPLOTLIB_AVAILABLE:
            return None
        samples = self.get_metrics()
        if not samples:
            return None
        # build time series per region
        regions = list(self.region_dsns.keys())
        times = [s['ts'] for s in samples]
        # convert to seconds offset for plotting
        t0 = times[0]
        xs = [ts - t0 for ts in times]
        ys = {r: [1.0 if s['status'].get(r) else 0.0 for s in samples] for r in regions}

        fig, ax = plt.subplots(figsize=(width/100.0, height/100.0), dpi=100)
        for r in regions:
            ax.step(xs, ys[r], where='post', label=r)
        ax.set_ylim(-0.1, 1.1)
        ax.set_xlabel('Seconds')
        ax.set_ylabel('Available (1/0)')
        ax.legend(loc='upper right')
        ax.grid(axis='x', linestyle='--', alpha=0.4)

        out = Path(out_path) if out_path else Path(__file__).with_name('availability.png')
        fig.tight_layout()
        try:
            fig.savefig(str(out))
            plt.close(fig)
            return str(out)
        except Exception:
            try:
                plt.close(fig)
            except Exception:
                pass
            return None


if __name__ == '__main__':
    # Simple CLI to run monitor against DSNs from environment/database.conf
    # Usage: python health_check.py
    import configparser

    config = configparser.ConfigParser()
    config.read('database.conf')
    dsns = {}
    try:
        dsns['us-east'] = config.get('DEFAULT', 'eastURL')
    except Exception:
        dsns['us-east'] = ''
    try:
        dsns['us-west'] = config.get('DEFAULT', 'westURL')
    except Exception:
        dsns['us-west'] = ''
    try:
        dsns['us-central'] = config.get('DEFAULT', 'centralURL')
    except Exception:
        dsns['us-central'] = ''

    monitor = ClusterHealthMonitor(dsns, sample_interval=5.0, retention_minutes=60)
    monitor.start()
    print('ClusterHealthMonitor started; sampling. Press Ctrl+C to exit.')
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('Stopping monitor...')
        monitor.stop()