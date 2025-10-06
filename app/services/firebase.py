from . import db
from app.services.notification import send_fcm_notification
from datetime import datetime

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
            "state_flag": {"ph": False, "temperature": False, "turbidity": False},
            "ph": False,
            "temperature": False,
            "turbidity": False
        },
        "threshold": {
            "ph": {"max": 0, "min": 0},
            "temperature": {"max": 0, "min": 0},
            "turbidity": {"max": 0, "min": 0}
        },
        "average": {
            "index": 0
        },
        "name": f"New Aquarium {aquarium_id}",
        "aquarium_id": aquarium_id,
        "auto_feeder" : { "schedule" : {}} 
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
    state_flag_ref = ref.get_ref("notification/state_flag")
    state_flag = state_flag_ref.get()

    ph_flag = state_flag["ph"]
    turbidity_flag = state_flag["turbidity"]
    temperature_flag = state_flag["temperature"]

    # Check pH
    if ph_notification:
        ph = data["ph"]
        ph_min = threshold["ph"]["min"]
        ph_max = threshold["ph"]["max"]

        if ph < ph_min or ph > ph_max:
            if not ph_flag:
                send_fcm_notification(aquarium_id, "pH")
                state_flag_ref.child("ph").set(True)
        else:
            if ph_flag:
                state_flag_ref.child("ph").set(False)

    # Check temperature
    if temperature_notification:
        temperature = data["temperature"]
        temperature_min = threshold["temperature"]["min"]
        temperature_max = threshold["temperature"]["max"]

        if temperature < temperature_min or temperature > temperature_max:
            if not temperature_flag:
                send_fcm_notification(aquarium_id, "Temperature")
                state_flag_ref.child("temperature").set(True)
        else:
            if temperature_flag:
                state_flag_ref.child("temperature").set(False)

    # Check turbidity
    if turbidity_notification:
        turbidity = data["turbidity"]
        turbidity_min = threshold["turbidity"]["min"]
        turbidity_max = threshold["turbidity"]["max"]

        if turbidity < turbidity_min or turbidity > turbidity_max:
            if not turbidity_flag:
                send_fcm_notification(aquarium_id, "Turbidity")
                state_flag_ref.child("turbidity").set(True)
        else:
            if turbidity_flag:
                state_flag_ref.child("turbidity").set(False)

def get_schedule_firebase(aquarium_id: int) -> dict:
    '''Get the active (enabled) feeding schedules of the auto feeder.
    
    This function retrieves all schedules of the auto feeder and filters out
    only those where "switch" is set to True.

    Args:
        aquarium_id (int): The ID of the aquarium.

    Returns:
        dict: Contains:
            - "status" (str): "success" or "empty"
            - "schedules" (list): List of active schedules (if any)
    '''
    ref = FirebaseReference(aquarium_id)
    ref_schedule = ref.get_ref("auto_feeder/schedule")
    schedule_value = ref_schedule.get() or {}

    active_schedules = []

    for v in schedule_value.values():
        if v.get("switch"):
            active_schedules.append({"time": v.get("time"), "food" : v.get("food"), "cycle" : v.get("cycle")})

    if not active_schedules:
        return {"status": "empty", "schedules": []}
    return {"status": "success", "schedules": active_schedules}





def add_schedule_firebase(aquarium_id: int, schedule: dict) -> dict:
    """Add a new feeding schedule to Firebase if it does not already exist.

    This function checks for duplicate feeding times in the aquarium's
    auto-feeder schedule. If the time does not exist, it adds a new schedule
    entry. If it already exists, it skips insertion.

    Args:
        aquarium_id (int): The unique identifier of the aquarium.
        schedule (dict): A dictionary containing schedule details with keys:
            - "time" (str): Feeding time in HH:MM format.
            - "cycle" (int): Amount or cycle number for feeding.
            - "switch" (bool) : Tells if the alarm is on or off
            - "food" (str) : Tells what type of food for the fish

    Returns:
        dict: A dictionary containing the operation result with keys:
            - "status" (str): Either "added" or "duplicate".
            - "time" (str): The feeding time provided.
            - "cycle" (int, optional): Returned only if added.
            - "switch" (bool): Tell if it's on or off
    """
    ref = FirebaseReference(aquarium_id)
    ref_schedule = ref.get_ref("auto_feeder")
    schedule_ref = ref_schedule.child("schedule")
    current_schedules = schedule_ref.get() or {}

    new_time = schedule["time"]
    cycle = schedule["cycle"]
    switch = schedule["switch"]
    food = schedule["food"]
    duplicate = False


    for key, value in current_schedules.items():
        if value["time"] == new_time:
            duplicate = True
            break

    if not duplicate:
        schedule_ref.push({"time": new_time, "cycle" : cycle, "switch" : switch, "food" : food})
        return {"status": "added", "time": new_time, "cycle": cycle, "switch" : switch}
    else:
        return {"status": "duplicate", "time": new_time, "switch" : switch}


