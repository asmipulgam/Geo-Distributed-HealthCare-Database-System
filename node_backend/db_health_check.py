import threading
import time
import psycopg2

class CockroachDBHealthChecker:
    def __init__(self, db_configs, interval=60):
        """
        db_configs: list of dicts, each with connection params for a CockroachDB instance
        interval: health check interval in seconds
        """
        self.db_configs = db_configs
        self.interval = interval
        self.health_results = {i: None for i in range(len(db_configs))}
        self.results_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = None

    def check_db(self, idx, conn_params):
        try:
            with psycopg2.connect(**conn_params) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1;")
                    result = {
                        "healthy": True,
                        "timestamp": time.time(),
                        "error": None,
                    }
        except Exception as e:
            result = {
                "healthy": False,
                "timestamp": time.time(),
                "error": str(e),
            }
        with self.results_lock:
            self.health_results[idx] = result

    def health_check_worker(self):
        while not self._stop_event.is_set():
            threads = []
            for idx, conn_params in enumerate(self.db_configs):
                t = threading.Thread(target=self.check_db, args=(idx, conn_params))
                t.start()
                threads.append(t)
            for t in threads:
                t.join()
            self._stop_event.wait(self.interval)

    def start(self):
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(target=self.health_check_worker, daemon=True)
            self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join()

    def get_results(self):
        with self.results_lock:
            return dict(self.health_results)

if __name__ == "__main__":
    # Example: list of CockroachDB connection configs
    db_configs = [
        {
            "host": "localhost",
            "port": 26257,
            "user": "your_user",
            "password": "your_password",
            "dbname": "your_db",
            "sslmode": "disable",  # or "require" if using SSL
        },
        # Add more configs for backup/replica DBs
    ]
    checker = CockroachDBHealthChecker(db_configs, interval=60)
    checker.start()
    print("CockroachDB health checks started. Press Ctrl+C to exit.")
    try:
        while True:
            results = checker.get_results()
            for idx, result in results.items():
                print(f"DB {idx}: {result}")
            time.sleep(10)
    except KeyboardInterrupt:
        checker.stop()
        print("Exiting...")
