import os
import json
import base64
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
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
LOCAL_TZ = ZoneInfo(tz_name)

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
def add_schedule_firestore(aquarium_id: int, cycle: int, schedule_time: datetime | str, job_id: str) -> str:
    """Add a schedule document to Firestore.

    Store schedule_time as a string 'YYYY-%m-%d %H:%M:%S' in Asia/Manila.
    """
    if isinstance(schedule_time, datetime):
        if schedule_time.tzinfo is None:
            schedule_time = schedule_time.replace(tzinfo=LOCAL_TZ)
        else:
            schedule_time = schedule_time.astimezone(LOCAL_TZ)
        schedule_time_str = schedule_time.strftime("%Y-%m-%d %H:%M:%S")
    else:
        # Assume valid string format already
        schedule_time_str = schedule_time

    db.collection("Schedules").document(job_id).set({
        "aquarium_id": aquarium_id,
        "cycle": cycle,
        "schedule_time": schedule_time_str,  # Stored as local Manila string
        "status": "pending"
    })
    return f"Schedule added: {job_id} at {schedule_time_str}"

# ─────────────────────────────
# 🔹 Create schedule and register in APScheduler
# ─────────────────────────────
def create_schedule(aquarium_id: int, cycle: int, schedule_time: str):
    """Create a Firestore schedule and register an APScheduler job.

    schedule_time is expected as 'YYYY-%m-%d %H:%M:%S' in Asia/Manila local time.
    """
    server_now = datetime.now(LOCAL_TZ)
    naive_time = datetime.strptime(schedule_time, "%Y-%m-%d %H:%M:%S")
    run_time_local = naive_time.replace(tzinfo=LOCAL_TZ)
    run_time_utc = run_time_local.astimezone(timezone.utc)

    print("\n[DEBUG] Creating Schedule:")
    print(f"Server local time now:       {server_now}")
    print(f"Requested schedule_time:     {schedule_time}")
    print(f"Localized run_time for APS:  {run_time_local}")
    print(f"UTC run_time for APS:        {run_time_utc}")

    job_id = f"schedule_at_{run_time_local.strftime('%Y%m%d_%H%M%S')}"
    output = add_schedule_firestore(aquarium_id, cycle, schedule_time, job_id)
    print(output)

    scheduler.add_job(
        func=send_scheduled_raspi,
        trigger="date",
        run_date=run_time_utc,
        args=[aquarium_id, cycle, job_id],
        id=job_id,
        replace_existing=True,
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
    """Recreate all pending Firestore schedules after restart and execute missed ones."""
    schedules_ref = db.collection("Schedules")
    docs = schedules_ref.stream()

    restored_count = skipped_duplicate = executed_past = 0
    now = datetime.now(LOCAL_TZ)
    print(f"[INIT] Rescheduling jobs... Local time: {now}")

    for doc in docs:
        data = doc.to_dict()
        job_id = doc.id
        aquarium_id = data.get("aquarium_id")
        cycle = data.get("cycle", 1)
        status = data.get("status", "pending")
        schedule_field = data.get("schedule_time")

        if status != "pending":
            continue
        if not schedule_field:
            print(f"[SKIP] {job_id}: missing schedule_time")
            continue

        # Normalize schedule_time to LOCAL_TZ for APScheduler
        if isinstance(schedule_field, str):
            # Stored as local Manila string
            try:
                parsed_time = datetime.strptime(schedule_field, "%Y-%m-%d %H:%M:%S")
                schedule_time_local = parsed_time.replace(tzinfo=LOCAL_TZ)
            except Exception as e:
                print(f"[ERROR] Failed to parse schedule_time for {job_id}: {e}")
                continue
        elif isinstance(schedule_field, datetime):
            # Legacy: Firestore Timestamp (UTC)
            schedule_time = schedule_field
            if schedule_time.tzinfo is None:
                schedule_time = schedule_time.replace(tzinfo=timezone.utc)
            schedule_time_local = schedule_time.astimezone(LOCAL_TZ)
        else:
            print(f"[SKIP] {job_id}: unsupported schedule_time type {type(schedule_field)}")
            continue

        if schedule_time_local <= now:
            # Execute missed pending job immediately
            try:
                print(f"[EXECUTE] Missed job {job_id} (scheduled {schedule_time_local}, now {now})")
                send_scheduled_raspi(aquarium_id, cycle, job_id)
                executed_past += 1
            except Exception as e:
                print(f"[ERROR] Failed executing missed job {job_id}: {e}")
            continue

        if scheduler.get_job(job_id):
            skipped_duplicate += 1
            print(f"[SKIP] Duplicate job {job_id}")
            continue

        run_date_utc = schedule_time_local.astimezone(timezone.utc)
        scheduler.add_job(
            func=send_scheduled_raspi,
            trigger="date",
            run_date=run_date_utc,
            args=[aquarium_id, cycle, job_id],
            id=job_id,
            replace_existing=True,
        )
        restored_count += 1
        print(f"[RESTORE] ✅ Job {job_id} scheduled for {schedule_time_local} (UTC {run_date_utc})")

    print(
        f"\n[RESULT] Rescheduling complete — "
        f"{restored_count} restored, "
        f"{executed_past} executed (past), "
        f"{skipped_duplicate} skipped (duplicate)."
    )

# ─────────────────────────────
# 🔹 Find & delete schedule by time (for API route compatibility)
# ─────────────────────────────
def find_schedule_by_time_and_aquarium(aquarium_id: int, schedule_time: str):
    """Find a schedule document id by aquarium_id and schedule_time string (exact match)."""
    docs = db.collection("Schedules").where("aquarium_id", "==", aquarium_id).where("schedule_time", "==", schedule_time).stream()
    for doc in docs:
        return doc.id
    return None


def delete_schedule_by_time(aquarium_id: int, schedule_time: str):
    """Delete a schedule both from APScheduler and Firestore by local Manila time string."""
    try:
        doc_id = find_schedule_by_time_and_aquarium(aquarium_id, schedule_time)
        if not doc_id:
            return jsonify({"error": f"No schedule found for aquarium {aquarium_id} at {schedule_time}"}), 404

        # Remove APScheduler job if it exists
        if scheduler:
            job = scheduler.get_job(doc_id)
            if job:
                scheduler.remove_job(doc_id)
                print(f"[DELETE] Removed APS job {doc_id}")

        # Delete Firestore document
        db.collection("Schedules").document(doc_id).delete()
        print(f"[DELETE] Deleted Firestore document {doc_id}")

        return jsonify({"message": f"Successfully deleted schedule for aquarium {aquarium_id} at {schedule_time}"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─────────────────────────────
# 🔹 Safety poller: execute any pending jobs that are due (fallback)
# ─────────────────────────────
def process_due_pending_jobs():
    """Fallback guard: find pending schedules whose Manila time is <= now and execute them.

    This ensures correctness if an APS 'date' job is missed due to infra nuances.
    """
    now_local = datetime.now(LOCAL_TZ)
    now_str = now_local.strftime("%Y-%m-%d %H:%M:%S")

    try:
        docs = db.collection("Schedules").where("status", "==", "pending").stream()
        checked = 0
        executed = 0
        for doc in docs:
            data = doc.to_dict()
            job_id = doc.id
            st = data.get("schedule_time")
            aquarium_id = data.get("aquarium_id")
            cycle = data.get("cycle", 1)
            if not st or not aquarium_id:
                continue

            checked += 1
            # Lexicographic comparison works with 'YYYY-MM-DD HH:MM:SS'
            if isinstance(st, str) and st <= now_str:
                print(f"[POLL] Executing due job {job_id} (scheduled {st}, now {now_str})")
                try:
                    send_scheduled_raspi(aquarium_id, cycle, job_id)
                    executed += 1
                except Exception as e:
                    print(f"[POLL][ERROR] Failed executing job {job_id}: {e}")
        if checked:
            print(f"[POLL] Checked {checked} pending; executed {executed} due jobs.")
    except Exception as e:
        print(f"[POLL][ERROR] {e}")
