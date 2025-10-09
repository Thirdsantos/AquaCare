from app.services.firebase import get_firebase_thresholds, compare_ml_firebase, get_firebase_thresholds
from app.services.firestore import add_dummy_schedules

def test_firebase_threshold():
 add_dummy_schedules()
