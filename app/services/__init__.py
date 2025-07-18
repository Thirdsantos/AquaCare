import os
import json
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, db, messaging
from .firebase import save_sensors, initialize_data_firebase, save_hourly, check_threshold

# Load .env variables
load_dotenv()

# Get JSON key from env
key_json = os.getenv("GOOGLE_FIREBASE_KEY")

if not key_json:
    print("Can't find the Firebase private key in .env")
    exit()


key_json = key_json.replace('\n', '\\n')



try:
    key_dict = json.loads(key_json)
except json.JSONDecodeError as e:
    print(f"JSON decode error: {e}")
    print(f"Error at position {e.pos}: {repr(key_json[max(0, e.pos-10):e.pos+10])}")
    exit()

# Initialize Firebase only if not already initialized
if not firebase_admin._apps:
    cred = credentials.Certificate(key_dict)
    firebase_admin.initialize_app(cred, {
        "databaseURL": "https://for-practice-ce750-default-rtdb.asia-southeast1.firebasedatabase.app/"
    })

db = db


    
