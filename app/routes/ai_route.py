from flask import Blueprint, request, jsonify
from app.services.ai import ask_gemini

ai_bp = Blueprint('ai', __name__, url_prefix='/')

@ai_bp.route("/ask", methods=["POST"])
def ask_gemini_route():
    data = request.json
    text = data.get("question")
    image = data.get("image")

    if not text and not image:
        return jsonify({"Error": "At least give a question or an image"}), 400

    # Call the service function
    response, status_code = ask_gemini(
        text=text,
        image=image
    )
    
    return jsonify(response), status_code