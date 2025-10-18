# AquaCare: Smart Aquarium Monitoring System

**AquaCare** is a smart aquarium monitoring system that tracks and manages key environmental parameters — **pH**, **temperature**, and **turbidity** — to ensure a healthy aquatic environment.

The backend is built with **Flask**, stores telemetry in **Firebase Realtime Database**, schedules and tracks feeding tasks in **Firestore** + **APScheduler**, sends alerts via **Firebase Cloud Messaging (FCM)**, exposes an **AI** endpoint backed by Gemini, and computes **hourly and daily analytics**. It also supports dispatching scheduled feed commands to a Tank-Pi device.

---

## Features

- **Sensor ingestion**: Real-time sensor data API with threshold checks and alerts.
- **Analytics**: Hourly logs roll up into daily averages with retention.
- **AI assistant**: Q&A about water quality with optional image input.
- **Scheduling**: Auto-feeder schedules saved in Firebase, plus one-time tasks in Firestore with APScheduler recovery after restarts.
- **Notifications**: FCM alerts when readings cross thresholds with edge de-duplication flags.
- **Tank-Pi integration**: Server dispatches scheduled feed tasks to Tank-Pi HTTP endpoint.

---

## Technologies

- Python, Flask
- Firebase Realtime Database (telemetry, schedules), Firebase Cloud Messaging
- Google Firestore (one-time tasks), APScheduler (job runner)
- Google Gemini API (AI)

---

## Base URL

Use your deployment base (examples below assume local):

`http://localhost:5001`

---

## API Reference

### Sensors

POST `/<aquarium_id>/sensors`

- **Path params**: `aquarium_id` (int)
- **Body**:
```json
{ "ph": 7.2, "temperature": 27.5, "turbidity": 120 }
```
- **Returns**: 200
```json
{ "Message": "Successfully recieved", "Data": { "ph": 7.2, "temperature": 27.5, "turbidity": 120 } }
```
- Notes: Initializes default structure if missing, writes to `aquariums/{id}/sensors`, evaluates thresholds and triggers FCM.

POST `/<aquarium_id>/hourly_log`

- **Path params**: `aquarium_id` (int)
- **Body**:
```json
{ "ph": 7.2, "temperature": 27.5, "turbidity": 120 }
```
- **Returns**: 200 `{ "Message": "Sucessful" }`
- Notes: Appends to hourly log with rolling index; auto-computes daily averages and prunes when full.

### AI

POST `/ask`

- **Body**:
```json
{ "question": "Is the water ok?", "image": "<base64>" }
```
- At least one of `question` or `image` is required.
- **Returns**: 200 `{ ...model response... }` or 400 when missing inputs.

### Schedule (Realtime Database)

Time format used for schedule times: 24-hour HH:MM (e.g., 00:05, 08:30, 18:05). Applies to add/update/delete/get schedule routes below.

POST `/add_schedule/<aquarium_id>`

- **Path params**: `aquarium_id` (int)
- **Body**:
```json
{ "time": "08:30", "cycle": 2, "switch": true, "food": "pellet", "daily": false }
```
- Examples: `"time": "00:05"` (12:05 AM), `"time": "18:05"` (6:05 PM)
- **Returns** (examples):
```json
{ "status": "added", "time": "08:30", "cycle": 2, "switch": true }
```
or
```json
{ "status": "duplicate", "time": "08:30", "switch": true }
```

DELETE `/delete_schedule/<aquarium_id>/<time>`

- **Path params**: `aquarium_id` (int), `time` (HH:MM)
- **Returns**:
```json
{ "status": "deleted", "time": "08:30" }
```
or
```json
{ "status": "not_found", "time": "08:30" }
```

PATCH `/update_schedule_cycle/<aquarium_id>/<time>/<cycle>`

- **Path params**: `aquarium_id` (int), `time` (HH:MM), `cycle` (int)
- **Returns**:
```json
{ "status": "updated", "time": "08:30", "cycle": 3 }
```
or
```json
{ "status": "not found", "time": "08:30" }
```

