from app import create_app
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
from app.services import firebase
from app.services import firestore
from datetime import datetime
import os
import pytz

app = create_app()
CORS(app)

# Get timezone (default: Asia/Manila)
tz_name = os.getenv("TZ", "Asia/Manila")
LOCAL_TZ = pytz.timezone(tz_name)

# Initialize APScheduler
schedule_background = BackgroundScheduler(timezone=LOCAL_TZ)
schedule_background.start()

# 🩺 Heartbeat function to confirm scheduler is alive
def debug_scheduler_heartbeat():
    print(f"[HEARTBEAT] APScheduler is alive at {datetime.now(LOCAL_TZ).strftime('%Y-%m-%d %H:%M:%S %Z')}")

# Run heartbeat every 60 seconds
schedule_background.add_job(
    func=debug_scheduler_heartbeat,
    trigger="interval",
    seconds=3,
    id="heartbeat_debug"
)

# Link scheduler to Firestore service and reschedule all jobs
firestore.scheduler = schedule_background
firestore.reschedule_all_jobs_from_firestore()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
