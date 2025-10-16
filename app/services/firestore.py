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
    payload = {"aquarium_id": aquarium_id, "cycle": cycle, "job_id": job_id, "food" : food, "schedule_time" : schedule_time}

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
   
   


    


    
'''
def send_scheduled_raspi(aquarium_id, cycle, job_id):S
  """Send scheduled task to Raspberry Pi and update Firestore after execution."""
    current_time = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[EXEC] send_scheduled_raspi START — local={current_time} job_id={job_id} aquarium_id={aquarium_id} cycle={cycle}", flush=True)

    target_url = f"https://pi-cam.alfreds.dev/{aquarium_id}/add_task"
    payload = {"aquarium_id": aquarium_id, "cycle": cycle, "job_id": job_id}

    skip_http = os.getenv("SKIP_PI_HTTP", "false").lower() == "true"
    if skip_http:
        print(f"[EXEC] SKIP_PI_HTTP=true — skipping HTTP call to Tank-Pi", flush=True)
    else:
        try:
            print(f"[EXEC] HTTP POST -> {target_url} payload={payload}", flush=True)
            response = requests.post(target_url, json=payload, timeout=5)
            response.raise_for_status()
            print(f"[EXEC] ✅ HTTP OK status={response.status_code} body={response.text[:200]}", flush=True)
        except requests.RequestException as e:
            print(f"[EXEC][ERROR] HTTP failed: {e}", flush=True)

    try:
        result = set_status_done_firebase(job_id)
        print(f"[EXEC] Firestore status updated: {result}", flush=True)
    except Exception as e:
        print(f"[EXEC][ERROR] Firestore update failed for {job_id}: {e}", flush=True)

    # Best-effort: remove APS job if it still exists (e.g., when executed by poller)
    try:
        if scheduler:
            job = scheduler.get_job(job_id)
            if job:
                scheduler.remove_job(job_id)
                print(f"[EXEC] Removed APS job {job_id} after execution", flush=True)
            else:
                print(f"[EXEC] No APS job {job_id} found to remove (may have been unscheduled or already removed)", flush=True)
    except Exception as e:
        print(f"[EXEC][WARN] Could not remove APS job {job_id}: {e}", flush=True)

    print(f"[EXEC] send_scheduled_raspi END — job_id={job_id}", flush=True)


def set_status_done_firebase(job_id: str):
    doc_ref = db.collection("Schedules").document(job_id)
    doc_ref.update({"status": "done"})
    return f"{job_id} marked as done"



def find_schedule_by_time_and_aquarium(aquarium_id: int, schedule_time: str):
    """Find a schedule document id by aquarium_id and schedule_time string (exact match)."""
    docs = db.collection("Schedules").where("aquarium_id", "==", aquarium_id).where("schedule_time", "==", schedule_time).stream()
    for doc in docs:
        return doc.id
    return None


def delete_schedule_by_time(aquarium_id: int, schedule_time: str):
    """Delete a schedule both from APScheduler and Firestore by local Manila time string."""
    try:
        print(f"[DELETE] Request to delete schedule aquarium_id={aquarium_id} schedule_time={schedule_time}", flush=True)
        doc_id = find_schedule_by_time_and_aquarium(aquarium_id, schedule_time)
        if not doc_id:
            print(f"[DELETE] Not found for aquarium_id={aquarium_id} at {schedule_time}", flush=True)
            return jsonify({"error": f"No schedule found for aquarium {aquarium_id} at {schedule_time}"}), 404

        # Remove APScheduler job if it exists
        if scheduler:
            job = scheduler.get_job(doc_id)
            if job:
                scheduler.remove_job(doc_id)
                print(f"[DELETE] Removed APS job {doc_id}")
            else:
                print(f"[DELETE] No APS job found for {doc_id}")

        # Delete Firestore document
        db.collection("Schedules").document(doc_id).delete()
        print(f"[DELETE] Deleted Firestore document {doc_id}")

        return jsonify({"message": f"Successfully deleted schedule for aquarium {aquarium_id} at {schedule_time}"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
'''