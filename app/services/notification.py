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


def send_aquanotifier_notification(aquarium_id, message_ai, sensor):
    title = f"AquaBot Notifier ({sensor}): Aquarium {aquarium_id}"
    body = message_ai
    topic = "aquacare_alerts"

    message = messaging.Message(
        notification=messaging.Notification(title=title, body=body),
        topic=topic
    )

    response = messaging.send(message)
    print("FCM sent: ", response)