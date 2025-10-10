import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv
import os
import json
import base64
import re
from datetime import datetime, timedelta, timezone
import tzlocal
from flask import jsonify
import requests
import pytz


load_dotenv()
tz_name = os.getenv("TZ", "Asia/Manila")
LOCAL_TZ = pytz.timezone(tz_name)



import os
import json
import base64
import firebase_admin
from firebase_admin import credentials, firestore

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

    raise ValueError(
        "Invalid GOOGLE_FIREBASE_KEY format. Expected base64, JSON string, or valid file path."
    )



key_json = load_firebase_credentials()

if not firebase_admin._apps:
    cred = credentials.Certificate(key_json)
    firebase_admin.initialize_app(cred)

db = firestore.client()


scheduler = None

def add_schedule_firestore(aquarium_id: int, cycle: int, schedule_time: datetime, job_id: str) -> str:
    """
    Add a schedule document to Firestore.

    Args:
        aquarium_id (int): ID of the aquarium.
        cycle (int): Feeding cycle or amount.
        schedule_time (datetime): Localized datetime for the schedule.
        job_id (str): Firestore document ID.

    Returns:
        str: Human-readable confirmation message.
    """

    if schedule_time.tzinfo is None:
        schedule_time = schedule_time.replace(tzinfo=LOCAL_TZ)

    db.collection("Schedules").document(job_id).set({
        "aquarium_id": aquarium_id,
        "cycle": cycle,
        "schedule_time": schedule_time,
        "status": "pending"
    })
    return f" Schedule added: {job_id} for aquarium {aquarium_id} at {schedule_time.isoformat()}"


def create_schedule(aquarium_id: int, cycle: int, schedule_time: str):
    """Create a Firestore schedule and register a one-time APScheduler job."""
    naive_time = datetime.strptime(schedule_time, "%Y-%m-%d %H:%M:%S")
    run_time = LOCAL_TZ.localize(naive_time)

    job_id = f"schedule_at_{run_time.strftime('%Y%m%d_%H%M%S')}"

    output = add_schedule_firestore(aquarium_id, cycle, run_time, job_id)
    print(output)

    scheduler.add_job(
        func=send_scheduled_raspi,
        trigger="date",
        run_date=run_time,
        args=[aquarium_id, cycle, job_id],
        id=job_id
    )

  
def send_scheduled_raspi(aquarium_id, cycle, job_id):
    target_url = f"https://pi-cam.alfreds.dev/{aquarium_id}/add_task"


    payload = {
        "aquarium_id": aquarium_id,
        "cycle": cycle,
        "job_id": job_id
    }

    try:
        # Send POST request
        response = requests.post(target_url, json=payload, timeout=5)
        response.raise_for_status()
        print(f"Task sent to Raspberry Pi: {response.status_code} - {response.text}")
    except requests.RequestException as e:
        print(f"Error sending task to Raspberry Pi: {e}")

    set_status = set_status_done_firebase(job_id)
    print(set_status)
    




def set_status_done_firebase(job_id: str):
    """Mark a schedule document as completed.

    Args:
        job_id: The unique id of the job (document id in the `Schedules` collection).

    Returns:
        A human-readable message confirming the completion status update.
    """
    doc_ref = db.collection("Schedules").document(job_id)
    doc_ref.update({
        "status" : "done"
    })

    return f"{job_id} is now succesfully completed"


def find_schedule_by_time_and_aquarium(aquarium_id: int, schedule_time: str):
    """Find a schedule document by aquarium_id and schedule_time."""
    target_time = datetime.strptime(schedule_time, "%Y-%m-%d %H:%M:%S").replace(tzinfo=LOCAL_TZ)
    start_time = target_time - timedelta(seconds=1)
    end_time = target_time + timedelta(seconds=1)

    schedules_ref = db.collection("Schedules")
    docs = schedules_ref.where("aquarium_id", "==", aquarium_id).stream()

    for doc in docs:
        st = doc.to_dict().get("schedule_time")
        if isinstance(st, datetime):
            st_dt = st
        elif isinstance(st, str):
            try:
                # Try ISO format first
                st_dt = datetime.fromisoformat(st)
            except ValueError:
                try:
                    # Handle Firestore timestamp format: "October 8, 2026 at 11:00:00 PM UTC+8"
                    # Remove timezone info for parsing, we'll add it back
                    time_part = re.sub(r'\s+UTC[+-]\d+$', '', st)
                    st_dt = datetime.strptime(time_part, "%B %d, %Y at %I:%M:%S %p")
                    
                    # Extract timezone offset if present
                    tz_match = re.search(r'UTC([+-]\d+)$', st)
                    if tz_match:
                        offset_hours = int(tz_match.group(1))
                        tz = timezone(timedelta(hours=offset_hours))
                        st_dt = st_dt.replace(tzinfo=tz)
                    else:
                        st_dt = st_dt.replace(tzinfo=LOCAL_TZ)
                except ValueError as e:
                    print(f"Could not parse timestamp format: {st}, error: {e}")
                    continue
        else:
            print(f"Unknown timestamp type: {type(st)}, value: {st}")
            continue

        # Ensure timezone awareness
        if st_dt.tzinfo is None:
            st_dt = st_dt.replace(tzinfo=LOCAL_TZ)

        if start_time <= st_dt <= end_time:
            return doc.id

    return None



