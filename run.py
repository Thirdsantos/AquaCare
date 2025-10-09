from app import create_app
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
from app.services import firebase
from app.services import firestore



app = create_app()

CORS(app)

schedule_background = BackgroundScheduler()
schedule_background.start()
firestore.scheduler = schedule_background
firestore.reschedule_all_jobs_from_firestore()

if __name__ == "__main__":
    app.run(host="0.0.0.0",  port=5001)



