from datetime import datetime
from . import db


def store_ai_chat(role: str, message: str):
    ref = db.reference("chats")
    
    # Safe timestamp for Firebase keys
    timestamp = datetime.now().isoformat().replace(":", "-").replace(".", "-")
    
    ref.child(timestamp).set({
        "role": role,
        "message": message
    })


def load_message(limit: int =10):
    ref = db.reference("chats")
    data = ref.get() or {}

    sorted_items = sorted(data.items())

    recent = sorted_items[-limit:]

    messages = [{"role": v["role"], "message": v["message"]} for _, v in recent]
    return messages