def delete_schedule_by_time(aquarium_id: int, schedule_time: str):
    """Delete a schedule for a specific aquarium at a given time."""
    try:
        doc_id = find_schedule_by_time_and_aquarium(aquarium_id, schedule_time)
        if not doc_id:
            return jsonify({"error": f"No schedule found for aquarium {aquarium_id} at {schedule_time}"}), 404

        # Remove APScheduler job if exists
        if scheduler:
            job = scheduler.get_job(doc_id)
            if job:
                scheduler.remove_job(doc_id)
                print(f"Removed job {doc_id} from APScheduler")
            else:
                print(f"No APS job found for {doc_id}")

        # Delete Firestore document
        db.collection("Schedules").document(doc_id).delete()
        print(f"Deleted Firestore document {doc_id}")

        return jsonify({"message": f"Successfully deleted schedule for aquarium {aquarium_id} at {schedule_time}"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
from datetime import datetime

def reschedule_all_jobs_from_firestore():
    """Recreate all pending Firestore schedules in APScheduler (after restart)."""
    schedules_ref = db.collection("Schedules")
    docs = schedules_ref.stream()

    restored_count = 0
    skipped_past = 0
    skipped_duplicate = 0
    now = datetime.now(LOCAL_TZ)
    print(f"Server timezone: {LOCAL_TZ}, Current time: {now}")

    for doc in docs:
        data = doc.to_dict()
        job_id = doc.id

        aquarium_id = data.get("aquarium_id")
        cycle = data.get("cycle", 1)
        schedule_time = data.get("schedule_time")
        status = data.get("status", "pending")
        print(f"Found schedule {job_id} — Firestore time: {schedule_time}")

        # Only reschedule pending jobs
        if status != "pending":
            continue

        if not schedule_time:
            print(f"Skipping {job_id} — no schedule_time found.")
            continue

        # Convert Firestore timestamp or string to datetime
        if isinstance(schedule_time, datetime):
            if schedule_time.tzinfo is None:
                # Firestore timestamps are UTC by default
                schedule_time = schedule_time.replace(tzinfo=pytz.UTC)
            scheduled_at = schedule_time.astimezone(LOCAL_TZ)
        else:
            try:
                scheduled_at = datetime.fromisoformat(schedule_time)
                if scheduled_at.tzinfo is None:
                    scheduled_at = pytz.UTC.localize(scheduled_at)
                scheduled_at = scheduled_at.astimezone(LOCAL_TZ)
            except Exception as e:
                print(f"Failed to parse schedule_time for {job_id}: {e}")
                continue

        print(f"Parsed schedule_time localized: {scheduled_at}, Now: {now}")

        # Skip jobs in the past
        if scheduled_at <= now:
            print(f"Skipping {job_id} — scheduled time is in the past.")
            skipped_past += 1
            continue

        # Skip duplicates
        existing_job = scheduler.get_job(job_id)
        if existing_job:
            print(f"Duplicate detected — Job {job_id} already exists. Skipping.")
            skipped_duplicate += 1
            continue

        # Recreate APScheduler job
        scheduler.add_job(
            func=send_scheduled_raspi,
            trigger="date",
            run_date=scheduled_at,
            args=[aquarium_id, cycle, job_id],
            id=job_id
        )

        restored_count += 1
        print(f"✅ Rescheduled job {job_id} for {scheduled_at}")

    print(
        f"\nFinished rescheduling: "
        f"{restored_count} restored, "
        f"{skipped_past} skipped (past), "
        f"{skipped_duplicate} skipped (duplicate)."
    )
