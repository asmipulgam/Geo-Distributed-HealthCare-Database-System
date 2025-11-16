import threading
import time
from typing import Callable, Any, Optional, Tuple, Dict

class Replicator:
    """
    Run a target callable repeatedly in a background thread with a fixed delay.

    Example:
        def work():
            print("doing work", time.time())

        r = Replicator(work, interval=2.0, run_on_start=True)
        r.start()
        time.sleep(6)
        r.stop()
    """

    def __init__(
        self,
        target: Callable[..., Any],
        interval: float = 5000.0,
        args: Optional[Tuple[Any, ...]] = None,
        kwargs: Optional[Dict[str, Any]] = None,
        run_on_start: bool = False,
        name: Optional[str] = None,
        daemon: bool = True,
    ):
        if interval < 0:
            raise ValueError("interval must be non-negative")
        self._target = target
        self._interval = float(interval)
        self._args = args or ()
        self._kwargs = kwargs or {}
        self._run_on_start = bool(run_on_start)
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._name = name or f"Replicator-{id(self)}"
        self._daemon = daemon
        self.last_exception: Optional[BaseException] = None

    def _run_loop(self) -> None:
        try:
            if self._run_on_start and not self._stop_event.is_set():
                try:
                    self._target(*self._args, **self._kwargs)
                except BaseException as e:
                    self.last_exception = e
            # loop: wait for interval, then run target unless stopped
            while not self._stop_event.wait(self._interval):
                try:
                    self._target(*self._args, **self._kwargs)
                except BaseException as e:
                    # store the exception, but keep running
                    self.last_exception = e
        except Exception as e:
            # safety catch-all; store for inspection
            self.last_exception = e

    def start(self) -> None:
        """Start the background thread. Safe to call multiple times."""
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run_loop, name=self._name, daemon=self._daemon)
            self._thread.start()

    def stop(self, timeout: Optional[float] = None) -> bool:
        """
        Signal the loop to stop and join the thread.
        Returns True if the thread exited cleanly within the timeout.
        """
        with self._lock:
            if not self._thread:
                return True
            self._stop_event.set()
            self._thread.join(timeout)
            alive = self._thread.is_alive()
            if not alive:
                self._thread = None
            return not alive

    def is_running(self) -> bool:
        t = self._thread
        return bool(t and t.is_alive())

    def set_interval(self, interval: float) -> None:
        if interval < 0:
            raise ValueError("interval must be non-negative")
        with self._lock:
            self._interval = float(interval)

    def run_once(self) -> None:
        """Run the target once in the calling thread (synchronous)."""
        self._target(*self._args, **self._kwargs)
    


# Example usage when running this file directly
if __name__ == "__main__":
    def demo_task():
        print("replicating at", time.time())

    rep = Replicator(demo_task, interval=1.5, run_on_start=True)
    rep.start()
    try:
        time.sleep(5)
    finally:
        rep.stop(timeout=2)