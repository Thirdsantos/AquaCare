import logging
import os
import sys
import traceback
import pytz
import atexit
import tzlocal
from datetime import datetime
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from app import create_app
from app.services import firebase
from app.services import firestore

# -----------------------
# Logging Setup
# -----------------------
LOG_FORMAT = "[%(asctime)s] [%(levelname)s] %(message)s"
LOG_LEVEL = logging.INFO

logging.basicConfig(
    level=LOG_LEVEL,
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler("server_debug.log", mode="a", encoding="utf-8")  # File log
    ]
)

logger = logging.getLogger(__name__)

# -----------------------
# Timezone Setup
# -----------------------
tz_name = os.getenv("TZ", "Asia/Manila")
LOCAL_TZ = pytz.timezone(tz_name)
logger.info(f"Server timezone: {tz_name}, Local time: {datetime.now(LOCAL_TZ)}")

# Diagnostic info
print("[INIT] APS Timezone:", LOCAL_TZ)
print("[INIT] System timezone:", tzlocal.get_localzone())
print("[INIT] Now UTC:", datetime.now(pytz.UTC))
print("[INIT] Now local:", datetime.now(LOCAL_TZ))

# -----------------------
# Flask App Setup
# -----------------------
app = create_app()
CORS(app)

# -----------------------
# APScheduler Setup
# -----------------------
scheduler = BackgroundScheduler(timezone=LOCAL_TZ, daemon=True)

def debug_scheduler_heartbeat():
    logger.info(f"💓 APScheduler heartbeat at {datetime.now(LOCAL_TZ).strftime('%Y-%m-%d %H:%M:%S %Z')}")

def job_listener(event):
    """Log job success/failure."""
    if event.exception:
        logger.exception(f"❌ Job {event.job_id} FAILED at {datetime.now(LOCAL_TZ)}")
    else:
        logger.info(f"✅ Job {event.job_id} executed successfully at {datetime.now(LOCAL_TZ)}")

# Register listeners and heartbeat job
scheduler.add_listener(job_listener, EVENT_JOB_ERROR | EVENT_JOB_EXECUTED)
scheduler.add_job(
    func=debug_scheduler_heartbeat,
    trigger="interval",
    seconds=10,
    id="heartbeat_debug",
    replace_existing=True
)

# Start scheduler
logger.info("🚀 Starting APScheduler...")
scheduler.start()
logger.info("✅ APScheduler started successfully.")

# -----------------------
# Shutdown Handler
# -----------------------
def on_exit():
    logger.warning(f"⚠️ APScheduler or process stopping at {datetime.now(LOCAL_TZ)}")

atexit.register(on_exit)

# -----------------------
# Firestore Job Restore
# -----------------------
firestore.scheduler = scheduler
try:
    firestore.reschedule_all_jobs_from_firestore()
    logger.info("🔁 Restored all Firestore jobs successfully.")
except Exception as e:
    logger.error("🔥 Failed to restore Firestore jobs:")
    traceback.print_exception(type(e), e, e.__traceback__)

# -----------------------
# Status Route
# -----------------------
@app.route("/status")
def status():
    jobs = scheduler.get_jobs()
    return {
        "status": "alive",
        "job_count": len(jobs),
        "jobs": [
            {"id": job.id, "next_run_time": str(job.next_run_time)}
            for job in jobs
        ]
    }

# -----------------------
# Flask Server Startup
# -----------------------
if __name__ == "__main__":
    logger.info("🌐 Flask app starting...")
    try:
        app.run(host="0.0.0.0", port=5001, debug=False, use_reloader=False)
    except Exception as e:
        logger.exception("💥 Flask crashed:")
        sys.exit(1)
