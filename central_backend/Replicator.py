import threading
import time
import os
import logging
from typing import Callable, Any, Optional, Tuple, Dict
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from client import COLS, DOCTOR_COLS
from datetime import datetime

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
        # Optional region routing metadata that will be forwarded to the target
        source_region: Optional[str] = None,
        target_regions: Optional[Any] = None,
        target_region: Optional[Any] = None,
        # Allow a DB client to be provided directly as a keyword argument
        db_client: Optional[Any] = None,
        # Maximum run time in seconds for this replicator (None to run indefinitely)
        max_run_seconds: Optional[float] = 6000,
        run_on_start: bool = False,
        name: Optional[str] = None,
        daemon: bool = True,
    ):
        if interval < 0:
            raise ValueError("interval must be non-negative")
        self._target = target
        self._interval = float(interval)
        self._args = args or ()
        # Start with explicit kwargs passed by caller
        self._kwargs = dict(kwargs or {})
        # If caller provided explicit source/target region args to the Replicator
        # forward them to the target callable unless the same keys were
        # explicitly provided in `kwargs`.
        if source_region is not None and 'source_region' not in self._kwargs:
            self._kwargs['source_region'] = source_region
        # support singular `target_region` and plural `target_regions` names
        if target_regions is not None and 'target_regions' not in self._kwargs:
            self._kwargs['target_regions'] = target_regions
        if target_region is not None and 'target_region' not in self._kwargs:
            self._kwargs['target_region'] = target_region
        # Optionally allow a DB client to be provided either as the explicit
        # `db_client` parameter or inside the `kwargs` mapping. Prefer the
        # explicit parameter when present and fall back to any value found
        # in `kwargs` for backward compatibility with older call sites.
        self._db_client = db_client or self._kwargs.pop('db_client', None)
        # Maximum allowed runtime (seconds). If set, the background loop will
        # stop after this many seconds have elapsed since `start()` was called.
        self._max_run_seconds = max_run_seconds
        self._start_time: Optional[float] = None
        self._name = name or f"Replicator-{id(self)}"

        # Setup a file logger for this replicator instance so logs are easy to
        # inspect. Logs are written to `replicator.log` in the same directory
        # as this module unless overridden by environment or further config.
        log_dir = os.path.dirname(__file__) or '.'
        log_path = os.path.join(log_dir, 'replicator.log')
        self._logger = logging.getLogger(self._name)
        # Avoid adding multiple handlers if multiple Replicator instances are created
        if not self._logger.handlers:
            fh = logging.FileHandler(log_path)
            fh.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
            self._logger.addHandler(fh)
        self._logger.setLevel(logging.INFO)
        self._run_on_start = bool(run_on_start)
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._daemon = daemon
        self.last_exception: Optional[BaseException] = None

    def _run_loop(self) -> None:
        try:
            if self._run_on_start and not self._stop_event.is_set():
                try:
                    # If a DB client was provided, run the internal replicate logic
                    if self._db_client:
                        self._logger.info(f"Running initial replicate_once (run_on_start) at time {datetime.now().isoformat()}Z")
                        self._replicate_once()
                    else:
                        self._target(*self._args, **self._kwargs)
                except BaseException as e:
                    self.last_exception = e
            # loop: wait for interval, then run target unless stopped
            while not self._stop_event.wait(self._interval):
                # Check for configured timeout and stop if elapsed
                try:
                    if self._max_run_seconds is not None and self._start_time is not None:
                        elapsed = time.time() - self._start_time
                        if elapsed >= float(self._max_run_seconds):
                            self._logger.info("Max runtime %s seconds reached (elapsed=%.1f); stopping loop", self._max_run_seconds, elapsed)
                            self._stop_event.set()
                            break
                except Exception:
                    # Don't fail the loop on logging/timeout check issues
                    pass
                try:
                    if self._db_client:
                        self._replicate_once()
                    else:
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
            # record start time before launching the thread so the timeout
            # countdown begins immediately
            self._start_time = time.time()
            self._logger.info("Starting replicator thread")
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
            self._logger.info("Stopping replicator thread (alive=%s)", alive)
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
        if self._db_client:
            self._replicate_once()
        else:
            self._target(*self._args, **self._kwargs)

    def _replicate_once(self):
        """Perform a single replication pass: read unprocessed outbox events
        from the source region DB and apply them to each target region DB.

        Expected kwargs provided to the Replicator (or constructor):
          - source_region: string region key
          - target_regions / target_region: list or single target region
        The Replicator will use `self._db_client.getURL({'region': region})`
        to obtain DSNs for connections.
        """
        print("Running")
        try:
            source_region = self._kwargs.get('source_region')
            targets = self._kwargs.get('target_regions') or self._kwargs.get('target_region') or []
            # normalize single target to list
            if isinstance(targets, (str,)):
                targets = [targets]
            if not source_region or not targets:
                return

            # Build or reuse connections
            src_conn = None
            src_created = False
            try:
                src_conn = getattr(self._db_client, 'connections', {}).get(source_region)
            except Exception:
                src_conn = None
            if src_conn is None:
                try:
                    src_dsn = self._db_client.getURL({'region': source_region})
                    if not src_dsn:
                        return
                    src_conn = psycopg2.connect(src_dsn)
                    src_created = True
                except Exception:
                    return
            if src_conn is not None:
                if src_created:
                    self._logger.info("Created new source connection for region %s", source_region)
                else:
                    self._logger.info("Reusing existing source connection for region %s", source_region)

            src_cur = src_conn.cursor()

            # Fetch batch of unprocessed events
            src_cur.execute("""
                SELECT event_id, table_name, op, payload
                FROM outbox_events
                WHERE processed = false
                ORDER BY created_at
                LIMIT 50;
            """)
            events = src_cur.fetchall()

            if not events:
                src_cur.close()
                if src_created:
                    try:
                        src_conn.close()
                    except Exception:
                        pass
                return

            # Process events: apply to each target region
            for event_id, table, op, payload in events:
                try:
                    if isinstance(payload, str):
                        try:
                            obj = json.loads(payload)
                        except Exception:
                            obj = payload
                    else:
                        obj = payload

                    # Prepare target connections map (reuse DBClient.connections when available)
                    target_conns = {}
                    for tgt in targets:
                        try:
                            existing = getattr(self._db_client, 'connections', {}).get(tgt)
                        except Exception:
                            existing = None
                        if existing:
                            target_conns[tgt] = (existing, False)
                            self._logger.info("Reusing existing connection for target %s", tgt)
                        else:
                            try:
                                tgt_dsn = self._db_client.getURL({'region': tgt})
                                if not tgt_dsn:
                                    continue
                                created_conn = psycopg2.connect(tgt_dsn)
                                target_conns[tgt] = (created_conn, True)
                                self._logger.info("Created new connection for target %s", tgt)
                            except Exception:
                                # couldn't connect to this target, skip it
                                continue

                    # Helper to determine patients table name for a payload/region
                    def _patients_table_for_payload(payload_obj, default_region):
                        region_key = None
                        if isinstance(payload_obj, dict):
                            region_key = payload_obj.get('Region')
                            if not region_key and payload_obj.get('State'):
                                try:
                                    region_key = self._db_client.region_map.get(payload_obj.get('State'))
                                except Exception:
                                    region_key = None
                        if not region_key:
                            region_key = default_region
                        suffix = str(region_key).split('-')[-1] if region_key else ''
                        return 'patients_west' if suffix == 'west' else 'patients_central'

                    # Now apply this event to each prepared target connection
                    for tgt, (repl_conn, repl_created) in target_conns.items():
                        repl_cur = None
                        try:
                            # Upsert/delete handling for patients/doctors
                            repl_cur = repl_conn.cursor()
                            if op == 'upsert':
                                # handle explicit patients table names (patients_west/patients_central)
                                if isinstance(table, str) and table.startswith('patients'):
                                    if table in ('patients_west', 'patients_central'):
                                        tgt_table = table
                                    else:
                                        tgt_table = _patients_table_for_payload(obj, source_region)
                                    cols = [f'"{c}"' for c in COLS]
                                    cols_sql = ', '.join(cols)
                                    placeholders = ', '.join(['%s'] * len(COLS))
                                    vals = []
                                    for c in COLS:
                                        v = obj.get(c) if isinstance(obj, dict) else None
                                        vals.append(v)
                                    update_assign = ', '.join(f'"{c}" = EXCLUDED."{c}"' for c in COLS if c not in ("Patient_ID", "State"))
                                    sql = f"""
                                        INSERT INTO {tgt_table} ({cols_sql}) VALUES ({placeholders})
                                        ON CONFLICT ("State","Patient_ID") DO UPDATE SET {update_assign};
                                    """
                                    repl_cur.execute(sql, tuple(vals))
                                elif table == 'doctors':
                                    cols = [f'"{c}"' for c in DOCTOR_COLS]
                                    cols_sql = ', '.join(cols)
                                    placeholders = ', '.join(['%s'] * len(cols))
                                    vals = []
                                    for c in DOCTOR_COLS:
                                        vals.append(obj.get(c) if isinstance(obj, dict) else None)
                                    update_assign = ', '.join(f'"{c}" = EXCLUDED."{c}"' for c in DOCTOR_COLS if c != 'Doctor_ID')
                                    sql = f"""
                                        INSERT INTO doctors ({cols_sql}) VALUES ({placeholders})
                                        ON CONFLICT ("Doctor_ID") DO UPDATE SET {update_assign};
                                    """
                                    print("Executing SQL:", sql, "with vals:", vals,"On",repl_conn)
                                    repl_cur.execute(sql, tuple(vals))
                                else:
                                    # Unknown table - attempt generic upsert using payload keys
                                    if isinstance(obj, dict):
                                        cols = ', '.join(f'"{k}"' for k in obj.keys())
                                        placeholders = ', '.join(['%s'] * len(obj))
                                        sql = f'INSERT INTO {table} ({cols}) VALUES ({placeholders}) ON CONFLICT DO NOTHING;'
                                        repl_cur.execute(sql, tuple(obj.values()))
                            elif op == 'delete':
                                if isinstance(table, str) and table.startswith('patients'):
                                    pid = obj.get('Patient_ID') or obj.get('id')
                                    state_val = obj.get('State')
                                    tgt_table = table if table in ('patients_west', 'patients_central') else _patients_table_for_payload(obj, source_region)
                                    repl_cur.execute(f'DELETE FROM {tgt_table} WHERE "Patient_ID" = %s AND "State" = %s;', (pid, state_val))
                                elif table == 'doctors':
                                    did = obj.get('Doctor_ID') or obj.get('id')
                                    repl_cur.execute('DELETE FROM doctors WHERE "Doctor_ID" = %s;', (did,))
                                else:
                                    did = obj.get('id') if isinstance(obj, dict) else None
                                    if did is not None:
                                        repl_cur.execute(f"DELETE FROM {table} WHERE id = %s;", (did,))

                            # commit per-target change (connection may be reused, commit is safe)
                            try:
                                repl_conn.commit()
                            except Exception:
                                try:
                                    repl_conn.rollback()
                                except Exception as e:
                                    print(e)
                                    pass
                        except Exception:
                            # record the exception, continue with other targets
                            try:
                                if repl_conn is not None:
                                    repl_conn.rollback()
                            except Exception as e:
                                print(e)
                                pass
                        finally:
                            try:
                                if repl_cur is not None:
                                    repl_cur.close()
                            except Exception as e:
                                print(e)
                                pass

                    # Close any target connections we created for this event batch
                    for tgt, (_, created_flag) in target_conns.items():
                        if created_flag:
                            try:
                                conn_to_close = target_conns[tgt][0]
                                conn_to_close.close()
                            except Exception as e:
                                print(e)
                                pass

                    # mark processed on source
                    try:
                        src_cur.execute("UPDATE outbox_events SET processed = true WHERE event_id = %s;", (event_id,))
                    except Exception as mark_err:
                        # The source connection may be in an aborted transaction state
                        # (e.g. "current transaction is aborted..."), so attempt to
                        # recover by rolling back the source connection and retrying.
                            self._logger.error("Exception while marking event as processed: %s", mark_err)
                            try:
                                src_conn.rollback()
                            except Exception:
                                pass
                            # Retry once using the existing cursor
                            try:
                                src_cur.execute("UPDATE outbox_events SET processed = true WHERE event_id = %s;", (event_id,))
                            except Exception:
                                # As a last resort, open a fresh connection to the
                                # source region and mark the event processed there.
                                try:
                                    src_dsn = self._db_client.getURL({'region': source_region})
                                    if src_dsn:
                                        fresh = psycopg2.connect(src_dsn)
                                        try:
                                            with fresh.cursor() as fresh_cur:
                                                fresh_cur.execute("UPDATE outbox_events SET processed = true WHERE event_id = %s;", (event_id,))
                                            fresh.commit()
                                            self._logger.info("Marked event %s processed using fresh connection", event_id)
                                        finally:
                                            try:
                                                fresh.close()
                                            except Exception:
                                                pass
                                except Exception as freshe:
                                    # Couldn't mark processed; log and continue. The
                                    # event will remain unprocessed and retried later.
                                    self._logger.error("Failed to mark event %s processed on fresh connection: %s", event_id, freshe)
                        
                except Exception as e:
                    print("Exception while marking event as processed:", e)
                    # record exception but keep processing remaining events
                    self.last_exception = e

            # commit source updates marking processed
            try:
                src_conn.commit()
            except Exception:
                try:
                    src_conn.rollback()
                except Exception:
                    pass
            src_cur.close()
            if src_created:
                try:
                    src_conn.close()
                except Exception:
                    pass
        except Exception as e:
            self.last_exception = e
    


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