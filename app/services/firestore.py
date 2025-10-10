import os
import json
import base64
import re
from datetime import datetime, timedelta
import pytz
import requests
from flask import jsonify
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

# ─────────────────────────────
# 🔹 Load environment + timezone
# ─────────────────────────────
load_dotenv()
tz_name = os.getenv("TZ", "Asia/Manila")
LOCAL_TZ = pytz.timezone(tz_name)

# ─────────────────────────────
# 🔹 Firebase Initialization
# ─────────────────────────────
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
scheduler = None

# ─────────────────────────────
# 🔹 Add schedule to Firestore (store string time)
# ─────────────────────────────
def add_schedule_firestore(aquarium_id: int, cycle: int, schedule_time: datetime, job_id: str) -> str:
    """Add a schedule document to Firestore."""
    if schedule_time.tzinfo is None:
        schedule_time = LOCAL_TZ.localize(schedule_time)
    else:
        schedule_time = schedule_time.astimezone(LOCAL_TZ)

    schedule_time_str = schedule_time.strftime("%Y-%m-%d %H:%M:%S")

    db.collection("Schedules").document(job_id).set({
        "aquarium_id": aquarium_id,
        "cycle": cycle,
        "schedule_time": schedule_time_str,  # 🔹 Stored as string
        "status": "pending"
    })
    return f"Schedule added: {job_id} at {schedule_time_str}"

# ─────────────────────────────
# 🔹 Create schedule and register in APScheduler
# ─────────────────────────────
def create_schedule(aquarium_id: int, cycle: int, schedule_time: str):
    """Create a Firestore schedule and register an APScheduler job."""
    server_now = datetime.now(LOCAL_TZ)
    naive_time = datetime.strptime(schedule_time, "%Y-%m-%d %H:%M:%S")
    run_time = LOCAL_TZ.localize(naive_time)

    print("\n[DEBUG] Creating Schedule:")
    print(f"Server local time now:       {server_now}")
    print(f"Requested schedule_time:     {schedule_time}")
    print(f"Localized run_time for APS:  {run_time}")

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

    added_job = scheduler.get_job(job_id)
    if added_job:
        print(f"[DEBUG] ✅ APS Job added: {added_job.id}, Run time: {added_job.next_run_time}")
    else:
        print(f"[DEBUG] ❌ Failed to add job {job_id} to APScheduler.")

# ─────────────────────────────
# 🔹 Execute scheduled job
# ─────────────────────────────
def send_scheduled_raspi(aquarium_id, cycle, job_id):
    """Send scheduled task to Raspberry Pi and update Firestore after execution."""
    current_time = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[DEBUG] Job Triggered — Time now: {current_time}, Job ID: {job_id}")

    target_url = f"https://pi-cam.alfreds.dev/{aquarium_id}/add_task"
    payload = {"aquarium_id": aquarium_id, "cycle": cycle, "job_id": job_id}

    try:
        print(f"[DEBUG] Sending POST to {target_url} with payload: {payload}")
        response = requests.post(target_url, json=payload, timeout=5)
        response.raise_for_status()
        print(f"[DEBUG] ✅ Task sent successfully — Status: {response.status_code}")
    except requests.RequestException as e:
        print(f"[ERROR] Failed to send task to Raspberry Pi: {e}")

    try:
        result = set_status_done_firebase(job_id)
        print(f"[DEBUG] Firestore update result: {result}")
    except Exception as e:
        print(f"[ERROR] Failed to update Firestore status for {job_id}: {e}")

# ─────────────────────────────
# 🔹 Mark Firestore schedule done
# ─────────────────────────────
def set_status_done_firebase(job_id: str):
    doc_ref = db.collection("Schedules").document(job_id)
    doc_ref.update({"status": "done"})
    return f"{job_id} marked as done"

# ─────────────────────────────
# 🔹 Reschedule all pending jobs on startup
# ─────────────────────────────
def reschedule_all_jobs_from_firestore():
    """Recreate all pending Firestore schedules after restart."""
    schedules_ref = db.collection("Schedules")
    docs = schedules_ref.stream()

    restored_count = skipped_past = skipped_duplicate = 0
    now = datetime.now(LOCAL_TZ)
    print(f"[INIT] Rescheduling jobs... Local time: {now}")

    for doc in docs:
        data = doc.to_dict()
        job_id = doc.id
        aquarium_id = data.get("aquarium_id")
        cycle = data.get("cycle", 1)
        status = data.get("status", "pending")
        schedule_str = data.get("schedule_time")

        if status != "pending":
            continue
        if not schedule_str:
            print(f"[SKIP] {job_id}: missing schedule_time")
            continue

        try:
            parsed_time = datetime.strptime(schedule_str, "%Y-%m-%d %H:%M:%S")
            schedule_time = LOCAL_TZ.localize(parsed_time)
        except Exception as e:
            print(f"[ERROR] Failed to parse schedule_time for {job_id}: {e}")
            continue

        if schedule_time <= now:
            skipped_past += 1
            print(f"[SKIP] {job_id}: already past ({schedule_time})")
            continue

        if scheduler.get_job(job_id):
            skipped_duplicate += 1
            print(f"[SKIP] Duplicate job {job_id}")
            continue

        scheduler.add_job(
            func=send_scheduled_raspi,
            trigger="date",
            run_date=schedule_time,
            args=[aquarium_id, cycle, job_id],
            id=job_id
        )
        restored_count += 1
        print(f"[RESTORE] ✅ Job {job_id} scheduled for {schedule_time}")

    print(
        f"\n[RESULT] Rescheduling complete — "
        f"{restored_count} restored, "
        f"{skipped_past} skipped (past), "
        f"{skipped_duplicate} skipped (duplicate)."
    )
