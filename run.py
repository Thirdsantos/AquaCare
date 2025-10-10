

from app import create_app
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from datetime import datetime
from app.services import firebase
from app.services import firestore
import pytz
import os
import atexit
import sys
import traceback

# -----------------------
# Setup Flask App
# -----------------------
app = create_app()
CORS(app)

# -----------------------
# Timezone Setup
# -----------------------
tz_name = os.getenv("TZ", "Asia/Manila")
LOCAL_TZ = pytz.timezone(tz_name)
print(f"[INIT] Server timezone: {tz_name}, Local time: {datetime.now(LOCAL_TZ)}")

# -----------------------
# APScheduler Setup
# -----------------------
schedule_background = BackgroundScheduler(timezone=LOCAL_TZ, daemon=True)

def debug_scheduler_heartbeat():
    print(f"[HEARTBEAT] APScheduler alive at {datetime.now(LOCAL_TZ).strftime('%Y-%m-%d %H:%M:%S %Z')}")

# Job Listener (detects if jobs fail or complete)
def job_listener(event):
    if event.exception:
        print(f"[ERROR] Job {event.job_id} FAILED at {datetime.now(LOCAL_TZ)}")
        traceback.print_exception(type(event.exception), event.exception, event.exception.__traceback__)
    else:
        print(f"[INFO] Job {event.job_id} executed successfully at {datetime.now(LOCAL_TZ)}")

schedule_background.add_listener(job_listener, EVENT_JOB_ERROR | EVENT_JOB_EXECUTED)

# Add Heartbeat Job (every 10 seconds)
schedule_background.add_job(
    func=debug_scheduler_heartbeat,
    trigger="interval",
    seconds=10,
    id="heartbeat_debug"
)

# Log APS startup and shutdown
print("[INIT] Starting APScheduler...")
schedule_background.start()
print("[INIT] APScheduler started successfully.")

# Detect when APS or process is shutting down
def on_exit():
    print(f"[SHUTDOWN] APScheduler or process stopping at {datetime.now(LOCAL_TZ)}")

atexit.register(on_exit)

# -----------------------
# Firestore Scheduler Restore
# -----------------------
firestore.scheduler = schedule_background
try:
    firestore.reschedule_all_jobs_from_firestore()
except Exception as e:
    print("[ERROR] Failed to restore Firestore jobs:")
    traceback.print_exception(type(e), e, e.__traceback__)

# -----------------------
# Flask Server
# -----------------------
if __name__ == "__main__":
    print("[INIT] Flask app starting...")
    try:
        app.run(host="0.0.0.0", port=5001)
    except Exception as e:
        print("[ERROR] Flask crashed:")
        traceback.print_exception(type(e), e, e.__traceback__)
        sys.exit(1)
