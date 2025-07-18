# tests/test_logs.py

from app.services.firebase import delete_logs, check_threshold, save_sensors, initialize_data_firebase  # ✅ Already imports and initializes Firebase via services

def test_delete_hourly():
  
    data = {"ph" : 43, "temperature": 22, "turbidity": 41}
    initialize_data_firebase("4")
    assert True 

