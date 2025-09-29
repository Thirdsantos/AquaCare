import os
import json
import base64
import io
from PIL import Image
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

def load_gemini_config():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("GEMINI_API_KEY not found in environment variables")
            return False
        
        genai.configure(api_key=api_key)
        return True
    except Exception as e:
        print(f"Error loading Gemini config: {e}")
        return False

# Initialize Gemini Model
def initialize_gemini():
    if not load_gemini_config():
        return None
    try:
        model = genai.GenerativeModel("models/gemini-2.5-flash")
        return model
    except Exception as e:
        print(f"Error initializing Gemini model: {e}")
        return None

model = initialize_gemini()

def decode_base64_image(base64_str):
    try:
        if "," in base64_str:
            base64_str = base64_str.split(",", 1)[1]
        image_bytes = base64.b64decode(base64_str)
        return Image.open(io.BytesIO(image_bytes))
    except Exception as e:
        print(f"Error decoding image: {e}")
        return None


def ask_gemini(text=None, image=None):
    if not model:
        return {"Error": "Gemini AI not properly initialized. Check API key configuration."}, 500
    
    if not text and not image:
        return {"Error": "At least give a question or an image"}, 400

    # Text only
    if text and not image:
        instruction = (
            "Your name is Aquabot. If a question is not related to aquatic life or aquarium and fish, "
            "please respond like 'Oops, I can only answer questions about aquatic life and the wonders of the water world. "
            "Let's talk fish, oceans, lakes, or anything aquatic!' "
            "Also, start your response like 'Hi, I'm Aquabot, happy to serve you!' "
            "Do not use bold text. "
            "User: "
        )
        modified_question = instruction + text
        try:
            response = model.generate_content([modified_question])
            return {"AI_Response": response.text}, 200
        except Exception as e:
            return {"Error": f"Gemini API error: {str(e)}"}, 500

    # Image only
    elif image and not text:
        detection_prompt = (
            "You are Aquabot, an expert in aquatic life. "
            "Please examine the image of a fish and describe what species it is, and then tell me the ideal water parameters "
            "for that fish in natural language. Include the following details in your explanation:\n"
            "- Fish name\n"
            "- Recommended pH range\n"
            "- Recommended temperature range (in °C)\n"
            "- Recommended turbidity range (in NTU)\n"
            "Do not return JSON. Just explain it clearly as Aquabot would.\n"
            "Avoid using bold text. Start with: 'Hi, I'm Aquabot, happy to serve you!'"
        )

        image_data = decode_base64_image(image)
        if not image_data:
            return {"Error": "Failed to decode image"}, 400

        try:
            response = model.generate_content([detection_prompt, image_data])
            return {"AI_Response": response.text}, 200
        except Exception as e:
            return {"Error": f"Gemini API failed: {str(e)}"}, 500


    # Text + Image
    else:
        instruction = (
            "Your name is Aquabot. If a question is not related to aquatic life or aquarium and fish, "
            "please respond like 'Oops, I can only answer questions about aquatic life and the wonders of the water world. "
            "Let's talk fish, oceans, lakes, or anything aquatic!' "
            "Also, start your response like 'Hi, I'm Aquabot, happy to serve you!' "
            "Do not use bold text. "
            "User: "
        )
        modified_question = instruction + text
        image_data = decode_base64_image(image)
        if not image_data:
            return {"Error": "Failed to decode image"}, 400
            
        try:
            response = model.generate_content([modified_question, image_data])
            return {"AI_Response": response.text}, 200
        except Exception as e:
            return {"Error": f"Gemini API error: {str(e)}"}, 500