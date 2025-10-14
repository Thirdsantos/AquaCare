# AquaCare: Smart Aquarium Monitoring System

**AquaCare** is a smart aquarium monitoring and automation system. It ingests real‑time water data (**pH**, **temperature**, **turbidity**), computes analytics, triggers alerts, runs one‑time/daily schedules for feeding, and exposes AI/ML tools to assist in husbandry decisions.

The backend is built with **Flask**. It writes telemetry to **Firebase Realtime Database**, manages one‑time feeding tasks in **Firestore**, schedules execution with **APScheduler** (UTC internally, Asia/Manila inputs), sends alerts via **Firebase Cloud Messaging (FCM)**, integrates an **AI** endpoint backed by Gemini, and can dispatch scheduled feed commands (with food type and cycle) to a Tank‑Pi device.

---

## Features

- **Sensor ingestion**: Real-time sensor data API with threshold checks and push alerts.
- **Analytics**: Hourly logs aggregate into daily averages with retention.
- **AI assistant**: Q&A about water quality with optional image input (Gemini).
- **Machine learning**: Compare predicted water parameters vs thresholds and get guidance.
- **Scheduling**:
  - Daily/recurring schedules in Firebase Realtime Database.
  - One-time tasks in Firestore with APScheduler.
  - Inputs are Asia/Manila local strings; APScheduler runs in UTC (automatic conversion).
  - Jobs are restored on restart; misfires within a grace window are executed.
- **Notifications**: FCM alerts on out-of-range readings with de‑duplication flags.
- **Tank‑Pi integration**: Dispatch scheduled feed commands (cycle and food) to Tank‑Pi.

---

## Technologies

- Python, Flask
- Firebase Realtime Database (telemetry, recurring schedules), Firebase Cloud Messaging (alerts)
- Google Firestore (one-time tasks: `Schedules` collection stores Manila string times)
- APScheduler (UTC scheduler with misfire grace; conversion from Asia/Manila on input)
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

PATCH `/update_daily/<aquarium_id>/<time>/<switch>`

- **Path params**: `aquarium_id` (int), `time` (HH:MM), `switch` string parsed to bool
- **Returns**:
```json
{ "status": "updated", "time": "08:30", "daily_enabled": true }
```
or
```json
{ "status": "not_found", "time": "08:30" }
```

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
{ "cycle": 2, "schedule_time": "2025-10-09 08:30:00", "food": "pellet" }
```
- **Time format**: 24‑hour `YYYY-MM-DD HH:MM:SS` in Asia/Manila (local) time.
- Stored in Firestore as a plain string (`schedule_time`), along with `cycle`, `food`, and `status`.
- APScheduler runs in UTC; the Manila string is converted to UTC for `run_date`.
- Creates a job id `schedule_at_YYYYMMDD_HHMMSS` and persists to `Firestore: Schedules/{jobId}` with `status=pending`.
- On execution, the server contacts Tank‑Pi (see below), updates Firestore `status=done`, and removes the APS job.
- **Returns**:
```json
{ "message": "Sucessfully added the schedule" }
```

POST `/task/delete/<aquarium_id>`

- **Body**:
```json
{ "schedule_time": "2025-10-09 08:30:00" }
```
- Locates the job by exact `schedule_time` string (Asia/Manila) and `aquarium_id`, removes the APS job if present, and deletes the Firestore doc.
- **Returns**:
```json
{ "message": "Sucessfully remove the schedule" }
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
  { "aquarium_id": <int>, "cycle": <int>, "food": "pellet|flakes", "job_id": "schedule_at_YYYYMMDD_HHMMSS" }
  ```
  - Timeouts and errors are logged server-side; Firestore is updated to `status=done` regardless, to ensure idempotent progress.

---

## Run locally

1. Ensure environment variable `GOOGLE_FIREBASE_KEY` contains your Firebase service account JSON (raw JSON or base64). For Realtime DB, set `databaseURL` in `app/services/__init__.py`.
2. Install dependencies and run:
```bash
python run.py
```
3. Server listens on `http://0.0.0.0:5001`.

Optional env vars:
- `TZ=Asia/Manila` (default) — input timezone for `schedule_time` strings.
- `SKIP_PI_HTTP=true` — skip Tank‑Pi HTTP calls but still mark Firestore done (useful for testing the scheduler end‑to‑end).
- The scheduler runs in UTC internally; `/status` shows `next_run_time` in UTC.

---

## Notes

- Realtime schedules are managed in Firebase under `auto_feeder/schedule` and are separate from one‑time Firestore tasks.
- Firestore one‑time tasks store `schedule_time` as a Manila string; APS converts it to UTC for execution.
- APScheduler jobs are restored at startup from Firestore pending records (misfires within grace are executed immediately).
- Use `GET /status` to see current scheduler jobs and their UTC `next_run_time`.

