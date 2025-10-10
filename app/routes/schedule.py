from flask import jsonify, request, Blueprint
from app.services.firebase import (
    add_schedule_firebase,
    delete_schedule_firebase,
    change_cycle_schedule_firebase,
    set_on_off_schedule_firebase,
    get_schedule_firebase,
    set_daily_schedule_firebase
)
from app.services.firestore import create_schedule, delete_schedule_by_time
from datetime import datetime 

schedule_route = Blueprint("schedule", __name__)

# ─────────────────────────────
# 🔹 Add Feeding Schedule
# ─────────────────────────────
@schedule_route.route("/add_schedule/<int:aquarium_id>", methods=["POST"])
def add_schedule(aquarium_id):
    schedule = request.get_json()
    result = add_schedule_firebase(aquarium_id, schedule)
    return jsonify(result)

# ─────────────────────────────
# 🔹 Delete Feeding Schedule
# ─────────────────────────────
@schedule_route.route("/delete_schedule/<int:aquarium_id>/<string:time>", methods=["DELETE"])
def delete_schedule(aquarium_id, time):
    delete = delete_schedule_firebase(aquarium_id, time)
    return jsonify(delete)

# ─────────────────────────────
# 🔹 Update Cycle
# ─────────────────────────────
@schedule_route.route("/update_schedule_cycle/<int:aquarium_id>/<string:time>/<int:cycle>", methods=["PATCH"])
def update_cycle(aquarium_id, time, cycle):
    update = change_cycle_schedule_firebase(aquarium_id, time, cycle)
    return jsonify(update)

# ─────────────────────────────
# 🔹 Update On/Off Switch
# ─────────────────────────────
@schedule_route.route("/update_schedule_switch/<int:aquarium_id>/<string:time>/<switch>", methods=["PATCH"])
def update_schedule_switch(aquarium_id, time, switch):
    switch_value = switch.lower() in ['true', '1', 't', 'y', 'yes']
    update = set_on_off_schedule_firebase(aquarium_id, switch_value, time)
    return jsonify(update)

# ─────────────────────────────
# 🔹 Get All Schedules
# ─────────────────────────────
@schedule_route.route("/get_schedules/<int:aquarium_id>", methods=["GET"])
def get_schedules(aquarium_id):
    schedules = get_schedule_firebase(aquarium_id)
    return jsonify(schedules)

# ─────────────────────────────
# 🔹 Update Daily Toggle
# ─────────────────────────────
@schedule_route.route("/update_daily/<int:aquarium_id>/<string:time>/<switch>", methods=["PATCH"])
def update_daily(aquarium_id, time, switch):
    daily_value = switch.lower() in ['true', '1', 't', 'y', 'yes']
    update = set_daily_schedule_firebase(aquarium_id, daily_value, time)
    return jsonify(update)

# ─────────────────────────────
# 🔹 Add Task (Firestore + APScheduler)
# ─────────────────────────────
@schedule_route.route("/task/<int:aquarium_id>", methods=["POST"])
def add_task(aquarium_id):
    json_req = request.get_json()

    # ✅ Validate schedule_time format (must be string in '%Y-%m-%d %H:%M:%S')
    schedule_time = json_req.get("schedule_time")
    try:
        datetime.strptime(schedule_time, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return jsonify({
            "error": "Invalid time format. Expected 'YYYY-MM-DD HH:MM:SS'"
        }), 400

    output = create_schedule(
        aquarium_id=aquarium_id,
        cycle=json_req["cycle"],
        schedule_time=schedule_time
    )
    return jsonify({
        "message": "Successfully added the schedule",
        "details": output
    })

# ─────────────────────────────
# 🔹 Delete Task (Firestore + APScheduler)
# ─────────────────────────────
@schedule_route.route("/task/delete/<int:aquarium_id>", methods=["POST"])
def delete_task(aquarium_id):
    json_req = request.get_json()
    schedule_time = json_req.get("schedule_time")

    if not schedule_time:
        return jsonify({"error": "Missing 'schedule_time' in request"}), 400

    output = delete_schedule_by_time(aquarium_id=aquarium_id, schedule_time=schedule_time)
    return jsonify({
        "message": "Successfully removed the schedule",
        "details": output
    })
