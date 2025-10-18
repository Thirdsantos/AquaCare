from flask import Blueprint, request, jsonify
from app.services.ai import ask_gemini

ai_bp = Blueprint('ai', __name__, url_prefix='/')

@ai_bp.route("/ask", methods=["POST"])
def ask_gemini_route():
    """Run an AI query using Gemini.

    At least one of `question` text or `image` (base64) must be provided.

    Body JSON:
      - question (str, optional): Prompt text to ask the model
      - image (str, optional): Base64-encoded image content

    Returns:
      Response: JSON with model output and HTTP status code from the service.
    """
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