PATCH `/update_schedule_switch/<aquarium_id>/<time>/<switch>`

- **Path params**: `aquarium_id` (int), `time` (HH:MM), `switch` ("true" | "false" | "1" | "0" | "y" | "n"...)
- **Returns**:
```json
{ "status": "updated", "time": "08:30", "enabled": true }
```
or
```json
{ "status": "not_found", "time": "08:30" }
```

<!-- Daily toggle route removed; handled via schedule body and switch fields. -->

GET `/get_schedules/<aquarium_id>`

- **Path params**: `aquarium_id` (int)
- **Returns** (examples):
```json
{ "status": "success", "schedules": [ { "time": "08:30", "cycle": 2, "food": "pellet" } ] }
```
or
```json
{ "status": "empty", "schedules": [] }
```

### One-time Tasks (Firestore + APScheduler)

POST `/task/<aquarium_id>`

- **Body**:
```json
{ "cycle": 2, "schedule_time": "2025-10-09 08:30:00", "food": "pellets" }
```
- Time format for `schedule_time`: 24-hour `YYYY-MM-DD HH:MM:SS` (e.g., `2025-10-09 00:05:00`, `2025-10-09 18:05:00`).
- Interpreted in the server's local timezone.
- Schedules a one-time job with id `<aquarium_id>_schedule_at_YYYY-MM-DD HH:MM:SS`. Persisted in `Firestore: Schedules/{document_id}` as pending and registered in APScheduler. On run, it triggers Tank-Pi (see below) and marks the document `status=done`.
- **Returns**:
```json
{ "message": "Sucessfully added the schedule" }
```

POST `/task/delete/<aquarium_id>`

- **Body**:
```json
{ "document_id": "<Firestore document id>" }
```
- Deletes the Firestore document and notifies Tank-Pi of deletion.
- **Returns**:
```json
{ "message": "Successfully removed the schedule" }
```

POST `/task_complete/<document_id>`

- Marks a Firestore schedule document as completed.
- **Returns**:
```json
{ "message": "<service response>" }
```

GET `/get_pending/<aquarium_id>`

- Lists pending schedule documents for the aquarium.
- **Returns**:
```json
{ "pending_aquariums": [ { /* schedule doc */ } ] }
```

### Machine Learning

POST `/ml`

- **Body** (example list of predictions):
```json
[
  { "tank_id": 1, "predicted_ph": 7.8, "predicted_temperature": 29.0, "predicted_turbidity": 160 }
]
```
- Compares predictions to active thresholds in Firebase and requests Gemini suggestions for any out-of-range values.
- **Returns**: 200 `{ "message": "ML comparison completed successfully" }` or errors.

---

## Thresholds and Alerts

- Thresholds live at `aquariums/{id}/threshold/{sensor}/(min|max)`.
- When `aquariums/{id}/notification/{sensor}` is true and a reading is outside the range, an FCM is sent and a per-sensor `notification/state_flag` prevents duplicate spamming until readings return to normal.

---

## Tank-Pi Integration

- On one-time schedule execution, the server sends a POST to Tank-Pi:

  - URL: `https://pi-cam.alfreds.dev/{aquarium_id}/add_task`
  - Body:
```json
  { "aquarium_id": <int>, "cycle": <int>, "job_id": "schedule_at_YYYYMMDD_HHMMSS" }
  ```
  - Timeouts and errors are logged server-side; after the request the Firestore doc is updated to `status=done`.

---

## Run locally

1. Ensure environment variable `GOOGLE_FIREBASE_KEY` contains your Firebase service account JSON (raw JSON or base64). For Realtime DB, set `databaseURL` in `app/services/__init__.py`.
2. Install dependencies and run:
```bash
python run.py
```
3. Server listens on `http://0.0.0.0:5001`.

---

## Notes

- Realtime schedules are managed in Firebase under `auto_feeder/schedule` and are separate from one-time Firestore tasks.
- APScheduler jobs are restored at startup from Firestore pending records.

