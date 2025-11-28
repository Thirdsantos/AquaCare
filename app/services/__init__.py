import os
import json
import base64
import firebase_admin
from firebase_admin import credentials, db as firebase_db

# --- Load Firebase credentials ---
cred = None

if os.path.exists("firebase_key.json"):
    print("Using firebase_key.json from Secret Files")
    cred = credentials.Certificate("firebase_key.json")
elif os.getenv("GOOGLE_FIREBASE_KEY_B64"):
    print("Using GOOGLE_FIREBASE_KEY_B64 from environment variable")
    try:
        decoded_json = base64.b64decode(os.getenv("GOOGLE_FIREBASE_KEY_B64")).decode("utf-8")
        key_dict = json.loads(decoded_json)
        cred = credentials.Certificate(key_dict)
    except (json.JSONDecodeError, base64.binascii.Error) as e:
        print(f"❌ Error decoding GOOGLE_FIREBASE_KEY_B64: {e}")
        exit()
else:
    print("❌ No Firebase credentials found.")
    exit()

# --- Initialize Firebase only once ---
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred, {
        "databaseURL": "https://for-practice-ce750-default-rtdb.asia-southeast1.firebasedatabase.app/"
    })

# --- Expose the db instance ---
db = firebase_db
