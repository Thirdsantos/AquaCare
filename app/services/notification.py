from firebase_admin import messaging

def send_fcm_notification(aquarium_id, sensor_type):
    title = f"AquaCare Alert: Aquarium {aquarium_id}"
    body = f"{sensor_type.capitalize()} is out of range!"
    topic = "aquacare_alerts"

    message = messaging.Message(
        notification=messaging.Notification(title=title, body=body),
        topic=topic
    )

    response = messaging.send(message)
    print("FCM sent:", response)
