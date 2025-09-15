from flask import jsonify, Blueprint, request
from app.services import db, save_sensors, initialize_data_firebase, save_hourly, check_threshold


sensors_bp = Blueprint("sensor", __name__)

@sensors_bp.route("/<int:aquarium_id>/sensors", methods = ["POST"])
def sensors(aquarium_id):
  data = request.json
  initialize_data_firebase(aquarium_id)
  save_sensors(aquarium_id, data)
  check_threshold(aquarium_id, data)

  return jsonify({"Message" : "Successfully recieved",
                  "Data" : data}), 200

@sensors_bp.route("/<int:aquarium_id>/hourly_log", methods = ["POST"])
def hourly_log(aquarium_id):
  data = request.json
  initialize_data_firebase(aquarium_id)
  save_hourly(aquarium_id, data)
  check_threshold(aquarium_id, data)

  return jsonify({"Message" : "Sucessful"}), 200

  

