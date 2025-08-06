from . import db
from app.services.notification import send_fcm_notification

class FirebaseReference:
    def __init__(self, aquarium_id):
        self.id = aquarium_id
        self.base = f"aquariums/{self.id}"

    def get_ref(self, sub_path=""):
        return db.reference(f"{self.base}/{sub_path}".rstrip('/'))


def save_sensors(aquarium_id, data):
    ref = FirebaseReference(aquarium_id)
    ref.get_ref("sensors").set(data)


def initialize_data_firebase(aquarium_id):
    ref = FirebaseReference(aquarium_id)
    root = ref.get_ref()

    init = {
        "sensors": {
            "ph": 0,
            "temperature": 0,
            "turbidity": 0
        },
        "hourly_log": {
            "index": 0
        },
        "notification": {
            "ph": False,
            "temperature": False,
            "turbidity": False
        },
        "threshold": {
            "ph": { "max": 0, "min": 0 },
            "temperature": { "max": 0, "min": 0 },
            "turbidity": { "max": 0, "min": 0 }
        },
        "average": {
            "index": 0
        },
        "name" : f"New Aquarium {aquarium_id}",
        "aquarium_id" : aquarium_id
    }

    if not root.get():
        root.set(init)


def delete_logs(aquarium_id, action):
    ref = FirebaseReference(aquarium_id)

    if action == 'hourly':
        base_ref = ref.get_ref("hourly_log")
        index_ref = ref.get_ref("hourly_log/index")

        logs = base_ref.get()
        index = index_ref.get()

        if not logs:
            return

        if index is not None and index >= 24:
            for key in logs:
                if key.isdigit():
                    base_ref.child(key).delete()

            index_ref.set(0)

    elif action == 'day':
        base_ref = ref.get_ref("average")
        index_ref = ref.get_ref("average/index")

        average = base_ref.get()
        index = index_ref.get()

        if not average:
            return

        if index is not None and index >= 30:
            for key in average:
                if key.isdigit():
                    base_ref.child(key).delete()

            index_ref.set(0)


def save_hourly(aquarium_id, data):
    ref = FirebaseReference(aquarium_id)

    hourly_ref = ref.get_ref("hourly_log")
    hourly_index = ref.get_ref("hourly_log/index")

    get_index = hourly_index.get()

    current_index = 1 if get_index is None else get_index + 1

    hourly_ref.child(str(current_index)).set(data)
    hourly_index.set(current_index)

    if current_index >= 24:
        average(aquarium_id)
        delete_logs(aquarium_id, "hourly")


def average(aquarium_id):
    ref = FirebaseReference(aquarium_id)

    logs_per_hour = ref.get_ref("hourly_log")
    get_logs = logs_per_hour.get()

    average_ref = ref.get_ref("average")
    index_ref = ref.get_ref("average/index")
    get_index = index_ref.get()

    ph, temperature, turbidity = [], [], []

    for key, value in get_logs.items():
        if key.isdigit():
            ph.append(value['ph'])
            temperature.append(value['temperature'])
            turbidity.append(value['turbidity'])

    ph_avg = sum(ph) / len(ph)
    temp_avg = sum(temperature) / len(temperature)
    turb_avg = sum(turbidity) / len(turbidity)

    average_dict = {
        "ph": ph_avg,
        "temperature": temp_avg,
        "turbidity": turb_avg
    }

    latest_index = 1 if get_index is None else get_index + 1

    average_ref.child(str(latest_index)).set(average_dict)
    index_ref.set(latest_index)

    delete_logs(aquarium_id, "day")


def notification_checker(aquarium_id, sensor):
    ref = FirebaseReference(aquarium_id)
    return ref.get_ref(f"notification/{sensor}").get()

def check_threshold(aquarium_id, data):
  ph_notification = notification_checker(aquarium_id, "ph")
  temperature_notification = notification_checker(aquarium_id, "temperature")
  turbidity_notification = notification_checker(aquarium_id, "turbidity")
  ref = FirebaseReference(aquarium_id)
  threshold = ref.get_ref("threshold").get()

  # Check pH
  if ph_notification:
    ph = data["ph"]
    ph_min = threshold["ph"]["min"]
    ph_max = threshold["ph"]["max"]

    if ph < ph_min or ph > ph_max:
      send_fcm_notification(aquarium_id, "pH")

  # Check temperature
  if temperature_notification:
    temperature = data["temperature"]
    temperature_min = threshold["temperature"]["min"]
    temperature_max = threshold["temperature"]["max"]

    if temperature < temperature_min or temperature > temperature_max:
      send_fcm_notification(aquarium_id, "Temperature")

  # Check turbidity
  if turbidity_notification:
    turbidity = data["turbidity"]
    turbidity_min = threshold["turbidity"]["min"]
    turbidity_max = threshold["turbidity"]["max"]

    if turbidity < turbidity_min or turbidity > turbidity_max:
      send_fcm_notification(aquarium_id, "Turbidity")
        

            
