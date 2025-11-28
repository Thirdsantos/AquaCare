import os, json, base64, firebase_admin
from firebase_admin import credentials, db as firebase_db

cred = None

# 1️⃣ Secret file
if os.path.exists("firebase_key.json"):
    cred = credentials.Certificate("firebase_key.json")

# 2️⃣ Base64 env variable
elif os.getenv("GOOGLE_FIREBASE_KEY_B64"):
    decoded = base64.b64decode(os.getenv("GOOGLE_FIREBASE_KEY")).decode("utf-8")
    key_dict = json.loads(decoded)
    cred = credentials.Certificate(key_dict)

else:
    print("❌ No Firebase credentials found.")
    exit()

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred, {
        "databaseURL": "https://for-practice-ce750-default-rtdb.asia-southeast1.firebasedatabase.app/"
    })

db = firebase_db
