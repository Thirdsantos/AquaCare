# AquaCare: Smart Aquarium Monitoring System

**AquaCare** is a smart aquarium monitoring system designed to track and manage key environmental parameters — including **pH**, **temperature**, and **turbidity** — to ensure a healthy aquatic environment.

The system features a **Flask-based backend** that receives sensor data from ESP32, stores logs in **Firebase Realtime Database**, sends alerts through **Firebase Cloud Messaging (FCM)**, and includes AI chatbot support for user queries. It also computes **hourly and daily analytics** for long-term monitoring.

---

## Features

- **Sensor Data Handling**  
  Accepts real-time data from aquarium sensors via API endpoints.

- **Threshold Monitoring & Alerts**  
  Automatically detects abnormal values and sends push notifications via FCM.

- **Hourly and Daily Analytics**  
  Aggregates and stores pH, temperature, and turbidity data per hour and per day.

- **AI Chatbot Integration**  
  Allows users to ask questions about water quality using natural language or image input.

- **Firebase Integration**  
  Real-time logging of sensor values and computed analytics.

---

## Technologies Used

- **Python** – Backend development  
- **Flask** – REST API framework  
- **Firebase Realtime Database** – NoSQL cloud database  
- **Firebase Cloud Messaging (FCM)** – Push notification service  
- **Gemini API** – For AI question/answering and image analysis

---

## API Documentation

### Base URL

https://aquacare-5cyr.onrender.com


---

### `POST /<aquarium_id>/sensors`

Receives real-time sensor data from an aquarium. It stores the data in Firebase under the specified aquarium ID and checks for threshold violations to send alerts if necessary.

**Path Parameter:**

- `aquarium_id` — Unique identifier for the aquarium (e.g., `tank01`)

**Request Body:**

```json
{
  "ph": 7.2,
  "temperature": 27.5,
  "turbidity": 120
}
{
  "Message": "Successfully received",
  "Data": {
    "ph": 7.2,
    "temperature": 27.5,
    "turbidity": 120
  }
}
```
### `POST /<aquarium_id>/hourly_log`
Stores hourly sensor data into Firebase for long-term analytics. It performs the same threshold checks as the real-time endpoint.

**Path Parameter:**

- `aquarium_id` — Unique identifier for the aquarium (e.g., `tank01`)

Request Body:

```json
{
  "ph": 7.2,
  "temperature": 27.5,
  "turbidity": 120
}
```
Response:
```json
{
  "Message": "Successful"
}
```

### POST /ask

Request Body:

```json
{
  "question": "Is the water still good for my fish?"
  "image" : "base64"
}
```

Response:
```json
{
  "AI_Response": "response"
}



