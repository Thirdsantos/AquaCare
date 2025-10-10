import logging
import os
import sys
import traceback
import pytz
import atexit
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
# Flask App Setup
# -----------------------
app = create_app()
CORS(app)

# -----------------------
# Timezone Setup
# -----------------------
tz_name = os.getenv("TZ", "Asia/Manila")
LOCAL_TZ = pytz.timezone(tz_name)
logger.info(f"Server timezone: {tz_name}, Local time: {datetime.now(LOCAL_TZ)}")

# -----------------------
# APScheduler Setup
# -----------------------
schedule_background = BackgroundScheduler(timezone=LOCAL_TZ, daemon=True)

def debug_scheduler_heartbeat():
    logger.info(f"APScheduler heartbeat at {datetime.now(LOCAL_TZ).strftime('%Y-%m-%d %H:%M:%S %Z')}")

# Job Listener — detects errors or completions
def job_listener(event):
    if event.exception:
        logger.exception(f"Job {event.job_id} FAILED at {datetime.now(LOCAL_TZ)}")
    else:
        logger.info(f"Job {event.job_id} executed successfully at {datetime.now(LOCAL_TZ)}")

schedule_background.add_listener(job_listener, EVENT_JOB_ERROR | EVENT_JOB_EXECUTED)

# Heartbeat job (every 10 seconds)
schedule_background.add_job(
    func=debug_scheduler_heartbeat,
    trigger="interval",
    seconds=10,
    id="heartbeat_debug"
)

# Start APS
logger.info("Starting APScheduler...")
schedule_background.start()
logger.info("APScheduler started successfully.")

# -----------------------
# Shutdown Detection
# -----------------------
def on_exit():
    logger.warning(f"APScheduler or process stopping at {datetime.now(LOCAL_TZ)}")

atexit.register(on_exit)

# -----------------------
# Firestore Scheduler Restore
# -----------------------
firestore.scheduler = schedule_background
try:
    firestore.reschedule_all_jobs_from_firestore()
    logger.info("Restored all Firestore jobs successfully.")
except Exception as e:
    logger.error("Failed to restore Firestore jobs:")
    traceback.print_exception(type(e), e, e.__traceback__)

# -----------------------
# Status Route
# -----------------------
@app.route("/status")
def status():
    jobs = schedule_background.get_jobs()
    return {
        "status": "alive",
        "job_count": len(jobs),
        "jobs": [job.id for job in jobs]
    }

# -----------------------
# Flask Server
# -----------------------
if __name__ == "__main__":
    logger.info("Flask app starting...")
    try:
        app.run(host="0.0.0.0", port=5001)
    except Exception as e:
        logger.exception("Flask crashed:")
        sys.exit(1)