def set_on_off_schedule_firebase(aquarium_id : int, switch : bool, time: str) -> dict:
    """Update the on/off switch of a feeding schedule in Firebase.

    This function finds a schedule by its feeding time and updates its
    switch value (enabled/disabled).

    Args:
        aquarium_id (int): The unique identifier of the aquarium.
        switch (bool): The new state of the schedule (True for on, False for off).
        time (str): Feeding time in HH:MM format.

    Returns:
        dict: A dictionary containing the operation result with keys:
            - "status" (str): Either "updated" or "not_found".
            - "time" (str): The feeding time requested.
            - "enabled" (bool, optional): The new switch value if updated.
    """
    ref = FirebaseReference(aquarium_id)
    switch_ref = ref.get_ref("auto_feeder/schedule")
    switch_value = switch_ref.get() 

    for key, value in switch_value.items():
        if value["time"] == time:
            key_ref = ref.get_ref(f"auto_feeder/schedule/{key}")
            key_ref.update({"switch" : switch})

            return {"status": "updated", "time": time, "enabled": switch}
        
    return {"status": "not_found", "time": time}


def change_cycle_schedule_firebase(aquarium_id : int, time: str, cycle : int) -> dict:
    """Update the feeding cycle of a schedule in Firebase.

    This function finds a schedule by its feeding time and updates its
    cycle value (amount or cycle number).

    Args:
        aquarium_id (int): The unique identifier of the aquarium.
        time (str): Feeding time in HH:MM format.
        cycle (int): The new cycle value to set.

    Returns:
        dict: A dictionary containing the operation result with keys:
            - "status" (str): Either "updated" or "not_found".
            - "time" (str): The feeding time requested.
            - "cycle" (int, optional): The new cycle value if updated.
    """
    ref = FirebaseReference(aquarium_id)
    cycle_ref = ref.get_ref("auto_feeder/schedule")
    cycle_value = cycle_ref.get()

    for key, value in cycle_value.items():
        if value["time"] == time:
            key_ref = cycle_ref.child(key)
            key_ref.update({"cycle" : cycle})

            return {"status": "updated", "time": time, "cycle": cycle}
    return {"status" : "not found", "time" : time}


def delete_schedule_firebase(aquarium_id: int, time: str) -> dict:
    """Delete a feeding schedule in Firebase by its time.

    Args:
        aquarium_id (int): The unique identifier of the aquarium.
        time (str): Feeding time in HH:MM format.

    Returns:
        dict: A dictionary containing the operation result with keys:
            - "status" (str): Either "deleted" or "not_found".
            - "time" (str): The feeding time requested for deletion.
    """
    ref = FirebaseReference(aquarium_id)
    schedule_ref = ref.get_ref("auto_feeder/schedule")
    schedules = schedule_ref.get() or {}

    for key, value in schedules.items():
        if value.get("time") == time:  
            schedule_ref.child(key).delete()
            return {"status": "deleted", "time": time}

    return {"status": "not_found", "time": time}




def get_firebase_thresholds() -> list:
    '''This function checks all the aquarium and return a list of active thresholds'''
    ref_aquarium = db.reference("aquariums")
    aquarium_value = ref_aquarium.get()

    if not aquarium_value:
        print("No aquarium data")
        return []
    
    active_thresholds = []

    for key, value in aquarium_value.items():
        
        notification = value.get("notification", {})
        thresholds = value.get("threshold", {})

        ph_active = notification.get("ph", False)
        temperature_active = notification.get("temperature", False)
        turbidity_active = notification.get("turbidity", False)

        if ph_active or temperature_active or turbidity_active:
            active_thresholds.append({
                "aquarium_id" : key,
                "ph_notification" : ph_active,
                "temperature_notification" : temperature_active,
                "turbidity_notification" : turbidity_active,
                "thresholds" : thresholds
            })

    return active_thresholds      


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

    
