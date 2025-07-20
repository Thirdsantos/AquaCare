# AquaCare: Smart Aquarium Monitoring System

AquaCare is a smart aquarium monitoring system that tracks and manages key environmental parameters — including **pH**, **temperature**, and **turbidity** — to ensure a healthy aquatic environment.

The system features a **Flask-based backend** that receives sensor data from ESP32, stores logs in **Firebase Realtime Database**, sends alerts through **Firebase Cloud Messaging (FCM)**, and includes AI chatbot support to answer user queries. It also calculates **hourly and daily analytics** to help users monitor trends over time.

---

##  Features

- **Sensor Data Handling**  
  Accepts real-time data from aquarium sensors via API endpoints.

- **Threshold Monitoring & Alerts**  
  Automatically checks if sensor values exceed critical levels and sends FCM push notifications.

- **Hourly and Daily Analytics**  
  Calculates and stores aggregated data (pH, temperature, turbidity) per hour and per day.

- **AI Chatbot**  
  Users can interact with an AI chatbot to ask questions about current or historical aquarium status.

- **Firebase Realtime Database Integration**  
  Stores sensor logs and analytics with real-time data retrieval support.

---

## Technologies Used

- **Python** – Backend language  
- **Flask** – REST API framework  
- **Firebase Realtime Database** – Cloud-based JSON database  
- **Firebase Cloud Messaging (FCM)** – Real-time push notification system  

---

## AquaCare API Documentation
Base URL:
**https://aquacare-5cyr.onrender.com**

---

## Endpoints
## POST /<aquarium_id>/sensors
Description:
Receives real-time sensor data from an aquarium. The backend checks if any values exceed safe thresholds and stores the data in Firebase under the provided aquarium_id.

Request Parameters:

**aquarium_id (URL path)**: Unique ID for the aquarium (e.g., tank01)

Request Body (JSON):

{
  "ph": 7.2,
  "temperature": 27.5,
  "turbidity": 120
}
Response (JSON):


{
  "Message": "Successfully recieved",
  "Data": {
    "ph": 7.2,
    "temperature": 27.5,
    "turbidity": 120
  }
}
---
## POST /<aquarium_id>/hourly_log
Description:
Logs sensor data once per hour to Firebase for long-term analytics. It also checks thresholds just like the real-time endpoint.

Request Parameters:

**aquarium_id (URL path)**: Aquarium ID to log data under

Request Body (JSON):

{
  "ph": 6.8,
  "temperature": 26.3,
  "turbidity": 98
}
Response (JSON):

{
  "Message": "Sucessful"
}
---

## POST /ask
Description:
Sends either a text question, an image, or both to the AI (Gemini) model. The AI responds with a smart analysis or explanation — for example, interpreting water quality from an image.

Request Body (JSON):

{
  "question": "What does high turbidity mean?",
  "image": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD..."
}

 You may send:

Just question

Just image (as Base64)

Or both

Response (JSON):

{
  "AI_Response": "High turbidity usually means the water is murky, which may be harmful to aquatic life."
}


