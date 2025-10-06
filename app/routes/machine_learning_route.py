from flask import Blueprint, request, jsonify

ml_route = Blueprint("machineLearning_route", __name__)

@ml_route.route("/ml", methods = ["POST"])
def ml_result():
  result_json = request.get_json()

  
