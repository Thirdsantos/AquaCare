from flask import Blueprint, request, jsonify
from app.services.firebase import compare_ml_firebase, get_firebase_thresholds

ml_route = Blueprint("machineLearning_route", __name__)

@ml_route.route("/ml", methods=["POST"])
def ml_result():
    """Compare ML predictions against thresholds stored in Firebase.

    Body JSON should be a list of prediction objects. The route fetches
    current thresholds, compares each prediction, and may trigger downstream
    alerts or actions via services.

    Returns:
      Response: 200 JSON on success or error details with appropriate codes.
    """
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

  
