
import threading
import time
import requests

class HealthChecker:
    def __init__(self, urls, callback=None):
        self.urls = urls
        self.health_results = {url: None for url in urls}
        self.results_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = None
        self.callback = callback

    def check_url(self, url):
        try:
            response = requests.get(url, timeout=5)
            result = {
                "status_code": response.status_code,
                "ok": response.ok,
                "body": response.text,
                "timestamp": time.time(),
            }
        except Exception as e:
            result = {
                "status_code": None,
                "ok": False,
                "body": str(e),
                "timestamp": time.time(),
            }
        with self.results_lock:
            self.health_results[url] = result

    def health_check_worker(self):
        while not self._stop_event.is_set():
            threads = []
            for url in self.urls:
                t = threading.Thread(target=self.check_url, args=(url,))
                t.start()
                threads.append(t)
            for t in threads:
                t.join()
            # Wait 1 minute or until stop event
            self._stop_event.wait(60)

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
    # Example usage: pass URLs as parameter
    LOCAL_URLS = [
        "http://localhost:5000/ping",
        # Add more URLs as needed
    ]
    checker = HealthChecker(LOCAL_URLS)
    checker.start()
    print("Health checks started. Press Ctrl+C to exit.")
    try:
        while True:
            results = checker.get_results()
            for url, result in results.items():
                print(f"{url}: {result}")
            time.sleep(10)
    except KeyboardInterrupt:
        checker.stop()
        print("Exiting...")
