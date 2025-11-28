from flask import jsonify, Blueprint, request
from app.services import db, save_sensors, initialize_data_firebase, save_hourly, check_threshold


sensors_bp = Blueprint("sensor", __name__)

@sensors_bp.route("/<int:aquarium_id>/sensors", methods=["GET", "POST"])
def sensors(aquarium_id):
    if request.method == "POST":
        data = request.json
        initialize_data_firebase(aquarium_id)
        save_sensors(aquarium_id, data)
        check_threshold(aquarium_id, data)
        return jsonify({"Message": "Successfully received", "Data": data}), 200

    elif request.method == "GET":
        ref = FirebaseReference(aquarium_id)
        sensors_data = ref.get_ref("sensors").get()  # Fetch the latest sensor readings
        if not sensors_data:
            return jsonify({"Message": "No sensor data found"}), 404
        return jsonify({"Message": "Success", "Data": sensors_data}), 200

@sensors_bp.route("/<int:aquarium_id>/hourly_log", methods = ["POST"])
def hourly_log(aquarium_id):
  """Record an hourly log entry and evaluate thresholds.

  Body JSON should include readings for this hour. This appends to the
  hourly log structure and may trigger notifications if thresholds are
  violated.

  Args:
    aquarium_id (int): The aquarium identifier.

  Returns:
    Response: 200 JSON when stored successfully.
  """
  data = request.json
  initialize_data_firebase(aquarium_id)
  save_hourly(aquarium_id, data)
  check_threshold(aquarium_id, data)

  return jsonify({"Message" : "Sucessful"}), 200



  

