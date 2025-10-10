from app import create_app
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
from app.services import firebase
from app.services import firestore
from tzlocal import get_localzone



app = create_app()

CORS(app)
LOCAL_TZ = get_localzone()

schedule_background = BackgroundScheduler(timezone=str(LOCAL_TZ))
schedule_background.start()
firestore.scheduler = schedule_background
firestore.reschedule_all_jobs_from_firestore()

if __name__ == "__main__":
    app.run(host="0.0.0.0",  port=5001)



