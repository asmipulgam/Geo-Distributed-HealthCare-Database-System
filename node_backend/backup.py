import datetime as dt
import os,shutil, subprocess, sys, threading, time
from pathlib import Path

CONTAINER_NAME = "roach-seattle-1"
DATABASE_NAME = "west"
LOCAL_BACKUPS = Path("./backups").resolve()

CONTAINER_BACKUP_PATH = "/cockroach/cockroach-data/backup"

RETENTION_DAYS = 1

INTERVAL_HOURS = 24

DOCKER_TIMEOUT = 3600  # 60 minutes

def _run(cmd, check=True, capture=False, timeout=None):
    print(">"," ".join(cmd))
    return subprocess.run(
        cmd,
        check=check,
        capture_output=capture,
        text=True,
        timeout=timeout,
    )

def _timestamp():
    return dt.datetime.utcnow().strftime("%Y%m%d_%H%M%S")

def backup():

    ts = _timestamp()
    local_target = LOCAL_BACKUPS / ts
    local_target.mkdir(parents=True, exist_ok=True)

    in_container_target = f"{CONTAINER_BACKUP_PATH}/{ts}"


    nodelocal_uri = f"nodelocal://1/backup/{ts}"

    sql = f"BACKUP DATABASE {DATABASE_NAME} INTO '{nodelocal_uri}';"
    _run([
        "docker","exec", CONTAINER_NAME,
        "cockroach", "sql",
        "--insecure",
        "--execute", sql
    ],
    timeout=DOCKER_TIMEOUT)

    container_backup_dir = f"{CONTAINER_NAME}:/cockroach/cockroach-data/extern/backup/{ts}"
    _run(["docker","cp",container_backup_dir, str(local_target)])
    print(f"Backup completed: {local_target}")
    return local_target

def cleanup():

    if RETENTION_DAYS <= 0:
        return
    cutoff = dt.datetime.utcnow() - dt.timedelta(days=RETENTION_DAYS)
    kept,removed = 0,0
    if not LOCAL_BACKUPS.exists():
        return
    for child in LOCAL_BACKUPS.iterdir():
        if child.is_dir():
            try:
                ts = dt.datetime.strptime(child.name, "%Y%m%d_%H%M%S")
            except ValueError:
                kept += 1
                continue
            if ts < cutoff:
                shutil.rmtree(child, ignore_errors=True)
                removed += 1
            else:
                kept += 1
    if removed:
        print(f" Cleaned up {removed} old backups; kept {kept}")

def loop_every(interval_hours, fn):
    while True:
        try:
            fn()
        except subprocess.CalledProcessError as e:
            print("Command Failed:" ,e)
        except Exception as e:
            print("Unknown Error:", e)
        time.sleep(max(60, interval_hours * 3600))

def run_scheduler():
    LOCAL_BACKUPS.mkdir(parents=True, exist_ok=True)
    def job():
        backup()
        cleanup()
    
    t = threading.Thread(target=loop_every, args=(INTERVAL_HOURS, job), daemon=True)
    t.start()
    print("Backup Scheduler started")
    try :
         while t.is_alive():
             t.join(timeout=1.0)
    except KeyboardInterrupt:
        print("\nStopping Backup Scheduler")

if __name__ == "__main__":
    backup()