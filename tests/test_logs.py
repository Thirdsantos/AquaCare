# tests/test_logs.py

from app.services.firebase import delete_logs, check_threshold, save_sensors, initialize_data_firebase, get_schedule_firebase, add_schedule_firebase, set_on_off_schedule_firebase, change_cycle_schedule_firebase, get_schedule_firebase# ✅ Already imports and initializes Firebase via services

def test_delete_hourly():
  
  d = {"time" : "10:00", "cycle" : 3}
  print(get_schedule_firebase(99))

