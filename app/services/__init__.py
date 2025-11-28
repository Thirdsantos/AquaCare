import os
import json
import base64
import firebase_admin
from firebase_admin import credentials, db

cred = None

if os.getenv("GOOGLE_FIREBASE_KEY"):
    print("Using GOOGLE_FIREBASE_KEY from environment variable (Base64)")
    key_b64 = os.getenv("GOOGLE_FIREBASE_KEY")
    try:
        key_json = base64.b64decode(key_b64).decode("utf-8")  # Decode Base64
        key_dict = json.loads(key_json)                        # Load JSON
        cred = credentials.Certificate(key_dict)
    except (base64.binascii.Error, json.JSONDecodeError) as e:
        print(f"❌ Error decoding GOOGLE_FIREBASE_KEY: {e}")
        exit()

else:
    print("❌ No Firebase credentials found.")
    exit()

# Initialize Firebase only once
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred, {
        "databaseURL": "https://for-practice-ce750-default-rtdb.asia-southeast1.firebasedatabase.app/"
    })

# Expose database instance
db = db
