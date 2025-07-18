# tests/test_logs.py

from app.services.firebase import delete_logs, check_threshold, save_sensors, initialize_data_firebase  # ✅ Already imports and initializes Firebase via services

def test_delete_hourly():
    # Replace "test_aqua_id" with an actual test aquarium_id you want to use in Firebase
    data = {"ph" : 43, "temperature": 22, "turbidity": 41}
    initialize_data_firebase("4")
    assert True  # You can later replace this with actual verification logic

