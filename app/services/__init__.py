import os
import json
import firebase_admin
from firebase_admin import credentials, db

cred = None

# 1️⃣ Check Secret File (Render mounts firebase_key.json automatically if added)
if os.path.exists("firebase_key.json"):
    print("Using firebase_key.json from Secret Files")
    cred = credentials.Certificate("firebase_key.json")

# 2️⃣ Check Environment Variable (e.g., from .env or Render env var)
elif os.getenv("GOOGLE_FIREBASE_KEY"):
    print("Using GOOGLE_FIREBASE_KEY from environment variable")
    key_json = os.getenv("GOOGLE_FIREBASE_KEY").replace('\\n', '\n')  # fix escaped \n
    try:
        key_dict = json.loads(key_json)
        cred = credentials.Certificate(key_dict)
    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error in GOOGLE_FIREBASE_KEY: {e}")
        exit()

# 3️⃣ Check Local File (for development)
elif os.path.exists("firebase_key.json"):
    print("Using local firebase_key.json")
    cred = credentials.Certificate("firebase_key.json")

else:
    print("❌ No Firebase credentials found (Secret File, Env, or Local).")
    exit()

# Initialize Firebase only once
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred, {
        "databaseURL": "https://for-practice-ce750-default-rtdb.asia-southeast1.firebasedatabase.app/"
    })

# Expose database instance
db = db
