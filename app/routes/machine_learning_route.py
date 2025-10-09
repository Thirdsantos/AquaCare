from flask import Blueprint, request, jsonify
from app.services.firebase import compare_ml_firebase, get_firebase_thresholds

ml_route = Blueprint("machineLearning_route", __name__)

@ml_route.route("/ml", methods=["POST"])
def ml_result():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing request body"}), 400
        
        firebase_thresholds = get_firebase_thresholds()
        if not firebase_thresholds:
            return jsonify({"error": "No Firebase thresholds found"}), 500

        compare_ml_firebase(data, firebase_thresholds)

        return jsonify({"message": "ML comparison completed successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

  
