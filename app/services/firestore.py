import os
import json
import base64
from datetime import datetime, timedelta, timezone
import requests
from flask import jsonify
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)
if not logging.getLogger().hasHandlers():  # Only configure if root logger has no handlers
    logging.basicConfig(
        level=logging.DEBUG,  # Default level
        format="[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )


load_dotenv()


def load_firebase_credentials():
    """Load Firebase credentials from environment or file with auto-detection."""
    key_data = os.getenv("GOOGLE_FIREBASE_KEY")

    if not key_data:
        raise ValueError("GOOGLE_FIREBASE_KEY environment variable is not set!")

    try:
        decoded = base64.b64decode(key_data).decode("utf-8")
        parsed = json.loads(decoded)
        print("Loaded Firebase credentials from Base64.")
        return parsed
    except (base64.binascii.Error, json.JSONDecodeError):
        pass

    try:
        parsed = json.loads(key_data)
        print("Loaded Firebase credentials from raw JSON string.")
        return parsed
    except json.JSONDecodeError:
        pass

    if os.path.exists(key_data):
        with open(key_data, "r") as f:
            parsed = json.load(f)
            print(f"Loaded Firebase credentials from file: {key_data}")
            return parsed

    raise ValueError("Invalid GOOGLE_FIREBASE_KEY format. Expected base64, JSON string, or valid file path.")


key_json = load_firebase_credentials()
if not firebase_admin._apps:
    cred = credentials.Certificate(key_json)
    firebase_admin.initialize_app(cred)

db = firestore.client()




def create_schedule(aquarium_id: int, cycle: int, schedule_time: str, food: str, job_id: str):
  """Create a Firestore schedule and register an APScheduler job.

  schedule_time is expected as 'YYYY-%m-%d %H:%M:%S' in Asia/Manila local time.

  """
  try:
    trim_time = schedule_time.replace(" ","_")
    job_id = f"schedule_at_{trim_time}"
    db.collection("Schedules").document(job_id).set({
        "aquarium_id": aquarium_id,
        "cycle": cycle,
        "schedule_time": schedule_time,
        "food" : food, 
        "status": "pending"        
      })
    logger.info(f"Schedule {job_id} added in the firestore")
    return "Sucesfully added in the firestore"
    
  except Exception as e:
      logger.error(f"Failed to add schedule {job_id}: {e}")
      return e
      

def send_schedule_raspi(aquarium_id: int, cycle: int, schedule_time: str, food: str, job_id: str):
    """Send scheduled task to Raspberry Pi"""
    target_url = f"https://pi-cam.alfreds.dev/{aquarium_id}/add_task"
    formated_job_id = f"schedule_at_{schedule_time.replace(' ', '_')}"

    payload = {"aquarium_id": aquarium_id, "cycle": cycle, "job_id": formated_job_id, "food" : food, "schedule_time" : schedule_time}

    try: 
        response = requests.post(target_url, json=payload)
        print(f"Sucessfully send to raspi | {response.status_code}")
    except Exception as e:
        print(e)

def delete_schedule_by_id(aquarium_id: int, document_id: str):
    """Delete a schedule in Firestore using document_id."""
    try:
        get_ref = db.collection("Schedules").document(document_id)
        doc = get_ref.get()

        if doc.exists:
            get_ref.delete()
            logger.info(f" Schedule {document_id} deleted successfully for aquarium {aquarium_id}.")
            return f"Schedule {document_id} deleted successfully."
        else:
            logger.warning(f" Schedule {document_id} not found for aquarium {aquarium_id}.")
            return f"Schedule {document_id} not found."

    except Exception as e:
        logger.error(f" Failed to delete schedule {document_id} for aquarium {aquarium_id}: {e}")
        return f"Error deleting schedule: {e}"

def set_complete_task(document_id: str):
    try:
        doc_ref = db.collection("Schedules").document(document_id)

        if not doc_ref:
            logger.error(f"{document_id} doesn't exist")
            return f"{document_id} doesn't exist"
        
        doc_ref.update({
            "status" : "done"
        })

        logger.info("Sucessfuly set the status to 'done'")
        return "Sucessfuly set the status to 'done'"
    except Exception as e:
        logger.error(e)
        return e

def send_deletion_raspi(aquarium_id: int, document_id: str):
    try:
        url = f"https://pi-cam.alfreds.dev/{aquarium_id}/delete_task"
        payload = {"aquarium_id": aquarium_id, "document_id": document_id}

        try:
            requests.post(url, json=payload)
            logger.info("Sucessfuly Delete the Task in Raspi")
            return "Sucessfuly Delete the Task in Raspi"
        
        except Exception as e:
            logger.error(f"ERROR {e}")
            return e
    except Exception as e:
        logger.error(f"ERROR {e}")
        return e
    
def get_scheduler_aquarium(aquarium_id: int):
   try:
      docs = db.collection("Schedules").where("aquarium_id", "==", aquarium_id).where("status", "==", "pending").stream()
      pending_schedule = [
            {**doc.to_dict(), "document_id": doc.id} for doc in docs
        ]

      if not pending_schedule:
        logger.info(f"No Pending Schedule is return for aquarium {aquarium_id}")
        return f"No Pending Schedule is return for aquarium {aquarium_id}"
       
      logger.info("Pending schedules are extracted")
      return pending_schedule
   
   except Exception as e:
      logger.error(f"ERROR Something went wrong, {e}")
      return e
   
   


    

