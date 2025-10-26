import logging
import os
import sys
import traceback
import atexit
from zoneinfo import ZoneInfo
from datetime import datetime, timezone
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from app import create_app
from app.services import firebase
from app.services import firestore


LOG_FORMAT = "[%(asctime)s] [%(levelname)s] %(message)s"
LOG_LEVEL = logging.INFO

logging.basicConfig(
    level=logging.DEBUG,
    format=LOG_FORMAT,
)

logger = logging.getLogger(__name__)


app = create_app()
CORS(app)





if __name__ == "__main__":
    logger.info(" Flask app starting...")
    try:
        app.run(host="0.0.0.0", port=5001, debug=False, use_reloader=False)
    except Exception as e:
        logger.exception(" Flask crashed:")
        sys.exit(1)