import os
import json
import firebase_admin
from firebase_admin import credentials, db, messaging
from .firebase import save_sensors, initialize_data_firebase, save_hourly, check_threshold

# Try environment variable first
key_json = os.getenv("GOOGLE_FIREBASE_KEY")

if key_json:
    # Fix \n issues if stored as raw text in env
    key_json = key_json.replace('\\n', '\n')
    try:
        key_dict = json.loads(key_json)
        cred = credentials.Certificate(key_dict)
    except json.JSONDecodeError as e:
        print(f"JSON decode error from environment: {e}")
        exit()
else:
    # Fallback: use local file (for local dev)
    if os.path.exists("firebase_key.json"):
        cred = credentials.Certificate("firebase_key.json")
    else:
        print(" No Firebase credentials found (neither env nor local file).")
        exit()

# Initialize Firebase only once
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred, {
        "databaseURL": "https://for-practice-ce750-default-rtdb.asia-southeast1.firebasedatabase.app/"
    })

# Expose database instance
db = db
